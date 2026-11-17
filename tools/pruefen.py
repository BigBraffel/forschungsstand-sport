#!/usr/bin/env python3
# Formale Pruefung der Daten: gueltiges JSON, alle zitierten Quellen vorhanden, Abbildungen vollstaendig.
# Laeuft bei jeder Aenderung automatisch (GitHub Actions); Fehler werden im Lauf angezeigt.
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fehler = []

def keys_in(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 's' and isinstance(v, list):
                yield from (x for x in v if isinstance(x, str))
            elif k != 'cite':
                yield from keys_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from keys_in(v)

for sub in ('topics', 'screening', 'kandidaten'):
    d = os.path.join(ROOT, 'data', sub)
    if not os.path.isdir(d):
        continue
    for f in sorted(os.listdir(d)):
        if not f.endswith('.json'):
            continue
        p = os.path.join(d, f)
        try:
            j = json.load(open(p))
        except Exception as e:
            fehler.append(f'{sub}/{f}: kein gültiges JSON ({e})'); continue
        if sub != 'topics':
            continue
        src = j.get('sources', {})
        for k in set(keys_in({x: j.get(x) for x in ('rx', 'takeaways', 'vars', 'timeline')})):
            if k not in src:
                fehler.append(f'{sub}/{f}: Quelle "{k}" wird zitiert, fehlt aber in sources')
        for k, s in src.items():
            if not s.get('apa'):
                fehler.append(f'{sub}/{f}: Quelle "{k}" ohne APA-Angabe')
        vids = {v['id'] for v in j.get('vars', [])}
        for g in j.get('matrix', []):
            for k in ('bereich', 'ziel', 'kat', 'items'):
                if k not in g: fehler.append(f'{sub}/{f}: Matrix-Gruppe ohne Feld "{k}"')
            if g.get('bereich') not in ('Leistung', 'Regeneration', 'Gesundheit'):
                fehler.append(f'{sub}/{f}: Matrix-Gruppe "{g.get("ziel")}" mit unbekanntem Bereich')
            for it in g.get('items', []):
                n = it.get('n', '?')
                if it.get('g') not in ('A', 'B', 'C', 'D'): fehler.append(f'{sub}/{f}: Wirkung "{n}" ohne gültigen Grad')
                if it.get('m') not in (None, -1, 0, 1, 2, 3, 4): fehler.append(f'{sub}/{f}: Wirkung "{n}" mit ungültiger Effektgröße')
                if it.get('m') not in (0, None) and it.get('d') not in ('auf', 'ab'): fehler.append(f'{sub}/{f}: Wirkung "{n}" ohne Richtung')
                if it.get('b') not in ('nutzen', 'schaden', 'neutral'): fehler.append(f'{sub}/{f}: Wirkung "{n}" ohne Bewertung')
                if it.get('v') not in vids: fehler.append(f'{sub}/{f}: Wirkung "{n}" verweist auf unbekannten Abschnitt')
                for k in it.get('s', []):
                    if k not in src: fehler.append(f'{sub}/{f}: Wirkung "{n}" zitiert fehlende Quelle "{k}"')
        for v in j.get('vars', []):
            for fig in v.get('figs', []):
                if not fig.get('data'):
                    fehler.append(f'{sub}/{f}: Abbildung "{fig.get("id")}" ohne Daten')

html = open(os.path.join(ROOT, 'index.html')).read()
m = re.search(r'const AVAILABLE = \[(.*?)\]', html)
if m:
    for t in re.findall(r'"([^"]+)"', m.group(1)):
        if not os.path.exists(os.path.join(ROOT, 'data', 'topics', t + '.json')):
            fehler.append(f'index.html: Thema "{t}" freigeschaltet, aber data/topics/{t}.json fehlt')

if fehler:
    print('\n'.join(fehler)); sys.exit(1)
print('Alle Daten formal in Ordnung.')
