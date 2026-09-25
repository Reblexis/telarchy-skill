#!/usr/bin/env bash
# The plugin's version is written in several files and they must all agree.
#
# `.claude-plugin/marketplace.json` is what the marketplace protocol reads,
# `plugins/telarchy/.claude-plugin/plugin.json` is what an install records, and
# every skill's SKILL.md frontmatter is what an agent loading that file sees. A
# release that bumps some of them ships an agent that reports a version nobody
# can install.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mp=$(python3 -c "import json;d=json.load(open('$HERE/.claude-plugin/marketplace.json'));print(d['metadata']['version'])")
[ -n "$mp" ] || { echo "FAIL: no version in marketplace.json metadata"; exit 1; }
echo "marketplace.metadata: $mp"
fails=0
check() {  # $1 label, $2 value
  echo "$1: $2"
  if [ "$2" != "$mp" ]; then echo "  FAIL: expected $mp"; fails=$((fails + 1)); fi
}
check "marketplace.plugins0" "$(python3 -c "import json;d=json.load(open('$HERE/.claude-plugin/marketplace.json'));print(d['plugins'][0]['version'])")"
check "plugin.json" "$(python3 -c "import json;d=json.load(open('$HERE/plugins/telarchy/.claude-plugin/plugin.json'));print(d['version'])")"
n=0
for f in "$HERE"/plugins/telarchy/skills/*/SKILL.md; do
  n=$((n + 1))
  v=$(awk 'NR==1 && $0!="---"{exit} NR>1 && /^---$/{exit} /^version:/{print $2; exit}' "$f")
  check "${f#$HERE/}" "${v:-<missing>}"
done
[ "$n" -gt 0 ] || { echo "FAIL: no skills found"; exit 1; }
[ "$fails" -eq 0 ] || { echo "FAIL: $fails version field(s) disagree"; exit 1; }
echo "PASS: all $((n + 2)) version fields agree at $mp"
