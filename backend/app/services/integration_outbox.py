"""Transactional outbox helpers for simulated ILMS integration."""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.integration import IntegrationOutbox
from app.services.mock_ilms import ILMSOperation


def queue_ilms_event(
    db: Session,
    *,
    loan_id: str,
    operation: ILMSOperation,
    provider: str = "MOCK_NCIP",
    correlation_id: str | None = None,
) -> IntegrationOutbox:
    """Stage an outbox event in the caller's transaction.

    This function never commits or dispatches network requests.
    The caller is responsible for committing or rolling back.
    """
    operation = ILMSOperation(operation)

    if provider not in ("MOCK_NCIP", "MOCK_SIP2"):
        raise ValueError("Unsupported mock ILMS provider")

    if not isinstance(loan_id, str) or not loan_id.strip():
        raise ValueError("loan_id is required")

    if correlation_id is None:
        correlation_id = str(uuid4())

    event = IntegrationOutbox(
        loan_id=loan_id,
        operation=operation.value,
        provider=provider,
        correlation_id=correlation_id,
        status="PENDING",
        attempt_count=0,
    )

    db.add(event)
    db.flush()

    return event
