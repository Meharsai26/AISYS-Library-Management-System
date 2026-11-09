import csv
import io


REQUIRED_COLUMNS = ("card_number", "display_name")
ALLOWED_STATUSES = {"ACTIVE", "BLOCKED", "EXPIRED"}


def validate_member_csv(content: bytes):
    """Validate synthetic member CSV without changing the database."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must use UTF-8 encoding") from exc

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("CSV header is missing")

    headers = [name.strip() for name in reader.fieldnames]

    if len(headers) != len(set(headers)):
        raise ValueError("Duplicate CSV column names")

    if any(column not in headers for column in REQUIRED_COLUMNS):
        raise ValueError(
            "Required columns: card_number, display_name"
        )

    valid_rows = []
    errors = []
    seen_cards = set()

    try:
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                errors.append({
                    "row": row_number,
                    "reason": "Unexpected extra columns",
                })
                continue

            card_number = (row.get("card_number") or "").strip()
            display_name = (row.get("display_name") or "").strip()
            status = (row.get("status") or "ACTIVE").strip().upper()

            reasons = []

            if not card_number or len(card_number) > 100:
                reasons.append("Invalid card_number")

            if not display_name or len(display_name) > 255:
                reasons.append("Invalid display_name")

            if status not in ALLOWED_STATUSES:
                reasons.append("Invalid member status")

            if card_number and card_number in seen_cards:
                reasons.append("Duplicate card_number in CSV")

            if card_number:
                seen_cards.add(card_number)

            if reasons:
                errors.append({
                    "row": row_number,
                    "reason": "; ".join(reasons),
                })
                continue

            valid_rows.append({
                "row": row_number,
                "card_number": card_number,
                "display_name": display_name,
                "status": status,
            })
    except csv.Error as exc:
        raise ValueError("Malformed CSV") from exc

    return {
        "valid_rows": valid_rows,
        "errors": errors,
    }


def import_members(content: bytes, db):
    """Import valid members using one database transaction."""
    from sqlalchemy import select
    from app.models.foundation import Member

    validation = validate_member_csv(content)
    valid_rows = validation["valid_rows"]
    errors = list(validation["errors"])

    existing_cards = set(
        db.scalars(select(Member.card_number)).all()
    )

    accepted = []

    for row in valid_rows:
        if row["card_number"] in existing_cards:
            errors.append({
                "row": row["row"],
                "reason": "card_number already exists in database",
            })
            continue

        accepted.append(row)

    try:
        for row in accepted:
            db.add(Member(
                card_number=row["card_number"],
                display_name=row["display_name"],
                status=row["status"],
            ))

        db.commit()

    except Exception:
        db.rollback()
        raise

    source_count = len(valid_rows) + len(validation["errors"])

    return {
        "source_count": source_count,
        "inserted_count": len(accepted),
        "rejected_count": len(errors),
        "reconciled": (
            source_count == len(accepted) + len(errors)
        ),
        "errors": errors,
    }
