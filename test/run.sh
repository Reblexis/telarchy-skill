#!/usr/bin/env bash
# Everything this repo can check about itself. The product is instructions, so
# the tests are about whether the instructions are true.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
fails=0
for t in "$HERE/version-consistency.sh" "$ROOT/examples/test_register_and_trade.sh"; do
  echo
  echo "### $(basename "$t")"
  bash "$t" || fails=$((fails + 1))
done
echo
if [ "$fails" -gt 0 ]; then echo "$fails test file(s) failed"; exit 1; fi
echo "all tests passed"
