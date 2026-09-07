#!/usr/bin/env python3
import json, re, subprocess, sys, pathlib
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HERE = pathlib.Path(__file__).resolve().parent
page, outfile = sys.argv[1], sys.argv[2]
out = subprocess.run([
    CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
    "--allow-file-access-from-files", "--hide-scrollbars",
    "--window-size=1500,1200", "--virtual-time-budget=45000",
    "--dump-dom", f"file://{HERE/page}",
], capture_output=True, text=True, timeout=280)
m = re.search(r'<pre id="report"[^>]*>(.*?)</pre>', out.stdout, re.S)
if not m:
    print(f"FAIL {page}: no report node"); sys.exit(1)
raw = m.group(1)
for a,b in [("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&#39;","'")]:
    raw = raw.replace(a,b)
d = json.loads(raw)
pathlib.Path(outfile).write_text(json.dumps(d))
if 'error' in d:
    print(f"JSERR {page}: {d['error'][:200]}"); sys.exit(1)
fails = [r for r in d['rows'] if not r['pass']]
print(f"OK {page}: measured={d['total']} failing={len(fails)} worst={min([r['ratio'] for r in fails], default='-')}")
