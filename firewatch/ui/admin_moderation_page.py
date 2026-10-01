"""Admin moderation (Fig 4)."""
import streamlit as st

from firewatch.config import DISPLAY_CLASS_ORDER, FLAG_REASONS, RISK_LEVELS, STATUSES
from firewatch.ui import components, data_access


@st.dialog("Remove submission")
def _confirm_remove(sub_id: int, admin_id: int):
    st.warning("This permanently deletes the image and its record. It cannot be undone.")  # REQ-9.5
    c1, c2 = st.columns(2)
    if c1.button("Delete permanently", type="primary", use_container_width=True):
        data_access.remove(sub_id, admin_id)
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


def _none_if_all(v):
    return None if v == "All" else v


def render():
    admin_id = components.require_admin()
    components.admin_header("moderation")

    f = st.columns(4)                                                   # REQ-9.2
    risk = f[0].selectbox("Risk", ["All", *RISK_LEVELS])
    cls = f[1].selectbox("Class", ["All", *DISPLAY_CLASS_ORDER])
    status = f[2].selectbox("Status", ["All", *STATUSES])
    dates = f[3].date_input("Date", value=[], help="Pick one day or a range")
    d_from = dates[0] if len(dates) >= 1 else None
    d_to = dates[-1] if len(dates) >= 1 else None

    rows = data_access.list_all(_none_if_all(risk), _none_if_all(cls),
                                _none_if_all(status), d_from, d_to)     # REQ-9.1

    heads = st.columns([1, 1.2, 1.2, 1.2, 1.2, 3.2])
    for h, label in zip(heads, ["", "Class", "Confidence", "Risk", "Status", "Actions"]):
        h.caption(label)

    if not rows:
        st.info("No submissions match these filters.")
    for r in rows:
        c = st.columns([1, 1.2, 1.2, 1.2, 1.2, 3.2], vertical_alignment="center")
        c[0].image(r["image_bytes"], width=56)
        c[1].write(r["predicted_class"])
        c[2].write(f"{r['confidence']:.0%}")
        c[3].markdown(components.risk_badge(r["risk_level"]), unsafe_allow_html=True)
        c[4].write(r["status"])
        a1, a2, a3 = c[5].columns(3)
        if a1.button("Approve", key=f"ap_{r['id']}", use_container_width=True):
            data_access.approve(r["id"], admin_id)
            st.rerun()
        if a2.button("Flag", key=f"fl_{r['id']}", use_container_width=True):
            _flag_dialog(r, admin_id)
        if a3.button("Remove", key=f"rm_{r['id']}", use_container_width=True):
            _confirm_remove(r["id"], admin_id)


@st.dialog("Flag submission")
def _flag_dialog(row: dict, admin_id: int):
    img, info = st.columns([1, 2], vertical_alignment="center")
    img.image(row["image_bytes"], use_container_width=True)
    info.markdown(f"**Submission #{row['id']}**")
    info.caption(f"Predicted: {row['predicted_class']} ({row['confidence']:.0%}) · "
                 f"Risk: {row['risk_level']} · Status: {row['status']}")

    reason = st.selectbox("Reason", FLAG_REASONS)                            # REQ-9.4
    correct = st.selectbox("Correct class (optional)", ["Not set", *DISPLAY_CLASS_ORDER])
    note = st.text_area("Optional note", placeholder="Optional note...")

    b1, b2 = st.columns(2)
    if b1.button("Save flag", type="primary", use_container_width=True):
        data_access.flag(row["id"], admin_id, reason,
                         None if correct == "Not set" else correct, note)
        st.rerun()                                   # closes the popup and refreshes the table
    if b2.button("Cancel", use_container_width=True):
        st.rerun()