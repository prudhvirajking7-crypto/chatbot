from datetime import datetime
from typing import List, Dict, Optional
from pymongo import MongoClient
from bson import ObjectId
from core.config import get_config


class ChatHistoryManager:
    def __init__(self, mongodb_uri=None):
        """Initialize chat history manager with MongoDB connection"""
        # Get MongoDB URI from various sources
        self.mongodb_uri = mongodb_uri or get_config("MONGODB_URI")

        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required for chat history")

        self.client = MongoClient(
            self.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
        self.db = self.client["chatbot_db"]
        self.conversations_collection = self.db["conversations"]
        self.messages_collection = self.db["messages"]

        # Create indexes for better performance
        self._create_indexes()

    def _create_indexes(self):
        """Create MongoDB indexes for better query performance"""
        try:
            # Index on user_id for filtering conversations
            self.conversations_collection.create_index("user_id")

            # Index on conversation_id for messages
            self.messages_collection.create_index("conversation_id")
        except Exception as e:
            print(f"Index creation note: {e}")

    def create_conversation(self, title: str = "New Chat", user_id: str = None) -> str:
        """
        Create a new conversation and return its ID.

        Args:
            title: Conversation title
            user_id: User ID (required for user-specific conversations)

        Returns:
            Conversation ID string
        """
        conversation = {
            "title": title,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Add user_id if provided
        if user_id:
            conversation["user_id"] = user_id

        result = self.conversations_collection.insert_one(conversation)
        return str(result.inserted_id)

    def get_all_conversations(self, user_id: str = None) -> List[Dict]:
        """
        Get all conversations sorted by most recent.

        Args:
            user_id: User ID to filter conversations (optional)

        Returns:
            List of conversation dictionaries
        """
        # Build query filter
        query = {}
        if user_id:
            query["user_id"] = user_id

        conversations = self.conversations_collection.find(query).sort("updated_at", -1)
        result = []
        for conv in conversations:
            result.append({
                "id": str(conv["_id"]),
                "title": conv.get("title", "New Chat"),
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at"),
            })
        return result

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a specific conversation by ID"""
        try:
            conv = self.conversations_collection.find_one({"_id": ObjectId(conversation_id)})
            if conv:
                return {
                    "id": str(conv["_id"]),
                    "title": conv.get("title", "New Chat"),
                    "created_at": conv.get("created_at"),
                    "updated_at": conv.get("updated_at"),
                }
        except:
            return None

    def update_conversation_title(self, conversation_id: str, title: str):
        """Update conversation title"""
        try:
            self.conversations_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"title": title, "updated_at": datetime.utcnow()}}
            )
        except:
            pass

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all its messages"""
        try:
            # Delete all messages in this conversation
            self.messages_collection.delete_many({"conversation_id": conversation_id})
            # Delete the conversation
            self.conversations_collection.delete_one({"_id": ObjectId(conversation_id)})
        except:
            pass

    def add_message(self, conversation_id: str, role: str, content: str):
        """Add a message to a conversation"""
        message = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
        }
        self.messages_collection.insert_one(message)

        # Update conversation's updated_at timestamp
        try:
            self.conversations_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
        except:
            pass

    def get_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a conversation"""
        messages = self.messages_collection.find(
            {"conversation_id": conversation_id}
        ).sort("timestamp", 1)

        result = []
        for msg in messages:
            result.append({
                "role": msg.get("role"),
                "content": msg.get("content"),
                "timestamp": msg.get("timestamp"),
            })
        return result

    def clear_conversation(self, conversation_id: str):
        """Clear all messages in a conversation"""
        self.messages_collection.delete_many({"conversation_id": conversation_id})

    def auto_generate_title(self, conversation_id: str, first_message: str):
        """Auto-generate conversation title from first message"""
        # Take first 50 characters of the message as title
        title = first_message[:50]
        if len(first_message) > 50:
            title += "..."
        self.update_conversation_title(conversation_id, title)
