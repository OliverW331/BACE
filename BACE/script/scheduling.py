"""Bounded case scheduling, independent branches, and cancellable subprocesses."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
import os
import signal
import subprocess
import threading
import time


class ExperimentInterrupted(InterruptedError):
    pass


class ProcessControl:
    def __init__(self):
        self.stopped = threading.Event()
        self.lock = threading.RLock()
        self.processes = set()

    def check(self):
        if self.stopped.is_set():
            raise ExperimentInterrupted('Stopped by user; saved outputs are resumable')

    @staticmethod
    def signal_process(process, sig):
        if process.poll() is None:
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass

    def cancel(self, *_):
        self.stopped.set()
        with self.lock:
            for process in self.processes:
                self.signal_process(process, signal.SIGTERM)

    def run(self, command, **kwargs):
        with self.lock:
            self.check()
            process = subprocess.Popen(command, start_new_session=True, **kwargs)
            self.processes.add(process)
        stopping_at = None
        try:
            while True:
                try:
                    code = process.wait(timeout=0.2)
                    self.check()
                    return code
                except subprocess.TimeoutExpired:
                    if self.stopped.is_set():
                        stopping_at = stopping_at or time.monotonic()
                        self.signal_process(process, signal.SIGKILL if time.monotonic()-stopping_at>3 else signal.SIGTERM)
        finally:
            if self.stopped.is_set():
                # The leader may have exited while a child ignored SIGTERM.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            with self.lock:
                self.processes.discard(process)


def parallel_branches(branches):
    """Finish independent branches even when a sibling fails; retain successes."""
    errors = []
    with ThreadPoolExecutor(max_workers=len(branches)) as pool:
        pending = {pool.submit(call): name for name, call in branches.items()}
        for future in as_completed(pending):
            try:
                future.result()
            except Exception as exc:
                errors.append((pending[future], exc))
    if errors:
        for _, error in errors:
            if isinstance(error, ExperimentInterrupted):
                raise error
        raise RuntimeError('Incomplete branches: '+', '.join(name for name, _ in errors)) from errors[0][1]


def run_cases(cases, execute, workers, control):
    """Keep at most workers submitted cases; never enqueue the entire study."""
    source = iter(cases)
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {}
        def submit():
            if control.stopped.is_set():
                return
            case = next(source, None)
            if case is not None:
                pending[pool.submit(execute, case)] = case['generation_case_id']
        for _ in range(workers):
            submit()
        while pending:
            done, _ = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
            for future in done:
                cid = pending.pop(future)
                try:
                    future.result()
                except ExperimentInterrupted:
                    control.cancel()
                except Exception as exc:
                    failures.append({'generation_case_id': cid, 'error': str(exc)})
                submit()
    control.check()
    return failures
