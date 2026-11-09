import pytest
from sqlalchemy.exc import IntegrityError

from app.models.foundation import Member
from tests.test_auth import (
    create_circulation_records,
    headers,
    login,
    setup_auth,
)


def get_admin_token(client, username):
    response = login(client, username, "SyntheticAdminPass123!")
    assert response.status_code == 200
    return response.json()["access_token"]


def set_fine(factory, member_id, paise):
    with factory() as db:
        member = db.get(Member, member_id)
        assert member is not None
        member.fine_balance_paise = paise
        db.commit()


def checkout(client, token, item_id, member_id):
    return client.post(
        "/api/v1/loans/checkout",
        headers=headers(token),
        json={
            "item_id": item_id,
            "member_id": member_id,
        },
    )


@pytest.mark.parametrize(
    "fine_paise, expected_status",
    [
        (0, 201),
        (50000, 201),
        (50001, 409),
        (75000, 409),
    ],
)
def test_checkout_fine_threshold(
    setup_auth, fine_paise, expected_status
):
    client, factory, admin, _ = setup_auth
    token = get_admin_token(client, admin)

    item_id, member_id = create_circulation_records(
        client, token
    )

    set_fine(factory, member_id, fine_paise)

    response = checkout(
        client, token, item_id, member_id
    )

    assert response.status_code == expected_status, response.text

    if expected_status == 409:
        assert response.json()["detail"] == "Fine limit exceeded"


def test_renewal_rejected_above_fine_limit(setup_auth):
    client, factory, admin, _ = setup_auth
    token = get_admin_token(client, admin)

    item_id, member_id = create_circulation_records(
        client, token
    )

    checked_out = checkout(
        client, token, item_id, member_id
    )
    assert checked_out.status_code == 201

    loan_id = checked_out.json()["loan_id"]

    set_fine(factory, member_id, 50001)

    response = client.post(
        f"/api/v1/loans/{loan_id}/renew",
        headers=headers(token),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Fine limit exceeded"


def test_renewal_allowed_at_fine_limit(setup_auth):
    client, factory, admin, _ = setup_auth
    token = get_admin_token(client, admin)

    item_id, member_id = create_circulation_records(
        client, token
    )

    checked_out = checkout(
        client, token, item_id, member_id
    )
    assert checked_out.status_code == 201

    loan_id = checked_out.json()["loan_id"]

    set_fine(factory, member_id, 50000)

    response = client.post(
        f"/api/v1/loans/{loan_id}/renew",
        headers=headers(token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["renewed_count"] == 1


def test_return_allowed_above_fine_limit(setup_auth):
    client, factory, admin, _ = setup_auth
    token = get_admin_token(client, admin)

    item_id, member_id = create_circulation_records(
        client, token
    )

    checked_out = checkout(
        client, token, item_id, member_id
    )
    assert checked_out.status_code == 201

    loan_id = checked_out.json()["loan_id"]

    set_fine(factory, member_id, 75000)

    response = client.post(
        f"/api/v1/loans/{loan_id}/return",
        headers=headers(token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "RETURNED"


def test_negative_fine_rejected_by_database(setup_auth):
    _, factory, _, _ = setup_auth

    with factory() as db:
        member = Member(
            card_number="NEG-FINE-TEST",
            display_name="Synthetic Negative Fine Test",
            status="ACTIVE",
            fine_balance_paise=-1,
        )
        db.add(member)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()
