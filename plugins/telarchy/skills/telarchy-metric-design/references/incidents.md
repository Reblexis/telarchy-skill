# When a metric went wrong on a live floor

Each of these happened on telarchy.com, most on Telarchy's own floor. They are why the rules in the skill exist. Match a design against them before shipping it.

1. **Retiring by clearing horizons voided traded books** (2026-09-08). A metric was retired by clearing its time preference; ten traded books, including proposal pairs, voided and 1,973 credits of other people's positions were refunded and had to be restored by hand. Rule: retire by freezing the horizons to the absolute dates the books already stand on, and keep the metric visible until its last book settles.
2. **A proposal's price subtracted from a number it was not paid out of** (2026-08-15). The ask was taken off a gross or non-money metric, printing the same fake loss on every proposal. Rule: only a money name (`(USD)` or `$`) that also says "net" subtracts the ask.
3. **The owner's own purchase became the revenue** (2026-09-01). A $5 test purchase by the owner counted as revenue for 19 hours and settled a daily market. Rule: write exclusions into the definition, and exclude the house's own money.
4. **A rename filed last week's total inside the new week.** Edits used to write readings. Rule: a rename is not a measurement; and a sync keyed by name stops silently on a rename.
5. **"Write only when changed" emptied the chart**, and a daily cron gave forecasters one point a day. Rule: record every reading taken, changed or not, on a reliable scheduler.
6. **A market settled partly on its own price** (found 2026-08-30). A blended "outlook" mixed the reading with the market's consensus. Rule: traders must never be able to move the number they are scored against.
7. **A number no proposal could move** (implied valuation, removed 2026-09-08). Every proposal carried dead, flat books and the markets voided N/A. Rule: a priced metric must be movable by a proposal within its horizon.
8. **A count of profitable traders** (retired 2026-09-13). It measured supply, not accuracy (an accurate market drives it to zero), and it could be faked by pricing your own position or holding both sides with two bots. Rule: measure the goal directly; the price of a head is the whole design.
9. **A trader count that looked only at one source** missed two of the four largest traders and was read as a statement of who mattered (2026-09-04). Rule: check what a definition leaves out, not only what it counts.
10. **A referral job measured by "makes a trade"** was satisfied with a one-credit trade. Rule: the genie test, on proposals' success criteria as much as on metrics.
11. **A game outcome the traders could ruin** (chess, 2026-09-19). One participant shorted the main book and bought the losing moves. Rule: where traders also steer the outcome, check whether worse is cheaper than better.
12. **An invented neutral reading** (chess, 2026-09-17). A 50 written at game start helped nobody and priced a number that did not exist. Rule: a result has a value only when there is a result; use `opensAt` for where books open.
13. **A book on the wrong clock** (snake, 2026-09-14). An attempt's length was priced on hourly cells, so the book closed every hour and paid on the hour instead of when the attempt ended. Fixed with `until-settled`; then a bot lost 1,644 credits because the horizon change was not announced. Rule: price the question's own clock, and announce any change to a traded book's horizon or settlement before it deploys.
14. **A mis-ranged metric.** A number that can reach 500,000 on a range of 1,000 settles at the ceiling and pays every "higher" holder in full; a 0.5-credit book pins to the ceiling on one 5-credit trade. Rule: realistic range, funded books.
15. **A metric with no horizon** opens no market, and a floor with no market looks broken.
16. **A retired metric's tab removed while its books were open** left holders reading the wrong number (2026-09-25). Rule: keep the frozen metric visible until its last book settles.
