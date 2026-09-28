"""House-rule check for new technology notes (and, with --essay, observer essays). Run from the vault root.

Usage: python check_notes.py [--essay] "Title A" "Title B" ...
Finds each title under 03_Entities/Artifacts-Technologies (or 05_Observer_Notes with --essay).
"""
import glob
import os
import re
import sys

args = sys.argv[1:]
ESSAY = '--essay' in args
titles_arg = [a for a in args if a != '--essay']
folder = '05_Observer_Notes' if ESSAY else '03_Entities/Artifacts-Technologies'

all_titles = set()
for p in glob.glob('0[0-7]_*/**/*.md', recursive=True):
    all_titles.add(os.path.splitext(os.path.basename(p))[0])

SOURCES = {'Encyclopaedia Britannica', 'Cambridge World History', 'English Wikipedia', 'Maps of Time (Christian)',
           'The Human Career (Klein)', 'Ancient Civilizations (Scarre and Fagan)',
           'The Dawn of Everything (Graeber and Wengrow)', 'The Transformation of the World (Osterhammel)',
           'ICS International Chronostratigraphic Chart', 'UNESCO World Heritage Centre', 'NobelPrize.org',
           'Smithsonian Human Origins Program'}
THEMES = {'science', 'technology', 'religion', 'war', 'trade', 'kinship', 'language', 'art', 'earth-systems'}
PRECISION = {'exact', 'year', 'decade', 'century', 'approx', 'deep-time'}
OBS = ['the species', 'meaning-engine', 'story-glue', 'claim-line', 'exchange-web', 'kin-lattice', 'sound-code',
       'mark-code', 'memory-outsourcing', 'grief-rite', 'sanctioned harm', 'the settling', 'heat-domestication',
       'status-signal', 'pattern-taming', 'ancestor-weight', 'tool-lineage']
ENTITY_SECTIONS = ['Summary', 'Facts', 'Context & Connections', "Observer's Reading", 'Open Questions']
ESSAY_SECTIONS = ['Question', 'What the Record Shows', "Observer's Reading", 'Limits of This Reading']
ERAS = {'Paleolithic', 'Neolithic', 'Bronze Age', 'Iron Age', 'Classical Antiquity', 'Medieval Period',
        'Early Modern Period', 'Industrial Age', 'Information Age'}
BOUNDS = [('Neolithic', -12000, -3300), ('Bronze Age', -3300, -1200), ('Iron Age', -1200, -500),
          ('Classical Antiquity', -500, 500), ('Medieval Period', 500, 1500), ('Early Modern Period', 1500, 1760),
          ('Industrial Age', 1760, 1945), ('Information Age', 1945, 3000)]

total_problems = 0
for title in titles_arg:
    path = os.path.join(folder, title + '.md')
    issues = []
    if not os.path.exists(path):
        print(f'!! {title}: file missing')
        total_problems += 1
        continue
    text = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if not m:
        print(f'!! {title}: no frontmatter')
        total_problems += 1
        continue
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    body = text[m.end():]
    if fm.get('title') != f'"{title}"':
        issues.append(f'title field {fm.get("title")}')
    want_type = 'observer-note' if ESSAY else 'technology'
    if fm.get('type') != want_type:
        issues.append(f'type {fm.get("type")}')
    if 'fact_checks' in fm:
        issues.append('has fact_checks')
    if fm.get('status') != 'seed':
        issues.append('status not seed')
    if fm.get('tags') != '[]':
        issues.append('tags not []')
    if fm.get('confidence') not in ('high', 'medium', 'low'):
        issues.append(f'confidence {fm.get("confidence")}')
    era = re.findall(r'\[\[([^\]]+)\]\]', fm.get('era', ''))
    if len(era) != 1 or era[0] not in ERAS:
        issues.append(f'era {fm.get("era")}')
    themes = [t.strip() for t in fm.get('themes', '').strip('[]').split(',') if t.strip()]
    if not themes or any(t not in THEMES for t in themes):
        issues.append(f'themes {themes}')
    srcs = re.findall(r'\[\[([^\]]+)\]\]', fm.get('sources', ''))
    if not 1 <= len(srcs) <= 3 or any(s not in SOURCES for s in srcs):
        issues.append(f'sources {srcs}')
    if ESSAY:
        for bad in ('region', 'date_start', 'date_end', 'date_precision'):
            if bad in fm:
                issues.append(f'essay has {bad}')
    else:
        region = re.findall(r'\[\[([^\]]+)\]\]', fm.get('region', ''))
        if len(region) != 1 or region[0] not in all_titles:
            issues.append(f'region {fm.get("region")}')
        try:
            ds = int(fm.get('date_start', ''))
            if ds < -11700:
                issues.append(f'date_start {ds} older than -11700')
            if era and era[0] != 'Neolithic' or True:
                for name, lo, hi in BOUNDS:
                    if name == (era[0] if era else ''):
                        if not lo <= ds < hi:
                            issues.append(f'date_start {ds} outside {name} bounds ({lo}..{hi})')
        except ValueError:
            issues.append(f'date_start {fm.get("date_start")}')
        if fm.get('date_precision') not in PRECISION:
            issues.append(f'precision {fm.get("date_precision")}')
    rel = re.findall(r'\[\[([^\]]+)\]\]', fm.get('related', ''))
    if not rel:
        issues.append('no related')
    secs = re.split(r'^## ', body, flags=re.M)[1:]
    names = [s.split('\n', 1)[0].strip() for s in secs]
    want = ESSAY_SECTIONS if ESSAY else ENTITY_SECTIONS
    if names != want:
        issues.append(f'sections {names}')
    sec = {s.split('\n', 1)[0].strip(): s.split('\n', 1)[1] if '\n' in s else '' for s in secs}
    links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]*)?\]\]', text)
    bad = sorted({l for l in links if l not in all_titles})
    if bad:
        issues.append(f'BAD LINKS {bad}')
    leak = {}
    for name, b in sec.items():
        if name == "Observer's Reading":
            continue
        low = re.sub(r'\[\[[^\]]+\]\]', '', b).lower()
        for o in OBS:
            if o in low:
                leak.setdefault(name, []).append(o)
    if leak:
        issues.append(f'Observer terms outside Reading {leak}')
    reading = sec.get("Observer's Reading", '').strip()
    rs = len(re.findall(r'[.!?](?:\s|$)', reading))
    lo, hi = (3, 6) if ESSAY else (2, 5)
    if not lo <= rs <= hi:
        issues.append(f"Reading sentences {rs}")
    if not any(o in reading.lower() for o in OBS):
        issues.append('Reading uses no Observer term')
    fbul = [l for l in sec.get('What the Record Shows' if ESSAY else 'Facts', '').split('\n') if l.startswith('- ')]
    if not fbul:
        issues.append('no bullets in facts section')
    if ESSAY and not 5 <= len(fbul) <= 8:
        issues.append(f'record bullets {len(fbul)}')
    if not ESSAY:
        oq = [l for l in sec.get('Open Questions', '').split('\n') if l.startswith('- ')]
        if not 1 <= len(oq) <= 3:
            issues.append(f'open questions {len(oq)}')
    words = len(body.split())
    wlo, whi = (350, 500) if ESSAY else (150, 315)
    if not wlo <= words <= whi:
        issues.append(f'words {words} (want {wlo}-{whi})')
    if '—' in text or '–' in text:
        issues.append('em/en dash')
    print(f'{"OK " if not issues else "!! "} {title}: words={words} links={len(set(links))} facts={len(fbul)} '
          f'date={fm.get("date_start")} {fm.get("date_precision")} era={era} conf={fm.get("confidence")}')
    for i in issues:
        print('     -', i)
    total_problems += len(issues)
print('TOTAL ISSUES', total_problems)
