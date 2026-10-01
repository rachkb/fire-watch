"""Admin login (Fig 3)."""
from datetime import datetime

import streamlit as st

from firewatch.ui import data_access


def render():
    if st.session_state.get("admin_id") is not None:
        st.switch_page(st.session_state["pages"]["moderation"])

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        st.markdown("<h3 style='text-align:center'> FireWatch</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center'><b>Admin Login</b><br>"
                    "Enter your credentials to log in</p>", unsafe_allow_html=True)

        notice = st.session_state.pop("login_notice", None)
        if notice:
            st.info(notice)

        with st.form("admin_login"):                    # Enter submits the form
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            try:
                admin_id = data_access.authenticate(username.strip(), password)
            except data_access.LoginLocked as e:        # REQ-8.4
                st.error(f"Too many failed attempts. Try again in {e.minutes} minute(s).")
            else:
                if admin_id is None:
                    st.error("Invalid username or password.")   # REQ-8.3: generic on purpose
                else:
                    st.session_state["admin_id"] = admin_id
                    st.session_state["admin_username"] = username.strip()
                    st.session_state["admin_last_activity"] = datetime.now()
                    st.switch_page(st.session_state["pages"]["moderation"])

        st.page_link(st.session_state["pages"]["home"], label="Back to FireWatch", icon="⬅️")