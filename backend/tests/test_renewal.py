from datetime import datetime, timedelta

from sqlalchemy import select

from tests.test_auth import (
    create_circulation_records,
    headers,
    login,
    setup_auth,
)
from app.models.foundation import AuditEvent, Loan, Member


def admin_token(client, username):
    response = login(client, username, "SyntheticAdminPass123!")
    assert response.status_code == 200
    return response.json()["access_token"]


def checkout_loan(client, token):
    item_id, member_id = create_circulation_records(client, token)

    response = client.post(
        "/api/v1/loans/checkout",
        headers=headers(token),
        json={"item_id": item_id, "member_id": member_id},
    )
    assert response.status_code == 201

    return response.json()["loan_id"], member_id


def renew(client, token, loan_id):
    return client.post(
        f"/api/v1/loans/{loan_id}/renew",
        headers=headers(token),
    )


def test_renewal_extends_due_date_and_records_audit(setup_auth):
    client, factory, admin, _ = setup_auth
    token = admin_token(client, admin)
    loan_id, _ = checkout_loan(client, token)

    with factory() as db:
        original_due = db.get(Loan, loan_id).due_at

    response = renew(client, token, loan_id)

    assert response.status_code == 200, response.text
    assert response.json()["renewed_count"] == 1

    with factory() as db:
        loan = db.get(Loan, loan_id)
        assert loan.renewed_count == 1
        assert loan.due_at == original_due + timedelta(days=14)

        audit = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "LOAN_RENEWAL",
                AuditEvent.entity_id == loan_id,
            )
        )
        assert audit is not None
        assert audit.outcome == "SUCCESS"


def test_maximum_renewal_limit(setup_auth):
    client, factory, admin, _ = setup_auth
    token = admin_token(client, admin)
    loan_id, _ = checkout_loan(client, token)

    assert renew(client, token, loan_id).status_code == 200
    assert renew(client, token, loan_id).status_code == 200

    denied = renew(client, token, loan_id)

    assert denied.status_code == 409
    assert "Maximum renewals" in denied.json()["detail"]

    with factory() as db:
        assert db.get(Loan, loan_id).renewed_count == 2


def test_returned_loan_cannot_be_renewed(setup_auth):
    client, _, admin, _ = setup_auth
    token = admin_token(client, admin)
    loan_id, _ = checkout_loan(client, token)

    returned = client.post(
        f"/api/v1/loans/{loan_id}/return",
        headers=headers(token),
    )
    assert returned.status_code == 200

    response = renew(client, token, loan_id)

    assert response.status_code == 409
    assert "already returned" in response.json()["detail"]


def test_blocked_member_cannot_renew(setup_auth):
    client, factory, admin, _ = setup_auth
    token = admin_token(client, admin)
    loan_id, member_id = checkout_loan(client, token)

    with factory() as db:
        member = db.get(Member, member_id)
        member.status = "BLOCKED"
        db.commit()

    response = renew(client, token, loan_id)

    assert response.status_code == 409
    assert "not eligible" in response.json()["detail"]

    with factory() as db:
        assert db.get(Loan, loan_id).renewed_count == 0


def test_unknown_loan_returns_404(setup_auth):
    client, _, admin, _ = setup_auth
    token = admin_token(client, admin)

    response = renew(
        client, token, "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


def test_renewal_requires_authentication(setup_auth):
    client, _, _, _ = setup_auth

    response = client.post(
        "/api/v1/loans/unknown/renew"
    )

    assert response.status_code == 401
