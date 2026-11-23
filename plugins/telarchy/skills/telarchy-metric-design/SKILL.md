---
name: telarchy-metric-design
version: 0.43.11
description: |
  Decide what a Telarchy (telarchy.com) workspace should measure, by the
  guide Telarchy's own chat follows (GET /api/guides/read-first), and encode
  it so the markets price the right thing: definitions that read as
  settlement text, numbers a proposal can move but a trader cannot, money
  and "net" naming, range, one horizon by default, settlement
  (machine-read on a clock, or person-reported and settled by hand), levels vs
  per-period numbers, formulas, N/A, and how to change or retire a metric
  without voiding people's positions. Use it whenever someone is choosing,
  reviewing, renaming, redefining or retiring metrics or KPIs on Telarchy,
  setting up a workspace (with telarchy-manage), asks "what should I
  track/optimize", "is this a good metric", or "why does this market price
  nonsense", or a template's seeded metrics need checking.
allowed-tools:
  - Bash
  - WebFetch
  - Read
---

# Designing Telarchy metrics

Everything downstream runs on this choice: the market prices what the owner listed, and every proposal is priced against it. **What to measure is taught by one text, `GET https://telarchy.com/api/guides/read-first`**: the rules and worked examples Telarchy's own chat follows, served from the same source as the chat's prompt. Read it before you propose anything and follow it; this skill adds only how to encode the result on the API and how to change a metric people already trade.

Your output is a **proposed metric, written out in plain words, that the owner confirms**. You propose; they decide. Nothing is created until they say yes to it in its final form, and a reply shaped like a question ("I think X, no?") opens a discussion rather than approving anything.

## 1. Choose by the guide

Read the project you are in (README, the business, the data) and ask only what you cannot infer. Then choose by the guide: start with one metric, and add one only when the owner would choose against what the first says.

## 2. On a floor other people trade

Two tests the guide does not need for a private space matter once outsiders trade it:

- **Traders cannot move it by trading it, and cannot cheaply ruin it.** A number that reads market prices lets traders move what they are scored on. Where the people who trade a floor also act on it, check whether making the outcome worse is cheaper than making it better.
- **Hard to farm.** Any count of heads is farmable at the price of a head: count net exposure rather than activity, roll bots up to their owner, exclude house accounts.

## 3. Write each one down

For each metric, draft these and show them together:

- **Name**: a short handle (about 20 characters before any unit tail). **Naming is machinery.** A trailing `(USD)` or `$` marks money and puts a `$` on the number. Money **and** the word "net" in the name makes each proposal's approved branch open at baseline minus the ask, because paying the proposer comes out of that number. So: never "net" on a gross number or a count (it prints the same fake loss on every proposal); only USD and `$` are detected, only in the last parenthetical; no date in a name (the market's date carries it, and a dated name orphans every recurring market). Formulas reference names exactly, and a sync keyed by name stops on a rename.
- **Description = the settlement text**: what is counted, where it comes from, at what moment, what is excluded (the owner's own purchases, money merely passing through, test accounts). Traders read this before pricing anything.
- **Level or per-period**: on a public floor a metric is a level that exists at every instant (a trailing-30-day total, a count as of now), not "revenue this week". A private floor may use a number that restarts each period (`resetsEvery`).
- **Range**: books run from `marketRangeMin` (default 0) to `marketRangeMax` and settlement clamps at the edges, so a metric that can reach 500,000 on a range of 1,000 pays every "higher" holder in full whatever happens. Percent gets 100; large currencies are tracked in thousands. Without an explicit range the first value sets it (0 to 2v for a positive v, -2|v| to 2|v| for a negative one, 0 to 1000 for a zero), and a later value never moves it; that guess is often wrong, so set the range yourself from what the owner says the number can reach. With neither a value nor a range it gets 0 to 100 and its books open at once.
- **Horizons**: which future dates get a market, matched to what the decisions affect and never finer than the data arrives (weekly data under daily markets settles a week of markets on one stale reading). **Default to one horizon**: ask how many dates the owner actually decides on, and for one send `{"enabled": false, "customHorizons": ["<that date>"]}` with a `horizonTitles` entry for it. Turning the curve on (`enabled: true`, `density` 3 by default) while also naming `customHorizons` stacks markets: three sampled dates plus each custom one, and every proposal then opens a pair on each (a hackathon floor asked for one date and got five books this way). Add dates only when the owner decides on several (a company floor often reads today, this week and next month). A metric with no horizon opens no market.
- **Settlement: who produces the reading, and when.** Ask before choosing a horizon.
  - *Machine-read on a clock* (a sync from Stripe, analytics, a database): a dated horizon, with the sync pushing before each boundary.
  - *Person-reported* (a rating, a judgment, a check-in someone has to remember): manual settlement. The horizon is `until-settled`, which the owner settles with `POST /api/metrics/:id/settle { value, reason }` once the reading exists, and the metric has `resolvesNaUntilMeasured: true` with no `value` in the create call, so any dated book voids and refunds rather than settling on a placeholder. A person-rated metric on a clock with a placeholder 0 once settled every book on that 0, 48 minutes before the rating arrived.
- **Shape**: a number whose spread matters as much as its middle, especially one that spans orders of magnitude (views, downloads, a launch's signups), gets `marketShape: "distribution"` with `marketScale: "log"` and a `marketRangeMin` above 0: its books then price the whole curve (median, 50% and 90% ranges) instead of one value. Everything else keeps the default binary book.
- **Source and cadence**: where the reading comes from and how often it is pushed; a result that has no value until it happens gets N/A handling or `opensAt`, never an invented neutral reading. N/A is not zero.
- **Liquidity**: what each book opens with (the 0.5-credit default is a trap: if a 5-credit trade moves consensus more than a fifth of the range, it is too thin).

Field names, formula grammar, horizon syntax and the exact API calls are in `references/encoding.md`. Read it before creating or editing anything.

## 4. Present, confirm, then encode

Show the owner the metric: its name, one-line definition, the rule of the guide it rests on, what proposal could move it, and its horizons. Say what you deliberately left out and why (activities you turned into proposal ideas are worth listing: they are the floor's first proposals). Wait for an explicit yes on the final form. Then create or edit with telarchy-manage (or the calls in `references/encoding.md`), and fund the books.

Templates seed metrics so nobody starts blank, but several are activities or vanity numbers (weekly hours, pieces published, stars, views) and per-period names. Review a template's metrics by the guide instead of keeping them by default.

## 5. Changing a metric that is already traded

People hold positions priced on the definition as it stood. So:

- **Words** (`name`, `description`) change any time without touching a market. If a rewording changes what would settle, announce it on the floor.
- **A new definition of a traded metric is a new metric.** Create it beside the old one, so the old books settle on the definition they were traded on.
- **Retire by freezing, never by clearing.** Set the old metric's horizons to the absolute dates its books already stand on (so nothing new opens and nothing open voids), keep it visible until its last book settles, and only then remove it. Clearing `timePreference` or deleting voids traded books and proposal pairs (it once refunded 1,973 credits of other people's positions by accident).
- **Announce any change to a traded book's horizon or settlement before it deploys.** A bot once lost 1,644 credits to an unannounced one.
- The formula of a traded metric cannot change (409); the range applies to books opened from then on.

Real cases where a metric went wrong on a live floor, and what each taught: `references/incidents.md`. Read it when a design is close to one of them, or when the owner asks why a rule exists.
