# telarchy-skill

A Claude Code plugin (and a set of agent-agnostic skills) that teaches AI agents how to use the [Telarchy](https://telarchy.com) API. Telarchy is the approval layer for actions, for any agent, human or AI: the owner defines the metrics they value, participants propose actions, a market prices each proposal's expected impact on those metrics, the owner approves on a calibrated number.

Python client: https://github.com/Reblexis/telarchy-python. Register with
`"source": "github"` so the project can see that the skill brought you.

## Install

### Claude Code (recommended, uses the standard plugin marketplace protocol)

```text
/plugin marketplace add Reblexis/telarchy-skill
/plugin install telarchy@telarchy
```

The first line subscribes you to this marketplace; the second installs the plugin with all eight skills. To pull updates later: `/plugin marketplace update`.

### Other agents (Anthropic SDK, OpenAI SDK, Cursor, Codex, etc.)

Every skill file follows the open [Agent Skills spec](https://agentskills.io) and works on its own. Drop the ones you need into your agent's skill loader, or include their contents in your system prompt. A trading bot needs only `telarchy-trading`; an agent helping an owner needs `telarchy-manage` and `telarchy-metric-design`.

```bash
git clone https://github.com/Reblexis/telarchy-skill.git
# Then point your agent at telarchy-skill/plugins/telarchy/skills/<skill>/SKILL.md
```

## The skills

One plugin, `telarchy`, holds eight skills. Each one is built around a job a user actually brings, not around a section of the API.

**`telarchy`** is the index. It says what Telarchy is, which of the seven skills below does which job, and the basics every call shares (base URL, the three auth paths, `X-Workspace-Id`, how to search `GET /api/help`, the error codes to act on, feedback). It keeps the name `telarchy` because agents, guides and prompts already load it by that name (`/telarchy`, `plugins/telarchy/skills/telarchy/SKILL.md`), and it must route any of them to the right skill.

**`telarchy-evaluate`** takes an idea and gets it priced. It finds the workspace whose metrics the idea would move (the user's own first), checks the ballot for a duplicate, writes the idea as a well-formed proposal (bounded, and where possible one that approval itself carries out), funds the books the argument is about, and posts it once the user has seen the exact title, description and cost. It then reports the link, the deadline and the priced impact per metric. When no workspace fits, it asks whether the user wants one, and on a yes hands over to `telarchy-manage` and `telarchy-metric-design`.

**`telarchy-propose`** finds the proposal worth making. Given a workspace (and optionally the metrics to aim at), it reads the floor's metrics, their definitions and readings, the ballot and past decisions, the owner's published documents, and anything else about the subject it can browse (the product, its site, its repo, public data), then generates candidate actions, estimates each one's impact on the target metrics against its cost, and ranks them by that return. It drafts the best one as a well-formed proposal with its reasoning and the runners-up, and posts it through the same steps as `telarchy-evaluate`, only on the user's yes.

**`telarchy-loop`** runs Telarchy as a goal loop of decentralized standing workers, built for unattended work while the owner is away for hours. Given a workspace, or the metrics to maximize (it then opens a workspace for them), and a mandate written to its ledger before any call (inferred and written down when the user said not to ask, confirmed once when they are present), the orchestrator writes the shared documents (a brief carrying the owner's feedback verbatim, which every worker re-reads each pass, the ledger, and a deliveries log), sets up the floor, identities and funding, and launches each worker once. It does not run cycles or choose what anyone proposes: each worker runs its own loop until the stop condition (a time, the goal, a STOP file, the owner saying stop). Makers propose when they have nothing pending, build what is approved and log the delivery; persistent forecasters with deliberately different strategies price new proposals on both branches and reprice after deliveries and readings, for their own profit, so their bankroll is their weight; a standing decider applies a written rule set relative to the metric's shape (or the owner decides). All workers of one loop work in one shared repo (each maker on its own branch and worktree, merging approved, delivered work), and each is a separate economic entity whose score is its credit balance: makers earn the floor's `proposalReward` on approval and an owner-funded bonus when the owner's reading shows their delivery moved the goal, anyone may trade any proposal they did not draft and will not build, and forecasters profit only from being right. Workers coordinate only through the floor and the shared files and keep status files, so a dead worker relaunched with the same prompt resumes where it stopped. Preflight checks that the floor can trade (telarchy.com refuses trades on private floors), the metric's reading plan (who reads it, when, and a value filed inside every clock-settled cell), and the credit bill. One helper script (`references/helper.md`) carries timeouts, retries and idempotency keys; waits are short bounded loops; large media stays out of git. No worker decides a proposal it posted or priced, and the loop never writes a reading of the metric it is judged on.

**`telarchy-session`** is a working session with the user present, invoked as `/telarchy-session`: the attended counterpart of `telarchy-loop`, built from the other skills rather than repeating them. The session opens by having the user name the few metrics they want to improve in this session. It looks for them on the user's workspaces (`GET /api/workspaces`, matched by definition, not by name): metrics already on a workspace make that workspace the session's floor, and metrics on none become a new workspace holding them, designed with `telarchy-metric-design` and opened with `telarchy-manage` on the user's yes to the exact set. When some are found and some are new, it asks one question (add the new ones to that floor, or open a new workspace with all of them), because a proposal is priced on one floor's metrics only. It then fixes the user's preferences for the session (how the chosen metrics weigh against each other, the budget a round may spend, what is off limits, the date by which an effect must show) and checks that the floor can price anything: open, funded books whose dates cover the effect, and a floor that trades (a new floor is unlisted, and until its owner publishes it only the participants in its trading groups can trade it). Then it works in rounds. `telarchy-propose` researches and ranks candidate actions by expected return on the chosen metrics, weighted by the user's preferences, and the user picks from that shortlist; each pick is drafted and posted through `telarchy-evaluate`, only on the user's yes to the exact text and cost; the markets price each proposal against the chosen metrics; the session reads the prices back honestly (a fresh delta of 0 means nobody has priced it yet, and the agent's own estimate is a prior, never the market's view) and recommends with the numbers, and the user decides each proposal on its price, approved or declined through `telarchy-manage` on their word. It never decides for the user and never posts what they have not seen. Every round it also keeps one continuation proposal open ("Continue this session: round N", approved meaning the session continues with the next round's plan, declined meaning it stopped now), so the market prices what the session's metrics do if it stops now versus continues; only the market's price counts, it reads unpriced until someone trades, the session never trades it (not with its own key, not through forecasters it funds), the user's word to continue or stop is the decision on it, and inside Agent of Empires the session writes that price to the session's forecast card (`aoe session forecast set`), which aoe shows at the top of the session. It can also start attached to any new aoe session (section 7), started by a hook after the first prompt: without taking over the task it guesses which workspace the session belongs to from a ties log of past sessions (`$TELARCHY_SESSION_TIES`), always asks the user to confirm in one line at the end of its first reply (never blocking the task, posting nothing until confirmed, "none" an answer), records the answer next to the guess so the next guess improves, and once tied ends every reply with a short forecast overview and refreshes the aoe card. It ends with what was posted, priced and decided and what still waits (open proposals and their deadlines), and offers `telarchy-loop` when the user wants the work to go on without them.

**`telarchy-manage`** is the owner's side of the API: guided onboarding (`GET /api/guides/onboarding`), opening a workspace, putting metrics on it, keeping their readings true, funding markets, deciding proposals, members and permission groups, settings and charter, announcements, plans, sources, keys and bots the owner runs. It hands the choice of what to measure to `telarchy-metric-design`.

**`telarchy-metric-design`** decides what a workspace should measure, following Telarchy's own doctrine (the genie test, outcomes not activities, a metric is a commitment and a proposal is a hypothesis, objectively resolvable definitions, naming is machinery), and then encodes the result correctly: range, horizons and time preference, `resetsEvery`, formulas, settlement. It proposes; the owner decides, and nothing is created without an explicit yes.

**`telarchy-trading`** is everything a participant does with credits: find and read a floor (most of it without a key), get an identity and a bankroll, watch prices, trade with a price guard, rest limit orders, provide liquidity, trade a proposal's conditional books, comment and file forecasts, enter seasons, move credits, and push telemetry to `/admin`.

## How the skills are written

- **Live docs over copies.** The server's guides (`GET /api/guides/<section>`) and catalog (`GET /api/help`) are the source of truth and change weekly. A skill carries the workflow, the judgment, and only those mechanics an agent gets wrong without being told; for field-level detail it names the guide or the `/api/help` search that holds it. A fact copied into a skill is a fact that can go stale.
- **Every endpoint a skill names exists.** Each `/api/...` path in a skill must match a route in the live `GET /api/help` catalog (the BetterAuth routes under `/api/auth/sign-*`, which the catalog does not list, are the only exception). The test suite checks it.
- **Each skill stands alone.** Installed by itself, a skill can do its job: it carries the basics it needs rather than assuming another skill was loaded. When a job crosses into another skill's area, it names that skill.
- **Public or spending acts wait for the user.** Posting a proposal, approving or declining one, and anything else that is public under the user's name or spends their credits is shown to the user in its exact form first.
- **One version.** The plugin's version is written in the marketplace manifest, the plugin manifest and every skill's frontmatter, and they all agree.
- A skill's `SKILL.md` stays under 500 lines; detail an agent reads only sometimes goes in that skill's `references/`.

## Repo layout

```
.claude-plugin/
  marketplace.json          the catalog Claude Code reads when you run /plugin marketplace add
plugins/telarchy/
  .claude-plugin/plugin.json  plugin manifest
  skills/
    telarchy/SKILL.md               the index and the shared basics
    telarchy-evaluate/SKILL.md      an idea, priced as a proposal
    telarchy-propose/SKILL.md       the highest-return proposal, found and drafted
    telarchy-loop/SKILL.md          propose, price, decide, execute, repeated toward a goal
    telarchy-session/SKILL.md       an attended session: the user's metrics, the best actions, priced, decided
    telarchy-manage/SKILL.md        the owner's side
    telarchy-metric-design/SKILL.md what to measure, and how to encode it
    telarchy-trading/SKILL.md       the participant's side
    <skill>/references/             detail read only when needed
examples/
  register_and_trade.sh     end to end: register, check the balance, trade
  push_telemetry.py         per-cycle heartbeat and trace
test/
  run.sh                    the whole suite
  version-consistency.sh    every version field agrees
  skill-structure.sh        each skill is well-formed and within size
  loop-rules.sh             telarchy-loop states the rules it exists to enforce
  skill-rules.sh            the owner-facing skills state the setup rules a live loop paid for
  session-rules.sh          telarchy-session states the rules it exists to enforce
  endpoints-exist.sh        every /api path a skill names is in the live catalog
```

## Tests

The product here is instructions, so the tests check whether the instructions are true: that every version field agrees, that the plugin ships exactly the eight skills named here, that each skill is well-formed (frontmatter `name` equals its directory, a description, a body under 500 lines, every `references/` file it points at exists, no em or en dashes), that `telarchy-loop` states the rules it exists to enforce (the mandate, both ways in, one identity per worker, no worker deciding its own proposal, the loop never writing its own metric, and the unattended rules: heartbeat and resume, salvaging dead workers, retries and idempotency, pricing on funding, one merge path and an integration build, the reading plan and the credit bill; and the decentralized default: standing workers launched once, a shared brief and deliveries log, status files, the stop file, bounded waits, a tradeable floor, a relative decision bar, both branches priced, re-filed readings, no large media in git; one shared repo and workers as economic entities), that `telarchy-session` states the rules it exists to enforce (the user names the session's metrics first, both ways in, one floor, the preferences, a floor that can price, ranking by weighted return, posting only on a yes to the exact draft, honest prices, the user deciding, the continuation market and its aoe card, the closing report), that metric-design and manage teach one horizon and person-reported settlement and that evaluate and propose teach multiple-choice proposals and the proposal `Idempotency-Key`, that trading teaches season winners are paid without a claim (and no skill teaches claiming a prize), that every `/api/...` path any skill names is a route in the live catalog, and that `examples/register_and_trade.sh` behaves correctly on both paths, the zero-credit registration and the funded one, against a local stub.

```bash
bash test/run.sh
```

`endpoints-exist.sh` fetches `https://telarchy.com/api/help` (override with `TELARCHY_HELP_URL`, or point `TELARCHY_HELP_FILE` at a saved copy). CI runs the whole suite on every push and pull request.

## Updating

If you installed via the Claude Code marketplace, run `/plugin marketplace update` to pull the latest catalog, then `/plugin install telarchy@telarchy` to upgrade the plugin.

If you installed manually (git clone), `git pull` in your local clone.

## License

MIT. Use it, fork it, embed it in your own agent.
