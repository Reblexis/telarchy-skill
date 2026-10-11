#!/usr/bin/env python3
"""telarchy-session's continuation market for one session: post, card, decide.

Contract: ../references/continuation.md. Standard library only. It never trades:
the only writes are POST /api/proposals and a proposal's approve or decline.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

DEFAULT_API = 'https://telarchy.com/api'
DEFAULT_SEED = 100
TIMEOUT = 30
RETRIES = 3
TITLE_MAX = 120
HEADLINE_MAX = 32
NOTE_MAX = 280
ROWS_MAX = 8
MOVERS_MAX = 3


class Fail(Exception):
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


def home(p):
    return os.path.expanduser(p)


def path_env(var, default):
    return home(os.environ.get(var) or default)


def ties_path():
    return path_env('TELARCHY_SESSION_TIES', '~/.config/telarchy/session-ties.jsonl')


def log_path():
    return path_env('TELARCHY_SESSION_CONTINUATIONS', '~/.config/telarchy/session-continuations.jsonl')


def floors_path():
    return path_env('TELARCHY_FLOORS', '~/.config/telarchy/floors.json')


def read_jsonl(path):
    out = []
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict):
                    out.append(rec)
    except OSError:
        pass
    return out


def append_jsonl(path, rec):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')


def last_tie(instance):
    tie = {}
    for rec in read_jsonl(ties_path()):
        if rec.get('aoe_instance_id') == instance:
            tie = rec
    return tie


def session_lines(instance):
    return [r for r in read_jsonl(log_path()) if r.get('aoe_instance_id') == instance]


def current_post(instance):
    posts = [r for r in session_lines(instance) if r.get('event') == 'post']
    return posts[-1] if posts else None


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_iso(s):
    s = s.strip()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def read_env_file(path, var):
    try:
        with open(home(path), encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('export '):
                    line = line[len('export '):].strip()
                name, sep, value = line.partition('=')
                if sep and name.strip() == var:
                    value = value.strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                        value = value[1:-1]
                    return value
    except OSError:
        return None
    return None


def credentials(workspace):
    """(api, key) for a floor: $TELARCHY_API_KEY first, else the floors file."""
    key = os.environ.get('TELARCHY_API_KEY')
    if key:
        return (os.environ.get('TELARCHY_API_URL') or DEFAULT_API).rstrip('/'), key
    floors = {}
    try:
        with open(floors_path(), encoding='utf-8') as f:
            floors = json.load(f)
    except (OSError, ValueError):
        floors = {}
    entry = floors.get(workspace) or floors.get('*')
    if isinstance(entry, dict) and entry.get('key_file') and entry.get('key_var'):
        key = read_env_file(entry['key_file'], entry['key_var'])
        if key:
            return (entry.get('api') or DEFAULT_API).rstrip('/'), key
    raise Fail(f'no Telarchy key for the floor {workspace}: set TELARCHY_API_KEY or add it to {floors_path()}', 2)


class Api:
    def __init__(self, base, key, workspace_id=None):
        self.base = base.rstrip('/')
        self.key = key
        self.workspace_id = workspace_id

    def call(self, method, path, body=None, idempotency_key=None):
        url = self.base + path
        data = json.dumps(body).encode() if body is not None else None
        headers = {'X-Agent-Key': self.key, 'Accept': 'application/json'}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        if self.workspace_id:
            headers['X-Workspace-Id'] = self.workspace_id
        if idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        last = None
        for attempt in range(RETRIES + 1):
            if attempt:
                time.sleep(min(2 * attempt, 6) if not os.environ.get('CONTINUATION_FAST_RETRY') else 0.05)
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    raw = r.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                raw = e.read()
                try:
                    payload = json.loads(raw) if raw else {}
                except ValueError:
                    payload = {'error': raw.decode('utf-8', 'replace')[:300]}
                if e.code >= 500:
                    last = f'{method} {path}: HTTP {e.code} {payload.get("error", "")}'
                    continue
                code = payload.get('code') or ''
                raise Fail(f'{method} {path}: HTTP {e.code} {payload.get("error", "")} {code}'.strip())
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                last = f'{method} {path}: {e}'
                continue
        raise Fail(last or f'{method} {path} failed')


def origin_of(api):
    return api[:-4] if api.endswith('/api') else api


def aoe_title(instance):
    try:
        r = subprocess.run(['aoe', 'session', 'show', instance], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in r.stdout.splitlines():
        if line.startswith('Session:'):
            return line.split(':', 1)[1].strip() or None
    return None


def fmt_num(x):
    if x is None:
        return '?'
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    if abs(x) >= 100:
        return f'{x:.0f}'
    if abs(x) >= 1:
        return f'{x:.2f}'.rstrip('0').rstrip('.')
    return f'{x:.3f}'.rstrip('0').rstrip('.')


def signed(x):
    s = fmt_num(x)
    return s if s.startswith('-') else '+' + s


def cut(s, n):
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


# ---------------------------------------------------------------- post

def cmd_post(args, instance):
    workspace = args.workspace
    api_base, key = credentials(workspace)
    tie = last_tie(instance)
    api = Api(api_base, key)
    mp = api.call('GET', f'/marketplace/{workspace}')
    ws_id = mp.get('workspaceId')
    if not ws_id:
        raise Fail(f'the floor {workspace} has no workspaceId in its marketplace payload')
    api.workspace_id = ws_id

    prev = current_post(instance)
    if prev and prev.get('proposal_id'):
        try:
            p = api.call('GET', f'/proposals/{prev["proposal_id"]}')
        except Fail:
            p = None
        if p and p.get('status') == 'pending':
            print(f'a continuation proposal is already open for this session: {prev.get("url")}')
            return 3
    rnd = (int(prev.get('round') or 1) + 1) if prev else 2

    deadline = parse_iso(args.decide_by) if args.decide_by else now_utc() + timedelta(hours=args.hours)
    if deadline <= now_utc():
        raise Fail('the deadline must be in the future', 2)

    books_by_metric = {}
    names = {}
    for m in mp.get('markets') or []:
        mid, name, res = m.get('metricId'), m.get('metricName'), m.get('resolvesOn')
        if not (mid and name and res):
            continue
        names.setdefault(name, mid)
        books_by_metric.setdefault(mid, []).append(m)

    wanted = args.metric or tie.get('metrics') or list(names)
    chosen, skipped = [], []
    for name in wanted:
        mid = names.get(name)
        later = sorted((b for b in books_by_metric.get(mid, []) if parse_iso(b['resolvesOn']) > deadline),
                       key=lambda b: parse_iso(b['resolvesOn']))
        if not later:
            skipped.append(name)
            continue
        chosen.append(later[0])
    for name in skipped:
        print(f'skipped {name}: no open book settles after {iso(deadline)}', file=sys.stderr)
    if not chosen:
        raise Fail('no session metric has an open book that settles after the deadline; '
                   'nothing posted (try a shorter --hours)', 2)

    seed = args.seed if args.seed is not None else tie.get('continuation_seed')
    seed = float(seed) if seed is not None else float(DEFAULT_SEED)
    each = math.floor(seed / len(chosen) * 100) / 100
    if each <= 0:
        raise Fail('the seed is too small to split over the books', 2)
    each_out = int(each) if each == int(each) else each
    liquidity = [{'metricId': b['metricId'], 'targetDate': b['resolvesOn'], 'amount': each_out} for b in chosen]

    label = args.label or tie.get('title') or aoe_title(instance)
    title = f'Continue this session: round {rnd}'
    if label:
        room = TITLE_MAX - len(title) - 3
        title = f'{title} ({cut(label, room)})'
    description = (args.plan.strip() + '\n\n'
                   'Approved means this working session continues with the plan above; declined means it '
                   'stopped now. So per metric and date the approved price is "continued", the declined price '
                   'is "stopped now", and the difference is what one more round is worth. Posted by the '
                   'telarchy-session skill; the session itself never trades this proposal.')
    body = {'title': title, 'description': description, 'decideBy': iso(deadline), 'liquidity': liquidity}
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return 0

    ikey = f'aoe-{instance}-round-{rnd}'
    created = api.call('POST', '/proposals', body, idempotency_key=ikey)
    number = created.get('number')
    url = f'{origin_of(api_base)}/{workspace}/p/{number}'
    cost = round(each * len(chosen), 2)
    cost = int(cost) if cost == int(cost) else cost
    books = [{'metric_id': b['metricId'], 'metric_name': b['metricName'], 'target_date': b['resolvesOn'],
              'amount': each_out} for b in chosen]
    append_jsonl(log_path(), {
        'at': iso(now_utc()), 'event': 'post', 'aoe_instance_id': instance, 'workspace': workspace,
        'workspace_id': ws_id, 'api': api_base, 'round': rnd, 'proposal_id': created.get('id'),
        'number': number, 'url': url, 'decide_by': iso(deadline), 'seed': cost, 'plan': args.plan.strip(),
        'books': books})
    print(json.dumps({'number': number, 'url': url, 'decide_by': iso(deadline), 'books': books, 'cost': cost}))
    return card(instance, write_aoe=not args.no_aoe)


# ---------------------------------------------------------------- card

def build_card(post, proposal, traders, weights):
    status = proposal.get('status')
    if status == 'declined' and proposal.get('lapsedAt'):
        status = 'lapsed'
    rows, scored, trades_total = [], [], 0
    seeded = {(b['metric_id'], b['target_date'][:10]) for b in post.get('books') or []}
    for i, m in enumerate(proposal.get('markets') or []):
        res = (m.get('resolvesOn') or '')[:10]
        if (m.get('metricId'), res) not in seeded:
            continue
        a, d = m.get('approved') or {}, m.get('declined') or {}
        cont, stop = a.get('consensus'), d.get('consensus')
        trades = int(a.get('tradeCount') or 0) + int(d.get('tradeCount') or 0)
        trades_total += trades
        row = {'name': cut(m.get('metricName') or m.get('metricId') or '?', 80), 'date': res,
               'stopped': stop, 'continued': cont,
               'depth': round(float(a.get('liquidity') or 0) + float(d.get('liquidity') or 0), 2)}
        tr = traders.get((m.get('metricId'), res))
        if tr is not None:
            row['traders'] = tr
        priced = bool(trades and cont is not None and stop is not None)
        move = 0.0
        if priced:
            span = float(m.get('rangeMax') or 0) - float(m.get('rangeMin') or 0)
            move = (cont - stop) / span if span > 0 else (cont - stop)
            w = float((weights or {}).get(m.get('metricName'), 1))
            scored.append((w * move, cont - stop, m.get('metricName') or '?'))
        rows.append((not priced, -abs(move), i, row))
    rows.sort(key=lambda t: t[:3])
    priced_count = sum(1 for t in rows if not t[0])
    rows = [t[3] for t in rows][:ROWS_MAX]

    rnd = post.get('round')
    if status == 'pending':
        if not scored:
            verdict, headline = 'unpriced', 'unpriced: nobody traded yet'
        else:
            score = sum(s for s, _, _ in scored)
            verdict = 'continue' if score > 0 else 'stop'
            top = max(scored, key=lambda t: abs(t[0]))
            headline = cut(f'{signed(top[1])} {top[2]}', HEADLINE_MAX)
    elif status == 'approved':
        verdict, headline = 'continue', f'continued: round {rnd}'
    elif status in ('declined', 'declined_spam'):
        verdict, headline = 'stop', 'session stopped'
    elif status == 'lapsed':
        verdict, headline = 'unpriced', 'lapsed undecided'
    else:
        verdict, headline = 'unpriced', 'withdrawn'

    c = {'verdict': verdict, 'headline': cut(headline, HEADLINE_MAX), 'metrics': rows,
         'source': {'label': cut(f'Telarchy #{post.get("number")}', 40), 'url': post.get('url')}}
    if post.get('plan'):
        c['note'] = cut(post['plan'], NOTE_MAX)
    dl = proposal.get('decideBy') or post.get('decide_by')
    if dl:
        c['decide_by'] = iso(parse_iso(dl))
    stats = {'priced': priced_count, 'books': len(seeded), 'trades': trades_total}
    return c, status, stats


def overview(c, status, post, stats):
    lines = []
    for r in c['metrics'][:stats['priced']][:MOVERS_MAX]:
        diff = r['continued'] - r['stopped']
        extra = []
        if r.get('traders') is not None:
            extra.append(f'{r["traders"]} traders')
        extra.append(f'{fmt_num(r.get("depth"))} cr depth')
        lines.append(f'{r["name"]} {r["date"]}: stopped {fmt_num(r["stopped"])} vs continued '
                     f'{fmt_num(r["continued"])} ({signed(diff)}), {", ".join(extra)}')
    head = f'Continuation {c["source"]["label"].replace("Telarchy ", "")}: {c["verdict"]}, {c["headline"]}'
    if stats['priced']:
        depth = f'priced on {stats["priced"]} of {stats["books"]} books, {stats["trades"]} trades'
    else:
        depth = 'Unpriced: no forecaster has traded it yet'
    tail = c['source']['url']
    if status == 'pending' and c.get('decide_by'):
        tail += f', decide by {c["decide_by"]}'
    return [head] + lines + [depth, tail]


def write_card(instance, c):
    try:
        r = subprocess.run(['aoe', 'session', 'forecast', 'set', '--session', instance],
                           input=json.dumps(c), capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            msg = (r.stderr or r.stdout).strip().splitlines()
            print(f'aoe card not written: {msg[-1] if msg else "exit " + str(r.returncode)}', file=sys.stderr)
    except (OSError, subprocess.SubprocessError) as e:
        print(f'aoe card not written: {e}', file=sys.stderr)


def card(instance, write_aoe=True):
    post = current_post(instance)
    if not post:
        c = {'verdict': 'unpriced', 'headline': 'no continuation proposal yet', 'metrics': []}
        if write_aoe:
            write_card(instance, c)
        print('no continuation proposal yet')
        return 0
    api_base, key = credentials(post['workspace'])
    if post.get('api') and not os.environ.get('TELARCHY_API_KEY'):
        api_base = post['api']
    api = Api(api_base, key, post.get('workspace_id'))
    proposal = api.call('GET', f'/proposals/{post["proposal_id"]}')
    traders = {}
    try:
        mp = api.call('GET', f'/marketplace/{post["workspace"]}')
        for p in mp.get('proposals') or []:
            if p.get('id') == post['proposal_id']:
                for m in p.get('markets') or []:
                    t = [m.get('approvedTraders'), m.get('declinedTraders')]
                    t = [int(x) for x in t if x is not None]
                    if t:
                        traders[(m.get('metricId'), (m.get('resolvesOn') or '')[:10])] = max(t)
    except Fail:
        pass
    c, status, stats = build_card(post, proposal, traders, last_tie(instance).get('weights'))
    if write_aoe:
        write_card(instance, c)
    print('\n'.join(overview(c, status, post, stats)))
    return 0


# ---------------------------------------------------------------- decide

def cmd_decide(args, instance):
    post = current_post(instance)
    if not post:
        raise Fail('this session has no continuation proposal to decide', 2)
    api_base, key = credentials(post['workspace'])
    if post.get('api') and not os.environ.get('TELARCHY_API_KEY'):
        api_base = post['api']
    api = Api(api_base, key, post.get('workspace_id'))
    pid = post['proposal_id']
    if args.decision == 'continue':
        api.call('POST', f'/proposals/{pid}/approve', {})
    else:
        api.call('POST', f'/proposals/{pid}/decline', {'declineReason': 'session stopped'})
    append_jsonl(log_path(), {'at': iso(now_utc()), 'event': 'decide', 'aoe_instance_id': instance,
                              'proposal_id': pid, 'decision': args.decision})
    return card(instance, write_aoe=not args.no_aoe)


def main(argv=None):
    ap = argparse.ArgumentParser(description='telarchy-session continuation market (references/continuation.md)')
    ap.add_argument('--instance', help='aoe session id (default $AOE_INSTANCE_ID)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('post', help='post the continuation proposal')
    p.add_argument('--workspace', required=True)
    p.add_argument('--plan', required=True)
    p.add_argument('--seed', type=float)
    g = p.add_mutually_exclusive_group()
    g.add_argument('--hours', type=float, default=24.0)
    g.add_argument('--decide-by')
    p.add_argument('--metric', action='append')
    p.add_argument('--label')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--no-aoe', action='store_true')
    c = sub.add_parser('card', help='re-read the price, write the aoe card, print the overview')
    c.add_argument('--no-aoe', action='store_true')
    d = sub.add_parser('decide', help="record the user's word: continue approves, stop declines")
    d.add_argument('decision', choices=['continue', 'stop'])
    d.add_argument('--no-aoe', action='store_true')
    args = ap.parse_args(argv)

    instance = (args.instance or os.environ.get('AOE_INSTANCE_ID') or '').strip()
    if not instance:
        print('no session: run inside an aoe session or pass --instance', file=sys.stderr)
        return 2
    try:
        if args.cmd == 'post':
            return cmd_post(args, instance)
        if args.cmd == 'card':
            return card(instance, write_aoe=not args.no_aoe)
        return cmd_decide(args, instance)
    except Fail as e:
        print(str(e), file=sys.stderr)
        return e.code


if __name__ == '__main__':
    sys.exit(main())
