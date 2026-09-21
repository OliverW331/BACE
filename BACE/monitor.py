#!/usr/bin/env python3
"""Read-only progress viewer for a detached BACE run; creates no files."""
import argparse
from collections import deque
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sqlite3
from statistics import median
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'script'))

from progress import RunProgress, clean

FINAL_STATES = {'complete', 'incomplete', 'interrupted'}
API_STAGES = {
    'candidates': ('generation_claim_candidate_selection_config.json', 'claim_candidate_calls.jsonl'),
    'support': ('generation_claim_support_config.json', 'claim_support_calls.jsonl'),
    'diagnosis': ('generation_claim_unsupported_diagnosis_config.json', 'claim_unsupported_diagnosis_calls.jsonl'),
}


class ApiView:
    """Observe new completions and live gate state without writing telemetry.

    Existing call bodies are skipped on attachment. Only new complete JSONL
    records are read, and the statistics window is bounded to sixty seconds.
    The shared gate exposes leases, not waiting jobs or provider quotas.
    """
    def __init__(self, run, scope, stage):
        from dotenv import dotenv_values
        sys.path.insert(0, str(ROOT / 'script/evaluation'))
        from generation_claims import normalize_azure_base_url
        from claim_execution import process_marker
        self.process_marker = process_marker
        self.run, self.scope, self.stage = run, scope, stage
        config_name, self.calls_name = API_STAGES[stage]
        config = json.loads((ROOT / 'config/evaluation/configs' / config_name).read_text())
        environment = {**dotenv_values(ROOT / '.env'), **os.environ}
        model = config['models'][environment.get(config['current_primary_model_env']) or config['current_primary_model']]
        endpoint = environment.get(model['endpoint_env'])
        execution = json.loads((ROOT / 'config/claim_execution.json').read_text())['stages'][stage]
        routing = execution['resource'] + '|' + normalize_azure_base_url(endpoint).rstrip('/') if endpoint else None
        self.key = hashlib.sha256(routing.encode()).hexdigest() if routing else None
        parent = Path('/dev/shm') if Path('/dev/shm').is_dir() else Path(tempfile.gettempdir())
        identity = hashlib.sha256(str(ROOT.resolve()).encode()).hexdigest()[:16]
        self.database = parent / f'bace-{os.getuid()}-{identity}' / 'requests.sqlite'
        self.started = time.monotonic()
        self.initial = True
        self.previous_active = set()
        self.finished = set()
        self.tails = {}
        self.events = deque()
        self.event_keys = set()
        self.retries = deque()
        self.read_errors = 0

    def new_lines(self, path, baseline):
        """Keep an offset, never consume an incomplete final line."""
        try:
            with path.open('rb') as source:
                stat = os.fstat(source.fileno())
                identity = (stat.st_dev, stat.st_ino)
                previous, offset = self.tails.get(path, (identity, 0))
                if previous != identity or offset > stat.st_size:
                    offset = 0
                if baseline:
                    offset = stat.st_size
                    # Keep any record still being appended at attachment time.
                    while offset:
                        start = max(0, offset - 65536)
                        source.seek(start)
                        chunk = source.read(offset - start)
                        newline = chunk.rfind(b'\n')
                        if newline >= 0:
                            offset = start + newline + 1
                            break
                        offset = start
                    self.tails[path] = (identity, offset)
                    return
                source.seek(offset)
                end = min(stat.st_size, offset + 4 * 1024 * 1024)
                while source.tell() < end:
                    line = source.readline()
                    if not line.endswith(b'\n'):
                        break
                    offset = source.tell()
                    self.tails[path] = (identity, offset)
                    yield line
                self.tails[path] = (identity, offset)
        except FileNotFoundError:
            return
        except OSError:
            self.read_errors += 1

    def record(self, record, now):
        if not record.get('model_called'):
            return
        key = (record.get('call_id'), record.get('finished_at_utc'))
        if key in self.event_keys:
            return
        ok = record.get('call_status') == 'success'
        before = after = None
        attempts = record.get('attempts') or []
        if ok and len(attempts) == 1 and attempts[0].get('network_retries') == 0:
            api = attempts[0].get('api_response') or {}
            try:
                start = datetime.fromisoformat(record['started_at_utc']).timestamp()
                finish = datetime.fromisoformat(record['finished_at_utc']).timestamp()
                created = float(api['created_at'])
                # Provider timestamps can have only whole-second precision.
                if start - 1 <= created <= finish + 1:
                    before, after = max(0, created - start), max(0, finish - created)
            except (KeyError, TypeError, ValueError, OverflowError):
                pass
        usage = record.get('usage') or {}
        self.events.append({'time': now, 'key': key, 'ok': ok,
                            'input': usage.get('input_tokens') or 0,
                            'output': usage.get('output_tokens') or 0,
                            'before': before, 'after': after})
        self.event_keys.add(key)

    def collect(self, state):
        now = time.monotonic()
        while self.events and now - self.events[0]['time'] > 60:
            self.event_keys.discard(self.events.popleft()['key'])
        while self.retries and now - self.retries[0] > 60:
            self.retries.popleft()
        active = {case['generation_case_id'] for case in state.get('active_cases', [])}
        finished = set(state.get('completed_case_ids', [])) | {
            case['generation_case_id'] for case in state.get('failures', [])}
        cases = active | self.previous_active | (set() if self.initial else finished - self.finished)
        for cid in sorted(cases):
            base = self.run / 'cases' / cid
            for line in self.new_lines(base / 'logs' / f'{self.stage}.log', self.initial):
                if b'retryable API error (RateLimitError);' in line:
                    self.retries.append(now)
            for line in self.new_lines(base / 'bace' / self.stage / self.calls_name, self.initial):
                try:
                    self.record(json.loads(line), now)
                except (ValueError, TypeError, AttributeError):
                    self.read_errors += 1
        self.previous_active, self.finished = active, finished
        self.initial = False
        # Retain cursors only while a case can still append new records.
        self.tails = {path: cursor for path, cursor in self.tails.items()
                      if path.relative_to(self.run / 'cases').parts[0] in active}

    def gate(self):
        if self.key is None or not self.database.exists():
            return None
        with closing(sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=0.1)) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            row = db.execute('SELECT * FROM resources WHERE key=?', (self.key,)).fetchone()
            leases = db.execute('SELECT pid,marker,expires FROM leases WHERE key=?', (self.key,)).fetchall()
        if row is None:
            return None
        now = time.time()
        markers = {lease['pid']: self.process_marker(lease['pid']) for lease in leases}
        live = sum(lease['expires'] > now and markers[lease['pid']] == lease['marker']
                   and markers[lease['pid']] is not None for lease in leases)
        return {**dict(row), 'live': live,
                'cooldown': max(0, row['blocked_until'] - now),
                'next': max(0, max(row['blocked_until'], row['next_request']) - now)}

    def lines(self):
        now = time.monotonic()
        while self.events and now - self.events[0]['time'] > 60:
            self.event_keys.discard(self.events.popleft()['key'])
        while self.retries and now - self.retries[0] > 60:
            self.retries.popleft()
        try:
            state = json.loads((self.run / 'execution_status.json').read_text())
        except (OSError, ValueError):
            state = {}
        # Preserve cursors during a temporarily unavailable status snapshot.
        if state:
            self.collect(state)
        status = state.get('status')
        try:
            age = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(state['updated_at_utc'])).total_seconds())
        except (KeyError, TypeError, ValueError):
            age = None
        label = 'STALE SNAPSHOT' if age is not None and age > 15 and status not in FINAL_STATES else (status or 'waiting').upper()
        try:
            gate = self.gate()
        except (OSError, sqlite3.Error):
            gate = None
        lines = [f'BACE {self.scope} | {self.stage.upper()} API | {label} | PID {state.get("pid", "?")}']
        if gate:
            lines += [f'Shared gate: In-flight {gate["live"]} | Limit {gate["capacity"]}/{gate["ceiling"]} (local)',
                      f'Pacing: Gap {gate["spacing"]:.2f}s | Cooldown {gate["cooldown"]:.1f}s | Next >= {gate["next"]:.1f}s']
        else:
            lines += ['Shared gate: unavailable or not initialized', 'Pacing: unavailable; viewer does not create or reset the gate']
        span = min(60, time.monotonic() - self.started)
        success = [event for event in self.events if event['ok']]
        rate = f'{len(success) * 60 / span:.1f}' if span >= 1 else '--'
        tokens = [f'{sum(event[key] for event in success) * 60 / span:.0f}' if span >= 1 else '--'
                  for key in ('input', 'output')]
        before = [event['before'] for event in success if event['before'] is not None]
        after = [event['after'] for event in success if event['after'] is not None]
        delays = [f'{median(values):.1f}s' if values else '--' for values in (before, after)]
        lines += [f'Observed {span:.0f}s / 60s window: OK {len(success)} | Errors {len(self.events)-len(success)} | 429 retries {len(self.retries)}',
                  f'Goodput {rate} jobs/min | OK-job tokens/min: input {tokens[0]} output {tokens[1]}',
                  f'Clean-call medians (n={len(before)}): Pre-server ~{delays[0]} | API-to-save ~{delays[1]}',
                  'Queue depth: unrecorded | Azure internal queue and quota: unavailable',
                  ('Snapshot age unknown' if age is None else f'Snapshot age {age:.0f}s') +
                  f' | Read errors {self.read_errors} | ' +
                  ('Gate also serves RAGChecker/RAGAS' if self.stage == 'support' else 'Read-only; statistics begin on attachment')]
        return lines, status


def snapshot_lines(formatter, path):
    try:
        state = json.loads(path.read_text())
        lines = formatter.lines(state)
        status = state['status']
        updated = datetime.fromisoformat(state['updated_at_utc'])
        age = max(0, (datetime.now(timezone.utc) - updated).total_seconds())
        lines[0] += f" | PID {state['pid']}"
        if age > 15 and status not in FINAL_STATES:
            lines[0] = f'BACE {formatter.scope} | STALE SNAPSHOT | PID {state["pid"]}'
            lines[-1] = f'No update for {int(age)}s; last state: {status}. Inspect runner.log.'
        return lines, status
    except FileNotFoundError:
        message = 'Waiting for the experiment to create its progress snapshot.'
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        message = f'Snapshot unavailable ({type(exc).__name__}); retrying.'
    return [f'BACE {formatter.scope} | WAITING', message,
            'This viewer does not start or stop the experiment.', '', '', '', '',
            f'Status: {path}'], None


def render(lines, stream, interactive):
    if not interactive:
        stream.write('\n'.join(clean(line) for line in lines) + '\n')
    else:
        try:
            width, height = os.get_terminal_size(stream.fileno())
        except (OSError, AttributeError, ValueError):
            width, height = 100, 24
        visible = [clean(line)[:max(1, width - 1)] for line in lines[:max(1, height - 1)]]
        # Repaint the current terminal viewport without opening an alternate screen.
        stream.write('\x1b[H' + '\n'.join('\r\x1b[2K' + line for line in visible) + '\x1b[J')
    stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=['main', 'pilot'], default='main')
    parser.add_argument('--once', action='store_true', help='Print one snapshot without terminal controls')
    parser.add_argument('--api', nargs='?', const='candidates', choices=sorted(API_STAGES),
                        help='Observe API pacing and live throughput; default stage: candidates')
    parser.add_argument('--interval', type=float, default=2, help='Refresh interval in seconds (default: 2)')
    args = parser.parse_args()
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error('--interval must be a positive finite number')
    run = ROOT / 'results' / f'{args.scope}_v1'
    # Use only the existing formatter; never enter its writer/thread context.
    formatter = RunProgress(args.scope, run, 1, 0, stream=io.StringIO())
    api = ApiView(run, args.scope, args.api) if args.api else None
    interactive = sys.stdout.isatty() and os.environ.get('TERM') != 'dumb' and not args.once
    try:
        while True:
            lines, status = api.lines() if api else snapshot_lines(formatter, run / 'execution_status.json')
            render(lines, sys.stdout, interactive)
            if not interactive or status in FINAL_STATES:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print('\nViewer closed; the background experiment is unchanged.')
        return
    except BrokenPipeError:
        return
    if interactive:
        print()


if __name__ == '__main__':
    main()
