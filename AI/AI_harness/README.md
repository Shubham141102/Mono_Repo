# AI Harness: a mini agent you can watch loop

A small, readable **agent harness** built from scratch in Python, with a web UI
that shows every turn of the agent loop live.

It answers questions by searching Wikipedia, reading pages and saving reports.
The default version runs **free on your own PC** with [Ollama](https://ollama.com),
so there's no API key and nothing to pip install.

## What is an agent harness?

A language model on its own can only turn text into text. It can't search, open
pages or save files. The **harness** is the code around the model that lets it act:

```
        ┌───────────────────────────────────────────────────────────────┐
        ▼                                                               │
  send messages ──► model replies ──► asked for a tool? ──yes──► run the tool,
                                            │                    add result to messages
                                            no
                                            ▼
                                     final answer, stop
```

In short: **agent = model + harness**. This repo is that loop, plus:

| Part | What it does here |
|---|---|
| **Tools** | `search_wikipedia`, `fetch_url`, `add`, `save_note`, `list_notes`, `read_note` |
| **The loop** | `run_agent()` in [`webapp/agent.py`](webapp/agent.py) |
| **Memory** | the `messages` list, re-sent to the model every turn |
| **Guardrails** | turn limit, trimmed page text, safe file names, errors returned to the model instead of crashing |

## Three versions

| Version | Model | Needs | Best for |
|---|---|---|---|
| [`webapp/`](webapp/) | Ollama (local, free) | Ollama | **Start here.** Chat UI with a live view of the loop |
| [`local_agent.py`](local_agent.py) | Ollama (local, free) | Ollama | One-file command-line version |
| [`research_agent.py`](research_agent.py) | Claude (API) | Anthropic API key (paid) | Stronger model; also shows a server-side tool |

## Quick start (web app)

1. Install [Ollama](https://ollama.com/download), then download a model that supports tools:
   ```bash
   ollama pull qwen2.5:7b
   ```
2. Clone this repo and start the server (Python 3.10+):
   ```bash
   python webapp/server.py
   ```
3. Open **http://localhost:8000** and try *"What is an agent harness?"*

The right-hand panel has three tabs:
- **Loop**: each turn as it happens: model reply → tool call → tool result → next turn.
- **Memory**: the exact messages the model receives. It has no other memory.
- **Notes**: reports the agent saved.

More detail is in [`webapp/README.md`](webapp/README.md).

## Command-line version

```bash
python local_agent.py "What is the tallest building in India?"
python local_agent.py --turns 1 "What is the tallest building in India?"   # see the loop cut short
```
After each run, `transcript.json` holds the full conversation the model saw.

## Claude API version

```bash
pip install -r requirements.txt
# PowerShell:  $env:ANTHROPIC_API_KEY = "your-key"
# bash:        export ANTHROPIC_API_KEY="your-key"
python research_agent.py "What is the tallest building in India?"
```

## Project structure

```
AI_Harness/
├── webapp/
│   ├── agent.py          # the harness: tools + the loop (yields events)
│   ├── server.py         # HTTP API, streams loop events to the browser
│   └── static/           # index.html, app.js, style.css
├── local_agent.py        # command-line harness for Ollama
├── research_agent.py     # command-line harness for the Claude API
└── requirements.txt      # only needed for research_agent.py
```

## Things to try

- Set **Max turns** to 1 and watch the agent stop before it can answer.
- Ask *"Fetch the page at not-a-real-url"* to see a tool error go back to the model, which then recovers.
- Add your own tool: write a function in `webapp/agent.py` and add it to `TOOLS` and `FUNCTIONS`.
- Swap the model in the top bar (any Ollama model with tool support).

## License

[MIT](LICENSE)
