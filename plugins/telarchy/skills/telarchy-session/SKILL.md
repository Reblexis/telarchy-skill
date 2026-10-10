---
name: telarchy-session
version: 0.39.3
description: |
  Run an attended Telarchy (telarchy.com) working session, invoked as
  /telarchy-session: the user first names the few metrics they want to
  improve in this session; the session finds them on the user's
  workspaces or, when they exist nowhere, opens a new workspace holding
  them; it fixes the user's preferences (weights between the metrics,
  budget, what is off limits, when the effect must show), then in rounds
  finds the highest-return actions for those metrics, posts the ones the
  user picks as proposals, has the markets price them, and leaves each
  decision to the user on its price. A continuation proposal each round
  has the market price stopping now versus continuing, shown in aoe; a
  hook can start it attached to any new aoe session.
  Use it for "/telarchy-session",
  "start a Telarchy session", "let's work on my metrics", "find the best
  moves for <metric> and put them up", or "help me improve <metric> with
  Telarchy" when the user is present. For unattended work while the user
  is away, use telarchy-loop.
allowed-tools:
  - Bash
  - WebFetch
  - WebSearch
  - Read
---

# A Telarchy working session

A session is a sitting with the user present: **their metrics, the best actions for them, priced, decided by them.** It is the attended counterpart of **telarchy-loop**, and it is built from the other skills rather than repeating them. Load each when its step comes:

- **telarchy-metric-design**: choosing and writing new metrics.
- **telarchy-manage**: opening a workspace, putting metrics on, funding books, deciding proposals.
- **telarchy-propose**: researching and ranking candidate actions by return.
- **telarchy-evaluate**: writing a proposal the market can price, posting it, reading the price.
- **telarchy-trading**: identities and keys, and any trade the user wants on the record.

Base URL `https://telarchy.com/api`; `GET /api/help?section=<segment>` is the contract and wins over this file. Report friction with `POST /api/feedback`.

**The user decides everything that is public or spends their credits**, in its exact form: a new workspace and its metrics, every proposal posted, every credit spent on seeding or forecasters, every approve and decline. Reading, research and drafting need no permission.

## 1. The session opens with the user's metrics

Before any call, the user names the metrics they want to improve in this session: two or three numbers, rarely more. Ask for them in one short question if the request did not already say ("which numbers do you want to move this session?"), and take their words as given. Each named metric is one of:

- **Already on a workspace.** Find it: `GET /api/workspaces` with their key lists the floors the key belongs to (with `memberRole`), and `GET /api/metrics` with `X-Workspace-Id` lists each floor's metrics. Match **by definition, not by name**: "revenue" on the floor may be gross where the user means net, and a near miss priced for a month is worse than a new metric. Show the match in one line ("Monthly revenue (EUR) on Acme: net revenue recognised in the month, read from Stripe on the 1st") and go on unless they object.
- **New.** No floor holds it. It goes on a **new workspace**: design it with telarchy-metric-design (one horizon, a settlement that matches who produces the reading), show the user the exact set, and on their yes open the floor (`POST /api/workspaces`) and put the metrics on with telarchy-manage (sections 2 to 4). An account holds three workspaces; at the cap, say so and ask which floor to use instead.

**A proposal is priced on one floor only**, against that floor's metrics. So the session runs on one floor. When some of the named metrics are found and some are new, ask one question: add the new ones to the floor that holds the others (only if the user manages it), or open a new workspace holding all of them. When they sit on two existing floors, ask which floor this session is about, or whether to run one session per floor.

The session's metrics are the ones the user named. The floor's other metrics stay priced (every proposal opens books on them too), but they do not steer the ranking unless the user says so.

## 2. The user's preferences

Fix these in one block, inferring what the context already says and asking only for the rest:

- **Weights**: how the chosen metrics trade off against each other ("a point of retention is worth 500 EUR of revenue to me", or a plain ranking). With one metric there is nothing to weigh.
- **Budget**: credits a round may spend on seeding proposals (and on forecasters, section 4), read against `GET /api/agents/me/balance`; the continuation seed, the credits a round puts behind its continuation proposal (section 5); plus any money or time the actions themselves may cost.
- **Off limits**: actions the user will not take (paid ads, anything public under their name, hiring, touching production), and who carries out an approved action.
- **When the effect must show**: the date by which an action has to move the number to count. It picks which books matter.

Restate the block; it is the yardstick for everything after. When the user changes a preference mid-session, restate the new block and re-rank.

## 3. Check the floor can price anything

A proposal on a floor that cannot trade opens books nobody can move. Check, with `GET /api/marketplace/<idOrSlug>` and `GET /api/setup/checklist?workspaceId=<id>`:

- **Open, funded books on each chosen metric** whose `periodEndsOn` falls after a sensible deadline and covers the effect date. Only those books get a pair. Missing or empty: fix it with telarchy-manage (add the date, fund the book) on the user's yes.
- **The floor trades.** A new workspace starts unlisted. A floor that is not public trades only for the participants its groups grant `trade` (the owner, admins, the Trader group); anyone else gets 403 `not_authorized`. So either the owner publishes it, on telarchy.com (the Share control beside the floor's name), or adds the forecasters who should price it to the Trader group. A floor that trades while not public never counts toward a prize season or a public board, even once published (`tradedPrivatelyAt` on the floor payload): say so before its first private trade, and publish first if the floor should count.
- **Who will price.** Look at who trades here (recent trades in the brief, `GET /api/marketplace/<idOrSlug>/context?format=md`). A floor with no traders prices nothing by the deadline; section 4 says what to do about it.

## 4. Rounds: rank, pick, post, price, decide

**Rank.** Run telarchy-propose sections 1 to 5 against the session's metrics: research the floor and the subject, break each metric into drivers, generate candidates, cut, and estimate each one's expected change per metric inside the effect window, and its cost. Score each candidate by its return **weighted** by the user's preferences: the weighted sum of expected gains over its cost, dropping anything off limits or over budget. Show the arithmetic in one line per candidate.

**Pick.** Present a ranked shortlist of three to five, each with its expected gain per metric, cost and one line of why, plus what the research could not establish. Say first if one action is so cheap and clearly right that a price cannot change the decision: recommend just doing it. The user picks which go up; they may edit, merge or reject any. Mutually exclusive picks are one proposal with options (telarchy-evaluate, section 4).

**Post.** Draft each pick with telarchy-evaluate (sections 4 to 6): bounded, with a `decideBy` that leaves traders days rather than minutes, and seed only the books on the session's metrics and dates. Show the user the exact title, description, deadline, books and total cost, and post only on their yes, with one `Idempotency-Key` per proposal reused on any retry. Report each link.

**Price.** The markets price each proposal against the floor's metrics; the session waits for them and reads the result back per chosen metric and date: the delta, its depth and how many traded it. Read it honestly:

- Right after posting every delta is 0: **nobody has priced it yet**, not "no impact". Say when to look again.
- Your own estimate from the ranking is a **prior**, never the market's view, and it is never presented as one.
- If nobody will price before the deadline, offer the user the ways out, each on their yes because each spends or publishes: they share the floor with people who trade; they put their own view on the record (telarchy-trading, section 7); or the session funds a few forecasters, each its own identity created with `initialCredits` and never the key that drafted the proposals, built as telarchy-loop's forecasters are. A delta priced only by the session's own forecasters is labeled that way in every report.

**Decide.** The user decides each proposal on its price. Recommend with the numbers (the weighted delta against the cost, the depth behind it, the deadline), and then the user decides: approve, choose an option, or decline with a reason, carried out with telarchy-manage (section 5) on their exact word. **The session never approves or declines on its own**, and never treats a lapse as a decision without saying so: a proposal undecided at `decideBy` lapses and refunds.

Then the next round: the decided and pending proposals, and what the floor said about them, inform the next ranking. One round with two well-chosen proposals beats five thin ones; whether another round runs is the user's word on the continuation proposal (section 5).

## 5. Stop now or continue: the continuation market

The session is itself an action: another round costs the user's time and credits, and it may or may not move the numbers. So every round keeps **one open continuation proposal** on the session's floor, and its price is the session's prediction of what happens if it stops now versus continues.

- **The proposal.** Post it alongside the round's picks, titled "Continue this session: round <N+1>", with the next round's plan in two or three lines as its description (what will be researched, posted or built, and how long it takes), `decideBy` at the planned end of the current round, and books seeded only on the session's metrics and dates. Approved means the session continues with that plan; declined means it stopped now. So per metric and date the approved price is "continued", the declined price is "stopped now", and the delta is what one more round is worth. Post it with telarchy-evaluate like any proposal, with its own `Idempotency-Key`.
- **Consent.** The continuation seed is part of the budget (section 2). Show the first continuation proposal in its exact form; the user's yes to it covers the later rounds' continuation proposals of the same form and seed. A change of either asks again.
- **Only the market prices it.** The prediction is only the market's price, never the agent's estimate, and nothing else is ever shown as it. Until someone trades it reads **unpriced**, not "no difference". The session never trades the continuation market, with its own key or through forecasters it funds: an agent that wants to keep running is the last one who should price whether it should. The user and anyone else on the floor may trade it. On a floor nobody else can trade yet (not public, and no forecasters in its Trader group), say plainly that the prediction stays unpriced until it does.
- **Deciding it.** The user's word to continue or stop is the decision on the continuation proposal. At each round's end, before asking whether to go on, read its price and give one line per metric: stopped now against continued, the delta, its depth and how many traded; recommend from the weighted delta against the round's cost. On "continue", approve it (telarchy-manage, section 5) and run the next round; on "stop", decline it with the reason "session stopped" and close (section 6). One that lapses at `decideBy` refunds; if the session goes on, post a fresh one.
- **Shown in aoe.** When `$AOE_INSTANCE_ID` is set the session runs inside aoe (Agent of Empires): after posting the continuation proposal and every time it reads its price, write the card with `aoe session forecast set` (JSON on stdin; the contract is aoe's `docs/guides/session-forecast.md`): `verdict` is `continue` when the weighted delta is above zero, `stop` when below, `unpriced` while nobody has traded; `headline` is the weighted delta in at most 32 characters ("+150 EUR revenue"); one `metrics` row per session metric and date with `stopped` (the declined price), `continued` (the approved price), `unit`, `traders` and `depth`; `note` is the next round's plan; `source` the proposal's link; `decide_by` its deadline. Without `$AOE_INSTANCE_ID`, skip it; if the command fails, say so once and go on. On close, write the final card (`stop`, headline "session stopped").
- **Forecast overview after every reply.** While the session is running (or tied, section 7), every reply ends with a forecast overview of at most four lines, from prices re-read in that turn: the continuation proposal per metric (stopped now against continued, the delta, depth and traders, or "unpriced"), then each other open session proposal's delta in one line, with its `decideBy`. Before the first continuation proposal exists, say "no continuation proposal yet" in one line. Refresh the aoe card in the same turn, so the band never shows an older price than the reply.

## 6. Close the session

End when the user says so, or when the budget for the session is spent. Report in a few lines:

- the session's metrics and preferences;
- what was posted, with links, and each one's priced delta on the chosen metrics and its depth;
- what was decided, and how;
- the last continuation price: per metric, stopped now against continued, and its depth;
- **what still waits**: open proposals with their `decideBy`, books still unpriced, readings the user owes the metrics, and anything approved that someone must now carry out;
- credits spent this session.

If the user wants the work to go on without them, offer telarchy-loop: it takes this session's floor, metrics and preferences as its mandate.

## 7. Attached to an aoe session

The session can also start **attached** to another task: a hook runs this skill after the first prompt of every new aoe session, whatever that prompt asks. Attached, the session does not take over the task. The agent does what the user asked; this skill only ties the session to a workspace and, once tied, keeps the continuation market (section 5) and the forecast overview going beside the work.

**Ties log.** Ties are remembered in a ties log, one JSON line per session, at `$TELARCHY_SESSION_TIES` (default `~/.config/telarchy/session-ties.jsonl`): `{"at", "aoe_instance_id", "cwd", "title", "prompt" (its first 200 characters), "guess", "workspace" (slug, or null), "answered" (true when the user answered the tie question), "metrics", "weights", "continuation_seed"}`. The last line for an `aoe_instance_id` is its tie.

**The guess.** Guess from what the work is about. Work on a floor's own subject belongs to that floor: building or fixing Telarchy itself is the `telarchy` floor, work on a company or a game is the floor that company or game runs on, work on the user's own life is their personal floor. So match the repo, working directory, aoe title (`aoe session show "$AOE_INSTANCE_ID"`) and prompt against the user's workspaces' names, descriptions and metrics (`GET /api/workspaces`, `GET /api/metrics`), and use past ties in the ties log for what the user answered before: only answered ties (`"answered": true`) are evidence, the same repo or directory first. None is never the default: guess none only when the work has nothing to do with any of the user's floors, never because earlier ties in the log read null.

**Always confirm.** The session always asks the user which workspace this session is tied to, even when the guess looks certain: one line at the end of the first reply, with the guess first and its metrics, the next one or two candidates, and "none". If the guess is a floor, the same line carries the continuation seed (the last one used on that floor, else a small default) so a yes covers it. The question never blocks the task: the agent answers the user's prompt first, and nothing is posted until the tie is confirmed. Record the answer in the ties log next to the guess with `"answered": true`, "none" included, so a wrong guess teaches the next one. A prompt that does not answer is recorded with `"workspace": null`, `"answered": false` and `"guess"` kept, never as none: it says nothing about where the session belongs, and the session does not ask again; the user can tie it later by saying so.

**Tied.** The session's metrics are the floor's metrics, or the ones the user names in the answer; weights and the continuation seed come from the answer or the floor's last tie, restated in one line. A round is a finished chunk of the user's task: at the end of each, the continuation proposal for the next chunk is posted or read (section 5), and the user's word to continue or stop decides it. Ranking new actions (section 4) runs only when the user asks for it.
