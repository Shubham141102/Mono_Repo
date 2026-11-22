import pandas as pd
import streamlit as st

import db

user = st.session_state.user

ICONS = ["📦", "🍔", "☕", "🛒", "🏠", "🚗", "⛽", "🚇", "💡", "📱", "🛍️", "👕", "💊", "🏋️", "🎬",
         "🎮", "📚", "✈️", "🎁", "🐶", "👶", "💇", "🧾", "💼", "💻", "📈", "🏦", "💰", "🪙", "🎓"]

st.title("🏷️ Categories")
st.caption("Expense and income have separate lists. Archived categories are hidden from the add form "
           "but kept on old records and charts. Only custom categories with no records can be deleted.")


def manage(kind):
    # ---- add
    with st.form(f"add_cat_{kind}", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 3, 1.3], vertical_alignment="bottom")
        icon = c1.selectbox("Icon", ICONS, key=f"icon_{kind}")
        name = c2.text_input("New category name", key=f"name_{kind}",
                             placeholder="e.g. Chai" if kind == "expense" else "e.g. Rental income")
        if c3.form_submit_button("Add", type="primary", width="stretch"):
            try:
                db.add_category(user["id"], kind, name, icon)
                st.toast(f"Added {icon} {name.strip()}")
            except ValueError as e:
                st.error(str(e))

    # ---- list / edit
    cats = db.get_categories(user["id"], kind)
    df = pd.DataFrame(cats)
    df["source"] = df["is_custom"].map({1: "Custom", 0: "Built-in"})
    df["archived"] = df["archived"].astype(bool)
    df["delete"] = False
    df = df[["id", "icon", "name", "source", "records", "archived", "delete"]]

    edited = st.data_editor(
        df, key=f"cat_editor_{kind}", hide_index=True, width="stretch",
        disabled=["id", "source", "records"],
        column_config={
            "id": None,
            "icon": st.column_config.SelectboxColumn("Icon", options=sorted(set(ICONS) | set(df["icon"])), width="small"),
            "name": st.column_config.TextColumn("Name", required=True, max_chars=50),
            "source": st.column_config.TextColumn("Type"),
            "records": st.column_config.NumberColumn("Records"),
            "archived": st.column_config.CheckboxColumn("Archived"),
            "delete": st.column_config.CheckboxColumn("Delete"),
        },
    )
    st.caption("Built-in categories can only be archived. Rename or change the icon of your own categories in the table.")

    if st.button("Save changes", type="primary", key=f"save_{kind}"):
        changed, errors = 0, []
        for orig, new in zip(df.to_dict("records"), edited.to_dict("records")):
            label = f"{orig['icon']} {orig['name']}"
            try:
                if new["delete"]:
                    db.delete_category(user["id"], orig["id"])
                    changed += 1
                    continue
                if (new["name"], new["icon"]) != (orig["name"], orig["icon"]):
                    if orig["source"] != "Custom":
                        raise ValueError("Built-in categories can't be renamed. Archive it and add your own instead.")
                    db.update_category(user["id"], orig["id"], str(new["name"] or ""), new["icon"])
                    changed += 1
                if new["archived"] != orig["archived"]:
                    db.set_archived(user["id"], orig["id"], new["archived"])
                    changed += 1
            except ValueError as e:
                errors.append(f"{label}: {e}")
        for e in errors:
            st.error(e)
        if changed and not errors:
            st.toast(f"Saved {changed} change(s).")
            st.rerun()
        elif changed:
            st.toast(f"Saved {changed} change(s); some were rejected.")


tab_exp, tab_inc = st.tabs(["Expense categories", "Income categories"])
with tab_exp:
    manage("expense")
with tab_inc:
    manage("income")
