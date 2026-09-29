"""Admin analytics: counts and administrator-reported errors (REQ-10.1, 10.3)."""
from sqlalchemy import func, select

from firewatch.config import RISK_LEVELS, STATUSES
from firewatch.db.models import Submission
from firewatch.db.session import session_scope

_CLASSES = ["Fire", "Smoke", "Non-Fire"]


def _count(db, *where) -> int:
    return db.scalar(select(func.count()).select_from(Submission).where(*where)) or 0


def _grouped(db, column, values) -> dict:
    counts = dict(db.execute(select(column, func.count()).group_by(column)).all())
    return {v: counts.get(v, 0) for v in values}


def analytics() -> dict:
    with session_scope() as db:
        misclassified = (Submission.status == "Flagged",
                         Submission.flag_reason == "Misclassified")
        return {
            "total": _count(db),
            "by_class": _grouped(db, Submission.predicted_class, _CLASSES),
            "by_risk": _grouped(db, Submission.risk_level, list(RISK_LEVELS)),
            "by_status": _grouped(db, Submission.status, STATUSES),
            # Fire/Smoke image predicted Non-Fire
            "false_negatives": _count(
                db, *misclassified, Submission.predicted_class == "Non-Fire",
                Submission.correct_class.in_(("Fire", "Smoke"))),
            # Non-Fire image predicted Fire/Smoke
            "false_positives": _count(
                db, *misclassified, Submission.predicted_class.in_(("Fire", "Smoke")),
                Submission.correct_class == "Non-Fire"),
        }