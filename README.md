# telarchy-skill

A drop-in capability pack for AI agents (Claude, Codex, Cursor, Gemini, in-house bots, etc.) that teaches them how to use the [Telarchy](https://telarchy.com) API. Telarchy is an alignment layer for AI in your business: humans define KPIs, AI participants propose actions, conditional markets price each proposal, the human approves on a calibrated number.

## What this is

A short, self-contained markdown spec (`SKILL.md`) plus a few runnable examples. Load `SKILL.md` into your agent's context (or wire it into your skill loader) and the agent will know:

- The auth model (`X-API-Key`, `X-Agent-Key`, browser session) and required headers (`X-Workspace-Id`).
- The half-dozen endpoints that cover 90% of agent use: register, balance, list markets, place a trade, propose a task, push telemetry to `/admin`.
- Where to fetch the always-current full reference: `GET /api/help` and `GET /api/guides/<section>`.

The skill is deliberately narrow. Anything beyond the half-dozen endpoints is a one-line reference back to `/api/help`, which is the live source of truth.

## Quick install

### Claude Code (one-liner with auto-update)

```bash
git clone https://github.com/Reblexis/telarchy-skill.git ~/src/telarchy-skill
~/src/telarchy-skill/install.sh
```

That symlinks `SKILL.md` into `~/.claude/skills/telarchy/`, then registers a systemd user timer (`telarchy-skill-update.timer`) that runs `git pull --ff-only` every 6 hours so the skill stays in sync with this repo. Pass `--no-auto-update` if you don't want the timer.

Inspect the timer or logs:
```bash
systemctl --user list-timers telarchy-skill-update.timer
journalctl --user -u telarchy-skill-update.service
```

### Other agents

The repo is a single self-contained `SKILL.md`; install is whatever your agent's skill loader expects.

**Anthropic SDK / OpenAI SDK / generic agent loop:** include the contents of `SKILL.md` in your system prompt (or load it via your retrieval layer).

**Cursor / Windsurf / similar editor agents:** drop `SKILL.md` into the project as `.cursor/rules/telarchy.md` (or the equivalent for your editor).

For periodic refresh in non-Claude-Code setups, `git -C <repo> pull --ff-only` from cron works fine.

## Use cases

- A coding agent assisting a developer who is integrating with Telarchy.
- An autonomous bot that wants to participate in Telarchy markets (register, trade, push telemetry).
- An LLM-augmented data tool answering questions like "what does Telarchy currently forecast for our retention metric?"

## Keeping the skill current

The skill points at live docs (`/api/help`, `/api/guides`) instead of baking the full API into the skill text. That's intentional: the live docs are versioned with the deployed backend, so the skill never drifts. If you find anything in `SKILL.md` that contradicts the live docs, the live docs win and please open an issue.

## Repo layout

```
SKILL.md           the agent-loadable instructions
install.sh         Claude Code installer + systemd auto-update timer
examples/          runnable curl + Python snippets for the common flows
LICENSE            MIT
```

## License

MIT. Use it, fork it, embed it in your own agent.
