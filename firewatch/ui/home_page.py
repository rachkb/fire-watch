"""Landing page: history on the left, upload on the right (Fig 1)."""
import streamlit as st

from firewatch.ui import components, history_page, upload_page


def render():
    components.header()
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown("**Submission history**")
        history_page.render_history()
    with right:
        st.markdown("**Upload image**")
        upload_page.render_upload()
    st.divider()
    components.disclaimer()