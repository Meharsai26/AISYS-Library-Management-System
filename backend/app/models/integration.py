"""Durable integration outbox for mock ILMS operations."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.foundation import new_id, utc_now


class IntegrationOutbox(Base):
    __tablename__ = "integration_outbox"

    __table_args__ = (
        CheckConstraint(
            "operation IN ('CHECKOUT', 'CHECKIN', 'RENEW')",
            name="ck_outbox_operation",
        ),
        CheckConstraint(
            "provider IN ('MOCK_NCIP', 'MOCK_SIP2')",
            name="ck_outbox_provider",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'DELIVERED', "
            "'RETRY', 'DEAD_LETTER')",
            name="ck_outbox_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_outbox_attempt_count",
        ),
        Index(
            "ix_outbox_status_created",
            "status",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_id,
    )
    loan_id: Mapped[str] = mapped_column(
        ForeignKey("loans.id"),
        nullable=False,
    )
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    correlation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
