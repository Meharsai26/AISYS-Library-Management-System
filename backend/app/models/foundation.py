from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    Index, Integer, String, UniqueConstraint, text
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def new_id():
    return str(uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.id"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id"), primary_key=True
    )


class Permission(Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100), primary_key=True
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id"), primary_key=True
    )
    permission_code: Mapped[str] = mapped_column(
        ForeignKey("permissions.code"), primary_key=True
    )


class BibliographicRecord(Base):
    __tablename__ = "bibliographic_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    author: Mapped[str | None] = mapped_column(String(255))
    isbn: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class LibraryItem(Base):
    __tablename__ = "library_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'CHECKED_OUT', "
            "'LOST', 'REPAIR', 'WITHDRAWN')",
            name="ck_library_item_status"
        ),
        CheckConstraint(
            "version >= 0", name="ck_library_item_version"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    bib_id: Mapped[str] = mapped_column(
        ForeignKey("bibliographic_records.id"), nullable=False
    )
    accession_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    barcode: Mapped[str | None] = mapped_column(
        String(64), unique=True
    )
    is_reference: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="AVAILABLE"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'BLOCKED', 'EXPIRED')",
            name="ck_member_status"
        ),
        CheckConstraint(
            "fine_balance_paise >= 0",
            name="ck_member_fine_nonnegative",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    card_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    fine_balance_paise: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint(
            "due_at > checked_out_at", name="ck_loan_due"
        ),
        CheckConstraint(
            "returned_at IS NULL OR returned_at >= checked_out_at",
            name="ck_loan_return"
        ),
        CheckConstraint(
            "renewed_count >= 0", name="ck_loan_renewals"
        ),
        Index(
            "uq_active_loan_per_item",
            "item_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    item_id: Mapped[str] = mapped_column(
        ForeignKey("library_items.id"), nullable=False
    )
    member_id: Mapped[str] = mapped_column(
        ForeignKey("members.id"), nullable=False
    )
    checked_out_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    renewed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_id
    )
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_accounts.id")
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    entity_id: Mapped[str | None] = mapped_column(String(36))
    outcome: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
