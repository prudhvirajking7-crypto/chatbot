import re
from typing import Iterator, Tuple


class ResponseRouter:
    """
    Intelligent query routing system that determines how to handle user queries
    based on query type and selected chat mode.
    """

    # Greeting patterns
    GREETING_PATTERNS = [
        r'\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b',
        r'\b(thanks|thank you|thx|appreciate it)\b',
        r'\b(bye|goodbye|see you|farewell)\b',
        r'\bhow are you\b',
        r'\bwhats up\b',
        r'\bwhat\'s up\b',
    ]

    # Document-related keywords
    DOCUMENT_KEYWORDS = [
        'document', 'documents', 'file', 'files', 'pdf', 'text',
        'according to', 'based on', 'what does it say', 'in the document',
        'from the file', 'summarize', 'explain the document', 'tell me about the document'
    ]

    # Coding / programming keywords — always route to RAG so docs are consulted
    CODING_KEYWORDS = [
        'code', 'function', 'class', 'method', 'variable', 'loop', 'array',
        'list', 'dict', 'dictionary', 'import', 'module', 'library', 'package',
        'install', 'pip', 'npm', 'syntax', 'error', 'exception', 'debug',
        'algorithm', 'implement', 'example', 'snippet', 'script', 'program',
        'api', 'endpoint', 'request', 'response', 'json', 'http', 'rest',
        'database', 'query', 'sql', 'mongodb', 'schema',
        'how to', 'how do i', 'how can i', 'write a', 'create a', 'build a',
        'def ', 'class ', 'return', 'lambda', 'async', 'await', 'callback',
        'framework', 'fastapi', 'flask', 'django', 'react', 'javascript', 'python',
        'typescript', 'rust', 'golang', 'java', 'kotlin', 'swift',
    ]

    def __init__(self):
        self.greeting_regex = re.compile('|'.join(self.GREETING_PATTERNS), re.IGNORECASE)

    def detect_query_type(self, query: str) -> str:
        """
        Detect the type of query.

        Returns:
            - "greeting": Simple greeting or pleasantry
            - "document_question": Question about documents
            - "general": General knowledge question
        """
        query_lower = query.lower().strip()

        # Check for greetings
        if self.greeting_regex.search(query_lower):
            return "greeting"

        # Check for document-related questions
        for keyword in self.DOCUMENT_KEYWORDS:
            if keyword.lower() in query_lower:
                return "document_question"

        # Check for coding/programming questions — route to RAG to use uploaded docs
        for keyword in self.CODING_KEYWORDS:
            if keyword.lower() in query_lower:
                return "coding_question"

        # Default to general question
        return "general"

    def route_query(
        self,
        query: str,
        mode: str,
        bot,
        doc_count: int = 0
    ) -> Tuple[str, str, list]:
        """
        Route the query to the appropriate handler based on mode and query type.

        Args:
            query: User's query
            mode: Chat mode ("Auto", "RAG Only", "Direct LLM")
            bot: RAGChatbot instance
            doc_count: Number of documents in knowledge base

        Returns:
            Tuple of (response, source_type, source_docs)
            - source_type: "direct_llm", "rag", "rag_fallback"
            - source_docs: List of source documents (empty for direct LLM)
        """
        query_type = self.detect_query_type(query)

        # Greetings ALWAYS use Direct LLM regardless of mode
        if query_type == "greeting":
            response = bot.get_direct_llm_response(query)
            return response, "direct_llm", []

        # Handle based on mode
        if mode == "Auto":
            return self._handle_auto_mode(query, query_type, bot, doc_count)
        elif mode == "RAG Only":
            return self._handle_rag_only_mode(query, bot)
        elif mode == "Direct LLM":
            return self._handle_direct_llm_mode(query, bot)
        else:
            # Default to Auto mode if invalid mode
            return self._handle_auto_mode(query, query_type, bot, doc_count)

    def route_query_stream(
        self,
        query: str,
        mode: str,
        bot,
        doc_count: int = 0
    ) -> Tuple[Iterator[str], str, list]:
        """
        Route query for token/chunk streaming.
        Returns (chunk_iterator, source_type, source_docs).
        """
        query_type = self.detect_query_type(query)

        if query_type == "greeting":
            return bot.stream_direct_llm_response(query), "direct_llm", []

        if mode == "Auto":
            if query_type == "document_question" and doc_count > 0:
                return bot.stream_rag_response_with_fallback(query)
            return bot.stream_direct_llm_response(query), "direct_llm", []

        if mode == "RAG Only":
            return bot.stream_rag_response_with_fallback(query)

        if mode == "Direct LLM":
            return bot.stream_direct_llm_response(query), "direct_llm", []

        return bot.stream_direct_llm_response(query), "direct_llm", []

    def _handle_auto_mode(
        self,
        query: str,
        query_type: str,
        bot,
        doc_count: int
    ) -> Tuple[str, str, list]:
        """
        Auto mode: Smart routing based on query type.
        - Document questions → RAG (if docs available, else Direct LLM)
        - General questions → Direct LLM
        """
        if query_type == "document_question" and doc_count > 0:
            # Try RAG first
            response, source_type, docs = bot.get_rag_response_with_fallback(query)
            return response, source_type, docs
        else:
            # Use Direct LLM for general questions or if no docs
            response = bot.get_direct_llm_response(query)
            return response, "direct_llm", []

    def _handle_rag_only_mode(self, query: str, bot) -> Tuple[str, str, list]:
        """
        RAG Only mode: Always try RAG, fallback to Direct LLM if no context.
        """
        response, source_type, docs = bot.get_rag_response_with_fallback(query)
        return response, source_type, docs

    def _handle_direct_llm_mode(self, query: str, bot) -> Tuple[str, str, list]:
        """
        Direct LLM mode: Always use Direct LLM, ignore RAG.
        """
        response = bot.get_direct_llm_response(query)
        return response, "direct_llm", []

    def route_query_events(
        self,
        query: str,
        mode: str,
        bot,
        doc_count: int = 0,
    ) -> tuple:
        """
        Route a query for event-based streaming (agentic RAG path).

        Returns (event_iterator, source_ref, docs_ref) where:
          - event_iterator yields {"type": "step"|"chunk", "content": str}
          - source_ref is a mutable list [source_type_str], set after iteration
          - docs_ref is a mutable list of Document objects, set after iteration
        """
        from services.agent_service import AgenticRAGService

        source_ref = ["direct_llm"]
        docs_ref: list = []
        query_type = self.detect_query_type(query)

        # Greetings always bypass the knowledge base
        if query_type == "greeting":
            def _greeting_events():
                source_ref[0] = "direct_llm"
                for chunk in bot.stream_direct_llm_response(query):
                    if chunk:
                        yield {"type": "chunk", "content": chunk}
            return _greeting_events(), source_ref, docs_ref

        # Coding questions always go to RAG when docs are available (learn syntax from docs)
        if query_type == "coding_question" and doc_count > 0 and mode != "Direct LLM":
            agent_svc = AgenticRAGService(bot)
            return agent_svc.stream_response(query, docs_ref, source_ref), source_ref, docs_ref

        # Agentic RAG when docs are indexed and mode supports it
        if mode in ("Auto", "RAG Only") and doc_count > 0:
            agent_svc = AgenticRAGService(bot)
            return agent_svc.stream_response(query, docs_ref, source_ref), source_ref, docs_ref

        # RAG Only requested but no docs indexed — graceful fallback
        if mode == "RAG Only":
            def _no_docs_events():
                source_ref[0] = "rag_fallback"
                for chunk in bot.stream_direct_llm_response(query):
                    if chunk:
                        yield {"type": "chunk", "content": chunk}
            return _no_docs_events(), source_ref, docs_ref

        # Direct LLM (or Auto with no docs)
        def _llm_events():
            source_ref[0] = "direct_llm"
            for chunk in bot.stream_direct_llm_response(query):
                if chunk:
                    yield {"type": "chunk", "content": chunk}
        return _llm_events(), source_ref, docs_ref

    @staticmethod
    def get_source_display(source_type: str, doc_count: int = 0) -> str:
        """
        Get a friendly display string for the source type.

        Args:
            source_type: "direct_llm", "rag", or "rag_fallback"
            doc_count: Number of source documents

        Returns:
            Formatted source string for display
        """
        if source_type == "rag":
            return f"🔍 RAG ({doc_count} sources)"
        elif source_type == "rag_fallback":
            return "🤖 Direct LLM (no relevant docs found)"
        else:
            return "🤖 Direct LLM"
