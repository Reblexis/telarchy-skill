#!/usr/bin/env bash
# telarchy-app is proprietary and its repository private (telarchy-app
# AGENTS.md, "Closed source"): a link to it is a 404 to every reader of these
# skills, and "AGPL" or "open source" about it is false. The public pieces are
# the Python client (github.com/Reblexis/telarchy-python), this skill, and the
# reference agents; name those instead.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hits=$(grep -rnE "github\.com/Reblexis/telarchy-app|AGPL|of telarchy-app|telarchy-app is open|open[- ]source.{0,40}telarchy-app" \
  "$ROOT/README.md" "$ROOT/plugins" "$ROOT/examples" 2>/dev/null || true)
if [ -n "$hits" ]; then
  echo "FAIL: the private telarchy-app is linked or called open source:"
  echo "$hits"
  exit 1
fi
echo "PASS: no skill points at the private telarchy-app"
