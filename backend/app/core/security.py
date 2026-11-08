import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.auth import AuthSession
from app.models.foundation import (
    AuditEvent, Permission, Role, RolePermission,
    UserAccount, UserRole,
)

password_hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def now_utc():
    return datetime.now(timezone.utc)


def as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def hash_password(password):
    return password_hasher.hash(password)


def verify_password(password, stored_hash):
    if not stored_hash:
        return False
    try:
        return password_hasher.verify(stored_hash, password)
    except VerificationError:
        return False


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def record_audit(db, action, outcome, actor_id=None,
                 entity_type="AUTH", entity_id=None):
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome=outcome,
        correlation_id=secrets.token_hex(16),
        occurred_at=now_utc(),
    )
    db.add(event)


def issue_session(db, user):
    token = secrets.token_urlsafe(32)
    current = now_utc()

    session = AuthSession(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        created_at=current,
        last_seen_at=current,
        expires_at=current + timedelta(
            minutes=settings.session_absolute_minutes
        ),
        is_revoked=False,
    )
    db.add(session)
    return token


def get_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    digest = hashlib.sha256(
        credentials.credentials.encode()
    ).hexdigest()

    session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == digest)
    )

    if session is None or session.is_revoked:
        raise HTTPException(status_code=401, detail="Invalid session")

    current = now_utc()

    if (
        current >= as_utc(session.expires_at)
        or current - as_utc(session.last_seen_at)
        >= timedelta(minutes=settings.session_idle_minutes)
    ):
        session.is_revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")

    user = db.get(UserAccount, session.user_id)

    if user is None or not user.is_active:
        session.is_revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Inactive account")

    session.last_seen_at = current
    db.commit()

    permissions = set(
        db.scalars(
            select(Permission.code)
            .join(
                RolePermission,
                Permission.code == RolePermission.permission_code,
            )
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        ).all()
    )

    return {
        "user": user,
        "session": session,
        "permissions": permissions,
    }


def require_permission(permission):
    def checker(identity=Depends(get_identity)):
        if permission not in identity["permissions"]:
            raise HTTPException(
                status_code=403,
                detail="Permission denied",
            )
        return identity
    return checker
