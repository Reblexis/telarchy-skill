#!/usr/bin/env bash
# telarchy-session states the rules it exists to enforce.
#
# The session is the attended counterpart of telarchy-loop (README.md,
# "telarchy-session", from Viktor's ask of 2026-10-05): the user names the
# metrics first, the session finds or opens the floor that holds them, ranks
# the highest-return actions by the user's preferences, posts the ones the
# user picks, and the user decides each one on its price. A skill that drops
# one of these teaches every agent that loads it to drop it too. Each check is
# one rule, looked for in the words the skill must use.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$ROOT/plugins/telarchy/skills/telarchy-session/SKILL.md" <<'PY'
import re, sys
p = sys.argv[1]
try:
    t = open(p).read()
except FileNotFoundError:
    print(f'FAIL: {p} does not exist'); sys.exit(1)
m = re.match(r'^---\n(.*?)\n---\n', t, re.S)
desc = ' '.join(m.group(1).lower().split()) if m else ''
low = ' '.join(t.lower().split())
rules = [
  ('it is invoked as /telarchy-session, and its description says so',
     desc, ['/telarchy-session']),
  ('it is the attended counterpart of telarchy-loop, which takes over when the user leaves',
     low, ['attended', 'telarchy-loop']),
  ('the session opens with the user naming the metrics to improve in this session, before any call',
     low, ['opens', 'names the metrics', 'this session', 'before any call']),
  ('metrics already on a workspace make it the floor, matched by definition, not by name',
     low, ['get /api/workspaces', 'by definition, not by name']),
  ('metrics on no workspace become a new workspace, designed and opened by the owning skills on a yes',
     low, ['new workspace', 'post /api/workspaces', 'telarchy-metric-design', 'telarchy-manage']),
  ('a proposal is priced on one floor only, so a mix of found and new metrics is one question',
     low, ['one floor', 'one question']),
  ("the user's preferences are fixed: weights, budget, what is off limits, when the effect must show",
     low, ['weights', 'budget', 'off limits']),
  ('the floor must be able to price: funded books covering the effect, and a floor that trades',
     low, ['funded', 'periodendson', 'not_authorized', 'publish', 'trader group']),
  ("candidates are ranked by return weighted by the user's preferences, through telarchy-propose",
     low, ['telarchy-propose', 'weighted', 'return']),
  ('the user picks from a ranked shortlist',
     low, ['shortlist', 'the user picks']),
  ('nothing is posted without the user\'s yes to the exact draft, posted through telarchy-evaluate with an Idempotency-Key',
     low, ['telarchy-evaluate', 'exact', 'idempotency-key']),
  ("prices are read honestly: a fresh 0 is unpriced, the agent's estimate is a prior",
     low, ['nobody has priced it yet', 'prior', "never the market's view"]),
  ('the user decides each proposal on its price; the agent never approves or declines on its own',
     low, ['the user decides', 'never approves or declines']),
  ('the session ends with what was posted, priced and decided, and what still waits',
     low, ['what still waits']),
  # The continuation market (Viktor's ask of 2026-10-06): the session keeps a
  # market-priced prediction of what happens if it stops now versus continues,
  # so the user can tell whether more work is worth it.
  ('every round the session keeps one open proposal pricing its own continuation, approved meaning continued and declined meaning stopped now',
     low, ['continuation proposal', 'continue this session', 'approved means', 'declined means', 'stopped now']),
  ("the stop-or-continue prediction is the market's price only, never the agent's estimate, and reads unpriced until someone trades",
     low, ['only the market', 'unpriced']),
  ('the session never trades its own continuation market, with its own key or through forecasters it funds',
     low, ['never trades the continuation', 'forecasters it funds']),
  ("the user's word to continue or stop is the decision on the continuation proposal",
     low, ["word to continue or stop is the decision"]),
  ('the continuation proposal costs credits, so its per-round seed is part of the budget the user agrees to',
     low, ['continuation seed']),
  ('the prediction is shown in aoe when the session runs inside one',
     low, ['aoe session forecast set', '$aoe_instance_id']),
  ('the closing report includes the last stop-or-continue price',
     low, ['last continuation price']),
  # Attached to an aoe session (Viktor's ask of 2026-10-06): a hook starts the
  # skill after the first prompt of every new aoe session; it learns which
  # sessions belong to which workspace, and always asks him to confirm.
  ('started alongside another task, the session ties itself to a workspace and does not take over the task',
     low, ['attached', 'does not take over']),
  ('ties are remembered in a ties log, one line per session, and past ties inform the guess',
     low, ['ties log', '$telarchy_session_ties', 'past ties']),
  ('the tie is always confirmed by the user, even when the guess looks certain, and none is an answer',
     low, ['always asks', 'even when the guess looks certain', '"none"']),
  ('the tie question never blocks the task: asked at the end of the reply, nothing is posted until confirmed',
     low, ['never blocks', 'nothing is posted until']),
  ('the answer is recorded with the guess, so wrong guesses teach the next one',
     low, ['record the answer', 'guess']),
  # The guess is not none by default (Viktor, 2026-10-09: "ofc its tied to that
  # worksapce.. why woul dyou keep guessing none"): work on a floor's own subject
  # belongs to that floor, and a question nobody answered teaches nothing.
  ("the guess comes from what the work is about: work on a floor's own subject is tied to that floor, and none is never the default",
     low, ["floor's own subject", 'none is never the default']),
  ('an unanswered tie question is recorded as unanswered, never as none, and only answered ties inform the guess',
     low, ['"answered": false', 'never as none', 'only answered ties']),
  ('after every reply a tied session ends with a current overview of the forecasts and refreshes the aoe card',
     low, ['forecast overview', 'every reply', 'refresh']),
]
fails = [r for r, text, need in rules if not all(x in text for x in need)]
for r in fails: print('FAIL: telarchy-session does not state:', r)
if fails: sys.exit(1)
print(f'PASS: {len(rules)} session rules stated')
PY
