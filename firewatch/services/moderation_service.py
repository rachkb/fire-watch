"""Admin moderation: list, approve, flag, remove. Every action writes an audit row (REQ-9.6)."""
from datetime import datetime, time

from sqlalchemy import select

from firewatch.config import FLAG_REASONS
from firewatch.db import storage
from firewatch.db.models import ModerationAction, Note, Submission
from firewatch.db.session import session_scope
from firewatch.services.rows import to_rows

_CLASSES = ("Fire", "Smoke", "Non-Fire")


def list_all(risk=None, cls=None, status=None, date_from=None, date_to=None, limit=50):
    """All submissions (any status), newest first. `limit` keeps the page fast."""
    where = []
    if risk:
        where.append(Submission.risk_level == risk)
    if cls:
        where.append(Submission.predicted_class == cls)
    if status:
        where.append(Submission.status == status)
    if date_from:
        where.append(Submission.upload_timestamp >= datetime.combine(date_from, time.min))
    if date_to:
        where.append(Submission.upload_timestamp <= datetime.combine(date_to, time.max))

    with session_scope() as db:
        q = (select(Submission).where(*where)
             .order_by(Submission.upload_timestamp.desc(), Submission.submission_id.desc()))
        if limit:
            q = q.limit(limit)
        return to_rows(db.scalars(q).all())


def _stamp(sub: Submission, admin_id: int, action: str, db):
    sub.reviewed_by = admin_id
    sub.reviewed_at = datetime.now()
    db.add(ModerationAction(submission_id=sub.submission_id, admin_id=admin_id, action=action))


def approve(sub_id: int, admin_id: int) -> bool:
    """Sets Approved and clears any flag (REQ-9.3). Returns False if the submission is gone."""
    with session_scope() as db:
        sub = db.get(Submission, sub_id)
        if sub is None:
            return False
        sub.status, sub.flag_reason, sub.correct_class = "Approved", None, None
        _stamp(sub, admin_id, "Approve", db)
        return True


def flag(sub_id: int, admin_id: int, reason: str, correct_class=None, note="") -> bool:
    """Sets Flagged with a reason, optional correct class and optional note (REQ-9.4)."""
    if reason not in FLAG_REASONS:
        raise ValueError(f"Unknown flag reason: {reason}")
    if correct_class is not None and correct_class not in _CLASSES:
        raise ValueError(f"Unknown class: {correct_class}")
    with session_scope() as db:
        sub = db.get(Submission, sub_id)
        if sub is None:
            return False
        sub.status, sub.flag_reason, sub.correct_class = "Flagged", reason, correct_class
        if note and note.strip():
            db.add(Note(submission_id=sub_id, admin_id=admin_id, note_text=note.strip()))
        _stamp(sub, admin_id, "Flag", db)
        return True


def remove(sub_id: int, admin_id: int) -> bool:
    """Permanently deletes the image and the record (REQ-9.5, NREQ-SEC-3).

    The image goes first. If that fails, the error is raised and the record is
    kept, so the admin can simply retry. If the database step fails afterwards,
    a retry also works because deleting a missing image is ignored."""
    with session_scope() as db:
        sub = db.get(Submission, sub_id)
        if sub is None:
            return False
        image_path = sub.image_path

    storage.delete_image(image_path)

    with session_scope() as db:
        sub = db.get(Submission, sub_id)
        if sub is not None:
            db.add(ModerationAction(submission_id=sub_id, admin_id=admin_id, action="Remove"))
            db.delete(sub)                       # notes are deleted with it (cascade)
    return True