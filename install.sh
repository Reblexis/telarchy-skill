#!/usr/bin/env bash
# Installs the Telarchy skill into Claude Code (~/.claude/skills/telarchy/)
# and (optionally) wires a systemd user timer that pulls upstream every 6 hours
# so the skill stays current without manual git-pulls.
#
# Re-run any time, idempotent. Pass --no-auto-update to skip the timer.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WANT_AUTO_UPDATE=1
for arg in "$@"; do
  case "$arg" in
    --no-auto-update) WANT_AUTO_UPDATE=0 ;;
    -h|--help)
      echo "Usage: ./install.sh [--no-auto-update]"
      echo "  Installs SKILL.md to ~/.claude/skills/telarchy/ and (by default)"
      echo "  sets up a systemd user timer to git-pull every 6 hours."
      exit 0
      ;;
  esac
done

# 1. Symlink SKILL.md into the Claude Code skills directory.
SKILL_DIR="${HOME}/.claude/skills/telarchy"
mkdir -p "$SKILL_DIR"
ln -sf "${REPO_DIR}/SKILL.md" "${SKILL_DIR}/SKILL.md"
echo "Linked: ${SKILL_DIR}/SKILL.md -> ${REPO_DIR}/SKILL.md"

if [ "$WANT_AUTO_UPDATE" = "0" ]; then
  echo "Skipping auto-update setup (--no-auto-update)."
  exit 0
fi

# 2. Detect systemd user services. If unavailable, point user at cron fallback.
if ! command -v systemctl >/dev/null 2>&1 || ! systemctl --user --version >/dev/null 2>&1; then
  cat <<EOF
systemctl --user not available; skipping systemd timer setup.
For periodic updates, add this cron line:
  0 */6 * * * /usr/bin/git -C ${REPO_DIR} pull --ff-only --quiet
EOF
  exit 0
fi

# 3. Drop the systemd user unit + timer.
UNIT_DIR="${HOME}/.config/systemd/user"
mkdir -p "$UNIT_DIR"

cat > "${UNIT_DIR}/telarchy-skill-update.service" <<EOF
[Unit]
Description=Pull latest Telarchy skill (Reblexis/telarchy-skill)
Documentation=https://github.com/Reblexis/telarchy-skill
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=${REPO_DIR}
# --ff-only refuses to merge: a fast-forward succeeds, anything divergent
# fails visibly so we don't silently overwrite local edits.
ExecStart=/usr/bin/git -C ${REPO_DIR} pull --ff-only --quiet
Environment=PATH=/usr/bin:/bin:/usr/local/bin

[Install]
WantedBy=default.target
EOF

cat > "${UNIT_DIR}/telarchy-skill-update.timer" <<EOF
[Unit]
Description=Refresh Telarchy skill from GitHub every 6 hours
Documentation=https://github.com/Reblexis/telarchy-skill

[Timer]
# Fire 5 min after boot, then every 6 hours. Persistent=true catches up
# missed runs after sleep / reboot.
OnBootSec=5min
OnUnitActiveSec=6h
Persistent=true
Unit=telarchy-skill-update.service

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now telarchy-skill-update.timer
echo "Auto-update enabled. Next run: $(systemctl --user list-timers telarchy-skill-update.timer --no-pager | awk 'NR==2 {print $1, $2, $3}')"
echo "Logs: journalctl --user -u telarchy-skill-update.service"
