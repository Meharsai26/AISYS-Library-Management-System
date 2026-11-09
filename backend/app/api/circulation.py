from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    get_db, record_audit, require_permission,
)
from app.models.foundation import LibraryItem, Loan, Member
from app.models.rfid import RFIDTag
from app.services.integration_outbox import queue_ilms_event
from app.services.mock_ilms import ILMSOperation

router = APIRouter(prefix="/api/v1/loans", tags=["Circulation"])


class CheckoutRequest(BaseModel):
    member_id: str
    item_id: str


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/checkout", status_code=201)
def checkout(
    payload: CheckoutRequest,
    identity=Depends(require_permission("circulation:write")),
    db: Session = Depends(get_db),
):
    from app.core.config import settings
    member = db.get(Member, payload.member_id)
    item = db.get(LibraryItem, payload.item_id)

    if member is None or item is None:
        raise HTTPException(
            status_code=404,
            detail="Member or item not found",
        )

    if member.status != "ACTIVE":
        raise HTTPException(
            status_code=409,
            detail="Member is not eligible",
        )

    if member.fine_balance_paise > settings.max_fine_paise:
        raise HTTPException(
            status_code=409,
            detail="Fine limit exceeded",
        )
    if item.is_reference:
        raise HTTPException(
            status_code=409,
            detail="Reference item cannot be borrowed",
        )

    if item.status != "AVAILABLE":
        raise HTTPException(
            status_code=409,
            detail="Item is not available",
        )

    current = utc_now()
    loan = Loan(
        item_id=item.id,
        member_id=member.id,
        checked_out_at=current,
        due_at=current + timedelta(days=14),
        renewed_count=0,
    )

    try:
        result = db.execute(
            update(LibraryItem)
            .where(
                LibraryItem.id == item.id,
                LibraryItem.status == "AVAILABLE",
            )
            .values(status="CHECKED_OUT", version=LibraryItem.version + 1)
        )

        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Item was checked out concurrently",
            )

        db.add(loan)
        db.flush()

        db.execute(
            update(RFIDTag)
            .where(
                RFIDTag.item_id == item.id,
                RFIDTag.status == "ACTIVE",
            )
            .values(security_armed=False)
        )

        record_audit(
            db,
            "LOAN_CHECKOUT",
            "SUCCESS",
            actor_id=identity["user"].id,
            entity_type="LOAN",
            entity_id=loan.id,
        )
        queue_ilms_event(
            db,
            loan_id=loan.id,
            operation=ILMSOperation.CHECKOUT,
        )

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Active loan conflict",
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "loan_id": loan.id,
        "member_id": loan.member_id,
        "item_id": loan.item_id,
        "status": "ACTIVE",
        "due_at": loan.due_at,
        "integration_status": "QUEUED",
    }


@router.post("/{loan_id}/return")
def return_loan(
    loan_id: str,
    identity=Depends(require_permission("circulation:write")),
    db: Session = Depends(get_db),
):
    loan = db.get(Loan, loan_id)

    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.returned_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Loan already returned",
        )

    current = utc_now()

    try:
        result = db.execute(
            update(Loan)
            .where(
                Loan.id == loan_id,
                Loan.returned_at.is_(None),
            )
            .values(returned_at=current)
        )

        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Loan already returned",
            )

        item_result = db.execute(
            update(LibraryItem)
            .where(
                LibraryItem.id == loan.item_id,
                LibraryItem.status == "CHECKED_OUT",
            )
            .values(status="AVAILABLE", version=LibraryItem.version + 1)
        )

        if item_result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Item state conflict",
            )

        db.execute(
            update(RFIDTag)
            .where(
                RFIDTag.item_id == loan.item_id,
                RFIDTag.status == "ACTIVE",
            )
            .values(security_armed=True)
        )

        record_audit(
            db,
            "LOAN_RETURN",
            "SUCCESS",
            actor_id=identity["user"].id,
            entity_type="LOAN",
            entity_id=loan.id,
        )
        queue_ilms_event(
            db,
            loan_id=loan.id,
            operation=ILMSOperation.CHECKIN,
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "loan_id": loan_id,
        "status": "RETURNED",
        "returned_at": current,
        "integration_status": "QUEUED",
    }


@router.post("/{loan_id}/renew")
def renew_loan(
    loan_id: str,
    identity=Depends(require_permission("circulation:write")),
    db: Session = Depends(get_db),
):
    """Renew an eligible active loan with a guarded update."""
    from app.core.config import settings

    loan = db.get(Loan, loan_id)

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    if loan.returned_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Loan already returned",
        )

    member = db.get(Member, loan.member_id)
    item = db.get(LibraryItem, loan.item_id)

    if member is None or item is None:
        raise HTTPException(
            status_code=409,
            detail="Member or item unavailable",
        )

    if member.status != "ACTIVE":
        raise HTTPException(
            status_code=409,
            detail="Member is not eligible",
        )

    if member.fine_balance_paise > settings.max_fine_paise:
        raise HTTPException(
            status_code=409,
            detail="Fine limit exceeded",
        )
    if item.is_reference:
        raise HTTPException(
            status_code=409,
            detail="Reference item cannot be renewed",
        )

    if item.status != "CHECKED_OUT":
        raise HTTPException(
            status_code=409,
            detail="Item is not checked out",
        )

    if loan.renewed_count >= settings.max_loan_renewals:
        raise HTTPException(
            status_code=409,
            detail="Maximum renewals reached",
        )

    old_count = loan.renewed_count
    old_due_at = loan.due_at

    new_due_at = old_due_at + timedelta(
        days=settings.loan_renewal_days
    )

    try:
        result = db.execute(
            update(Loan)
            .where(
                Loan.id == loan_id,
                Loan.returned_at.is_(None),
                Loan.renewed_count == old_count,
                Loan.due_at == old_due_at,
                Loan.renewed_count < settings.max_loan_renewals,
            )
            .values(
                due_at=new_due_at,
                renewed_count=old_count + 1,
            )
        )

        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Loan changed concurrently",
            )

        record_audit(
            db,
            "LOAN_RENEWAL",
            "SUCCESS",
            actor_id=identity["user"].id,
            entity_type="LOAN",
            entity_id=loan_id,
        )

        queue_ilms_event(
            db,
            loan_id=loan.id,
            operation=ILMSOperation.RENEW,
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    return {
        "loan_id": loan_id,
        "status": "ACTIVE",
        "renewed_count": old_count + 1,
        "due_at": new_due_at,
        "integration_status": "QUEUED",
    }
