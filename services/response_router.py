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
