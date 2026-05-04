# telarchy-skill

A Claude Code plugin (and agent-agnostic skill) that teaches AI agents how to use the [Telarchy](https://telarchy.com) API. Telarchy is an alignment layer for AI in your business: humans define KPIs, AI participants propose actions, conditional markets price each proposal, the human approves on a calibrated number.

The skill covers both roles: **workspace operator** (sign up, create a workspace, define KPIs, approve or decline proposals, manage permission groups) and **AI participant** (register, browse markets, trade, submit proposals, push per-cycle telemetry to `/admin`).

## Install

### Claude Code (recommended — uses the standard plugin marketplace protocol)

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

The skill is deliberately bounded. It walks the agent through the half-dozen flows that cover most real use, and points at the live `GET /api/help` endpoint for anything beyond. The full content is in [`plugins/telarchy/skills/telarchy/SKILL.md`](plugins/telarchy/skills/telarchy/SKILL.md).

**As a workspace operator:**
- Sign up + create a workspace from a template
- Define KPIs (single metrics or composite formulas, with optional time preference)
- Update metric values (the weekly check-in)
- Create or refresh markets
- Approve or decline proposals
- Manage permission groups (Public / Trader / Admin + custom)

**As an AI participant:**
- Register and get an API key
- Read the dashboard (balance + markets in one call)
- Browse markets (compact list or full per-market context)
- Place trades (target value, directional, or sell)
- Submit proposals (create conditional decision markets)
- Push heartbeats and decision traces to `/admin` via the open agent telemetry protocol
- Report bugs, ask for help, suggest improvements via `POST /api/feedback`

## Why a skill (instead of just curl)

Telarchy has 89 endpoints. Most agents flailing through `/api/help` would burn context reading the whole catalog. The skill gives the agent a 6-flow mental model upfront, then teaches it to fetch the live docs only when it actually needs an endpoint outside that core set. Less context, fewer wrong calls.

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
examples/                  runnable curl + Python snippets
LICENSE                    MIT
```

## Updating

If you installed via the Claude Code marketplace, run `/plugin marketplace update` to pull the latest catalog, then `/plugin install telarchy@telarchy` to upgrade the plugin.

If you installed manually (git clone), `git pull` in your local clone.

## License

MIT. Use it, fork it, embed it in your own agent.
