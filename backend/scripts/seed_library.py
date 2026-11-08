from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.foundation import (
    BibliographicRecord,
    LibraryItem,
    Member,
)

BOOKS = [
    ("AISYS-SEED-001", "Introduction to Artificial Intelligence", "AISYS Demo"),
    ("AISYS-SEED-002", "Database Management Systems", "AISYS Demo"),
    ("AISYS-SEED-003", "Python Programming Fundamentals", "AISYS Demo"),
]

MEMBERS = [
    ("AISYS-DEMO-M001", "Synthetic Student One"),
    ("AISYS-DEMO-M002", "Synthetic Student Two"),
]


def seed():
    books_created = 0
    items_created = 0
    members_created = 0

    with SessionLocal.begin() as db:
        for accession, title, author in BOOKS:
            existing = db.scalar(
                select(LibraryItem).where(
                    LibraryItem.accession_number == accession
                )
            )

            if existing:
                continue

            book = BibliographicRecord(title=title, author=author)
            db.add(book)
            db.flush()

            db.add(
                LibraryItem(
                    bib_id=book.id,
                    accession_number=accession,
                    status="AVAILABLE",
                    is_reference=False,
                )
            )
            books_created += 1
            items_created += 1

        for card_number, display_name in MEMBERS:
            existing = db.scalar(
                select(Member).where(
                    Member.card_number == card_number
                )
            )

            if existing:
                continue

            db.add(
                Member(
                    card_number=card_number,
                    display_name=display_name,
                    status="ACTIVE",
                )
            )
            members_created += 1

    print("Synthetic seed completed")
    print("Books created:", books_created)
    print("Items created:", items_created)
    print("Members created:", members_created)


if __name__ == "__main__":
    seed()
