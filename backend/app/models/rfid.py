from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def new_rfid_id():
    return str(uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class RFIDTag(Base):
    __tablename__ = "rfid_tags"

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')",
            name="ck_rfid_tag_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_rfid_id,
    )

    epc: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )

    item_id: Mapped[str] = mapped_column(
        ForeignKey("library_items.id"),
        unique=True,
        nullable=False,
    )

    security_armed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
    )

    tagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
