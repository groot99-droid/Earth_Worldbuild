"""Check hub bodies (the text above '## Notes Tagged With This Theme') against the Brief 3 Part A rules.

Usage (run from the vault root):
    python check_hubs.py <hub_dir> [<hub title> ...]

<hub_dir> holds one '<Hub Title>.md' file per hub, body only.
Link targets are resolved against the CURRENT vault: every .md under the numbered folders 00_ to 07_.
"""
import glob
import json
import os
import re
import sys

HUB_DIR = sys.argv[1]
ONLY = sys.argv[2:]
HUBS = ['Science', 'Technology', 'Religion and Belief', 'War and Conflict', 'Trade and Economy',
        'Kinship and Society', 'Language and Writing', 'Art and Ritual', 'Earth Systems and Life']

titles = {}
for p in glob.glob('0[0-7]_*/**/*.md', recursive=True):
    titles[os.path.splitext(os.path.basename(p))[0]] = p


def fm_of(path):
    t = open(path, encoding='utf-8').read()
    m = re.match(r'---\r?\n(.*?)\r?\n---', t, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip()
    return fm


meta = {}
for title, p in titles.items():
    fm = fm_of(p)
    meta[title] = dict(type=fm.get('type', ''), era=fm.get('era', '').strip('"[]'),
                       region=fm.get('region', '').strip('"[]'), path=p)

ERA_NOTES = {t for t, m in meta.items() if m['type'] == 'era'}
REGION_NOTES = {t for t, m in meta.items() if m['path'].startswith('02_Regions')}
HUMAN_ERAS = {'Paleolithic', 'Neolithic', 'Bronze Age', 'Iron Age', 'Classical Antiquity', 'Medieval Period',
              'Early Modern Period', 'Industrial Age', 'Information Age'}
SPECIAL = ['Oceania', 'Andes', 'Sub-Saharan Africa', 'Central Asian', 'Siberia and the Arctic', 'Arctic',
           'Mesoamerica', 'Southeast Asia']
OBS = ['the species', 'meaning-engine', 'story-glue', 'claim-line', 'exchange-web', 'kin-lattice', 'sound-code',
       'mark-code', 'memory-outsourcing', 'grief-rite', 'sanctioned harm', 'the settling', 'heat-domestication',
       'status-signal', 'pattern-taming', 'ancestor-weight', 'tool-lineage', 'observer']
ORDER = ['Summary', 'Key Threads', 'Through the Eras', 'Regional Patterns', 'Debates and Limits',
         "Observer's Reading", 'Open Questions']
ERA_LABELS = ['Paleolithic', 'Neolithic', 'Bronze Age', 'Iron Age', 'Classical Antiquity', 'Medieval Period',
              'Early Modern Period', 'Industrial Age', 'Information Age']


def bullets(block):
    return [l for l in block.split('\n') if l.startswith('- ')]


problems = 0
for hub in HUBS:
    if ONLY and hub not in ONLY:
        continue
    t = open(os.path.join(HUB_DIR, hub + '.md'), encoding='utf-8').read().replace('\r\n', '\n')
    secs = re.split(r'^## ', t, flags=re.M)[1:]
    names = [s.split('\n', 1)[0].strip() for s in secs]
    body = {s.split('\n', 1)[0].strip(): s.split('\n', 1)[1] for s in secs}
    issues = []
    if names != ORDER:
        issues.append(f'section order {names}')
    links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]*)?\]\]', t)
    bad = sorted({l for l in links if l not in titles})
    if bad:
        issues.append(f'BAD LINKS {bad}')
    kt = bullets(body.get('Key Threads', ''))
    if not 10 <= len(kt) <= 14:
        issues.append(f'Key Threads bullets {len(kt)}')
    nolink = [i + 1 for i, l in enumerate(kt) if '[[' not in l]
    if nolink:
        issues.append(f'Key Threads bullets without a link {nolink}')
    ktl = set(re.findall(r'\[\[([^\]|]+)', body.get('Key Threads', '')))
    eras = {meta[l]['era'] for l in ktl if l in meta and meta[l]['era']} | {l for l in ktl if l in ERA_NOTES}
    regs = {meta[l]['region'] for l in ktl if l in meta and meta[l]['region']} | {l for l in ktl if l in REGION_NOTES}
    regs.discard('Planet-wide')
    if len(eras & ERA_NOTES) < 8:
        issues.append(f'Key Threads eras {len(eras & ERA_NOTES)} {sorted(eras & ERA_NOTES)}')
    if len(regs) < 8:
        issues.append(f'Key Threads regions {len(regs)} {sorted(regs)}')
    tl = bullets(body.get('Through the Eras', ''))
    starts = [re.match(r'- \*\*([^:*]+):', l).group(1) if re.match(r'- \*\*([^:*]+):', l) else '??' for l in tl]
    if starts != ERA_LABELS:
        issues.append(f'Through the Eras labels {starts}')
    nolink = [i + 1 for i, l in enumerate(tl) if '[[' not in l]
    if nolink:
        issues.append(f'Through the Eras lines without a link {nolink}')
    rp = bullets(body.get('Regional Patterns', ''))
    if not 5 <= len(rp) <= 8:
        issues.append(f'Regional Patterns bullets {len(rp)}')
    rpt = body.get('Regional Patterns', '')
    hits = [r for r in ['Oceania', 'Andes', 'Sub-Saharan Africa', 'Central Asian', 'Siberia and the Arctic',
                        'Mesoamerica', 'Southeast Asia'] if r in rpt]
    if len(hits) < 3:
        issues.append(f'Regional Patterns special regions {hits}')
    db = bullets(body.get('Debates and Limits', ''))
    if not 3 <= len(db) <= 5:
        issues.append(f'Debates bullets {len(db)}')
    oq = bullets(body.get('Open Questions', ''))
    if not 4 <= len(oq) <= 6:
        issues.append(f'Open Questions bullets {len(oq)}')
    orr = body.get("Observer's Reading", '').strip()
    sents = len(re.findall(r'[.!?](?:\s|$)', orr))
    if not 2 <= sents <= 5:
        issues.append(f"Observer's Reading sentences {sents}")
    summ = body.get('Summary', '').strip()
    ss = len(re.findall(r'[.!?](?:\s|$)', summ))
    if not 3 <= ss <= 5:
        issues.append(f'Summary sentences {ss}')
    leak = {}
    for name, b in body.items():
        if name == "Observer's Reading":
            continue
        low = re.sub(r'\[\[[^\]]+\]\]', '', b).lower()
        for o in OBS:
            if o in low:
                leak.setdefault(name, []).append(o)
    if leak:
        issues.append(f'Observer-term leakage {leak}')
    if '—' in t or '–' in t:
        issues.append(f'dashes em={t.count(chr(0x2014))} en={t.count(chr(0x2013))}')
    print(f'== {hub}: words={len(t.split())} links={len(links)} unique={len(set(links))} '
          f'{"OK" if not issues else "ISSUES"}')
    for i in issues:
        print('   -', i)
    problems += len(issues)
print('TOTAL ISSUES', problems)
