import streamlit as st

from firewatch.ui import (admin_analytics_page, admin_login_page,
                          admin_moderation_page, home_page)

st.set_page_config(page_title="FireWatch", page_icon="🔥", layout="wide")

pages = {
    "home": st.Page(home_page.render, title="Home", url_path="home", default=True),
    "login": st.Page(admin_login_page.render, title="Admin Login", url_path="admin-login"),
    "moderation": st.Page(admin_moderation_page.render, title="Moderation",
                          url_path="admin-moderation"),
    "analytics": st.Page(admin_analytics_page.render, title="Analytics",
                         url_path="admin-analytics"),
}
st.session_state["pages"] = pages          # lets any page link to another

# Hidden sidebar navigation so the layout matches the wireframes.
# position="hidden" needs a recent Streamlit (about 1.46+). Check: pip show streamlit
st.navigation(list(pages.values()), position="hidden").run()