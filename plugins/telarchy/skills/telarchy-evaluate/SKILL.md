---
name: telarchy-evaluate
version: 0.32.0
description: |
  Take an idea, plan or decision and get it priced on Telarchy
  (telarchy.com): find the workspace whose metrics it would move (the
  user's own floors first), check nobody already proposed it, rewrite it as
  a well-formed proposal (bounded, and where possible one that approval
  itself carries out), fund the books the argument is about, post it once
  the user has seen the exact text and cost, and report the priced impact
  per metric, the link and the deadline. If no workspace fits, ask whether
  to create one and hand over to telarchy-manage and
  telarchy-metric-design. Use it whenever the user says "evaluate this",
  "put this on Telarchy", "what would the market say about X", "should I do
  X", "propose X", "price this idea", or wants a decision, experiment, hire,
  spend or feature judged against their metrics, even if they do not name
  Telarchy's proposal flow.
allowed-tools:
  - Bash
  - WebFetch
  - Read
---

# Evaluating an idea on Telarchy

On Telarchy an idea is evaluated by posting it as a **proposal**. Every open market on the workspace then gets a twin pair per metric and date: where the number lands **if the owner approves**, and where it lands **if they decline**. People with credits at stake price both, and the gap (`delta = approved - declined`) is the market's estimate of what the idea is worth, per metric, per date. Your job is to get the idea onto the right floor in a form the market can price, then read the answer back honestly.

Base URL `https://telarchy.com/api`. The live guides are `GET /api/guides/get-paid` (the proposer's side) and `GET /api/guides/proposals` (what the numbers mean); `GET /api/help?section=proposals` is the contract. Report anything broken with `POST /api/feedback`.

**Posting is public and can spend the user's credits.** Show them the exact title, description, workspace, deadline and total cost, and post only on their yes. Anything else you do before that (reading, drafting) needs no permission.

## 1. Pin down the idea

Get from the user, or infer from context, and restate in one or two lines:

- **The action**: what exactly will be done, by whom, by when, at what cost.
- **The outcome they hope for**: which of their numbers it should move. This tells you which workspace and which books matter.
- **Who decides**: an idea for the user's own project goes to their floor, where they decide. An idea offered to someone else's company goes to that company's public floor, where its owner decides (and may pay for it, with `askUsd`).

If the user gave you only an outcome ("reach $1M ARR", "grow the community"), that is a metric, not a proposal: ask what they would actually do to get there, or offer two or three concrete actions to choose from.

## 2. Find the workspace

You need an identity to post. Use the user's key (`X-Agent-Key`, with `workspace:trade`; see telarchy-trading, section 2, to get one). Then:

```bash
curl -s https://telarchy.com/api/workspaces -H "X-Agent-Key: $KEY"   # the floors this key belongs to, with memberRole
curl -s "https://telarchy.com/api/marketplace/<idOrSlug>/context?format=md"   # a floor's brief: metrics, definitions, open books, pending proposals
```

Read each candidate's metrics (the brief, or `GET /api/metrics` with `X-Workspace-Id`) and pick the floor whose metrics the idea would actually move, by definition, not by name. For an idea about someone else's company, find their public floor in `GET /api/marketplace/workspaces/public`.

- **One fits**: say which and why in one line, and go on.
- **Several fit**: ask the user which, naming the metric each would be judged on.
- **None fits**, or the user has no workspace: say so plainly, and ask whether they want a workspace for it. On a yes, set it up with **telarchy-manage** (the account and workspace) and **telarchy-metric-design** (what to measure: the metrics must be the outcomes this idea is meant to move, not the idea's own activity). Fund its books, then come back here. On a no, stop: there is nothing for a market to price against.

A floor with metrics but no open, funded books cannot price anything either. Check `GET /api/marketplace/<idOrSlug>`: its `markets[]` rows are the books a proposal will be priced on.

## 3. Check it can go up, and is not already there

- `externalProposalsDisabled: true` on `GET /api/marketplace/<idOrSlug>` means only the owner and admins post there (403 `external_proposals_disabled`). If the user is not one, tell them; do not retry.
- Read the ballot: `GET /api/proposals?status=pending` (with `X-Workspace-Id`), and skim recently decided ones (`?status=approved`, `?status=declined`, with their decline reasons). If the same idea is pending, report its current price instead of posting a duplicate. If it was declined, read why: the reason may kill the idea or tell you how to reshape it.
- A floor may cap pending proposals per participant (429 with `{ pending, cap }`).

## 4. Write it so the market can price it

The market's job is to price the **outcome**. Every doubt about whether the action will even happen is doubt the market must also price, and nobody can separate the two afterwards. So:

**Bound it** by time, money, count, or a discrete act, and make it something the decider could commit to regardless of how it turns out:

| Not this | This |
|---|---|
| Hire 2 sales reps | Run a 2-week sourcing sprint and interview 10 candidates |
| Improve onboarding | Spend 20 engineering hours rewriting the onboarding flow |
| Grow through paid acquisition | Spend $5,000 on one named channel over 30 days |
| Reach $1M ARR | (a metric, not a proposal) |

**Better, make approval the action itself**, so nothing stands between the button and the world and the declined branch is a real counterfactual: "Assign the onboarding rewrite as this sprint's committed work", "Wire $5,000 to the named channel for a 30-day campaign", "Release the new pricing page to production". Where no mechanism makes approval self-executing, propose the commitment: "Commit to X by <date>".

**Title** at most 80 characters, the action in plain words (a paid job leads with its price by convention: `$400: rewrite the store page`). **Description** at most 10,000 characters, written for a stranger who will not ask a follow-up question: what will be done, what changes when it is done, how anyone can tell, and the evidence behind the expectation. That description is what forecasters price.

Several mutually exclusive variants of one decision ("which of these three pricing pages") are **one proposal with `options`** (`[{ id, label }]`, ids `^[a-z0-9-]{1,24}$`, labels at most 40 characters), not several proposals: the owner then chooses one, and the books compare directly.

## 5. Deadline and money

- **`decideBy`** (an ISO instant) is when the owner must decide. It defaults to the floor's `decisionMinutes` (one day) and **can never be moved** after posting. A market needs people to see it, so a proposal due in minutes is decided on its opening seed, which is nothing. Give an idea that needs real pricing days, not hours. Only books whose date settles after `decideBy` get a pair.
- **Seed the books, or there is no price.** A proposal is the proposer's to fund: with no seed its books open empty and the floor says "no price yet" (unless the owner set a per-date `proposalOpensWith`, read from `markets[]`). Fund only the books the argument is about with `liquidity: [{ metricId, targetDate, amount }]`: `amount` goes into each branch of that metric and date, so the bill is `amount x 2` per book (x the option count on an option proposal). `liquiditySubsidy` instead puts the same amount into every book, which is often many more than expected. Pick books whose `proposalOpensWith` is not null and whose `periodEndsOn` is after your `decideBy`. Payment comes from liquidity credits first, trading credits second, and trading credits in a pool count against the user's profit and season score until they come back. A few hundred credits on the one or two books that matter reads far better than a thin spread over twenty.
- **`askUsd`** only when the user wants to be paid for doing the work on someone else's floor. It needs payout details on the account (`POST /api/auth/profile { payoutMethod }`) or `payoutHandle` in the body, and on a floor whose money metric says "net", the approved branch opens lower by the ask. Approval makes the ask owed.

## 6. Confirm, post, read the answer

Show the user the final draft: floor, title, description, options if any, `decideBy`, which books get how much, total cost, ask. On their yes:

```bash
curl -s -X POST https://telarchy.com/api/proposals \
  -H "X-Agent-Key: $KEY" -H "X-Workspace-Id: $WS" -H "Content-Type: application/json" \
  -d '{"title":"Spend $5,000 on one named channel over 30 days","description":"...",
       "decideBy":"2026-10-02T18:00:00Z",
       "liquidity":[{"metricId":"<id>","targetDate":"2026-10","amount":150}]}'
# 201 { id, number, conditionalMarketIds, liquiditySubsidy, options }
curl -s "https://telarchy.com/api/proposals/<id>" -H "X-Workspace-Id: $WS"   # markets[]: approved, declined, delta, baselineConsensus
```

The proposal lives at `https://telarchy.com/<slug>/p/<number>`.

**Report back in a few lines:** the link, the deadline, and per metric and date the delta with how much sits behind it. Read it honestly:

- Both branches open at the same baseline, so right after posting the delta is 0 and means **nobody has priced it yet**, not "no impact". Say so, and say when to look again.
- A row with no trades is the opening seed. Never present it as the crowd's view.
- A delta on a thin book (little liquidity, one trader) is one person's opinion; name the depth beside the number.
- If the user wants their own estimate on the record, they can trade the branches (telarchy-trading, section 7) or file a forecast. Say which way their view points and what it would cost, and act only on their word.

Afterwards: talk to the owner on `GET/POST /api/proposals/<id>/messages`; fix wording with `PATCH /api/proposals/<id>` while pending (every edit is logged publicly; the ask re-anchors the books only while untraded; the deadline never changes); deepen your own books with `POST /api/predictions/markets/liquidity/bulk { proposalId, liquidity: [...] }`; pull it with `POST /api/proposals/<id>/withdraw` (everyone refunded). If the user owns the floor, deciding it is telarchy-manage, section 5.
