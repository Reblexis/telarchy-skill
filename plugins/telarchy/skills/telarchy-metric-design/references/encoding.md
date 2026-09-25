# Encoding a metric in the API

Read this before creating or editing a metric. The live detail is in the guides `creating`, `time-preference`, `formulas` and `sources` (`GET https://telarchy.com/api/guides/<name>`), and `GET /api/help?section=metrics` is the contract; check a field there before sending it.

## Contents

- Create
- The fields
- Horizons
- Formulas
- Readings and settlement
- Editing, retiring, deleting

## Create

Needs `manage` on the workspace (`X-Agent-Key` or a session, plus `X-Workspace-Id`).

```bash
curl -s -X POST https://telarchy.com/api/metrics \
  -H "X-Agent-Key: $KEY" -H "X-Workspace-Id: $WS" -H "Content-Type: application/json" \
  -d '{"name":"Revenue, 30 days (USD)",
       "description":"Stripe charges minus refunds over the trailing 30 days, read every 15 minutes. Excludes the owner'"'"'s own test purchases.",
       "value":4120,"marketRangeMax":20000,
       "timePreference":{"enabled":false,"customHorizons":["+0d","+0w","2026-10"],
                         "horizonCredits":{"+0w":{"book":500,"proposal":0}}}}'
```

Create leaves first and composites second (a formula names its parts).

## The fields

| Field | Default | Notes |
|---|---|---|
| `name` | required | Short handle. Trailing `(USD)` or `$` = money; money plus "net" = approved branches open at baseline minus the ask. No date in it. Formulas and syncs reference it exactly. |
| `description` | `""` | The settlement text: what, where from, when, what is excluded. |
| `value` | `0` | The current reading. Ignored (stored as 0) on a computed metric. Never invent one: use the honest current value, or N/A handling. |
| `formula` | `"0"` | Empty or `0` = leaf. Anything else = computed. Markets open only on leaves. |
| `marketRangeMax` | `1000` | Books run 0..this. Settlement clamps at the top. Leaf only, positive. |
| `timePreference` | `{ enabled: true, halfLife: 1 }` | Which dates open markets. Omitted means that default, so set it deliberately. `null` = no curve and no horizons (an evidence series). |
| `resetsEvery` | `null` | `hour`, `day`, `week`, `month`, `year` when the number restarts each period. Changes only which readings the chart attributes to a period, never settlement. Null for a level. |
| `resolvesNaUntilMeasured` | `false` | For a number that does not exist until an event (a valuation before a round): its markets void as N/A while it has no reading. The first reading ends that for good. |
| `opensAt` | `null` | Leaf only, inside the range: where untraded books open instead of at the reading. For a number with no running reading (a game's score). Put it in the create call, or the first book opens at the wrong price. |
| `liquidityCredits` | workspace default | What a new book on this metric opens with. `horizonCredits` overrides it per date. |
| `settlementLagMinutes` | 0 | How long after a period the number is final (0 to 90 days). Markets opened afterwards settle that long after their period. |
| `marketTitle` | null | The whole question over this metric's book, in the owner's words (at most 200 chars). |

There is no `target`, `granularity` or `unit`. A goal line is a market, not a field. Order is set with `POST /api/metrics/reorder` (an array of ids); the headline is the furthest-resolving open market, ties to the lower order.

## Horizons

`timePreference = { enabled, halfLife, density, customHorizons, horizonCredits, horizonTitles }`.

- `halfLife` is in **years**: the median sampled date sits at it. 0.25 to 0.5 tactical, 1 annual planning, 2 to 5 structural. `density` (default 3) is how many dates the curve samples; every date is a book that needs money, and every proposal adds two books per date, so count before raising it: metrics x dates x (1 + 2 per pending proposal).
- At most one metric on any path carries the curve. Different timescales are siblings.
- `customHorizons` (max 24), with the curve on or off:
  - rolling `+Nmin` (1 to 1440), `+Nh`, `+Nd`, `+Nw`, `+Nm` (months), `+Ny`, re-resolved on every refresh; `+0d` / `+0w` is the current period.
  - one-shot `YYYY`, `YYYY-MM`, `YYYY-Www`, `YYYY-MM-DD`, `YYYY-MM-DDTHH` (UTC hour), `YYYY-MM-DDTHH:MM` (UTC minute); resolves at the end of that period.
  - `until-settled`: no clock; trades until `POST /api/metrics/:id/settle`, then the next refresh opens a fresh one. Settling settles every open book on the metric, so give it a metric of its own or one whose dated books share the answer.
- `horizonCredits[entry] = { book, proposal }`: what the metric's own book and each proposal branch open with on that date, paid by the owner. `proposal` defaults to 0, meaning proposers fund their own.
- `horizonTitles[entry]`: at most 60 chars, the words the floor reads in place of the clock ("this attempt").
- A company floor reads well on three dates: `+0d`, `+0w`, and next month as an absolute date. Never finer than the data cadence.
- A floor on minute horizons forces the refresh each minute: `POST /api/predictions/markets/refresh {"force": true}` with a manager key.

## Formulas

`{Name}` references plus `+ - * / ^ ( )`, `sqrt abs log log10 min max pow clamp`. No comparisons, no `%`, no bare identifiers. A missing reference evaluates as 0; an unknown value makes the whole formula unknown; NaN evaluates as 0. Shapes worth knowing: weighted sum `{A} * 0.6 + {B} * 0.4`; geometric mean for balance `sqrt({Adoption} * {Retention})`; diminishing returns `pow({X}, 0.6)`; only the part above a threshold `max({X} - 500, 0)`; normalise `clamp({Raw} / {Max} * 1000, 0, 1000)`. Do not hardwire a link you are unsure of (another workspace's metric, an assumed causal weight): that is a proposal. Renaming does not rewrite formulas.

## Readings and settlement

- One write path: `PUT /api/metrics/:id { value, oldValue, updateNote }`. Always send `oldValue`, or the change log records nothing.
- `asOf` (never in the future) files a reading at the instant it describes, so a September total typed on 3 October settles September.
- `na: true` (or `value: null`) says the number does not exist for that moment: that period's market voids and refunds. N/A is not zero.
- A market settles on the last reading dated inside its own period, once one arrives. With none it voids after `max(settlementLagMinutes, 24 hours)` past the period's end. A reading one second past the boundary belongs to the next period. Push every reading you take, changed or not.
- History you can prove: `POST /api/metrics/:id/logs/backfill { readings: [{ at, value }] }`, strictly older than the oldest reading, and only before anything on the metric has resolved.
- Settle early when the answer is known: `POST /api/metrics/:id/settle { value, reason }` settles every open book on the metric.

## Editing, retiring, deleting

- `name`, `description`: any time, markets untouched. Announce if settlement meaning changed.
- `formula`: 409 while any book on the metric has trades; untraded books are voided and respawned.
- `marketRangeMax`: applies from now on. Traded books keep their range; untraded ones respawn at the new one.
- `timePreference`: reconciles markets (dropped dates deactivate to sell-only and still resolve; new dates open). **Never set it to `null` on a metric with traded books or proposal pairs**: freeze it instead, with `customHorizons` set to the absolute dates its open books stand on and the curve off.
- A new definition of a traded metric is a new metric, created beside it.
- `DELETE /api/metrics/:id`: 409 while any traded book is open. Voiding a traded book needs `{ acknowledgeTraded: true, reason }`, published.
