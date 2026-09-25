#!/usr/bin/env bash
# Every /api path a skill names is a route in the live catalog.
#
# GET /api/help is generated from the router, so it is the contract. A skill
# that teaches a path the server no longer has sends every agent that trusts it
# into a 404 (0.31.0 still taught POST /api/proposals/:id/delivery and the
# owner calls route a week after the app removed both). The BetterAuth routes
# (/api/auth/sign-up/email, /api/auth/sign-in/email) are served by the auth
# library and are not in the catalog; they are the only exception.
#
# TELARCHY_HELP_FILE=<saved catalog> runs offline; TELARCHY_HELP_URL overrides
# the host.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAT=$(mktemp); trap 'rm -f "$CAT"' EXIT
if [ -n "${TELARCHY_HELP_FILE:-}" ]; then cp "$TELARCHY_HELP_FILE" "$CAT"
else curl -sf --max-time 30 "${TELARCHY_HELP_URL:-https://telarchy.com/api/help}" > "$CAT"; fi
python3 - "$ROOT" "$CAT" <<'PY'
import json, os, re, sys
root, cat = sys.argv[1], sys.argv[2]
ALLOW = {'/api/auth/sign-up/email', '/api/auth/sign-in/email'}
def norm(p):
    p = p.split('?')[0].split('#')[0].rstrip('/.')
    return ['*' if (s.startswith((':', '<', '{', '$')) or s == '*') else s for s in p.split('/')]
catalog = [norm(e['path']) for e in json.load(open(cat))['endpoints']]
if len(catalog) < 50: print(f'FAIL: catalog has only {len(catalog)} routes'); sys.exit(1)
def known(p):
    n = norm(p)
    return any(len(c) == len(n) and all(a == b or a == '*' or b == '*' for a, b in zip(c, n)) for c in catalog)
fails, checked = [], 0
for dirpath, _, files in os.walk(os.path.join(root, 'plugins')):
    for f in files:
        if not f.endswith('.md'): continue
        fp = os.path.join(dirpath, f)
        for i, line in enumerate(open(fp), 1):
            for p in re.findall(r'/api/[A-Za-z0-9_\-/<>:{}.$]*[A-Za-z0-9_\->}]', line):
                checked += 1
                if p.split('?')[0] in ALLOW: continue
                if not known(p): fails.append(f'{os.path.relpath(fp, root)}:{i}: {p}')
for f in fails: print('FAIL: not in the catalog:', f)
if fails: sys.exit(1)
print(f'PASS: {checked} path mentions, all in the catalog of {len(catalog)} routes')
PY
