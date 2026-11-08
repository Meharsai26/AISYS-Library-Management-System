from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_db, require_permission
from app.models.foundation import Member

router = APIRouter(prefix="/api/v1/members", tags=["Members"])


class MemberCreate(BaseModel):
    card_number: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)


@router.get("")
def list_members(
    identity=Depends(require_permission("member:read")),
    db: Session = Depends(get_db),
):
    members = db.scalars(
        select(Member).order_by(Member.card_number).limit(100)
    ).all()

    return [
        {
            "id": member.id,
            "card_number": member.card_number,
            "display_name": member.display_name,
            "status": member.status,
        }
        for member in members
    ]


@router.post("", status_code=201)
def create_member(
    payload: MemberCreate,
    identity=Depends(require_permission("member:write")),
    db: Session = Depends(get_db),
):
    member = Member(
        card_number=payload.card_number,
        display_name=payload.display_name,
        status="ACTIVE",
    )

    db.add(member)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate member card number",
        )

    db.refresh(member)

    return {
        "id": member.id,
        "card_number": member.card_number,
        "status": member.status,
    }
