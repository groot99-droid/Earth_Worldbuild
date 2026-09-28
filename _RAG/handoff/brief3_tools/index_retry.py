"""Run the incremental vault indexer, retrying with backoff while the SQLite DB is locked by another process.

Run from the vault root:  python index_retry.py
"""
import os
import subprocess
import sys
import time

PY = os.path.join('_RAG', '.venv', 'Scripts', 'python.exe')
ENV = dict(os.environ, PYTHONUTF8='1')
for attempt in range(1, 31):
    r = subprocess.run([PY, os.path.join('_RAG', 'build_index.py')], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=ENV)
    out = (r.stdout + r.stderr).strip().splitlines()
    print(f'attempt {attempt}: exit {r.returncode}: {out[-2:] if out else []}', flush=True)
    if r.returncode == 0:
        print('INDEX OK', flush=True)
        sys.exit(0)
    time.sleep(25)
print('GAVE UP after 30 attempts', flush=True)
sys.exit(1)
