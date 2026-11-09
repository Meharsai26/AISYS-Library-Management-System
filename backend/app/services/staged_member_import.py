import csv
import io
import json

from sqlalchemy import select

from app.models.foundation import Member, utc_now
from app.models.migration import ImportBatch, ImportStagingRow
from app.services.member_import import validate_member_csv


def stage_and_import_members(content: bytes, filename: str, db):
    """Stage and import synthetic CSV members atomically."""
    validation = validate_member_csv(content)

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    source_rows = list(reader)

    if not filename or len(filename) > 255:
        raise ValueError("Invalid import filename")

    valid_by_row = {
        row["row"]: row for row in validation["valid_rows"]
    }
    error_by_row = {
        error["row"]: error["reason"]
        for error in validation["errors"]
    }

    try:
        existing_cards = set(
            db.scalars(select(Member.card_number)).all()
        )

        batch = ImportBatch(
            import_type="MEMBERS",
            filename=filename,
            status="STAGED",
            source_count=len(source_rows),
            inserted_count=0,
            rejected_count=0,
        )
        db.add(batch)
        db.flush()

        for row_number, source_row in enumerate(
            source_rows, start=2
        ):
            valid = valid_by_row.get(row_number)
            error = error_by_row.get(row_number)

            if valid and valid["card_number"] in existing_cards:
                error = "card_number already exists in database"

            staging = ImportStagingRow(
                batch_id=batch.id,
                row_number=row_number,
                raw_data=json.dumps(source_row),
                status="REJECTED" if error else "VALID",
                error_message=error,
            )

            db.add(staging)

            if error:
                batch.rejected_count += 1
                continue

            member = Member(
                card_number=valid["card_number"],
                display_name=valid["display_name"],
                status=valid["status"],
            )

            db.add(member)
            db.flush()

            staging.target_member_id = member.id
            staging.status = "IMPORTED"
            batch.inserted_count += 1
            existing_cards.add(member.card_number)

        db.flush()

        staged_rows = db.scalars(
            select(ImportStagingRow).where(
                ImportStagingRow.batch_id == batch.id
            )
        ).all()

        if len(staged_rows) != batch.source_count:
            raise RuntimeError("Source/staging row mismatch")

        imported = [
            row for row in staged_rows
            if row.status == "IMPORTED"
        ]

        rejected = [
            row for row in staged_rows
            if row.status == "REJECTED"
        ]

        if (
            len(imported) != batch.inserted_count
            or len(rejected) != batch.rejected_count
            or batch.source_count
            != batch.inserted_count + batch.rejected_count
        ):
            raise RuntimeError("Import count reconciliation failed")

        for row in imported:
            member = db.get(Member, row.target_member_id)
            source = valid_by_row[row.row_number]

            if (
                member is None
                or member.card_number != source["card_number"]
            ):
                raise RuntimeError("Target member reconciliation failed")

        batch.status = "COMPLETED"
        batch.completed_at = utc_now()

        result = {
            "batch_id": batch.id,
            "source_count": batch.source_count,
            "inserted_count": batch.inserted_count,
            "rejected_count": batch.rejected_count,
            "reconciled": True,
        }

        db.commit()
        return result

    except Exception:
        db.rollback()
        raise
