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
  # The approval market (telarchy-app docs/guides/approval-odds.md, 2026-10-18):
  # nothing reaches it unless the post names approvalLiquidity, an unfunded one
  # shows no chance anywhere, and a proposal with options has none.
  ('telarchy-evaluate', 'approvalLiquidity funds the approval market; nothing goes there unless named; not on options',
     ['approvalliquidity', 'approval market', 'unless you name it', 'no_approval_market']),
  ('telarchy-propose', 'a little approvalLiquidity gives the chance the owner approves a price',
     ['approvalliquidity', 'chance the owner approves']),
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
  # Owner setup over the API (telarchy-app docs/owner-on-the-floor.md, 2026-10-16):
  # the range defaults from the first value, a metric with neither a value nor
  # a range has no market, a new floor's half-credit book default prices
  # nothing, the first floor brings 10,000 liquidity credits, and an owner adds
  # forecasters through the Trader group.
  ('telarchy-metric-design', 'the range defaults from the first value (0..2v, -2|v|..2|v|, 0..1000) and an AI setup sets it itself',
     ['first value', '0 to 2v', '-2|v| to 2|v|', '0 to 1000', 'marketrangemin', 'never moves', 'set the range yourself']),
  ('telarchy-metric-design', 'no value and no range means no market until one arrives',
     ['neither a value nor a range', 'no market']),
  ('telarchy-manage', 'an AI setup sets its range itself rather than rely on the first-value default',
     ['first value', 'set the range yourself']),
  ('telarchy-manage', 'a new floor books open with half a credit, so a setup sends horizonCredits per date',
     ['0.5 credits', 'horizoncredits', '1,000']),
  ('telarchy-manage', 'the first floor an account creates brings 10,000 liquidity credits, once (liquidityGranted)',
     ['10,000', 'once per account', 'liquiditygranted']),
  ('telarchy-manage', 'an owner adds forecasters by putting their ids in the Trader group, keeping existing members',
     ['forecasters', 'trader group', 'keeping its existing members', 'claude-sonnet', 'claude-fable', 'reference-astra',
      'deepseek-pro', 'qwen-max', 'kimi-k3', 'glm', 'muse-spark', 'couple of minutes']),
  ('telarchy-manage', 'for now only official forecasters can be invited; anyone else is 403',
     ['only telarchy\'s official forecasters can be invited', '403', '"official": true', 'members/suggestions']),
]
fails = [f'{s} does not state: {r}' for s, r, n in rules if not all(x in low(s) for x in n)]
# The encoding reference carries the field defaults and the horizon syntax.
enc = ' '.join(open(os.path.join(d, 'telarchy-metric-design', 'references', 'encoding.md')).read().lower().split())
for r, n in [('rolling offsets include calendar quarters +Nq (+0q this quarter, +1q next)', ['`+nq`', '+0q', '+1q', 'last month']),
             ('the range defaults from the first value, not 1000', ['first value', '2v', '-2|v|', 'marketrangemin', 'no market'])]:
    if not all(x in enc for x in n): fails.append(f'encoding.md does not state: {r}')
if '| `marketrangemax` | `1000` |' in enc: fails.append('encoding.md still says marketRangeMax defaults to 1000')
if '| `value` | `0` |' in enc: fails.append('encoding.md still says value defaults to 0')
for s in sorted(os.listdir(d)):
    if os.path.exists(os.path.join(d, s, 'SKILL.md')) and 'books run from 0 to' in low(s):
        fails.append(f'{s} still says every book runs from 0')
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
