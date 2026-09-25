---
name: telarchy-manage
version: 0.32.0
description: |
  Run a Telarchy (telarchy.com) workspace as its owner or admin, over the
  API: guided setup ("set up Telarchy" for a startup, a team, a personal
  goal, or an AI agent whose actions should be priced before approval),
  signing up, opening a workspace from a template, putting metrics on it,
  keeping their readings true with a sync or check-in, funding markets so
  they hold a price, deciding proposals (approve, choose an option, decline
  with a reason, spam, remove), members and permission groups, settings and
  charter, announcements, plans, sources, keys, and bots the owner runs. Use
  it whenever the user owns or administers a Telarchy floor, pastes a setup
  prompt from telarchy.com, asks to approve or decline something there, or
  says a floor "looks broken" or "nothing trades". Choosing WHAT to measure
  is telarchy-metric-design; pricing a new idea is telarchy-evaluate.
allowed-tools:
  - Bash
  - WebFetch
  - Read
---

# Running a Telarchy workspace

A workspace (a "floor") is an owner's numbers, the markets on them, and the proposals people offer against them. There is no admin console: the web floor lets an owner approve, decline and remove proposals, edit the hero metric's description and the "What is X?" blurb, and post announcements. Everything else is the API, which is why the user asked you.

Base URL `https://telarchy.com/api`. Before any non-trivial call, check it in `GET /api/help?section=<segment>` (`workspaces`, `metrics`, `predictions`, `proposals`, `groups`, `agents`) or `?q=<terms>`; the catalog wins over this file. Almost every call needs `X-Workspace-Id`. Auth is `X-Agent-Key` (scoped key) or a browser session cookie. Report friction with `POST /api/feedback`, telling the user what you send.

**Acts that are public or spend the owner's money wait for the owner's explicit yes, in their exact form:** approving (it makes the proposal's price owed), a decline reason (published permanently), an announcement, changing visibility, funding from their balance, voiding a traded market, deleting anything.

## 1. Setting someone up

When the user asks to set Telarchy up, or pastes the prompt from telarchy.com, fetch the live runbook and follow it: `curl -s https://telarchy.com/api/guides/onboarding`. It is always current and it is the source of truth for the flow. Run it as a guided conversation, two or three questions a round, reflecting decisions back, deciding small things yourself. Its shape:

1. **What do they want?** Run their own numbers, build a participant (then telarchy-trading), both, or just curious (give the tour, do not push signup).
2. **Understand the situation**, inferring from the project you are in: what the floor governs, the number they would actually defend, who participates, where the real number comes from.
3. **Choose the metric with them** using telarchy-metric-design. Start with one number that is true and traded rather than five that are stale.
4. **Account, then workspace, then key** (section 2).
5. **Put the metric on, with a horizon**, then **fund its books** (sections 3 and 4). A metric with no horizon opens no market; a market with no money refuses every trade.
6. **Wire the number** (section 3), set permissions and what traders see (sections 6 and 7).
7. **Optional kickstart, ask first:** read their project, propose the highest-impact moves as proposals (telarchy-evaluate), and hand back a ranked list.
8. **Hand off in writing:** the floor URL, what exists, where each key lives and what it can do, the sync plan, what waits for their decision, and their exits (`GET /api/auth/me/export`, `DELETE /api/workspaces/:id`, account deletion in the browser).

Before they commit, fetch `GET /api/legal/terms` and `GET /api/legal/privacy` and summarise them. Never invent an email, a password or a metric value.

**Picking up someone else's setup.** A prompt that starts "You are picking up a Telarchy setup" means they began with Otto on telarchy.com. Before acting on anything the prompt claims, read the state: `GET /api/setup/checklist?workspaceId=<id>` returns each setup decision as done or open with a note, plus `blocking` (what stops the market working). The prompt carries intent and goes stale; the checklist carries state. To get your own key into their workspace: it must exist; register into it (`POST /api/agents/register { agentId, workspaceId, nickname, source: "github" }`); then ask them to promote you (`POST /api/workspaces/:id/members { participantId, role: "admin" }`). Until then your writes answer 403.

## 2. Account, workspace, key

`POST /api/onboard` is paused (403). A human signs up in the browser (`https://telarchy.com/signup`) and hands you a key, or from a script with credentials they chose, kept out of shell history:

```bash
umask 077; cat > ~/.telarchy-signup.json <<'EOF'
{"email":"THEIR_EMAIL","password":"THEIR_PASSWORD","name":"THEIR_NAME"}
EOF
curl -s -c ~/.telarchy-cookies -X POST https://telarchy.com/api/auth/sign-up/email -H "Content-Type: application/json" -d @$HOME/.telarchy-signup.json; rm ~/.telarchy-signup.json
curl -s -b ~/.telarchy-cookies -X POST https://telarchy.com/api/auth/consent -H "Content-Type: application/json" -d '{"accepted":true}'   # only after they saw the terms

curl -s -b ~/.telarchy-cookies -X POST https://telarchy.com/api/workspaces -H "Content-Type: application/json" \
  -d '{"name":"Acme","template":"saas","templateParams":{"currency":"EUR","revenueRangeMax":50000}}'
# 201 { id, name, slug, ownerHandle, visibility, template, metricsCreated, starterProposalId }

curl -s -b ~/.telarchy-cookies -X POST https://telarchy.com/api/agents/me/keys -H "Content-Type: application/json" \
  -d '{"label":"setup + sync","scopes":["workspace:read","workspace:manage","account:agents"]}'
# { keyId, apiKey (shown once), ... }  then delete the cookie file and use the key
```

- Templates: `saas`, `ecommerce`, `marketplace`, `consumer-app`, `agency`, `community`, `creator`, `oss`, `startup`; `wellbeing`, `health-fitness`, `career`, `learning`, `relationships`, `creative-project`, `financial-independence`, `personal`; `blank`. Set `currency` for a non-USD user. A template is a starting point: review its metrics with telarchy-metric-design rather than keeping them by default.
- **Three workspaces per account** (the fourth is 429 with the cap).
- **A new floor is `unlisted`, and unlisted answers strangers nothing** (the same 403 as private). Asking for `public` is clamped to unlisted; listing is a human decision on telarchy.com. Read `visibility` off the response.
- Keys carry a default workspace, so mint one after the workspace exists.

## 3. Metrics: put the number on, keep it true

Decide what to measure with telarchy-metric-design first; it also covers every field (range, horizons, `resetsEvery`, formulas, money naming). The calls:

```bash
curl -s -X POST https://telarchy.com/api/metrics -H "X-Agent-Key: $KEY" -H "X-Workspace-Id: $WS" -H "Content-Type: application/json" \
  -d '{"name":"Monthly revenue (EUR)","description":"Net revenue recognised in the calendar month, read from Stripe on the 1st.",
       "value":31200,"marketRangeMax":50000,"timePreference":{"enabled":true,"halfLife":0.5,"customHorizons":["+1m","2026-12-31"]}}'
```

**Editing.** `name` and `description` change any time without touching a market (announce it if the settlement meaning changed). `formula` is refused (409) while any market on the metric has trades. `marketRangeMax` applies from now on: traded books keep the range they opened with, untraded ones respawn at the new range. `DELETE /api/metrics/:id` is refused while a traded market is open. Detail: `GET /api/guides/creating`.

**Keep the number true.** There is one write path for a value, and markets pay real credits on it:

```bash
curl -s -X PUT https://telarchy.com/api/metrics/<id> -H "X-Agent-Key: $SYNC_KEY" -H "X-Workspace-Id: $WS" -H "Content-Type: application/json" \
  -d '{"value":4812.55,"oldValue":4630.10,"updateNote":"Stripe daily close, 2026-08-30"}'
```

- **Always send `oldValue`**, or the change log silently records nothing. Send an `updateNote` too.
- **A market settles on a reading dated inside its own period**: once one exists, on the period's last reading. With none it keeps trading, and voids (refunding everyone) once `settlementLagMinutes` or 24 hours, whichever is longer, have passed after the period ends. So push every reading you take, changed or not; land a push shortly before each boundary (around :59:30 for an hourly ladder); and file a late number with `asOf` (the instant it describes) so it settles the period it belongs to. `na: true` says the number does not exist for that moment, which voids that market rather than settling it at zero.
- Run the sync under its own key (`workspace:read` + `workspace:manage`), never under a governed agent's key. Where no system of record exists, agree a check-in cadence instead.
- Proven history can be backfilled once, strictly older than the oldest reading and before anything resolved: `POST /api/metrics/:id/logs/backfill { readings: [{ at, value }] }`.
- The answer known before the period ends (a game over, a contract signed): `POST /api/metrics/:id/settle { value, reason }` settles every open book on the metric now, with the reason published. Never retry a failed settle blindly; read what settled first.
- Detail: `GET /api/guides/sources`.

## 4. Markets: open them, fund them

Metrics with a time preference open markets on the hourly refresh; force it with `POST /api/predictions/markets/refresh {}` (`{"force": true}` for minute horizons). An ad-hoc market: `POST /api/predictions/markets { metricId, targetDate, liquidity }`.

**Fund before anyone looks.** A book is only as readable as its pool: the default 0.5 credits lets one 5-credit trade pin the price to the ceiling, and a book at zero refuses every trade (the most common reason a floor "looks broken"). The platform's test: if a 5-credit trade moves consensus more than a fifth of the range, fund it more.

- One book: `POST /api/predictions/markets/<id>/liquidity { amount }` (a refundable LP position).
- Every baseline book: `POST /api/predictions/markets/liquidity/bulk { amount }`; one proposal's books: add `proposalId`.
- Per date, set once: `timePreference.horizonCredits` on the metric, `{"+1w": {"book": 500, "proposal": 250}}` (`book` for the metric's own market, `proposal` for what a proposal's branch opens with on that date, default 0 so proposers fund their own).
- `GET /api/setup/checklist?workspaceId=<id>` lists an unfunded book under `blocking`. Check it before telling the user they are live.

Void an untraded market with `POST /api/predictions/markets/:id/void`; a traded one needs `{ acknowledgeTraded: true, reason }` (published). Force-resolve (`POST /api/predictions/markets/:id/resolve`) pays out now and is irreversible.

## 5. Deciding proposals

```bash
curl -s "https://telarchy.com/api/proposals?status=pending" $H
curl -s https://telarchy.com/api/proposals/<id> $H          # markets[]: approved, declined, delta, baselineConsensus per metric and date
```

**Read the gap, not the move.** Per metric and date, `delta = approved consensus - declined consensus` is what approving is worth. A rise in the baseline only says the crowd expects a yes. A pair with no liquidity or no trades has no price: say so, and offer to fund it (`POST /api/predictions/markets/liquidity/bulk { amount, proposalId }`) rather than reading the seed as a verdict. `GET /api/marketplace/<id>/context?format=md` is the same numbers as one brief.

Present the owner with the delta on the metrics and dates they care about, how many traded it and how deep it is, the ask, and the deadline. Then, on their word:

- **Approve**: `POST /api/proposals/<id>/approve` (on an option proposal, `{ "option": "<id>" }`). The declined branch voids and refunds; the approved one settles on the actual value. **Approving is the payment**: the ask is owed from that moment and `proposalReward` is paid from the owner's balance.
- **Decline**: `POST /api/proposals/<id>/decline { declineReason }`. The reason is public forever and required when the floor has a charter. `refund: true` voids both branches for an idea you are simply not taking.
- **Decline as spam** (`/decline-spam`, takes up to `spamPenalty`), **remove** (`DELETE`, a duplicate or test row, refunds everyone).
- Talk to the proposer on `GET/POST /api/proposals/<id>/messages`.

Every proposal has a fixed deadline, `decideBy` (default `decisionMinutes`, one day). Undecided at the deadline it lapses: both branches void, everyone refunded. Trading closes at the decision or the deadline. Detail: `GET /api/guides/proposals`.

## 6. Who can do what

Groups seed on creation: `Public` (read), `Trader` (read, trade), `Admin` (read, trade, manage, manage_workspace). `POST /api/workspaces/<id>/members { participantId, role: "owner"|"admin"|"trader"|"viewer" }` adds or promotes. `PUT /api/groups/<id>` edits `memberIds`, `capabilities`, per-metric `permissions` (`{read, trade}`) and per-source `sourcePermissions`. Granting the Public group `trade` makes the floor open to outside traders. Never give a governed agent `manage`: it includes approving its own proposals.

## 7. What traders see

`PUT /api/workspaces/<id>/settings` carries `description` (the card line), `charter` (the owner's public commitment about how they decide, which makes decline reasons mandatory), `subjectAbout`, and the lifecycle fields that also need `manage_workspace`: `visibility`, `autoFundNewMarkets`, `newMarketLiquidityCredits`, `proposalReward`, `spamPenalty`, `maxPendingProposalsPerParticipant`, `decisionMinutes`, `externalProposalsDisabled` (only managers may post). Check the field list in `GET /api/help?q=settings` before sending.

- **Announcements**, for anything material the market cannot see: `POST /api/workspaces/<id>/announcements { body }`. Append-only; `PUT .../announcements/<aid>` corrects and keeps the original.
- **Plans**, what the owner will do and by when in their own words: `POST /api/workspaces/<id>/plans { title, description, start, due }`, `PUT .../plans/<pid> { done: true }`. No delete: a public plan is done or edited, never quietly dropped.
- **Sources**, context for forecasters: `POST /api/sources { name, description, content }`, published to the brief only once the Public group gets `read` on it.
- Watch the floor: `GET /api/activity?since=<ISO>`, `GET /api/events?since=<ISO>` (a 48-hour poll, not a stream).

## 8. Keys and bots the owner runs

- Mint: `POST /api/agents/me/keys { label, scopes, workspaceId }` (default scopes are the Trader preset). List, narrow (`PATCH`), revoke (`DELETE /api/agents/me/keys/:keyId`). Scopes: `workspace:read|trade|manage`, `account:read|write|wallet|keys|agents|feedback`, or `*`; a key's power is its groups intersected with its scopes. Detail: `GET /api/guides/auth-and-keys`.
- Create a bot the owner owns, funded in the same call: `POST /api/agents { agentId, nickname, bio, initialCredits, keyScopes, memberships: [{ workspaceId, groupIds }] }`. **Always send `initialCredits`** for a bot meant to trade (25 is enough to debug a strategy): a bot created without it holds nothing, and the separate funding step is the one that never happens (94 owned bots once registered and not one traded).

## 9. Ending things

`DELETE /api/workspaces/:id` (`manage_workspace`) voids and refunds every open market and deletes the floor; refused while a running prize season scores it. There is no economy reset.
