import os
import csv
import pandas as pd
from collections import defaultdict
from qgis.core import (
    QgsProject, QgsGeometry, QgsVectorLayer
)


# =============================================================
# Utility Functions
# =============================================================

def get_layer_from_project(layer_name: str) -> QgsVectorLayer:
    """Retrieve a QGIS layer by name."""
    layers = QgsProject.instance().mapLayersByName(layer_name)
    if not layers:
        raise ValueError(f"Layer '{layer_name}' not found in QGIS project.")
    return layers[0]


def load_layer_from_file(file_path: str) -> QgsVectorLayer:
    """Load a GeoJSON or GeoPackage file as a QGIS vector layer."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    layer = QgsVectorLayer(file_path, os.path.basename(file_path), "ogr")
    if not layer.isValid():
        raise ValueError(f"Failed to load vector layer: {file_path}")
    return layer


def build_union_geometries(base_layer: QgsVectorLayer, field_name: str) -> tuple[dict, dict]:
    """Group and union base layer geometries by a given field."""
    geom_by_field = defaultdict(list)
    for feat in base_layer.getFeatures():
        geom_by_field[feat[field_name]].append(feat.geometry())

    union_by_field = {
        field_value: QgsGeometry.unaryUnion(geoms)
        for field_value, geoms in geom_by_field.items()
    }

    return geom_by_field, union_by_field


def group_layer_by_attribute(layer: QgsVectorLayer, attribute_name: str) -> dict:
    """Group features of a layer by an attribute value."""
    grouped = defaultdict(list)
    for feat in layer.getFeatures():
        value = feat[attribute_name]
        geom = feat.geometry()
        if geom and not geom.isEmpty():
            grouped[value].append(geom)
    return grouped


def calculate_total_area_per_group(grouped_geometries: dict) -> dict:
    """Calculate total area for each group of geometries."""
    return {
        group_name: sum(geom.area() for geom in geoms if geom and not geom.isEmpty())
        for group_name, geoms in grouped_geometries.items()
    }


def calculate_intersections(union_by_field: dict, grouped_plan_geoms: dict) -> list:
    """Calculate intersecting areas between base and planning geometries."""
    results = []
    for base_value, base_geom in union_by_field.items():
        for group_value, plan_geoms in grouped_plan_geoms.items():
            intersecting_area = 0.0
            for geom in plan_geoms:
                if base_geom.intersects(geom):
                    inter_geom = base_geom.intersection(geom)
                    intersecting_area += inter_geom.area()
            results.append({
                'Bestand': base_value,
                'Planung': group_value,
                'Area': round(intersecting_area, 2),
            })
    return results


def calculate_unsealed_areas(grouped_plan_geoms: dict, geom_by_field: dict) -> list:
    """Calculate 'unsealed' (difference) area between planning and base geometries."""
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
            results.append({
                'Bestand': 'Uncovered',
                'Planung': group_value,
                'Area': round(unsealed_area, 2),
            })
    return results


def apply_factors_with_pandas(results: list, factors_csv: str, output_csv_path: str = None) -> pd.DataFrame:
    """
    Use pandas to read factor values, merge with results, compute BFF_Area, and optionally write to CSV.

    Formula:
        BFF_Area = (Faktor_Bestand - Faktor_Planung) * Area

    Args:
        results (list[dict]): List of dictionaries with keys ['Bestand', 'Planung', 'Area'].
        factors_csv (str): Path to CSV containing at least ['Beschreibung', 'Faktor'] columns.
        output_csv_path (str, optional): If provided, writes the final dataframe to this path.

    Returns:
        pd.DataFrame: DataFrame with added columns ['Faktor_Bestand', 'Faktor_Planung', 'BFF_Area'].
    """
    # --- Load data ---
    df_results = pd.DataFrame(results)
    df_factors = pd.read_csv(factors_csv, sep=";")

    # Normalize column names
    df_factors.columns = [c.strip() for c in df_factors.columns]
    if not {'Beschreibung', 'BFF_2020'}.issubset(df_factors.columns):
        raise ValueError("Factor CSV must contain columns: 'Beschreibung' and 'BFF_2020'")
    df_factors = df_factors[['Beschreibung', 'BFF_2020']]
    
    # --- Merge factor values for Bestand and Planung ---
    df = (
        df_results
        .merge(df_factors.rename(columns={'Beschreibung': 'Bestand', 'BFF_2020': 'Faktor_Bestand'}),
               on='Bestand', how='left')
        .merge(df_factors.rename(columns={'Beschreibung': 'Planung', 'BFF_2020': 'Faktor_Planung'}),
               on='Planung', how='left')
    )

    # --- Fill missing factors with 0 ---
    df['Faktor_Bestand'] = df['Faktor_Bestand'].fillna(0)
    df['Faktor_Planung'] = df['Faktor_Planung'].fillna(0)

    # --- Calculate BFF_Area ---
    df['BFF_Area'] = (df['Faktor_Bestand'] - df['Faktor_Planung']) * df['Area']
    df['BFF_Area'] = df['BFF_Area'].round(2)

    # --- Write to CSV if requested ---
    if output_csv_path:
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        df.to_csv(output_csv_path, index=False, encoding='utf-8')
        print(f"Results with BFF_Area written to: {output_csv_path}")

    return df



def write_results_to_csv(results: list, total_area_by_group: dict, output_path: str):
    """Write all results to a CSV file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Add total area rows
    for group_name, total_area in total_area_by_group.items():
        results.append({
            'Bestand': 'Gesamt',
            'Planung': group_name,
            'Area': round(total_area, 2),
            'BFF_Area': ''
        })

    with open(output_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['Bestand', 'Planung', 'Area', 'BFF_Area'])
        writer.writeheader()
        writer.writerows(results)

    print(f"Results written to: {output_path}")


def add_building_green(results: list, building_green: list):
    """
    """
    for green in building_green:
        results.append(green)
    
    return results 

def main(
    field_name: str,
    attribute_name: str,
    factors_csv: str,
    output_csv_path: str,
    base_file: str = None,
    base_layer_name: str = None,
    planning_file: str = None,
    planning_layer_name: str = None,
    building_green: list = None
):
    """
    Netto-Null-Bilanzierung main function.

    You can provide either:
      - base_file (GeoJSON/GPKG) or base_layer_name (QGIS project layer)
      - planning_file (GeoJSON/GPKG) or planning_layer_name (QGIS project layer)
    """
    # --- Base layer ---
    if base_file:
        print(f"Using base layer from file: {base_file}")
        base_layer = load_layer_from_file(base_file)
    elif base_layer_name:
        print(f"Using base layer from project: {base_layer_name}")
        base_layer = get_layer_from_project(base_layer_name)
    else:
        raise ValueError("You must provide either 'base_file' or 'base_layer_name'.")

    # --- Planning layer ---
    if planning_file:
        print(f"Using planning layer from file: {planning_file}")
        planning_layer = load_layer_from_file(planning_file)
    elif planning_layer_name:
        print(f"Using planning layer from project: {planning_layer_name}")
        planning_layer = get_layer_from_project(planning_layer_name)
    else:
        raise ValueError("You must provide either 'planning_file' or 'planning_layer_name'.")

    if not attribute_name:
        raise ValueError("You must specify 'attribute_name' to group planning geometries.")

    grouped_plan_geoms = group_layer_by_attribute(planning_layer, attribute_name)
    geom_by_field, union_by_field = build_union_geometries(base_layer, field_name)

    total_area_by_group = calculate_total_area_per_group(grouped_plan_geoms)
    results = calculate_intersections(union_by_field, grouped_plan_geoms)
    results += calculate_unsealed_areas(grouped_plan_geoms, geom_by_field)

    results = add_building_green(results, building_green)

    # --- Apply factors and export ---
    results_df = apply_factors_with_pandas(results, factors_csv)
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    results_df.to_csv(output_csv_path, index=False, encoding="utf-8")

    print(f"\n Results written to: {output_csv_path}")
    print(f"Gesamt-BBF-Bilanz: {int(results_df['BFF_Area'].sum())} m²")


# =============================================================
# Example Usage (Qgis Python console)
# =============================================================

# if __name__ == "__main__":
project_dir = QgsProject.instance().homePath()

# Additional values not part of the layers
building_green = [
    {'Bestand': 'Versiegelt', 'Planung': "Gründach (extensiv)", 'Area': 3600},
    {'Bestand': 'Versiegelt', 'Planung': "Vertikalbegrünung (bodengebunden)", 'Area': 1000},
]

main(
    #base_layer_name="Beispielprojekt_Bestand",  
    base_file=os.path.join(
        project_dir, "NettoNullBilanzierung", "examples", "data", "Beispielprojekt_Bestand.geojson"),
    field_name="IMPV_Code",
    #planning_layer_name="Beispielprojekt_Planungen", 
    planning_file=os.path.join(
        project_dir, "NettoNullBilanzierung", "examples", "data", "Beispielprojekt_Planungen.geojson"),
    attribute_name="BBF_BEschreibung",
    factors_csv=os.path.join(project_dir, "data", "factors.csv"),
    building_green=building_green,
    output_csv_path=os.path.join(
        project_dir, "results", "NettoNullBilanz_Beispielprojekt.csv"),
)
