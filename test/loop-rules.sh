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
  'the mandate is fixed and written to the ledger before any call':
    ['mandate', 'before any call', 'ledger'],
  'when the user said not to ask, the mandate is inferred and written down, not asked':
    ['inferred', 'not to ask'],
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
  # Unattended operation: the operator is away for hours (hackathon-game loop,
  # 2026-09-27/28, docs/retro/telarchy-product-lessons.md in that repo).
  'the orchestrator writes a heartbeat to the ledger every cycle':
    ['heartbeat'],
  'a resumed loop never re-posts proposals or re-creates workers':
    ['never re-post', 're-create'],
  'workers die mid-task: they commit early and the orchestrator finishes committed work instead of re-running it':
    ['commit early', 'instead of re-running'],
  'every API call has a timeout and retries':
    ['timeout', 'retries'],
  'a retried proposal post carries an Idempotency-Key':
    ['idempotency-key'],
  'evaluators start the moment a proposal is funded; no proposal lapses unpriced':
    ['the moment a proposal is funded', 'lapses unpriced'],
  'one merge path, and an integration step gives the owner one build':
    ['one merge path', 'integration', 'one build'],
  'cadence comes from the harness scheduler; a blocked self-restart watchdog is not routed around':
    ['scheduler', 'watchdog'],
  'the reading plan: who reads the metric and when, manual settlement or N/A for a person-reported metric':
    ['reading plan', 'until-settled', 'resolvesnauntilmeasured', 'person'],
  'a reading lands before any clock-settled date':
    ['before any clock-settled date'],
  'the credit bill is computed up front; ask for funding or choose smaller seeds and record the choice':
    ['credit bill', 'ask for funding', 'smaller seeds', 'record the choice'],
  'unattended default decision mode is a written numeric rule, since the owner is away':
    ['unattended', 'owner is away'],
  'the loop stops on its own and leaves a final report':
    ['final report'],
  # Decentralized standing workers are the default (Viktor, 2026-09-30:
  # "the agents should be decentralized not being laucnhed by you they should
  # work decentrilzied on improvign the numbers").
  'the default operating mode is decentralized standing workers, each launched once':
    ['decentralized', 'default', 'launch each worker once', 'standing'],
  'the orchestrator does not run cycles or choose what workers propose':
    ['does not run cycles', 'does not choose what'],
  'the owner\'s feedback goes verbatim into a shared brief every worker re-reads each pass':
    ['brief', 'verbatim', 're-reads', 'every pass'],
  'deliveries go to a shared deliveries log the orchestrator surfaces to the owner':
    ['deliveries log', 'surface'],
  'workers coordinate only through the floor and the shared files':
    ['only through the floor and the shared files'],
  'every worker keeps a status file so a fresh copy resumes after a crash':
    ['status file', 'resumes'],
  'a dead worker is restarted with the same prompt':
    ['same prompt'],
  'each worker runs until the stop condition, including a STOP file':
    ['until the stop condition', 'stop file'],
  'waits are short bounded loops because the harness may cap long waits':
    ['bounded', 'cap'],
  # Trailer Lab run, 2026-09-29/30.
  'telarchy.com refuses trades on a private floor; preflight checks it':
    ['workspace_not_public', 'public floor', 'self-hosted'],
  'the approval bar is set relative to the metric\'s shape, not a fixed high bar':
    ['running maximum', 'relative to the metric'],
  'forecasters always record both branches when the rule counts distinct forecasters':
    ['both branches', 'distinct forecasters'],
  'the owner\'s current value is re-filed inside each clock-settled cell before it closes':
    ['re-file', 'inside each'],
  'large media never goes into git':
    ['large media', 'git'],
}
fails = [name for name, needles in rules.items() if not all(n in low for n in needles)]
for name in fails:
    print('FAIL: telarchy-loop does not state:', name)
if fails: sys.exit(1)
print(f'PASS: telarchy-loop states all {len(rules)} rules')
PY
