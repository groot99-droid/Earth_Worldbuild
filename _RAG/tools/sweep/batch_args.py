"""Print the next N fact-check candidates as a JSON array: python batch_args.py N [type ...]"""
import json
import subprocess
import sys
import time

N = int(sys.argv[1])
types = sys.argv[2:] or ["person", "place", "technology", "event", "era", "species", "culture", "region"]
VAULT = r"C:\Users\utopi\OneDrive\Desktop\Earth _WorldBuilding"
PY = VAULT + r"\_RAG\.venv\Scripts\python.exe"
now = time.time()
out = []
for t in types:
    if len(out) >= N:
        break
    r = subprocess.run([PY, VAULT + r"\_RAG\tools\worklist.py", "factcheck", "--type", t],
                       capture_output=True, text=True, encoding="utf-8", env={"PYTHONUTF8": "1", "SYSTEMROOT": "C:\\Windows"})
    for line in r.stdout.splitlines():
        row = json.loads(line)
        if row["mtime"] > now - 30 * 60:
            continue
        out.append({"title": row["title"], "path": row["path"].replace("\\", "/"), "type": row["type"]})
        if len(out) >= N:
            break
print(json.dumps(out, ensure_ascii=False))
