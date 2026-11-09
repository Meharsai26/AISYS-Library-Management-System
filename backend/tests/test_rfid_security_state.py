"""Phase 6 synthetic RFID security-state integration tests."""

import pytest
from sqlalchemy import select

from app.models.foundation import LibraryItem, Loan
from app.models.integration import IntegrationOutbox
from app.models.rfid import RFIDTag
from tests.test_auth import setup_auth
from tests.test_circulation_outbox import (
    authenticate,
    checkout,
    create_checkout,
)


def prepare_tagged_item(setup_auth):
    client, factory, admin, _ = setup_auth
    auth = authenticate(client, admin)
    item_id, member_id = create_checkout(client, auth)

    assigned = client.post(
        "/api/v1/rfid/tags/assign",
        headers=auth,
        json={
            "item_id": item_id,
            "epc": "MOCK-EPC-PHASE6-001",
        },
    )
    assert assigned.status_code == 201, assigned.text

    return client, factory, auth, item_id, member_id


def read_security_state(factory, item_id):
    with factory() as db:
        tag = db.scalar(
            select(RFIDTag).where(RFIDTag.item_id == item_id)
        )
        assert tag is not None
        return tag.security_armed


def test_checkout_disarms_mock_tag(setup_auth):
    client, factory, auth, item_id, member_id = (
        prepare_tagged_item(setup_auth)
    )

    assert read_security_state(factory, item_id) is True

    response = checkout(client, auth, item_id, member_id)
    assert response.status_code == 201, response.text

    assert read_security_state(factory, item_id) is False


def test_return_rearms_mock_tag(setup_auth):
    client, factory, auth, item_id, member_id = (
        prepare_tagged_item(setup_auth)
    )

    checked_out = checkout(client, auth, item_id, member_id)
    assert checked_out.status_code == 201
    assert read_security_state(factory, item_id) is False

    returned = client.post(
        f"/api/v1/loans/{checked_out.json()['loan_id']}/return",
        headers=auth,
    )
    assert returned.status_code == 200, returned.text

    assert read_security_state(factory, item_id) is True


def test_duplicate_checkout_preserves_disarmed_state(setup_auth):
    client, factory, auth, item_id, member_id = (
        prepare_tagged_item(setup_auth)
    )

    first = checkout(client, auth, item_id, member_id)
    assert first.status_code == 201
    assert read_security_state(factory, item_id) is False

    second = checkout(client, auth, item_id, member_id)
    assert second.status_code == 409

    assert read_security_state(factory, item_id) is False


def test_outbox_failure_rolls_back_tag_state(
    setup_auth, monkeypatch
):
    client, factory, auth, item_id, member_id = (
        prepare_tagged_item(setup_auth)
    )

    def simulate_failure(*args, **kwargs):
        raise RuntimeError("Synthetic outbox failure")

    monkeypatch.setattr(
        "app.api.circulation.queue_ilms_event",
        simulate_failure,
    )

    with pytest.raises(
        RuntimeError,
        match="Synthetic outbox failure",
    ):
        checkout(client, auth, item_id, member_id)

    assert read_security_state(factory, item_id) is True

    with factory() as db:
        item = db.get(LibraryItem, item_id)
        assert item.status == "AVAILABLE"

        assert db.scalars(
            select(Loan).where(Loan.item_id == item_id)
        ).all() == []

        assert db.scalars(
            select(IntegrationOutbox)
        ).all() == []
