#!/usr/bin/env bash
# The owner-facing skills state the setup rules the hackathon-game loop
# (2026-09-27/28) paid for by missing them.
#
# The metric was person-rated and settled on a clock, so every book settled on
# a placeholder 0 fifty minutes before the first rating landed; the curve plus
# custom dates opened five books where one was wanted; mutually exclusive
# choices went up as nine binary proposals; a retried post created a duplicate.
# Each check is one rule, looked for in the words the skill must use.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$ROOT/plugins/telarchy/skills" <<'PY'
import sys, os
d = sys.argv[1]
def low(name):
    return ' '.join(open(os.path.join(d, name, 'SKILL.md')).read().lower().split())
rules = [
  ('telarchy-metric-design', 'settlement is chosen: a person-reported metric gets manual settlement and N/A until measured',
     ['person-reported', 'until-settled', 'resolvesnauntilmeasured', 'machine']),
  ('telarchy-metric-design', 'one horizon by default; curve plus custom dates stacks markets',
     ['one horizon', '"enabled": false', 'customhorizons', 'stacks']),
  ('telarchy-manage', 'settlement is chosen: a person-reported metric gets manual settlement and N/A until measured',
     ['person-reported', 'until-settled', 'resolvesnauntilmeasured']),
  ('telarchy-manage', 'one horizon by default; curve plus custom dates stacks markets',
     ['one horizon', 'customhorizons', 'stacks']),
  ('telarchy-evaluate', 'mutually exclusive options are one multiple-choice proposal, decided with approve {option}',
     ['mutually exclusive', 'one proposal', 'options', '{ "option"']),
  ('telarchy-evaluate', 'a retried proposal post sends the same Idempotency-Key',
     ['idempotency-key', 'retry']),
  ('telarchy-propose', 'mutually exclusive options are one multiple-choice proposal, decided with approve {option}',
     ['mutually exclusive', 'one proposal', 'options', '{ "option"']),
  ('telarchy-propose', 'a retried proposal post sends the same Idempotency-Key',
     ['idempotency-key', 'retry']),
  # Seasons have no claim step (telarchy-app docs/seasons.md, "Payment",
  # 2026-10-02): a winner is paid to the payout method on the account and
  # has 30 days from settlement to add one.
  ('telarchy-trading', 'season winners do nothing to be paid: payout method on the account, 30 days to add one',
     ['nothing to be paid', 'payoutmethod', 'payby', '30 days']),
  ('telarchy-trading', "a bot without a payout method of its own is paid to its owner's (2026-10-03)",
     ["paid to its owner's"]),
  # The connector (telarchy-app docs/connector.md, 2026-10): a chat that has
  # the Telarchy tools already acts as the person, so the index says so and
  # never sends that agent off to mint a key.
  ('telarchy', 'the connector at /mcp acts as the person; with its tools, use them and ask for no key',
     ['telarchy.com/mcp', 'acts as the person', 'no key', 'asks first']),
]
fails = [f'{s} does not state: {r}' for s, r, n in rules if not all(x in low(s) for x in n)]
# The retired claim step must not be taught anywhere.
for s in sorted(os.listdir(d)):
    f = os.path.join(d, s, 'SKILL.md')
    if os.path.exists(f) and ('/claim' in low(s) and 'seasons' in low(s) and '/api/seasons/:id/claim' in low(s)
                              or 'claim your prize' in low(s) or 'claim a prize' in low(s)):
        fails.append(f'{s} still teaches claiming a season prize')
for f in fails: print('FAIL:', f)
if fails: sys.exit(1)
print(f'PASS: {len(rules)} setup rules stated, no prize claim taught')
PY
