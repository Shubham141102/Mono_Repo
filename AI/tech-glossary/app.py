"""Tech Glossary - entry point. Run with:  streamlit run app.py"""
import streamlit as st

import db
import ui

st.set_page_config(page_title="Tech Glossary", page_icon="📘", layout="centered",
                   initial_sidebar_state="expanded")
db.init()
ui.apply_css()

nav = st.navigation([
    st.Page("chat_page.py", title="Ask", icon="💬", default=True),
    st.Page("glossary_page.py", title="Glossary", icon="📚"),
])
nav.run()
