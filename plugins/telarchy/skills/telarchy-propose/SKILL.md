---
name: telarchy-propose
version: 0.33.0
description: |
  Find and draft the highest-return proposal for a Telarchy (telarchy.com)
  workspace: read the floor's metrics, definitions, readings, ballot, past
  decisions, charter and documents, research everything else about the
  subject the agent can browse (the product, its site, repo, store page,
  reviews, public data, the local project), break the target metric into
  its drivers, generate candidate actions, estimate each one's impact on
  the target metrics against its cost, rank by return, and draft the best
  as a well-formed proposal with its reasoning and the runners-up, posted
  only on the user's yes. Use it whenever the user asks "what should we
  do next", "what should I propose", "find the best proposal", "highest
  ROI move for <floor>", "suggest proposals for my workspace", "make a
  proposal that raises <metric>", or wants to earn by proposing paid work
  on someone else's floor. To price an idea the user already has, use
  telarchy-evaluate.
allowed-tools:
  - Bash
  - WebFetch
  - WebSearch
  - Read
---

# Proposing the highest-return action

A proposal on Telarchy is an action someone offers to take. The market prices where each of the floor's metrics lands if the owner approves and if they decline, and the gap is the action's value. Your job here is to find the action whose gap is largest for what it costs, before anyone has priced it: do the research a good forecaster would do, then propose the thing that research says is worth most.

Base URL `https://telarchy.com/api`; `GET /api/help?section=proposals` is the contract. The proposer's guide is `GET /api/guides/get-paid`. Posting mechanics, the rules for writing a proposal the market can price, and the confirmation step are the same as **telarchy-evaluate** (sections 3 to 6); load it before drafting.

**Posting is public and can spend the user's credits, so nothing is posted without their yes on the exact draft.** Research and drafting need no permission.

## 1. Fix the target

- **The floor.** The user names it, or it is the one floor their key belongs to (`GET /api/workspaces` with their key). If several fit, ask.
- **The metrics.** The ones the user named, or else all of the floor's priced metrics, weighted by what the owner says matters: the charter, the order of the metrics, the lead (headline) metric, announcements. On a floor whose charter names one number the owner decides on, that number dominates.
- **The dates.** Only books whose period ends after a sensible deadline get a pair (`markets[]` rows of `GET /api/marketplace/<idOrSlug>`, `periodEndsOn`), so the action's effect has to land inside one of them. An action whose payoff comes after the furthest priced date is worth nothing to this market, however good it is; if the floor's dates are all too short for the best action, say so and suggest the owner add one (telarchy-manage).
- **Whose return.** Proposing to the user's own floor, the return is the owner's: metric gain per unit of cost. Proposing paid work to someone else's floor, the user also names an ask (`askUsd`), which is part of the cost, and on a money metric named "net" the approved branch opens lower by it; the proposal is worth posting only if the gain clears the ask.

## 2. Research: read everything that could change the ranking

On the floor, most of it needs no key on a public floor:

- The brief, `GET /api/marketplace/<idOrSlug>/context?format=md`: every metric's definition (the settlement text, read it exactly), readings, open books and prices, every proposal with its priced impact, announcements, published documents.
- Each target metric's history (`GET /api/metrics/<id>/logs`) and what the owner wrote when it moved (`GET /api/predictions/markets/<id>/context`, the update notes).
- The ballot and the record: `GET /api/proposals?status=pending`, and the decided ones (`?status=approved`, `?status=declined` with decline reasons, delivery states). Decline reasons are the owner telling you what they will not do; approved ones show what they will.
- `GET /api/data-room/actions?workspace=<slug>` (what has been happening), and on Telarchy's own floor `GET /api/data-room/planned` (what the owner already committed to: do not propose it again).

Off the floor, whatever the agent can reach about the subject: the product itself, its website and pricing page, its store page and reviews, its public repo and issues, its social accounts, competitors, public statistics about its market, and the local project if you are running inside it. Cite what you use; forecasters will check it.

Stop researching when another hour would not change which action ranks first.

## 3. Break the metric into its drivers

Write the target metric as a product (or sum) of things you can measure, with current values: revenue = visitors x conversion x price x retention, or whatever fits this subject. Put a number on each from the research. The driver furthest below where it could plausibly be, and cheapest to move, is where an action has leverage. A proposal aimed at a driver that is already near its ceiling moves nothing.

If the floor has several target metrics, note which drivers they share: an action that moves a shared driver scores on all of them.

## 4. Generate candidates, then cut

Write 10 to 20 candidate actions across the drivers, including cheap ones, unglamorous ones, and ones nobody on the ballot has thought of. Then cut any that:

- is an outcome rather than an action ("reach $10k MRR"), or cannot be bounded by time, money, count or a discrete act;
- duplicates a pending proposal or something the owner already planned;
- was declined before, unless you can show the decline reason no longer holds;
- breaks the charter or needs a party nobody controls;
- moves the number without the goal behind it (gaming the metric's definition, buying a count, shifting revenue between periods). The market may even pay for it; the owner should not, and proposing it costs the user their standing on the floor.

## 5. Estimate each one's return

For every survivor, per target metric and priced date:

- **Mechanism**: which driver it moves, by how much if it works, and the evidence (a base rate, a comparable case, the subject's own history).
- **Probability it works**, and **when the effect shows up**: an effect landing after the priced date counts zero on that date.
- **Expected change** = size x probability, in the metric's own units, inside the window.
- **Cost**: money, the ask, the owner's time, anything it consumes, and the credits to seed its books.
- **Side effects** on the other metrics, positive or negative.

Return = expected, weighted metric gain / total cost. Show the arithmetic in a line per candidate so the user (and later the forecasters) can argue with a specific number. Say how confident you are; an estimate with an honest wide range beats a precise guess.

If the top action is so clearly worth it and so cheap that no price could change the decision (a free promotion slot about to close, a broken checkout), say so first and recommend just doing it; a market adds nothing to a decision that is already obvious, and it may have a deadline sooner than any proposal can be priced. Then draft the best action that genuinely needs a price.

Compare the top gains with the metric's own noise (how much it moves week to week with nobody doing anything). A gain far inside the noise will price as nothing, however sensible the action.

## 6. Draft the winner

Take the top candidate and write it the way telarchy-evaluate says: bounded, ideally one where approval itself is the action, a title of at most 80 characters, and a description written for a stranger that carries your mechanism, evidence and estimate, since that is what forecasters price. If the top two or three are mutually exclusive ways of doing one thing, make them one proposal with `options` so the owner chooses between priced alternatives. Pick `decideBy` long enough for traders to see it (days, not hours) and before the dates the effect lands on, and seed only the books where the effect lands (`liquidity: [{ metricId, targetDate, amount }]`).

## 7. Present, then post on a yes

Give the user, briefly:

- the drafted proposal (title, description, deadline, which books get how much, total cost, ask if any);
- why it ranks first, in one or two lines with its expected gain and cost;
- the runners-up, one line each with their numbers, and what was cut and why when it matters;
- what the research could not establish.

Post only on their yes, following telarchy-evaluate section 6, then report the link and read the market back honestly: a fresh pair reads 0 because nobody has priced it, not because it is worthless. Your estimate is a prior; once people trade, the market's number replaces it, and it is never presented as the market's view. If the user wants to put their own credits behind the estimate, that is trading (telarchy-trading, section 7), on their word.

One well-researched proposal beats several thin ones: every proposal costs the owner attention and the proposer credits, and a floor can charge a spam penalty. Post more than one only when the user asks for it.
