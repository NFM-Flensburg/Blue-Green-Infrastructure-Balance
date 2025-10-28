# Netto-Null-Bilanzierung (Qgis Plugin)


&nbsp;&nbsp;&nbsp;&nbsp;![nettonullbilanzierung](https://github.com/NFM-Flensburg/Netto-Null-Bilanzierung/blob/master/icons/logo.png)

<h2>Installation</h2>
<ul>
    <li>In QGIS, select <code>Plugins > Manage and Install Plugins...</code></li>
    <li>Find <code>qgis2web</code></li>
</ul>
<p>or:</p>
<ul>
    <li><a href="https://github.com/NFM-Flensburg/Netto-Null-Bilanzierung/archive/master.zip" target="_blank">Download</a> master repository from github</li>
	<li>In QGIS, open <code>Plugins &gt; Manage and Install Plugins... &gt; Install from ZIP</code></li>	
				
</ul>

## Hingerund: Bilanzierung von Versiegelung und Blau-Grünen Qualitäten

Dieses Repository enthält ein Plugin, mit dem Flächenveränderungen zwischen *Bestands- und Planungszuständen* analysiert und bilanziert werden können. 
Grundlage ist der Ansatz der **Netto-Null-Bilanzierung**, der die Veränderungen von Flächen unter Berücksichtigung ihrer blau-grüner Qualitäten bewertet. 

Die Methode verbindet quantitative Flächenänderungen mit qualitativen Bewertungsfaktoren (z. B. Begrünung, Durchlässigkeit, Entsiegelung) und ermöglicht so eine differenzierte Bilanzierung im Sinne einer klima- und ressourcenschonenden Stadtentwicklung.

Das Python-Skript `script_core.py` bietet folgende Hauptfunktionen:

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

