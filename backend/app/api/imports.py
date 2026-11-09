from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_db, require_permission
from app.services.staged_member_import import stage_and_import_members


router = APIRouter(
    prefix="/api/v1/imports",
    tags=["Data Migration"],
)

MAX_CSV_BYTES = 1024 * 1024


class MemberImportRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    csv_content: str = Field(min_length=1)


@router.post("/members")
def import_member_csv(
    payload: MemberImportRequest,
    identity=Depends(require_permission("member:write")),
    db: Session = Depends(get_db),
):
    if not payload.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV filenames are supported",
        )

    content = payload.csv_content.encode("utf-8")

    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413,
            detail="CSV content exceeds 1 MiB limit",
        )

    try:
        return stage_and_import_members(
            content=content,
            filename=payload.filename,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
