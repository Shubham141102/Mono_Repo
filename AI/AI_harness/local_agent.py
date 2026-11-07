"""
Local research agent - same harness idea, but the "brain" is a free model
running on your own PC through Ollama. No API key, no cost.

Run:   python local_agent.py "What is the tallest building in India?"
Try:   python local_agent.py --turns 1 "What is the tallest building in India?"
"""

import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"        # any Ollama model that supports tools
MAX_TURNS = 10              # guardrail: stop runaway loops (change with --turns N)
MAX_PAGE_CHARS = 4000       # guardrail: small models have small context
NOTES_DIR = Path("notes")
TRANSCRIPT = Path("transcript.json")   # EXPERIMENT 5: the agent's full memory

SYSTEM_PROMPT = """You are a research assistant. Use the tools:
- search_wikipedia with 2-4 key words to find relevant articles.
- fetch_url to read the best result. ALWAYS fetch a page before answering a factual
  question - search snippets are too short to answer from.
- add to add two numbers (use it for every addition, one step at a time).
- save_note to save a markdown report, only when the user asks for one.
Answer only from pages you fetched. When you have the final answer, reply in 2 sentences and stop."""


# ---------------- 1. TOOLS (your code does the real work) ----------------

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
    req = urllib.request.Request(url, headers={"User-Agent": "local-agent-demo/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def search_wikipedia(query: str) -> str:
    """Free full-text Wikipedia search (matches words anywhere, any order). No key needed."""
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


def save_note(filename: str, content: str) -> str:
    NOTES_DIR.mkdir(exist_ok=True)
    name = Path(filename).name
    if not name.endswith(".md"):
        name += ".md"
    (NOTES_DIR / name).write_text(content, encoding="utf-8")
    return f"Saved to {NOTES_DIR / name}"


def add(a: str, b: str) -> str:            # EXPERIMENT 3: forces many loops
    result = float(a) + float(b)
    return str(int(result) if result.is_integer() else result)


def _tool(name, description, props):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object",
                       "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
                       "required": list(props)}}}

TOOLS = [
    _tool("search_wikipedia", "Search Wikipedia. Returns article titles and URLs.",
          {"query": "search terms"}),
    _tool("fetch_url", "Read a web page and return its text.", {"url": "full https URL"}),
    _tool("save_note", "Save the final markdown report.",
          {"filename": "e.g. answer.md", "content": "markdown report"}),
    _tool("add", "Add two numbers and return the sum.",
          {"a": "first number", "b": "second number"}),
]
FUNCTIONS = {"search_wikipedia": search_wikipedia, "fetch_url": fetch_url,
             "save_note": save_note, "add": add}


def run_tool(name, args):
    try:
        return FUNCTIONS[name](**args)
    except Exception as e:  # EXPERIMENT 4: errors go back to the model, not a crash
        return f"Error in {name}: {type(e).__name__}: {e}"


def call_model(messages):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": TOOLS,
                       "stream": False}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())["message"]


def save_transcript(messages):              # EXPERIMENT 5
    TRANSCRIPT.write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[harness] full conversation saved to {TRANSCRIPT}")


# ---------------- 2. THE LOOP (this is the harness) ----------------

def research(question, max_turns=MAX_TURNS):
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}]
    tool_calls_made = 0

    for turn in range(1, max_turns + 1):
        print(f"\n===== turn {turn} of max {max_turns} =====")
        # EXPERIMENT 1: the model has no memory - we re-send everything each loop
        print(f"[harness] sending {len(messages)} messages to the model...")

        reply = call_model(messages)
        messages.append(reply)                      # keep history
        if reply.get("content"):
            print(f"[model] {reply['content'].strip()}")

        calls = reply.get("tool_calls") or []
        if not calls:                               # no tool requested -> done
            print(f"\n[harness] Done after {turn} turns and {tool_calls_made} tool calls.")
            save_transcript(messages)
            return
        for call in calls:                          # run each requested tool
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            print(f"[tool] {name}({json.dumps(args)[:120]})")
            result = run_tool(name, args)
            tool_calls_made += 1
            print(f"   -> {result[:150].replace(chr(10), ' ')}")
            messages.append({"role": "tool", "tool_name": name, "content": result})

    # EXPERIMENT 2: what happens when the loop is cut short
    print(f"\n[harness] Stopped: hit the limit of {max_turns} turns before the model finished.")
    save_transcript(messages)


if __name__ == "__main__":
    args = sys.argv[1:]
    turns = MAX_TURNS
    if len(args) >= 2 and args[0] == "--turns":     # EXPERIMENT 2: python local_agent.py --turns 1 "..."
        turns, args = int(args[1]), args[2:]
    try:
        research(" ".join(args) or input("Question: "), turns)
    except urllib.error.URLError as e:
        print(f"Can't reach Ollama at {OLLAMA_URL} - is the Ollama app running? ({e})")