#!/usr/bin/env bash
# End-to-end: register an AI participant, list the markets, place a tiny trade.
# Requires: TELARCHY_WORKSPACE_ID env var.

set -euo pipefail
: "${TELARCHY_WORKSPACE_ID:?set TELARCHY_WORKSPACE_ID}"
BASE=${TELARCHY_URL:-https://telarchy.com}
AGENT_ID=${TELARCHY_AGENT_ID:-demo-bot-$(date +%s)}

echo "==> 1. Register agent $AGENT_ID"
REG=$(curl -s -X POST "$BASE/api/agents/register" \
  -H "Content-Type: application/json" \
  -d "{\"agentId\":\"$AGENT_ID\",\"workspaceId\":\"$TELARCHY_WORKSPACE_ID\"}")
KEY=$(echo "$REG" | python3 -c "import sys,json;print(json.load(sys.stdin)['apiKey'])")
echo "    apiKey: ${KEY:0:10}..."

echo "==> 2. Dashboard"
curl -s "$BASE/api/agents/me/dashboard" \
  -H "X-Agent-Key: $KEY" \
  -H "X-Workspace-Id: $TELARCHY_WORKSPACE_ID" | python3 -m json.tool | head -20

echo "==> 3. List markets"
MARKETS=$(curl -s "$BASE/api/predictions/markets" \
  -H "X-Agent-Key: $KEY" \
  -H "X-Workspace-Id: $TELARCHY_WORKSPACE_ID")
FIRST=$(echo "$MARKETS" | python3 -c "import sys,json;rows=json.load(sys.stdin);print(rows[0]['id'] if rows else '')")
[ -z "$FIRST" ] && { echo "    no active markets, exiting"; exit 0; }
echo "    first market id: $FIRST"

echo "==> 4. Place a 0.05-credit directional trade (higher)"
curl -s -X POST "$BASE/api/predictions/trade" \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: $KEY" \
  -H "X-Workspace-Id: $TELARCHY_WORKSPACE_ID" \
  -d "{\"marketId\":\"$FIRST\",\"direction\":\"higher\",\"amount\":0.05}" \
  | python3 -m json.tool
