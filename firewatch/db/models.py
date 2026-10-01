"""SQLAlchemy tables for FireWatch (schema agreed in the design review)."""
from datetime import datetime

from sqlalchemy import (CheckConstraint, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from firewatch.config import FLAG_REASONS, RISK_LEVELS, STATUSES


class Base(DeclarativeBase):
    pass


def _in(column: str, values) -> str:
    """Builds a CHECK expression like: status IN ('Pending','Approved')."""
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


CLASSES = ("Fire", "Smoke", "Non-Fire")


class AdminUser(Base):
    __tablename__ = "admin_user"

    admin_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # bcrypt, salt included
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # REQ-8.4
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class Submission(Base):
    __tablename__ = "submission"
    __table_args__ = (
        CheckConstraint(_in("predicted_class", CLASSES), name="ck_sub_class"),
        CheckConstraint(_in("risk_level", list(RISK_LEVELS)), name="ck_sub_risk"),
        CheckConstraint(_in("status", STATUSES), name="ck_sub_status"),
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_sub_conf"),
        CheckConstraint(f"flag_reason IS NULL OR {_in('flag_reason', FLAG_REASONS)}",
                        name="ck_sub_reason"),
        CheckConstraint(f"correct_class IS NULL OR {_in('correct_class', CLASSES)}",
                        name="ck_sub_correct"),
    )

    submission_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)   # key in storage
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now,
                                                       nullable=False, index=True)
    predicted_class: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    prob_fire: Mapped[float] = mapped_column(Float, nullable=False)        # REQ-6.1, 7.4
    prob_smoke: Mapped[float] = mapped_column(Float, nullable=False)
    prob_non_fire: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="Pending",
                                        nullable=False, index=True)
    flag_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)   # REQ-9.4
    correct_class: Mapped[str | None] = mapped_column(String(10), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("admin_user.admin_id"),
                                                    nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    notes: Mapped[list["Note"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "note"

    note_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submission.submission_id", ondelete="CASCADE"), nullable=False)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admin_user.admin_id"), nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    submission: Mapped[Submission] = relationship(back_populates="notes")


class ModerationAction(Base):
    """Audit trail (REQ-9.6). submission_id is deliberately NOT a foreign key,
    so the record survives when a submission is permanently removed."""
    __tablename__ = "moderation_action"
    __table_args__ = (
        CheckConstraint(_in("action", ("Approve", "Flag", "Remove")), name="ck_action"),
    )

    action_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(Integer, nullable=False)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admin_user.admin_id"), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)