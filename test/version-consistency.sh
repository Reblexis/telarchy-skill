#!/usr/bin/env bash
# The skill's version is written in three files and they must agree.
#
# `.claude-plugin/marketplace.json` is what the marketplace protocol reads,
# `plugins/telarchy/.claude-plugin/plugin.json` is what an install records, and
# the SKILL.md frontmatter is what an agent loading the file sees. A release
# that bumps two of the three ships an agent that reports a version nobody can
# install, and nothing here caught that before.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mp=$(python3 -c "import json;d=json.load(open('$HERE/.claude-plugin/marketplace.json'));print(d['metadata']['version'])")
mp_plugin=$(python3 -c "import json;d=json.load(open('$HERE/.claude-plugin/marketplace.json'));print(d['plugins'][0]['version'])")
pl=$(python3 -c "import json;d=json.load(open('$HERE/plugins/telarchy/.claude-plugin/plugin.json'));print(d['version'])")
sk=$(awk '/^version:/{print $2; exit}' "$HERE/plugins/telarchy/skills/telarchy/SKILL.md")

echo "marketplace.metadata: $mp"
echo "marketplace.plugins0: $mp_plugin"
echo "plugin.json:          $pl"
echo "SKILL.md frontmatter: $sk"

for v in "$mp_plugin" "$pl" "$sk"; do
  if [ "$v" != "$mp" ]; then
    echo "FAIL: versions disagree (expected $mp everywhere)"
    exit 1
  fi
done
[ -n "$mp" ] || { echo "FAIL: no version found"; exit 1; }
echo "PASS: all four version fields agree at $mp"
