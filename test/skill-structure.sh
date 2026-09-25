#!/usr/bin/env bash
# Each skill is well-formed, the plugin ships exactly the skills the README
# names, and every skill stays small enough to load whole.
#
# The rules come from README.md, "The skills" and "How the skills are written":
# five skills, frontmatter name = directory, a description that says when to
# use it, a body under 500 lines, every references/ file it points at exists,
# and no em or en dashes anywhere (owner rule: they read as machine-written).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$ROOT" <<'PY'
import os, re, sys
root = sys.argv[1]
skills_dir = os.path.join(root, 'plugins/telarchy/skills')
expected = {'telarchy', 'telarchy-evaluate', 'telarchy-manage', 'telarchy-metric-design', 'telarchy-trading'}
fails = []
present = {d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))}
if present != expected:
    fails.append(f'the plugin ships {sorted(present)}, the README names {sorted(expected)}')
for name in sorted(present & expected):
    d = os.path.join(skills_dir, name)
    p = os.path.join(d, 'SKILL.md')
    if not os.path.exists(p):
        fails.append(f'{name}: no SKILL.md'); continue
    text = open(p).read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    if not m:
        fails.append(f'{name}: no frontmatter'); continue
    fm, body = m.group(1), m.group(2)
    nm = re.search(r'^name:\s*(\S+)\s*$', fm, re.M)
    if not nm or nm.group(1) != name:
        fails.append(f'{name}: frontmatter name is {nm.group(1) if nm else None}, must equal the directory')
    desc = re.search(r'^description:\s*(.*?)(?=^\S|\Z)', fm, re.M | re.S)
    dtext = ' '.join(desc.group(1).replace('|', ' ').split()) if desc else ''
    if len(dtext) < 80:
        fails.append(f'{name}: description missing or too short to say when to use it ({len(dtext)} chars)')
    if len(dtext) > 1024:
        fails.append(f'{name}: description is {len(dtext)} chars, the Agent Skills limit is 1024')
    lines = body.count('\n') + 1
    if lines >= 500:
        fails.append(f'{name}: body is {lines} lines, keep it under 500 and move detail to references/')
    for ref in set(re.findall(r'references/[A-Za-z0-9_.\-]+\.md', text)):
        if not os.path.exists(os.path.join(d, ref)):
            fails.append(f'{name}: points at {ref}, which does not exist')
# no dashes anywhere a reader sees
for dirpath, _, files in os.walk(root):
    if '/.git' in dirpath or 'workspace' in dirpath: continue
    for f in files:
        if f.endswith(('.md', '.json', '.sh', '.py')):
            fp = os.path.join(dirpath, f)
            for i, line in enumerate(open(fp, encoding='utf-8', errors='replace'), 1):
                if chr(0x2014) in line or chr(0x2013) in line:
                    fails.append(f'{os.path.relpath(fp, root)}:{i}: em or en dash')
for f in fails: print('FAIL:', f)
if fails: sys.exit(1)
print(f'PASS: {len(expected)} skills well-formed')
PY
