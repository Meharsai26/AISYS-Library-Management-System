import json

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.session import Base
from app.models.foundation import Member
from app.models.migration import ImportBatch, ImportStagingRow
from app.services.staged_member_import import stage_and_import_members


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        yield factory
    finally:
        engine.dispose()


def count_rows(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_staged_import_reconciles_persisted_members(session_factory):
    content = (
        b"card_number,display_name,status\n"
        b"P5-M001,Alice,ACTIVE\n"
        b"P5-M002,Bob,BLOCKED\n"
    )

    with session_factory() as db:
        result = stage_and_import_members(
            content, "synthetic_members.csv", db
        )

    with session_factory() as db:
        batch = db.get(ImportBatch, result["batch_id"])
        rows = db.scalars(
            select(ImportStagingRow).where(
                ImportStagingRow.batch_id == batch.id
            )
        ).all()

        assert batch.status == "COMPLETED"
        assert batch.completed_at is not None
        assert batch.source_count == 2
        assert batch.inserted_count == 2
        assert batch.rejected_count == 0
        assert result["reconciled"] is True
        assert len(rows) == 2

        for row in rows:
            assert row.status == "IMPORTED"
            assert row.target_member_id is not None

            member = db.get(Member, row.target_member_id)
            assert member is not None

            source = json.loads(row.raw_data)
            assert member.card_number == source["card_number"]


def test_staged_import_persists_rejected_rows(session_factory):
    with session_factory() as db:
        db.add(Member(
            card_number="P5-EXISTING",
            display_name="Existing Member",
            status="ACTIVE",
        ))
        db.commit()

        content = (
            b"card_number,display_name,status\n"
            b"P5-EXISTING,Duplicate,ACTIVE\n"
            b"P5-NEW,New Member,ACTIVE\n"
            b"P5-INVALID,Invalid Member,UNKNOWN\n"
        )

        result = stage_and_import_members(
            content, "mixed_members.csv", db
        )

    with session_factory() as db:
        batch = db.get(ImportBatch, result["batch_id"])
        rows = db.scalars(
            select(ImportStagingRow).where(
                ImportStagingRow.batch_id == batch.id
            )
        ).all()

        assert batch.source_count == 3
        assert batch.inserted_count == 1
        assert batch.rejected_count == 2
        assert result["reconciled"] is True
        assert len(rows) == 3

        rejected = [row for row in rows if row.status == "REJECTED"]
        assert len(rejected) == 2
        assert all(row.error_message for row in rejected)
        assert all(row.target_member_id is None for row in rejected)

        assert count_rows(db, Member) == 2


def test_staged_import_rolls_back_all_changes(session_factory):
    with session_factory() as db:
        def fail_after_member_insert(session, flush_context, instances):
            if any(isinstance(obj, Member) for obj in session.new):
                raise RuntimeError("Simulated staging transaction failure")

        event.listen(db, "before_flush", fail_after_member_insert)

        try:
            with pytest.raises(
                RuntimeError, match="Simulated staging transaction failure"
            ):
                stage_and_import_members(
                    b"card_number,display_name\nP5-M001,Alice\n",
                    "rollback.csv",
                    db,
                )
        finally:
            event.remove(
                db, "before_flush", fail_after_member_insert
            )

    with session_factory() as db:
        assert count_rows(db, Member) == 0
        assert count_rows(db, ImportBatch) == 0
        assert count_rows(db, ImportStagingRow) == 0
