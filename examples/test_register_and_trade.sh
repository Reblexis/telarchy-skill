#!/usr/bin/env bash
# Test for register_and_trade.sh, run against a local stub of the API.
#
# The example is the only end-to-end script in this repo, so it is the one
# thing here that can be wrong in a way a reader cannot detect: it reads as
# authoritative. The 2026-09-01 DX review found it placing a 0.05-credit trade
# straight after a registration that is documented to mint zero credits, so it
# could never reach its own last step.
#
# Two cases, because the script has two paths and both have been wrong before:
#   1. zero credits, the state a real registration leaves you in. The script
#      must say so and name the call that fixes it, not fire a doomed trade.
#   2. funded. The script must actually trade, and the body it sends is pinned
#      to the route's real field names.
#
# Run: bash examples/test_register_and_trade.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=${PORT:-8799}
STUB_LOG=$(mktemp)
TRADE_BODY=$(mktemp)
trap 'kill "${STUB_PID:-0}" 2>/dev/null || true; rm -f "$STUB_LOG" "$TRADE_BODY"' EXIT

run_stub() {  # $1 = balance the stub reports, $2 = file to record the trade body in
python3 - "$PORT" "$1" "$2" <<'PYEOF' > "$STUB_LOG" 2>&1 &
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

BALANCE = float(sys.argv[2])   # 0 = what a real API registration mints
TRADE_LOG = sys.argv[3]        # where the trade body is recorded, for assertions

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(n).decode()
        if self.path.startswith('/api/agents/register'):
            return self._send(201, {'agentId': 'stub-bot', 'apiKey': 'stub-key-value', 'nickname': None})
        if self.path.startswith('/api/predictions/trade'):
            with open(TRADE_LOG, 'w') as f:
                f.write(body)
            if BALANCE <= 0:
                return self._send(400, {'error': 'Insufficient balance: this participant holds 0 credits.',
                                        'balance': 0, 'cost': 0.05})
            return self._send(201, {'tradeId': 't1', 'shares': 1.0, 'cost': 1.0, 'consensus': 11})
        return self._send(404, {'error': 'Not found', 'path': self.path})
    def do_GET(self):
        if self.path.startswith('/api/agents/me/balance'):
            return self._send(200, {'balance': BALANCE})
        if self.path.startswith('/api/predictions/markets'):
            return self._send(200, [{'id': 'stub-market', 'metricName': 'Activation',
                                     'consensus': 10, 'liquidity': 100}])
        return self._send(404, {'error': 'Not found', 'path': self.path})

HTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()
PYEOF
STUB_PID=$!
for _ in $(seq 1 60); do
  curl -s -o /dev/null "http://127.0.0.1:$PORT/api/agents/me/balance" && return 0
  sleep 0.1
done
echo "stub never came up"; cat "$STUB_LOG"; exit 1
}

stop_stub() { kill "${STUB_PID:-0}" 2>/dev/null || true; wait "${STUB_PID:-0}" 2>/dev/null || true; }

run_example() {
  set +e
  OUT=$(TELARCHY_URL="http://127.0.0.1:$PORT" \
        TELARCHY_WORKSPACE_ID="stub-workspace" \
        TELARCHY_AGENT_ID="stub-bot" \
        bash "$HERE/register_and_trade.sh" 2>&1)
  CODE=$?
  set -e
}

fail() { echo "FAIL: $1"; echo "--- script output ---"; echo "$OUT"; exit 1; }

echo "== case 1: a fresh registration, zero credits =="
: > "$TRADE_BODY"
run_stub 0 "$TRADE_BODY"
run_example
stop_stub

# A zero balance is the ordinary path, not an error the reader must debug.
[ "$CODE" -eq 0 ] || fail "exited $CODE on the ordinary zero-credit path"
# The rule: an API registration mints an identity, not a bankroll. Say it.
echo "$OUT" | grep -qi "0 credits\|no credits\|zero credits" \
  || fail "never says the new participant holds no credits"
# And hand over the call that fixes it, naming the participant to fund.
echo "$OUT" | grep -q "/api/agents/transfer" \
  || fail "never names the transfer call that funds the participant"
echo "$OUT" | grep -q "stub-bot" || fail "never names the participant to fund"
# It must not fire a trade it already knows will be refused.
[ -s "$TRADE_BODY" ] && fail "attempted the trade anyway, at zero credits"
echo "$OUT" | grep -q "Insufficient balance" && fail "printed a refusal instead of guidance"

echo "== case 2: a funded participant actually trades =="
: > "$TRADE_BODY"
run_stub 100 "$TRADE_BODY"
run_example
stop_stub

[ "$CODE" -eq 0 ] || fail "exited $CODE with a funded balance"
[ -s "$TRADE_BODY" ] || fail "never placed a trade despite holding credits"
# The field name is the contract. The trader prompt shipped outcome:"HIGHER"
# against a route that has only ever read direction:"higher", so the example is
# pinned to the real fields here rather than trusted to stay right.
grep -q '"direction"' "$TRADE_BODY" || fail "trade body omits direction: $(cat "$TRADE_BODY")"
grep -qE '"(higher|lower)"' "$TRADE_BODY" || fail "direction not lowercase: $(cat "$TRADE_BODY")"
grep -q '"marketId"' "$TRADE_BODY" || fail "trade body omits marketId: $(cat "$TRADE_BODY")"

echo "PASS: register_and_trade.sh handles both the zero-credit and the funded path"
