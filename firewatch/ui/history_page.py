"""Submission history section (left column of the landing page, Fig 1)."""
from math import ceil

import streamlit as st

from firewatch.config import DISPLAY_CLASS_ORDER, HISTORY_PAGE_SIZE, RISK_LEVELS
from firewatch.ui import components, data_access


def _reset_page():
    st.session_state["hist_page"] = 1


def _go(n: int):
    st.session_state["hist_page"] = n


def render_history():
    f1, f2 = st.columns(2)
    risk = f1.selectbox("Risk", ["All", *RISK_LEVELS], key="hist_risk",
                        on_change=_reset_page)                          # REQ-7.3
    cls = f2.selectbox("Class", ["All", *DISPLAY_CLASS_ORDER], key="hist_class",
                       on_change=_reset_page)

    page = st.session_state.get("hist_page", 1)
    rows, total = data_access.list_approved(
        page, HISTORY_PAGE_SIZE,
        class_filter=None if cls == "All" else cls,
        risk_filter=None if risk == "All" else risk,
    )
    pages = max(1, ceil(total / HISTORY_PAGE_SIZE))
    if page > pages:
        st.session_state["hist_page"] = page = pages
        rows, total = data_access.list_approved(
            page, HISTORY_PAGE_SIZE,
            class_filter=None if cls == "All" else cls,
            risk_filter=None if risk == "All" else risk)

    if not rows:
        st.info("No submissions match these filters yet.")              # REQ-7.5
        return

    for r in rows:                                                      # REQ-7.1
        with st.container(border=True):
            a, b, c, d = st.columns([1, 3, 1.4, 1.3], vertical_alignment="center")
            a.image(r["image_bytes"], width=64)
            b.markdown(f"**{components.class_label(r['predicted_class'], r['confidence'])}**")
            b.caption(f"{r['timestamp']:%Y-%m-%d %H:%M}")
            c.markdown(components.risk_badge(r["risk_level"]), unsafe_allow_html=True)
            if d.button("Details", key=f"det_{r['id']}"):               # REQ-7.4
                components.result_dialog(
                    {k: r[k] for k in ("predicted_class", "confidence",
                                       "probabilities", "risk_level")},
                    r["image_bytes"], heatmap_fn=None, timestamp=r["timestamp"])

    # Prev / 1 2 3 / Next (Fig 1)
    window = list(range(max(1, page - 2), min(pages, page + 2) + 1))
    cols = st.columns([1.3] + [0.7] * len(window) + [1.3])
    cols[0].button("‹ Prev", disabled=page <= 1, on_click=_go, args=(page - 1,),
                   key="pg_prev", use_container_width=True)
    for col, n in zip(cols[1:-1], window):
        col.button(str(n), key=f"pg_{n}", on_click=_go, args=(n,),
                   type="primary" if n == page else "secondary",
                   use_container_width=True)
    cols[-1].button("Next ›", disabled=page >= pages, on_click=_go, args=(page + 1,),
                    key="pg_next", use_container_width=True)