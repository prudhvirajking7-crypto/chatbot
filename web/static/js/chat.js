(function () {
  const form       = document.getElementById("chat-form");
  if (!form) return;

  const chatBody   = document.getElementById("chat-body");
  const msgList    = document.getElementById("message-list");
  const input      = document.getElementById("prompt-input");
  const convId     = document.getElementById("conversation-id");
  const chatTitle  = document.getElementById("chat-title");
  const modeSelect = document.getElementById("mode-select");
  const sendBtn    = document.getElementById("send-btn");
  const charCount  = document.getElementById("char-count");
  const menuBtn    = document.getElementById("menu-btn");
  const sidebar    = document.getElementById("sidebar");
  const overlay    = document.getElementById("sidebar-overlay");
  const emptyState = document.getElementById("empty-state");

  const BOOTSTRAP  = window.__BOOTSTRAP__ || {};
  const userInitial = BOOTSTRAP.userInitial || "U";

  // ── Auto-resize textarea ──────────────────────────
  if (input) {
    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 160) + "px";
      if (charCount) charCount.textContent = `${input.value.length} / 4000`;
    });
  }

  // ── Suggestion cards ──────────────────────────────
  document.querySelectorAll(".suggestion-card").forEach((card) => {
    card.addEventListener("click", () => {
      if (!input) return;
      input.value = card.dataset.prompt || "";
      input.dispatchEvent(new Event("input"));
      input.focus();
    });
  });

  // ── Mobile sidebar ────────────────────────────────
  const openSidebar  = () => { sidebar?.classList.add("open"); overlay?.classList.add("show"); document.body.style.overflow = "hidden"; };
  const closeSidebar = () => { sidebar?.classList.remove("open"); overlay?.classList.remove("show"); document.body.style.overflow = ""; };

  menuBtn?.addEventListener("click", () => sidebar?.classList.contains("open") ? closeSidebar() : openSidebar());
  overlay?.addEventListener("click", closeSidebar);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSidebar(); });

  // ── Scroll helpers ────────────────────────────────
  const nearBottom = () => chatBody ? chatBody.scrollHeight - chatBody.scrollTop - chatBody.clientHeight < 160 : false;
  const scrollDown = (force = false) => {
    if (!chatBody) return;
    if (force || nearBottom()) requestAnimationFrame(() => { chatBody.scrollTop = chatBody.scrollHeight; });
  };

  // ── HTML escape ───────────────────────────────────
  const esc = (s) => (s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ── Markdown renderer ─────────────────────────────
  const md = (raw) => {
    let html = esc(raw || "");
    const blocks = [];
    html = html.replace(/```([\w-]+)?\n?([\s\S]*?)```/g, (_m, lang, code) => {
      const l = (lang || "").toLowerCase();
      const cls  = l ? ` class="language-${l}"` : "";
      const dlang = l ? ` data-lang="${l}"` : "";
      return `@@${blocks.push(`<pre${dlang}><code${cls}>${(code||"").trimEnd()}</code></pre>`) - 1}@@`;
    });
    html = html.replace(/^###\s+(.+)$/gm, "<h4>$1</h4>");
    html = html.replace(/^##\s+(.+)$/gm,  "<h3>$1</h3>");
    html = html.replace(/^#\s+(.+)$/gm,   "<h2>$1</h2>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/__(.+?)__/g,     "<strong>$1</strong>");
    html = html.replace(/(^|[^*])\*(?!\s)(.+?)(?<!\s)\*(?!\*)/g, "$1<em>$2</em>");
    html = html.replace(/`([^`\n]+)`/g,   "<code>$1</code>");

    const lines = html.split("\n");
    const out = [];
    let inUl = false, inOl = false;
    const closeLists = () => {
      if (inUl) { out.push("</ul>"); inUl = false; }
      if (inOl) { out.push("</ol>"); inOl = false; }
    };
    for (const line of lines) {
      const t = line.trim();
      if (!t) { closeLists(); out.push("<br>"); continue; }
      const ul = line.match(/^\s*[-*]\s+(.+)$/);
      if (ul) { if (!inUl) { closeLists(); out.push("<ul>"); inUl = true; } out.push(`<li>${ul[1]}</li>`); continue; }
      const ol = line.match(/^\s*\d+\.\s+(.+)$/);
      if (ol) { if (!inOl) { closeLists(); out.push("<ol>"); inOl = true; } out.push(`<li>${ol[1]}</li>`); continue; }
      closeLists();
      if (/^<h[2-4]>/.test(t) || /^@@\d+@@$/.test(t)) out.push(t);
      else out.push(`<p>${line}</p>`);
    }
    closeLists();
    return out.join("").replace(/@@(\d+)@@/g, (_m, i) => blocks[+i] || "");
  };

  // ── Build message row ─────────────────────────────
  const buildRow = (role, html, isMarkdown = false) => {
    const row = document.createElement("div");
    row.className = `msg-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = role === "assistant" ? "msg-avatar ai-avatar" : "msg-avatar user-avatar";
    if (role === "assistant") {
      avatar.innerHTML = `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5L12 4.25V9.75L7 12.5L2 9.75V4.25L7 1.5Z" stroke="white" stroke-width="1.3" stroke-linejoin="round"/><circle cx="7" cy="7" r="1.5" fill="white"/></svg>`;
    } else {
      avatar.textContent = userInitial;
    }

    const body = document.createElement("div");
    body.className = "msg-body";
    if (role === "user") body.style.alignItems = "flex-end";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (isMarkdown) bubble.innerHTML = html;
    else bubble.textContent = html;

    body.appendChild(bubble);
    if (role === "assistant") { row.appendChild(avatar); row.appendChild(body); }
    else { row.appendChild(avatar); row.appendChild(body); }
    return { row, body, bubble };
  };

  // ── Create streaming assistant placeholder ────────
  const createStreamRow = () => {
    const row = document.createElement("div");
    row.className = "msg-row assistant";

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar ai-avatar";
    avatar.innerHTML = `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5L12 4.25V9.75L7 12.5L2 9.75V4.25L7 1.5Z" stroke="white" stroke-width="1.3" stroke-linejoin="round"/><circle cx="7" cy="7" r="1.5" fill="white"/></svg>`;

    const body = document.createElement("div");
    body.className = "msg-body";

    // Steps wrap
    const stepsWrap = document.createElement("div");
    stepsWrap.className = "agent-steps-wrap";
    stepsWrap.style.display = "none";

    const toggle = document.createElement("button");
    toggle.className = "steps-toggle open";
    toggle.innerHTML = `<i class="toggle-chevron">▶</i> <span class="toggle-label">Reasoning…</span>`;

    const stepsList = document.createElement("div");
    stepsList.className = "steps-list";

    toggle.addEventListener("click", () => {
      const isOpen = !stepsList.classList.contains("hidden");
      stepsList.classList.toggle("hidden", isOpen);
      toggle.classList.toggle("open", !isOpen);
      const n = stepsList.children.length;
      toggle.querySelector(".toggle-label").textContent = isOpen
        ? `${n} reasoning step${n !== 1 ? "s" : ""}`
        : "Reasoning…";
    });

    stepsWrap.appendChild(toggle);
    stepsWrap.appendChild(stepsList);

    // Typing indicator
    const typing = document.createElement("div");
    typing.className = "typing-indicator";
    typing.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;

    // Actual bubble (hidden until first chunk)
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.style.display = "none";

    body.appendChild(stepsWrap);
    body.appendChild(typing);
    body.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(body);
    msgList.appendChild(row);

    return { row, body, stepsWrap, toggle, stepsList, typing, bubble };
  };

  // ── Enter key to submit ───────────────────────────
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      if (!sendBtn?.disabled) form.requestSubmit?.() ?? form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    }
  });

  // ── Form submit ───────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompt = (input?.value || "").trim();
    if (!prompt) return;
    if (sendBtn) sendBtn.disabled = true;

    // Hide empty state
    if (emptyState) { emptyState.remove(); }

    // Add user message
    const { row: userRow } = buildRow("user", prompt);
    msgList.appendChild(userRow);
    if (input) { input.value = ""; input.style.height = "auto"; }
    if (charCount) charCount.textContent = "0 / 4000";
    scrollDown(true);

    // Create streaming placeholder
    const s = createStreamRow();
    scrollDown(true);

    try {
      const res = await fetch("/chat/send/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          mode: modeSelect?.value || "Auto",
          conversation_id: convId?.value || null,
        }),
      });

      if (!res.ok) {
        const raw = await res.text();
        let msg = "Request failed.";
        try { msg = JSON.parse(raw).error || msg; } catch {}
        s.typing.remove();
        s.bubble.style.display = "";
        s.bubble.textContent = msg;
        scrollDown(true);
        return;
      }

      if (!res.body) {
        s.typing.remove();
        s.bubble.style.display = "";
        s.bubble.textContent = "Streaming unavailable.";
        scrollDown(true);
        return;
      }

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      let output = "";
      let steps = 0;

      const updateMeta = (data) => {
        if (data.conversation_id && convId) convId.value = data.conversation_id;
        if (data.conversation_id) window.history.replaceState({}, "", `/chat?conversation_id=${data.conversation_id}`);
        if (data.conversation_title && chatTitle) chatTitle.textContent = data.conversation_title;
      };

      const addStep = (content) => {
        if (s.stepsWrap.style.display === "none") s.stepsWrap.style.display = "";
        const stepEl = document.createElement("div");
        stepEl.className = "step-row";
        stepEl.innerHTML = `
          <div class="step-icon">
            <svg viewBox="0 0 10 10" fill="none" width="10" height="10">
              <circle cx="5" cy="5" r="4" stroke="currentColor" stroke-width="1.2"/>
              <path d="M3 5l1.5 1.5L7 3.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
          </div>
          <span>${esc(content)}</span>`;
        s.stepsList.appendChild(stepEl);
        steps++;
        if (nearBottom()) scrollDown(true);
      };

      const appendChunk = (content) => {
        if (!content) return;
        const stick = nearBottom();
        if (s.typing.parentNode) { s.typing.remove(); }
        if (s.bubble.style.display === "none") {
          s.bubble.style.display = "";
          // Collapse steps
          if (steps > 0) {
            s.stepsList.classList.add("hidden");
            s.toggle.classList.remove("open");
            s.toggle.querySelector(".toggle-label").textContent = `${steps} reasoning step${steps !== 1 ? "s" : ""}`;
          }
        }
        output += content;
        s.bubble.innerHTML = md(output);
        if (stick) scrollDown(true);
      };

      const handleEvent = (evt) => {
        if (!evt?.type) return;
        switch (evt.type) {
          case "meta": updateMeta(evt); break;
          case "step": addStep(evt.content || ""); break;
          case "chunk": appendChunk(evt.content || ""); break;
          case "done":
            updateMeta(evt);
            scrollDown(true);
            break;
          case "error":
            appendChunk("\n\n[Request ended with an error. Please retry.]");
            break;
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() || "";
        for (const line of lines) {
          const t = line.trim();
          if (!t) continue;
          try { handleEvent(JSON.parse(t)); } catch { appendChunk(t); }
        }
      }
      if (buf.trim()) {
        try { handleEvent(JSON.parse(buf.trim())); } catch { appendChunk(buf.trim()); }
      }
      if (!output) {
        if (s.typing.parentNode) s.typing.remove();
        s.bubble.style.display = "";
        s.bubble.innerHTML = md("No response received. Please try again.");
      }
      scrollDown(true);

    } catch (err) {
      if (s.typing.parentNode) s.typing.remove();
      s.bubble.style.display = "";
      s.bubble.textContent = `Request failed: ${err}`;
      scrollDown(true);
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      input?.focus();
    }
  });

  // ── Render existing messages on load ──────────────
  scrollDown(true);
  window.addEventListener("load", () => {
    msgList?.querySelectorAll(".msg-row.assistant .bubble").forEach((b) => {
      b.innerHTML = md(b.textContent || "");
    });
    scrollDown(true);
  });
})();
