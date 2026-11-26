"""Expense Tracker - entry point. Run with:  streamlit run app.py"""
import streamlit as st

import auth
import db

st.set_page_config(page_title="Expense Tracker", page_icon="💸", layout="centered")
db.init_db()


def login_page():
    st.title("💸 Expense Tracker")
    st.caption("Track your income, expenses and budgets. Your data is private to your account.")
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary", width="stretch"):
                user, msg = auth.login(email, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                st.error(msg)

    with tab_signup:
        with st.form("signup", clear_on_submit=False):
            name = st.text_input("Name")
            email = st.text_input("Email ")
            password = st.text_input("Password (min 8 characters)", type="password")
            confirm = st.text_input("Confirm password", type="password")
            code = st.text_input("Invite code") if db._secret("INVITE_CODE") else ""
            if st.form_submit_button("Create account", type="primary", width="stretch"):
                ok, msg = auth.signup(name, email, password, confirm, code)
                (st.success if ok else st.error)(msg)


user = st.session_state.get("user")

if not user:
    pg = st.navigation([st.Page(login_page, title="Log in", icon="🔐")])
else:
    with st.sidebar:
        st.markdown(f"**{user['name']}**  \n{user['email']}")
        if user["role"] == "admin":
            st.caption("Admin")
        if st.button("Log out", width="stretch"):
            st.session_state.clear()
            st.rerun()
    pg = st.navigation([
        st.Page("views/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("views/transactions.py", title="Transactions", icon="💳"),
        st.Page("views/categories.py", title="Categories", icon="🏷️"),
    ])

pg.run()
