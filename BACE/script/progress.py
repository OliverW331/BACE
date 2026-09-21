"""Bounded, in-place terminal progress; one overwritten run-status snapshot."""
import os
import sys
import threading
import time
from datetime import datetime, timezone

from common import write


STAGES = ('generation', 'direct', 'integrated', 'atomic', 'dedup',
          'candidates', 'support', 'diagnosis', 'ragchecker', 'ragas')


def duration(seconds):
    seconds = max(0, int(seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def clean(value):
    """Prevent control characters or wrapped labels from moving the display."""
    return ''.join(c if c.isprintable() and c.isascii() else ' ' for c in str(value))


class TerminalDisplay:
    def __init__(self, stream=None):
        self.stream = stream if stream is not None else sys.stderr
        self.interactive = self.stream.isatty() and os.environ.get('TERM') != 'dumb'
        self.rows = 0
        self.started = False
        self.disabled = False
        self.final_lines = None

    def render(self, lines, final=False):
        if self.disabled:
            return
        try:
            if not self.interactive:
                if not self.started or final:
                    self.stream.write(' | '.join(clean(s) for s in lines[:3]) + '\n')
                    self.stream.flush()
                self.started = True
                return
            try:
                width, height = os.get_terminal_size(self.stream.fileno())
            except (OSError, AttributeError, ValueError):
                width, height = 100, 24
            capacity = max(1, height - 1)
            visible = [clean(s)[:max(1, width - 1)] for s in lines[:capacity]]
            prefix = ('\x1b[?1049h\x1b[?25l' if not self.started else '') + '\x1b[H'
            count = len(visible)
            body = '\n'.join('\r\x1b[2K' + (visible[i] if i < len(visible) else '')
                             for i in range(count))
            self.stream.write(prefix + body + "\x1b[J")
            if final:
                self.final_lines = lines[:3]
            self.rows = count
            self.started = True
            self.stream.flush()
        except (OSError, ValueError):
            # A detached/broken output stream must not abort model work.
            self.disabled = True

    def close(self):
        if self.interactive and self.started:
            try:
                self.stream.write('\x1b[?25h\x1b[?1049l')
                if self.final_lines:
                    self.stream.write('\n'.join(clean(s) for s in self.final_lines)+'\n')
                self.stream.flush()
            except (OSError, ValueError):
                pass


class RunProgress:
    def __init__(self, scope, run, workers, expected, stream=None, interval=2):
        self.scope, self.run = scope, run
        self.workers, self.expected = workers, expected
        self.display = TerminalDisplay(stream)
        self.interval = interval
        self.started = time.monotonic()
        self.status = 'preflight'
        self.note = 'Checking frozen inputs and environment'
        self.active = {}
        self.completed = set()
        self.reused = set()
        self.failures = {}
        self.reused_stages = 0
        self.lock = threading.Lock()
        self.refresh_lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = None
        self.snapshot_error = None

    def phase(self, status, note):
        with self.lock:
            self.status, self.note = status, note

    def begin_case(self, case):
        with self.lock:
            occupied = {item['slot'] for item in self.active.values()}
            slot = next(i for i in range(1, self.workers + 1) if i not in occupied)
            self.active[case['generation_case_id']] = {
                'slot': slot, 'company': case['company_name'],
                'year': case['target_reporting_year'], 'task': case['task_id'],
                'stage': 'inputs', 'state': 'preparing',
                'stage_started': time.monotonic(), 'executed_stages': 0, 'stages': {},
            }

    def begin_stage(self, cid, label):
        with self.lock:
            self.active[cid].update(stage=label, state='checking checkpoint',
                                    stage_started=time.monotonic())
            self.active[cid]['stages'][label] = {'state':'checking','started':time.monotonic(),'complete':False}

    def stage_state(self, cid, state, label=None):
        with self.lock:
            self.active[cid]['state'] = state
            label = label or self.active[cid]['stage']
            self.active[cid]['stages'][label]['state'] = state

    def finish_stage(self, cid, label, reused):
        with self.lock:
            self.active[cid]['state'] = 'reused' if reused else 'saved'
            self.active[cid]['stages'][label].update(state='reused' if reused else 'saved',complete=True)
            self.active[cid]['executed_stages'] += int(not reused)
            self.reused_stages += int(reused)
            self.note = f'{"Reused" if reused else "Saved"} {label}: {cid}'

    def finish_case(self, cid, error=None, cancelled=False):
        with self.lock:
            current = self.active.pop(cid)
            if cancelled:
                self.note = f"Interrupted: {cid}; saved outputs are resumable"
            elif error is not None:
                self.failures[cid] = str(error)
                self.note = f'Failed: {cid}; inspect its stage log'
            else:
                self.completed.add(cid)
                if current['executed_stages'] == 0:
                    self.reused.add(cid)

    def snapshot(self):
        now = time.monotonic()
        with self.lock:
            active = [{**{k: v for k, v in item.items() if k not in ('stage_started','stages')},
                       'stages':{name:{'state':node['state'],'complete':node['complete'],
                                       'elapsed_seconds':round(now-node['started'],1)} for name,node in item['stages'].items()},
                       'generation_case_id': cid,
                       'stage_elapsed_seconds': round(now - item['stage_started'], 1)}
                      for cid, item in sorted(self.active.items(), key=lambda kv: kv[1]['slot'])]
            return {
                'status': self.status, 'expected_cases': self.expected,
                'completed_case_ids': sorted(self.completed),
                'failures': [{'generation_case_id': cid, 'error': error}
                             for cid, error in sorted(self.failures.items())],
                'active_cases': active,
                'pending_cases': max(0, self.expected - len(self.completed) - len(self.failures) - len(active)),
                'reused_cases': len(self.reused), 'newly_completed_cases': len(self.completed - self.reused),
                'reused_stages': self.reused_stages,
                'elapsed_seconds': round(now - self.started, 1),
                'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
                'note': self.note,
            }

    def lines(self, state):
        done = len(state['completed_case_ids'])
        total = state['expected_cases']
        percent = 100 * done / total if total else 0
        lines = [f'BACE {self.scope} | {state["status"].upper()}',
                 f'Cases {done}/{total} ({percent:.1f}%) | Running {len(state["active_cases"])}'
                 f' | Pending {state["pending_cases"]} | Failed {len(state["failures"])}',
                 f'Elapsed {duration(state["elapsed_seconds"])} | New {state["newly_completed_cases"]}'
                 f' | Reused {state["reused_cases"]} cases / {state["reused_stages"]} stages']
        pages = max(1, (len(state['active_cases']) + 3) // 4)
        page = int(state['elapsed_seconds'] // 6) % pages
        slots = {i+1:item for i,item in enumerate(state['active_cases'])}
        for slot in range(page*4+1,page*4+5):
            item = slots.get(slot)
            if item is None:
                lines.append(f'[{slot}] Idle')
                continue
            stages = item.get('stages',{})
            bace = [name for name in STAGES[:-2] if name in stages and not stages[name]['complete']]
            bace_label = bace[0] if bace else 'done' if stages.get('diagnosis',{}).get('complete') else 'waiting'
            def external(name):
                node = stages.get(name)
                return 'wait' if not node else 'done' if node['complete'] else node['state']
            label = clean(item['company'])[:16]
            task = item['task'].split('_')[0]
            age = duration(stages[bace[0]]['elapsed_seconds']) if bace else ''
            lines.append(f'[{item["slot"]}] {label} {item["year"]} {task} | B:{bace_label} {age}'
                         f' RC:{external("ragchecker")} RA:{external("ragas")}')
        note = self.snapshot_error or state['note']
        lines.append(f'Page {page+1}/{pages} | B=BACE RC=RAGChecker RA=RAGAS | {note}')
        return lines

    def refresh(self, final=False):
        with self.refresh_lock:
            state = self.snapshot()
            try:
                write(self.run / 'execution_status.json', state)
                self.snapshot_error = None
            except OSError as exc:
                self.snapshot_error = f'Status snapshot could not be saved: {exc}'
            self.display.render(self.lines(state), final=final)

    def _refresh_loop(self):
        while not self.stop.wait(self.interval):
            self.refresh()

    def __enter__(self):
        self.refresh()
        self.thread = threading.Thread(target=self._refresh_loop, name='terminal-progress', daemon=True)
        self.thread.start()
        return self

    def __exit__(self, kind, error, traceback):
        self.stop.set()
        if self.thread is not None:
            self.thread.join()
        if error is not None:
            self.phase('interrupted' if isinstance(error, KeyboardInterrupt) else 'incomplete', str(error))
        try:
            self.refresh(final=True)
        finally:
            self.display.close()
