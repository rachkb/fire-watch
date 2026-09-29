"""Saving uploads and listing the public history."""
from io import BytesIO

from PIL import Image
from sqlalchemy import func, select

from firewatch.db import storage
from firewatch.db.models import Submission
from firewatch.db.session import session_scope
from firewatch.services.rows import to_rows


def _content_type(data: bytes) -> str:
    fmt = Image.open(BytesIO(data)).format
    return "image/jpeg" if fmt == "JPEG" else "image/png"


def add_submission(image_bytes: bytes, result: dict) -> int:
    """Stores the image, then the record with status Pending (REQ-6.1).
    If the record can't be saved, the uploaded image is removed again."""
    key = storage.save_image(image_bytes, _content_type(image_bytes))
    try:
        probs = result["probabilities"]
        with session_scope() as db:
            sub = Submission(
                image_path=key,
                predicted_class=result["predicted_class"],
                confidence_score=float(result["confidence"]),
                prob_fire=float(probs["Fire"]),
                prob_smoke=float(probs["Smoke"]),
                prob_non_fire=float(probs["Non-Fire"]),
                risk_level=result["risk_level"],
            )
            db.add(sub)
            db.flush()
            return sub.submission_id
    except Exception:
        storage.delete_image(key)
        raise


def list_approved(page: int, page_size: int, class_filter=None, risk_filter=None):
    """Approved submissions only, newest first. Returns (rows, total_count)."""
    where = [Submission.status == "Approved"]
    if class_filter:
        where.append(Submission.predicted_class == class_filter)
    if risk_filter:
        where.append(Submission.risk_level == risk_filter)

    with session_scope() as db:
        total = db.scalar(select(func.count()).select_from(Submission).where(*where))
        subs = db.scalars(
            select(Submission).where(*where)
            .order_by(Submission.upload_timestamp.desc(), Submission.submission_id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        ).all()
        return to_rows(subs), total