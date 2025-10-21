# Netto-Null-Bilanzierung
Skripte zur Netto-Null-Bilanzierung im Urbanen Kontext


## Bilanzierung von Versiegelung und Blau-Grünen Qualitäten

Dieses Repository enthält das Skript **`scripts/bilanzierung.py`**, mit dem Flächenveränderungen zwischen *Bestands- und Planungszuständen* analysiert und bilanziert werden können. 
Grundlage ist der Ansatz der **Netto-Null-Bilanzierung**, der die Veränderungen von Flächen unter Berücksichtigung ihrer blau-grüner Qualitäten bewertet. 

Die Methode verbindet quantitative Flächenänderungen mit qualitativen Bewertungsfaktoren (z. B. Begrünung, Durchlässigkeit, Entsiegelung) und ermöglicht so eine differenzierte Bilanzierung im Sinne einer klima- und ressourcenschonenden Stadtentwicklung.

## Funktionen des Skripts

Das Python-Skript `bilanzierung.py` bietet folgende Hauptfunktionen:

- **Einlesen von Geodaten** aus Datei (z. B. GeoPackage) oder direkt aus QGIS-Layern.
- **Überlagerung** von Bestands- und Planungspolygonen zur Ermittlung der Flächenüberschneidungen.
- **Bilanzierung** der Flächenänderungen nach Kategorien (z. B. „Versiegelt“, „Teilversiegelt“, „Begrünt“, etc.).
- **Faktorbasiertes Scoring** auf Grundlage des [Biotopflächenfaktors 2020 (BFF 2020)](https://www.berlin.de/sen/uvk/_assets/natur-gruen/landschaftsplanung/bff-biotopflaechenfaktor/broschuere_bff_gesamtbericht_iasp_20201215.pdf).
- **Export** der Ergebnisse als CSV-Tabelle mit allen Flächen und Bilanzwerten.

Die Funktionen sind so ausgelegt, dass sowohl Dateiein- und -ausgabe als auch QGIS-interne Layer verwendet werden können. 

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



