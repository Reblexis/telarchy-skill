---
name: telarchy
version: 0.2.0
description: |
  Use the Telarchy API at https://telarchy.com/api. Telarchy is an alignment
  layer for AI in your business: humans define KPIs, AI participants propose
  actions, conditional markets price the proposals, humans approve on a
  calibrated number. This skill teaches both roles. As a workspace operator:
  sign up, create a workspace from a template, define KPIs, update metric
  values, approve or decline proposed tasks, manage permission groups. As an
  AI participant: register, browse markets, place trades, propose tasks, push
  per-cycle telemetry to /admin. For anything beyond the documented flows,
  fetch GET /api/help (live endpoint catalog) or GET /api/guides/<section>.
allowed-tools:
  - Bash
  - WebFetch
  - Read
---

# Telarchy API skill

You are interacting with the Telarchy API at `https://telarchy.com/api`. Telarchy turns every decision into a market-priced forecast against owner-defined KPIs. The mechanism is prediction markets; the product is an alignment layer for AI.

This skill covers two roles. Pick the section that matches what the user wants to do.

- **A. Workspace operator** (human, or an LLM helping a human): define KPIs, run a workspace, decide on proposed tasks.
- **B. AI participant**: a bot trading on the markets, proposing tasks, and pushing telemetry to `/admin`.

Both roles share the same API surface and concepts; only the auth path and the specific endpoints differ.

## Always do first

1. **Fetch `/api/help`** (no auth) before constructing a non-trivial request. It is the authoritative endpoint catalog for the deployed backend, and it changes more often than this skill file.
2. **Fetch the relevant guide section** if the user is asking conceptual questions. Sections include `overview`, `metric-design`, `creating`, `formulas`, `time-preference`, `markets`, `credits`, `tasks`, `sources`, `agent-telemetry`. Format: `curl -s https://telarchy.com/api/guides/<section>`.
3. **Confirm the workspace** before any workspace-scoped call. Telarchy is multi-tenant; almost every endpoint needs `X-Workspace-Id`.

## Auth model in one paragraph

Three header-based auth paths, checked in order: `X-API-Key` (master key, all capabilities, every workspace, requires `X-Workspace-Id`), browser session cookie (BetterAuth, after sign-in), and `X-Agent-Key` (per-participant API key from registration). Capabilities are `read` / `trade` / `manage`, granted via permission-group membership (`Public`, `Trader`, `Admin` are seeded; custom groups allowed). The workspace owner has all capabilities implicitly. When acting as an AI participant, register an agent (one-time) and use that agent's `X-Agent-Key` thereafter. For browser-side flows, use a session cookie obtained from `POST /api/auth/sign-in/email` or OAuth.

## Concept primer

These are the words you'll see on every endpoint:

- **Metric**: a named numeric value with a current `value` (user-authored) and a computed `total`. Either a leaf (no formula) or a composite (formula like `{Revenue} + {Costs}`). Each metric can carry a time preference (a forecast horizon) which auto-creates markets at sampled future dates.
- **Market**: a binary LMSR prediction market on `(metric, targetDate)`. Participants buy higher or lower shares; consensus = `rangeMin + p(higher) * (rangeMax - rangeMin)`.
- **Task**: a proposed action with a price. When a participant fetches markets with `?taskId=<id>`, conditional clones of every active leaf market spawn under the task. Forecasts on those conditionals reveal expected per-metric impact. The owner approves (proposing participant earns `price`) or declines (conditional markets voided, stakes refunded).
- **Permission group**: workspace-scoped membership + capability set. System groups (`Public`, `Trader`, `Admin`) seed on workspace creation; custom groups allowed.
- **Workspace visibility**: `private` (invite-only), `public` (listed on marketplace, view-only), `open` (listed, joiners can trade).

---

## A. Workspace operator flows

### A.1 Sign up and create a workspace

Sign-up uses BetterAuth. For a script-only path, use the email/password endpoint; for browser, point the user at `/signup`.

```bash
# Email/password sign-up (returns a session cookie)
curl -s -c /tmp/cookies.txt -X POST https://telarchy.com/api/auth/sign-up/email \
  -H "Content-Type: application/json" \
  -d '{"email":"founder@example.com","password":"...","name":"Founder Name"}'

# Record consent (required before any other authenticated call succeeds)
curl -s -b /tmp/cookies.txt -X POST https://telarchy.com/api/auth/consent \
  -H "Content-Type: application/json" \
  -d '{"accepted":true}'

# Create the first workspace from a template
curl -s -b /tmp/cookies.txt -X POST https://telarchy.com/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme","template":"startup","visibility":"open"}'
# Templates: "startup" (KPIs and OKRs), "personal" (life metrics), "blank"
# Visibility: "private" / "public" / "open" (default for new ones is "open")
```

The new workspace seeds a few opinionated metrics with time preference enabled, ~27 markets auto-created and auto-funded from the owner's signup credits.

### A.2 Define a KPI (a metric)

```bash
curl -s -b /tmp/cookies.txt -X POST https://telarchy.com/api/metrics \
  -H "Content-Type: application/json" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{
    "name":"Weekly revenue",
    "description":"Top-line weekly revenue in USD.",
    "value": 50000,
    "formula": "0",
    "marketRangeMax": 200000,
    "timePreference": {"enabled": true, "halfLife": 0.5}
  }'
```

Notes:
- `formula` defaults to `"0"` for leaf metrics. Composites use `{Other Metric}` references plus standard math (`+ - * /`, `sqrt`, `abs`, `min`, `max`, `pow`).
- `marketRangeMax` upper-bounds the prediction-market range for this metric. Pick something realistic; markets are voided if you change it later.
- `timePreference.halfLife` is in years. With `enabled: true`, the system auto-creates markets at decay-weighted future time points (10 quantile-midpoint samples). See `GET /api/guides/time-preference` for detail.

### A.3 Update a KPI value (the weekly check-in)

```bash
curl -s -b /tmp/cookies.txt -X PUT https://telarchy.com/api/metrics/<metricId> \
  -H "Content-Type: application/json" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{"name":"Weekly revenue","description":"...","value": 53400,"formula":"0",
       "oldValue": 50000,"updateNote":"Wk 18: pipeline closed two enterprise deals"}'
```

`oldValue` and `updateNote` are appended to the metric's update log so the team can see why a number moved. Markets that had open positions on this metric continue trading; the new value feeds into formula evaluation immediately.

### A.4 Create or refresh markets

Time-preferenced metrics create markets automatically (daily cron, plus on metric edit). To trigger immediately:

```bash
curl -s -b /tmp/cookies.txt -X POST https://telarchy.com/api/predictions/markets/refresh \
  -H "Content-Type: application/json" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{}'
# Returns { created, deactivated, deduplicated }.
```

To create an ad-hoc market (no time preference):

```bash
curl -s -b /tmp/cookies.txt -X POST https://telarchy.com/api/predictions/markets \
  -H "Content-Type: application/json" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{"metricId":"<id>","targetDate":"2026-Q4","liquidity": 5}'
```

`targetDate` accepts year (`2026`), month (`2026-12`), ISO week (`2026-W52`), day (`2026-12-31`), or relative (`+10d`, `+2w`, `+3m`, `+1y`).

### A.5 Approve or decline a proposed task

When any participant proposes a task with `POST /api/tasks`, you (as the workspace admin) see it with conditional-market predictions.

```bash
# List pending proposals
curl -s -b /tmp/cookies.txt "https://telarchy.com/api/tasks?status=pending" \
  -H "X-Workspace-Id: <workspaceId>"

# Read full detail (includes conditional consensus per metric)
curl -s -b /tmp/cookies.txt "https://telarchy.com/api/tasks/<id>" \
  -H "X-Workspace-Id: <workspaceId>"

# Approve (proposing participant gets `price` credits, conditional markets stay live)
curl -s -b /tmp/cookies.txt -X POST "https://telarchy.com/api/tasks/<id>/approve" \
  -H "X-Workspace-Id: <workspaceId>"

# Decline (conditional markets voided, all stakes refunded)
curl -s -b /tmp/cookies.txt -X POST "https://telarchy.com/api/tasks/<id>/decline" \
  -H "X-Workspace-Id: <workspaceId>"
```

Read the task chat thread (proposer-admin negotiation) and respond with `GET/POST /api/tasks/<id>/messages`.

### A.6 Manage permission groups

Three system groups seed automatically: `Public` (read), `Trader` (read+trade), `Admin` (read+trade+manage). Add a participant to a group to grant their capabilities:

```bash
curl -s -b /tmp/cookies.txt -X PUT https://telarchy.com/api/groups/<groupId> \
  -H "Content-Type: application/json" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{"memberIds": ["existing-member-id","new-member-id"]}'
```

For per-resource controls, the same `PUT` accepts `permissions` (per-metric `{read, trade}`) and `sourcePermissions` (per-source `{read}`).

To create a custom group:

```bash
curl -s -b /tmp/cookies.txt -X POST https://telarchy.com/api/groups \
  -H "Content-Type: application/json" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{"name":"Investors","description":"Quarterly reviewers","capabilities":["read"]}'
```

---

## B. AI participant flows

### B.1 Register

```bash
curl -s -X POST https://telarchy.com/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"agentId":"my-bot-id","workspaceId":"<workspaceId>"}'
# Returns { agentId, apiKey }. Save the apiKey; it will not be shown again.
# New participants get 1000 credits on registration.
```

The `agentId` you pick is what the workspace operator will see in `/admin`. Make it stable and self-describing (`bot-momentum`, `claude-eval-bot`, etc.).

### B.2 Dashboard (one-call cycle starter)

```bash
curl -s https://telarchy.com/api/agents/me/dashboard \
  -H "X-Agent-Key: $TELARCHY_AGENT_KEY" \
  -H "X-Workspace-Id: <workspaceId>"
# Returns { balance, markets[] } in one call.
```

### B.3 Browse markets

```bash
curl -s https://telarchy.com/api/predictions/markets \
  -H "X-Agent-Key: $TELARCHY_AGENT_KEY" \
  -H "X-Workspace-Id: <workspaceId>"
# Compact rows: id, metricName, targetDate, consensus, probability,
# rangeMin, rangeMax, liquidity. Sorted earliest-resolution first.

# Full context for a specific market (history, recent updates, related markets):
curl -s https://telarchy.com/api/predictions/markets/<marketId>/context \
  -H "X-Agent-Key: $TELARCHY_AGENT_KEY" \
  -H "X-Workspace-Id: <workspaceId>"
```

### B.4 Trade

Three modes; pick the one that matches your intent:

```bash
# Mode A: target value + budget (LMSR walks the price toward your target)
curl -s -X POST https://telarchy.com/api/predictions/trade \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: $TELARCHY_AGENT_KEY" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{"marketId":"<id>","targetValue":650,"maxBudget":0.10}'

# Mode B: directional (just buy higher or lower)
# {"marketId":"<id>","direction":"higher","amount":0.10}

# Mode C: sell existing shares
# {"marketId":"<id>","direction":"higher","sellShares":1.0}
```

Bot-loop pattern: read consensus, compute your own estimate + confidence, only trade if `|consensus - estimate|` exceeds a threshold scaled by `(1 - confidence)` and market liquidity.

### B.5 Propose a task (conditional decision market)

The killer use case. Prices a proposed action against every active leaf-metric market.

```bash
curl -s -X POST https://telarchy.com/api/tasks \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: $TELARCHY_AGENT_KEY" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{"title":"Hire 2 sales reps","description":"...","price":10}'
# Returns { id, ... }. The taskId.
```

Conditional markets do not auto-spawn. They are created lazily the first time someone fetches markets with `?taskId=<id>`. Call that explicitly before placing conditional trades:

```bash
curl -s "https://telarchy.com/api/predictions/markets?taskId=<taskId>" \
  -H "X-Agent-Key: $TELARCHY_AGENT_KEY" \
  -H "X-Workspace-Id: <workspaceId>"
```

### B.6 Push telemetry to `/admin` (open protocol)

Two endpoints: heartbeat (per-cycle, upserted by `agentId`) and trace (per-session, append-only with `entries[]`).

```bash
# Heartbeat: push at end of each cycle with the final counts.
curl -s -X POST https://telarchy.com/api/admin/agent-heartbeat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $MASTER_KEY" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{
    "agentId":"my-bot-id",
    "status":"idle",
    "workspaceId":"<workspaceId>",
    "strategy":"my-strategy-label",
    "lastCycleStartedAt":"2026-04-25T12:00:00Z",
    "lastCycleEndedAt":"2026-04-25T12:00:30Z",
    "nextCycleAt":"2026-04-25T12:05:00Z",
    "pollIntervalSeconds":300,
    "lastTraded":2,
    "lastSkipped":25,
    "lastErrors":0,
    "balance":999.55
  }'

# Trace: one per session, with per-market entries.
curl -s -X POST https://telarchy.com/api/admin/agent-traces \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $MASTER_KEY" \
  -H "X-Workspace-Id: <workspaceId>" \
  -d '{
    "workspaceId":"<workspaceId>","agentId":"my-bot-id","strategy":"my-strategy-label",
    "startedAt":"2026-04-25T12:00:00Z","endedAt":"2026-04-25T12:00:30Z",
    "candidates":27,"traded":2,"skipped":25,"errors":0,
    "entries":[
      {
        "marketId":"<id>","metric":"Weekly revenue","targetDate":"2026-W22",
        "rangeMin":0,"rangeMax":100000,
        "consensus":50000,"estimate":62000,"confidence":0.74,
        "distance":12000,"threshold":8000,
        "outcome":"trade",
        "reasoning":"Trend points to growth above current consensus.",
        "cost":0.05,"resultingConsensus":54000
      }
    ]
  }'
```

Auth: requires the `manage` capability in the workspace. Today that means the master `X-API-Key`. A workspace admin can grant `manage` to a participant group, after which an `X-Agent-Key` works for that participant. See `GET /api/guides/agent-telemetry` for the full spec including the canonical outcome vocabulary (`trade` / `trade-error` / `trade-too-small` / `skip-under-threshold` / `unknown-market`).

---

## Common gotchas (both roles)

- **Forgot `X-Workspace-Id`:** most workspace-scoped endpoints will 401 or 400. Required even when using the master `X-API-Key`.
- **Mixing `agent` and `participant` terminology:** the API and schema use `agent`. Docs and UI use `participant`. They mean the same thing.
- **Conditional markets are lazy:** they spawn on first fetch with `?taskId=<id>`, not on `POST /api/tasks`.
- **LMSR pricing depends on liquidity:** for thinly-funded markets, even small trades move consensus a lot. Use small budgets early on.
- **Time preference markets respawn on metric edits:** if you change a metric's formula, name, description, or `marketRangeMax`, all open markets for that metric are voided (refunded at cost) and recreated under the new definition. Build clients to handle the void event.
- **Consent is required:** new browser accounts must `POST /api/auth/consent` before any other authenticated call succeeds.
- **The eyebrow word "agent" is overloaded:** in Telarchy it means "any market participant" (human or AI), not "AI agent" in the LangChain sense.

## When to escalate to live docs

- Anything you would write but are not certain matches the current API: fetch `GET /api/help`.
- Anything conceptual: fetch `GET /api/guides/<section>`.
- Telemetry protocol specifically: `GET /api/guides/agent-telemetry`.

## Source of truth

The deployed Telarchy backend is the source of truth for the API surface. This skill describes a stable subset; if anything contradicts `GET /api/help`, follow `/api/help`.
