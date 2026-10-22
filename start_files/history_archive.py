"""FastAPI endpoints and CLI for the existing app database's history tables."""
import argparse
import json
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlsplit

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .history_store import ConflictError, HistoryStore, canonical

APP_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(APP_ROOT / ".env")
bearer = HTTPBearer(auto_error=False)


def require_key(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    configured = os.getenv("HISTORY_API_KEY") or os.getenv("FASTAPI_API") or os.getenv("API_KEY")
    if not configured or configured.startswith(("http://", "https://")):
        raise HTTPException(status_code=503, detail="Configure HISTORY_API_KEY or an existing secret FASTAPI_API/API_KEY")
    if creds is None or not secrets.compare_digest(creds.credentials, configured):
        raise HTTPException(status_code=401, detail="Invalid API key", headers={"WWW-Authenticate": "Bearer"})


def database_path():
    explicit = os.getenv("APP_DATABASE_PATH")
    if explicit:
        return Path(explicit).expanduser().resolve()
    configured = os.getenv("DATABASE_URL")
    if configured:
        # Refuse to pretend a SQLite adapter supports Neon/PostgreSQL.
        parsed = urlsplit(configured)
        if parsed.scheme not in {"sqlite", "sqlite+pysqlite"}:
            raise RuntimeError("This package targets the existing SQLite database shown in your app. A PostgreSQL DATABASE_URL requires a PostgreSQL adapter.")
        if parsed.netloc or parsed.query or parsed.fragment:
            raise RuntimeError("Set APP_DATABASE_PATH explicitly for this SQLite URL")
        path = unquote(parsed.path)
        if path.startswith("//"):
            return Path(path[1:]).resolve()
        return (APP_ROOT / path.lstrip("/")).resolve()
    # This is the exact database used by both pasted MLS modules.
    return APP_ROOT / "databases" / "brightmls.db"


@lru_cache(maxsize=1)
def store():
    directory = Path(os.getenv("APP_HISTORY_DIR", str(APP_ROOT / "history")))
    filename = os.getenv("APP_HISTORY_FILE", "n8n_dns_foundation_history.json")
    return HistoryStore(database_path(), directory, filename,
                        int(os.getenv("APP_HISTORY_MAX_FILE_BYTES", str(64 * 1024 * 1024))))


router = APIRouter(prefix="/api/history", tags=["Application history"], dependencies=[Depends(require_key)])


class EventInput(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=250)
    payload: Any
    source: str = Field("n8n", min_length=1, max_length=250)
    occurred_at: Optional[str] = Field(None, max_length=100)
    idempotency_key: Optional[str] = Field(None, min_length=1, max_length=500)


class FactInput(BaseModel):
    key: str = Field(..., min_length=1, max_length=500)
    value: Any
    status: str = "reported"
    source: str = Field(..., min_length=1, max_length=500)
    observed_at: str = Field(..., min_length=1, max_length=100)


def small_payload(payload):
    if len(canonical(payload).encode("utf-8")) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Event/fact payload exceeds 2 MiB")


@router.get("/health")
def health():
    try:
        return {"ok": True, **store().stats()}
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/events")
def create_event(event: EventInput):
    small_payload(event.payload)
    try:
        return store().save_event(event.event_type, event.payload, event.source, event.occurred_at, event.idempotency_key)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/events")
def events(q: str = Query("", max_length=500), event_type: Optional[str] = None,
           limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return store().events(q, event_type, limit, offset)


@router.get("/events/{event_id}")
def event(event_id: str):
    result = store().event(event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="History event not found")
    return result


@router.post("/facts")
def create_fact(fact: FactInput):
    small_payload(fact.value)
    try:
        return store().save_fact(fact.key, fact.value, fact.status, fact.source, fact.observed_at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/facts")
def facts(prefix: str = Query("", max_length=500), q: str = Query("", max_length=500)):
    return {"items": store().facts(prefix, q)}


@router.get("/context")
def context(prefix: str = Query("", max_length=500), q: str = Query("", max_length=500)):
    """Fetch evidence-labeled facts for an n8n/AI task before making changes."""
    return {"facts": store().facts(prefix, q), "history": store().events(q, limit=20),
            "note": "Facts are snapshots. Re-read live DNS or routing before applying changes; planned facts are not completed actions."}


@router.post("/import")
def import_history(after: str = Query("", max_length=2000), limit: int = Query(100, ge=1, le=1000)):
    try:
        return store().import_directory(after, limit)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/sync")
def sync_file():
    return store().mirror()


@router.get("/archives")
def archives(q: str = Query("", max_length=500), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return store().archives(q, limit, offset)


@router.get("/archives/{archive_id}")
def download_archive(archive_id: str):
    result = store().archive(archive_id)
    if result is None:
        raise HTTPException(status_code=404, detail="File version not found")
    return Response(content=result["original_bytes"], media_type="application/octet-stream",
                    headers={"X-Content-SHA256": result["sha256"],
                             "Content-Disposition": 'attachment; filename="history-archive-' + result["id"] + '.bin"'})


def main():
    parser = argparse.ArgumentParser(description="Archive history in your existing FastAPI SQLite database")
    parser.add_argument("command", choices=["init", "import", "seed", "status", "sync"])
    parser.add_argument("--seed-file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = store().initialize()
        elif args.command == "seed":
            if not args.seed_file:
                parser.error("seed requires --seed-file")
            result = store().seed_facts(json.loads(args.seed_file.read_text())["facts"])
        elif args.command == "import":
            batches, cursor = [], ""
            while True:
                result = store().import_directory(cursor, 100)
                batches.append(result)
                if not result["hasMore"]:
                    break
                cursor = result["nextCursor"]
            result = {"batches": batches, "stats": store().stats(),
                      "ok": all(not b["errors"] and b["historyFileSaved"] for b in batches)}
        elif args.command == "sync":
            result = store().mirror()
        else:
            result = store().stats()
        print(json.dumps(result, indent=2))
        if result.get("historyFileSaved") is False or result.get("ok") is False:
            raise SystemExit(1)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
