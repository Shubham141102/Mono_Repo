import datetime as dt

import pandas as pd
import streamlit as st

import db

user = st.session_state.user
today = dt.date.today()
ss = st.session_state
ss.setdefault("cat_v", 0)

ICONS = ["📦", "🍔", "☕", "🛒", "🏠", "🚗", "⛽", "🚇", "💡", "📱", "🛍️", "👕", "💊", "🏥", "🏋️", "🎬",
         "🎮", "📚", "✈️", "🎁", "🐶", "👶", "💇", "🧾", "💼", "💻", "🏢", "📈", "🏦", "💰", "💳", "🏆", "🪙", "🎓"]
COLOR_NAMES = ["Auto"] + list(db.COLORS)
NAME_BY_HEX = {v: k for k, v in db.COLORS.items()}

st.title("🏷️ Categories")
st.caption("Expense and income have separate lists. Archived categories are hidden from the add form "
           "but stay on old transactions and charts.")

period = st.segmented_control("Totals for", ["This month", "This year", "All time"], default="This month") or "This month"
start = {"This month": today.replace(day=1), "This year": dt.date(today.year, 1, 1),
         "All time": dt.date(1900, 1, 1)}[period]


def delete_panel(kind, cats):
    """Confirm deletions; categories with transactions are reassigned or archived (CAT-5)."""
    by_id = {c["id"]: c for c in cats}
    pend = [cid for cid in ss.get(f"pend_{kind}", []) if cid in by_id]
    if not pend:
        return
    with st.container(border=True):
        st.markdown("**Confirm deletion**")
        plan = {}
        for cid in pend:
            c = by_id[cid]
            name = f"{c['icon']} {c['name']}"
            if c["records"] == 0:
                st.write(f"{name} has no transactions and will be deleted.")
                plan[cid] = ("delete", None)
                continue
            st.write(f"{name} has **{c['records']}** transactions. What should happen to them?")
            action = st.radio("Action", ["Move them to another category", "Archive the category instead"],
                              key=f"act_{cid}", horizontal=True, label_visibility="collapsed")
            if action.startswith("Move"):
                targets = [x for x in cats if x["id"] != cid and not x["archived"]]
                to = st.selectbox("Move to", targets, key=f"to_{cid}",
                                  format_func=lambda x: f"{x['icon']} {x['name']}")
                plan[cid] = ("move", to["id"] if to else None)
            else:
                plan[cid] = ("archive", None)
        a, b, _ = st.columns([1, 1, 3])
        if a.button("Confirm", type="primary", key=f"confirm_{kind}"):
            msgs = []
            for cid, (act, to) in plan.items():
                try:
                    if act == "delete":
                        db.delete_category(user["id"], cid)
                    elif act == "move":
                        n = db.reassign_and_delete(user["id"], cid, to)
                        msgs.append(f"moved {n}")
                    else:
                        db.set_archived(user["id"], cid, True)
                except ValueError as e:
                    st.error(f"{by_id[cid]['name']}: {e}")
            ss[f"pend_{kind}"] = []
            ss.cat_v += 1
            st.toast("Done" + (f" ({', '.join(msgs)} transactions)" if msgs else "."))
            st.rerun()
        if b.button("Cancel", key=f"cancel_{kind}"):
            ss[f"pend_{kind}"] = []
            ss.cat_v += 1
            st.rerun()


def manage(kind):
    # ---- add (CAT-4)
    with st.form(f"add_cat_{kind}", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([1, 1.3, 3, 1.2], vertical_alignment="bottom")
        icon = c1.selectbox("Icon", ICONS, key=f"icon_{kind}")
        color = c2.selectbox("Colour", COLOR_NAMES, key=f"color_{kind}")
        name = c3.text_input("New category name", key=f"name_{kind}",
                             placeholder="e.g. Petrol" if kind == "expense" else "e.g. Side Business")
        if c4.form_submit_button("Add", type="primary", width="stretch"):
            try:
                db.add_category(user["id"], kind, name, icon)
                if color != "Auto":
                    new = next(c for c in db.get_categories(user["id"], kind)
                               if c["name"].lower() == name.strip().lower() and c["is_custom"])
                    db.set_color(user["id"], new["id"], db.COLORS[color])
                st.toast(f"Added {icon} {name.strip()}")
            except ValueError as e:
                st.error(str(e))

    cats = db.get_categories(user["id"], kind)
    delete_panel(kind, cats)

    totals = {r["id"]: r for r in db.category_breakdown(user["id"], kind, start, today)}
    df = pd.DataFrame(cats)
    df["source"] = df["is_custom"].map({1: "Custom", 0: "Built-in"})
    df["archived"] = df["archived"].astype(bool)
    df["colour"] = df["color"].map(lambda h: NAME_BY_HEX.get(h, "Auto") if h else "Auto")
    df["total"] = df["id"].map(lambda i: float(totals[i]["total"]) if i in totals else 0.0)
    df["count"] = df["id"].map(lambda i: int(totals[i]["n"]) if i in totals else 0)
    df["delete"] = False
    df = df.sort_values(["archived", "total", "name"], ascending=[True, False, True])
    df = df[["id", "icon", "colour", "name", "source", "total", "count", "archived", "delete"]]

    # ---- list / edit (CAT-1, CAT-4, CAT-6)
    edited = st.data_editor(
        df, key=f"cat_editor_{kind}_{ss.cat_v}", hide_index=True, width="stretch",
        disabled=["id", "source", "total", "count"],
        column_config={
            "id": None,
            "icon": st.column_config.SelectboxColumn("Icon", options=sorted(set(ICONS) | set(df["icon"])), width="small"),
            "colour": st.column_config.SelectboxColumn("Colour", options=COLOR_NAMES, required=True, width="small"),
            "name": st.column_config.TextColumn("Name", required=True, max_chars=50),
            "source": st.column_config.TextColumn("Type"),
            "total": st.column_config.NumberColumn(
                "Spent (₹)" if kind == "expense" else "Received (₹)", format="localized"),
            "count": st.column_config.NumberColumn("Transactions"),
            "archived": st.column_config.CheckboxColumn("Archived"),
            "delete": st.column_config.CheckboxColumn("Delete"),
        },
    )
    st.caption(f"Totals are for {period.lower()}. Built-in categories can't be renamed or deleted, "
               "only archived; colour applies to your charts.")

    if st.button("Save changes", type="primary", key=f"save_{kind}"):
        changed, errors, to_delete = 0, [], []
        for orig, new in zip(df.to_dict("records"), edited.to_dict("records")):
            label = f"{orig['icon']} {orig['name']}"
            try:
                if new["delete"]:
                    if orig["source"] != "Custom":
                        raise ValueError("Built-in categories can't be deleted. Archive it instead.")
                    to_delete.append(orig["id"])
                    continue
                if (new["name"], new["icon"]) != (orig["name"], orig["icon"]):
                    if orig["source"] != "Custom":
                        raise ValueError("Built-in categories can't be renamed. Archive it and add your own.")
                    db.update_category(user["id"], orig["id"], str(new["name"] or ""), new["icon"])
                    changed += 1
                if new["colour"] != orig["colour"]:
                    db.set_color(user["id"], orig["id"], db.COLORS.get(new["colour"]))
                    changed += 1
                if new["archived"] != orig["archived"]:
                    db.set_archived(user["id"], orig["id"], new["archived"])
                    changed += 1
            except ValueError as e:
                errors.append(f"{label}: {e}")
        for e in errors:
            st.error(e)
        if to_delete:
            ss[f"pend_{kind}"] = to_delete
        if changed:
            st.toast(f"Saved {changed} change(s).")
        if (changed or to_delete) and not errors:
            ss.cat_v += 1
            st.rerun()


tab_exp, tab_inc = st.tabs(["Expense categories", "Income categories"])
with tab_exp:
    manage("expense")
with tab_inc:
    manage("income")
