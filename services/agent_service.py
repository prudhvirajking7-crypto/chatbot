"""
Agentic RAG Service
===================
1. Searches the knowledge base (fast, k=4 docs)
2. Streams the LLM answer token-by-token for instant output
"""

import queue
import threading
from typing import Iterator


class AgenticRAGService:

    SYSTEM_PROMPT = """You are a helpful AI assistant. Answer clearly and concisely.
- Fix obvious typos/spelling silently — never mention them
- Start with a direct one-sentence answer
- Keep responses 80-180 words unless asked for more
- For code questions: write clean runnable code first, brief explanation after
- Use proper code fences with language tags (```python, ```js etc.)
- Use bullet points only for list-like content
- Be friendly and conversational"""

    RAG_PROMPT = """Use the context below to answer the question accurately.

Context:
{context}

Rules:
- Answer based on the context when relevant; use general knowledge when context doesn't cover it
- Fix obvious typos/spelling silently
- Start with a direct one-sentence answer
- Keep responses 80-180 words unless asked for more
- For code: write clean runnable code first, then brief explanation
- Use proper code fences (```python, ```js etc.)
- Do NOT mention page numbers, filenames, chunk counts, or retrieval details

Question: {question}
Answer:"""

    def __init__(self, rag_chatbot):
        self.bot = rag_chatbot

    def _search(self, query: str, retrieved_docs: list, event_q: queue.Queue) -> str:
        """Search KB, emit step events, return context string."""
        event_q.put({"type": "step", "content": "Searching knowledge base..."})
        try:
            docs = self.bot.retriever.invoke(query)
        except Exception:
            event_q.put({"type": "step", "content": "Search unavailable — answering from general knowledge"})
            return ""

        if not docs:
            event_q.put({"type": "step", "content": "No matching documents — answering from general knowledge"})
            return ""

        retrieved_docs.extend(docs)
        event_q.put({"type": "step", "content": f"Found {len(docs)} relevant documents — generating answer..."})
        return "\n\n---\n\n".join(doc.page_content for doc in docs[:4])

    def _stream_generate(self, query: str, context: str, event_q: queue.Queue):
        """Stream LLM tokens directly into event_q as chunk events."""
        from langchain_core.messages import HumanMessage, SystemMessage

        if context:
            prompt = self.RAG_PROMPT.format(context=context, question=query)
            messages = [HumanMessage(content=prompt)]
        else:
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=query),
            ]

        try:
            for chunk in self.bot.llm.stream(messages):
                token = getattr(chunk, "content", "") or ""
                if token:
                    event_q.put({"type": "chunk", "content": token})
        except Exception as exc:
            event_q.put({"type": "chunk", "content": f"\n\nSorry, an error occurred: {exc}"})

    def _run(self, query: str, retrieved_docs: list, event_q: queue.Queue):
        try:
            context = self._search(query, retrieved_docs, event_q)
            self._stream_generate(query, context, event_q)
        except Exception as exc:
            event_q.put({"type": "chunk", "content": f"Sorry, something went wrong: {exc}"})
        finally:
            event_q.put({"type": "_done"})

    def stream_response(self, query: str, docs_ref: list, source_ref: list) -> Iterator[dict]:
        """Yield step and chunk events. Chunks stream as tokens arrive."""
        event_q: queue.Queue = queue.Queue()
        retrieved_docs: list = []

        yield {"type": "step", "content": "Analyzing your question..."}

        thread = threading.Thread(
            target=self._run,
            args=(query, retrieved_docs, event_q),
            daemon=True,
        )
        thread.start()

        while True:
            try:
                event = event_q.get(timeout=90)
            except queue.Empty:
                break
            if event.get("type") == "_done":
                break
            yield event

        thread.join(timeout=5)

        docs_ref.extend(retrieved_docs)
        source_ref[0] = "rag" if retrieved_docs else "direct_llm"
