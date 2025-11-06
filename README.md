# Blue-Green Infrastructure Balance

<img src="https://github.com/NFM-Flensburg/Netto-Null-Bilanzierung/blob/main/icons/icon.png" alt="drawing" width="200"/> 

## Installation

Currently, the plugin works only from a ZIP file.

1. [Download](https://github.com/NFM-Flensburg/Netto-Null-Bilanzierung/archive/master.zip) the master repository from GitHub.  
2. In QGIS, go to `Plugins → Manage and Install Plugins… → Install from ZIP` and select the downloaded ZIP file.  

---

## Usage

1. **Start the Plugin**  
   Open QGIS (version 3.16 or higher) and launch the plugin via the menu:  
   `Plugins → Net Zero Balance → Start`.

2. **Load Input Data**  
   The plugin requires **two vector layers** (or GeoJSON files):

   * **Before Layer** – contains the current sealed or built areas.  
   * **After Layer** – contains areas after / planned.

   You can also add (optionally) other information such as building gree. Either inside the dialog or
   as an additional point layer holding the information. (see example data).
   
   Example data can be found in the `example_data/` folder of the plugin.  
   These can be loaded directly into QGIS via:  
   `Layer → Add Layer → Add Vector Layer → GeoJSON`.

4. **Run the Analysis**  
   Select the layers and the corresponding fields with material or surface attributes in the plugin dialog.   

   The plugin calculates the **Blue-Green Balance** based on the *Biotope Area Factor Berlin (BFF 2020)*, taking into account the material or surface types.

5. **View and Export Results**  
   After the calculation:

   * The balance values are displayed in the plugin window.  
   * A **CSV file** with detailed results is saved to the output path you specify.  

6. **Interpretation**  
   * **Positive values** → additional sealing, compensation required.  
   * **Negative values** → balance improved (designed for de-sealing / ecological enhancement).  

> *For detailed error messages, open the Python Console in QGIS. All information will be printed there, including errors or successful results.*

---

## Background: Sealing and Blue-Green Infrastructure Balance

This plugin allows analysis and balancing of changes between **existing and new / planned states**. The approach follows the **Blue-Green Balance methodology**, evaluating changes in land surfaces with respect to their blue-green infrastructure qualities.  

The method combines quantitative area changes with qualitative evaluation factors (e.g., greening, permeability, de-sealing), enabling detailed ecological and climate-sensitive urban planning.

The Python script `script_core.py` can also be run standalone in the QGIS Python console and provides the following functions:

- **Read geospatial data** from a file (e.g., GeoPackage) or directly from QGIS layers.  
- **Overlay existing and planned polygons** to determine intersecting areas.  
- **Balance area changes** by categories (e.g., “Sealed,” “Partially Sealed,” “Green,” etc.).  
- **Factor-based scoring** according to the [Biotope Area Factor 2020 (BFF 2020)](https://www.berlin.de/sen/uvk/_assets/natur-gruen/landschaftsplanung/bff-biotopflaechenfaktor/broschuere_bff_gesamtbericht_iasp_20201215.pdf).  
- **Export results** as a CSV table with all areas and balance values.  

---

## Evaluation Method – Biotope Area Factor 2020 (BFF 2020)

The plugin uses the **Biotope Area Factor 2020 (BFF)** from the  
[Institute for Agricultural and Urban Ecological Projects (IASP)](https://www.berlin.de/sen/uvk/_assets/natur-gruen/landschaftsplanung/bff-biotopflaechenfaktor/broschuere_bff_gesamtbericht_iasp_20201215.pdf)  
to assess the ecological effectiveness of surfaces with respect to:

- Microclimate  
- Air quality  
- Biodiversity  
- Rainwater management  
- Health and recreational quality  

Factor values range from **0 (fully sealed)** to **1 (vegetated area)**, including intermediate stages such as **partially sealed, vegetated paved surfaces, or green roofs**. This allows qualitative improvements (e.g., de-sealing or greening) to be represented in quantitative area balances.

---

## Sources & Further Reading

- **Institute for Agricultural and Urban Ecological Projects (IASP) (2020)**  
  *The Biotope Area Factor 2020 – Final Report of Two Studies*  
  [PDF (Berlin.de)](https://www.berlin.de/sen/uvk/_assets/natur-gruen/landschaftsplanung/bff-biotopflaechenfaktor/broschuere_bff_gesamtbericht_iasp_20201215.pdf)

---

## AI Assistance Disclosure

Parts of this source code, documentation, or other project materials were created with the help of [ChatGPT (GPT-5) by OpenAI](https://openai.com/). All content has been reviewed and verified by the project maintainers.

---
### Project Funding

This project is funded by the **State of Schleswig-Holstein**.

<img src="nfm_logo.JPG" alt="drawing" width="400"/>
