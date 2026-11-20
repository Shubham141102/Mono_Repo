"""Shared styling and the term-detail renderer used by both pages."""
import html
import os
import re
from datetime import date
from typing import Callable

import streamlit as st

import db
import llm
import taxonomy as tx

ACCENT = "#C96442"
INK, INK_2, MUTED = "#1F1E1D", "#5E5D59", "#73726C"
LINE, SURFACE, SURFACE_2 = "#E8E5DA", "#FFFFFF", "#F0EEE6"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap');
html, body, [class*="css"], .stMarkdown, .stButton button, input, textarea {{ font-family: 'Inter', sans-serif; }}
#MainMenu, footer, [data-testid="stDecoration"] {{ display: none; }}
section[data-testid="stSidebar"] {{ background: {SURFACE_2}; }}
/* Sidebar history list: tight rows like a chat history */
section[data-testid="stSidebar"] .st-key-side-list {{ gap: 0 !important; }}
section[data-testid="stSidebar"] .st-key-side-list [data-testid="stVerticalBlock"] {{ gap: 0 !important; }}
section[data-testid="stSidebar"] .st-key-side-list .stButton {{ width: 100%; }}
section[data-testid="stSidebar"] .st-key-side-list .stTooltipHoverTarget {{ width: 100%; }}
section[data-testid="stSidebar"] .stButton button[kind="tertiary"] {{
  justify-content: flex-start; width: 100%; min-height: 0; padding: .32rem .6rem; border-radius: 8px;
  color: {INK}; font-size: .9rem; line-height: 1.3; }}
section[data-testid="stSidebar"] .stButton button[kind="tertiary"] p {{
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left; }}
section[data-testid="stSidebar"] .stButton button[kind="tertiary"]:hover {{ background: #E6E2D6; }}
.side-cat {{ display: flex; justify-content: space-between; font-size: .7rem; font-weight: 600; color: #8A877F;
            margin: 1rem .6rem .55rem; text-transform: uppercase; letter-spacing: .06em; }}
.side-cat span {{ font-weight: 500; }}
section[data-testid="stSidebar"] .st-key-new-lookup button {{ justify-content: flex-start; border-radius: 10px;
  background: {SURFACE}; border: 1px solid {LINE}; font-weight: 500; }}
section[data-testid="stSidebar"] .st-key-new-lookup button:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}

.serif {{ font-family: 'Source Serif 4', serif; }}
.entry-title {{ font-family: 'Source Serif 4', serif; font-size: 1.6rem; font-weight: 600; margin: 0; line-height: 1.25; }}
.entry-sub {{ color: {MUTED}; font-size: .95rem; margin: .1rem 0 .6rem; }}
.pill {{ display: inline-block; padding: .15rem .6rem; border-radius: 999px; font-size: .76rem;
        margin: 0 .3rem .3rem 0; border: 1px solid #E3DFD3; color: {INK_2}; background: {SURFACE}; }}
.pill.cat {{ background: {ACCENT}; color: #fff; border-color: {ACCENT}; }}
.pill.hot {{ border-color: {ACCENT}; color: {ACCENT}; }}
.def {{ font-size: 1.02rem; line-height: 1.65; margin: .6rem 0 1rem; }}
.box {{ border: 1px solid {LINE}; border-radius: 14px; padding: .8rem 1rem; background: {SURFACE}; height: 100%; }}
.box h4 {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: {MUTED}; margin: 0 0 .4rem; }}
.box ul {{ margin: 0; padding-left: 1.1rem; }} .box li {{ margin: .2rem 0; }}
.verdict {{ border-left: 3px solid {ACCENT}; padding: .2rem 0 .2rem .8rem; margin: .5rem 0; }}
</style>
"""


# Per-area identity for the area cards: (icon, gradient start, gradient end).
# Darker colour first so white titles at the top-left stay readable.
AREA_STYLE = {
    "01 Programming": ("💻", "#3730A3", "#818CF8"),
    "02 DSA": ("🧩", "#6D28D9", "#C084FC"),
    "03 Core CS": ("🖥️", "#1E293B", "#64748B"),
    "04 Databases": ("🗄️", "#115E59", "#2DD4BF"),
    "05 Web Development": ("🌐", "#075985", "#38BDF8"),
    "06 Data Engineering": ("🔀", "#92400E", "#F59E0B"),
    "07 AI / ML": ("🧠", "#9D174D", "#F472B6"),
    "08 AI Engineering": ("🤖", "#9A3412", "#FB923C"),
    "09 Systems": ("⚙️", "#14532D", "#4ADE80"),
    "10 DevOps & Cloud": ("☁️", "#155E75", "#22D3EE"),
    "11 Dev Tools": ("🛠️", "#3F3A36", "#A8A29E"),
    "12 Security": ("🔒", "#7F1D1D", "#F87171"),
}


def apply_css():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(s) -> str:
    return html.escape(str(s or ""))


def box(title: str, items: list[str]) -> str:
    lis = "".join(f"<li>{esc(i)}</li>" for i in items) or "<li>—</li>"
    return f"<div class='box'><h4>{title}</h4><ul>{lis}</ul></div>"


def placement_label(row: dict) -> str:
    if row["category"] == tx.UNSORTED:
        return tx.UNSORTED
    return f"{tx.display_area(row['category'])} › {row['subcategory']}"


def tag_pills(tags: list[str]) -> str:
    return "".join(
        f"<span class='pill hot'>★ interview</span>" if t == "interview" else f"<span class='pill'>#{esc(t)}</span>"
        for t in tags)


def render_entry(row: dict, k: str, on_related: Callable[[str], None] | None = None):
    """Full term detail. `on_related` makes related terms clickable (chat page)."""
    e = row["data"]
    sub = e["full_name"] if e["full_name"] and e["full_name"] != e["name"] else ""
    st.markdown(
        f"<p class='entry-title'>{esc(e['name'])}</p>"
        + (f"<p class='entry-sub'>{esc(sub)}</p>" if sub else "<div style='height:.5rem'></div>")
        + f"<div><span class='pill cat'>{esc(placement_label(row))}</span>{tag_pills(row['tags'])}</div>"
        + f"<p class='def'>{esc(e['definition'])}</p>",
        unsafe_allow_html=True,
    )

    t1, t2, t3, t4, t5 = st.tabs(["Pros & cons", "When to use", "Alternatives", "Example", "🔬 Deep dive"])
    with t1:
        c1, c2 = st.columns(2)
        c1.markdown(box("✅ Advantages", e["advantages"]), unsafe_allow_html=True)
        c2.markdown(box("⚠️ Disadvantages", e["disadvantages"]), unsafe_allow_html=True)
    with t2:
        st.markdown(f"<div class='verdict'><b>Use it when</b> {esc(e['when_to_use'])}</div>"
                    f"<div class='verdict' style='border-color:#8A877F'><b>Avoid it when</b> "
                    f"{esc(e['when_not_to_use'])}</div>", unsafe_allow_html=True)
        st.markdown(box("🌍 Where it's used", e["where_used"]), unsafe_allow_html=True)
    with t3:
        for a in e["alternatives"]:
            st.markdown(f"**{a['name']}** — {a['choose_it_when']}")
    with t4:
        ex = e["example"]
        st.markdown(ex["scenario"])
        if ex["code"].strip():
            st.code(ex["code"], language=(ex["code_language"] or None))
    with t5:
        deep_dive_tab(row, k)

    if e["related_terms"]:
        st.caption("Explore next")
        if on_related:
            key = f"rel-{k}"

            def _picked():
                v = st.session_state.get(key)
                st.session_state[key] = None
                if v:
                    on_related(v)

            st.pills("Explore next", e["related_terms"][:6], key=key,
                     label_visibility="collapsed", on_change=_picked)
        else:
            st.markdown(tag_pills_plain(e["related_terms"]), unsafe_allow_html=True)

    with st.expander("📝 Notes & filing"):
        notes = st.text_area("My notes", value=row["notes"], key=f"notes-{k}",
                             placeholder="Add your own notes, gotchas, links…")
        current = (f"{row['category']}{tx.SEP}{row['subcategory']}"
                   if tx.is_valid(row["category"], row["subcategory"]) else tx.UNSORTED)
        new_place = st.selectbox("Filed under", tx.PLACEMENTS, index=tx.PLACEMENTS.index(current),
                                 key=f"place-{k}", help="Move this term if the AI filed it wrong.")
        c1, c2, _ = st.columns([1, 1, 3])
        if c1.button("Save", key=f"sn-{k}", type="primary"):
            db.update_notes(row["id"], notes)
            if new_place != current:
                db.set_placement(row["id"], *tx.split(new_place))
            st.toast("Saved")
            st.rerun()
        if c2.button("Delete term", key=f"del-{k}"):
            db.delete(row["id"])
            st.toast("Deleted from glossary")
            st.rerun()


def tag_pills_plain(items: list[str]) -> str:
    return "".join(f"<span class='pill'>{esc(i)}</span>" for i in items)


# ---------------- AI provider settings (shared by both pages) ----------------
DEFAULT_BACKGROUND = "Software, data engineering and AI"


def remember_settings(provider: str, ollama_model: str, api_key: str, background: str):
    """Widget values vanish when you switch pages, so keep a copy in plain session state."""
    st.session_state["cfg"] = {"provider": provider, "ollama_model": ollama_model,
                               "api_key": api_key, "background": background}


def saved_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        key = key or st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        pass
    return key


def current_settings() -> dict:
    cfg = st.session_state.get("cfg")
    if cfg:
        return cfg
    models = llm.ollama_models()
    return {"provider": "Ollama (local, free)", "ollama_model": models[0] if models else "",
            "api_key": saved_api_key(), "background": DEFAULT_BACKGROUND}


# ---------------- Deep dive ----------------
ANSWERS_SPLIT = re.compile(r"^#{1,4}\s*(?:\d+\.\s*)?Answers\b.*$", re.MULTILINE | re.IGNORECASE)


def show_deep_dive(text: str):
    """Render the article; keep the quiz answers hidden until asked."""
    parts = ANSWERS_SPLIT.split(text, maxsplit=1)
    st.markdown(parts[0])
    if len(parts) > 1 and parts[1].strip():
        with st.expander("👀 Show answers (try the questions first)"):
            st.markdown(parts[1])


def deep_dive_tab(row: dict, k: str):
    cfg = current_settings()
    use_ollama = cfg["provider"].startswith("Ollama")
    who = f"Ollama · {cfg['ollama_model']}" if use_ollama else "Claude"

    existing = row.get("deep_dive") or ""
    if existing:
        st.caption(f"Generated by {row.get('deep_dive_meta') or 'AI'}")
        show_deep_dive(existing)
        clicked = st.button("↻ Regenerate", key=f"deep-{k}", type="tertiary")
    else:
        st.markdown("A long-form lesson on this term: how it works inside, hands-on code, trade-offs, "
                    "alternatives compared, and a short quiz.")
        if use_ollama:
            st.caption(f"Uses {who}. On CPU this takes **5–15 minutes** and quality is basic; "
                       "Claude is much better for deep dives (Settings on the Ask page).")
        else:
            st.caption("Uses Claude. Takes about a minute, roughly 20–30¢.")
        clicked = st.button("🔬 Generate deep dive", key=f"deep-{k}", type="primary")

    if not clicked:
        return
    if use_ollama and not cfg["ollama_model"]:
        st.error("Ollama isn't running. Start it and refresh.")
        return
    if not use_ollama and not cfg["api_key"]:
        st.error("Add your Anthropic API key in ⚙️ Settings on the Ask page.")
        return

    e = row["data"]
    placement = f"{tx.display_area(row['category'])} > {row['subcategory']}"
    known = [t["name"] for t in db.all_terms() if t["id"] != row["id"]]
    gen = (llm.deep_dive_ollama(cfg["ollama_model"], e["name"], placement, cfg["background"], known)
           if use_ollama else
           llm.deep_dive_claude(cfg["api_key"], e["name"], placement, cfg["background"], known))
    try:
        text = st.write_stream(gen)
    except llm.LookupError_ as err:
        st.error(str(err))
        return
    if isinstance(text, str) and text.strip():
        db.set_deep_dive(row["id"], text, f"{who} · {date.today().isoformat()}")
        row["deep_dive"] = text
        st.success("Deep dive saved to this term.")
