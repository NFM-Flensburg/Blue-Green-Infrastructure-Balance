# -*- coding: utf-8 -*-
import os
from collections import defaultdict
from typing import Callable, Optional, Tuple

import pandas as pd
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProject,
    QgsGeometry,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsVectorFileWriter,
    QgsWkbTypes,
)


# ============================================================
# BASIC HELPERS
# ============================================================
def get_layer_from_project(layer_name: str) -> QgsVectorLayer:
    layers = QgsProject.instance().mapLayersByName(layer_name)
    if not layers:
        raise ValueError(f"Layer '{layer_name}' not found in QGIS project.")
    return layers[0]


def calculate_total_layer_area(layer: QgsVectorLayer) -> float:
    total_area = 0.0
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom and not geom.isEmpty():
            total_area += geom.area()
    return total_area


def safe_polygon_geometry(geom: QgsGeometry):
    """
    Keep only valid area-bearing geometry.
    """
    if not geom or geom.isEmpty():
        return None

    try:
        geom = geom.makeValid()
    except Exception:
        pass

    if not geom or geom.isEmpty():
        return None

    try:
        if geom.area() <= 0:
            return None
    except Exception:
        return None

    return geom


# ============================================================
# FACTORS
# ============================================================
def load_factor_table(factors_csv: str) -> pd.DataFrame:
    df_factors = pd.read_csv(factors_csv, sep=";")
    df_factors.columns = [c.strip() for c in df_factors.columns]

    if not {"Description", "BFF_2020"}.issubset(df_factors.columns):
        raise ValueError("Factor CSV must contain columns: 'Description' and 'BFF_2020'")

    df_factors = df_factors[["Description", "BFF_2020"]].copy()
    df_factors["Description"] = df_factors["Description"].astype(str).str.strip()
    return df_factors


# ============================================================
# GEOMETRY HELPERS
# ============================================================
def build_union_geometries(base_layer: QgsVectorLayer, field_name: str) -> Tuple[dict, dict]:
    geom_by_field = defaultdict(list)

    for feat in base_layer.getFeatures():
        geom = safe_polygon_geometry(feat.geometry())
        if geom is None:
            continue
        geom_by_field[feat[field_name]].append(geom)

    union_by_field = {
        field_value: QgsGeometry.unaryUnion(geoms)
        for field_value, geoms in geom_by_field.items()
        if geoms
    }
    return geom_by_field, union_by_field


def build_total_base_union(geom_by_field: dict):
    all_base_geoms = [geom for geoms in geom_by_field.values() for geom in geoms if geom and not geom.isEmpty()]
    if not all_base_geoms:
        return None
    geom = QgsGeometry.unaryUnion(all_base_geoms)
    return safe_polygon_geometry(geom)


def collect_plan_features(layer: QgsVectorLayer, attribute_name: str) -> list:
    out = []
    for feat in layer.getFeatures():
        geom = safe_polygon_geometry(feat.geometry())
        if geom is None:
            continue

        out.append({
            "After": feat[attribute_name],
            "geometry": geom,
        })
    return out


# ============================================================
# NORMAL CHANGE ROWS (BASE -> PLAN)
# ============================================================
def calculate_atomic_change_rows(
    union_by_field: dict,
    total_base_union,
    plan_features: list,
) -> list:
    rows = []

    for pf in plan_features:
        plan_geom = pf["geometry"]
        after_value = pf["After"]

        # intersection with base categories
        for before_value, base_geom in union_by_field.items():
            if not base_geom or base_geom.isEmpty():
                continue
            if not base_geom.intersects(plan_geom):
                continue

            inter_geom = base_geom.intersection(plan_geom)
            inter_geom = safe_polygon_geometry(inter_geom)
            if inter_geom is None:
                continue

            area = inter_geom.area()
            if area <= 0:
                continue

            rows.append({
                "Before": before_value,
                "After": after_value,
                "Area": round(area, 2),
                "geometry": inter_geom,
                "Source": "intersection",
            })

        # uncovered part
        uncovered_geom = plan_geom.difference(total_base_union) if total_base_union else plan_geom
        uncovered_geom = safe_polygon_geometry(uncovered_geom)
        if uncovered_geom is not None:
            area = uncovered_geom.area()
            if area > 0:
                rows.append({
                    "Before": "Uncovered",
                    "After": after_value,
                    "Area": round(area, 2),
                    "geometry": uncovered_geom,
                    "Source": "uncovered",
                })

    return rows


# ============================================================
# MEASURES / BUILDING GREEN
# ============================================================
def add_building_green(results: list, building_green: list) -> list:
    for green in building_green or []:
        results.append(green)
    return results


def _bg_from_layer(
    building_green_layer_name: str,
    building_green_field_name: Optional[str],
    log_cb: Optional[Callable[[str], None]] = None,
) -> list:
    """
    Measures from optional layer.
    Assumption:
    - Before is fixed as 'Versiegelte Belagsfläche'
    - After comes from the provided field (e.g. Gründach ...)
    """
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
        geom = safe_polygon_geometry(feat.geometry())

        area_val = None
        if has_area:
            area_val = feat[area_field]

        if area_val is None and geom is not None:
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
            "Area": round(area_val, 2),
            "geometry": geom,
            "Source": "building_green_layer",
        })

    if log_cb:
        log_cb(f"  Added {len(out)} building-green rows from layer")

    return out


def split_rows_for_spatial(rows: list) -> tuple:
    """
    Separate rows with geometry (for spatial output)
    from rows without geometry (for balance only).
    """
    spatial_rows = []
    nonspatial_rows = []

    for row in rows or []:
        geom = row.get("geometry")
        if geom is not None and not geom.isEmpty():
            spatial_rows.append(row)
        else:
            nonspatial_rows.append(row)

    return spatial_rows, nonspatial_rows


# ============================================================
# FACTOR APPLICATION
# ============================================================
def apply_factors_to_rows(rows: list, factors_csv: str) -> pd.DataFrame:
    df_results = pd.DataFrame(rows)
    if df_results.empty:
        return df_results

    df_factors = load_factor_table(factors_csv)

    df = (
        df_results
        .merge(
            df_factors.rename(columns={"Description": "Before", "BFF_2020": "Factor_before"}),
            on="Before",
            how="left",
        )
        .merge(
            df_factors.rename(columns={"Description": "After", "BFF_2020": "Factor_after"}),
            on="After",
            how="left",
        )
    )

    df["Factor_before"] = df["Factor_before"].fillna(0)
    df["Factor_after"] = df["Factor_after"].fillna(0)

    df["DeltaFactor"] = (df["Factor_after"] - df["Factor_before"]).round(3)
    df["BFF_Area"] = (df["DeltaFactor"] * df["Area"]).round(2)

    def classify_delta(v):
        if v > 0:
            return "improvement"
        if v < 0:
            return "decline"
        return "neutral"

    df["ChangeClass"] = df["DeltaFactor"].apply(classify_delta)
    return df


# ============================================================
# AGGREGATION
# ============================================================
def aggregate_change_rows(df_atomic: pd.DataFrame) -> pd.DataFrame:
    if df_atomic.empty:
        return df_atomic

    group_cols = ["Before", "After", "Factor_before", "Factor_after", "DeltaFactor"]

    df_agg = (
        df_atomic.groupby(group_cols, dropna=False, as_index=False)
        .agg({
            "Area": "sum",
            "BFF_Area": "sum",
        })
    )

    df_agg["Area"] = df_agg["Area"].round(2)
    df_agg["BFF_Area"] = df_agg["BFF_Area"].round(2)
    return df_agg


# ============================================================
# SPATIAL OUTPUT
# ============================================================
def write_spatial_change_layer(
    df: pd.DataFrame,
    output_path: str,
    crs,
    layer_name: str = "spatial_changes",
) -> str:
    if df.empty:
        return output_path

    fields = QgsFields()
    fields.append(QgsField("Before", QVariant.String))
    fields.append(QgsField("After", QVariant.String))
    fields.append(QgsField("Area", QVariant.Double))
    fields.append(QgsField("F_before", QVariant.Double))
    fields.append(QgsField("F_after", QVariant.Double))
    fields.append(QgsField("Delta", QVariant.Double))
    fields.append(QgsField("BFF_Area", QVariant.Double))
    fields.append(QgsField("Class", QVariant.String))
    fields.append(QgsField("Source", QVariant.String))

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name

    writer = QgsVectorFileWriter.create(
        output_path,
        fields,
        QgsWkbTypes.MultiPolygon,
        crs,
        QgsProject.instance().transformContext(),
        options,
    )

    if writer.hasError() != QgsVectorFileWriter.NoError:
        raise ValueError(f"Could not create spatial output: {writer.errorMessage()}")

    for _, row in df.iterrows():
        geom = safe_polygon_geometry(row.get("geometry"))
        if geom is None:
            continue

        feat = QgsFeature(fields)
        feat.setGeometry(geom)

        feat["Before"] = str(row.get("Before", ""))
        feat["After"] = str(row.get("After", ""))
        feat["Area"] = float(row.get("Area", 0))
        feat["F_before"] = float(row.get("Factor_before", 0))
        feat["F_after"] = float(row.get("Factor_after", 0))
        feat["Delta"] = float(row.get("DeltaFactor", 0))
        feat["BFF_Area"] = float(row.get("BFF_Area", 0))
        feat["Class"] = str(row.get("ChangeClass", ""))
        feat["Source"] = str(row.get("Source", ""))

        writer.addFeature(feat)

    del writer
    return output_path


# ============================================================
# MAIN
# ============================================================
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
    """
    Main calculation entry point.

    Logic:
    - normal plan/base intersections
    - measures from optional building_green layer
    - manual building_green rows
    - one shared factor logic
    - balance and spatial output remain consistent
    """
    if log_cb:
        log_cb(f"Using base layer: {base_layer_name}")
    base_layer = get_layer_from_project(base_layer_name)

    if log_cb:
        log_cb(f"Using plan layer: {planning_layer_name}")
    planning_layer = get_layer_from_project(planning_layer_name)

    # optional measures from layer
    building_green_from_layer = _bg_from_layer(
        building_green_layer_name,
        building_green_field_name,
        log_cb=log_cb,
    )

    # --------------------------------------------------------
    # 1) normal atomic rows from plan/base logic
    # --------------------------------------------------------
    plan_features = collect_plan_features(planning_layer, plan_field_name)
    geom_by_field, union_by_field = build_union_geometries(base_layer, base_field_name)
    total_base_union = build_total_base_union(geom_by_field)

    normal_atomic_rows = calculate_atomic_change_rows(
        union_by_field=union_by_field,
        total_base_union=total_base_union,
        plan_features=plan_features,
    )

    # --------------------------------------------------------
    # 2) measures rows
    # --------------------------------------------------------
    bg_layer_spatial_rows, bg_layer_nonspatial_rows = split_rows_for_spatial(building_green_from_layer)
    manual_bg_spatial_rows, manual_bg_nonspatial_rows = split_rows_for_spatial(building_green or [])

    # --------------------------------------------------------
    # 3) master rows for balance
    # --------------------------------------------------------
    balance_rows = []
    balance_rows.extend(normal_atomic_rows)
    balance_rows.extend(building_green_from_layer)
    balance_rows.extend(building_green or [])

    balance_df_atomic = apply_factors_to_rows(balance_rows, factors_csv)
    results_df = aggregate_change_rows(balance_df_atomic)

    # --------------------------------------------------------
    # 4) master rows for spatial output
    # --------------------------------------------------------
    spatial_rows = []
    spatial_rows.extend(normal_atomic_rows)
    spatial_rows.extend(bg_layer_spatial_rows)
    spatial_rows.extend(manual_bg_spatial_rows)

    spatial_df = apply_factors_to_rows(spatial_rows, factors_csv)

    # --------------------------------------------------------
    # 5) write outputs
    # --------------------------------------------------------
    output_dir = os.path.dirname(output_csv_path)
    os.makedirs(output_dir, exist_ok=True)

    results_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")

    spatial_output_path = os.path.splitext(output_csv_path)[0] + "_spatial_changes.gpkg"
    write_spatial_change_layer(
        spatial_df,
        output_path=spatial_output_path,
        crs=planning_layer.crs(),
        layer_name="spatial_changes",
    )

    # --------------------------------------------------------
    # 6) summary / log
    # --------------------------------------------------------
    net_balance = float(results_df["BFF_Area"].sum()) if "BFF_Area" in results_df.columns else 0.0
    total_planning_area = calculate_total_layer_area(planning_layer)
    percentage = (net_balance / total_planning_area * 100) if total_planning_area > 0 else 0.0

    if log_cb:
        log_cb(f"Results written to: {output_csv_path}")
        log_cb(f"Spatial change layer written to: {spatial_output_path}")
        log_cb("")
        log_cb("===== BALANCE SUMMARY =====")
        log_cb(f"Total planning area : {total_planning_area:.2f} m²")
        log_cb(f"Net Balance         : {net_balance:.2f} m²")
        log_cb(f"Percentage          : {percentage:.2f} %")
        log_cb("")
        log_cb("===== SPATIAL CHANGE FIELD =====")
        log_cb("Use field 'Delta' for coloring the polygons:")
        log_cb("  positive  = improvement")
        log_cb("  negative  = decline")
        log_cb("  zero      = neutral")
        log_cb("")
        log_cb("===== MEASURES SUMMARY =====")
        log_cb(f"Measures from layer (all)     : {len(building_green_from_layer)}")
        log_cb(f"Measures from layer (spatial) : {len(bg_layer_spatial_rows)}")
        log_cb(f"Measures manual (all)         : {len(building_green or [])}")
        log_cb(f"Measures manual (spatial)     : {len(manual_bg_spatial_rows)}")

    result_dict = {
        "Total planning area": f"{total_planning_area:.2f} m2",
        "Net Balance": f"{net_balance:.2f} m2",
        "Percentage": f"{percentage:.2f} %",
        "Results path": output_csv_path,
        "Spatial change path": spatial_output_path,
    }
    return result_dict, results_df
