#!/usr/bin/env bash
# telarchy-session's continuation helper does what references/continuation.md
# says, against a local stub of the API and of aoe (test_continuation.py).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/test_continuation.py"
