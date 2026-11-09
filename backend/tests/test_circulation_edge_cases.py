"""Circulation edge cases and outbox consistency."""

from sqlalchemy import func, select

from app.models.foundation import LibraryItem
from app.models.integration import IntegrationOutbox
from tests.test_auth import setup_auth
from tests.test_circulation_outbox import (
    authenticate,
    checkout,
    create_checkout,
)


def prepare_loan(setup_auth):
    client, factory, admin, _ = setup_auth
    auth = authenticate(client, admin)

    item_id, member_id = create_checkout(client, auth)
    response = checkout(client, auth, item_id, member_id)

    assert response.status_code == 201, response.text

    return client, factory, auth, item_id, response.json()["loan_id"]


def event_count(factory, loan_id):
    with factory() as db:
        return db.scalar(
            select(func.count())
            .select_from(IntegrationOutbox)
            .where(IntegrationOutbox.loan_id == loan_id)
        )


def test_returned_loan_cannot_be_renewed(setup_auth):
    client, factory, auth, _, loan_id = prepare_loan(setup_auth)

    returned = client.post(
        f"/api/v1/loans/{loan_id}/return",
        headers=auth,
    )
    assert returned.status_code == 200

    before = event_count(factory, loan_id)

    renewed = client.post(
        f"/api/v1/loans/{loan_id}/renew",
        headers=auth,
    )

    assert renewed.status_code == 409
    assert event_count(factory, loan_id) == before


def test_reference_item_cannot_be_renewed(setup_auth):
    client, factory, auth, item_id, loan_id = prepare_loan(setup_auth)

    with factory() as db:
        item = db.get(LibraryItem, item_id)
        item.is_reference = True
        db.commit()

    before = event_count(factory, loan_id)

    response = client.post(
        f"/api/v1/loans/{loan_id}/renew",
        headers=auth,
    )

    assert response.status_code == 409
    assert event_count(factory, loan_id) == before


def test_duplicate_return_creates_no_extra_event(setup_auth):
    client, factory, auth, _, loan_id = prepare_loan(setup_auth)

    first = client.post(
        f"/api/v1/loans/{loan_id}/return",
        headers=auth,
    )
    assert first.status_code == 200

    before = event_count(factory, loan_id)

    second = client.post(
        f"/api/v1/loans/{loan_id}/return",
        headers=auth,
    )

    assert second.status_code == 409
    assert event_count(factory, loan_id) == before
