
# -*- coding: utf-8 -*-
import os
import csv
from collections import defaultdict
from typing import Callable, Optional, Tuple, Dict, List

import pandas as pd
from qgis.core import QgsProject, QgsGeometry, QgsVectorLayer


def get_layer_from_project(layer_name: str) -> QgsVectorLayer:
    layers = QgsProject.instance().mapLayersByName(layer_name)
    if not layers:
        raise ValueError(f"Layer '{layer_name}' not found in QGIS project.")
    return layers[0]


def build_union_geometries(base_layer: QgsVectorLayer, field_name: str) -> Tuple[dict, dict]:
    geom_by_field = defaultdict(list)
    for feat in base_layer.getFeatures():
        geom_by_field[feat[field_name]].append(feat.geometry())

    union_by_field = {
        field_value: QgsGeometry.unaryUnion(geoms)
        for field_value, geoms in geom_by_field.items()
    }
    return geom_by_field, union_by_field


def group_layer_by_attribute(layer: QgsVectorLayer, attribute_name: str) -> dict:
    grouped = defaultdict(list)
    for feat in layer.getFeatures():
        value = feat[attribute_name]
        geom = feat.geometry()
        if geom and not geom.isEmpty():
            grouped[value].append(geom)
    return grouped


def calculate_total_area_per_group(grouped_geometries: dict) -> dict:
    return {
        group_name: sum(geom.area() for geom in geoms if geom and not geom.isEmpty())
        for group_name, geoms in grouped_geometries.items()
    }


def calculate_intersections(union_by_field: dict, grouped_plan_geoms: dict) -> list:
    results = []
    for base_value, base_geom in union_by_field.items():
        for group_value, plan_geoms in grouped_plan_geoms.items():
            intersecting_area = 0.0
            for geom in plan_geoms:
                if base_geom.intersects(geom):
                    inter_geom = base_geom.intersection(geom)
                    intersecting_area += inter_geom.area()
            results.append({'Before': base_value, 'After': group_value, 'Area': round(intersecting_area, 2)})
    return results


def calculate_unsealed_areas(grouped_plan_geoms: dict, geom_by_field: dict) -> list:
    all_plan_geoms = [g for group_geoms in grouped_plan_geoms.values() for g in group_geoms if not g.isEmpty()]
    merged_plan_geom = QgsGeometry.unaryUnion(all_plan_geoms) if all_plan_geoms else None

    all_base_geoms = [geom for geoms in geom_by_field.values() for geom in geoms]
    union_base_geom = QgsGeometry.unaryUnion(all_base_geoms) if all_base_geoms else None

    if not merged_plan_geom:
        return []

    unsealed_geom = merged_plan_geom.difference(union_base_geom) if union_base_geom else merged_plan_geom

    results = []
    if unsealed_geom and not unsealed_geom.isEmpty():
        for group_value, plan_geoms in grouped_plan_geoms.items():
            unsealed_area = 0.0
            for geom in plan_geoms:
                if unsealed_geom.intersects(geom):
                    inter_geom = unsealed_geom.intersection(geom)
                    unsealed_area += inter_geom.area()
            results.append({'Before': 'Uncovered', 'After': group_value, 'Area': round(unsealed_area, 2)})
    return results


def apply_factors_with_pandas(results: list, factors_csv: str) -> pd.DataFrame:
    df_results = pd.DataFrame(results)
    df_factors = pd.read_csv(factors_csv, sep=";")

    df_factors.columns = [c.strip() for c in df_factors.columns]
    if not {'Description', 'BFF_2020'}.issubset(df_factors.columns):
        raise ValueError("Factor CSV must contain columns: 'Description' and 'BFF_2020'")

    df_factors = df_factors[['Description', 'BFF_2020']]

    df = (
        df_results
        .merge(df_factors.rename(columns={'Description': 'Before', 'BFF_2020': 'Factor_before'}),
               on='Before', how='left')
        .merge(df_factors.rename(columns={'Description': 'After', 'BFF_2020': 'Factor_after'}),
               on='After', how='left')
    )

    # If something is missing here, validation should have stopped earlier; keep safe fill anyway.
    df['Factor_before'] = df['Factor_before'].fillna(0)
    df['Factor_after'] = df['Factor_after'].fillna(0)

    # BFF_Area
    df['BFF_Area'] = (df['Factor_after'] - df['Factor_before']) * df['Area']
    df['BFF_Area'] = df['BFF_Area'].round(2)
    return df


def add_building_green(results: list, building_green: list) -> list:
    for green in building_green or []:
        results.append(green)
    return results


def _bg_from_layer(
    building_green_layer_name: str,
    building_green_field_name: Optional[str],
    log_cb: Optional[Callable[[str], None]] = None,
) -> list:
    """Extract building-green rows from an optional layer/table."""
    out = []
    if not building_green_layer_name:
        return out

    bg_layer = get_layer_from_project(building_green_layer_name)
    field_names = [f.name() for f in bg_layer.fields()]

    area_field = "Area"
    has_area = area_field in field_names
    has_after = building_green_field_name in field_names if building_green_field_name else False

    if log_cb:
        log_cb(f"Building-green layer: {building_green_layer_name}")
        log_cb(f"  Using area field: {area_field if has_area else '(geometry area)'}")
        log_cb(f"  Using after field: {building_green_field_name if has_after else '(constant)'}")

    for feat in bg_layer.getFeatures():
        geom = feat.geometry()
        # Determine area
        area_val = None
        if has_area:
            area_val = feat[area_field]
        if area_val is None:
            # if geometry has area (polygon), use it
            if geom and not geom.isEmpty():
                try:
                    area_val = float(geom.area())
                except Exception:
                    area_val = None

        if area_val is None:
            continue

        try:
            area_val = float(area_val)
        except Exception:
            continue

        if area_val == 0:
            continue

        after_val = "Building Green"
        if has_after:
            v = feat[building_green_field_name]
            if v is not None and str(v).strip():
                after_val = str(v).strip()

        out.append({
            "Before": "Versiegelte Belagsfläche",
            "After": after_val,
            "Area": area_val,
        })

    if log_cb:
        log_cb(f"  Added {len(out)} building-green rows from layer")
    return out


def main(
    plan_field_name: str,
    base_field_name: str,
    factors_csv: str,
    output_csv_path: str,
    base_layer_name: str,
    planning_layer_name: str,
    building_green: list,
    building_green_layer_name: str = None,
    building_green_field_name: str = None,
    log_cb: Optional[Callable[[str], None]] = None,
):
    """Main calculation entry point."""
    if log_cb:
        log_cb(f"Using base layer: {base_layer_name}")
    base_layer = get_layer_from_project(base_layer_name)

    if log_cb:
        log_cb(f"Using plan layer: {planning_layer_name}")
    planning_layer = get_layer_from_project(planning_layer_name)

    # Optional building green layer
    building_green_from_layer = _bg_from_layer(building_green_layer_name, building_green_field_name, log_cb=log_cb)

    grouped_plan_geoms = group_layer_by_attribute(planning_layer, plan_field_name)
    geom_by_field, union_by_field = build_union_geometries(base_layer, base_field_name)

    results = calculate_intersections(union_by_field, grouped_plan_geoms)
    results += calculate_unsealed_areas(grouped_plan_geoms, geom_by_field)

    # Add building_green entries (layer + manual table)
    results = add_building_green(results, building_green_from_layer)
    results = add_building_green(results, building_green)

    # Apply factors and write
    results_df = apply_factors_with_pandas(results, factors_csv)

    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    # Windows-friendly for umlauts
    results_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")

    total = float(results_df["BFF_Area"].sum()) if "BFF_Area" in results_df.columns else 0.0
    if log_cb:
        log_cb(f"Results written to: {output_csv_path}")
        log_cb(f"Total balance: {int(total)} m²")

    result_dict = {
        "Total balance": f"{int(total)} m2",
        "Results path": output_csv_path,
    }
    return result_dict, results_df
