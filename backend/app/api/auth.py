import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    get_db, get_identity, hash_password, issue_session,
    record_audit, verify_password,
)
from app.models.foundation import UserAccount

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Demonstration-only, per-process rate limiting.
# A production deployment needs shared persistent rate limiting.
login_attempts = defaultdict(deque)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    key = username.casefold()
    attempts = login_attempts[key]
    current_time = time.monotonic()

    while attempts and current_time - attempts[0] > 60:
        attempts.popleft()

    if len(attempts) >= 5:
        record_audit(db, "AUTH_LOGIN", "RATE_LIMITED")
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts")

    user = db.scalar(
        select(UserAccount).where(UserAccount.username == username)
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        attempts.append(current_time)
        record_audit(db, "AUTH_LOGIN", "DENIED")
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    attempts.clear()
    token = issue_session(db, user)
    record_audit(db, "AUTH_LOGIN", "SUCCESS", user.id)
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/me")
def me(identity=Depends(get_identity)):
    return {
        "id": identity["user"].id,
        "username": identity["user"].username,
        "permissions": sorted(identity["permissions"]),
    }


@router.post("/logout")
def logout(
    identity=Depends(get_identity),
    db: Session = Depends(get_db),
):
    identity["session"].is_revoked = True
    record_audit(
        db, "AUTH_LOGOUT", "SUCCESS", identity["user"].id
    )
    db.commit()
    return {"message": "Logged out"}
