from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_db, record_audit, require_permission
from app.models.foundation import LibraryItem
from app.models.rfid import RFIDTag
from app.rfid.mock_reader import MockRFIDReader

router = APIRouter(prefix="/api/v1/rfid", tags=["Mock RFID"])
reader = MockRFIDReader()


class TagAssignment(BaseModel):
    item_id: str
    epc: str = Field(
        min_length=10,
        max_length=128,
        pattern=r"^MOCK-EPC-[A-Za-z0-9-]+$",
    )


class ScanRequest(BaseModel):
    epc: str = Field(min_length=1, max_length=128)


@router.post("/tags/assign", status_code=201)
def assign_tag(
    payload: TagAssignment,
    identity=Depends(require_permission("tag:write")),
    db: Session = Depends(get_db),
):
    item = db.get(LibraryItem, payload.item_id)

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    tag = RFIDTag(
        item_id=item.id,
        epc=payload.epc,
        security_armed=True,
        status="ACTIVE",
    )

    try:
        db.add(tag)
        db.flush()

        record_audit(
            db,
            "RFID_TAG_ASSIGN",
            "SUCCESS",
            actor_id=identity["user"].id,
            entity_type="RFID_TAG",
            entity_id=tag.id,
        )

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="EPC or item already assigned",
        )

    return {
        "tag_id": tag.id,
        "epc": tag.epc,
        "item_id": tag.item_id,
        "status": tag.status,
        "hardware_connected": False,
    }


@router.post("/scans/mock")
def mock_scan(
    payload: ScanRequest,
    identity=Depends(require_permission("tag:read")),
    db: Session = Depends(get_db),
):
    try:
        reading = reader.scan(payload.epc)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Invalid synthetic EPC",
        )

    tag = db.scalar(
        select(RFIDTag).where(RFIDTag.epc == payload.epc)
    )

    if tag is None:
        raise HTTPException(status_code=404, detail="Unknown tag")

    if tag.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Tag not active")

    item = db.get(LibraryItem, tag.item_id)
    if item is None:
        raise HTTPException(status_code=409, detail="Item missing")

    tag.last_seen_at = datetime.now(timezone.utc)

    record_audit(
        db,
        "RFID_MOCK_SCAN",
        "SUCCESS",
        actor_id=identity["user"].id,
        entity_type="RFID_TAG",
        entity_id=tag.id,
    )
    db.commit()

    return {
        **reading,
        "tag_id": tag.id,
        "item_id": item.id,
        "accession_number": item.accession_number,
        "item_status": item.status,
        "security_armed": tag.security_armed,
    }
