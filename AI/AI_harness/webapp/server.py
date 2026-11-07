"""
Backend for the mini agent. Standard library only - no pip install needed.

    python webapp/server.py
    then open http://localhost:8000

API
  GET  /api/health          -> is Ollama running? which models are installed?
  POST /api/chat            -> runs the agent loop, streams events (Server-Sent Events)
  GET  /api/memory?id=...   -> the full message list the model sees (the agent's memory)
  POST /api/reset           -> start a new conversation
  GET  /api/notes           -> list saved reports
  GET  /api/notes/<name>    -> read one report
"""

import json
import threading
import urllib.error
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import agent

HOST, PORT = "127.0.0.1", 8000   # only reachable from this PC
STATIC_DIR = Path(__file__).resolve().parent / "static"
CONTENT_TYPES = {".html": "text/html", ".css": "text/css", ".js": "application/javascript"}

conversations: dict[str, list] = {}   # conversation id -> messages (memory)
lock = threading.Lock()


def get_conversation(cid: str) -> list:
    with lock:
        if cid not in conversations:
            conversations[cid] = agent.new_conversation()
        return conversations[cid]


class Handler(BaseHTTPRequestHandler):
    # ---------- helpers ----------
    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def _static(self, name: str):
        path = STATIC_DIR / Path(name).name          # no ../ tricks
        if not path.is_file():
            return self._json({"error": "not found"}, 404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(path.suffix, "text/plain") + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):               # quieter console
        if "/api/chat" in (args[0] if args else ""):
            super().log_message(fmt, *args)

    # ---------- GET ----------
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            return self._static("index.html")
        if url.path.startswith("/static/"):
            return self._static(url.path[len("/static/"):])
        if url.path == "/api/health":
            try:
                models = agent.list_models()
                return self._json({"ollama": True, "models": models, "default_model": agent.DEFAULT_MODEL})
            except Exception as e:
                return self._json({"ollama": False, "error": str(e), "models": [],
                                   "default_model": agent.DEFAULT_MODEL})
        if url.path == "/api/memory":
            cid = parse_qs(url.query).get("id", [""])[0]
            return self._json(conversations.get(cid, agent.new_conversation()))
        if url.path == "/api/notes":
            notes = sorted(agent.NOTES_DIR.glob("*.md")) if agent.NOTES_DIR.exists() else []
            return self._json([{"name": p.name, "size": p.stat().st_size} for p in notes])
        if url.path.startswith("/api/notes/"):
            try:
                return self._json({"content": agent.read_note(unquote(url.path[len("/api/notes/"):]))})
            except Exception as e:
                return self._json({"error": str(e)}, 404)
        return self._json({"error": "not found"}, 404)

    # ---------- POST ----------
    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/api/reset":
            cid = str(uuid.uuid4())
            get_conversation(cid)
            return self._json({"id": cid})
        if url.path == "/api/chat":
            return self._chat()
        return self._json({"error": "not found"}, 404)

    def _chat(self):
        req = self._read_json()
        cid = req.get("id") or str(uuid.uuid4())
        text = (req.get("message") or "").strip()
        model = req.get("model") or agent.DEFAULT_MODEL
        max_turns = max(1, min(int(req.get("max_turns") or 10), 30))
        if not text:
            return self._json({"error": "empty message"}, 400)

        # Stream events to the browser as they happen (Server-Sent Events).
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def send(event):
            self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()

        try:
            send({"type": "start", "id": cid, "model": model})
            for event in agent.run_agent(get_conversation(cid), text, model, max_turns):
                send(event)
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser closed the tab
        except urllib.error.HTTPError as e:   # Ollama answered with an error
            detail = e.read().decode(errors="replace")[:300]
            send({"type": "error", "message": f"Ollama error {e.code}: {detail}. "
                                              f"Is '{model}' installed? Try: ollama pull {model}"})
        except urllib.error.URLError as e:     # Ollama not reachable at all
            send({"type": "error", "message": f"Can't reach Ollama - is the app running? ({e.reason})"})
        except Exception as e:
            send({"type": "error", "message": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Mini agent running at http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
