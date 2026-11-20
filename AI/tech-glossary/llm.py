"""Calls Claude or a local Ollama model and returns a structured glossary entry."""
import json
import re
import urllib.error
import urllib.request
from typing import Literal

import anthropic
from pydantic import BaseModel

import taxonomy as tx

MODEL = "claude-opus-5-5"
OLLAMA_URL = "http://localhost:11434"

# The model can only answer with one of these strings (enforced by the output schema).
Placement = Literal.__getitem__(tuple(tx.PLACEMENTS))


class Sense(BaseModel):
    label: str        # e.g. "STL (C++ Standard Template Library)"
    domain: str       # e.g. "Programming > C++"
    one_liner: str


class Alternative(BaseModel):
    name: str
    choose_it_when: str


class Example(BaseModel):
    scenario: str
    code: str         # empty string if a code snippet doesn't make sense
    code_language: str


class Entry(BaseModel):
    status: Literal["ok", "ambiguous", "unknown"]
    senses: list[Sense]               # filled only when status == "ambiguous"
    name: str
    full_name: str
    placement: Placement              # "Area › Topic" from the fixed taxonomy
    interview_relevant: bool
    tags: list[str]
    definition: str
    where_used: list[str]
    advantages: list[str]
    disadvantages: list[str]
    when_to_use: str
    when_not_to_use: str
    alternatives: list[Alternative]
    example: Example
    related_terms: list[str]

    def to_record(self) -> dict:
        """Dict for storage, with placement split into category / subcategory."""
        d = self.model_dump()
        d["category"], d["subcategory"] = tx.split(self.placement)
        tags = [t for t in d["tags"] if t.lower() != "interview"]
        if self.interview_relevant:
            tags.append("interview")
        d["tags"] = tags
        return d


class Filing(BaseModel):
    placement: Placement


TREE_TEXT = "\n".join(f"{a}: {', '.join(ts)}" for a, ts in tx.TAXONOMY.items())

PLACEMENT_RULES = f"""Placement: pick exactly ONE "Area › Topic" from this fixed learning taxonomy
(the schema lists the allowed strings):
{TREE_TEXT}
Decide what the term actually IS, then pick the topic that describes it. Tools and products are
filed under the topic they belong to (Docker -> "10 DevOps & Cloud › Containers",
LangChain -> "08 AI Engineering › Frameworks", Kafka -> "06 Data Engineering › Streaming",
MySQL -> "04 Databases › SQL", STL -> "01 Programming › C++",
RAG evaluation metrics -> "08 AI Engineering › Evaluation",
Reranking -> "08 AI Engineering › RAG", gRPC -> "05 Web Development › APIs",
Dynamic Programming -> "02 DSA › Dynamic Programming", Binary Search -> "02 DSA › Arrays & Strings").
Prefer the most specific matching topic: an algorithm/data-structure topic goes to DSA, not Programming.
Use "{tx.UNSORTED}" only if nothing fits at all."""

SYSTEM = f"""You are a precise technical glossary. The user types a word, acronym or technology;
you return a structured entry for it.

Rules:
- Ambiguity: if the term has more than one common TECHNICAL meaning the user could plausibly mean
  (e.g. "STL" = C++ Standard Template Library / STL 3D file format / seasonal decomposition),
  and no chosen meaning was given, set status="ambiguous", list 2-5 senses (most likely first,
  weighted toward the user's background), and leave every other field empty ("" or [];
  placement="{tx.UNSORTED}", interview_relevant=false).
  Ignore non-technical meanings (Kafka the author, Python the snake). If only one technical
  meaning is common (Kafka -> Apache Kafka, Docker, React), it is NOT ambiguous.
- If you don't recognise the term at all, set status="unknown" and leave other fields empty.
  Never invent a technology. Company-internal or document-specific terms are "unknown" unless
  the user explains them.
- If the "Chosen meaning" is a description written by the user, treat it as the source of truth:
  answer with status="ok", build the entry around that description plus general knowledge of
  the concepts it mentions, and do not invent specific facts the description doesn't imply.
- Otherwise set status="ok", senses=[] and fill everything.
- {PLACEMENT_RULES}
- interview_relevant: true if this commonly comes up in software / data / ML interviews.
- Tags: 3-6 short lowercase tags for cross-cutting topics.
- Be concrete, not generic. Bad: "scalable, flexible". Good: "handles millions of events/sec
  by partitioning topics across brokers".
- where_used: real use cases or kinds of companies/systems, 3-5 items.
- advantages / disadvantages: 3-5 each, specific.
- when_to_use / when_not_to_use: one or two sentences of decision guidance.
- alternatives: 2-5, each with when you'd pick it instead.
- example: a short real-world scenario, plus a minimal code/config snippet if it helps
  (else code="" and code_language="").
- related_terms: 3-6 terms worth looking up next.
- If your knowledge may be out of date for a fast-moving tool, say so in the definition."""


class LookupError_(Exception):
    pass


def _user_msg(term: str, chosen_sense: str | None, background: str) -> str:
    return (
        f"Term: {term}\n"
        f"Chosen meaning: {chosen_sense or '(none chosen yet)'}\n"
        f"User background: {background or '(not given)'}"
    )


# ---------------- Claude API ----------------
def _claude_parse(api_key: str, system: str, user_msg: str, schema, effort: str):
    client = anthropic.Anthropic(api_key=api_key or None)
    try:
        response = client.beta.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            output_format=schema,
            output_config={"effort": effort},
            # If Claude's safety filter declines, retry automatically on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        raise LookupError_("Invalid API key. Check the key in Settings.")
    except anthropic.RateLimitError:
        raise LookupError_("Rate limited by the API. Wait a few seconds and try again.")
    except anthropic.APIStatusError as e:
        raise LookupError_(f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        raise LookupError_("Couldn't reach the Claude API. Check your internet connection.")

    if response.stop_reason == "refusal":
        raise LookupError_("Claude declined to answer this one.")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise LookupError_("The answer was cut off or malformed. Try again.")
    return response.parsed_output


def lookup(api_key: str, term: str, chosen_sense: str | None, background: str) -> Entry:
    entry = _claude_parse(api_key, SYSTEM, _user_msg(term, chosen_sense, background), Entry, "medium")
    return _normalize(entry, chosen_sense)


# ---------------- Ollama (local, free) ----------------
def _ollama(path: str, payload: dict | None = None, timeout: float = 600) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{OLLAMA_URL}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ollama_models() -> list[str]:
    """Installed chat models (embedding models filtered out)."""
    try:
        names = [m["name"] for m in _ollama("/api/tags", timeout=3).get("models", [])]
        return [n for n in names if "embed" not in n]
    except (urllib.error.URLError, OSError):
        return []


def _ollama_parse(model: str, system: str, user_msg: str, schema):
    try:
        resp = _ollama("/api/chat", {
            "model": model,
            "stream": False,
            "format": schema.model_json_schema(),   # forces output to match the schema
            "options": {"temperature": 0.2, "num_ctx": 8192},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg + "\n\nReply with the JSON object only."},
            ],
        })
    except urllib.error.HTTPError as e:
        raise LookupError_(f"Ollama error {e.code}: {e.read()[:300].decode(errors='replace')}")
    except TimeoutError:
        raise LookupError_("Ollama took too long (over 10 minutes). Try again or use a smaller model.")
    except (urllib.error.URLError, OSError):
        raise LookupError_("Ollama isn't running. Start it (open the Ollama app or run `ollama serve`).")
    try:
        return schema.model_validate_json(resp.get("message", {}).get("content", ""))
    except ValueError:
        raise LookupError_("The local model returned malformed output. Try again.")


def lookup_ollama(model: str, term: str, chosen_sense: str | None, background: str) -> Entry:
    entry = _normalize(_ollama_parse(model, SYSTEM, _user_msg(term, chosen_sense, background), Entry),
                       chosen_sense)
    if entry.status == "ok":
        # Small models file poorly while writing a long answer; a short dedicated call is far more accurate.
        msg = f"Term: {entry.name}\nDefinition: {entry.definition}"
        entry.placement = _ollama_parse(model, FILE_SYSTEM, msg, Filing).placement
    return entry


def _normalize(e: Entry, chosen_sense: str | None) -> Entry:
    """Small local models sometimes mislabel the status; fix the obvious cases."""
    has_answer = bool(e.definition.strip())
    # A "definition" that is really a refusal, or an entry with every section empty, is not an answer.
    if has_answer and (NON_ANSWER.search(e.definition)
                       or not (e.advantages or e.where_used or e.alternatives)):
        has_answer = False
        if e.status == "ok":
            e.status = "unknown"
    if e.status == "ambiguous" and (chosen_sense or len(e.senses) < 2) and has_answer:
        e.status = "ok"
    if e.status == "ok" and not has_answer:
        e.status = "ambiguous" if len(e.senses) >= 2 else "unknown"
    if e.status == "ambiguous" and len(e.senses) < 2 and not has_answer:
        e.status = "unknown"   # "ambiguous" with nothing to choose from is really "don't know"
    return e


NON_ANSWER = re.compile(
    r"not (a )?(commonly |widely )?(recogni[sz]ed|known)|provide more context|please clarify|"
    r"i('m| am) not (sure|familiar)|no (widely )?known (term|technology)|could not find|unclear what",
    re.IGNORECASE)

QUESTION_PREFIX = re.compile(
    r"^\s*(what\s+(is|are|'s)|whats|explain|define|tell\s+me\s+about|meaning\s+of|describe)\s+(an?\s+|the\s+)?",
    re.IGNORECASE)


def clean_term(text: str) -> str:
    """'what is OKF?' -> 'OKF'. Keeps the rest of the phrase as typed."""
    t = QUESTION_PREFIX.sub("", text.strip()).strip().rstrip("?.! ").strip()
    return t or text.strip()


# ---------------- Deep dive (long-form, streamed) ----------------
DEEP_SYSTEM = "You are a senior engineer and patient technical mentor. Write in Markdown."

DEEP_PROMPT = """Teach me {term} ({placement}) in depth.
My background: {background}. Terms I already know: {known}. Connect to them where useful.

Write these sections as "## " headings. SKIP any section that doesn't apply to this kind of term
(concepts like algorithms have no deployment). Use plain English first, then the technical terms.

## 1. Mental model
The problem it solves, an analogy, key terminology (max 6 terms).
## 2. How it works inside
Components, step-by-step flow, and one ASCII diagram in a ``` code block.
## 3. Where it fits
Its place in a real end-to-end system and what it integrates with.
## 4. Hands-on
One realistic example, code under 40 lines with comments, expected output, 3 common mistakes.
## 5. Trade-offs
Strengths, limitations, hidden complexity, when NOT to use it.
## 6. Production notes
Scaling, security, monitoring, failure modes (only if applicable).
## 7. Alternatives
The 3 closest, as a Markdown comparison table (performance, scalability, ease, ecosystem,
cost, best fit), then a short "choose X when..." guide.
## 8. Check yourself
3 conceptual + 2 scenario questions, numbered. Do NOT answer them here.
## Answers
Answers to the section 8 questions, numbered to match.

Accuracy: say when something is version-specific or you're unsure. Name a real company only if
you're confident its usage is publicly documented; otherwise describe the type of company.
Target length: about 2,500 words. Start directly with section 1, no preamble."""


def _deep_msg(term: str, placement: str, background: str, known: list[str]) -> str:
    return DEEP_PROMPT.format(term=term, placement=placement, background=background or "not given",
                              known=", ".join(known[:40]) or "none yet")


def deep_dive_claude(api_key: str, term: str, placement: str, background: str, known: list[str]):
    """Yields text chunks as Claude writes them."""
    client = anthropic.Anthropic(api_key=api_key or None)
    try:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=32000,
            system=DEEP_SYSTEM,
            messages=[{"role": "user", "content": _deep_msg(term, placement, background, known)}],
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            yield from stream.text_stream
            final = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise LookupError_("Invalid API key. Check the key in Settings.")
    except anthropic.RateLimitError:
        raise LookupError_("Rate limited (too many tokens this minute). Wait a minute and try again.")
    except anthropic.APIStatusError as e:
        raise LookupError_(f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        raise LookupError_("Couldn't reach the Claude API. Check your internet connection.")
    if final.stop_reason == "refusal":
        raise LookupError_("Claude declined to write this deep dive.")


def deep_dive_ollama(model: str, term: str, placement: str, background: str, known: list[str]):
    """Yields text chunks from a local model. Slow on CPU (several minutes)."""
    payload = {
        "model": model,
        "stream": True,
        # Bigger working memory than a lookup: the prompt plus a ~2,500-word answer must fit.
        "options": {"temperature": 0.3, "num_ctx": 16384, "num_predict": 9000},
        "messages": [
            {"role": "system", "content": DEEP_SYSTEM},
            {"role": "user", "content": _deep_msg(term, placement, background, known)},
        ],
    }
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            for line in r:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if chunk.get("error"):
                    raise LookupError_(f"Ollama error: {chunk['error']}")
                yield chunk.get("message", {}).get("content", "")
                if chunk.get("done"):
                    break
    except urllib.error.HTTPError as e:
        raise LookupError_(f"Ollama error {e.code}: {e.read()[:300].decode(errors='replace')}")
    except TimeoutError:
        raise LookupError_("Ollama took too long (over 30 minutes).")
    except (urllib.error.URLError, OSError):
        raise LookupError_("Ollama isn't running. Start it (open the Ollama app or run `ollama serve`).")


# ---------------- Re-filing an existing term (short, fast call) ----------------
FILE_SYSTEM = f"You file glossary terms into a fixed taxonomy.\n{PLACEMENT_RULES}"


def classify(term: str, definition: str, *, model: str = "", api_key: str = "") -> tuple[str, str]:
    """Return (area, topic) for a saved term. Uses Ollama if `model` is given, else Claude."""
    msg = f"Term: {term}\nDefinition: {definition}"
    if model:
        f = _ollama_parse(model, FILE_SYSTEM, msg, Filing)
    else:
        f = _claude_parse(api_key, FILE_SYSTEM, msg, Filing, "low")
    return tx.split(f.placement)
