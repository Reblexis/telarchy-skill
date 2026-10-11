# The continuation helper

`scripts/continuation.py` carries out the continuation market of section 5 for one session: it posts the proposal, reads its price back into the aoe card and the forecast overview, and records the user's word to continue or stop. Python 3.8 or newer, standard library only. Run it with the skill directory's path, for example `python3 <skill>/scripts/continuation.py card`.

It never trades, with any key: an agent that wants to keep running is the last one who should price whether it should. The only writes it makes are `POST /api/proposals`, `POST /api/proposals/:id/approve` and `POST /api/proposals/:id/decline`.

## Which session, which floor, which key

- **Session**: `--instance <id>`, else `$AOE_INSTANCE_ID`. Without either it exits 2.
- **Floor**: `post --workspace <slug>`. `card` and `decide` take the floor from the session's last line in the continuations log.
- **Key and API**: `$TELARCHY_API_KEY` with `$TELARCHY_API_URL` (default `https://telarchy.com/api`) when the key is set. Otherwise the floors file, `$TELARCHY_FLOORS` (default `~/.config/telarchy/floors.json`), an object keyed by floor slug with `"*"` as the fallback entry: `{"telarchy": {"api": "https://telarchy.com/api", "key_file": "~/keys/me.env", "key_var": "TELARCHY_KEY"}}`. `key_file` is a shell env file holding `KEY=value` lines (an `export ` prefix and quotes are allowed); `key_var` names the line. No key found: exit 2, naming the floor. The key is sent as `X-Agent-Key` with `X-Workspace-Id` set to the floor's id.
- **Ties log** (`$TELARCHY_SESSION_TIES`, default `~/.config/telarchy/session-ties.jsonl`): the session's last tie supplies the defaults below (`metrics`, `weights`, `continuation_seed`, `title`).

## The continuations log

`$TELARCHY_SESSION_CONTINUATIONS`, default `~/.config/telarchy/session-continuations.jsonl`, one JSON object per line, appended and never rewritten:

- a post: `{"at", "event": "post", "aoe_instance_id", "workspace", "workspace_id", "api", "round", "proposal_id", "number", "url", "decide_by", "seed", "plan", "books": [{"metric_id", "metric_name", "target_date", "amount"}]}`;
- a decision: `{"at", "event": "decide", "aoe_instance_id", "proposal_id", "decision": "continue" | "stop"}`.

The session's last `post` line is its current continuation proposal.

## post

`post --workspace <slug> --plan "<the next round's plan, two or three lines>" [--seed <credits>] [--hours <h> | --decide-by <ISO instant>] [--metric <name>]... [--label <text>] [--dry-run]`

1. **One open per session.** If the session's current continuation proposal is still `pending` on the server, nothing is posted: it prints that proposal's link and exits 3.
2. **Round**: one more than the session's last posted round; the first is round 2 (round 1 is the work already under way).
3. **Deadline**: `--decide-by`, else now plus `--hours` (default 24).
4. **Books**: the session's metrics are `--metric` names, else the tie's `metrics`, else every metric with an open book. For each, the open book (from `GET /api/marketplace/<slug>`) whose `resolvesOn` is the earliest after the deadline; a metric with none is skipped and named on stderr, because only a date that settles after the deadline gets a pair. No book at all: exit 2, nothing posted.
5. **Seed**: `--seed`, else the tie's `continuation_seed`, else 100 credits, split evenly over the chosen books (rounded down to a hundredth) and sent as the per-book `liquidity` list, so no other book is seeded.
6. **Post**: `POST /api/proposals` with title `Continue this session: round <N> (<label>)` (label: `--label`, else the tie's `title`, else the aoe session title; the parenthesis is dropped when there is none; the title is at most 120 characters), the plan plus one fixed paragraph saying approved means the session continues with this plan and declined means it stopped now, `decideBy`, and `liquidity`. The `Idempotency-Key` is `aoe-<instance>-round-<N>`, the same on every retry, so a retry never posts twice.
7. Appends the post line, prints one JSON line `{"number", "url", "decide_by", "books", "cost"}`, then does what `card` does.

`--dry-run` prints the body it would send and posts nothing. The proposal's link is `<origin>/<slug>/p/<number>`, the origin being the API URL without `/api`.

## card

`card [--no-aoe]` re-reads the session's current continuation proposal (`GET /api/proposals/:id`, traders from the floor's marketplace) and writes the aoe card (`aoe session forecast set`, contract in aoe's `docs/guides/session-forecast.md`), then prints the forecast overview: at most four lines.

- **Rows**: one per seeded book (metric and date), at most 8: `stopped` is the declined branch's price, `continued` the approved branch's, `traders` the most traders on either branch, `depth` both branches' liquidity in credits. A row is **priced** once either branch has a trade.
- **Pending**: `unpriced` with headline `unpriced: nobody traded yet` while no row is priced; otherwise the score is the sum over priced rows of weight times delta over the book's range (`rangeMax - rangeMin`), the weight being the tie's `weights[<metric name>]`, else 1. Above zero is `continue`; zero or below is `stop`, since another round costs something and the market sees nothing for it. The headline is the priced row with the largest weighted share: its signed delta and metric name, cut to 32 characters.
- **Decided**: approved is `continue` with headline `continued: round <N>`; declined is `stop` with `session stopped`; lapsed is `unpriced` with `lapsed undecided`; withdrawn or removed is `unpriced` with `withdrawn`.
- **No proposal yet**: `unpriced`, headline `no continuation proposal yet`, and that one overview line.
- `note` is the plan (cut to 280 characters), `source` is `{"label": "Telarchy #<number>", "url"}`, `decide_by` the deadline.
- With `--no-aoe` (accepted by every verb) the card is not written. If `aoe` fails, it says so in one stderr line and still prints the overview, exit 0.

## decide

`decide continue|stop` decides the session's current continuation proposal on the user's word: `continue` approves it (`POST /api/proposals/:id/approve`), `stop` declines it with the reason `session stopped`. It needs a key with `manage` on the floor. It appends the decision line, then does what `card` does. A proposal that is no longer pending answers 409 on the server; the helper prints it and exits 1.

## Errors

Every call has a 30 second timeout and up to 3 retries on network errors and 5xx answers, POSTs included (their `Idempotency-Key` makes that safe). An API error prints the server's `error` and `code` and exits 1.
