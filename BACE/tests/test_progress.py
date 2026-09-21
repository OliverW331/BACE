"""Terminal behavior, concurrent accounting and completion/resume regressions."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from common import read, write
from progress import RunProgress, STAGES, TerminalDisplay
import pipeline


class TTY(io.StringIO):
    def isatty(self):
        return True

    def fileno(self):
        return 2


def case(index):
    return {'generation_case_id': f'case-{index}', 'company_name': f'Company {index}',
            'target_reporting_year': 2023, 'task_id': 'E1-1'}


class ProgressTests(unittest.TestCase):
    def test_redraw_reuses_eight_rows_and_crops_control_characters(self):
        stream = TTY()
        with patch.dict(os.environ, {'TERM': 'xterm'}), patch('progress.os.get_terminal_size', return_value=os.terminal_size((64, 24))):
            display = TerminalDisplay(stream)
            for index in range(20):
                display.render([f'Frame {index}: ' + 'x' * 150 + '\n\x1b[2J' for _ in range(8)])
        output = stream.getvalue()
        display.close()
        # Emulate the emitted cursor/erase controls, including a 24-row screen.
        row, column, scrolls = 0, 0, 0
        screen = [''] * 24
        for token in re.findall(r'\x1b\[[0-9;?]*[A-Za-z]|[^\x1b]', output):
            if token == '\x1b[H':
                row, column = 0, 0
            elif token == '\x1b[J':
                screen[row] = screen[row][:column]
                screen[row+1:] = [''] * (23-row)
            elif token.endswith('A') and token.startswith('\x1b['):
                row = max(0, row - int(token[2:-1]))
            elif token == '\x1b[2K':
                screen[row] = ''
            elif token.startswith('\x1b['):
                self.assertIn(token, ('\x1b[?25l', '\x1b[?25h', '\x1b[?1049h', '\x1b[?1049l'))
            elif token == '\r':
                column = 0
            elif token == '\n':
                row += 1
                if row == 24:
                    scrolls += 1
                    screen.pop(0); screen.append(''); row = 23
            else:
                self.assertLess(column, 64)
                screen[row] += token
                column += 1
        self.assertEqual(scrolls, 0)
        self.assertEqual(sum(bool(line) for line in screen), 8)
        self.assertTrue(all(line.startswith('Frame 19:') for line in screen[:8]))
        self.assertTrue(stream.getvalue().endswith('\x1b[?25h\x1b[?1049l'))

    def test_redirected_output_prints_only_start_and_finish(self):
        stream = io.StringIO(); display = TerminalDisplay(stream)
        for index in range(100):
            display.render([f'Frame {index}', 'Counts', 'Elapsed', 'Worker'])
        display.render(['Complete', 'Counts', 'Elapsed'], final=True)
        display.close()
        self.assertEqual(len(stream.getvalue().splitlines()), 2)
        self.assertNotIn('\x1b', stream.getvalue())

    def test_small_terminal_and_broken_stream(self):
        stream = TTY()
        with patch.dict(os.environ, {'TERM': 'xterm'}), patch('progress.os.get_terminal_size', return_value=os.terminal_size((40, 5))):
            display = TerminalDisplay(stream)
            display.render(['x' * 100] * 8)
            self.assertEqual(display.rows, 4)
            display.close()
        class Broken(TTY):
            def write(self, value):
                raise BrokenPipeError('detached terminal')
        display = TerminalDisplay(Broken())
        display.render(['Working'])
        display.close()
        self.assertTrue(display.disabled)

    def test_concurrent_counts_distinguish_reuse_success_and_failure(self):
        with tempfile.TemporaryDirectory() as d:
            progress = RunProgress('pilot', Path(d), 4, 12, stream=io.StringIO())
            barrier = threading.Barrier(4)
            def work(index):
                item = case(index); cid = item['generation_case_id']
                progress.begin_case(item)
                barrier.wait(timeout=3)
                snapshot = progress.snapshot()
                self.assertEqual(len({c['slot'] for c in snapshot['active_cases']}), len(snapshot['active_cases']))
                progress.begin_stage(cid, 'generation')
                progress.stage_state(cid, 'running (attempt 2/3)')
                progress.finish_stage(cid, 'generation', reused=index == 0)
                progress.finish_case(cid, error=ValueError('fixture failure') if index == 3 else None)
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(work, range(4)))
            state = progress.snapshot()
            self.assertEqual(len(state['completed_case_ids']), 3)
            self.assertEqual(state['reused_cases'], 1)
            self.assertEqual(state['newly_completed_cases'], 2)
            self.assertEqual(len(state['failures']), 1)
            self.assertEqual(state['pending_cases'], 8)
            self.assertEqual(state['active_cases'], [])
            for _ in range(20):
                progress.refresh()
            self.assertEqual([p.name for p in Path(d).iterdir()], ['execution_status.json'])

    def test_error_restores_cursor_and_never_reports_complete(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'TERM': 'xterm'}):
            stream = TTY()
            with self.assertRaisesRegex(RuntimeError, 'summary failed'):
                with RunProgress('pilot', Path(d), 4, 1, stream=stream) as progress:
                    progress.begin_case(case(0))
                    progress.finish_case('case-0')
                    progress.phase('finalizing', 'Preparing summaries')
                    raise RuntimeError('summary failed')
            state = read(Path(d) / 'execution_status.json')
            self.assertEqual(state['status'], 'incomplete')
            self.assertEqual(len(state['completed_case_ids']), 1)
            self.assertIn('summary failed', state['note'])
            self.assertIn('\x1b[?25h\x1b[?1049l',stream.getvalue())

    def test_native_stage_reuse_preserves_receipts_without_terminal_spam(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()) as output:
            root = Path(d)
            write(root / 'config/experiment.json', {'runtime': {'max_stage_attempts': 2}})
            script = root / 'script/fixture.py'; script.parent.mkdir()
            script.write_text('import argparse,json\nfrom pathlib import Path\n'
                              'p=argparse.ArgumentParser();p.add_argument("--output-dir");a=p.parse_args()\n'
                              'o=Path(a.output_dir);o.mkdir(parents=True,exist_ok=True)\n'
                              '(o/"result.txt").write_text("fixed output")\n'
                              '(o/"manifest.json").write_text(json.dumps({"status":"complete"}))\n'
                              'print("Verbose native model output")\n')
            base = root / 'cases/case-0'
            with patch.object(pipeline, 'ROOT', root):
                first = RunProgress('pilot', root, 1, 1, stream=io.StringIO())
                first.begin_case(case(0))
                pipeline.stage(base, 'generation', 'fixture.py', [], base / 'generation', 'manifest.json', progress=first)
                first.finish_case('case-0')
                self.assertEqual(first.snapshot()['newly_completed_cases'], 1)
                receipt = (base / 'state.json').read_bytes()
                second = RunProgress('pilot', root, 1, 1, stream=io.StringIO())
                second.begin_case(case(0))
                with patch.object(pipeline.subprocess, 'Popen', side_effect=AssertionError('No new native calls on resume')):
                    pipeline.stage(base, 'generation', 'fixture.py', [], base / 'generation', 'manifest.json', progress=second)
                second.finish_case('case-0')
                self.assertEqual(second.snapshot()['reused_cases'], 1)
                self.assertEqual((base / 'state.json').read_bytes(), receipt)
            self.assertEqual(output.getvalue(), '')
            self.assertIn('Verbose native model output', (base / 'logs/generation.log').read_text())

    def test_orchestration_marks_complete_only_after_summary_returns(self):
        import acceptance
        import summarize
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); items = [case(i) for i in range(12)]
            write(root / 'config/experiment.json', {'runtime': {'case_workers': 4}})
            write(root / 'config/freeze.json', {})
            write(root / 'evidence/inputs/pilot_selection.json', {'cases': items})
            source = root / 'evidence/inputs/generation_cases.jsonl'
            source.write_text(''.join(json.dumps(item) + '\n' for item in items))
            def finish(item, run, progress, control=None):
                cid = item['generation_case_id']
                progress.begin_case(item)
                for label in STAGES:
                    progress.begin_stage(cid, label)
                    progress.finish_stage(cid, label, reused=True)
                progress.finish_case(cid)
                return cid
            def finalize(run, quiet=False):
                state = read(run / 'execution_status.json')
                self.assertEqual(state['status'], 'finalizing')
                self.assertEqual(len(state['completed_case_ids']), 12)
                self.assertTrue(quiet)
            run = root / 'results/pilot_v1'
            with patch.object(pipeline, 'ROOT', root), patch.object(acceptance, 'check_frozen'), \
                 patch.object(pipeline, 'run_case', side_effect=finish), patch.object(summarize, 'summarize', side_effect=finalize):
                with RunProgress('pilot', run, 4, 12, stream=io.StringIO()) as progress:
                    pipeline._run_experiment('pilot', progress)
                self.assertEqual(read(run / 'execution_status.json')['status'], 'complete')

    def test_display_revision_preserves_exact_predecessor_and_rejects_model_changes(self):
        import acceptance
        original = {'schema_version': 'bace_freeze_v1',
                    'files': {'script/pipeline.py': 'old', 'config/tasks.json': 'fixed'},
                    'environment': {'model': 'fixed'}}
        old_hash = hashlib.sha256((json.dumps(original, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()).hexdigest()
        revised = json.loads(json.dumps(original))
        revised['files']['script/pipeline.py'] = 'new'
        revised['files']['script/progress.py'] = 'display'
        revised['display_revision'] = {'previous_freeze_sha256': old_hash, 'changed_files': {
            'script/pipeline.py': {'before': 'old', 'after': 'new'},
            'script/progress.py': {'before': None, 'after': 'display'}}}
        self.assertEqual(acceptance.display_predecessor(revised), original)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); write(root / 'config/freeze.json', revised)
            with patch.object(acceptance, 'ROOT', root):
                acceptance.validate_run_freeze(old_hash)
                with self.assertRaises(ValueError):
                    acceptance.validate_run_freeze('unrelated')
        revised['files']['config/tasks.json'] = 'changed'
        with self.assertRaises(ValueError):
            acceptance.display_predecessor(revised)
        revised['display_revision']['changed_files']['config/tasks.json'] = {'before': 'fixed', 'after': 'changed'}
        with self.assertRaises(ValueError):
            acceptance.display_predecessor(revised)


if __name__ == '__main__':
    unittest.main()
