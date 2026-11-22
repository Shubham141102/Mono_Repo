import datetime as dt

import pandas as pd
import streamlit as st

import db

user = st.session_state.user
today = dt.date.today()

st.title("📝 Records")

# ---------------- add form
with st.container(border=True):
    kind_label = st.segmented_control("Type", ["Expense", "Income"], default="Expense", key="add_kind") or "Expense"
    kind = kind_label.lower()
    active_cats = db.get_categories(user["id"], kind, include_archived=False)

    if not active_cats:
        st.warning(f"No active {kind} categories. Add or unarchive one on the Categories page.")
    else:
        with st.form("add_txn", clear_on_submit=True):
            c1, c2 = st.columns(2)
            amount = c1.number_input("Amount (₹)", min_value=0.0, step=50.0, format="%.2f")
            category = c2.selectbox("Category", active_cats, format_func=lambda c: f"{c['icon']} {c['name']}")
            c3, c4 = st.columns(2)
            txn_date = c3.date_input("Date", value=today, max_value=today)
            payment = c4.selectbox("Payment method", db.PAYMENT_METHODS)
            tags = st.text_input("Tags (optional, comma separated)", placeholder="e.g. trip-goa, office")
            note = st.text_input("Note (optional)", placeholder="e.g. dinner with friends")
            if st.form_submit_button(f"Add {kind}", type="primary", width="stretch"):
                if amount <= 0:
                    st.error("Amount must be greater than 0.")
                else:
                    clean_tags = ",".join(t.strip().lower() for t in tags.split(",") if t.strip())
                    db.add_transaction(user["id"], kind, amount, category["id"], txn_date,
                                       payment, clean_tags, note.strip())
                    st.toast(f"Added {category['icon']} {category['name']} · ₹{amount:,.2f}")

# ---------------- filters
st.subheader("Your records")
c1, c2 = st.columns([2, 1])
period = c1.date_input("Date range", value=(today.replace(day=1), today), max_value=today)
type_label = c2.selectbox("Show", ["All", "Expense", "Income"])
f_kind = None if type_label == "All" else type_label.lower()

all_cats = db.get_categories(user["id"])
picked = st.multiselect(
    "Categories", [c for c in all_cats if f_kind is None or c["kind"] == f_kind],
    format_func=lambda c: f"{c['icon']} {c['name']} ({c['kind']})", placeholder="All categories",
)
if not isinstance(period, tuple) or len(period) != 2:
    st.info("Pick an end date for the range.")
    st.stop()
start, end = period

rows = db.list_transactions(user["id"], start, end, f_kind, [c["id"] for c in picked])
if not rows:
    st.info("No records for these filters.")
    st.stop()

inc = sum(float(r["amount"]) for r in rows if r["kind"] == "income")
exp = sum(float(r["amount"]) for r in rows if r["kind"] == "expense")
m1, m2, m3 = st.columns(3)
m1.metric("Income", f"₹{inc:,.0f}")
m2.metric("Expense", f"₹{exp:,.0f}")
m3.metric("Net", f"₹{inc - exp:,.0f}")

# ---------------- editable list
label = lambda c: f"{c['icon']} {c['name']}"
cat_by_label = {(c["kind"], label(c)): c["id"] for c in all_cats}

df = pd.DataFrame(rows)
df["txn_date"] = pd.to_datetime(df["txn_date"]).dt.date
df["amount"] = df["amount"].astype(float)
df["category"] = df["icon"] + " " + df["category"]
df["delete"] = False
df = df[["id", "txn_date", "kind", "category", "amount", "payment_method", "tags", "note", "delete"]]

st.caption(f"{len(df)} records · edit cells directly, tick **Delete** to remove, then **Save changes**.")
edited = st.data_editor(
    df, key="txn_editor", hide_index=True, width="stretch", disabled=["id", "kind"],
    column_config={
        "id": None,
        "txn_date": st.column_config.DateColumn("Date", max_value=today, required=True),
        "kind": st.column_config.TextColumn("Type"),
        "category": st.column_config.SelectboxColumn(
            "Category", options=sorted({label(c) for c in all_cats}), required=True),
        "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.01, format="%.2f", required=True),
        "payment_method": st.column_config.SelectboxColumn("Payment", options=db.PAYMENT_METHODS, required=True),
        "tags": st.column_config.TextColumn("Tags"),
        "note": st.column_config.TextColumn("Note"),
        "delete": st.column_config.CheckboxColumn("Delete"),
    },
)

if st.button("Save changes", type="primary"):
    updated = deleted = 0
    errors = []
    for orig, new in zip(df.to_dict("records"), edited.to_dict("records")):
        if new["delete"]:
            deleted += db.delete_transaction(user["id"], orig["id"])
            continue
        if all(orig[k] == new[k] for k in ["txn_date", "category", "amount", "payment_method", "tags", "note"]):
            continue
        cid = cat_by_label.get((orig["kind"], new["category"]))
        if cid is None:
            errors.append(f"{new['category']} is not a valid {orig['kind']} category.")
            continue
        tags = ",".join(t.strip().lower() for t in str(new["tags"] or "").split(",") if t.strip())
        updated += db.update_transaction(
            user["id"], orig["id"], orig["kind"], new["amount"], cid, new["txn_date"],
            new["payment_method"], tags, str(new["note"] or "").strip(),
        )
    for e in errors:
        st.error(e)
    st.toast(f"Updated {updated}, deleted {deleted}.")
    if updated or deleted:
        st.rerun()
