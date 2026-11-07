// Frontend for the mini agent. Talks to server.py and shows the harness loop live.

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};
const short = (s, n = 160) => (s.length > n ? s.slice(0, n) + "…" : s);

let conversationId = null;
let busy = false;
const stats = { turns: 0, tools: 0 };

// ---------------- setup ----------------

async function checkHealth() {
  const status = $("status");
  try {
    const h = await (await fetch("/api/health")).json();
    const select = $("model");
    const current = select.value;
    select.innerHTML = "";
    const models = h.models.length ? h.models : [h.default_model];
    for (const m of models) select.append(new Option(m, m));
    select.value = models.includes(current) ? current
                 : models.includes(h.default_model) ? h.default_model : models[0];
    status.className = "status " + (h.ollama ? "ok" : "bad");
    $("status-text").textContent = h.ollama ? "Ollama connected" : "Ollama not running";
  } catch {
    status.className = "status bad";
    $("status-text").textContent = "server offline";
  }
}

async function newChat() {
  const r = await (await fetch("/api/reset", { method: "POST" })).json();
  conversationId = r.id;
  $("messages").innerHTML = "";
  $("messages").append(emptyState);
  $("timeline").innerHTML = '<li class="hint">Events from the loop show up here as they happen.</li>';
  stats.turns = 0; stats.tools = 0;
  updateStats(1);
  refreshMemory();
}

function updateStats(msgCount) {
  $("stat-turns").textContent = stats.turns;
  $("stat-tools").textContent = stats.tools;
  if (msgCount !== undefined) $("stat-msgs").textContent = msgCount;
}

// ---------------- chat ----------------

function addUserMessage(text) {
  const m = el("div", "msg user");
  m.append(el("div", "bubble", text));
  $("messages").append(m);
}

function addAgentMessage() {
  const m = el("div", "msg agent");
  const steps = el("details", "steps");
  const summary = el("summary", null, "Working…");
  const list = el("ul");
  steps.append(summary, list);
  const bubble = el("div", "bubble thinking", "Thinking…");
  m.append(steps, bubble);
  $("messages").append(m);
  return { steps, summary, list, bubble };
}

function scrollChat() {
  const box = $("messages");
  box.scrollTop = box.scrollHeight;
}

// ---------------- timeline (the loop, live) ----------------

function addEvent(cls, title, meta, body) {
  const tl = $("timeline");
  tl.querySelector(".hint")?.remove();
  const li = el("li", "ev " + cls);
  const head = el("div", "head");
  head.append(el("span", null, title));
  if (meta) head.append(el("span", "meta", meta));
  li.append(head);
  if (body) li.append(el("pre", null, body));
  tl.append(li);
  li.scrollIntoView({ block: "nearest" });
}

function handleEvent(ev, ui) {
  switch (ev.type) {
    case "start":
      conversationId = ev.id;
      addEvent("turn", "▶ New request", ev.model);
      break;

    case "turn_start":
      stats.turns++;
      updateStats(ev.messages_sent);
      ui.summary.textContent = `Turn ${ev.turn} of max ${ev.max_turns}…`;
      addEvent("turn", `Turn ${ev.turn}`, `sending ${ev.messages_sent} messages to the model`);
      break;

    case "model_reply": {
      const what = ev.tool_calls ? `asks for ${ev.tool_calls} tool call(s)` : "final answer (no tools)";
      addEvent("reply", `Model replied: ${what}`, `${(ev.ms / 1000).toFixed(1)}s`, ev.text || null);
      break;
    }

    case "tool_call": {
      const args = JSON.stringify(ev.args);
      addEvent("call", `🔧 ${ev.name}`, "harness runs the tool", args);
      const li = el("li", "call");
      li.append(el("b", null, ev.name), document.createTextNode(`(${short(args, 90)})`));
      ui.list.append(li);
      ui.bubble.textContent = `Running ${ev.name}…`;
      break;
    }

    case "tool_result":
      stats.tools++;
      updateStats();
      addEvent("result" + (ev.is_error ? " err" : ""),
               ev.is_error ? `✖ ${ev.name} failed → error sent back to the model` : `✔ ${ev.name} result → sent back to the model`,
               `${ev.ms} ms`, short(ev.result, 600));
      ui.list.append(el("li", ev.is_error ? "err" : "", `→ ${short(ev.result.replace(/\s+/g, " "), 110)}`));
      ui.bubble.textContent = "Thinking…";
      break;

    case "done":
      addEvent("done", "■ Done: model stopped asking for tools",
               `${ev.turns} turns · ${ev.tool_calls} tool calls`);
      ui.summary.textContent = `${ev.turns} turn(s), ${ev.tool_calls} tool call(s): show steps`;
      ui.bubble.className = "bubble";
      ui.bubble.textContent = ev.answer || "(the model returned an empty answer)";
      break;

    case "stopped":
      addEvent("stop", `■ Stopped: hit the ${ev.turns}-turn limit`, `${ev.tool_calls} tool calls`);
      ui.summary.textContent = `Stopped after ${ev.turns} turn(s): show steps`;
      ui.bubble.className = "bubble error";
      ui.bubble.textContent = `The loop hit the max-turns limit (${ev.turns}) before the model finished. Raise "Max turns" and try again.`;
      break;

    case "error":
      addEvent("error", "Error", null, ev.message);
      ui.summary.textContent = "Failed";
      ui.bubble.className = "bubble error";
      ui.bubble.textContent = ev.message;
      break;
  }
  scrollChat();
}

async function send(text) {
  if (busy || !text.trim()) return;
  busy = true;
  $("send").disabled = true;
  emptyState.remove();
  addUserMessage(text);
  const ui = addAgentMessage();
  scrollChat();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: conversationId,
        message: text,
        model: $("model").value,
        max_turns: Number($("max-turns").value) || 10,
      }),
    });
    // Read the Server-Sent Events stream: each event is "data: {...}\n\n"
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const chunk = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        if (chunk.startsWith("data: ")) handleEvent(JSON.parse(chunk.slice(6)), ui);
      }
    }
  } catch (e) {
    handleEvent({ type: "error", message: "Lost connection to the server: " + e.message }, ui);
  } finally {
    busy = false;
    $("send").disabled = false;
    $("input").focus();
    refreshMemory();
    refreshNotes();
  }
}

// ---------------- memory + notes panels ----------------

async function refreshMemory() {
  if (!conversationId) return;
  const msgs = await (await fetch("/api/memory?id=" + encodeURIComponent(conversationId))).json();
  const box = $("memory");
  box.innerHTML = "";
  msgs.forEach((m, i) => {
    const card = el("div", "mem " + m.role);
    const role = el("div", "role");
    role.append(el("span", null, `${i + 1}. ${m.role}${m.tool_name ? " · " + m.tool_name : ""}`));
    card.append(role);
    let body = m.content || "";
    if (m.tool_calls?.length) {
      body += (body ? "\n" : "") + m.tool_calls
        .map((c) => `→ calls ${c.function.name}(${JSON.stringify(c.function.arguments)})`).join("\n");
    }
    card.append(el("pre", null, body || "(empty)"));
    box.append(card);
  });
  $("stat-msgs").textContent = msgs.length;
}

async function refreshNotes() {
  const notes = await (await fetch("/api/notes")).json();
  const list = $("notes");
  list.innerHTML = "";
  if (!notes.length) list.append(el("li", "hint", "No notes yet. Ask the agent to save a report."));
  for (const n of notes) {
    const li = el("li");
    const b = el("button");
    b.append(el("span", null, n.name), el("span", "meta", `${n.size} B`));
    b.onclick = async () => {
      const r = await (await fetch("/api/notes/" + encodeURIComponent(n.name))).json();
      const view = $("note-view");
      view.hidden = false;
      view.textContent = r.content ?? r.error;
    };
    li.append(b);
    list.append(li);
  }
}

// ---------------- wiring ----------------

const emptyState = $("empty");

$("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = $("input").value;
  $("input").value = "";
  send(text);
});
$("input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("composer").requestSubmit(); }
});
$("input").addEventListener("input", (e) => {
  e.target.style.height = "auto";
  e.target.style.height = e.target.scrollHeight + "px";
});
document.querySelectorAll(".chip").forEach((c) => (c.onclick = () => send(c.textContent)));
document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => {
  document.querySelectorAll(".tab, .panel").forEach((x) => x.classList.remove("active"));
  t.classList.add("active");
  $("panel-" + t.dataset.tab).classList.add("active");
  if (t.dataset.tab === "memory") refreshMemory();
  if (t.dataset.tab === "notes") refreshNotes();
}));
$("new-chat").onclick = newChat;

checkHealth();
setInterval(checkHealth, 15000);
newChat();
refreshNotes();
