"""
The agent harness: tools + the loop.

This is the same idea as local_agent.py, but instead of print()-ing each step,
the loop YIELDS events. The web server streams those events to the browser,
so you can watch every turn of the loop live.
"""

import html
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

OLLAMA = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"
MAX_PAGE_CHARS = 4000
NOTES_DIR = Path(__file__).resolve().parent.parent / "notes"

SYSTEM_PROMPT = """You are a helpful research assistant with tools:
- search_wikipedia: find relevant Wikipedia articles.
- fetch_url: read a web page (use it on 1-2 of the best search results).
- add: add two numbers. Use it for every addition, one step at a time.
- save_note: save a markdown report. Only use it when the user asks you to save or write a report.
- list_notes / read_note: see reports you saved earlier.
Rules for questions about facts:
1. Call search_wikipedia with 2-4 key words.
2. ALWAYS call fetch_url on the best result before answering. Search snippets are too short to answer from.
3. Answer only from what the fetched page says, and name the page you used.
Reply briefly and stop when you have the answer."""


# ============================== TOOLS ==============================

class _TextExtractor(HTMLParser):
    """HTML -> plain text, skipping code, menus, headers and footers."""
    SKIP = ("script", "style", "noscript", "nav", "header", "footer", "aside", "form", "sup")

    def __init__(self):
        super().__init__()
        self.parts, self._skip = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "mini-agent-demo/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def search_wikipedia(query: str) -> str:
    """Full-text Wikipedia search: matches words anywhere in articles, any order."""
    url = ("https://en.wikipedia.org/w/api.php?action=query&list=search&srlimit=5&format=json&srsearch="
           + urllib.parse.quote(query))
    hits = json.loads(_get(url))["query"]["search"]
    if not hits:
        return "No results. Try fewer or different words."
    lines = []
    for h in hits:
        snippet = re.sub(r"<[^>]+>", "", h["snippet"])  # strip <span> highlight tags
        link = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(h["title"].replace(" ", "_"))
        lines.append(f"- {h['title']}: {link}\n  {html.unescape(snippet)}")
    return "\n".join(lines)


def fetch_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Only http(s) URLs are allowed")
    parser = _TextExtractor()
    parser.feed(_get(url))
    text = " ".join(parser.parts)
    return text[:MAX_PAGE_CHARS] + ("\n...[trimmed]" if len(text) > MAX_PAGE_CHARS else "")


def add(a: str, b: str) -> str:
    result = float(a) + float(b)
    return str(int(result) if result.is_integer() else result)


def _safe_note_path(filename: str) -> Path:
    name = Path(filename).name  # guardrail: "../../x" -> "x"
    if not name:
        raise ValueError("Empty filename")
    if not name.endswith(".md"):
        name += ".md"
    return NOTES_DIR / name


def save_note(filename: str, content: str) -> str:
    NOTES_DIR.mkdir(exist_ok=True)
    path = _safe_note_path(filename)
    path.write_text(content, encoding="utf-8")
    return f"Saved {len(content)} chars to notes/{path.name}"


def list_notes() -> str:
    names = sorted(p.name for p in NOTES_DIR.glob("*.md")) if NOTES_DIR.exists() else []
    return "\n".join(names) or "No notes saved yet."


def read_note(filename: str) -> str:
    return _safe_note_path(filename).read_text(encoding="utf-8")


def _tool(name, description, props):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object",
                       "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
                       "required": list(props)}}}


TOOLS = [
    _tool("search_wikipedia", "Search Wikipedia articles. Returns titles, URLs and a short snippet of each.",
          {"query": "2-4 key words, e.g. 'agent harness'"}),
    _tool("fetch_url", "Read a web page and return its text.", {"url": "full https URL"}),
    _tool("add", "Add two numbers and return the sum.", {"a": "first number", "b": "second number"}),
    _tool("save_note", "Save a markdown report to a file.",
          {"filename": "e.g. answer.md", "content": "markdown report"}),
    _tool("list_notes", "List saved report files.", {}),
    _tool("read_note", "Read a saved report.", {"filename": "file name from list_notes"}),
]
FUNCTIONS = {"search_wikipedia": search_wikipedia, "fetch_url": fetch_url, "add": add,
             "save_note": save_note, "list_notes": list_notes, "read_note": read_note}


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Run a tool. Errors are returned to the model (so it can recover), never raised."""
    if name not in FUNCTIONS:
        return f"Error: unknown tool '{name}'. Available: {', '.join(FUNCTIONS)}", True
    try:
        return FUNCTIONS[name](**args), False
    except Exception as e:
        return f"Error in {name}: {type(e).__name__}: {e}", True


# ============================== MODEL ==============================

def call_model(messages: list, model: str) -> dict:
    body = json.dumps({"model": model, "messages": messages, "tools": TOOLS, "stream": False}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())["message"]


def list_models() -> list[str]:
    with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as resp:
        return [m["name"] for m in json.loads(resp.read()).get("models", [])]


# ============================== THE LOOP ==============================

def new_conversation() -> list:
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def run_agent(messages: list, user_text: str, model: str, max_turns: int):
    """
    THE HARNESS LOOP. Appends to `messages` (the agent's memory) and yields
    an event dict for every step, so the UI can show the loop live.
    """
    messages.append({"role": "user", "content": user_text})
    tool_calls_made = 0

    for turn in range(1, max_turns + 1):
        yield {"type": "turn_start", "turn": turn, "max_turns": max_turns,
               "messages_sent": len(messages)}

        t0 = time.time()
        reply = call_model(messages, model)                    # 1. ask the model
        messages.append(reply)                                 # 2. remember its reply
        yield {"type": "model_reply", "turn": turn, "ms": int((time.time() - t0) * 1000),
               "text": (reply.get("content") or "").strip(),
               "tool_calls": len(reply.get("tool_calls") or [])}

        calls = reply.get("tool_calls") or []
        if not calls:                                          # 3. no tools? -> done
            yield {"type": "done", "turns": turn, "tool_calls": tool_calls_made,
                   "answer": (reply.get("content") or "").strip()}
            return

        for call in calls:                                     # 4. run each tool
            name = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            yield {"type": "tool_call", "turn": turn, "name": name, "args": args}
            t0 = time.time()
            result, is_error = run_tool(name, args)
            tool_calls_made += 1
            yield {"type": "tool_result", "turn": turn, "name": name, "result": result,
                   "is_error": is_error, "ms": int((time.time() - t0) * 1000)}
            messages.append({"role": "tool", "tool_name": name, "content": result})  # 5. feed back
        # ...and loop again

    yield {"type": "stopped", "turns": max_turns, "tool_calls": tool_calls_made}
