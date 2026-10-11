"""Behavior of telarchy-session's continuation helper, against a local stub.

The contract is plugins/telarchy/skills/telarchy-session/references/continuation.md.
Every test runs the real script as a subprocess, the way an agent does, against
a stub of the Telarchy API and a stub `aoe` that records the card it is given.
The rule the helper exists for (Viktor, task #240, 2026-10-09: "actually upload
the telarchy propossl and show the status inside sessiosn") is that a tied
session really posts its continuation proposal and its price reaches the card;
the rules it must never break are that it never trades its own continuation
market and never has two open at once.

Run: python3 test/test_continuation.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'plugins/telarchy/skills/telarchy-session/scripts/continuation.py')
INSTANCE = 'abc123def456'
KEY = 'tk_test_key'


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


NOW = datetime.now(timezone.utc)
SOON = iso(NOW + timedelta(hours=2))        # settles before a 24 h deadline
LATER = iso(NOW + timedelta(days=3))        # first date after a 24 h deadline
LATEST = iso(NOW + timedelta(days=60))      # also after, but not the earliest


class Stub:
    """A small in-memory Telarchy: one floor, its open books, proposals."""

    def __init__(self):
        self.requests = []          # (method, path, headers, body)
        self.fail_next_posts = 0    # answer this many POST /api/proposals with 502 first
        self.proposals = {}
        self.posted_keys = {}       # Idempotency-Key -> proposal id
        self.markets = [
            {'metricId': 'm-rev', 'metricName': 'Revenue (USD)', 'resolvesOn': SOON, 'rangeMin': 0, 'rangeMax': 1000},
            {'metricId': 'm-rev', 'metricName': 'Revenue (USD)', 'resolvesOn': LATEST, 'rangeMin': 0, 'rangeMax': 1000},
            {'metricId': 'm-rev', 'metricName': 'Revenue (USD)', 'resolvesOn': LATER, 'rangeMin': 0, 'rangeMax': 1000},
            {'metricId': 'm-users', 'metricName': 'Active users', 'resolvesOn': LATER, 'rangeMin': 0, 'rangeMax': 50},
            {'metricId': 'm-daily', 'metricName': 'Daily signups', 'resolvesOn': SOON, 'rangeMin': 0, 'rangeMax': 10},
        ]

    def add_proposal(self, pid, number, status='pending', pairs=None, decide_by=None):
        self.proposals[pid] = {
            'id': pid, 'number': number, 'status': status,
            'decideBy': decide_by or iso(NOW + timedelta(hours=24)),
            'markets': pairs if pairs is not None else [],
        }

    def pair(self, metric_id, name, resolves, approved, declined, a_trades=0, d_trades=0,
             rmin=0, rmax=1000, a_traders=None, d_traders=None):
        return {
            'metricId': metric_id, 'metricName': name, 'resolvesOn': resolves,
            'rangeMin': rmin, 'rangeMax': rmax,
            'approved': {'consensus': approved, 'liquidity': 500.0, 'tradeCount': a_trades},
            'declined': {'consensus': declined, 'liquidity': 500.0, 'tradeCount': d_trades},
            'delta': approved - declined,
            '_traders': (a_traders if a_traders is not None else a_trades,
                         d_traders if d_traders is not None else d_trades),
        }


def make_handler(stub):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body):
            raw = json.dumps(body).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _record(self):
            n = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(n) if n else b''
            body = json.loads(raw) if raw else None
            stub.requests.append((self.command, self.path, dict(self.headers), body))
            return body

        def _authed(self):
            return self.headers.get('X-Agent-Key') == KEY

        def do_GET(self):
            self._record()
            if not self._authed():
                return self._send(401, {'error': 'unauthorized', 'code': 'unauthorized'})
            path = self.path.split('?')[0]
            if path == '/api/marketplace/acme':
                props = []
                for p in stub.proposals.values():
                    props.append({'id': p['id'], 'number': p['number'], 'status': p['status'], 'markets': [
                        {'metricId': m['metricId'], 'resolvesOn': m['resolvesOn'],
                         'approvedTraders': m['_traders'][0], 'declinedTraders': m['_traders'][1]}
                        for m in p['markets']]})
                return self._send(200, {'workspaceId': 'ws-1', 'slug': 'acme', 'markets': stub.markets,
                                        'proposals': props})
            if path.startswith('/api/proposals/'):
                pid = path.rsplit('/', 1)[1]
                p = stub.proposals.get(pid)
                if not p:
                    return self._send(404, {'error': 'not found', 'code': 'not_found'})
                out = dict(p)
                out['markets'] = [{k: v for k, v in m.items() if k != '_traders'} for m in p['markets']]
                return self._send(200, out)
            return self._send(404, {'error': 'no route', 'code': 'not_found'})

        def do_POST(self):
            body = self._record()
            if not self._authed():
                return self._send(401, {'error': 'unauthorized', 'code': 'unauthorized'})
            if self.headers.get('X-Workspace-Id') != 'ws-1':
                return self._send(400, {'error': 'workspace', 'code': 'bad_workspace'})
            path = self.path.split('?')[0]
            if path == '/api/proposals':
                if stub.fail_next_posts > 0:
                    stub.fail_next_posts -= 1
                    # the server did create it, then the answer was lost
                    key = self.headers.get('Idempotency-Key')
                    if key and key not in stub.posted_keys:
                        self._create(body, key)
                    return self._send(502, {'error': 'bad gateway'})
                key = self.headers.get('Idempotency-Key')
                if key in stub.posted_keys:
                    p = stub.proposals[stub.posted_keys[key]]
                    return self._send(201, {'id': p['id'], 'number': p['number']})
                p = self._create(body, key)
                return self._send(201, {'id': p['id'], 'number': p['number']})
            if path.endswith('/approve') or path.endswith('/decline'):
                pid = path.split('/')[3]
                p = stub.proposals.get(pid)
                if not p:
                    return self._send(404, {'error': 'not found', 'code': 'not_found'})
                if p['status'] != 'pending':
                    return self._send(409, {'error': 'not pending', 'code': 'not_pending', 'status': p['status']})
                p['status'] = 'approved' if path.endswith('/approve') else 'declined'
                return self._send(200, {'ok': True})
            return self._send(404, {'error': 'no route', 'code': 'not_found'})

        def _create(self, body, key):
            number = 100 + len(stub.proposals)
            pid = f'p-{number}'
            pairs = []
            for b in body.get('liquidity') or []:
                mk = next(m for m in stub.markets if m['metricId'] == b['metricId'] and m['resolvesOn'] == b['targetDate'])
                pairs.append(stub.pair(b['metricId'], mk['metricName'], b['targetDate'], 10.0, 10.0,
                                       rmin=mk['rangeMin'], rmax=mk['rangeMax']))
            stub.add_proposal(pid, number, pairs=pairs, decide_by=body.get('decideBy'))
            stub.proposals[pid]['title'] = body.get('title')
            if key:
                stub.posted_keys[key] = pid
            return stub.proposals[pid]
    return H


class Base(unittest.TestCase):
    def setUp(self):
        self.stub = Stub()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.stub))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = f'http://127.0.0.1:{self.server.server_port}/api'
        self.tmp = tempfile.mkdtemp()
        self.ties = os.path.join(self.tmp, 'ties.jsonl')
        self.conts = os.path.join(self.tmp, 'continuations.jsonl')
        self.floors = os.path.join(self.tmp, 'floors.json')
        self.card_file = os.path.join(self.tmp, 'card.json')
        bindir = os.path.join(self.tmp, 'bin')
        os.mkdir(bindir)
        # a stub aoe: records the card on stdin, fails when AOE_STUB_FAIL is set
        with open(os.path.join(bindir, 'aoe'), 'w') as f:
            f.write('#!/bin/sh\n'
                    'if [ "$1 $2" = "session show" ]; then echo "Session: Fix the pricing page"; exit 0; fi\n'
                    '[ -n "$AOE_STUB_FAIL" ] && { echo "aoe exploded" >&2; exit 1; }\n'
                    f'echo "$@" > "{self.card_file}.args"\n'
                    f'cat > "{self.card_file}"\n')
        os.chmod(os.path.join(bindir, 'aoe'), 0o755)
        self.env = {
            'PATH': bindir + os.pathsep + os.environ.get('PATH', ''),
            'HOME': self.tmp,
            'AOE_INSTANCE_ID': INSTANCE,
            'TELARCHY_API_URL': self.api,
            'TELARCHY_API_KEY': KEY,
            'TELARCHY_SESSION_TIES': self.ties,
            'TELARCHY_SESSION_CONTINUATIONS': self.conts,
            'TELARCHY_FLOORS': self.floors,
        }

    def tearDown(self):
        self.server.shutdown()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args, env=None):
        e = dict(self.env)
        e.update(env or {})
        e = {k: v for k, v in e.items() if v is not None}
        return subprocess.run([sys.executable, SCRIPT, *args], env=e, capture_output=True, text=True, timeout=60)

    def tie(self, **fields):
        rec = {'aoe_instance_id': INSTANCE, 'workspace': 'acme', 'answered': True}
        rec.update(fields)
        with open(self.ties, 'a') as f:
            f.write(json.dumps(rec) + '\n')

    def log_post(self, pid, number, round_=2, books=None, plan='Ship the pricing page.'):
        rec = {'at': iso(NOW), 'event': 'post', 'aoe_instance_id': INSTANCE, 'workspace': 'acme',
               'workspace_id': 'ws-1', 'api': self.api, 'round': round_, 'proposal_id': pid, 'number': number,
               'url': f'http://127.0.0.1/acme/p/{number}', 'decide_by': iso(NOW + timedelta(hours=24)),
               'seed': 100, 'plan': plan,
               'books': books if books is not None else [
                   {'metric_id': 'm-rev', 'metric_name': 'Revenue (USD)', 'target_date': LATER, 'amount': 50}]}
        with open(self.conts, 'a') as f:
            f.write(json.dumps(rec) + '\n')

    def posts(self):
        return [r for r in self.stub.requests if r[0] == 'POST']

    def card(self):
        with open(self.card_file) as f:
            return json.load(f)

    def log_lines(self):
        if not os.path.exists(self.conts):
            return []
        return [json.loads(l) for l in open(self.conts) if l.strip()]


class Post(Base):
    def test_a_tied_session_really_posts_its_continuation_proposal(self):
        self.tie()
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'Rewrite the pricing page.')
        self.assertEqual(r.returncode, 0, r.stderr)
        posts = self.posts()
        self.assertEqual(len(posts), 1)
        method, path, headers, body = posts[0]
        self.assertEqual(path, '/api/proposals')
        self.assertEqual(headers.get('X-Agent-Key'), KEY)
        self.assertEqual(headers.get('X-Workspace-Id'), 'ws-1')
        self.assertTrue(body['title'].startswith('Continue this session: round 2'))
        self.assertIn('Rewrite the pricing page.', body['description'])
        self.assertIn('approved', body['description'].lower())
        self.assertIn('stopped now', body['description'].lower())
        out = json.loads(r.stdout.splitlines()[0])
        self.assertEqual(out['number'], 100)
        self.assertTrue(out['url'].endswith('/acme/p/100'))

    def test_the_first_proposal_is_round_2_and_its_idempotency_key_names_session_and_round(self):
        self.tie()
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        headers = self.posts()[0][2]
        self.assertEqual(headers.get('Idempotency-Key'), f'aoe-{INSTANCE}-round-2')

    def test_each_metric_seeds_only_its_earliest_book_settling_after_the_deadline(self):
        self.tie(metrics=['Revenue (USD)', 'Active users'])
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x', '--seed', '100')
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.posts()[0][3]
        self.assertNotIn('liquiditySubsidy', body)
        books = sorted((b['metricId'], b['targetDate'], b['amount']) for b in body['liquidity'])
        self.assertEqual(books, [('m-rev', LATER, 50), ('m-users', LATER, 50)])

    def test_a_metric_whose_books_all_settle_before_the_deadline_is_skipped_and_named(self):
        self.tie(metrics=['Revenue (USD)', 'Daily signups'])
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x', '--seed', '90')
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.posts()[0][3]
        self.assertEqual([(b['metricId'], b['amount']) for b in body['liquidity']], [('m-rev', 90)])
        self.assertIn('Daily signups', r.stderr)

    def test_no_book_after_the_deadline_posts_nothing(self):
        self.tie(metrics=['Daily signups'])
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.posts(), [])
        self.assertEqual(self.log_lines(), [])

    def test_a_shorter_deadline_reaches_an_earlier_book(self):
        self.tie(metrics=['Daily signups'])
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x', '--hours', '1')
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.posts()[0][3]
        self.assertEqual([(b['metricId'], b['targetDate']) for b in body['liquidity']], [('m-daily', SOON)])
        dl = datetime.strptime(body['decideBy'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        self.assertLess(abs((dl - (NOW + timedelta(hours=1))).total_seconds()), 120)

    def test_without_named_metrics_every_metric_with_an_open_book_after_the_deadline_is_seeded(self):
        self.tie()
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x', '--seed', '100')
        body = self.posts()[0][3]
        self.assertEqual(sorted(b['metricId'] for b in body['liquidity']), ['m-rev', 'm-users'])

    def test_metric_flag_wins_over_the_tie(self):
        self.tie(metrics=['Revenue (USD)', 'Active users'])
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x', '--metric', 'Active users')
        body = self.posts()[0][3]
        self.assertEqual([b['metricId'] for b in body['liquidity']], ['m-users'])

    def test_the_seed_comes_from_the_tie_else_defaults_to_100_credits(self):
        self.tie(continuation_seed=40, metrics=['Revenue (USD)'])
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.assertEqual(self.posts()[0][3]['liquidity'][0]['amount'], 40)

    def test_default_seed_is_100_credits(self):
        self.tie(metrics=['Revenue (USD)', 'Active users'])
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.assertEqual(sum(b['amount'] for b in self.posts()[0][3]['liquidity']), 100)
        self.assertEqual(json.loads(r.stdout.splitlines()[0])['cost'], 100)

    def test_the_seed_is_split_evenly_and_rounded_down_to_a_hundredth(self):
        self.tie(metrics=['Revenue (USD)', 'Active users'])
        self.stub.markets.append({'metricId': 'm-nps', 'metricName': 'NPS', 'resolvesOn': LATER, 'rangeMin': 0, 'rangeMax': 100})
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x', '--seed', '100', '--metric', 'Revenue (USD)',
                     '--metric', 'Active users', '--metric', 'NPS')
        self.assertEqual([b['amount'] for b in self.posts()[0][3]['liquidity']], [33.33, 33.33, 33.33])

    def test_only_one_continuation_proposal_is_open_per_session(self):
        self.tie()
        self.stub.add_proposal('p-7', 7, status='pending')
        self.log_post('p-7', 7)
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.assertEqual(r.returncode, 3)
        self.assertEqual(self.posts(), [])
        self.assertIn('/acme/p/7', r.stdout + r.stderr)

    def test_after_the_last_one_lapsed_the_next_is_the_following_round_with_its_own_key(self):
        self.tie()
        self.stub.add_proposal('p-7', 7, status='lapsed')
        self.log_post('p-7', 7, round_=2)
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.assertEqual(r.returncode, 0, r.stderr)
        _, _, headers, body = self.posts()[0]
        self.assertTrue(body['title'].startswith('Continue this session: round 3'))
        self.assertEqual(headers['Idempotency-Key'], f'aoe-{INSTANCE}-round-3')

    def test_the_title_carries_the_session_label_from_the_tie_else_the_aoe_title(self):
        self.tie(title='Fix the agents page')
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.assertEqual(self.posts()[0][3]['title'], 'Continue this session: round 2 (Fix the agents page)')

    def test_the_title_falls_back_to_the_aoe_session_title(self):
        self.tie()
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.assertEqual(self.posts()[0][3]['title'], 'Continue this session: round 2 (Fix the pricing page)')

    def test_the_title_is_at_most_120_characters(self):
        self.tie(title='y' * 300)
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        title = self.posts()[0][3]['title']
        self.assertLessEqual(len(title), 120)
        self.assertTrue(title.startswith('Continue this session: round 2 ('))

    def test_a_lost_answer_is_retried_with_the_same_key_and_never_posts_twice(self):
        self.tie()
        self.stub.fail_next_posts = 1
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.assertEqual(r.returncode, 0, r.stderr)
        posts = self.posts()
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0][2]['Idempotency-Key'], posts[1][2]['Idempotency-Key'])
        self.assertEqual(len(self.stub.proposals), 1)

    def test_the_post_is_logged_and_the_card_is_written_in_the_same_run(self):
        self.tie()
        self.run_cli('post', '--workspace', 'acme', '--plan', 'Rewrite the pricing page.')
        lines = self.log_lines()
        self.assertEqual(len(lines), 1)
        rec = lines[0]
        for k in ('at', 'event', 'aoe_instance_id', 'workspace', 'workspace_id', 'api', 'round', 'proposal_id',
                  'number', 'url', 'decide_by', 'seed', 'plan', 'books'):
            self.assertIn(k, rec)
        self.assertEqual(rec['event'], 'post')
        self.assertEqual(rec['aoe_instance_id'], INSTANCE)
        card = self.card()
        self.assertEqual(card['verdict'], 'unpriced')
        self.assertTrue(card['source']['url'].endswith('/acme/p/100'))

    def test_dry_run_posts_nothing_and_logs_nothing(self):
        self.tie()
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x', '--dry-run')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.posts(), [])
        self.assertEqual(self.log_lines(), [])
        self.assertIn('Continue this session', r.stdout)

    def test_an_api_error_is_printed_and_exits_1(self):
        self.tie()
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x', env={'TELARCHY_API_KEY': 'wrong'})
        self.assertEqual(r.returncode, 1)
        self.assertIn('unauthorized', r.stderr)
        self.assertEqual(self.log_lines(), [])


class Keys(Base):
    def test_without_a_session_id_it_refuses(self):
        r = self.run_cli('card', env={'AOE_INSTANCE_ID': None})
        self.assertEqual(r.returncode, 2)

    def test_the_floors_file_supplies_the_api_and_key_for_the_floor(self):
        keyfile = os.path.join(self.tmp, 'me.env')
        with open(keyfile, 'w') as f:
            f.write('# my key\nexport ACME_KEY="%s"\n' % KEY)
        with open(self.floors, 'w') as f:
            json.dump({'acme': {'api': self.api, 'key_file': keyfile, 'key_var': 'ACME_KEY'}}, f)
        self.tie()
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x',
                         env={'TELARCHY_API_KEY': None, 'TELARCHY_API_URL': None})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.posts()[0][2]['X-Agent-Key'], KEY)

    def test_the_floors_file_star_entry_is_the_fallback(self):
        keyfile = os.path.join(self.tmp, 'me.env')
        with open(keyfile, 'w') as f:
            f.write('ACME_KEY=%s\n' % KEY)
        with open(self.floors, 'w') as f:
            json.dump({'*': {'api': self.api, 'key_file': keyfile, 'key_var': 'ACME_KEY'}}, f)
        self.tie()
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x',
                         env={'TELARCHY_API_KEY': None, 'TELARCHY_API_URL': None})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_key_anywhere_exits_2_naming_the_floor(self):
        self.tie()
        r = self.run_cli('post', '--workspace', 'acme', '--plan', 'x',
                         env={'TELARCHY_API_KEY': None, 'TELARCHY_API_URL': None})
        self.assertEqual(r.returncode, 2)
        self.assertIn('acme', r.stderr)
        self.assertEqual(self.stub.requests, [])


class Card(Base):
    def books(self):
        return [{'metric_id': 'm-rev', 'metric_name': 'Revenue (USD)', 'target_date': LATER, 'amount': 50},
                {'metric_id': 'm-users', 'metric_name': 'Active users', 'target_date': LATER, 'amount': 50}]

    def test_no_proposal_yet_reads_unpriced_no_continuation_proposal_yet(self):
        self.tie()
        r = self.run_cli('card')
        self.assertEqual(r.returncode, 0, r.stderr)
        card = self.card()
        self.assertEqual(card['verdict'], 'unpriced')
        self.assertEqual(card['headline'], 'no continuation proposal yet')
        self.assertEqual(r.stdout.strip(), 'no continuation proposal yet')

    def test_an_untraded_proposal_is_unpriced_never_no_difference(self):
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[s.pair('m-rev', 'Revenue (USD)', LATER, 10, 10)])
        self.log_post('p-7', 7)
        self.run_cli('card')
        card = self.card()
        self.assertEqual(card['verdict'], 'unpriced')
        self.assertNotIn('+0', card['headline'])

    def test_a_priced_gain_reads_continue_with_both_worlds_on_the_card(self):
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[s.pair('m-rev', 'Revenue (USD)', LATER, 120, 100, a_trades=3, d_trades=2)])
        self.log_post('p-7', 7)
        r = self.run_cli('card')
        self.assertEqual(r.returncode, 0, r.stderr)
        card = self.card()
        self.assertEqual(card['verdict'], 'continue')
        self.assertTrue(card['headline'].startswith('+20'))
        self.assertLessEqual(len(card['headline']), 32)
        row = card['metrics'][0]
        self.assertEqual(row['name'], 'Revenue (USD)')
        self.assertEqual(row['date'], LATER[:10])
        self.assertEqual(row['stopped'], 100)
        self.assertEqual(row['continued'], 120)
        self.assertEqual(row['traders'], 3)
        self.assertEqual(row['depth'], 1000)
        self.assertEqual(card['source']['label'], 'Telarchy #7')
        self.assertIn('decide_by', card)
        self.assertEqual(card['note'], 'Ship the pricing page.')

    def test_a_priced_loss_reads_stop(self):
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[s.pair('m-rev', 'Revenue (USD)', LATER, 90, 100, a_trades=1)])
        self.log_post('p-7', 7)
        self.run_cli('card')
        self.assertEqual(self.card()['verdict'], 'stop')
        self.assertTrue(self.card()['headline'].startswith('-10'))

    def test_traded_but_no_difference_reads_stop(self):
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[s.pair('m-rev', 'Revenue (USD)', LATER, 100, 100, a_trades=2)])
        self.log_post('p-7', 7)
        self.run_cli('card')
        self.assertEqual(self.card()['verdict'], 'stop')

    def test_mixed_rows_are_weighed_by_share_of_range(self):
        # +20 of a 0..1000 range (2%) against -5 of a 0..50 range (10%): stop
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[
            s.pair('m-rev', 'Revenue (USD)', LATER, 120, 100, a_trades=1),
            s.pair('m-users', 'Active users', LATER, 20, 25, a_trades=1, rmax=50)])
        self.log_post('p-7', 7, books=self.books())
        self.run_cli('card')
        card = self.card()
        self.assertEqual(card['verdict'], 'stop')
        self.assertIn('Active users', card['headline'])

    def test_the_users_weights_from_the_tie_steer_the_verdict(self):
        self.tie(weights={'Revenue (USD)': 10, 'Active users': 1})
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[
            s.pair('m-rev', 'Revenue (USD)', LATER, 120, 100, a_trades=1),
            s.pair('m-users', 'Active users', LATER, 20, 25, a_trades=1, rmax=50)])
        self.log_post('p-7', 7, books=self.books())
        self.run_cli('card')
        card = self.card()
        self.assertEqual(card['verdict'], 'continue')
        self.assertIn('Revenue', card['headline'])

    def test_only_the_seeded_books_become_rows(self):
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[
            s.pair('m-rev', 'Revenue (USD)', LATER, 120, 100, a_trades=1),
            s.pair('m-rev', 'Revenue (USD)', LATEST, 300, 100, a_trades=1),
            s.pair('m-other', 'Something else', LATER, 1, 900, a_trades=9)])
        self.log_post('p-7', 7)
        self.run_cli('card')
        rows = self.card()['metrics']
        self.assertEqual([(r['name'], r['date']) for r in rows], [('Revenue (USD)', LATER[:10])])

    def test_decided_and_lapsed_proposals(self):
        cases = [('approved', 'continue', 'continued: round 2'), ('declined', 'stop', 'session stopped'),
                 ('lapsed', 'unpriced', 'lapsed undecided'), ('withdrawn', 'unpriced', 'withdrawn')]
        self.tie()
        for status, verdict, headline in cases:
            with self.subTest(status=status):
                self.stub.proposals.clear()
                self.stub.add_proposal('p-7', 7, status=status,
                                       pairs=[self.stub.pair('m-rev', 'Revenue (USD)', LATER, 120, 100, a_trades=1)])
                if not self.log_lines():
                    self.log_post('p-7', 7)
                self.run_cli('card')
                self.assertEqual(self.card()['verdict'], verdict)
                self.assertEqual(self.card()['headline'], headline)

    def test_the_card_carries_only_fields_aoe_accepts_within_its_limits(self):
        self.tie()
        s = self.stub
        pairs = [s.pair('m-rev', 'Revenue (USD) ' + 'z' * 100, LATER, 120, 100, a_trades=1)]
        s.add_proposal('p-7', 7, pairs=pairs)
        self.log_post('p-7', 7, plan='p' * 1000)
        self.run_cli('card')
        card = self.card()
        self.assertTrue(set(card) <= {'verdict', 'headline', 'metrics', 'note', 'source', 'decide_by'})
        self.assertNotIn('updated_at', card)
        self.assertLessEqual(len(card['headline']), 32)
        self.assertLessEqual(len(card['note']), 280)
        self.assertLessEqual(len(card['metrics']), 8)
        for row in card['metrics']:
            self.assertTrue(set(row) <= {'name', 'date', 'stopped', 'continued', 'unit', 'traders', 'depth'})
            self.assertLessEqual(len(row['name']), 80)
        self.assertLessEqual(len(card['source']['label']), 40)
        self.assertLessEqual(len(json.dumps(card)), 16384)

    def test_the_card_goes_to_this_session(self):
        self.tie()
        self.run_cli('card')
        with open(self.card_file + '.args') as f:
            args = f.read().split()
        self.assertEqual(args[:3], ['session', 'forecast', 'set'])
        self.assertIn(INSTANCE, args)

    def test_a_declined_proposal_with_lapsed_at_reads_as_lapsed(self):
        self.tie()
        self.stub.add_proposal('p-7', 7, status='declined',
                               pairs=[self.stub.pair('m-rev', 'Revenue (USD)', LATER, 120, 100, a_trades=1)])
        self.stub.proposals['p-7']['lapsedAt'] = iso(NOW)
        self.log_post('p-7', 7)
        self.run_cli('card')
        self.assertEqual(self.card()['verdict'], 'unpriced')
        self.assertEqual(self.card()['headline'], 'lapsed undecided')

    def test_the_biggest_movers_come_first_and_unpriced_rows_last(self):
        self.tie()
        s = self.stub
        pairs = [s.pair('m-a', 'Quiet', LATER, 100, 100),
                 s.pair('m-b', 'Small', LATER, 110, 100, a_trades=1),
                 s.pair('m-c', 'Big fall', LATER, 100, 400, a_trades=1),
                 s.pair('m-d', 'Mid', LATER, 150, 100, d_trades=2)]
        s.add_proposal('p-7', 7, pairs=pairs)
        books = [{'metric_id': m, 'metric_name': n, 'target_date': LATER, 'amount': 10}
                 for m, n in [('m-a', 'Quiet'), ('m-b', 'Small'), ('m-c', 'Big fall'), ('m-d', 'Mid')]]
        self.log_post('p-7', 7, books=books)
        r = self.run_cli('card')
        self.assertEqual([row['name'] for row in self.card()['metrics']], ['Big fall', 'Mid', 'Small', 'Quiet'])
        lines = r.stdout.splitlines()
        self.assertTrue(lines[1].startswith('Big fall'), r.stdout)
        self.assertIn('priced on 3 of 4 books, 4 trades', r.stdout)

    def test_an_untraded_proposal_says_no_forecaster_has_traded_it(self):
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[s.pair('m-rev', 'Revenue (USD)', LATER, 100, 100)])
        self.log_post('p-7', 7)
        r = self.run_cli('card')
        self.assertIn('Unpriced: no forecaster has traded it yet', r.stdout)
        self.assertNotIn('priced on', r.stdout)

    def test_the_overview_shows_at_most_three_movers(self):
        self.tie()
        s = self.stub
        pairs = [s.pair(f'm-{i}', f'Metric {i}', LATER, 10 + i, 10, a_trades=1) for i in range(8)]
        s.add_proposal('p-7', 7, pairs=pairs)
        books = [{'metric_id': f'm-{i}', 'metric_name': f'Metric {i}', 'target_date': LATER, 'amount': 10}
                 for i in range(8)]
        self.log_post('p-7', 7, books=books)
        r = self.run_cli('card')
        movers = [l for l in r.stdout.splitlines() if ': stopped ' in l]
        self.assertEqual(len(movers), 3, r.stdout)

    def test_the_overview_is_at_most_six_lines(self):
        self.tie()
        s = self.stub
        pairs = [s.pair(f'm-{i}', f'Metric {i}', LATER, 10 + i, 10, a_trades=1) for i in range(8)]
        s.add_proposal('p-7', 7, pairs=pairs)
        books = [{'metric_id': f'm-{i}', 'metric_name': f'Metric {i}', 'target_date': LATER, 'amount': 10}
                 for i in range(8)]
        self.log_post('p-7', 7, books=books)
        r = self.run_cli('card')
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        self.assertGreaterEqual(len(lines), 2)
        self.assertLessEqual(len(lines), 6)
        self.assertIn('/acme/p/7', r.stdout)

    def test_an_aoe_failure_is_said_once_and_the_overview_still_prints(self):
        self.tie()
        r = self.run_cli('card', env={'AOE_STUB_FAIL': '1'})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
        self.assertIn('aoe', r.stderr)
        self.assertIn('no continuation proposal yet', r.stdout)

    def test_no_aoe_skips_the_card(self):
        self.tie()
        r = self.run_cli('card', '--no-aoe')
        self.assertEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(self.card_file))

    def test_reading_the_card_writes_nothing_to_the_floor(self):
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[s.pair('m-rev', 'Revenue (USD)', LATER, 120, 100, a_trades=1)])
        self.log_post('p-7', 7)
        self.run_cli('card')
        self.assertEqual(self.posts(), [])


class Decide(Base):
    def setUp(self):
        super().setUp()
        self.tie()
        s = self.stub
        s.add_proposal('p-7', 7, pairs=[s.pair('m-rev', 'Revenue (USD)', LATER, 120, 100, a_trades=1)])
        self.log_post('p-7', 7)

    def test_stop_declines_with_the_reason_session_stopped(self):
        r = self.run_cli('decide', 'stop')
        self.assertEqual(r.returncode, 0, r.stderr)
        (_, path, _, body), = self.posts()
        self.assertEqual(path, '/api/proposals/p-7/decline')
        self.assertEqual(body['declineReason'], 'session stopped')
        self.assertEqual(self.card()['verdict'], 'stop')
        self.assertEqual(self.card()['headline'], 'session stopped')
        self.assertEqual(self.log_lines()[-1]['decision'], 'stop')

    def test_continue_approves(self):
        r = self.run_cli('decide', 'continue')
        self.assertEqual(r.returncode, 0, r.stderr)
        (_, path, _, _), = self.posts()
        self.assertEqual(path, '/api/proposals/p-7/approve')
        self.assertEqual(self.card()['headline'], 'continued: round 2')
        self.assertEqual(self.log_lines()[-1]['event'], 'decide')

    def test_deciding_twice_is_refused_by_the_server_and_exits_1(self):
        self.run_cli('decide', 'continue')
        r = self.run_cli('decide', 'stop')
        self.assertEqual(r.returncode, 1)
        self.assertIn('not_pending', r.stderr)

    def test_anything_but_continue_or_stop_is_refused(self):
        r = self.run_cli('decide', 'maybe')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.posts(), [])


class NeverTrades(Base):
    def test_the_helper_never_trades_its_own_continuation_market(self):
        """The session never trades the continuation market (SKILL.md section 5):
        across post, card and decide, the only writes are the proposal and its decision."""
        self.tie()
        self.run_cli('post', '--workspace', 'acme', '--plan', 'x')
        self.run_cli('card')
        self.run_cli('decide', 'continue')
        allowed = {'/api/proposals', '/api/proposals/p-100/approve', '/api/proposals/p-100/decline'}
        for method, path, _, _ in self.posts():
            self.assertIn(path.split('?')[0], allowed)
        self.assertFalse(any('trade' in p or 'predictions' in p or 'liquidity' in p
                             for _, p, _, _ in self.stub.requests))


if __name__ == '__main__':
    unittest.main(verbosity=1)
