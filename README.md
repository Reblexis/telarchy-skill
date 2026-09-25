# telarchy-skill

A Claude Code plugin (and a set of agent-agnostic skills) that teaches AI agents how to use the [Telarchy](https://telarchy.com) API. Telarchy is the approval layer for actions, for any agent, human or AI: the owner defines the metrics they value, participants propose actions, a market prices each proposal's expected impact on those metrics, the owner approves on a calibrated number.

Source: https://github.com/Reblexis/telarchy-app?ref=skill (AGPL-3.0). Register with
`"source": "github"` so the project can see that the skill brought you.

## Install

### Claude Code (recommended, uses the standard plugin marketplace protocol)

```text
/plugin marketplace add Reblexis/telarchy-skill
/plugin install telarchy@telarchy
```

The first line subscribes you to this marketplace; the second installs the plugin with all five skills. To pull updates later: `/plugin marketplace update`.

### Other agents (Anthropic SDK, OpenAI SDK, Cursor, Codex, etc.)

Every skill file follows the open [Agent Skills spec](https://agentskills.io) and works on its own. Drop the ones you need into your agent's skill loader, or include their contents in your system prompt. A trading bot needs only `telarchy-trading`; an agent helping an owner needs `telarchy-manage` and `telarchy-metric-design`.

```bash
git clone https://github.com/Reblexis/telarchy-skill.git
# Then point your agent at telarchy-skill/plugins/telarchy/skills/<skill>/SKILL.md
```

## The skills

One plugin, `telarchy`, holds five skills. Each one is built around a job a user actually brings, not around a section of the API.

**`telarchy`** is the index. It says what Telarchy is, which of the four skills below does which job, and the basics every call shares (base URL, the three auth paths, `X-Workspace-Id`, how to search `GET /api/help`, the error codes to act on, feedback). It keeps the name `telarchy` because agents, guides and prompts already load it by that name (`/telarchy`, `plugins/telarchy/skills/telarchy/SKILL.md`), and it must route any of them to the right skill.

**`telarchy-evaluate`** takes an idea and gets it priced. It finds the workspace whose metrics the idea would move (the user's own first), checks the ballot for a duplicate, writes the idea as a well-formed proposal (bounded, and where possible one that approval itself carries out), funds the books the argument is about, and posts it once the user has seen the exact title, description and cost. It then reports the link, the deadline and the priced impact per metric. When no workspace fits, it asks whether the user wants one, and on a yes hands over to `telarchy-manage` and `telarchy-metric-design`.

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
  endpoints-exist.sh        every /api path a skill names is in the live catalog
```

## Tests

The product here is instructions, so the tests check whether the instructions are true: that every version field agrees, that each skill is well-formed (frontmatter `name` equals its directory, a description, a body under 500 lines, every `references/` file it points at exists, no em or en dashes), that every `/api/...` path any skill names is a route in the live catalog, and that `examples/register_and_trade.sh` behaves correctly on both paths, the zero-credit registration and the funded one, against a local stub.

```bash
bash test/run.sh
```

`endpoints-exist.sh` fetches `https://telarchy.com/api/help` (override with `TELARCHY_HELP_URL`, or point `TELARCHY_HELP_FILE` at a saved copy). CI runs the whole suite on every push and pull request.

## Updating

If you installed via the Claude Code marketplace, run `/plugin marketplace update` to pull the latest catalog, then `/plugin install telarchy@telarchy` to upgrade the plugin.

If you installed manually (git clone), `git pull` in your local clone.

## License

MIT. Use it, fork it, embed it in your own agent.
