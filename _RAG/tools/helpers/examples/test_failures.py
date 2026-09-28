"""Verify: 403 is recorded once and not retried; 429 backs off (honouring Retry-After) and then succeeds."""
import sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # _RAG/tools
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # _RAG
import fetch_source as fs

hits = {"/blocked": 0, "/limited": 0}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        hits[self.path] = hits.get(self.path, 0) + 1
        if self.path == "/blocked":
            self.send_response(403); self.end_headers(); self.wfile.write(b"no")
        elif self.path == "/limited":
            if hits["/limited"] <= 2:
                self.send_response(429); self.send_header("Retry-After", "2"); self.end_headers(); self.wfile.write(b"slow down")
            else:
                self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
                self.wfile.write(b"<html><title>ok</title><body><p>" + b"word " * 200 + b"</p></body></html>")


srv = HTTPServer(("127.0.0.1", 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
http = fs.Http(None)

t0 = time.monotonic()
r = http.get(f"http://127.0.0.1:{port}/blocked")
print(f"403 case: status={r.status}, requests received={hits['/blocked']}, blocked map={http.blocked}, elapsed={time.monotonic()-t0:.1f}s")
assert r.status == 403 and hits["/blocked"] == 1, "403 must not be retried"

t0 = time.monotonic()
r = http.get(f"http://127.0.0.1:{port}/limited")
dt = time.monotonic() - t0
print(f"429 case: final status={r.status}, requests received={hits['/limited']}, elapsed={dt:.1f}s (two waits of 2s from Retry-After expected)")
assert r.status == 200 and hits["/limited"] == 3 and dt >= 4, "429 must back off and retry up to twice"

# a wall page served with 200 is refused, not used
assert fs.looks_walled("Just a moment... Checking your browser before accessing")
print("wall detection ok")
# the log never contains an email even when one is configured
h2 = fs.Http("someone@example.org")
h2.get(f"http://127.0.0.1:{port}/blocked")
assert "someone@example.org" not in str(h2.log), "log must not contain the contact email"
print("log is free of the contact email")
print("ALL FAILURE-HANDLING CHECKS PASSED")
