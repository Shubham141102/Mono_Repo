import calendar
import datetime as dt
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import db

user = st.session_state.user
today = dt.date.today()

# Categorical palette (validated: lightness, chroma, colour-blind separation). "Other" is neutral grey.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
OTHER_COLOR = "#8a8984"
MAX_SLICES = 6


def month_start(d, back=0):
    y, m = d.year, d.month - back
    while m <= 0:
        m += 12
        y -= 1
    return dt.date(y, m, 1)


def month_end(first):
    return first.replace(day=calendar.monthrange(first.year, first.month)[1])


def inr(x):
    return f"₹{x:,.0f}"


st.title("📊 Overview")

# ---------------- month picker
months = [month_start(today, i) for i in range(12)]
picked = st.selectbox("Month", months, format_func=lambda d: d.strftime("%B %Y"))
start, end = picked, min(month_end(picked), today)
prev_start = month_start(picked, 1)

income, expense = db.totals(user["id"], start, end)
p_income, p_expense = db.totals(user["id"], prev_start, month_end(prev_start))
net = income - expense
rate = f"{net / income:.0%}" if income else "—"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Income", inr(income), f"{income - p_income:+,.0f} vs last month" if p_income or p_expense else None)
c2.metric("Expense", inr(expense), f"{expense - p_expense:+,.0f} vs last month" if p_income or p_expense else None,
          delta_color="inverse")
c3.metric("Net", inr(net))
c4.metric("Savings rate", rate)


# ---------------- breakdown (donut + ranked list)
def breakdown(kind):
    rows = db.category_breakdown(user["id"], kind, start, end)
    if not rows:
        st.info(f"No {kind} recorded in {picked.strftime('%B %Y')}.")
        return
    for r in rows:
        r["total"] = float(r["total"])
    total = sum(r["total"] for r in rows)

    # at most 6 slices: top 5 + "Other" when there are more than 6 categories
    if len(rows) > MAX_SLICES:
        shown, rest = rows[: MAX_SLICES - 1], rows[MAX_SLICES - 1:]
    else:
        shown, rest = rows, []
    colors = {r["id"]: PALETTE[i] for i, r in enumerate(shown)}
    labels = [f"{r['icon']} {r['name']}" for r in shown]
    values = [r["total"] for r in shown]
    slice_colors = [colors[r["id"]] for r in shown]
    if rest:
        labels.append(f"Other ({len(rest)})")
        values.append(sum(r["total"] for r in rest))
        slice_colors.append(OTHER_COLOR)

    left, right = st.columns([1, 1], vertical_alignment="center")
    with left:
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.62, sort=False, direction="clockwise",
            marker=dict(colors=slice_colors, line=dict(color="rgba(0,0,0,0)", width=2)),
            textinfo="percent", textposition="inside", insidetextorientation="horizontal",
            hovertemplate="%{label}<br>₹%{value:,.0f} · %{percent}<extra></extra>",
        ))
        fig.update_layout(
            showlegend=False, height=280, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text=f"<b>{inr(total)}</b><br><span style='font-size:12px'>total {kind}</span>",
                              showarrow=False, font=dict(size=18))],
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"donut_{kind}")

    with right:
        for r in rows:  # every category, largest first; swatch matches its slice
            color = colors.get(r["id"], OTHER_COLOR)
            share = r["total"] / total
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;gap:8px;font-size:14px'>"
                f"<span><span style='display:inline-block;width:10px;height:10px;border-radius:2px;"
                f"background:{color};margin-right:6px'></span>{html.escape(r['icon'] + ' ' + r['name'])}</span>"
                f"<span><b>{inr(r['total'])}</b> · {share:.0%}</span></div>",
                unsafe_allow_html=True,
            )
            st.progress(share)


tab_exp, tab_inc = st.tabs(["Expenses by category", "Income by category"])
with tab_exp:
    breakdown("expense")
with tab_inc:
    breakdown("income")

# ---------------- 12-month summary table
st.subheader("Monthly summary")
summary = {r["month"]: r for r in db.monthly_summary(user["id"], months[-1])}
table = []
for m in months:  # newest first, zeros for empty months
    r = summary.get(m.strftime("%Y-%m"), {})
    inc, exp = float(r.get("income") or 0), float(r.get("expense") or 0)
    table.append({"Month": m.strftime("%b %Y"), "Income (₹)": inc, "Expense (₹)": exp,
                  "Net (₹)": inc - exp, "Savings rate": (inc - exp) / inc if inc else None})
df = pd.DataFrame(table)
ti, te = df["Income (₹)"].sum(), df["Expense (₹)"].sum()
df.loc[len(df)] = {"Month": "Total (12 months)", "Income (₹)": ti, "Expense (₹)": te,
                   "Net (₹)": ti - te, "Savings rate": (ti - te) / ti if ti else None}
df["Savings rate"] = df["Savings rate"] * 100

st.dataframe(
    df, hide_index=True, width="stretch",
    column_config={
        "Income (₹)": st.column_config.NumberColumn(format="localized"),
        "Expense (₹)": st.column_config.NumberColumn(format="localized"),
        "Net (₹)": st.column_config.NumberColumn(format="localized"),
        "Savings rate": st.column_config.NumberColumn(format="%.0f%%"),
    },
)
