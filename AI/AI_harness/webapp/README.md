# Mini Agent: end-to-end web app

A chat UI on the left, with the **harness loop shown live** on the right.
It runs fully on your PC: Ollama is the brain and Python's standard library is the backend.
There's no API key and nothing to pip install.

## Run it
1. Make sure the Ollama app is running and you have the model:
   ```powershell
   ollama pull qwen2.5:7b
   ```
2. From the `AI_Harness` folder:
   ```powershell
   python webapp/server.py
   ```
3. Open **http://localhost:8000**

Stop the server with `Ctrl+C`.

## How it fits together
```
Browser (static/)                 Backend (server.py)                 Agent (agent.py)
───────────────────               ───────────────────                 ─────────────────
type a question  ──POST /api/chat──►  keeps conversations in memory ──► run_agent() loop:
                                                                          ask model (Ollama)
timeline updates ◄──SSE events────   streams each event as it happens ◄── yield event
                                                                          run tool, yield event
Memory tab       ──GET /api/memory─►  returns the messages list           ...repeat until done
Notes tab        ──GET /api/notes──►  lists notes/*.md
```

| File | Role |
|---|---|
| `agent.py` | **The harness**: tools, `run_tool()` (errors go back to the model), and `run_agent()`, the loop |
| `server.py` | HTTP API, runs the loop and streams events to the browser |
| `static/index.html` | Page layout: chat, plus the Loop / Memory / Notes tabs |
| `static/app.js` | Sends messages, reads the event stream, draws the timeline |
| `static/style.css` | Styling, including dark mode and phone layout |

## The tabs
- **Loop**: every turn live: messages sent → model reply → tool call → tool result → next turn.
- **Memory**: the exact list of messages the model receives every turn. It has no other memory.
- **Notes**: reports saved by the `save_note` tool (files in `AI_Harness/notes/`).

## Things to try
- Set **Max turns** to `1` and ask a research question. You'll see the loop cut off.
- Ask a follow-up in the same chat ("make the report shorter"). The memory carries over.
- Click **New chat** and watch the memory reset to just the system prompt.
- Add your own tool: write a function in `agent.py`, then add it to `TOOLS` and `FUNCTIONS`.
