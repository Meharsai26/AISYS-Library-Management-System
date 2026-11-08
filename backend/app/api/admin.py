from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_db, require_permission
from app.models.foundation import AuditEvent

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administration"],
)


@router.get("/audit-events")
def list_audit_events(
    limit: int = Query(default=20, ge=1, le=100),
    identity=Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
):
    events = db.scalars(
        select(AuditEvent)
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(limit)
    ).all()

    return {
        "events": [
            {
                "id": event.id,
                "action": event.action,
                "outcome": event.outcome,
                "entity_type": event.entity_type,
                "correlation_id": event.correlation_id,
                "occurred_at": event.occurred_at,
            }
            for event in events
        ]
    }
