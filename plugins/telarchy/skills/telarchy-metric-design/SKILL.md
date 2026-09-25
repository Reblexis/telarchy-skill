---
name: telarchy-metric-design
version: 0.33.0
description: |
  Decide what a Telarchy (telarchy.com) workspace should measure, following
  Telarchy's own doctrine, and encode it so the markets price the right
  thing: the genie test, outcomes not activities, a metric is a commitment
  and a proposal is a hypothesis, objectively resolvable definitions that
  read as settlement text, numbers a proposal can move but a trader cannot,
  money and "net" naming, range, horizons and time preference, levels vs
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

Everything downstream runs on this choice. The market prices what the owner listed, every proposal is priced against it, and the owner approves on that price. The system faithfully optimizes whatever it is given, so a badly chosen metric produces a confident number about the wrong thing, which is worse than no number. The canonical text is the live guide, `GET https://telarchy.com/api/guides/metric-design`; read it at the start of any real design session. This skill is how to apply it.

Your output is a **proposed set of metrics, written out in plain words, that the owner confirms**. You propose; they decide. Nothing is created until they say yes to the set in its final form, and a reply shaped like a question ("I think X, no?") opens a discussion rather than approving anything.

## 1. Find what they actually value

Start from terminal goals, not from what is easy to count. Read the project you are in (README, the business, the data) and ask only what you cannot infer: what does this floor govern, what outcome would the owner defend in an argument, over what timescale, and where does each real number live. If they have ranked goals, keep the ranking; it decides which metric leads.

A workspace usually needs **several** metrics, not "one number": a company cares about more than one thing, and a single metric is exactly the missing-dimension failure below. On a floor that is priced in public, keep it to **three or four at most** (fewer means more liquidity behind each book and fewer dead proposal pairs). Start the market on the one or two that are true and synced today, rather than five that go stale.

## 2. Test every candidate

Run each candidate through these, in order. Most bad metrics fail the first two.

1. **The genie test.** Assume a perfectly competent optimizer that delivers precisely what the definition says, not what was meant. If every metric here were maximized perfectly, walk through the world that produces. Is it the outcome they want? It comes back no in three shapes: a **missing dimension** (something they care about is nowhere, so nothing protects it), a **proxy satisfiable on its own** (revenue up, business hollowed out; a rate up because the denominator was gamed), a **trade-off they would never endorse** (a formula lets one part collapse while another overcompensates). Fix the definition until perfect achievement of it is exactly the outcome.
2. **Outcome, not activity.** Lines of code, tickets closed, features shipped, posts published, hours worked, followers, views, "engagement": track the activity and you get more activity. The test: *would they still want this if it caused nothing else?* If not, it is instrumental. A belief that an activity causes the outcome is a **proposal** ("will doing X move Y?"), which the market can price; a metric is a **commitment** that this quantity certainly matters.
3. **The level of abstraction they are sure of.** A self-reported happiness score is a better leaf than a dopamine reading, because the link between them is the uncertain part. Subjective metrics are legitimate when the feeling is the point: say so with a `(self-reported)` tail and a description that admits it is a gut read.
4. **Objectively resolvable.** Someone was paid or not paid on this number. Anyone with the data must land on the same value. A number a machine publishes beats one a person types, because nobody has to trust the person.
5. **A proposal can move it within its horizon.** A number nothing on the floor can move in the priced window (an implied valuation before a round closes) gives every proposal flat, dead books and forecasters nothing to be paid for.
6. **Traders cannot move it by trading it, and cannot cheaply ruin it.** A number that reads market prices lets traders move what they are scored on. Where the people who trade a floor also act on it (a game decided by the market), check whether making the outcome worse is cheaper than making it better; if so, someone will short it and do the work badly.
7. **Hard to farm.** Any count of heads is farmable at the price of a head, so the price of a head is the whole design: count net exposure rather than activity, roll bots up to their owner, exclude house accounts. Keep it as simple as possible while staying robust.
8. **Readable scale.** Prefer a bounded number (a percentage, a win rate) over an unbounded raw count when both carry the same meaning.

Then check the set as a whole: different timescales are **sibling metrics** with their own half-lives, not one metric trying to mean both; different audiences are **different workspaces**; do not wire one workspace's metrics into another's formula (the link is the uncertain part, so test it with a proposal). Double counting is fine only when deliberate.

## 3. Write each one down

For each metric, draft these and show them together:

- **Name**: a short handle (about 20 characters before any unit tail). **Naming is machinery.** A trailing `(USD)` or `$` marks money and puts a `$` on the number. Money **and** the word "net" in the name makes each proposal's approved branch open at baseline minus the ask, because paying the proposer comes out of that number. So: never "net" on a gross number or a count (it prints the same fake loss on every proposal); only USD and `$` are detected, only in the last parenthetical; no date in a name (the market's date carries it, and a dated name orphans every recurring market). Formulas reference names exactly, and a sync keyed by name stops on a rename.
- **Description = the settlement text**: what is counted, where it comes from, at what moment, what is excluded (the owner's own purchases, money merely passing through, test accounts). Traders read this before pricing anything.
- **Level or per-period**: on a public floor a metric is a level that exists at every instant (a trailing-30-day total, a count as of now), not "revenue this week". A private floor may use a number that restarts each period (`resetsEvery`).
- **Range**: books run from 0 to `marketRangeMax` and settlement clamps at the top, so a metric that can reach 500,000 on a range of 1,000 pays every "higher" holder in full whatever happens. Percent gets 100; large currencies are tracked in thousands.
- **Horizons**: which future dates get a market, matched to what the decisions affect and never finer than the data arrives (weekly data under daily markets settles a week of markets on one stale reading). Company floors read well on three dates (today, this week, next month); a game prices "until settled". A metric with no horizon opens no market.
- **Source and cadence**: where the reading comes from and how often it is pushed; a result that has no value until it happens gets N/A handling or `opensAt`, never an invented neutral reading. N/A is not zero.
- **Liquidity**: what each book opens with (the 0.5-credit default is a trap: if a 5-credit trade moves consensus more than a fifth of the range, it is too thin).

Field names, formula grammar, horizon syntax and the exact API calls are in `references/encoding.md`. Read it before creating or editing anything.

## 4. Present, confirm, then encode

Show the owner the set as a short list: each metric's name, one-line definition, why it passes the genie test, what proposal could move it, and its horizons. Say what you deliberately left out and why (activities you turned into proposal ideas are worth listing: they are the floor's first proposals). Wait for an explicit yes on the final form. Then create or edit with telarchy-manage (or the calls in `references/encoding.md`), and fund the books.

Templates seed metrics so nobody starts blank, but several are activities or vanity numbers (weekly hours, pieces published, stars, views) and per-period names. Review a template's metrics with these tests instead of keeping them by default.

## 5. Changing a metric that is already traded

People hold positions priced on the definition as it stood. So:

- **Words** (`name`, `description`) change any time without touching a market. If a rewording changes what would settle, announce it on the floor.
- **A new definition of a traded metric is a new metric.** Create it beside the old one, so the old books settle on the definition they were traded on.
- **Retire by freezing, never by clearing.** Set the old metric's horizons to the absolute dates its books already stand on (so nothing new opens and nothing open voids), keep it visible until its last book settles, and only then remove it. Clearing `timePreference` or deleting voids traded books and proposal pairs (it once refunded 1,973 credits of other people's positions by accident).
- **Announce any change to a traded book's horizon or settlement before it deploys.** A bot once lost 1,644 credits to an unannounced one.
- The formula of a traded metric cannot change (409); the range applies to books opened from then on.

Real cases where a metric went wrong on a live floor, and what each taught: `references/incidents.md`. Read it when a design is close to one of them, or when the owner asks why a rule exists.
