#!/usr/bin/env python3
# PubMed-Abgleich fuer die Website "Forschungsstand Maximalkrafttraining".
# Im Artefakt als tools/pubmed_update.txt abgelegt (das Artefakt nimmt keine .py-Dateien an).
#
#   scan  <screening.json> <kandidaten.json> [vormerk_anzahl]
#       Fragt PubMed ab dem Datum meta.letzte_abfrage_edat ab und vergleicht mit dem Register:
#       - NEU: PMIDs, die noch nicht im Register stehen. Eindeutige Faelle werden per Titelregel kodiert
#         (P, E, M, K, C, S), Uebersichtsarbeiten landen als Kandidaten zur manuellen Pruefung.
#       - GEAENDERT: registrierte PMIDs, die PubMed seitdem geaendert hat UND die jetzt als zurueckgezogen,
#         korrigiert oder bedenklich markiert sind, oder bei A/V-Eintraegen mit geaendertem Titel.
#         Routineaenderungen (z. B. MeSH-Indexierung) loesen keine erneute Pruefung aus.
#       - VORMERKUNGEN: die aeltesten V-Eintraege (Standard 5), damit die Warteliste abgearbeitet wird.
#       Schreibt das aktualisierte Register (nur Regel-Kodierungen + Abfragedatum) zurueck und alle
#       manuell zu pruefenden Faelle in <kandidaten.json>. Bereits gesichtete PMIDs werden nie erneut geprueft.
#   init  <screening.json> <kandidaten.json> <profil> <suchanfrage>
#       Legt ein neues Themenregister an (profil: training, ausdauer, regeneration oder ernaehrung): holt ALLE Treffer der Suchanfrage,
#       kodiert sie per Titelregel und schreibt alle Uebersichtsarbeiten als Kandidaten zur manuellen Pruefung.
#   set   <screening.json> <PMID> <CODE> [Notiz]
#       Traegt eine manuelle Entscheidung ein (A, V oder X). Bei A/V werden Titel/Jahr/Journal uebernommen.
import json, re, sys, subprocess, urllib.parse, time, datetime

Q = '("resistance training"[MeSH Terms] OR "strength training"[tiab] OR "resistance training"[tiab] OR "weight training"[tiab] OR powerlifting[tiab]) AND ("muscle strength"[MeSH Terms] OR "maximal strength"[tiab] OR "maximum strength"[tiab] OR 1RM[tiab] OR "one-repetition maximum"[tiab] OR "one repetition maximum"[tiab]) AND humans[MeSH Terms] AND english[lang]'
EU = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
RULES = [
 ('P', r'\b(older|elderly|aged|ageing|aging|senior|sarcopen|frail|postmenopaus|menopaus|nursing home|geriatr|octogenarian|nonagenarian|retire)'),
 ('P', r'(patient|disease|disorder|cancer|tumou?r|stroke|cardiac|heart|coronary|hypertens|diabet|obes|overweight|copd|pulmonary|asthma|arthritis|osteoarth|osteopor|rheumat|sclerosis|parkinson|dementia|cognitive impair|alzheim|hiv|renal|kidney|dialys|transplant|surgery|surgical|postoperative|arthroplast|reconstruct|fracture|injur|tendin|tendon|pain|rehabilit|patell|cruciate|acl\b|meniscus|rotator|impingement|spinal cord|cerebral palsy|down syndrome|dystroph|myopath|myositis|fibromyalg|lymphedema|sepsis|critical(ly)? ill|intensive care|hospital|disab|amput|paraplegi|tetrapleg|haemophil|hemophil|cystic fibrosis|covid|schizophren|depress|anxiety|autism|intellectual|syndrome|lupus|psoria|crohn|hepat|liver|chemo|breast|prostate|colorectal|lung|hemodial|haemodial|bariatric|frailty|incontinen|pelvic floor|pregnan|postpartum|polycystic|thyroid|insulin resist|metabolic syndrome|immobiliz|bed rest|disuse|unloading|spaceflight|microgravity|veteran|ankle instabil|low back|neck pain)'),
 ('P', r'\b(child|children|adolescen|youth|young athletes|boys|girls|pubert|pediatric|paediatric|school|junior|under-1[0-9]|u1[0-9]|prepubert|kids|juvenile|teen)'),
 ('P', r'\b(rats?|mice|mouse|murine|rodent|porcine|pigs?|dogs?|equine|horses?|in vitro|cell culture|myotube)\b'),
 ('E', r'(supplement|creatine|protein|whey|casein|amino acid|leucine|hmb|caffeine|nitrate|beetroot|vitamin|omega|fish oil|diet|nutrition|feeding|fasting|ketogen|carbohydrate|energy restriction|calori|beta-alanine|β-alanine|citrulline|ashwagandha|collagen|bicarbonate|alcohol|milk|dairy|meal|food|steroid|testosterone|nandrolone|anabolic|hormon|contracept|drug|nsaid|ibuprofen|paracetamol|acetaminophen|sodium|cannabi|nicotin)'),
 ('M', r'(reliab|validity|valid\b|reproducib|agreement|predict(ion|ing)? .*1 ?rm|estimat(e|ing|ion) of (the )?(1|one)|load-velocity|load–velocity|velocity profile|test-retest|measurement|equation|accelerometer|sensor|device|encoder|transducer|app\b|smartphone|wearable|monitoring|reference values|normative)'),
 ('K', r'(acute|post-activation|postactivation|potentiation|single session|warm-up|warm up|priming|time course of recovery|recovery after|muscle damage|soreness|doms|fatigue response|hormonal response|neuromuscular fatigue|crossover design)'),
 ('C', r'(concurrent|endurance athlete|runner|running economy|cyclist|cycling|rower|rowing|swimm|triathl|marathon|aerobic training|interval training|hiit|sprint interval)'),
]
REVPT = {'Meta-Analysis', 'Systematic Review', 'Review', 'Practice Guideline', 'Guideline', 'Consensus Development Conference'}
REVTI = re.compile(r'(meta-analy|meta-regress|systematic review|umbrella review|position stand|position statement|scoping review|network meta)', re.I)
FLAGPT = {'Retracted Publication', 'Retraction of Publication', 'Published Erratum', 'Expression of Concern', 'Corrected and Republished Article'}

def call(fn, **p):
    args = ['curl', '-sS', '-m', '120', EU + fn]
    for k, v in p.items(): args += ['--data-urlencode', f'{k}={v}']
    for attempt in range(5):
        out = subprocess.run(args, capture_output=True, text=True).stdout
        try:
            j = json.loads(out)
            if 'error' not in j: return j
        except Exception: pass
        time.sleep(2 + 2 * attempt)
    sys.exit('PubMed nicht erreichbar: ' + fn)

def search(datetype, mind, maxd, q=None):
    r = call('esearch.fcgi', db='pubmed', term=q or Q, retmode='json', retmax=10000, datetype=datetype, mindate=mind, maxdate=maxd)
    return r['esearchresult']['idlist']

def summaries(ids):
    res = {}
    for i in range(0, len(ids), 300):
        d = call('esummary.fcgi', db='pubmed', id=','.join(ids[i:i+300]), retmode='json')['result']
        for u in d.get('uids', []):
            x = d[u]
            res[u] = dict(t=x.get('title', ''), y=x.get('pubdate', '')[:4], j=x.get('source', ''), pt=x.get('pubtype', []),
                          doi=next((a['value'] for a in x.get('articleids', []) if a['idtype'] == 'doi'), None))
        time.sleep(0.4)
    return res

PROFIL = 'training'
def rule(x):
    for code, rx in RULES:
        if PROFIL == 'ernaehrung' and (code == 'E' or rx is RULES[0][1]): continue
        if PROFIL == 'ausdauer' and code == 'C': continue
        if PROFIL == 'regeneration' and code in ('K', 'E'): continue
        if PROFIL == 'regeneration' and rx is RULES[1][1]: rx = rx.replace('|injur', '').replace('|pain', '').replace('|rehabilit', '')
        if re.search(rx, x['t'], re.I): return code
    if REVTI.search(x['t']) or any(p in REVPT for p in x['pt']): return '?'
    return 'S'

def scan(regf, candf, nv=5):
    global Q, PROFIL
    reg = json.load(open(regf)); r = reg['r']
    Q = reg['meta'].get('query', Q); PROFIL = reg['meta'].get('profil', 'training')
    last = reg['meta']['letzte_abfrage_edat']
    today = datetime.date.today().strftime('%Y/%m/%d')
    # Neue Arbeiten: nach Eingangsdatum (edat) UND nach Aenderungsdatum (mdat). Frische Arbeiten haben oft noch keine
    # MeSH-Indexierung und fallen durch Filter wie humans[MeSH Terms]; sobald sie indexiert sind, aendert sich mdat.
    mdat_ids = search('mdat', last, today)
    new_ids = [u for u in dict.fromkeys(search('edat', last, today) + mdat_ids) if u not in r]
    mod_ids = [u for u in mdat_ids if u in r]
    meta = summaries(list(dict.fromkeys(new_ids + mod_ids)))
    cand = dict(abfrage=dict(von=last, bis=today), neu_manuell=[], neu_regel={}, geaendert=[], vormerkungen=[])
    for u in new_ids:
        if u not in meta: continue
        c = rule(meta[u])
        if c == '?': cand['neu_manuell'].append(dict(pmid=u, **meta[u]))
        else: r[u] = c; cand['neu_regel'][u] = c
    for u in mod_ids:
        x = meta.get(u)
        if not x: continue
        flagged = bool(FLAGPT & set(x['pt']))
        old_t = reg['d'].get(u, {}).get('t')
        title_changed = r[u] in ('A', 'V') and old_t is not None and old_t.strip().lower() != x['t'].strip().lower()
        if flagged or title_changed:
            cand['geaendert'].append(dict(pmid=u, status=r[u], markiert=sorted(FLAGPT & set(x['pt'])), titel_alt=old_t, **x))
    vs = sorted([u for u, c in r.items() if c == 'V'], key=lambda u: reg['d'].get(u, {}).get('y', '9999'))
    cand['vormerkungen'] = [dict(pmid=u, **reg['d'].get(u, {})) for u in vs[:nv]]
    reg['meta']['letzte_abfrage_edat'] = today
    reg['meta']['stand'] = today.replace('/', '-')
    reg['meta']['gesamt'] = len(r)
    json.dump(reg, open(regf, 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump(cand, open(candf, 'w'), ensure_ascii=False, indent=1)
    print(f"Zeitraum {last} bis {today}: {len(new_ids)} neue PMIDs ({len(cand['neu_regel'])} per Regel kodiert, "
          f"{len(cand['neu_manuell'])} zur manuellen Pruefung), {len(cand['geaendert'])} geaenderte relevante Eintraege, "
          f"{len(cand['vormerkungen'])} Vormerkungen zur Auswertung. Register: {len(r)} Eintraege.")

CODES_TRAINING = {"A":"Aufgenommen","V":"Vorgemerkt: relevant, noch nicht ausgewertet","X":"Übersichtsarbeit geprüft: nicht im Fokus (andere Zielgröße, Methode oder Population)","S":"Einzelstudie: nicht einzeln aufgenommen (durch Übersichtsarbeiten abgedeckt)","P":"Ausgeschlossen: Population (klinisch, Ältere, Kinder/Jugendliche, Tiere)","E":"Ernährung/Supplemente/Pharmaka: für Ernährungsseiten vorgemerkt","C":"Concurrent-/Ausdauertraining: für Ausdauerseite vorgemerkt","M":"Ausgeschlossen: Messmethodik (Tests, Reliabilität, Vorhersage)","K":"Ausgeschlossen: Akutstudie ohne Trainingsintervention"}
CODES_ERN = dict(CODES_TRAINING, P="Ausgeschlossen: Population (Erkrankte, Kinder/Jugendliche, Tiere)", C="Concurrent-/Ausdauertraining: nicht im Fokus dieses Themas", K="Ausgeschlossen: Akutstudie ohne Trainingsintervention")

def init(regf, candf, profil, query):
    global Q, PROFIL
    Q, PROFIL = query, profil
    today = datetime.date.today().strftime('%Y/%m/%d')
    ids = search('edat', '1800/01/01', today)
    meta = summaries(ids)
    r, cand = {}, []
    for u in ids:
        if u not in meta: continue
        c = rule(meta[u])
        if c == '?': cand.append(dict(pmid=u, **meta[u])); r[u] = 'X'
        else: r[u] = c
    reg = dict(meta=dict(stand=today.replace('/', '-'), letzte_abfrage_edat=today, query=query, profil=profil, gesamt=len(r),
                         hinweis='Erstsichtung: Übersichtsarbeiten manuell nach Titel (bei Aufnahme nach Abstract) geprüft; übrige Einträge regelbasiert nach Titel klassifiziert.'),
               codes=CODES_ERN if profil == 'ernaehrung' else CODES_TRAINING, r=r, d={})
    json.dump(reg, open(regf, 'w'), ensure_ascii=False, separators=(',', ':'))
    cand.sort(key=lambda x: x['y'], reverse=True)
    json.dump(cand, open(candf, 'w'), ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(ids), 'Treffer;', dict(Counter(r.values())), '; Uebersichtsarbeiten zur Pruefung:', len(cand))

def setcode(regf, pmid, code, note=''):
    assert code in ('A', 'V', 'X'), 'Code muss A, V oder X sein'
    reg = json.load(open(regf))
    reg['r'][pmid] = code
    if code in ('A', 'V'):
        d = reg['d'].get(pmid)
        if not d:
            x = summaries([pmid])[pmid]; d = dict(t=x['t'], y=x['y'], j=x['j'], n='')
        if note: d['n'] = note
        reg['d'][pmid] = d
    else:
        reg['d'].pop(pmid, None)
    reg['meta']['gesamt'] = len(reg['r'])
    json.dump(reg, open(regf, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(pmid, '->', code)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'scan': scan(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 5)
    elif cmd == 'init': init(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == 'set': setcode(sys.argv[2], sys.argv[3], sys.argv[4], ' '.join(sys.argv[5:]))
    else: sys.exit('Befehl unbekannt: ' + cmd)
