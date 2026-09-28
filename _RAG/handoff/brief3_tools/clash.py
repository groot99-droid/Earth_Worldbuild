"""Title-clash and link-target check. Run from the vault root.

Usage: python clash.py "Title A" "Title B" ...
Prints, per title, whether a note with that title already exists anywhere in the numbered vault folders.
Also writes titles.txt (one 'title<TAB>path' per line) next to this script for grep.
"""
import glob
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
titles = {}
for p in glob.glob('0[0-7]_*/**/*.md', recursive=True):
    titles.setdefault(os.path.splitext(os.path.basename(p))[0], []).append(p)
with open(os.path.join(here, 'titles.txt'), 'w', encoding='utf-8') as f:
    for t in sorted(titles):
        f.write(t + '\t' + '; '.join(titles[t]) + '\n')
print('vault titles:', len(titles))
low = {t.lower(): t for t in titles}
for t in sys.argv[1:]:
    if t in titles:
        print('CLASH  ', t, '->', titles[t])
    elif t.lower() in low:
        print('CASE-CLASH', t, '->', low[t.lower()])
    else:
        print('free   ', t)
