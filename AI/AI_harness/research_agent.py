"""
A tiny web research agent - built to show what an "agent harness" is.

The harness is everything in this file that is NOT the model:
  1. TOOLS      - what the model is allowed to ask for
  2. THE LOOP   - send messages -> model asks for tools -> we run them -> repeat
  3. GUARDRAILS - turn limit, output trimming, safe file paths, errors fed back
  4. LOGGING    - print every step so you can watch the agent work

Two kinds of tools are used here:
  - SERVER tool  (web_search): Anthropic runs it; results come back in the reply.
  - CLIENT tools (fetch_url, save_note): YOUR code runs them. This is the harness's job.

Run:  python research_agent.py "What is the tallest building in India?"
"""

import json
import ssl
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import anthropic
import certifi  # installed with the anthropic SDK; gives Python a trusted cert list

MODEL = "claude-opus-5-5"
MAX_TURNS = 15              # guardrail: stop runaway loops
MAX_PAGE_CHARS = 6000       # guardrail: don't flood the context with huge pages
NOTES_DIR = Path("notes")   # the only folder the agent may write to
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

SYSTEM_PROMPT = """You are a careful research assistant.
1. Use web_search to find sources.
2. Use fetch_url to read the 2-4 most relevant pages in full.
3. Call save_note ONCE with a short markdown report:
   answer first, then key facts, then a 'Sources' list of URLs.
Prefer facts you actually read over memory. After saving, reply with a
2-3 sentence summary and stop."""


# --------------------------------------------------------------------------
# 1. CLIENT TOOLS - plain Python functions. The model never runs these;
#    it only *asks*, and the harness decides whether and how to run them.
# --------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Turns HTML into readable text, skipping scripts/styles."""
    def __init__(self):
        super().__init__()
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def fetch_url(url: str) -> str:
    """Download a page and return its visible text (trimmed)."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("Only http(s) URLs are allowed")  # guardrail
    req = urllib.request.Request(url, headers={"User-Agent": "research-agent-demo/1.0"})
    with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    parser = _TextExtractor()
    parser.feed(html)
    text = " ".join(parser.parts)
    if len(text) > MAX_PAGE_CHARS:
        text = text[:MAX_PAGE_CHARS] + f"\n...[trimmed, page had {len(text)} chars]"
    return text


def save_note(filename: str, content: str) -> str:
    """Save a markdown report into ./notes/ (and nowhere else)."""
    NOTES_DIR.mkdir(exist_ok=True)
    safe_name = Path(filename).name  # guardrail: "../../x" becomes "x"
    if not safe_name.endswith(".md"):
        safe_name += ".md"
    path = NOTES_DIR / safe_name
    path.write_text(content, encoding="utf-8")
    return f"Saved {len(content)} chars to {path}"


# The model only sees names, descriptions and schemas - write them carefully!
TOOLS = [
    # SERVER tool: no input_schema, no Python function - Anthropic runs it.
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 5},
    # CLIENT tools: we describe them, and run them below in run_tool().
    {
        "name": "fetch_url",
        "description": "Fetch a web page and return its visible text (trimmed to ~6000 chars).",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Full http(s) URL"}},
            "required": ["url"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "save_note",
        "description": "Save the final markdown research report to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "e.g. tallest-building.md"},
                "content": {"type": "string", "description": "Markdown report"},
            },
            "required": ["filename", "content"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

CLIENT_TOOLS = {"fetch_url": fetch_url, "save_note": save_note}


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Run a client tool safely. Errors go BACK to the model so it can recover."""
    try:
        return CLIENT_TOOLS[name](**args), False
    except Exception as e:  # a failure becomes a message, not a crash
        return f"Error running {name}: {type(e).__name__}: {e}", True


# --------------------------------------------------------------------------
# 2. THE LOOP - this while-loop IS the harness.
# --------------------------------------------------------------------------

def research(question: str) -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    messages = [{"role": "user", "content": question}]

    for turn in range(1, MAX_TURNS + 1):
        print(f"\n===== turn {turn} =====")
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": "medium"},
            # If the model declines, the API retries on a fallback model by itself.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

        # Always keep the model's full reply in the history (append-only).
        messages.append({"role": "assistant", "content": response.content})

        # LOGGING: show what happened in this reply.
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"[model] {block.text.strip()}")
            elif block.type == "server_tool_use":
                print(f"[server tool] {block.name}({json.dumps(block.input)})")
            elif block.type == "web_search_tool_result":
                if isinstance(block.content, list):
                    for r in block.content[:5]:
                        print(f"   - {r.title}  {r.url}")
                else:
                    print(f"   search error: {block.content}")

        # Decide what to do next, based on WHY the model stopped.
        if response.stop_reason == "refusal":
            print("[harness] The model declined this request.")
            return
        if response.stop_reason == "pause_turn":
            continue  # a long server-tool turn paused; send it back to continue
        if response.stop_reason != "tool_use":
            print(f"\n[harness] Done (stop_reason={response.stop_reason}).")
            return

        # The model asked for client tools -> the harness runs them for real.
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"[client tool] {block.name}({json.dumps(block.input)[:120]})")
            output, is_error = run_tool(block.name, block.input)
            print(f"   -> {output[:150].replace(chr(10), ' ')}...")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,   # must match the request's id
                "content": output,
                "is_error": is_error,
            })

        # All results go back together in ONE user message.
        messages.append({"role": "user", "content": tool_results})

    print(f"\n[harness] Stopped: hit MAX_TURNS={MAX_TURNS}.")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or input("Research question: ")
    research(q)
