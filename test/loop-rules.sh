#!/usr/bin/env bash
# telarchy-loop states the rules it exists to enforce.
#
# A loop that proposes, prices, decides and executes on its own is the
# "perfect optimizer" of the metric-design guide's genie test, pointed at a
# live floor with the user's credits. What keeps it aligned is a handful of
# rules, and a skill that drops one of them teaches every agent that loads it
# to break it. Each check below is one rule from README.md, "telarchy-loop",
# looked for in the words the skill must use.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$ROOT/plugins/telarchy/skills/telarchy-loop/SKILL.md" <<'PY'
import re, sys
p = sys.argv[1]
try:
    t = open(p).read()
except FileNotFoundError:
    print(f'FAIL: {p} does not exist'); sys.exit(1)
low = ' '.join(t.lower().split())
rules = {
  'the mandate is confirmed once, before any call, and bounds everything after':
    ['mandate', 'before any call'],
  'both ways in: an existing workspace, or metrics to maximize (it opens a workspace)':
    ['given a workspace', 'given metrics', 'post /api/workspaces'],
  'the mandate names the stop condition, the budget and the worker counts':
    ['stop', 'budget', 'proposer', 'forecaster', 'executor'],
  'two decision modes, the owner deciding by default':
    ['`owner`', '`rule`', 'default'],
  'one identity per worker, created funded':
    ['one identity per worker', 'post /api/agents', 'initialcredits'],
  'no worker decides a proposal it posted or priced':
    ['no worker decides a proposal it posted or priced'],
  'a forecaster never prices a proposal it drafted':
    ['never prices a proposal it drafted'],
  'the loop never writes a reading of the metric it is judged on':
    ['never writes a reading'],
  'executors stay inside the execution scope; anything beyond it goes back to the user':
    ['execution scope', 'back to the user'],
  'the loop keeps a ledger and reads it first on resume':
    ['ledger', 'resume'],
  'an all-internal price is labelled as the loop\'s own estimate':
    ['outside trader'],
  'forecasters persist for the whole loop, across proposals, each maximizing its own profit':
    ['persist for the whole loop', 'own profit'],
  'forecasters run diverse strategies chosen for the task':
    ['diverse', 'strategy'],
  'forecasters trade the baseline markets as well as the proposal books':
    ['baseline markets'],
  'influence grows with what a forecaster earns: its bankroll is its weight, a loser is never topped up':
    ['bankroll is its weight', 'never topped up'],
  'actions that move the definition and not the goal are cut':
    ['gaming'],
}
fails = [name for name, needles in rules.items() if not all(n in low for n in needles)]
for name in fails:
    print('FAIL: telarchy-loop does not state:', name)
if fails: sys.exit(1)
print(f'PASS: telarchy-loop states all {len(rules)} rules')
PY
