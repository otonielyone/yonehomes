"""Archive history inside the application's existing SQLite database."""
import base64
import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import fcntl

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_history_events (
 id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE,
 event_type TEXT NOT NULL, source TEXT NOT NULL, occurred_at TEXT,
 recorded_at TEXT NOT NULL, payload_json TEXT NOT NULL,
 source_path TEXT, source_collection TEXT, mirrored_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_app_history_events_time ON app_history_events(recorded_at);
CREATE INDEX IF NOT EXISTS ix_app_history_events_type ON app_history_events(event_type);
CREATE TABLE IF NOT EXISTS app_history_facts (
 key TEXT PRIMARY KEY, value_json TEXT NOT NULL, status TEXT NOT NULL,
 source TEXT NOT NULL, observed_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 event_id TEXT NOT NULL REFERENCES app_history_events(id)
);
CREATE TABLE IF NOT EXISTS app_history_archives (
 id TEXT PRIMARY KEY, relative_path TEXT NOT NULL, sha256 TEXT NOT NULL,
 captured_at TEXT NOT NULL, size_bytes INTEGER NOT NULL,
 original_bytes BLOB NOT NULL, searchable_text TEXT NOT NULL,
 UNIQUE(relative_path, sha256)
);
CREATE INDEX IF NOT EXISTS ix_app_history_archives_path ON app_history_archives(relative_path);
"""


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ConflictError(ValueError):
    pass


class HistoryStore:
    def __init__(self, database_path, history_dir, history_file="n8n_dns_foundation_history.json", max_file_bytes=64 * 1024 * 1024):
        self.database_path = Path(database_path).resolve()
        self.history_dir = Path(history_dir).resolve()
        if Path(history_file).name != history_file:
            raise ValueError("History filename must be a single filename")
        self.history_file = self.history_dir / history_file
        self.max_file_bytes = max_file_bytes
        # Never silently create a second database because a path was mistyped.
        if not self.database_path.is_file():
            raise FileNotFoundError("Existing app database not found: " + str(self.database_path))

    @contextmanager
    def connection(self, write=False):
        conn = sqlite3.connect(self.database_path.as_uri() + "?mode=rw", uri=True, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if write:
                conn.commit()
        except BaseException:
            if write:
                conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        with self.connection() as conn:
            conn.executescript(SCHEMA)
        return self.stats()

    def stats(self):
        with self.connection() as conn:
            return {"database": str(self.database_path), "historyDirectory": str(self.history_dir),
                    "historyFile": str(self.history_file),
                    "events": conn.execute("SELECT COUNT(*) FROM app_history_events").fetchone()[0],
                    "facts": conn.execute("SELECT COUNT(*) FROM app_history_facts").fetchone()[0],
                    "fileVersions": conn.execute("SELECT COUNT(*) FROM app_history_archives").fetchone()[0],
                    "pendingFileMirror": conn.execute("SELECT COUNT(*) FROM app_history_events WHERE mirrored_at IS NULL").fetchone()[0]}

    def _insert_event(self, conn, event_type, payload, source, occurred_at=None, idempotency_key=None,
                      source_path=None, source_collection=None):
        encoded = canonical(payload)
        if idempotency_key:
            old = conn.execute("SELECT * FROM app_history_events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if old:
                if (old["event_type"], old["payload_json"], old["source"], old["occurred_at"]) != (event_type, encoded, source, occurred_at):
                    raise ConflictError("Idempotency key was reused with different event content")
                return old["id"], False
        event_id = str(uuid.uuid4())
        conn.execute("INSERT INTO app_history_events (id,idempotency_key,event_type,source,occurred_at,recorded_at,payload_json,source_path,source_collection) VALUES (?,?,?,?,?,?,?,?,?)",
                     (event_id, idempotency_key, event_type, source, occurred_at, now(), encoded, source_path, source_collection))
        return event_id, True

    def save_event(self, event_type, payload, source="n8n", occurred_at=None, idempotency_key=None):
        with self.connection(write=True) as conn:
            event_id, created = self._insert_event(conn, event_type, payload, source, occurred_at, idempotency_key)
        mirrored = self.mirror()
        return {"id": event_id, "created": created, "databaseSaved": True, **mirrored}

    def save_fact(self, key, value, status, source, observed_at):
        if status not in {"verified", "reported", "planned", "unknown"}:
            raise ValueError("Fact status must be verified, reported, planned or unknown")
        payload = {"key": key, "value": value, "status": status, "source": source, "observed_at": observed_at}
        with self.connection(write=True) as conn:
            encoded = canonical(value)
            old = conn.execute("SELECT * FROM app_history_facts WHERE key=?", (key,)).fetchone()
            identical = old and (old["value_json"], old["status"], old["source"], old["observed_at"]) == (encoded, status, source, observed_at)
            if identical:
                event_id, created = old["event_id"], False
            else:
                event_id, created = self._insert_event(conn, "context.fact.updated", payload, source, observed_at)
                conn.execute("INSERT INTO app_history_facts (key,value_json,status,source,observed_at,updated_at,event_id) VALUES (?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,status=excluded.status,source=excluded.source,observed_at=excluded.observed_at,updated_at=excluded.updated_at,event_id=excluded.event_id",
                             (key, encoded, status, source, observed_at, now(), event_id))
        return {"key": key, "id": event_id, "created": created, "databaseSaved": True, **self.mirror()}

    def seed_facts(self, facts):
        # Seed everything in one database transaction, then mirror once.
        changed = 0
        with self.connection(write=True) as conn:
            for fact in facts:
                key, value, status, source, observed = (fact[k] for k in ("key", "value", "status", "source", "observed_at"))
                if status not in {"verified", "reported", "planned", "unknown"}:
                    raise ValueError("Invalid seed fact status")
                encoded = canonical(value)
                old = conn.execute("SELECT * FROM app_history_facts WHERE key=?", (key,)).fetchone()
                # Do not overwrite newer facts on a repeat installation.
                if old and old["observed_at"] > observed:
                    continue
                if old and (old["value_json"], old["status"], old["source"], old["observed_at"]) == (encoded, status, source, observed):
                    continue
                event_id, _ = self._insert_event(conn, "context.fact.updated", fact, source, observed)
                conn.execute("INSERT INTO app_history_facts (key,value_json,status,source,observed_at,updated_at,event_id) VALUES (?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,status=excluded.status,source=excluded.source,observed_at=excluded.observed_at,updated_at=excluded.updated_at,event_id=excluded.event_id",
                             (key, encoded, status, source, observed, now(), event_id))
                changed += 1
        return {"factsUpdated": changed, "databaseSaved": True, **self.mirror()}

    def _archive_bytes(self, conn, relative_path, data):
        checksum = hashlib.sha256(data).hexdigest()
        archive_id = digest(relative_path + "\0" + checksum)
        exists = conn.execute("SELECT 1 FROM app_history_archives WHERE id=?", (archive_id,)).fetchone()
        if not exists:
            conn.execute("INSERT INTO app_history_archives VALUES (?,?,?,?,?,?,?)",
                         (archive_id, relative_path, checksum, now(), len(data), data, data.decode("utf-8", errors="replace")))
        return archive_id, not bool(exists)

    def archive_file(self, path):
        path = Path(path)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Only regular history files are imported")
        resolved = path.resolve()
        relative = str(resolved.relative_to(self.history_dir))
        if path.stat().st_size > self.max_file_bytes:
            raise ValueError("History file exceeds configured byte limit: " + relative)
        data = path.read_bytes()
        if len(data) > self.max_file_bytes:
            raise ValueError("History file grew beyond configured byte limit: " + relative)
        documents, errors = [], []
        try:
            if path.suffix.lower() == ".json":
                documents = [json.loads(data)]
            elif path.suffix.lower() == ".jsonl":
                documents = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
        except (ValueError, UnicodeDecodeError):
            errors.append("Original bytes archived; structured event extraction failed for " + relative)
        imported = 0
        with self.connection(write=True) as conn:
            archive_id, created = self._archive_bytes(conn, relative, data)
            for document in documents:
                collections = {"document": document} if isinstance(document, list) else {k: document[k] for k in ("history", "execution_history", "events") if isinstance(document, dict) and isinstance(document.get(k), list)}
                if not collections:
                    collections = {"document": [document]}
                for collection, events in collections.items():
                    for event in events:
                        if isinstance(event, dict) and event.get("archive_event_id"):
                            old = conn.execute("SELECT payload_json FROM app_history_events WHERE id=?", (event["archive_event_id"],)).fetchone()
                            if old and canonical(event.get("payload")) == old[0]:
                                continue
                        key = "file:" + digest(canonical([relative, collection, event]))
                        event_type = str(event.get("event", event.get("event_type", "history.imported"))) if isinstance(event, dict) else "history.imported"
                        timestamp = event.get("timestamp", event.get("occurred_at")) if isinstance(event, dict) else None
                        if timestamp is not None:
                            timestamp = str(timestamp)
                        _, added = self._insert_event(conn, event_type, event, "file-import", timestamp, key, relative, collection)
                        imported += int(added)
        return {"path": relative, "archiveId": archive_id, "newFileVersion": created, "eventsImported": imported, "warnings": errors}

    def import_directory(self, after="", limit=100):
        if not self.history_dir.is_dir():
            raise FileNotFoundError("History directory does not exist: " + str(self.history_dir))
        paths = []
        for path in self.history_dir.rglob("*"):
            if not path.is_file() or path.is_symlink() or path.name.startswith("."):
                continue
            try:
                relative = str(path.resolve().relative_to(self.history_dir))
            except ValueError:
                continue
            if relative > after:
                paths.append((relative, path))
        paths.sort(key=lambda item: item[0])
        selected = paths[:limit]
        results, errors = [], []
        for relative, path in selected:
            try:
                results.append(self.archive_file(path))
            except (OSError, ValueError) as exc:
                errors.append({"path": relative, "error": str(exc)})
        more = len(paths) > len(selected)
        mirror = self.mirror()
        return {"files": results, "errors": errors, "hasMore": more,
                "nextCursor": selected[-1][0] if more and selected else None, **mirror}

    def mirror(self):
        # Database commits first. Failed file writes leave durable pending events.
        # Retrying this operation is safe and does not duplicate archive entries.
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
            if self.history_file.is_symlink():
                raise ValueError("Refusing to replace a symlink history file")
            lock_path = self.history_dir / ".app-history.lock"
            with lock_path.open("a+b") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                with self.connection(write=True) as conn:
                    if self.history_file.exists():
                        old_bytes = self.history_file.read_bytes()
                        if len(old_bytes) > self.max_file_bytes:
                            raise ValueError("Main history file exceeds byte limit")
                        document = json.loads(old_bytes)
                        if not isinstance(document, dict):
                            raise ValueError("Main history file must contain a JSON object")
                        self._archive_bytes(conn, self.history_file.name, old_bytes)
                    else:
                        document = {"record_id": "yone-app-history", "execution_history": []}
                    events = document.setdefault("execution_history", [])
                    if not isinstance(events, list):
                        raise ValueError("execution_history must be an array; original file retained")
                    existing_ids = {e.get("archive_event_id") for e in events if isinstance(e, dict)}
                    rows = conn.execute("SELECT * FROM app_history_events WHERE mirrored_at IS NULL ORDER BY recorded_at,id").fetchall()
                    for row in rows:
                        if row["id"] in existing_ids:
                            continue
                        payload = json.loads(row["payload_json"])
                        original_present = (row["source_path"] == self.history_file.name and
                            isinstance(document.get(row["source_collection"]), list) and
                            any(canonical(e) == row["payload_json"] for e in document[row["source_collection"]]))
                        if not original_present:
                            events.append({"id": row["id"], "archive_event_id": row["id"],
                                           "timestamp": row["occurred_at"] or row["recorded_at"],
                                           "event": row["event_type"], "source": row["source"], "payload": payload})
                    facts = conn.execute("SELECT * FROM app_history_facts ORDER BY key").fetchall()
                    context = document.setdefault("learned_context", {})
                    if not isinstance(context, dict):
                        raise ValueError("learned_context must be an object; original file retained")
                    for fact in facts:
                        context[fact["key"]] = {"value": json.loads(fact["value_json"]), "status": fact["status"],
                                                "source": fact["source"], "observed_at": fact["observed_at"]}
                    # Do not change the file on a no-op retry.
                    new_bytes = (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
                    if self.history_file.exists() and not rows and json.loads(self.history_file.read_bytes()) == document:
                        return {"historyFileSaved": True, "historyFile": str(self.history_file), "mirroredEvents": 0}
                    if len(new_bytes) > self.max_file_bytes:
                        raise ValueError("Updated history file exceeds byte limit")
                    fd, tmp = tempfile.mkstemp(prefix=".app-history-", dir=self.history_dir)
                    try:
                        with os.fdopen(fd, "wb") as output:
                            output.write(new_bytes)
                            output.flush()
                            os.fsync(output.fileno())
                        os.replace(tmp, self.history_file)
                        dirfd = os.open(self.history_dir, os.O_RDONLY)
                        try:
                            os.fsync(dirfd)
                        finally:
                            os.close(dirfd)
                    finally:
                        Path(tmp).unlink(missing_ok=True)
                    conn.execute("UPDATE app_history_events SET mirrored_at=? WHERE mirrored_at IS NULL", (now(),))
                    self._archive_bytes(conn, self.history_file.name, new_bytes)
                return {"historyFileSaved": True, "historyFile": str(self.history_file), "mirroredEvents": len(rows)}
        except (OSError, ValueError, sqlite3.Error) as exc:
            return {"historyFileSaved": False, "historyFile": str(self.history_file), "mirrorError": str(exc)}

    @staticmethod
    def _event(row):
        out = dict(row)
        out["payload"] = json.loads(out.pop("payload_json"))
        return out

    def events(self, q="", event_type=None, limit=50, offset=0):
        clauses, params = [], []
        if q:
            clauses.append("(instr(lower(payload_json),lower(?))>0 OR instr(lower(event_type),lower(?))>0)")
            params.extend([q, q])
        if event_type:
            clauses.append("event_type=?")
            params.append(event_type)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM app_history_events" + where, params).fetchone()[0]
            rows = conn.execute("SELECT * FROM app_history_events" + where + " ORDER BY recorded_at DESC,id DESC LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
        return {"total": count, "items": [self._event(r) for r in rows], "limit": limit, "offset": offset}

    def event(self, event_id):
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM app_history_events WHERE id=?", (event_id,)).fetchone()
            return self._event(row) if row else None

    def facts(self, prefix="", q=""):
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM app_history_facts WHERE substr(key,1,length(?))=? AND (instr(lower(key),lower(?))>0 OR instr(lower(value_json),lower(?))>0) ORDER BY key", (prefix, prefix, q, q)).fetchall()
        return [{**{k: r[k] for k in r.keys() if k != "value_json"}, "value": json.loads(r["value_json"])} for r in rows]

    def archives(self, q="", limit=50, offset=0):
        with self.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM app_history_archives WHERE instr(lower(searchable_text),lower(?))>0 OR instr(lower(relative_path),lower(?))>0", (q, q)).fetchone()[0]
            rows = conn.execute("SELECT id,relative_path,sha256,captured_at,size_bytes FROM app_history_archives WHERE instr(lower(searchable_text),lower(?))>0 OR instr(lower(relative_path),lower(?))>0 ORDER BY captured_at DESC,id DESC LIMIT ? OFFSET ?", (q, q, limit, offset)).fetchall()
        return {"total": count, "items": [dict(r) for r in rows], "limit": limit, "offset": offset}

    def archive(self, archive_id):
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM app_history_archives WHERE id=?", (archive_id,)).fetchone()
        return dict(row) if row else None
