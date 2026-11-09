"""Single-worker dispatcher for simulated NCIP/SIP2 events.

No real network calls, scheduling, or concurrent worker leasing.
"""

from sqlalchemy.orm import Session

from app.models.foundation import Loan
from app.models.integration import IntegrationOutbox
from app.models.foundation import utc_now
from app.services.mock_ilms import (
    ILMSOperation,
    ILMSOutcome,
    ILMSRequest,
    MockNCIPAdapter,
    MockSIP2Adapter,
)

MAX_ATTEMPTS = 3

ADAPTERS = {
    "MOCK_NCIP": MockNCIPAdapter,
    "MOCK_SIP2": MockSIP2Adapter,
}


def dispatch_outbox_event(
    db: Session,
    event_id: str,
    *,
    simulated_outcome: ILMSOutcome = ILMSOutcome.ACCEPTED,
) -> IntegrationOutbox:
    """Process a queued event; caller manages commit/rollback.

    Do not invoke this concurrently for the same event.
    """
    event = db.get(IntegrationOutbox, event_id)

    if event is None:
        raise ValueError("Outbox event not found")

    if event.status not in ("PENDING", "RETRY"):
        raise ValueError("Outbox event is not dispatchable")

    if event.attempt_count >= MAX_ATTEMPTS:
        raise ValueError("Maximum dispatch attempts reached")

    loan = db.get(Loan, event.loan_id)

    if loan is None:
        raise ValueError("Associated loan not found")

    adapter_class = ADAPTERS.get(event.provider)

    if adapter_class is None:
        raise ValueError("Unsupported mock ILMS provider")

    request = ILMSRequest(
        operation=ILMSOperation(event.operation),
        loan_id=loan.id,
        member_id=loan.member_id,
        item_id=loan.item_id,
        correlation_id=event.correlation_id,
    )

    adapter = adapter_class(simulated_outcome)
    result = adapter.execute(request)

    event.attempt_count += 1

    if result.outcome == ILMSOutcome.ACCEPTED:
        event.status = "DELIVERED"
        event.delivered_at = utc_now()
        event.last_error = None

    elif result.outcome == ILMSOutcome.REJECTED:
        event.status = "DEAD_LETTER"
        event.last_error = result.message

    elif result.outcome in (
        ILMSOutcome.TIMEOUT,
        ILMSOutcome.UNAVAILABLE,
    ):
        event.status = (
            "DEAD_LETTER"
            if event.attempt_count >= MAX_ATTEMPTS
            else "RETRY"
        )
        event.last_error = result.message

    else:
        raise ValueError("Unsupported adapter outcome")

    db.flush()
    return event
