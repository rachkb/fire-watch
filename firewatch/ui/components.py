"""Shared UI pieces: header, risk badge/banner, result dialog, admin header, guard."""
from datetime import datetime, timedelta

import streamlit as st

from firewatch.config import (
    DISCLAIMER_TEXT, DISPLAY_CLASS_ORDER, LOW_CONFIDENCE_THRESHOLD,
    RISK_LEVELS, SESSION_TIMEOUT_MINUTES, TAGLINE,
)

_ADMIN_KEYS = ("admin_id", "admin_username", "admin_last_activity")


def _page(name: str):
    return st.session_state["pages"][name]


# ---------- headers ----------

def header():
    """Public header: logo, name, tagline, and Admin Login link (REQ-8.1)."""
    left, right = st.columns([5, 1], vertical_alignment="center")
    left.markdown(f"### FireWatch\n{TAGLINE}")
    right.page_link(_page("login"), label="Admin Login")
    st.divider()


def admin_header(current: str):
    """Admin header with Moderation / Analytics navigation and Log out (Fig 4, 5)."""
    c1, c2, c3, c4 = st.columns([4, 1.3, 1.3, 1], vertical_alignment="center")
    c1.markdown(f"### FireWatch\n{TAGLINE}")
    c2.page_link(_page("moderation"), label="Moderation",
                 disabled=(current == "moderation"))
    c3.page_link(_page("analytics"), label="Analytics",
                 disabled=(current == "analytics"))
    if c4.button("Log out", use_container_width=True):
        for k in _ADMIN_KEYS:
            st.session_state.pop(k, None)
        st.switch_page(_page("home"))
    st.divider()


def require_admin() -> int:
    """Call at the top of every admin page (REQ-9.7). Returns the admin id."""
    admin_id = st.session_state.get("admin_id")
    last = st.session_state.get("admin_last_activity")
    expired = bool(last) and datetime.now() - last > timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    if admin_id is None or expired:
        for k in _ADMIN_KEYS:
            st.session_state.pop(k, None)
        if expired:
            st.session_state["login_notice"] = "Your session expired. Log in again."
        st.switch_page(_page("login"))
        st.stop()
    st.session_state["admin_last_activity"] = datetime.now()
    return admin_id


# ---------- low-confidence wording ----------

def is_low_confidence(confidence: float) -> bool:
    return float(confidence) < LOW_CONFIDENCE_THRESHOLD


def class_label(predicted_class: str, confidence: float) -> str:
    """Headline text. Low-confidence results read 'Uncertain (leaning Fire, 51%)'
    so the class is still shown (REQ-3.1) without sounding like a firm verdict."""
    if is_low_confidence(confidence):
        return f"Uncertain (leaning {predicted_class}, {float(confidence):.0%})"
    return f"{predicted_class} ({float(confidence):.0%})"


# ---------- risk ----------

def risk_badge(level: str) -> str:
    """Small colored pill (HTML) for list rows. Render with unsafe_allow_html=True."""
    color = RISK_LEVELS[level]["color"]
    return (f'<span style="background:{color};color:#fff;padding:2px 10px;'
            f'border-radius:12px;font-size:0.85rem">{level}</span>')


def risk_banner(level: str):
    info = RISK_LEVELS[level]
    st.markdown(
        f"""<div style="background:{info['color']};color:#fff;padding:14px 18px;
        border-radius:8px"><b>Risk Level: {level.upper()}</b><br>{info['message']}</div>""",
        unsafe_allow_html=True,
    )


def disclaimer():
    st.markdown(
        f"<p style='text-align:center;opacity:.7;font-size:.85rem'>{DISCLAIMER_TEXT}</p>",
        unsafe_allow_html=True,
    )   # NREQ-SAFE-1


# ---------- result / details dialog (Fig 2) ----------

@st.dialog("Detection result", width="large")
def result_dialog(result: dict, image, heatmap_fn=None, timestamp=None):
    """
    Layout follows Fig 2: image + class + probability bars + risk box on top,
    heatmap below. image may be a PIL image or bytes.
    heatmap_fn=None (history details) means no heatmap, because heatmaps
    are never stored (REQ-6.6).
    """
    top_l, top_r = st.columns(2)
    top_l.image(image, use_container_width=True)
    with top_r:
        low = is_low_confidence(result["confidence"])
        if low:
            st.markdown("#### UNCERTAIN")
            st.caption(f"Leaning {result['predicted_class']} · "
                       f"Confidence: {result['confidence']:.0%}"
                       + (f" · {timestamp:%Y-%m-%d %H:%M}" if timestamp else ""))
        else:
            st.markdown(f"#### {result['predicted_class'].upper()}")
            st.caption(f"Confidence: {result['confidence']:.0%}"
                       + (f" · {timestamp:%Y-%m-%d %H:%M}" if timestamp else ""))
        for name in DISPLAY_CLASS_ORDER:                      # REQ-3.3
            p = float(result["probabilities"][name])
            st.progress(p, text=f"{name}: {p:.0%}")
        if low:                                               # REQ-3.4
            st.warning("Low Confidence, Manual Review Recommended.")
        risk_banner(result["risk_level"])                     # moved up, right under probabilities

    if heatmap_fn is None:
        st.caption("Heatmaps are generated when an image is analyzed and are not stored.")
    elif st.toggle("Show heatmap", value=True):                # REQ-5.3
        try:
            st.image(heatmap_fn(), use_container_width=True)
        except Exception:
            st.warning("Heatmap unavailable.")                 # REQ-5.4
    disclaimer()