# Regeln für die inhaltliche Auswertung

Diese Regeln gelten für jeden Aktualisierungslauf, ob automatisch oder von Hand.

## Datenformat

**Themen-JSON** (`data/topics/<id>.json`):
- Felder: id, title, stand (JJJJ-MM-TT), lead, intro (optional), rxtitle, rxlead, rx, note, varstitle, takeaways, vars, sources, timeline, changelog.
- `rx` (Ableitungen): label, value, text, cite. `cite` ist ein reiner Anzeigetext.
- `takeaways`: t, ev (hoch/moderat/niedrig), p, s. `s` ist eine Liste von Quellenschlüsseln.
- `vars`: id, name, q, ev, key[], critic, figs[], s[].
- `figs`: id, title, cap, type (forest, bars, lineci, dots, tiers), data, opts. Bei Verhältnismaßen (RR, OR) gilt `opts.ref = 1`. Die genauen Formate stehen im Kommentar „Diagrammtypen“ in `index.html`.
- `sources`: Schlüssel → short, year, type, basis („Abstract“/„Volltext“), pmid, doi, apa, optional flag.
- `timeline`: y, t, p, tag (neu/conf/rel/contra), s.
- `changelog`: d (TT.MM.JJJJ), t. Der neueste Eintrag steht zuerst.

`index.html` wird nur geändert, wenn ein neues Thema hinzukommt (NAV und AVAILABLE).

## Ablauf je Thema

1. `data/kandidaten/<id>.json` lesen. Ausgewertet werden nur `neu_manuell`, `geaendert` und `vormerkungen`; alles andere wird nicht erneut geprüft.
2. Für jeden Eintrag den Abstract per efetch lesen: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&rettype=abstract&retmode=xml&id=<PMID>`.
3. Entscheiden und eintragen mit `python3 tools/pubmed_update.py set data/screening/<id>.json <PMID> <A|V|X> [kurze deutsche Notiz]`:
   - **A (aufnehmen):** Die Arbeit passt zur Fragestellung des Themas.
     - Training: gesunde Erwachsene und eine relevante Zielgröße.
     - Ernährung und Supplemente: Leistung, Regeneration und Gesundheit bei Erwachsenen ohne spezielle Erkrankung; Gesundheitsendpunkte auch aus größeren Populationen.
     - Bevorzugt werden Metaanalysen, Metaregressionen, Netzwerk-Metaanalysen, systematische Reviews und Positionspapiere.
   - **V:** relevant, aber in diesem Lauf nicht ausgewertet.
   - **X:** nicht im Fokus.
4. `geaendert`: Ist eine aufgenommene Arbeit zurückgezogen oder korrigiert, die Aussage prüfen, gegebenenfalls entfernen oder anpassen und mit `flag` markieren.
5. Je aufgenommener Arbeit:
   - Quelle mit APA-7-Zitat (deutsche Fassung) anlegen.
   - Den Befund in der passenden Variable ergänzen; nur wenn keine passt, eine neue Variable anlegen.
   - Wenn sinnvoll, eine Abbildung mit den im Abstract berichteten Zahlen ergänzen.
   - Einordnung und Evidenzgrad überprüfen; takeaways und rx anpassen, wenn sich eine Kernaussage ändert.
   - Einen Eintrag im Forschungsverlauf (timeline) ergänzen.
6. Hat sich ein Thema geändert, den changelog vorne ergänzen („PubMed: X neue Einträge gesichtet, Y aufgenommen, Z Vormerkungen ausgewertet“ plus Kurzbeschreibung) und `stand` auf das heutige Datum setzen.
7. Danach in der Kandidatendatei `"bearbeitet": true` setzen.

Zusätzlich gehört zu jedem Lauf eine kurze Websuche nach neuen Positionspapieren und Preprints, die nicht in PubMed stehen. Außerdem wird geprüft, ob für Quellen mit `flag` inzwischen vollständige Angaben oder begutachtete Fassungen vorliegen.

## APA 7 (deutsche Fassung)

- **Autoren:** „Nachname, I. I.“, verbunden mit „&amp;“, ohne Komma vor dem letzten Namen, bis 20 Autoren.
- **Titel:** in Satzschreibung. Nach einem Doppelpunkt wird großgeschrieben.
- **Zeitschrift:** großgeschrieben und kursiv, mit Band: `<em>Zeitschrift, Band</em>(Heft), Seiten`.
- **Seitenzahlen** werden ausgeschrieben (157–175, nicht 157–75); bei elektronischen Artikeln steht „Artikel N“.
- **DOI** steht separat im Feld `doi`.
- **short:** „Nachname et al., Jahr“ bzw. „A &amp; B, Jahr“.
- **Zeitschriftenname** immer aus den PubMed-Metadaten (efetch, Feld Journal/Title) übernehmen, nie raten.

## Verbindliche Regeln

- Nur wissenschaftliche Quellen; Abstracts genügen. Blogs oder News sind kein Beleg.
- Jede Zahl muss aus der Quelle stammen. Nichts schätzen oder erfinden; unsichere Angaben sichtbar markieren (`flag`).
- Kritisch nach der Evidenzhierarchie bewerten: Positionspapier/Umbrella > Netzwerk-MA/MA/Metaregression > systematischer Review > RCT > Sonstiges. Bei Widersprüchen begründen, welcher Befund wahrscheinlicher zutrifft (Studienzahl, Methodik, Aktualität, Population).
- Auf der Seite ausschließlich deutsche Sprache. Keine Originalabbildungen übernehmen. Design und Aufbau nicht verändern.
- Alte Studien bleiben erhalten. Widerlegte Befunde werden nicht gelöscht, sondern im Forschungsverlauf als überholt (`contra`/`rel`) eingeordnet.
- Vor dem Speichern muss `python3 tools/pruefen.py` fehlerfrei durchlaufen.
