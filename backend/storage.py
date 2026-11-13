"""Persistent run snapshots and normalized audit entities; SQLite dev, Postgres production."""
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from backend.config import settings


class Base(DeclarativeBase):
    pass


class IncidentRun(Base):
    __tablename__ = "incident_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    session_hash: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class AuditEntity(Base):
    __tablename__ = "audit_entities"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class Approval(Base):
    __tablename__ = "approvals"
    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)


url = settings.database_url.get_secret_value()
if url.startswith("postgres://"):
    url = "postgresql+psycopg://" + url[len("postgres://"):]
elif url.startswith("postgresql://"):
    url = "postgresql+psycopg://" + url[len("postgresql://"):]
engine = create_engine(url, pool_pre_ping=True, **(
    {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else
    {"pool_size": 2, "max_overflow": 1, "pool_recycle": 180}
))


def initialize() -> None:
    Base.metadata.create_all(engine)


def insert_run(run: dict, session_hash: str, idempotency_key: str | None) -> None:
    with Session(engine) as db:
        db.add(IncidentRun(id=run["id"], scenario_id=run["scenario_id"], status=run["status"],
                          session_hash=session_hash, idempotency_key=idempotency_key,
                          created_at=datetime.now(UTC), payload=deepcopy(run)))
        db.commit()


def save_run(run: dict) -> None:
    run["updated_at"] = datetime.now(UTC).isoformat()
    with Session(engine) as db:
        record = db.get(IncidentRun, run["id"])
        if record is None:
            raise ValueError("Run not found")
        record.payload = deepcopy(run)
        record.status = run["status"]
        for kind, key in [("event", "events"), ("evidence", "evidence"),
                          ("hypothesis", "hypotheses"), ("tool", "tool_invocations"),
                          ("patch_attempt", "patch_attempts")]:
            for index, item in enumerate(run.get(key, [])):
                ident = f"{run['id']}:{kind}:{index}"
                if db.get(AuditEntity, ident) is None:
                    db.add(AuditEntity(id=ident, run_id=run["id"], kind=kind,
                                       sequence=index, payload=item if isinstance(item, dict) else {"value": item}))
        for kind in ("verification", "review", "report"):
            if run.get(kind) is not None:
                ident = f"{run['id']}:{kind}"
                value = run[kind] if isinstance(run[kind], dict) else {"text": run[kind]}
                db.merge(AuditEntity(id=ident, run_id=run["id"], kind=kind, sequence=0, payload=value))
        db.commit()


def get_run(run_id: str) -> dict | None:
    with Session(engine) as db:
        record = db.get(IncidentRun, run_id)
        return deepcopy(record.payload) if record else None


def find_idempotency(key: str) -> dict | None:
    with Session(engine) as db:
        record = db.scalar(select(IncidentRun).where(IncidentRun.idempotency_key == key))
        return deepcopy(record.payload) if record else None


def list_runs(limit: int = 100) -> list[dict]:
    with Session(engine) as db:
        return [deepcopy(x.payload) for x in db.scalars(
            select(IncidentRun).order_by(IncidentRun.created_at.desc()).limit(limit))]


def quota_counts(session_hash: str) -> tuple[int, int, int]:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    terminal = {"verified", "unverified", "failed", "interrupted", "awaiting_verification", "cancelled"}
    with Session(engine) as db:
        records = list(db.scalars(select(IncidentRun).where(IncidentRun.created_at >= today)))
        return len(records), sum(x.session_hash == session_hash for x in records), sum(
            x.status not in terminal for x in records)


def recover_interrupted() -> int:
    terminal = {"verified", "unverified", "failed", "interrupted", "awaiting_verification", "cancelled"}
    count = 0
    for run in list_runs(1000):
        if run["status"] not in terminal:
            run["status"] = "interrupted"
            run["error"] = "The process restarted during this investigation. Evidence is preserved; no external action was replayed."
            save_run(run)
            count += 1
    return count


def record_approval(run_id: str) -> dict[str, Any]:
    with Session(engine) as db:
        previous = db.get(Approval, run_id)
        if previous:
            return previous.payload
        result = {"status": "approved", "run_id": run_id, "created_at": datetime.now(UTC).isoformat(),
                  "note": "Owner approved the patch artifact. Production was not modified."}
        db.add(Approval(run_id=run_id, created_at=datetime.now(UTC), status="approved", payload=result))
        db.commit()
        return result
