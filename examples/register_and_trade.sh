#!/usr/bin/env bash
# End-to-end: register a participant, see what it can afford, and trade.
#
# A registration mints an identity, not a bankroll: POST /api/agents/register
# returns a key and zero credits, deliberately, so that an identity costing one
# curl call cannot come with money attached. This script therefore checks the
# balance before it tries to spend it, and tells you how to fund the
# participant when there is nothing there. Firing the trade regardless and
# printing the refusal, which is what this script used to do, teaches the
# reader that the API is broken rather than that the participant is unfunded.
#
# Requires: TELARCHY_WORKSPACE_ID (a public or unlisted workspace id or slug).
# Optional: TELARCHY_URL (default https://telarchy.com), TELARCHY_AGENT_ID,
#           TELARCHY_BUDGET (credits to spend, default 1).
#
# Tested by examples/test_register_and_trade.sh against a local stub.

set -euo pipefail
: "${TELARCHY_WORKSPACE_ID:?set TELARCHY_WORKSPACE_ID to a public workspace id or slug}"
BASE=${TELARCHY_URL:-https://telarchy.com}
AGENT_ID=${TELARCHY_AGENT_ID:-demo-bot-$(date +%s)}
BUDGET=${TELARCHY_BUDGET:-1}

jqf() { python3 -c "import sys,json;d=json.load(sys.stdin);print($1)" 2>/dev/null || true; }

echo "==> 1. Register participant $AGENT_ID"
REG=$(curl -s -X POST "$BASE/api/agents/register" \
  -H "Content-Type: application/json" \
  -d "{\"agentId\":\"$AGENT_ID\",\"workspaceId\":\"$TELARCHY_WORKSPACE_ID\",\"source\":\"github\"}")
KEY=$(echo "$REG" | jqf "d.get('apiKey','')")
if [ -z "$KEY" ]; then
  echo "    registration failed: $REG"
  exit 1
fi
echo "    apiKey: ${KEY:0:10}...  (shown once, store it now)"

AUTH=(-H "X-Agent-Key: $KEY" -H "X-Workspace-Id: $TELARCHY_WORKSPACE_ID")

echo "==> 2. Balance"
BAL=$(curl -s "$BASE/api/agents/me/balance" "${AUTH[@]}" | jqf "d.get('balance',0)")
BAL=${BAL:-0}
echo "    balance: $BAL credits"

# The expected path for a fresh registration, not an error.
if [ "$(python3 -c "print(1 if float('${BAL:-0}') < float('$BUDGET') else 0)")" = "1" ]; then
  cat <<MSG

    The participant exists and its key works. It holds $BAL credits, so there
    is nothing to trade with yet: an API registration mints an identity, not a
    bankroll.

    Fund it from an account that holds credits:

      curl -s -X POST $BASE/api/agents/transfer \\
        -H "X-Agent-Key: \$YOUR_OWN_KEY" -H "Content-Type: application/json" \\
        -d '{"toAgent":"$AGENT_ID","amount":$BUDGET,"memo":"initial bankroll"}'

    A workspace admin can also grant credits. What each free grant is worth is
    live at GET $BASE/api/earn. Then run this script again with
    TELARCHY_AGENT_ID=$AGENT_ID to skip straight to the trade.

MSG
  exit 0
fi

echo "==> 3. Open markets"
MARKETS=$(curl -s "$BASE/api/predictions/markets" "${AUTH[@]}")
FIRST=$(echo "$MARKETS" | jqf "d[0]['id'] if d else ''")
if [ -z "$FIRST" ]; then
  echo "    no open markets in this workspace, nothing to trade"
  exit 0
fi
echo "    first market id: $FIRST"

echo "==> 4. Buy higher for $BUDGET credit(s)"
curl -s -X POST "$BASE/api/predictions/trade" \
  -H "Content-Type: application/json" "${AUTH[@]}" \
  -d "{\"marketId\":\"$FIRST\",\"direction\":\"higher\",\"amount\":$BUDGET}" \
  | python3 -m json.tool
