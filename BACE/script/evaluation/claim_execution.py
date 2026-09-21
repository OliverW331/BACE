"""Bounded claim requests with one result writer and shared rate-limit waits."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
import random
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]


def coordination_database():
    """SQLite locking requires local storage, never the project's NFS mount."""
    parent = Path('/dev/shm') if Path('/dev/shm').is_dir() else Path(tempfile.gettempdir())
    identity = hashlib.sha256(str(ROOT.resolve()).encode()).hexdigest()[:16]
    directory = parent/f'bace-{os.getuid()}-{identity}'
    directory.mkdir(mode=0o700,exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid!=os.getuid():
        raise ValueError('Unsafe local coordination directory')
    return directory/'requests.sqlite'


def settings(stage, workers=None):
    path = ROOT/'config/claim_execution.json'
    config = json.loads(path.read_text())
    value = {**config['stages'][stage], 'version':config['version'],
             'config_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    if workers is not None:
        value['workers'] = workers
    if not 1 <= value['workers'] <= value['max_inflight']:
        raise ValueError('Claim workers must be between one and the shared stage limit')
    return value


def completed_jobs(jobs, execute, workers, delay=0):
    """Yield completed results on the caller thread, even after another job fails.

    At most workers jobs are submitted. The caller alone appends JSONL records;
    sorted native output materialization remains in each existing stage script.
    """
    if workers < 1 or delay < 0:
        raise ValueError('Invalid claim concurrency or request delay')
    pending_items = iter(enumerate(jobs,1))
    errors = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {}
        def submit():
            item = next(pending_items,None)
            if item is None:
                return
            if delay:
                time.sleep(delay)
            pending[pool.submit(execute,item)] = item
        for _ in range(workers):
            submit()
        while pending:
            done,_ = wait(pending,return_when=FIRST_COMPLETED)
            for future in done:
                item = pending.pop(future)
                try:
                    record = future.result()
                except Exception as exc:
                    errors.append((item[1].get('call_id','unknown'),exc))
                else:
                    yield item[1],record
                submit()
    if errors:
        raise RuntimeError(f'{len(errors)} claim jobs raised exceptions; successful calls were retained') from errors[0][1]


def process_marker(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()
        return None if fields[0]=='Z' else fields[19]
    except (FileNotFoundError,ProcessLookupError):
        return None


def retry_after(error, fallback):
    headers = getattr(getattr(error,'response',None),'headers',{})
    for key in ('retry-after-ms','x-ms-retry-after-ms'):
        try:
            return max(fallback,float(headers[key])/1000)
        except (KeyError,TypeError,ValueError):
            pass
    value = headers.get('retry-after')
    try:
        return max(fallback,float(value))
    except (TypeError,ValueError):
        try:
            stamp = parsedate_to_datetime(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return max(fallback,(stamp-datetime.now(timezone.utc)).total_seconds())
        except (TypeError,ValueError,OverflowError):
            return fallback


class RequestGate:
    """A tiny live coordination database; completed requests leave no history.

    SQLite transactions coordinate threads and subprocesses. Dead-process leases
    are reclaimed immediately; a timeout lease also handles interrupted clients.
    Stages using the same model deployment share a resource, including external
    evaluators. A 429 reduces the live limit once per cooldown, without history.
    """
    def __init__(self, key, limit, timeout=600, database=None, initial=None, spacing=0):
        self.key,self.limit,self.timeout = key,limit,timeout
        self.database = Path(database) if database is not None else coordination_database()
        initial = min(limit,initial or limit)
        self.database.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS resources (key TEXT PRIMARY KEY, blocked_until REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, key TEXT, pid INTEGER, marker TEXT, expires REAL)')
            columns = {r[1] for r in db.execute('PRAGMA table_info(resources)')}
            for name,kind in [('capacity','INTEGER'),('successes','INTEGER'),('resized_at','REAL'),('ceiling','INTEGER'),('spacing','REAL'),('next_request','REAL')]:
                if name not in columns:
                    db.execute(f'ALTER TABLE resources ADD COLUMN {name} {kind}')
            db.execute('INSERT OR IGNORE INTO resources(key,blocked_until,capacity,successes,resized_at,ceiling,spacing,next_request) VALUES (?,0,?,0,0,?,?,0)',(key,initial,limit,spacing))
            db.execute('UPDATE resources SET capacity=CASE WHEN ceiling IS NULL OR ceiling!=? THEN ? ELSE MIN(COALESCE(capacity,?),?) END,ceiling=?,successes=COALESCE(successes,0),resized_at=COALESCE(resized_at,0),spacing=COALESCE(spacing,0.1),next_request=COALESCE(next_request,0) WHERE key=?',(limit,initial,initial,limit,limit,key))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database,timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def request(self):
        token = uuid.uuid4().hex
        pid = os.getpid()
        marker = process_marker(pid)
        while True:
            now = time.time()
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                markers = {}
                for lease,p,m,expires in db.execute('SELECT id,pid,marker,expires FROM leases WHERE key=?',(self.key,)).fetchall():
                    if p not in markers:
                        markers[p] = process_marker(p)
                    if expires<=now or markers[p]!=m:
                        db.execute('DELETE FROM leases WHERE id=?',(lease,))
                row = db.execute('SELECT blocked_until,capacity,next_request,spacing FROM resources WHERE key=?',(self.key,)).fetchone()
                blocked = max(0,max(row[0],row[2])-now)
                active = db.execute('SELECT COUNT(*) FROM leases WHERE key=?',(self.key,)).fetchone()[0]
                acquired = blocked==0 and active<min(self.limit,row[1])
                if acquired:
                    db.execute('INSERT INTO leases VALUES (?,?,?,?,?)',(token,self.key,pid,marker,now+self.timeout+60))
                    db.execute('UPDATE resources SET next_request=? WHERE key=?',(now+row[3],self.key))
            if acquired:
                break
            time.sleep(min(1,blocked) if blocked else random.uniform(0.08,0.2))
        try:
            yield
        finally:
            with self.connect() as db:
                db.execute('DELETE FROM leases WHERE id=?',(token,))

    def cooldown(self, seconds):
        with self.connect() as db:
            now = time.time()
            db.execute('UPDATE resources SET capacity=CASE WHEN blocked_until<=? THEN MAX(1,capacity/2) ELSE capacity END,spacing=CASE WHEN blocked_until<=? THEN MIN(30,MAX(0.25,spacing*2)) ELSE spacing END, blocked_until=MAX(blocked_until,?),successes=0,resized_at=? WHERE key=?',
                       (now,now,now+seconds,now,self.key))

    def success(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            capacity,count,stamp,blocked,spacing = db.execute('SELECT capacity,successes,resized_at,blocked_until,spacing FROM resources WHERE key=?',(self.key,)).fetchone()
            count += 1
            now = time.time()
            if count>=max(8,capacity) and now-stamp>=5 and blocked<=now:
                capacity,count,stamp = min(self.limit,capacity+1),0,now
                spacing = max(0.05,spacing*0.9)
            db.execute('UPDATE resources SET capacity=?,successes=?,resized_at=?,spacing=? WHERE key=?',
                       (capacity,min(count,self.limit),stamp,spacing,self.key))


def attach_gate(client, stage, execution, timeout=600):
    if client is not None:
        routing = execution.get('resource',stage)+'|'+str(client.base_url).rstrip('/')
        client._bace_request_gate = RequestGate(hashlib.sha256(routing.encode()).hexdigest(),execution['max_inflight'],timeout,initial=execution.get('initial_inflight'),spacing=0.1)


def create_response(client, **kwargs):
    gate = getattr(client,'_bace_request_gate',None)
    if gate is None:
        return client.responses.create(**kwargs)
    with gate.request():
        try:
            response = client.responses.create(**kwargs)
            gate.success()
            return response
        except Exception as exc:
            if getattr(exc,'status_code',None)==429:
                gate.cooldown(retry_after(exc,2))
            raise


def shared_retry_delay(client, error, fallback):
    delay = retry_after(error,fallback)
    if getattr(error,'status_code',None)==429:
        gate = getattr(client,'_bace_request_gate',None)
        if gate is not None:
            gate.cooldown(delay)
    return delay
