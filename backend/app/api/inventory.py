"""Read-only software-simulated RFID inventory preview."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_db, require_permission
from app.models.foundation import LibraryItem
from app.models.rfid import RFIDTag


router = APIRouter(
    prefix="/api/v1/inventory",
    tags=["Mock Inventory"],
)


class MockInventoryRequest(BaseModel):
    scanned_epcs: list[str] = Field(max_length=500)


@router.post("/reconcile/mock")
def reconcile_mock_inventory(
    payload: MockInventoryRequest,
    identity=Depends(require_permission("tag:read")),
    db: Session = Depends(get_db),
):
    """Compare observed EPCs against currently available tagged items.

    This is a nonpersistent preview, not a shelf-specific
    inventory session or a physical handheld reader scan.
    """

    tag_rows = db.execute(
        select(RFIDTag.epc, LibraryItem.status)
        .join(
            LibraryItem,
            LibraryItem.id == RFIDTag.item_id,
        )
        .where(RFIDTag.status == "ACTIVE")
    ).all()

    registered = {row.epc for row in tag_rows}
    expected = {
        row.epc
        for row in tag_rows
        if row.status == "AVAILABLE"
    }

    observed = set(payload.scanned_epcs)

    matched = sorted(expected & observed)
    missing = sorted(expected - observed)
    unexpected_known = sorted(
        (observed & registered) - expected
    )
    unknown = sorted(observed - registered)

    return {
        "source": "MOCK",
        "hardware_connected": False,
        "persistent_session": False,
        "matched_epcs": matched,
        "missing_epcs": missing,
        "unknown_epcs": unknown,
        "unexpected_known_epcs": unexpected_known,
        "expected_count": len(expected),
        "observed_unique_count": len(observed),
    }
