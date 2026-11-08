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
