import calendar
import datetime as dt
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import db

user = st.session_state.user
today = dt.date.today()

PALETTE = list(db.COLORS.values())      # validated categorical order
OTHER_COLOR = "#8a8984"                 # neutral grey for "Other"
INCOME_COLOR, EXPENSE_COLOR = PALETTE[0], PALETTE[1]
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
    return f"{'−' if x < 0 else ''}₹{abs(x):,.0f}"


st.title("📊 Dashboard")

# ---------------- period filter (DASH-1)
preset = st.segmented_control(
    "Period", ["This month", "Last month", "This year", "Custom"], default="This month") or "This month"
if preset == "This month":
    start, end = month_start(today), today
    p_start = month_start(today, 1)
    p_end = month_end(p_start)
    vs = "vs last month"
elif preset == "Last month":
    start = month_start(today, 1)
    end = month_end(start)
    p_start = month_start(today, 2)
    p_end = month_end(p_start)
    vs = "vs month before"
elif preset == "This year":
    start, end = dt.date(today.year, 1, 1), today
    p_start = dt.date(today.year - 1, 1, 1)
    last_day = calendar.monthrange(today.year - 1, today.month)[1]
    p_end = dt.date(today.year - 1, today.month, min(today.day, last_day))  # handles 29 Feb
    vs = "vs same period last year"
else:
    rng = st.date_input("Custom range", value=(month_start(today), today), max_value=today)
    if not isinstance(rng, tuple) or len(rng) != 2:
        st.info("Pick an end date for the range.")
        st.stop()
    start, end = rng
    p_end = start - dt.timedelta(days=1)
    p_start = p_end - (end - start)
    vs = "vs previous period"
st.caption(f"{start:%d %b %Y} – {end:%d %b %Y}")

# ---------------- summary cards (DASH-2)
income, expense = db.totals(user["id"], start, end)
p_income, p_expense = db.totals(user["id"], p_start, p_end)
net, p_net = income - expense, p_income - p_expense
has_prev = bool(p_income or p_expense)
delta = lambda cur, prev: f"{cur - prev:+,.0f} {vs}" if has_prev else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Income", inr(income), delta(income, p_income))
c2.metric("Expense", inr(expense), delta(expense, p_expense), delta_color="inverse")
c3.metric("Net cash flow", inr(net), delta(net, p_net))
c4.metric("Savings rate", f"{net / income:.0%}" if income else "—",
          help="Net cash flow ÷ income. Shows — when there is no income in the period.")

exp_rows = db.category_breakdown(user["id"], "expense", start, end)
inc_rows = db.category_breakdown(user["id"], "income", start, end)

# ---------------- highlights (DASH-5)
h1, h2 = st.columns(2)
if exp_rows:
    top = exp_rows[0]
    h1.metric("Highest spending", f"{top['icon']} {top['name']}", f"{inr(float(top['total']))} spent", delta_color="off")
else:
    h1.metric("Highest spending", "—")
if inc_rows:
    top = inc_rows[0]
    h2.metric("Top income source", f"{top['icon']} {top['name']}", f"{inr(float(top['total']))} received", delta_color="off")
else:
    h2.metric("Top income source", "—")


# ---------------- breakdowns (DASH-3)
def slice_colors(rows):
    """Category's own colour if the user picked one, else the next unused palette colour."""
    used = {r["color"] for r in rows if r["color"]}
    free = iter([c for c in PALETTE if c not in used] + PALETTE)
    return {r["id"]: r["color"] or next(free) for r in rows}


def breakdown(kind, rows):
    if not rows:
        st.info(f"No {kind} in this period.")
        return
    for r in rows:
        r["total"] = float(r["total"])
    total = sum(r["total"] for r in rows)
    shown, rest = (rows[: MAX_SLICES - 1], rows[MAX_SLICES - 1:]) if len(rows) > MAX_SLICES else (rows, [])
    colors = slice_colors(shown)

    labels = [f"{r['icon']} {r['name']}" for r in shown]
    values = [r["total"] for r in shown]
    fills = [colors[r["id"]] for r in shown]
    if rest:
        labels.append(f"Other ({len(rest)})")
        values.append(sum(r["total"] for r in rest))
        fills.append(OTHER_COLOR)

    left, right = st.columns([1, 1], vertical_alignment="center")
    with left:
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.62, sort=False, direction="clockwise",
            marker=dict(colors=fills, line=dict(color="rgba(0,0,0,0)", width=2)),
            textinfo="percent", textposition="inside", insidetextorientation="horizontal",
            hovertemplate="%{label}<br>₹%{value:,.0f} · %{percent}<extra></extra>",
        ))
        fig.update_layout(
            showlegend=False, height=280, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text=f"<b>{inr(total)}</b><br><span style='font-size:12px'>total {kind}</span>",
                              showarrow=False, font=dict(size=18))],
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"donut_{kind}")
    with right:
        for r in rows:
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
    breakdown("expense", exp_rows)
with tab_inc:
    breakdown("income", inc_rows)

# ---------------- 12 months: grouped bars + table (DASH-4)
st.subheader("Last 12 months")
months = [month_start(today, i) for i in range(12)]
summary = {r["month"]: r for r in db.monthly_summary(user["id"], months[-1])}
table = []
for m in months:
    r = summary.get(m.strftime("%Y-%m"), {})
    inc, exp = float(r.get("income") or 0), float(r.get("expense") or 0)
    table.append({"Month": m.strftime("%b %Y"), "Income (₹)": inc, "Expense (₹)": exp,
                  "Net (₹)": inc - exp, "Savings rate": (inc - exp) / inc * 100 if inc else None})

chart = list(reversed(table))  # oldest -> newest, left to right
fig = go.Figure([
    go.Bar(name="Income", x=[r["Month"] for r in chart], y=[r["Income (₹)"] for r in chart],
           marker=dict(color=INCOME_COLOR, cornerradius=4),
           hovertemplate="%{x}<br>Income ₹%{y:,.0f}<extra></extra>"),
    go.Bar(name="Expense", x=[r["Month"] for r in chart], y=[r["Expense (₹)"] for r in chart],
           marker=dict(color=EXPENSE_COLOR, cornerradius=4),
           hovertemplate="%{x}<br>Expense ₹%{y:,.0f}<extra></extra>"),
])
fig.update_layout(
    barmode="group", bargap=0.3, bargroupgap=0.08, height=320,
    margin=dict(t=30, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", y=1.12, x=0), hovermode="x unified",
    yaxis=dict(tickprefix="₹", separatethousands=True, gridcolor="rgba(128,128,128,0.2)", zeroline=False),
    xaxis=dict(showgrid=False),
)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="bars_12m")

df = pd.DataFrame(table)
ti, te = df["Income (₹)"].sum(), df["Expense (₹)"].sum()
df.loc[len(df)] = {"Month": "Total (12 months)", "Income (₹)": ti, "Expense (₹)": te,
                   "Net (₹)": ti - te, "Savings rate": (ti - te) / ti * 100 if ti else None}
st.dataframe(
    df, hide_index=True, width="stretch",
    column_config={
        "Income (₹)": st.column_config.NumberColumn(format="localized"),
        "Expense (₹)": st.column_config.NumberColumn(format="localized"),
        "Net (₹)": st.column_config.NumberColumn(format="localized"),
        "Savings rate": st.column_config.NumberColumn(format="%.0f%%"),
    },
)

# ---------------- recent (DASH-5)
st.subheader("Recent transactions")
recent = db.list_transactions(user["id"], dt.date(1900, 1, 1), today, limit=5)
if not recent:
    st.caption("Nothing yet. Add your first transaction on the Transactions page.")
for r in recent:
    amt = float(r["amount"])
    money = f":red[−₹{amt:,.2f}]" if r["kind"] == "expense" else f":green[+₹{amt:,.2f}]"
    st.markdown(f"{r['icon']} **{r['category']}** · {money}")
    st.caption(f"{r['txn_date']} · {r['payment_method']}" + (f" · {r['note']}" if r["note"] else ""))
