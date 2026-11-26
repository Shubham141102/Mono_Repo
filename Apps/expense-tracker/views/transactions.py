import datetime as dt
import math
import time

import pandas as pd
import streamlit as st

import db

user = st.session_state.user
today = dt.date.today()
PAGE_SIZE = 50
ss = st.session_state
ss.setdefault("editor_v", 0)

st.title("💳 Transactions")

# ---------------- add form (TXN-1, TXN-2)
with st.container(border=True):
    kind = (st.segmented_control("Type", ["Expense", "Income"], default="Expense", key="add_kind") or "Expense").lower()
    active_cats = db.get_categories(user["id"], kind, include_archived=False)
    if not active_cats:
        st.warning(f"No active {kind} categories. Add or restore one on the Categories page.")
    else:
        with st.form("add_txn", clear_on_submit=True):
            c1, c2 = st.columns(2)
            amount = c1.number_input("Amount (₹)", min_value=0.0, step=50.0, format="%.2f")
            category = c2.selectbox("Category", active_cats, format_func=lambda c: f"{c['icon']} {c['name']}")
            c3, c4 = st.columns(2)
            txn_date = c3.date_input("Date", value=today, max_value=today)
            payment = c4.selectbox("Payment method", db.PAYMENT_METHODS)
            tags = st.text_input("Tags (optional, comma separated)", placeholder="e.g. trip-goa, office")
            note = st.text_input("Notes (optional)", placeholder="e.g. dinner with friends")
            if st.form_submit_button(f"Add {kind}", type="primary", width="stretch"):
                clean_tags = ",".join(t.strip().lower() for t in tags.split(",") if t.strip())
                sig = (kind, round(amount, 2), category["id"], txn_date, payment, clean_tags, note.strip())
                last = ss.get("last_add")
                if amount <= 0:
                    st.error("Amount must be greater than 0.")
                elif last and last[0] == sig and time.time() - last[1] < 10:
                    st.warning("Same transaction was just added, so this one was not saved. "
                               "If it's really a second one, submit again in a few seconds.")
                else:
                    db.add_transaction(user["id"], kind, amount, category["id"], txn_date,
                                       payment, clean_tags, note.strip())
                    ss.last_add = (sig, time.time())
                    st.toast(f"Added {category['icon']} {category['name']} · ₹{amount:,.2f}")

# ---------------- filters (TXN-4)
st.subheader("History")
all_cats = db.get_categories(user["id"])
f1, f2 = st.columns([2, 1])
period = f1.date_input("Date range", value=(today.replace(day=1), today), max_value=today)
type_label = f2.selectbox("Type", ["All", "Expense", "Income"])
f_kind = None if type_label == "All" else type_label.lower()
f3, f4 = st.columns(2)
picked = f3.multiselect(
    "Categories", [c for c in all_cats if f_kind is None or c["kind"] == f_kind],
    format_func=lambda c: f"{c['icon']} {c['name']} ({c['kind']})", placeholder="All categories")
pms = f4.multiselect("Payment method", db.PAYMENT_METHODS, placeholder="All methods")
f5, f6 = st.columns([2, 1])
search = f5.text_input("Search notes, tags or category", placeholder="e.g. biryani")
sort = f6.selectbox("Sort", list(db.SORTS))

if not isinstance(period, tuple) or len(period) != 2:
    st.info("Pick an end date for the range.")
    st.stop()
start, end = period
filters = dict(payment_methods=pms, search=search)
cids = [c["id"] for c in picked]

total, inc, exp = db.count_transactions(user["id"], start, end, f_kind, cids, **filters)
m1, m2, m3 = st.columns(3)
m1.metric("Income", f"₹{inc:,.0f}")
m2.metric("Expense", f"₹{exp:,.0f}")
m3.metric("Net", f"{'−' if inc < exp else ''}₹{abs(inc - exp):,.0f}")
if not total:
    st.info("No transactions match these filters.")
    st.stop()

# ---------------- pagination + export (TXN-4, TXN-6)
pages = math.ceil(total / PAGE_SIZE)
p1, p2, p3 = st.columns([1, 2, 1.4], vertical_alignment="bottom")
page = p1.number_input("Page", min_value=1, max_value=pages, value=1, step=1, key=f"page_{pages}") if pages > 1 else 1
p2.caption(f"{total} transactions · page {page} of {pages}")
all_rows = db.list_transactions(user["id"], start, end, f_kind, cids, sort=sort, **filters)
export = pd.DataFrame([{
    "Date": r["txn_date"], "Type": r["kind"].title(), "Category": r["category"], "Payment method": r["payment_method"],
    "Amount": float(r["amount"]), "Notes": r["note"], "Tags": r["tags"],
} for r in all_rows])
p3.download_button("⬇ Export CSV", export.to_csv(index=False).encode("utf-8"),
                   file_name=f"transactions_{start}_{end}.csv", mime="text/csv", width="stretch")

rows = db.list_transactions(user["id"], start, end, f_kind, cids, limit=PAGE_SIZE,
                            offset=(page - 1) * PAGE_SIZE, sort=sort, **filters)
label = lambda c: f"{c['icon']} {c['name']}"
cat_by_label = {(c["kind"], label(c)): c["id"] for c in all_cats}

df = pd.DataFrame(rows)
df["txn_date"] = pd.to_datetime(df["txn_date"]).dt.date
df["amount"] = df["amount"].astype(float)
df["category"] = df["icon"] + " " + df["category"]

edit_mode = st.toggle("Edit mode", help="Turn on to change or delete transactions.")

# ---------------- read-only view with green / red amounts (TXN-3)
if not edit_mode:
    view = pd.DataFrame({
        "Date": df["txn_date"], "Type": df["kind"].str.title(), "Category": df["category"],
        "Payment": df["payment_method"],
        "Amount (₹)": df.apply(lambda r: r["amount"] if r["kind"] == "income" else -r["amount"], axis=1),
        "Notes": df["note"], "Tags": df["tags"],
    })
    styled = (view.style
              .format({"Amount (₹)": lambda v: f"{'+' if v > 0 else '−'}{abs(v):,.2f}"})
              .map(lambda v: "color: #0ca30c; font-weight: 600" if v > 0 else "color: #e34948; font-weight: 600",
                   subset=["Amount (₹)"]))
    st.dataframe(styled, hide_index=True, width="stretch")
    st.stop()

# ---------------- edit / delete (TXN-5)
if ss.get("pending_delete"):
    ids = ss.pending_delete
    st.warning(f"Delete {len(ids)} transaction(s)? This can't be undone.")
    a, b, _ = st.columns([1, 1, 3])
    if a.button("Yes, delete", type="primary"):
        n = sum(db.delete_transaction(user["id"], i) for i in ids)
        ss.pending_delete = None
        ss.editor_v += 1
        st.toast(f"Deleted {n}.")
        st.rerun()
    if b.button("Cancel"):
        ss.pending_delete = None
        ss.editor_v += 1
        st.rerun()

df["delete"] = False
df = df[["id", "txn_date", "kind", "category", "amount", "payment_method", "tags", "note", "delete"]]
edited = st.data_editor(
    df, key=f"txn_editor_{ss.editor_v}", hide_index=True, width="stretch", disabled=["id", "kind"],
    column_config={
        "id": None,
        "txn_date": st.column_config.DateColumn("Date", max_value=today, required=True),
        "kind": st.column_config.TextColumn("Type"),
        "category": st.column_config.SelectboxColumn(
            "Category", options=sorted({label(c) for c in all_cats}), required=True),
        "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.01, format="%.2f", required=True),
        "payment_method": st.column_config.SelectboxColumn("Payment", options=db.PAYMENT_METHODS, required=True),
        "tags": st.column_config.TextColumn("Tags"),
        "note": st.column_config.TextColumn("Notes"),
        "delete": st.column_config.CheckboxColumn("Delete"),
    },
)

if st.button("Save changes", type="primary"):
    updated, to_delete, errors = 0, [], []
    for orig, new in zip(df.to_dict("records"), edited.to_dict("records")):
        if new["delete"]:
            to_delete.append(orig["id"])
            continue
        if all(orig[k] == new[k] for k in ["txn_date", "category", "amount", "payment_method", "tags", "note"]):
            continue
        cid = cat_by_label.get((orig["kind"], new["category"]))
        if cid is None:
            errors.append(f"{new['category']} is not a {orig['kind']} category.")
            continue
        clean_tags = ",".join(t.strip().lower() for t in str(new["tags"] or "").split(",") if t.strip())
        updated += db.update_transaction(user["id"], orig["id"], orig["kind"], new["amount"], cid,
                                         new["txn_date"], new["payment_method"], clean_tags,
                                         str(new["note"] or "").strip())
    for e in errors:
        st.error(e)
    if to_delete:
        ss.pending_delete = to_delete
    if updated:
        st.toast(f"Updated {updated}.")
    if updated or to_delete:
        ss.editor_v += 1
        st.rerun()
