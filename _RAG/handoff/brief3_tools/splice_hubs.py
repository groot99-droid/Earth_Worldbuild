"""Splice hub draft bodies into the vault's 04_Themes hubs.

Keeps each hub's current frontmatter and everything from '## Notes Tagged With This Theme' onward
(including the generated <!-- AUTO:members --> block). Replaces only the text between them.

Usage (from the vault root):  python splice_hubs.py <draft_dir>
"""
import os
import re
import sys

DRAFTS = sys.argv[1]
HUBS = ['Science', 'Technology', 'Religion and Belief', 'War and Conflict', 'Trade and Economy',
        'Kinship and Society', 'Language and Writing', 'Art and Ritual', 'Earth Systems and Life']
MARK = '## Notes Tagged With This Theme'

for hub in HUBS:
    vault_path = os.path.join('04_Themes', hub + '.md')
    with open(vault_path, encoding='utf-8', newline='') as f:
        cur = f.read()
    with open(os.path.join(DRAFTS, hub + '.md'), encoding='utf-8', newline='') as f:
        draft = f.read().replace('\r\n', '\n').strip('\n')
    fm = re.match(r'---\n.*?\n---\n', cur, re.S)
    if not fm or cur.count(MARK) != 1 or '<!-- AUTO:members -->' not in cur:
        print('SKIP (unexpected layout):', hub)
        continue
    head = cur[:fm.end()]
    tail = cur[cur.index(MARK):]
    new = head + '\n' + draft + '\n\n' + tail
    with open(vault_path, 'w', encoding='utf-8', newline='') as f:
        f.write(new)
    print(f'spliced {hub}: {len(cur.split())} -> {len(new.split())} words')
