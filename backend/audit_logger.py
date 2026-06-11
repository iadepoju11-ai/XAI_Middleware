import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, DateTime, JSON, Index,
    create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

import config


class Base(DeclarativeBase):
    pass


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    input_features = Column(JSON, nullable=False)
    decision = Column(String, nullable=False)       # "accept" | "deny"
    probability = Column(Float, nullable=False)
    shap_values = Column(JSON, nullable=False)
    fairness_flags = Column(JSON, nullable=True)
    model_version = Column(String, nullable=False)


# Append-only enforcement at ORM level
@event.listens_for(AuditRecord, "before_update")
def _block_update(mapper, connection, target):
    raise RuntimeError("AuditRecord is append-only — updates are not permitted.")


@event.listens_for(AuditRecord, "before_delete")
def _block_delete(mapper, connection, target):
    raise RuntimeError("AuditRecord is append-only — deletes are not permitted.")


engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def log_decision(
    *,
    application_id: str,
    input_features: dict,
    decision: str,
    probability: float,
    shap_values: dict,
    fairness_flags: dict | None,
    model_version: str,
) -> str:
    record = AuditRecord(
        id=str(uuid.uuid4()),
        application_id=application_id,
        timestamp=datetime.now(timezone.utc),
        input_features=input_features,
        decision=decision,
        probability=probability,
        shap_values=shap_values,
        fairness_flags=fairness_flags,
        model_version=model_version,
    )
    with SessionLocal() as session:
        session.add(record)
        session.commit()
    return application_id


def get_decision(application_id: str) -> dict | None:
    with SessionLocal() as session:
        record = (
            session.query(AuditRecord)
            .filter(AuditRecord.application_id == application_id)
            .first()
        )
        return _to_dict(record) if record else None


def list_decisions(page: int = 1, page_size: int = 20, decision_filter: str | None = None,
                   date_from: datetime | None = None, date_to: datetime | None = None) -> dict:
    with SessionLocal() as session:
        q = session.query(AuditRecord)
        if decision_filter:
            q = q.filter(AuditRecord.decision == decision_filter)
        if date_from:
            q = q.filter(AuditRecord.timestamp >= date_from)
        if date_to:
            q = q.filter(AuditRecord.timestamp <= date_to)
        total = q.count()
        records = (
            q.order_by(AuditRecord.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": [_to_dict(r) for r in records],
    }


def export_decisions(fmt: str = "json") -> list[dict]:
    with SessionLocal() as session:
        records = session.query(AuditRecord).order_by(AuditRecord.timestamp.asc()).all()
    return [_to_dict(r) for r in records]


def get_recent_decisions(n: int = 500) -> list[dict]:
    with SessionLocal() as session:
        records = (
            session.query(AuditRecord)
            .order_by(AuditRecord.timestamp.desc())
            .limit(n)
            .all()
        )
    return [_to_dict(r) for r in records]


def _to_dict(record: AuditRecord) -> dict:
    return {
        "id": record.id,
        "application_id": record.application_id,
        "timestamp": record.timestamp.isoformat(),
        "input_features": record.input_features,
        "decision": record.decision,
        "probability": record.probability,
        "shap_values": record.shap_values,
        "fairness_flags": record.fairness_flags,
        "model_version": record.model_version,
    }
