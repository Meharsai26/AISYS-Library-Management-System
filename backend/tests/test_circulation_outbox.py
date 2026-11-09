"""Integration tests for atomic circulation/outbox writes."""

import pytest
from sqlalchemy import select

from app.models.foundation import AuditEvent, LibraryItem, Loan
from app.models.integration import IntegrationOutbox
from tests.test_auth import (
    create_circulation_records,
    headers,
    login,
    setup_auth,
)


def authenticate(client, username):
    response = login(
        client, username, "SyntheticAdminPass123!"
    )
    assert response.status_code == 200
    return headers(response.json()["access_token"])


def create_checkout(client, auth):
    book = client.post(
        "/api/v1/bibliographic-records",
        headers=auth,
        json={"title": "Synthetic Outbox Test"},
    )
    assert book.status_code == 201

    item = client.post(
        "/api/v1/items",
        headers=auth,
        json={
            "bib_id": book.json()["id"],
            "accession_number": "OUTBOX-001",
        },
    )
    assert item.status_code == 201

    member = client.post(
        "/api/v1/members",
        headers=auth,
        json={
            "card_number": "OUTBOX-MEMBER-001",
            "display_name": "Synthetic Outbox Member",
        },
    )
    assert member.status_code == 201

    return item.json()["id"], member.json()["id"]


def checkout(client, auth, item_id, member_id):
    return client.post(
        "/api/v1/loans/checkout",
        headers=auth,
        json={"item_id": item_id, "member_id": member_id},
    )


def test_checkout_creates_pending_outbox_event(setup_auth):
    client, factory, admin, _ = setup_auth
    auth = authenticate(client, admin)
    item_id, member_id = create_checkout(client, auth)

    response = checkout(client, auth, item_id, member_id)

    assert response.status_code == 201, response.text
    assert response.json()["integration_status"] == "QUEUED"

    loan_id = response.json()["loan_id"]

    with factory() as db:
        events = db.scalars(
            select(IntegrationOutbox).where(
                IntegrationOutbox.loan_id == loan_id
            )
        ).all()

        assert len(events) == 1
        assert events[0].operation == "CHECKOUT"
        assert events[0].provider == "MOCK_NCIP"
        assert events[0].status == "PENDING"
        assert events[0].attempt_count == 0
        assert events[0].correlation_id


def test_return_and_renewal_create_distinct_events(setup_auth):
    client, factory, admin, _ = setup_auth
    auth = authenticate(client, admin)
    item_id, member_id = create_checkout(client, auth)

    checked_out = checkout(client, auth, item_id, member_id)
    assert checked_out.status_code == 201

    loan_id = checked_out.json()["loan_id"]

    renewed = client.post(
        f"/api/v1/loans/{loan_id}/renew",
        headers=auth,
    )
    assert renewed.status_code == 200
    assert renewed.json()["integration_status"] == "QUEUED"

    returned = client.post(
        f"/api/v1/loans/{loan_id}/return",
        headers=auth,
    )
    assert returned.status_code == 200
    assert returned.json()["integration_status"] == "QUEUED"

    with factory() as db:
        events = db.scalars(
            select(IntegrationOutbox).where(
                IntegrationOutbox.loan_id == loan_id
            )
        ).all()

        assert len(events) == 3
        assert {e.operation for e in events} == {
            "CHECKOUT", "RENEW", "CHECKIN"
        }
        assert all(e.status == "PENDING" for e in events)
        assert len({e.id for e in events}) == 3


def test_rejected_checkout_does_not_queue_event(setup_auth):
    client, factory, admin, _ = setup_auth
    auth = authenticate(client, admin)
    item_id, member_id = create_checkout(client, auth)

    first = checkout(client, auth, item_id, member_id)
    assert first.status_code == 201

    second = checkout(client, auth, item_id, member_id)
    assert second.status_code == 409

    with factory() as db:
        events = db.scalars(
            select(IntegrationOutbox)
        ).all()
        assert len(events) == 1


def test_outbox_failure_rolls_back_checkout(
    setup_auth, monkeypatch
):
    client, factory, admin, _ = setup_auth
    auth = authenticate(client, admin)
    item_id, member_id = create_checkout(client, auth)

    def simulate_failure(*args, **kwargs):
        raise RuntimeError("Synthetic outbox write failure")

    monkeypatch.setattr(
        "app.api.circulation.queue_ilms_event",
        simulate_failure,
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic outbox write failure",
    ):
        checkout(client, auth, item_id, member_id)

    with factory() as db:
        item = db.get(LibraryItem, item_id)
        assert item.status == "AVAILABLE"

        loans = db.scalars(
            select(Loan).where(Loan.item_id == item_id)
        ).all()
        assert loans == []

        events = db.scalars(
            select(IntegrationOutbox)
        ).all()
        assert events == []

        checkout_audits = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "LOAN_CHECKOUT"
            )
        ).all()
        assert checkout_audits == []
