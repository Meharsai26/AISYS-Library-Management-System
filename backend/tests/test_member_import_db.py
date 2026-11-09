import pytest

from sqlalchemy import create_engine, event, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models.foundation import Member
from app.services.member_import import import_members


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    TestingSession = sessionmaker(bind=engine)

    try:
        with TestingSession() as db:
            yield db
    finally:
        engine.dispose()


def member_count(db):
    return db.scalar(
        select(func.count()).select_from(Member)
    )


def test_successful_member_import(db_session):
    csv_data = (
        b"card_number,display_name,status\n"
        b"M101,Alice,ACTIVE\n"
        b"M102,Bob,BLOCKED\n"
    )

    result = import_members(csv_data, db_session)

    assert result["source_count"] == 2
    assert result["inserted_count"] == 2
    assert result["rejected_count"] == 0
    assert result["reconciled"] is True
    assert member_count(db_session) == 2

    bob = db_session.scalar(
        select(Member).where(Member.card_number == "M102")
    )
    assert bob.status == "BLOCKED"


def test_existing_database_duplicate(db_session):
    db_session.add(Member(
        card_number="M101",
        display_name="Existing Member",
        status="ACTIVE",
    ))
    db_session.commit()

    csv_data = (
        b"card_number,display_name\n"
        b"M101,Duplicate Member\n"
        b"M102,New Member\n"
    )

    result = import_members(csv_data, db_session)

    assert result["inserted_count"] == 1
    assert result["rejected_count"] == 1
    assert result["reconciled"] is True
    assert member_count(db_session) == 2

    existing = db_session.scalar(
        select(Member).where(Member.card_number == "M101")
    )
    assert existing.display_name == "Existing Member"


def test_invalid_row_rejected(db_session):
    csv_data = (
        b"card_number,display_name,status\n"
        b"M101,Alice,ACTIVE\n"
        b"M102,Bob,INVALID\n"
    )

    result = import_members(csv_data, db_session)

    assert result["source_count"] == 2
    assert result["inserted_count"] == 1
    assert result["rejected_count"] == 1
    assert result["errors"][0]["row"] == 3
    assert result["reconciled"] is True
    assert member_count(db_session) == 1


def test_transaction_failure_rolls_back(db_session):
    csv_data = (
        b"card_number,display_name\n"
        b"M101,Alice\n"
        b"M102,Bob\n"
    )

    def simulate_failure(session, flush_context, instances):
        raise RuntimeError("Simulated database failure")

    event.listen(
        db_session,
        "before_flush",
        simulate_failure,
    )

    try:
        with pytest.raises(
            RuntimeError, match="Simulated database failure"
        ):
            import_members(csv_data, db_session)
    finally:
        event.remove(
            db_session,
            "before_flush",
            simulate_failure,
        )

    assert member_count(db_session) == 0
