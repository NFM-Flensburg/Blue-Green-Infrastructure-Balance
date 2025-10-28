# Netto-Null-Bilanzierung / Blau-Grün Bilanzierung

<img src="https://github.com/NFM-Flensburg/Netto-Null-Bilanzierung/blob/main/icons/icon.png" alt="drawing" width="200"/> 

<h2>Installation</h2>

<p>Currently only working from ZIP</p>
<ul>
    <li><a href="https://github.com/NFM-Flensburg/Netto-Null-Bilanzierung/archive/master.zip" target="_blank">Download</a> master repository from github</li>
	<li>In QGIS, open <code>Plugins &gt; Manage and Install Plugins... &gt; Install from ZIP</code></li>	
				
</ul>

## Usage 

1. **Plugin starten**
   Öffne QGIS (ab Version 3.16) und starte das Plugin **Netto-Null-Bilanzierung** über das Menü:
   `Plugins → Netto Null Bilanzierung → Start`

2. **Eingabedaten laden**
   Das Plugin benötigt **zwei Vektorebenen** (oder GeoJSON-Dateien):

   * **Bestandsebene** – enthält die aktuell versiegelten oder bebauten Flächen 
   * **Planungsebene** – enthält die geplanten oder umgestalteten Flächen.

   Beispiel-Daten findest du im Ordner `example_data/` des Plugins.
   Diese können direkt in QGIS geladen werden über
   `Layer → Datenquelle öffnen → GeoJSON`.

3. **Analyse ausführen**
   Wähle die beiden Layer und die entsprechenden Felder mit Material-Eigenschaften im Plugin-Dialog aus und starte die Analyse mit
   **„Berechnung starten“**.
   Das Plugin berechnet die **Netto-Null-Bilanz** basierend auf dem
   *Biotopflächenfaktor Berlin (BFF 2020)* und berücksichtigt die jeweiligen Material- oder Flächentypen.

4. **Ergebnisse ansehen und exportieren**
   Nach erfolgreicher Berechnung werden:

   * Die Bilanzwerte im Plugin-Fenster angezeigt.
   * Eine **CSV-Datei** mit den detaillierten Ergebnissen im gewählten Ausgabepfad gespeichert.

5. **Interpretation**
   * **Positive Werte** → Zusätzliche Versiegelung, Ausgleich erforderlich.
   * **Negative Werte** → Flächenbilanz verbessert (Entsiegelung / ökologische Aufwertung).


*Um detaillierte Fehlermeldungen zu erhalten, öffne in Qgis die Python-Console. Dort werden alle Informationen ausgegeben (sowohl im Falle eines Fehlers, als auch bei erfolgreicher Berechnung)*



## Hintegrund: Bilanzierung von Versiegelung und Blau-Grünen Qualitäten

Dieses Repository enthält ein Plugin, mit dem Flächenveränderungen zwischen *Bestands- und Planungszuständen* analysiert und bilanziert werden können. 
Grundlage ist der Ansatz der **Netto-Null-Bilanzierung**, der die Veränderungen von Flächen unter Berücksichtigung ihrer blau-grüner Qualitäten bewertet. 

Die Methode verbindet quantitative Flächenänderungen mit qualitativen Bewertungsfaktoren (z. B. Begrünung, Durchlässigkeit, Entsiegelung) und ermöglicht so eine differenzierte Bilanzierung im Sinne einer klima- und ressourcenschonenden Stadtentwicklung.

Das Python-Skript `script_core.py`, das auch standalone in der Python console in Qgis verwendet werden kann bietet folgende Hauptfunktionen:

- **Einlesen von Geodaten** aus Datei (z. B. GeoPackage) oder direkt aus QGIS-Layern.
- **Überlagerung** von Bestands- und Planungspolygonen zur Ermittlung der Flächenüberschneidungen.
- **Bilanzierung** der Flächenänderungen nach Kategorien (z. B. „Versiegelt“, „Teilversiegelt“, „Begrünt“, etc.).
- **Faktorbasiertes Scoring** auf Grundlage des [Biotopflächenfaktors 2020 (BFF 2020)](https://www.berlin.de/sen/uvk/_assets/natur-gruen/landschaftsplanung/bff-biotopflaechenfaktor/broschuere_bff_gesamtbericht_iasp_20201215.pdf).
- **Export** der Ergebnisse als CSV-Tabelle mit allen Flächen und Bilanzwerten.

## Bewertungsmethodik - Biotopflächenfaktor 2020 (BFF 2020)

Zur Bewertung der Flächenqualitäten wird der **Biotopflächenfaktor 2020 (BFF)** des  
[Instituts für Agrar- und Stadtökologische Projekte (IASP)](https://www.berlin.de/sen/uvk/_assets/natur-gruen/landschaftsplanung/bff-biotopflaechenfaktor/broschuere_bff_gesamtbericht_iasp_20201215.pdf) verwendet.  
Er bildet die Grundlage für die Bewertung der ökologischen Wirksamkeit von Flächen hinsichtlich:

- Mikroklima  
- Luftqualität  
- Biodiversität  
- Regenwasserbewirtschaftung  
- Gesundheit und Aufenthaltsqualität  

Die Faktoren reichen von **0 (versiegelt)** bis **1 (Vegetationsfläche)** und decken auch Zwischenstufen wie **teilversiegelt**, **begrünte Belagsflächen** oder **Gründach** ab.  
Damit können qualitative Veränderungen – etwa durch Entsiegelung oder Begrünung – in quantitativen Flächenbilanzen abgebildet werden.


## Quellen & weiterführende Literatur

- **Institut für Agrar- und Stadtökologische Projekte (IASP) (2020)**  
  *Der Biotopflächenfaktor 2020 – Abschluss- und Gesamtbericht zweier Studien*  
  [PDF (berlin.de)](https://www.berlin.de/sen/uvk/_assets/natur-gruen/landschaftsplanung/bff-biotopflaechenfaktor/broschuere_bff_gesamtbericht_iasp_20201215.pdf)


### Das Projekt ist gefördert vom Land Schleswig-Holstein.

<img src="nfm_logo.JPG" alt="drawing" width="400"/>

