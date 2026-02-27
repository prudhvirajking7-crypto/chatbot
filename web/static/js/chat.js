(function () {
    const form = document.getElementById("chat-form");
    if (!form) return;

    const messageList = document.getElementById("message-list");
    const promptInput = document.getElementById("prompt-input");
    const conversationInput = document.getElementById("conversation-id");
    const conversationTitle = document.getElementById("conversation-title");
    const conversationIdText = document.getElementById("conversation-id-text");
    const modeSelect = document.getElementById("mode-select");
    const sendButton = form.querySelector("button[type='submit']");
    const toggleSidebarBtn = document.getElementById("toggle-sidebar");
    const closeSidebarBtn = document.getElementById("close-sidebar");
    const leftPanel = document.getElementById("left-panel");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");
    const focusInput = () => {
        if (promptInput) promptInput.focus();
    };

    const isNearBottom = () => {
        const distance = messageList.scrollHeight - messageList.scrollTop - messageList.clientHeight;
        return distance < 120;
    };

    const closeSidebar = () => {
        if (!leftPanel) return;
        leftPanel.classList.remove("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.remove("show");
        if (toggleSidebarBtn) toggleSidebarBtn.setAttribute("aria-expanded", "false");
        document.body.classList.remove("no-scroll");
    };

    const openSidebar = () => {
        if (!leftPanel) return;
        leftPanel.classList.add("open");
        if (sidebarBackdrop) sidebarBackdrop.classList.add("show");
        if (toggleSidebarBtn) toggleSidebarBtn.setAttribute("aria-expanded", "true");
        document.body.classList.add("no-scroll");
    };

    const scrollToBottom = (force = false) => {
        if (force || isNearBottom()) {
            requestAnimationFrame(() => {
                messageList.scrollTop = messageList.scrollHeight;
            });
        }
    };

    const removeEmptyState = () => {
        const emptyState = messageList.querySelector(".empty-state");
        if (emptyState) emptyState.remove();
    };

    const escapeHtml = (text) =>
        (text || "").replace(/[&<>"']/g, (char) => {
            const map = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;",
            };
            return map[char] || char;
        });

    const renderMarkdown = (rawText) => {
        let html = escapeHtml(rawText || "");
        const codeBlocks = [];

        html = html.replace(/```([\w-]+)?\n?([\s\S]*?)```/g, (_match, lang, code) => {
            const cls = lang ? ` class="language-${lang.toLowerCase()}"` : "";
            const block = `<pre><code${cls}>${(code || "").trimEnd()}</code></pre>`;
            const idx = codeBlocks.push(block) - 1;
            return `@@CODEBLOCK_${idx}@@`;
        });

        html = html.replace(/^###\s+(.+)$/gm, "<h4>$1</h4>");
        html = html.replace(/^##\s+(.+)$/gm, "<h3>$1</h3>");
        html = html.replace(/^#\s+(.+)$/gm, "<h2>$1</h2>");

        html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        html = html.replace(/__(.+?)__/g, "<strong>$1</strong>");
        html = html.replace(/(^|[^*])\*(?!\s)(.+?)(?<!\s)\*(?!\*)/g, "$1<em>$2</em>");
        html = html.replace(/(^|[^_])_(?!\s)(.+?)(?<!\s)_(?!_)/g, "$1<em>$2</em>");
        html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");

        const lines = html.split("\n");
        const out = [];
        let inUl = false;
        let inOl = false;

        const closeLists = () => {
            if (inUl) {
                out.push("</ul>");
                inUl = false;
            }
            if (inOl) {
                out.push("</ol>");
                inOl = false;
            }
        };

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) {
                closeLists();
                out.push("<br>");
                continue;
            }

            const ulMatch = line.match(/^\s*[-*]\s+(.+)$/);
            if (ulMatch) {
                if (!inUl) {
                    closeLists();
                    out.push("<ul>");
                    inUl = true;
                }
                out.push(`<li>${ulMatch[1]}</li>`);
                continue;
            }

            const olMatch = line.match(/^\s*(\d+)\.\s+(.+)$/);
            if (olMatch) {
                if (!inOl) {
                    closeLists();
                    out.push("<ol>");
                    inOl = true;
                }
                out.push(`<li>${olMatch[2]}</li>`);
                continue;
            }

            closeLists();
            if (/^<h[2-4]>/.test(trimmed) || /^@@CODEBLOCK_\d+@@$/.test(trimmed)) {
                out.push(trimmed);
            } else {
                out.push(`<p>${line}</p>`);
            }
        }

        closeLists();
        html = out.join("");
        html = html.replace(/@@CODEBLOCK_(\d+)@@/g, (_m, idx) => codeBlocks[Number(idx)] || "");
        return html;
    };

    const createMessageElement = (role, text) => {
        const article = document.createElement("article");
        article.className = `msg ${role}`;

        const bubble = document.createElement("div");
        bubble.className = "bubble";
        if (role === "assistant") {
            bubble.innerHTML = renderMarkdown(text);
        } else {
            bubble.textContent = text;
        }
        article.appendChild(bubble);

        return article;
    };

    const createStreamingAssistantElement = () => {
        const article = document.createElement("article");
        article.className = "msg assistant typing";

        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = "Thinking";
        article.appendChild(bubble);

        messageList.appendChild(article);
        return { article, bubble };
    };

    if (toggleSidebarBtn && leftPanel) {
        toggleSidebarBtn.addEventListener("click", () => {
            if (leftPanel.classList.contains("open")) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });

        if (sidebarBackdrop) {
            sidebarBackdrop.addEventListener("click", closeSidebar);
        }
        if (closeSidebarBtn) {
            closeSidebarBtn.addEventListener("click", closeSidebar);
        }

        leftPanel.querySelectorAll(".conversation-item a").forEach((link) => {
            link.addEventListener("click", closeSidebar);
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeSidebar();
        });

        window.addEventListener("resize", closeSidebar);
    }

    if (promptInput) {
        promptInput.addEventListener("keydown", (event) => {
            const isPlainEnter =
                event.key === "Enter" &&
                !event.shiftKey &&
                !event.ctrlKey &&
                !event.altKey &&
                !event.metaKey;
            if (!isPlainEnter || event.isComposing) return;

            event.preventDefault();
            if (sendButton && sendButton.disabled) return;

            if (typeof form.requestSubmit === "function") {
                form.requestSubmit();
            } else {
                form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
            }
        });
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const prompt = promptInput.value.trim();
        if (!prompt) return;
        if (sendButton) sendButton.disabled = true;

        removeEmptyState();
        messageList.appendChild(createMessageElement("user", prompt));
        promptInput.value = "";
        scrollToBottom(true);
        focusInput();

        const assistant = createStreamingAssistantElement();
        scrollToBottom(true);

        try {
            const response = await fetch("/chat/send/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt,
                    mode: modeSelect.value,
                    conversation_id: conversationInput.value || null,
                }),
            });

            if (!response.ok) {
                const raw = await response.text();
                let data = {};
                try {
                    data = raw ? JSON.parse(raw) : {};
                } catch (_err) {
                    data = { error: raw || `HTTP ${response.status} ${response.statusText}` };
                }
                assistant.article.classList.remove("typing");
                assistant.bubble.textContent = data.error || "Failed to send message.";
                scrollToBottom(true);
                return;
            }

            if (!response.body) {
                assistant.article.classList.remove("typing");
                assistant.bubble.textContent = "Streaming is not available in this browser.";
                scrollToBottom(true);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let output = "";
            const updateConversationMeta = (data) => {
                if (data.conversation_id) {
                    conversationInput.value = data.conversation_id;
                    conversationIdText.textContent = data.conversation_id;
                    window.history.replaceState({}, "", `/chat?conversation_id=${data.conversation_id}`);
                }
                if (data.conversation_title) {
                    conversationTitle.textContent = data.conversation_title;
                }
            };

            const appendAssistantChunk = (content) => {
                if (!content) return;
                const shouldStick = isNearBottom();
                if (assistant.article.classList.contains("typing")) {
                    assistant.article.classList.remove("typing");
                    assistant.bubble.innerHTML = "";
                }
                output += content;
                assistant.bubble.innerHTML = renderMarkdown(output);
                if (shouldStick) scrollToBottom(true);
            };

            const handleEvent = (evt) => {
                if (!evt || !evt.type) return;

                if (evt.type === "meta") {
                    updateConversationMeta(evt);
                    return;
                }

                if (evt.type === "chunk") {
                    appendAssistantChunk(evt.content || "");
                    return;
                }

                if (evt.type === "done") {
                    updateConversationMeta(evt);
                    return;
                }

                if (evt.type === "error") {
                    appendAssistantChunk("\n\n[Request ended with an error. Please retry.]");
                }
            };

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed) continue;
                    try {
                        handleEvent(JSON.parse(trimmed));
                    } catch (_err) {
                        appendAssistantChunk(trimmed);
                    }
                }
            }

            const finalLine = buffer.trim();
            if (finalLine) {
                try {
                    handleEvent(JSON.parse(finalLine));
                } catch (_err) {
                    appendAssistantChunk(finalLine);
                }
            }

            if (!output) {
                assistant.article.classList.remove("typing");
                assistant.bubble.innerHTML = renderMarkdown("No response received. Please try again.");
            }

            scrollToBottom(true);
        } catch (error) {
            assistant.article.classList.remove("typing");
            assistant.bubble.textContent = `Request failed: ${error}`;
            scrollToBottom(true);
        } finally {
            if (sendButton) sendButton.disabled = false;
            focusInput();
        }
    });

    scrollToBottom(true);
    setTimeout(() => scrollToBottom(true), 120);
    window.addEventListener("load", () => {
        messageList.querySelectorAll(".msg.assistant .bubble").forEach((bubble) => {
            bubble.innerHTML = renderMarkdown(bubble.textContent || "");
        });
        scrollToBottom(true);
        setTimeout(() => scrollToBottom(true), 80);
    });
})();
