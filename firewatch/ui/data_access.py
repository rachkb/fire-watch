"""
Temporary data seam for the UI.

Every page reads and writes through the functions in this file and never
touches storage directly. Right now they use an in-memory list kept in
st.session_state (seeded with sample rows) so the UI can be built and demoed
before the database exists. When firewatch/services/ is ready, replace the
BODIES of these functions with calls to the services. The signatures stay the
same, so no page has to change.

Dev data resets whenever the browser session restarts.
"""
import hmac
from datetime import datetime, timedelta
from io import BytesIO

import streamlit as st
from PIL import Image

from firewatch.inference.risk import get_risk_level

_SEED = [
    ("Fire", 0.93, "Approved"), ("Smoke", 0.71, "Approved"),
    ("Non-Fire", 0.88, "Approved"), ("Fire", 0.66, "Approved"),
    ("Smoke", 0.91, "Approved"), ("Non-Fire", 0.55, "Pending"),
    ("Fire", 0.82, "Pending"), ("Smoke", 0.74, "Flagged"),
]
_COLORS = {"Fire": (214, 90, 40), "Smoke": (140, 140, 150), "Non-Fire": (70, 140, 80)}


def _png(color) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (160, 120), color).save(buf, format="PNG")
    return buf.getvalue()


def _probs(cls: str, conf: float) -> dict:
    rest = (1 - conf) / 2
    return {c: (conf if c == cls else rest) for c in ("Fire", "Smoke", "Non-Fire")}


def _store() -> list:
    if "_dev_subs" not in st.session_state:
        now = datetime.now()
        st.session_state["_dev_subs"] = [
            {
                "id": i + 1, "image_bytes": _png(_COLORS[cls]),
                "predicted_class": cls, "confidence": conf,
                "probabilities": _probs(cls, conf),
                "risk_level": get_risk_level(cls, conf),
                "timestamp": now - timedelta(hours=i * 5),
                "status": status, "flag_reason": None,
                "correct_class": None, "notes": [],
            }
            for i, (cls, conf, status) in enumerate(_SEED)
        ]
        st.session_state["_dev_next_id"] = len(_SEED) + 1
    return st.session_state["_dev_subs"]


def _find(sub_id: int) -> dict:
    return next(s for s in _store() if s["id"] == sub_id)


# ---------- public (general user) ----------

def add_submission(image_bytes: bytes, result: dict) -> int:
    """Save a classified upload with status Pending (REQ-6.1)."""
    subs = _store()
    sub_id = st.session_state["_dev_next_id"]
    st.session_state["_dev_next_id"] += 1
    subs.append({
        "id": sub_id, "image_bytes": image_bytes,
        "predicted_class": result["predicted_class"],
        "confidence": float(result["confidence"]),
        "probabilities": dict(result["probabilities"]),
        "risk_level": result["risk_level"],
        "timestamp": datetime.now(), "status": "Pending",
        "flag_reason": None, "correct_class": None, "notes": [],
    })
    return sub_id


def list_approved(page: int, page_size: int, class_filter=None, risk_filter=None):
    """Approved submissions only, newest first. Returns (rows, total_count)."""
    rows = [s for s in _store() if s["status"] == "Approved"]
    if class_filter:
        rows = [s for s in rows if s["predicted_class"] == class_filter]
    if risk_filter:
        rows = [s for s in rows if s["risk_level"] == risk_filter]
    rows.sort(key=lambda s: s["timestamp"], reverse=True)
    start = (page - 1) * page_size
    return rows[start:start + page_size], len(rows)


# ---------- admin ----------

def list_all(risk=None, cls=None, status=None, date_from=None, date_to=None):
    rows = list(_store())
    if risk:
        rows = [s for s in rows if s["risk_level"] == risk]
    if cls:
        rows = [s for s in rows if s["predicted_class"] == cls]
    if status:
        rows = [s for s in rows if s["status"] == status]
    if date_from:
        rows = [s for s in rows if s["timestamp"].date() >= date_from]
    if date_to:
        rows = [s for s in rows if s["timestamp"].date() <= date_to]
    return sorted(rows, key=lambda s: s["timestamp"], reverse=True)


def approve(sub_id: int, admin_id: int):
    """Sets Approved and clears any flag (REQ-9.3)."""
    s = _find(sub_id)
    s.update(status="Approved", flag_reason=None, correct_class=None)


def flag(sub_id: int, admin_id: int, reason: str, correct_class=None, note=""):
    s = _find(sub_id)
    s.update(status="Flagged", flag_reason=reason, correct_class=correct_class)
    if note.strip():
        s["notes"].append({"admin_id": admin_id, "text": note.strip(),
                           "created_at": datetime.now()})


def remove(sub_id: int, admin_id: int):
    """Hard delete of image and record (REQ-9.5)."""
    subs = _store()
    subs[:] = [s for s in subs if s["id"] != sub_id]


def analytics() -> dict:
    subs = _store()

    def count(key, values):
        return {v: sum(1 for s in subs if s[key] == v) for v in values}

    misclassified = [s for s in subs
                     if s["status"] == "Flagged" and s["flag_reason"] == "Misclassified"]
    return {
        "total": len(subs),
        "by_class": count("predicted_class", ["Fire", "Smoke", "Non-Fire"]),
        "by_risk": count("risk_level", ["High", "Medium", "Low", "None", "Uncertain"]),
        "by_status": count("status", ["Pending", "Approved", "Flagged"]),
        "false_negatives": sum(
            1 for s in misclassified
            if s["predicted_class"] == "Non-Fire" and s["correct_class"] in ("Fire", "Smoke")),
        "false_positives": sum(
            1 for s in misclassified
            if s["predicted_class"] in ("Fire", "Smoke") and s["correct_class"] == "Non-Fire"),
    }


def authenticate(username: str, password: str):
    """Returns admin_id or None. Uses firewatch.auth.service once it exists."""
    try:
        from firewatch.auth.service import authenticate as real
    except ImportError:
        real = None
    if real:
        return real(username, password)
    # Dev fallback: credentials from .streamlit/secrets.toml (gitignored). Remove later.
    try:
        u, p = st.secrets["DEV_ADMIN_USERNAME"], st.secrets["DEV_ADMIN_PASSWORD"]
    except Exception:
        return None
    ok = hmac.compare_digest(username, u) and hmac.compare_digest(password, p)
    return 1 if ok else None