from typing import Optional, Dict
from pymongo import MongoClient
from bson import ObjectId
from core.config import get_config


class UserManager:
    """
    Manages user data operations including preferences and statistics.
    """

    def __init__(self, mongodb_uri: Optional[str] = None):
        """Initialize the UserManager with MongoDB connection."""
        # Get MongoDB URI
        self.mongodb_uri = mongodb_uri or get_config("MONGODB_URI")

        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required")

        # Connect to MongoDB
        self.client = MongoClient(
            self.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
        self.db = self.client["chatbot_db"]
        self.users_collection = self.db["users"]

    def get_user(self, user_id: str) -> Optional[Dict]:
        """
        Get user information by user ID.

        Args:
            user_id: User ID

        Returns:
            User dictionary or None
        """
        try:
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                return user
            return None
        except Exception as e:
            print(f"Get user error: {e}")
            return None

    def get_user_stats(self, user_id: str) -> Dict:
        """
        Get user statistics.

        Args:
            user_id: User ID

        Returns:
            Dictionary with stats (message_count, tokens_used)
        """
        try:
            user = self.users_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"message_count": 1, "tokens_used": 1, "_id": 0}
            )

            if user:
                return {
                    "message_count": user.get("message_count", 0),
                    "tokens_used": user.get("tokens_used", 0)
                }
            return {"message_count": 0, "tokens_used": 0}

        except Exception as e:
            print(f"Get user stats error: {e}")
            return {"message_count": 0, "tokens_used": 0}

    def get_user_preferences(self, user_id: str) -> Dict:
        """
        Get user preferences.

        Args:
            user_id: User ID

        Returns:
            Dictionary with preferences
        """
        try:
            user = self.users_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"preferences": 1, "_id": 0}
            )

            if user and "preferences" in user:
                return user["preferences"]

            # Return default preferences
            return {
                "default_mode": "Auto",
                "theme": "light"
            }

        except Exception as e:
            print(f"Get user preferences error: {e}")
            return {"default_mode": "Auto", "theme": "light"}

    def update_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """
        Update user preferences.

        Args:
            user_id: User ID
            preferences: New preferences dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"preferences": preferences}}
            )
            return result.modified_count > 0 or result.matched_count > 0

        except Exception as e:
            print(f"Update user preferences error: {e}")
            return False

    def increment_message_count(self, user_id: str, count: int = 1) -> bool:
        """
        Increment user's message count.

        Args:
            user_id: User ID
            count: Number to increment by (default 1)

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"message_count": count}}
            )
            return result.modified_count > 0

        except Exception as e:
            print(f"Increment message count error: {e}")
            return False

    def increment_token_usage(self, user_id: str, tokens: int) -> bool:
        """
        Increment user's token usage.

        Args:
            user_id: User ID
            tokens: Number of tokens to add

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"tokens_used": tokens}}
            )
            return result.modified_count > 0

        except Exception as e:
            print(f"Increment token usage error: {e}")
            return False

    def get_formatted_stats(self, user_id: str) -> str:
        """
        Get formatted user statistics string for display.

        Args:
            user_id: User ID

        Returns:
            Formatted stats string
        """
        stats = self.get_user_stats(user_id)
        message_count = stats["message_count"]
        tokens = stats["tokens_used"]

        # Format tokens with K/M suffix
        if tokens >= 1_000_000:
            tokens_str = f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1_000:
            tokens_str = f"{tokens / 1_000:.1f}K"
        else:
            tokens_str = str(tokens)

        return f"{message_count} msgs, {tokens_str} tokens"
