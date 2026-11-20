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

- `def` (optional, Trainingsthemen): Definition am Seitenanfang, {t, s}; nur mit wissenschaftlicher Quelle.
- Die Reihenfolge der Befunde in `key` ist egal: Die Seite ordnet sie automatisch nach Aussagekraft der zitierten Quelle (Positionspapier/Umbrella > Metaanalyse > systematischer Review > Einzelstudie > narrativer Review), innerhalb einer Stufe nach Studienzahl („N Studien“ im Text) und Jahr. Jeder Befund muss deshalb seine Quelle im Text nennen (Nachname et al., Jahr).

`index.html` wird nur geändert, wenn ein neues Thema hinzukommt (NAV und AVAILABLE; ein neues Supplement zusätzlich in SUPPS).

## Wirkungsübersicht (nur Supplemente, Feld `matrix`)

`matrix` ist eine Liste von Gruppen: bereich (Leistung/Regeneration/Gesundheit), ziel, kat, items.
- `kat` ordnet die Gruppe der themenübergreifenden Ansicht „Nach Ziel“ zu: kraft, masse, ausdauer, regeneration, entzuendung, hormone, herz, stoffwechsel, infekte, knochen, gehirn, status, sicherheit.
- Jede Wirkung (`items`) hat diese Felder:
  - n: Name
  - g: Grad
  - d: Richtung (`auf`/`ab`/null)
  - m: Größe
  - b: Bewertung (`nutzen`/`schaden`/`neutral`)
  - k: Studien der größten Analyse
  - p: Teilnehmende der größten Analyse, oder null
  - s: Quellen
  - t: Befund mit den Zahlen aus den Abstracts
  - v: zugehöriger Abschnitt in `vars`

**Grad (Verlässlichkeit, nicht Stärke).** Auf der Seite erscheint er als Beleglage mit vier Punkten: A = Stark (4), B = Gut (3), C = Begrenzt (2), D = Schwach (1), "0" = Keine Daten (leer). Es gibt bewusst keine Ampelfarben; farbig (Bernstein, „Nachteil“) sind nur Wirkungen mit b = schaden.
- A: mehrere übereinstimmende Metaanalysen oder eine große (mind. 20 Studien bzw. 1000 Teilnehmende) mit eindeutigem Ergebnis.
- B: mindestens eine Metaanalyse mit 8 oder mehr Studien, überwiegend übereinstimmend.
- C: wenige Studien, widersprüchliche Metaanalysen, hohe Heterogenität oder eingeschränkt übertragbare Population.
- D: sehr wenige oder kleine Studien, überwiegend indirekte Hinweise.
- "0": keine Daten. Für eine relevante Wirkung wurde keine Metaanalyse oder systematische Übersicht gefunden (s = [], m = null). Wird grau dargestellt.

**Größe `m`:**
- 0: nicht signifikant
- 1: SMD unter 0,2 bzw. Risikoänderung unter 10 %
- 2: SMD 0,2–0,49 bzw. 10–24 %
- 3: SMD 0,5–0,79 bzw. 25–49 %
- 4: SMD ab 0,8 bzw. ab 50 %
- null: Metaanalysen widersprechen sich
- −1: Richtung belegt, Größe nicht berichtet

Bei Rohwerten (kg, mmHg, Tage) wird die Größe nach praktischer Bedeutung eingestuft und im Befund begründet.

**Pflege bei jedem Lauf:** Wird eine Arbeit zu einem Supplement aufgenommen, die passende Wirkung prüfen und anpassen (Grad, Effekt, Studienzahl, Befund, Quellen) oder eine neue Wirkung anlegen. Ändert sich eine Einstufung, kommt das in den changelog und, wenn es einem früheren Befund widerspricht, auch in die timeline.

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
