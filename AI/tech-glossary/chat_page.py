"""Ask page: chat-style lookup. Type a term, get a structured explanation, saved to the glossary."""
import os

import streamlit as st

import db
import llm
import taxonomy as tx
import ui

st.markdown("""
<style>
.block-container { max-width: 800px; padding-top: 2.5rem; padding-bottom: 7rem; }
.hero { text-align: center; margin: 9vh 0 2rem; }
.hero h1 { font-family: 'Source Serif 4', serif; font-weight: 500; font-size: 2.4rem; margin: 0 0 .4rem; }
.hero p { color: #73726C; margin: 0; }
[data-testid="stChatMessage"] { background: transparent; padding: .25rem 0; gap: .9rem; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .stMarkdown p {
  background: #F0EEE6; display: inline-block; padding: .55rem .95rem; border-radius: 18px; margin: 0; }
</style>
""", unsafe_allow_html=True)

# ---------------- State ----------------
ss = st.session_state
ss.setdefault("messages", [])   # [{"role": "user"/"assistant", ...}]
ss.setdefault("queue", None)    # (term, sense) waiting to be looked up


def ask(term: str, sense: str | None = None, shown_text: str | None = None):
    ss.messages.append({"role": "user", "text": shown_text or term})
    ss.queue = (term, sense)


def show_saved(row: dict):
    ss.messages.append({"role": "user", "text": row["name"]})
    ss.messages.append({"role": "assistant", "kind": "entry", "id": row["id"], "cached": True})


def pick_suggestion():
    v = ss.get("suggest")
    ss["suggest"] = None
    if v:
        ask(v)


# ---------------- Sidebar ----------------
with st.sidebar:
    if st.button("New lookup", icon=":material/edit_square:", width="stretch", key="new-lookup"):
        ss.messages, ss.queue = [], None
        st.rerun()

    query = st.text_input("Search glossary", placeholder="Search glossary", label_visibility="collapsed",
                          icon=":material/search:")
    terms = db.all_terms()
    q = query.strip().lower()
    shown = [t for t in terms if not q or q in t["name"].lower() or q in t["category"].lower()
             or q in t["subcategory"].lower() or any(q in tag.lower() for tag in t["tags"])]

    # Group by area only; the topic shows as a tooltip on hover.
    groups: dict[str, list[dict]] = {}
    for t in sorted(shown, key=lambda t: (t["category"], t["name"].lower())):
        groups.setdefault(t["category"], []).append(t)

    with st.container(key="side-list"):
        for area, items in groups.items():
            name = tx.display_area(area)
            st.markdown(f"<div class='side-cat'>{ui.esc(name)}<span>{len(items)}</span></div>",
                        unsafe_allow_html=True)
            for t in items:
                if st.button(t["name"], key=f"side-{t['id']}", type="tertiary", help=t["subcategory"]):
                    show_saved(t)
                    st.rerun()
    if not terms:
        st.caption("Terms you look up will appear here.")
    elif not shown:
        st.caption("No matches.")

    st.divider()
    with st.expander("⚙️  Settings"):
        provider = st.radio("AI provider", ["Ollama (local, free)", "Claude API"], index=0, key="provider")
        use_ollama = provider.startswith("Ollama")
        api_key, ollama_model = "", ""
        if use_ollama:
            models = llm.ollama_models()
            if models:
                ollama_model = st.selectbox("Local model", models, key="ollama_model")
                st.caption("~1 min per new term on CPU. Saved terms load instantly.")
            else:
                st.error("Ollama isn't running. Start it, then refresh.")
        else:
            env_key = os.environ.get("ANTHROPIC_API_KEY", "")
            try:
                env_key = env_key or st.secrets.get("ANTHROPIC_API_KEY", "")
            except Exception:
                pass
            api_key = st.text_input("Anthropic API key", type="password",
                                    placeholder="Using saved key" if env_key else "sk-ant-...") or env_key
            st.caption(f"Model: `{llm.MODEL}`")
        background = st.text_input("Your background", value=ui.DEFAULT_BACKGROUND,
                                   key="background", help="Used to pick the right meaning of ambiguous terms.")
    ui.remember_settings(provider, ollama_model, api_key, background)


# ---------------- Messages ----------------
def context_box(i: int, term: str, placeholder: str):
    """Let the user say what they mean; the text is passed to the model as the chosen meaning."""
    with st.form(f"ctx-{i}", border=False):
        c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
        hint = c1.text_input("Context", placeholder=placeholder, label_visibility="collapsed")
        if c2.form_submit_button("Explain", width="stretch") and hint.strip():
            ask(term, hint.strip(), shown_text=f"{term}: {hint.strip()}")
            st.rerun()


def render_message(i: int, m: dict):
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(ui.esc(m["text"]))
        return
    with st.chat_message("assistant", avatar="📘"):
        if m["kind"] == "error":
            st.error(m["text"])
        elif m["kind"] == "ambiguous":
            st.markdown(f"**{ui.esc(m['term'])}** can mean a few different things. Which one?")
            for j, s in enumerate(m["senses"]):
                if st.button(f"{s['label']}  ·  {s['domain']}", key=f"sense-{i}-{j}", help=s["one_liner"]):
                    ask(m["term"], s["label"], shown_text=s["label"])
                    st.rerun()
            context_box(i, m["term"], "None of these? Describe what you mean")
        elif m["kind"] == "unknown":
            st.markdown(f"I don't recognise **{ui.esc(m['term'])}** as a public tech term. "
                        "If it's from your company or a specific document, the AI can't know it on its own.")
            context_box(i, m["term"], "Add context, e.g. “OKF in our context-layer architecture docs = …”")
        elif m["kind"] == "entry":
            row = next((t for t in terms if t["id"] == m["id"]), None)
            if row:
                ui.render_entry(row, f"{i}", on_related=ask)
                st.caption("📚 From your glossary" if m.get("cached") else
                           f"✓ Saved to your glossary under {ui.placement_label(row)}")
            else:
                st.caption("_This term was deleted from your glossary._")


def run_lookup(term: str, sense: str | None) -> dict:
    key = db.make_key(term, sense)
    cached = db.get_by_key(key)
    if cached:
        return {"role": "assistant", "kind": "entry", "id": cached["id"], "cached": True}
    if use_ollama and not ollama_model:
        return {"role": "assistant", "kind": "error", "text": "Ollama isn't available. Start it and refresh the page."}
    if not use_ollama and not api_key:
        return {"role": "assistant", "kind": "error", "text": "Add your Anthropic API key in ⚙️ Settings first."}
    try:
        if use_ollama:
            entry = llm.lookup_ollama(ollama_model, term, sense, background)
        else:
            entry = llm.lookup(api_key, term, sense, background)
    except llm.LookupError_ as err:
        return {"role": "assistant", "kind": "error", "text": str(err)}

    if entry.status == "ambiguous":
        return {"role": "assistant", "kind": "ambiguous", "term": term,
                "senses": [s.model_dump() for s in entry.senses]}
    if entry.status == "unknown":
        return {"role": "assistant", "kind": "unknown", "term": term}
    db.save(key, entry.to_record())
    return {"role": "assistant", "kind": "entry", "id": db.get_by_key(key)["id"], "cached": False}


# ---------------- Page ----------------
if not ss.messages:
    st.markdown("<div class='hero'><h1>What do you want to learn?</h1>"
                "<p>Type any technology, tool or concept. Every answer is filed into your learning map.</p></div>",
                unsafe_allow_html=True)
    st.pills("Try one", ["Kafka", "RAG", "Kubernetes", "STL", "Delta Lake", "Dynamic Programming"],
             key="suggest", label_visibility="collapsed", on_change=pick_suggestion)

for i, m in enumerate(ss.messages):
    render_message(i, m)

if ss.queue:
    term, sense = ss.queue
    with st.chat_message("assistant", avatar="📘"):
        with st.spinner(f"Thinking about {term}…"):
            reply = run_lookup(term, sense)
    ss.messages.append(reply)
    ss.queue = None
    st.rerun()

prompt = st.chat_input("Ask about any technology, e.g. Kafka, STL, LoRA…")
if prompt and prompt.strip():
    ask(llm.clean_term(prompt), shown_text=prompt.strip())
    st.rerun()
