#!/usr/bin/env python3
# Fragt PubMed fuer alle Themen ab und legt die manuell zu pruefenden Faelle in data/kandidaten/<thema>.json ab.
# Laeuft automatisch per GitHub Actions (alle 2 Wochen freitags), kann aber auch lokal gestartet werden:
#   python3 tools/scan_all.py            -> nur in Lauf-Wochen (Abstand zu 20.11.2026 durch 14 teilbar)
#   python3 tools/scan_all.py --immer    -> sofort, unabhaengig vom Rhythmus
#
# Kandidatendateien, die noch nicht ausgewertet sind ("bearbeitet": false), werden nicht ueberschrieben,
# sondern um die neuen Faelle ergaenzt. So geht nichts verloren, falls eine Auswertung ausfaellt.
import datetime, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = datetime.date(2026, 11, 20)
VORMERK = 2

def main():
    heute = datetime.date.today()
    if '--immer' not in sys.argv and (heute - START).days % 14 != 0:
        print(f'{heute}: keine Lauf-Woche, nichts zu tun.')
        return
    regdir = os.path.join(ROOT, 'data', 'screening')
    canddir = os.path.join(ROOT, 'data', 'kandidaten')
    os.makedirs(canddir, exist_ok=True)
    uebersicht = {}
    for f in sorted(os.listdir(regdir)):
        if not f.endswith('.json'):
            continue
        thema = f[:-5]
        regf, candf = os.path.join(regdir, f), os.path.join(canddir, f)
        alt = json.load(open(candf)) if os.path.exists(candf) else None
        tmp = candf + '.neu'
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'pubmed_update.py'), 'scan', regf, tmp, str(VORMERK)], check=True)
        neu = json.load(open(tmp)); os.remove(tmp)
        if alt and not alt.get('bearbeitet', False):
            gesehen = {x['pmid'] for k in ('neu_manuell', 'geaendert') for x in alt.get(k, [])}
            for k in ('neu_manuell', 'geaendert'):
                alt[k] += [x for x in neu[k] if x['pmid'] not in gesehen]
            alt['neu_regel'].update(neu['neu_regel'])
            alt['vormerkungen'] = neu['vormerkungen']
            alt['abfrage']['bis'] = neu['abfrage']['bis']
            neu = alt
        neu['bearbeitet'] = False
        neu['thema'] = thema
        json.dump(neu, open(candf, 'w'), ensure_ascii=False, indent=1)
        uebersicht[thema] = dict(manuell=len(neu['neu_manuell']), geaendert=len(neu['geaendert']),
                                 regel=len(neu['neu_regel']), vormerkungen=len(neu['vormerkungen']))
    json.dump(dict(datum=heute.isoformat(), themen=uebersicht), open(os.path.join(canddir, '_uebersicht.json'), 'w'),
              ensure_ascii=False, indent=1)
    print(json.dumps(uebersicht, ensure_ascii=False, indent=1))
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'rueckzug.py')], check=True)

if __name__ == '__main__':
    main()
