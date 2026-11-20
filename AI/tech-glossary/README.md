# Tech Glossary

A personal tech knowledge base with a chat interface. Type any technology or concept and get a structured explanation, automatically filed into your own learning map.

## Features

- **Ask (chat):** type a term such as `Kafka`, `STL` or `what is RAG?`. You get a definition, pros and cons, when to use it and when not to, alternatives, a code example, and related terms you can click.
- **Ambiguity handling:** terms with several meanings show "Did you mean…" options. For unknown or company-specific terms, you can add context.
- **Fixed taxonomy:** every term is filed under *Area › Topic* from [`taxonomy.py`](taxonomy.py) (12 areas). Edit that file to change the hierarchy.
- **Glossary page:** a reference view with search, filters (area, topic, A–Z, interview), card and table views, coverage by area, and CSV and Markdown export.
- **Deep dive:** a long-form lesson per term covering internals, hands-on code, trade-offs, a comparison table and a quiz with hidden answers. It is generated on demand and saved.
- **Notes and re-filing:** add your own notes to any term, or move it to another topic.

## AI providers

| Provider | Cost | Speed | Quality |
|---|---|---|---|
| Ollama (local, default) | Free | ~1 min per term, ~3–4 min per deep dive on CPU | Fine for lookups, basic deep dives |
| Claude API (`claude-opus-5-5`) | ~2–3¢ per lookup, ~20–30¢ per deep dive | Fast | Much better categorisation and deep dives |

Switch providers in **⚙️ Settings** in the Ask page sidebar.

## Run it

```bash
pip install -r requirements.txt

# Ollama (default): install from https://ollama.com, then
ollama pull qwen2.5:7b

streamlit run app.py
```

To use Claude, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your key, or paste the key in Settings.

Your glossary is stored locally in `glossary.db` (SQLite), which git ignores.

## Files

| File | Purpose |
|---|---|
| `app.py` | Entry point and page navigation |
| `chat_page.py` | Ask page: chat-style lookups |
| `glossary_page.py` | Glossary page: reference view, filters, export |
| `ui.py` | Shared styling, term detail view, deep-dive tab |
| `llm.py` | Claude and Ollama calls, output schema, prompts |
| `db.py` | SQLite storage |
| `taxonomy.py` | The fixed Area › Topic learning map |
