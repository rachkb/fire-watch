"""Admin analytics (Fig 5). The wireframe leaves the cards unlabeled, so this
uses: 4 status/total cards, a class/risk chart panel, and a misclassification panel."""
import pandas as pd
import streamlit as st

from firewatch.config import RISK_LEVELS
from firewatch.ui import components, data_access


def render():
    components.require_admin()
    components.admin_header("analytics")
    s = data_access.analytics()                                         # REQ-10.1

    cards = st.columns(4)
    cards[0].metric("Total submissions", s["total"])
    cards[1].metric("Pending", s["by_status"]["Pending"])
    cards[2].metric("Approved", s["by_status"]["Approved"])
    cards[3].metric("Flagged", s["by_status"]["Flagged"])

    left, right = st.columns(2)
    with left.container(border=True):
        tab_class, tab_risk = st.tabs(["By predicted class", "By risk level"])

        class_df = pd.DataFrame({
            "Class": list(s["by_class"].keys()),
            "Count": list(s["by_class"].values()),
        })
        tab_class.bar_chart(class_df, x="Class", y="Count")

        risk_df = pd.DataFrame({
            "Risk level": list(s["by_risk"].keys()),
            "Count": list(s["by_risk"].values()),
        })
        tab_risk.bar_chart(risk_df, x="Risk level", y="Count")
    with right.container(border=True):
        st.markdown("**Administrator-reported errors**")
        m1, m2 = st.columns(2)
        m1.metric("False negatives", s["false_negatives"],
                  help="Flagged Misclassified: Fire or Smoke image predicted Non-Fire")
        m2.metric("False positives", s["false_positives"],
                  help="Flagged Misclassified: Non-Fire image predicted Fire or Smoke")

    st.caption("Based only on submissions reviewed by administrators, "
               "not a measure of overall model accuracy.")              # REQ-10.4

    risk = st.selectbox("Risk", ["All", *RISK_LEVELS])                  # REQ-10.2
    rows = data_access.list_all(risk=None if risk == "All" else risk, limit=10)

    heads = st.columns([1, 1.5, 1.5, 1.5, 2])
    for h, label in zip(heads, ["", "Class", "Confidence", "Risk", "Date"]):
        h.caption(label)
    if not rows:
        st.info("No detections match this filter.")
    for r in rows:
        c = st.columns([1, 1.5, 1.5, 1.5, 2], vertical_alignment="center")
        c[0].image(r["image_bytes"], width=56)
        c[1].write(r["predicted_class"])
        c[2].write(f"{r['confidence']:.0%}")
        c[3].markdown(components.risk_badge(r["risk_level"]), unsafe_allow_html=True)
        c[4].write(f"{r['timestamp']:%Y-%m-%d %H:%M}")