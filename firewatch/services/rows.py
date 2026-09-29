"""Turns database rows into the plain dicts the UI expects (same shape the
old in-memory data used), including the image bytes for thumbnails."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from io import BytesIO

from PIL import Image

from firewatch.db import storage


@lru_cache(maxsize=1)
def _placeholder() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (160, 120), (200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _safe_image(key: str) -> bytes:
    try:
        return storage.get_image_bytes(key)
    except Exception:
        return _placeholder()        # a missing file must not break the whole list


def to_rows(subs) -> list[dict]:
    """Call inside session_scope(). Downloads uncached images in parallel."""
    subs = list(subs)
    with ThreadPoolExecutor(max_workers=8) as pool:
        images = list(pool.map(_safe_image, [s.image_path for s in subs]))
    return [
        {
            "id": s.submission_id,
            "image_bytes": img,
            "predicted_class": s.predicted_class,
            "confidence": s.confidence_score,
            "probabilities": {"Fire": s.prob_fire, "Smoke": s.prob_smoke,
                              "Non-Fire": s.prob_non_fire},
            "risk_level": s.risk_level,
            "timestamp": s.upload_timestamp,
            "status": s.status,
            "flag_reason": s.flag_reason,
            "correct_class": s.correct_class,
        }
        for s, img in zip(subs, images)
    ]