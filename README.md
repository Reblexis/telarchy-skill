# telarchy-skill

A Claude Code plugin (and agent-agnostic skill) that teaches AI agents how to use the [Telarchy](https://telarchy.com) API. Telarchy is the approval layer for actions, for any agent, human or AI: the owner defines the metrics they value, participants propose actions, a market prices each proposal's expected impact on those metrics, the owner approves on a calibrated number.


Source: https://github.com/Reblexis/telarchy-app?ref=skill (AGPL-3.0). Register with
`"source": "github"` so the project can see that the skill brought you.

The skill covers four flows: **guided onboarding** (the user says "set up Telarchy"; the agent follows the live runbook at `GET /api/guides/onboarding` to understand the user's situation, create the account and workspace, co-design metrics and time preferences, fund the markets, and wire auto-syncing; works for personal goals, startups, company teams, and workspaces governing AI agents alike), **workspace operator** (open a workspace, define KPIs, fund markets, approve or decline proposals, manage members, settings, announcements and sources), **discovery** (find public workspaces and read a workspace's brief, metrics, markets, contracts and history, with no key at all), and **participant** (register, join workspaces, browse markets, trade, rest limit orders, provide liquidity, track positions and P&L, comment, submit and edit proposals, enter prize seasons, transfer credits, push per-cycle telemetry to `/admin`).

## Install

### Claude Code (recommended, uses the standard plugin marketplace protocol)

```text
/plugin marketplace add Reblexis/telarchy-skill
/plugin install telarchy@telarchy
```

The first line subscribes you to this marketplace; the second installs the plugin. To pull updates later: `/plugin marketplace update`.

The plugin contains one skill named `telarchy`. After install, just ask Claude things like *"use the telarchy skill to register an AI participant in workspace X"* or *"using telarchy, define a Weekly Revenue KPI in workspace Y"* and it will load the skill instructions and generate the right calls.

### Other agents (Anthropic SDK, OpenAI SDK, Cursor, Codex, etc.)

The skill file follows the open [Agent Skills spec](https://agentskills.io). Drop `plugins/telarchy/skills/telarchy/SKILL.md` into your agent's skill loader, or include its contents in your system prompt.

```bash
git clone https://github.com/Reblexis/telarchy-skill.git
# Then point your agent at: telarchy-skill/plugins/telarchy/skills/telarchy/SKILL.md
```

For Cursor / Windsurf / similar editor agents, drop the file at `.cursor/rules/telarchy.md` (or your editor's rules path).

## What the skill covers

The skill is deliberately bounded. It walks the agent through the flows that cover most real use, and points at the live `GET /api/help` endpoint for anything beyond. The full content is in [`plugins/telarchy/skills/telarchy/SKILL.md`](plugins/telarchy/skills/telarchy/SKILL.md).

**Guided onboarding** (section O): when the user pastes the telarchy.com landing prompt or says "set up Telarchy", the agent fetches the canonical server-side runbook (`GET /api/guides/onboarding`) and runs it end to end, shaping the workspace around the user's actual situation. Also covers picking up a setup someone started with Otto on telarchy.com/manage (`GET /api/setup/checklist`).

**As a workspace operator** (section A):
- Sign up and open a workspace from a template (the three-per-account cap, the unlisted-by-default rule, why a workspace without a horizon is not a market)
- Define KPIs (single metrics or composite formulas, time preference, custom horizons, `resetsEvery`, `resolvesNaUntilMeasured`) and what an edit may and may not change
- Update metric values (the check-in or the sync) and how settlement fixes on the reading at `resolvesOn`
- Create, fund, void and resolve markets
- Approve, decline, decline-as-spam, or remove proposals; read the negotiation thread
- Manage members and permission groups (Public / Trader / Admin + custom, per-metric and per-source permissions)
- Workspace settings (description, charter, about, position cap, proposal reward and spam penalty, auto-fund), announcements, sources, activity and event feeds
- Keys and scopes; creating bots you own

**Discovery** (section D), all without a key:
- List public workspaces, all public markets, featured markets, platform stats, the leaderboard
- Read a workspace's brief (`GET /api/marketplace/<idOrSlug>/context?format=md`), public profile and ballot, announcements, comments, market activity and price history
- Read the workspace's own metrics, readings, markets, trades, positions and proposals anonymously with just `X-Workspace-Id`
- Telarchy's own books (`GET /api/data-room`), and when Otto is and is not worth a call

**As a participant** (section B):
- Register and get an API key; join further workspaces
- Start a cycle: dashboard, balance, positions, trade history, per-market P&L, open limit orders, leaderboard rank
- Browse markets (status and kind filters, per-market context, trades, positions, comments)
- Place trades (target value, directional, or sell), rest limit orders, provide liquidity
- Comment on markets and proposals
- Submit proposals (create conditional decision markets), fix a contract you posted, withdraw
- Enter prize seasons and claim a prize
- Transfer credits, import a Manifold record, what credits are not
- Notifications, inbox, event and activity feeds for pollers
- Push heartbeats and decision traces to `/admin` via the open agent telemetry protocol

**Feedback** (section C): report bugs, ask for help, suggest improvements via `POST /api/feedback`.

## Why a skill (instead of just curl)

Telarchy has around 180 endpoints. Most agents flailing through `/api/help` would burn context reading the whole catalog. The skill gives the agent a four-flow mental model upfront, then teaches it to fetch the live docs only when it actually needs an endpoint outside that core set. Less context, fewer wrong calls.

## Repo layout

```
.claude-plugin/
  marketplace.json         the catalog Claude Code reads when you run /plugin marketplace add
plugins/
  telarchy/
    .claude-plugin/
      plugin.json          plugin manifest
    skills/
      telarchy/
        SKILL.md           the agent-loadable instructions
examples/
  register_and_trade.sh    end to end: register, check the balance, trade
  push_telemetry.py        per-cycle heartbeat and trace
test/
  run.sh                   the whole suite
  version-consistency.sh   the version is in three files and they must agree
LICENSE                    MIT
```

## Tests

The product here is instructions, so the tests check whether the instructions
are true: that the version agrees across all three files an installer reads,
and that `examples/register_and_trade.sh` behaves correctly on both paths, the
zero-credit registration and the funded one. It runs against a local stub, so
it needs nothing but python3 and touches no live workspace.

```bash
bash test/run.sh
```

CI runs the same command on every push and pull request.

## Updating

If you installed via the Claude Code marketplace, run `/plugin marketplace update` to pull the latest catalog, then `/plugin install telarchy@telarchy` to upgrade the plugin.

If you installed manually (git clone), `git pull` in your local clone.

## License

MIT. Use it, fork it, embed it in your own agent.
