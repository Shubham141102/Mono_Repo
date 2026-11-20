"""Glossary page: a business-style reference view of everything you've looked up."""
import csv
import io
from datetime import datetime, timedelta

import streamlit as st

import db
import taxonomy as tx
import ui

st.markdown(f"""
<style>
.block-container {{ max-width: 1240px; padding-top: 2rem; }}
.g-head h1 {{ font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 2.1rem; margin: 0; }}
.g-head p {{ color: {ui.MUTED}; margin: .2rem 0 0; }}
.g-head {{ margin-bottom: 1rem; }}


.panel {{ background: {ui.SURFACE}; border: 1px solid {ui.LINE}; border-radius: 14px; padding: 1rem 1.1rem; }}
.panel h3 {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: {ui.MUTED}; margin: 0 0 .7rem; font-weight: 600; }}
section[data-testid="stSidebar"] .panel {{ margin-top: .5rem; }}
.cov-row {{ display: grid; grid-template-columns: 1fr 64px 20px; align-items: center; gap: 8px; padding: 5px 0; }}
.cov-name {{ font-size: .86rem; color: {ui.INK}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.cov-name.zero {{ color: #A8A59C; }}
.cov-track {{ height: 8px; background: {ui.SURFACE_2}; border-radius: 4px; }}
.cov-bar {{ height: 8px; background: {ui.ACCENT}; border-radius: 0 4px 4px 0; }}
.cov-n {{ font-size: .82rem; color: {ui.INK_2}; text-align: right; font-variant-numeric: tabular-nums; }}
.cov-foot {{ font-size: .78rem; color: {ui.MUTED}; margin-top: .6rem; }}

.card .where {{ font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; margin-bottom: .3rem; }}
.card {{ min-height: 205px; }}
.grp {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: {ui.MUTED};
        margin: 1.3rem 0 .5rem; padding-bottom: .3rem; border-bottom: 1px solid {ui.LINE}; }}
.card {{ background: {ui.SURFACE}; border: 1px solid {ui.LINE}; border-radius: 14px; padding: .9rem 1rem .4rem; }}
.card .nm {{ font-family: 'Source Serif 4', serif; font-size: 1.15rem; font-weight: 600; margin: 0; }}
.card .fn {{ font-size: .8rem; color: {ui.MUTED}; margin: 0 0 .4rem; min-height: 1rem; }}
.card .df {{ font-size: .88rem; line-height: 1.5; color: {ui.INK_2}; margin: 0 0 .5rem;
             display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
</style>
""", unsafe_allow_html=True)

terms = db.all_terms()
esc = ui.esc


# ---------------- Detail dialog ----------------
@st.dialog("Term details", width="large")
def open_term(term_id: int):
    row = next((t for t in db.all_terms() if t["id"] == term_id), None)
    if row:
        ui.render_entry(row, f"dlg-{term_id}")


# ---------------- Header ----------------
if not terms:
    st.markdown("<div class='g-head'><h1>Knowledge Glossary</h1>"
                "<p>Your personal reference of technologies and concepts.</p></div>", unsafe_allow_html=True)
    st.info("Your glossary is empty. Go to **💬 Ask** and look something up.")
    st.stop()

week_ago = datetime.now() - timedelta(days=7)
added_week = sum(1 for t in terms if datetime.fromisoformat(t["created_at"]) >= week_ago)
area_counts = {a: sum(1 for t in terms if t["category"] == a) for a in tx.TAXONOMY}
unsorted = sum(1 for t in terms if t["category"] == tx.UNSORTED)

stats = [f"{len(terms)} terms", f"{added_week} added this week"]
if unsorted:
    stats.append(f"<span style='color:{ui.ACCENT}'>{unsorted} unsorted, needs filing</span>")

# ---------------- Header row: title left, toolbar right ----------------
ss = st.session_state
area_opts = ["All areas"] + [a for a in tx.TAXONOMY if area_counts[a]] + ([tx.UNSORTED] if unsorted else [])
if ss.get("area_sel") not in area_opts:
    ss["area_sel"] = "All areas"
topic_opts = ["All topics"] + (sorted({t["subcategory"] for t in terms if t["category"] == ss["area_sel"]})
                               if ss["area_sel"] != "All areas" else [])
if ss.get("topic_sel") not in topic_opts:
    ss["topic_sel"] = "All topics"


def clear_filters():
    ss["area_sel"], ss["topic_sel"], ss["letter"], ss["only_iv"] = "All areas", "All topics", None, False


n_active = sum([ss["area_sel"] != "All areas", ss["topic_sel"] != "All topics",
                bool(ss.get("letter")), bool(ss.get("only_iv"))])

h_left, h_right = st.columns([1.2, 1.8], vertical_alignment="center")
h_left.markdown("<div class='g-head'><h1>Knowledge Glossary</h1>"
                f"<p>{' · '.join(stats)}</p></div>", unsafe_allow_html=True)
with h_right:
    s1, s2, s3 = st.columns([2.3, 1.15, 0.9], vertical_alignment="center")
    query = s1.text_input("Search", placeholder="Search terms, definitions, tags…",
                          label_visibility="collapsed", icon=":material/search:").strip().lower()
    with s2.popover(f"Filters · {n_active}" if n_active else "Filters", icon=":material/tune:", width="stretch"):
        area = st.selectbox("Area", area_opts, key="area_sel",
                            format_func=lambda a: a if a in ("All areas", tx.UNSORTED)
                            else f"{tx.display_area(a)} ({area_counts[a]})")
        topic = st.selectbox("Topic", topic_opts, key="topic_sel", disabled=area == "All areas")
        letters = sorted({t["name"][:1].upper() for t in terms if t["name"]})
        letter = st.pills("Starts with", letters, key="letter")
        only_interview = st.toggle("★ Interview only", key="only_iv")
        st.button("Clear filters", on_click=clear_filters, disabled=not n_active, type="tertiary")
    view = s3.segmented_control(
        "View", ["Cards", "Table"], default="Cards", key="view", label_visibility="collapsed",
        format_func=lambda v: ":material/grid_view:" if v == "Cards" else ":material/table_rows:")
    view = view or "Cards"

# ---------------- Coverage by area (sidebar) ----------------
with st.sidebar:
    top = max(area_counts.values()) or 1
    rows = []
    for area_name, n in area_counts.items():
        name = tx.display_area(area_name)
        bar = f"<div class='cov-bar' style='width:{max(n / top * 100, 4):.0f}%'></div>" if n else ""
        rows.append(f"<div class='cov-row' title='{esc(name)}: {n} term{'s' if n != 1 else ''}'>"
                    f"<span class='cov-name{' zero' if not n else ''}'>{esc(name)}</span>"
                    f"<div class='cov-track'>{bar}</div><span class='cov-n'>{n or '–'}</span></div>")
    gaps = [tx.display_area(a) for a, n in area_counts.items() if not n]
    foot = f"<div class='cov-foot'>Not started: {esc(', '.join(gaps))}</div>" if gaps else ""
    st.markdown(f"<div class='panel'><h3>Coverage by area</h3>{''.join(rows)}{foot}</div>",
                unsafe_allow_html=True)

# ---------------- List ----------------
with st.container():
    def keep(t):
        d = t["data"]
        hay = " ".join([t["name"], d.get("full_name", ""), d["definition"], " ".join(t["tags"])]).lower()
        return ((not query or query in hay)
                and (area == "All areas" or t["category"] == area)
                and (topic == "All topics" or t["subcategory"] == topic)
                and (not letter or t["name"][:1].upper() == letter)
                and (not only_interview or "interview" in t["tags"]))

    shown = sorted([t for t in terms if keep(t)], key=lambda t: (t["category"], t["subcategory"], t["name"].lower()))
    if len(shown) != len(terms):
        st.caption(f"Showing {len(shown)} of {len(terms)} terms")

    if not shown:
        st.info("No terms match these filters.")
    elif view == "Table":
        st.dataframe(
            [{"Term": t["name"], "Area": tx.display_area(t["category"]), "Topic": t["subcategory"],
              "Definition": t["data"]["definition"], "Tags": ", ".join(t["tags"]),
              "Added": t["created_at"][:10]} for t in shown],
            hide_index=True, width="stretch",
            column_config={"Definition": st.column_config.TextColumn(width="large")},
        )
    else:
        for start in range(0, len(shown), 3):
            cols = st.columns(3, gap="medium")
            for col, t in zip(cols, shown[start:start + 3]):
                with col:
                    d = t["data"]
                    _, c1, _ = ui.AREA_STYLE.get(t["category"], ("", ui.MUTED, ""))
                    fn = d["full_name"] if d.get("full_name") and d["full_name"] != t["name"] else ""
                    st.markdown(
                        f"<div class='card' style='border-top:3px solid {c1}'>"
                        f"<div class='where' style='color:{c1}'>{esc(ui.placement_label(t))}</div>"
                        f"<p class='nm'>{esc(t['name'])}</p><p class='fn'>{esc(fn)}</p>"
                        f"<p class='df'>{esc(d['definition'])}</p>{ui.tag_pills(t['tags'][:4])}</div>",
                        unsafe_allow_html=True)
                    if st.button("Open →", key=f"open-{t['id']}", type="tertiary"):
                        open_term(t["id"])

    # ---------------- Export ----------------
    st.divider()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Term", "Full name", "Area", "Topic", "Definition", "Advantages", "Disadvantages",
                "When to use", "When not to use", "Alternatives", "Tags", "Notes", "Added"])
    for t in shown:
        d = t["data"]
        w.writerow([t["name"], d.get("full_name", ""), tx.display_area(t["category"]), t["subcategory"],
                    d["definition"], "; ".join(d["advantages"]), "; ".join(d["disadvantages"]),
                    d["when_to_use"], d["when_not_to_use"], "; ".join(a["name"] for a in d["alternatives"]),
                    ", ".join(t["tags"]), t["notes"], t["created_at"][:10]])

    md = ["# Knowledge Glossary", ""]
    last = None
    for t in shown:
        label = ui.placement_label(t)
        if label != last:
            md += [f"## {label}", ""]
            last = label
        d = t["data"]
        md += [f"### {t['name']}", "", d["definition"], "",
               "**Advantages:** " + "; ".join(d["advantages"]), "",
               "**Disadvantages:** " + "; ".join(d["disadvantages"]), "",
               "**Use it when:** " + d["when_to_use"], "", "**Avoid it when:** " + d["when_not_to_use"], "",
               "**Alternatives:** " + ", ".join(a["name"] for a in d["alternatives"]), ""]

    e1, e2, _ = st.columns([1, 1, 2])
    e1.download_button("⬇ Export to Excel (CSV)", buf.getvalue().encode("utf-8-sig"),
                       file_name="glossary.csv", mime="text/csv", width="stretch")
    e2.download_button("⬇ Export as Markdown", "\n".join(md), file_name="glossary.md",
                       mime="text/markdown", width="stretch")
