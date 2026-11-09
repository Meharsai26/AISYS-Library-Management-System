import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import login_attempts
from app.core.security import get_db, hash_password
from app.db.session import Base
from app.main import app
from app.models.foundation import (
    AuditEvent, Permission, Role, RolePermission,
    UserAccount, UserRole,
)

@pytest.fixture
def setup_auth():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    with TestingSession() as db:
        admin_role = Role(code="ADMIN")
        librarian_role = Role(code="LIBRARIAN")
        db.add_all([admin_role, librarian_role])
        db.flush()

        permission = Permission(code="audit:read")
        for code in [
            "catalog:read",
            "catalog:write",
            "member:read",
            "member:write",
            "circulation:write", "tag:read", "tag:write",
        ]:
            db.add(Permission(code=code))
            db.flush()
            db.add(
                RolePermission(
                    role_id=admin_role.id,
                    permission_code=code,
                )
            )
        db.add(permission)
        db.flush()

        db.add(RolePermission(
            role_id=admin_role.id,
            permission_code="audit:read",
        ))

        admin_username = "test_admin_" + secrets.token_hex(5)
        librarian_username = "test_librarian_" + secrets.token_hex(5)

        for username, password, role in [
            (admin_username, "SyntheticAdminPass123!", admin_role),
            (librarian_username, "SyntheticLibrarianPass123!", librarian_role),
        ]:
            user = UserAccount(
                username=username,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id))

        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    login_attempts.clear()

    try:
        with TestClient(app) as client:
            yield client, TestingSession, admin_username, librarian_username
    finally:
        app.dependency_overrides.clear()
        login_attempts.clear()
        engine.dispose()


def login(client, username, password):
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_and_current_user(setup_auth):
    client, _, admin, _ = setup_auth

    response = login(client, admin, "SyntheticAdminPass123!")
    assert response.status_code == 200

    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers=headers(token))

    assert me.status_code == 200
    assert me.json()["username"] == admin
    assert "audit:read" in me.json()["permissions"]


def test_invalid_password(setup_auth):
    client, _, admin, _ = setup_auth

    response = login(client, admin, "WrongPassword123!")

    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_missing_authentication(setup_auth):
    client, _, _, _ = setup_auth

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_logout_revokes_session(setup_auth):
    client, _, admin, _ = setup_auth

    response = login(client, admin, "SyntheticAdminPass123!")
    token = response.json()["access_token"]

    logout = client.post(
        "/api/v1/auth/logout",
        headers=headers(token),
    )
    assert logout.status_code == 200

    after_logout = client.get(
        "/api/v1/auth/me",
        headers=headers(token),
    )
    assert after_logout.status_code == 401


def test_librarian_cannot_read_audit(setup_auth):
    client, _, _, librarian = setup_auth

    response = login(
        client, librarian, "SyntheticLibrarianPass123!"
    )
    token = response.json()["access_token"]

    audit = client.get(
        "/api/v1/admin/audit-events",
        headers=headers(token),
    )

    assert audit.status_code == 403


def test_admin_can_read_audit(setup_auth):
    client, _, admin, _ = setup_auth

    response = login(client, admin, "SyntheticAdminPass123!")
    token = response.json()["access_token"]

    audit = client.get(
        "/api/v1/admin/audit-events",
        headers=headers(token),
    )

    assert audit.status_code == 200
    assert isinstance(audit.json()["events"], list)


def test_login_creates_audit_event(setup_auth):
    client, TestingSession, admin, _ = setup_auth

    response = login(client, admin, "SyntheticAdminPass123!")
    assert response.status_code == 200

    with TestingSession() as db:
        events = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "AUTH_LOGIN",
                AuditEvent.outcome == "SUCCESS",
            )
        ).all()

        assert len(events) == 1


def test_create_and_list_book(setup_auth):
    client, _, admin, _ = setup_auth
    token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    response = client.post(
        "/api/v1/bibliographic-records",
        headers=headers(token),
        json={
            "title": "Synthetic Library Book",
            "author": "Demo Author",
            "isbn": "9780000000001",
        },
    )

    assert response.status_code == 201

    books = client.get(
        "/api/v1/bibliographic-records",
        headers=headers(token),
    )

    assert books.status_code == 200
    assert len(books.json()) == 1


def test_create_item(setup_auth):
    client, _, admin, _ = setup_auth
    token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    book = client.post(
        "/api/v1/bibliographic-records",
        headers=headers(token),
        json={"title": "Synthetic RFID Book"},
    )

    assert book.status_code == 201

    item = client.post(
        "/api/v1/items",
        headers=headers(token),
        json={
            "bib_id": book.json()["id"],
            "accession_number": "SYN-ITEM-001",
        },
    )

    assert item.status_code == 201
    assert item.json()["status"] == "AVAILABLE"


def test_create_member(setup_auth):
    client, _, admin, _ = setup_auth
    token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    response = client.post(
        "/api/v1/members",
        headers=headers(token),
        json={
            "card_number": "SYN-MEMBER-001",
            "display_name": "Synthetic Member",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "ACTIVE"


def create_circulation_records(client, token, reference=False):
    auth = headers(token)

    book = client.post(
        "/api/v1/bibliographic-records",
        headers=auth,
        json={"title": "Synthetic Circulation Test"},
    )
    assert book.status_code == 201

    item = client.post(
        "/api/v1/items",
        headers=auth,
        json={
            "bib_id": book.json()["id"],
            "accession_number": "CIRC-001",
            "is_reference": reference,
        },
    )
    assert item.status_code == 201

    member = client.post(
        "/api/v1/members",
        headers=auth,
        json={
            "card_number": "CIRC-MEMBER-001",
            "display_name": "Synthetic Borrower",
        },
    )
    assert member.status_code == 201

    return item.json()["id"], member.json()["id"]


def test_checkout_success_and_duplicate_prevention(setup_auth):
    client, _, admin, _ = setup_auth
    token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    item_id, member_id = create_circulation_records(
        client, token
    )

    payload = {"item_id": item_id, "member_id": member_id}

    first = client.post(
        "/api/v1/loans/checkout",
        headers=headers(token),
        json=payload,
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/loans/checkout",
        headers=headers(token),
        json=payload,
    )
    assert duplicate.status_code == 409


def test_reference_item_checkout_denied(setup_auth):
    client, _, admin, _ = setup_auth
    token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    item_id, member_id = create_circulation_records(
        client, token, reference=True
    )

    response = client.post(
        "/api/v1/loans/checkout",
        headers=headers(token),
        json={"item_id": item_id, "member_id": member_id},
    )

    assert response.status_code == 409


def test_checkout_and_return(setup_auth):
    client, _, admin, _ = setup_auth
    token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    item_id, member_id = create_circulation_records(
        client, token
    )

    checkout = client.post(
        "/api/v1/loans/checkout",
        headers=headers(token),
        json={"item_id": item_id, "member_id": member_id},
    )
    assert checkout.status_code == 201

    loan_id = checkout.json()["loan_id"]

    returned = client.post(
        f"/api/v1/loans/{loan_id}/return",
        headers=headers(token),
    )

    assert returned.status_code == 200
    assert returned.json()["status"] == "RETURNED"

    second_return = client.post(
        f"/api/v1/loans/{loan_id}/return",
        headers=headers(token),
    )
    assert second_return.status_code == 409

    items = client.get(
        "/api/v1/items",
        headers=headers(token),
    )
    assert items.json()[0]["status"] == "AVAILABLE"


def test_mock_rfid_assignment_and_scan(setup_auth):
    client, _, admin, _ = setup_auth
    token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    item_id, _ = create_circulation_records(client, token)
    auth = headers(token)

    assigned = client.post(
        "/api/v1/rfid/tags/assign",
        headers=auth,
        json={"item_id": item_id, "epc": "MOCK-EPC-TEST001"},
    )

    assert assigned.status_code == 201
    assert assigned.json()["hardware_connected"] is False

    scanned = client.post(
        "/api/v1/rfid/scans/mock",
        headers=auth,
        json={"epc": "MOCK-EPC-TEST001"},
    )

    assert scanned.status_code == 200
    assert scanned.json()["item_id"] == item_id
    assert scanned.json()["source"] == "MOCK"
    assert scanned.json()["hardware_connected"] is False


def test_mock_rfid_duplicate_assignment_rejected(setup_auth):
    client, _, admin, _ = setup_auth
    token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    item_id, _ = create_circulation_records(client, token)
    auth = headers(token)

    payload = {"item_id": item_id, "epc": "MOCK-EPC-DUP001"}

    first = client.post(
        "/api/v1/rfid/tags/assign",
        headers=auth,
        json=payload,
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/rfid/tags/assign",
        headers=auth,
        json=payload,
    )
    assert duplicate.status_code == 409


def test_mock_rfid_unknown_tag_and_access_control(setup_auth):
    client, _, admin, librarian = setup_auth
    admin_token = login(
        client, admin, "SyntheticAdminPass123!"
    ).json()["access_token"]

    unknown = client.post(
        "/api/v1/rfid/scans/mock",
        headers=headers(admin_token),
        json={"epc": "MOCK-EPC-UNKNOWN"},
    )
    assert unknown.status_code == 404

    librarian_token = login(
        client, librarian, "SyntheticLibrarianPass123!"
    ).json()["access_token"]

    forbidden = client.post(
        "/api/v1/rfid/tags/assign",
        headers=headers(librarian_token),
        json={
            "item_id": "nonexistent-item",
            "epc": "MOCK-EPC-DENIED",
        },
    )
    assert forbidden.status_code == 403
