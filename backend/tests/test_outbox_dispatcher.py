"""Tests for manually dispatched mock NCIP/SIP2 events."""

import pytest
from sqlalchemy import select

from app.models.integration import IntegrationOutbox
from app.services.mock_ilms import ILMSOutcome
from app.services.outbox_dispatcher import (
    MAX_ATTEMPTS,
    dispatch_outbox_event,
)
from tests.test_auth import setup_auth
from tests.test_circulation_outbox import (
    authenticate,
    checkout,
    create_checkout,
)


@pytest.fixture
def pending_event(setup_auth):
    client, factory, admin, _ = setup_auth
    auth = authenticate(client, admin)
    item_id, member_id = create_checkout(client, auth)

    response = checkout(client, auth, item_id, member_id)
    assert response.status_code == 201

    loan_id = response.json()["loan_id"]

    with factory() as db:
        event = db.scalar(
            select(IntegrationOutbox).where(
                IntegrationOutbox.loan_id == loan_id
            )
        )
        assert event is not None
        event_id = event.id

    return factory, event_id


def read_event(factory, event_id):
    with factory() as db:
        event = db.get(IntegrationOutbox, event_id)
        assert event is not None
        return {
            "status": event.status,
            "attempt_count": event.attempt_count,
            "last_error": event.last_error,
            "delivered_at": event.delivered_at,
            "provider": event.provider,
        }


def dispatch(factory, event_id, outcome):
    with factory() as db:
        event = dispatch_outbox_event(
            db,
            event_id,
            simulated_outcome=outcome,
        )
        result = (event.status, event.attempt_count)
        db.commit()
        return result


def test_accepted_event_is_delivered(pending_event):
    factory, event_id = pending_event

    result = dispatch(
        factory, event_id, ILMSOutcome.ACCEPTED
    )

    assert result == ("DELIVERED", 1)

    event = read_event(factory, event_id)
    assert event["status"] == "DELIVERED"
    assert event["attempt_count"] == 1
    assert event["delivered_at"] is not None
    assert event["last_error"] is None


def test_timeout_then_success(pending_event):
    factory, event_id = pending_event

    assert dispatch(
        factory, event_id, ILMSOutcome.TIMEOUT
    ) == ("RETRY", 1)

    retry_event = read_event(factory, event_id)
    assert "timeout" in retry_event["last_error"].lower()

    assert dispatch(
        factory, event_id, ILMSOutcome.ACCEPTED
    ) == ("DELIVERED", 2)


def test_unavailable_reaches_dead_letter(pending_event):
    factory, event_id = pending_event
    assert MAX_ATTEMPTS == 3

    for expected_attempt in range(1, MAX_ATTEMPTS + 1):
        status, count = dispatch(
            factory,
            event_id,
            ILMSOutcome.UNAVAILABLE,
        )

        assert count == expected_attempt

        if expected_attempt < MAX_ATTEMPTS:
            assert status == "RETRY"
        else:
            assert status == "DEAD_LETTER"

    event = read_event(factory, event_id)
    assert event["attempt_count"] == MAX_ATTEMPTS
    assert event["delivered_at"] is None
    assert "unavailable" in event["last_error"].lower()


def test_rejection_dead_letters_immediately(pending_event):
    factory, event_id = pending_event

    result = dispatch(
        factory, event_id, ILMSOutcome.REJECTED
    )

    assert result == ("DEAD_LETTER", 1)


def test_delivered_event_cannot_dispatch_again(pending_event):
    factory, event_id = pending_event

    dispatch(factory, event_id, ILMSOutcome.ACCEPTED)

    with factory() as db:
        with pytest.raises(
            ValueError,
            match="not dispatchable",
        ):
            dispatch_outbox_event(db, event_id)

    assert read_event(factory, event_id)["attempt_count"] == 1


def test_dead_letter_cannot_dispatch_again(pending_event):
    factory, event_id = pending_event

    dispatch(factory, event_id, ILMSOutcome.REJECTED)

    with factory() as db:
        with pytest.raises(
            ValueError,
            match="not dispatchable",
        ):
            dispatch_outbox_event(db, event_id)


def test_dispatch_rollback_preserves_pending_event(pending_event):
    factory, event_id = pending_event

    with factory() as db:
        event = dispatch_outbox_event(
            db,
            event_id,
            simulated_outcome=ILMSOutcome.ACCEPTED,
        )
        assert event.status == "DELIVERED"
        db.rollback()

    persisted = read_event(factory, event_id)
    assert persisted["status"] == "PENDING"
    assert persisted["attempt_count"] == 0
    assert persisted["delivered_at"] is None


def test_mock_sip2_delivery(pending_event):
    factory, event_id = pending_event

    with factory() as db:
        event = db.get(IntegrationOutbox, event_id)
        event.provider = "MOCK_SIP2"
        db.commit()

    assert dispatch(
        factory, event_id, ILMSOutcome.ACCEPTED
    ) == ("DELIVERED", 1)

    assert read_event(factory, event_id)["provider"] == "MOCK_SIP2"


def test_unknown_event_is_rejected(pending_event):
    factory, _ = pending_event

    with factory() as db:
        with pytest.raises(
            ValueError,
            match="not found",
        ):
            dispatch_outbox_event(
                db,
                "00000000-0000-0000-0000-000000000000",
            )
