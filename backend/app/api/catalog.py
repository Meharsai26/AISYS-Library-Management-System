from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_db, require_permission
from app.models.foundation import BibliographicRecord, LibraryItem

router = APIRouter(prefix="/api/v1", tags=["Catalog"])


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str | None = None
    isbn: str | None = Field(default=None, max_length=20)


class ItemCreate(BaseModel):
    bib_id: str
    accession_number: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    is_reference: bool = False


@router.get("/bibliographic-records")
def list_books(
    identity=Depends(require_permission("catalog:read")),
    db: Session = Depends(get_db),
):
    books = db.scalars(
        select(BibliographicRecord)
        .order_by(BibliographicRecord.title, BibliographicRecord.id)
        .limit(100)
    ).all()

    return [
        {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
        }
        for book in books
    ]


@router.post("/bibliographic-records", status_code=201)
def create_book(
    payload: BookCreate,
    identity=Depends(require_permission("catalog:write")),
    db: Session = Depends(get_db),
):
    book = BibliographicRecord(
        title=payload.title,
        author=payload.author,
        isbn=payload.isbn,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    return {"id": book.id, "title": book.title}


@router.get("/items")
def list_items(
    identity=Depends(require_permission("catalog:read")),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(LibraryItem)
        .order_by(LibraryItem.accession_number)
        .limit(100)
    ).all()

    return [
        {
            "id": item.id,
            "bib_id": item.bib_id,
            "accession_number": item.accession_number,
            "status": item.status,
            "is_reference": item.is_reference,
        }
        for item in items
    ]


@router.post("/items", status_code=201)
def create_item(
    payload: ItemCreate,
    identity=Depends(require_permission("catalog:write")),
    db: Session = Depends(get_db),
):
    if db.get(BibliographicRecord, payload.bib_id) is None:
        raise HTTPException(status_code=404, detail="Book not found")

    item = LibraryItem(
        bib_id=payload.bib_id,
        accession_number=payload.accession_number,
        barcode=payload.barcode,
        is_reference=payload.is_reference,
        status="AVAILABLE",
    )

    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate accession number or barcode",
        )

    db.refresh(item)

    return {
        "id": item.id,
        "accession_number": item.accession_number,
        "status": item.status,
    }
