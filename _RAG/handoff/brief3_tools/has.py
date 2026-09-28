"""Lookup titles in titles.txt (written by clash.py). Usage: python has.py "Title" ...  (or a substring, prefixed with ~)."""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
titles = {}
for line in open(os.path.join(here, 'titles.txt'), encoding='utf-8'):
    t, _, p = line.rstrip('\n').partition('\t')
    titles[t] = p
for q in sys.argv[1:]:
    if q.startswith('~'):
        s = q[1:].lower()
        hits = [t for t in titles if s in t.lower()]
        print(f'~{s}: ' + ('; '.join(hits[:12]) if hits else '(none)'))
    elif q in titles:
        print('OK       ', q)
    else:
        s = q.lower().split()[0]
        near = [t for t in titles if s in t.lower()][:5]
        print('MISSING  ', q, '  ~', '; '.join(near))
