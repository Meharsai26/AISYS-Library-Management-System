from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.foundation import new_id, utc_now


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('STAGED', 'COMPLETED', 'FAILED')",
            name="ck_import_batch_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    import_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    filename: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="STAGED"
    )
    source_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    inserted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    rejected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class ImportStagingRow(Base):
    __tablename__ = "import_staging_rows"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "row_number",
            name="uq_import_batch_row",
        ),
        CheckConstraint(
            "status IN ('VALID', 'REJECTED', 'IMPORTED')",
            name="ck_import_staging_row_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("import_batches.id"), nullable=False
    )
    row_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    raw_data: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        Text
    )
    target_member_id: Mapped[str | None] = mapped_column(
        ForeignKey("members.id")
    )
