from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from pymongo import MongoClient
from bson import ObjectId
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
import secrets
from core.config import get_config


class AuthManager:
    """
    Manages Google OAuth2 authentication and user sessions.
    """

    def __init__(self, mongodb_uri: Optional[str] = None):
        """Initialize the AuthManager with MongoDB connection."""
        # Get MongoDB URI
        self.mongodb_uri = mongodb_uri or get_config("MONGODB_URI")

        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required for authentication")

        # Connect to MongoDB
        self.client = MongoClient(
            self.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
        self.db = self.client["chatbot_db"]
        self.users_collection = self.db["users"]
        self.sessions_collection = self.db["sessions"]

        # Create indexes
        self._create_indexes()

        # Get Google OAuth credentials
        self.client_id = (self._get_config("GOOGLE_CLIENT_ID") or "").strip()
        self.client_secret = (self._get_config("GOOGLE_CLIENT_SECRET") or "").strip()
        self.redirect_uri = (self._get_config("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback") or "").strip()

    def _get_config(self, key: str, default: Optional[str] = None) -> str:
        """Get configuration from secrets or environment variables."""
        return get_config(key, default)

    def _create_indexes(self):
        """Create necessary MongoDB indexes."""
        try:
            # Unique index on user email
            self.users_collection.create_index("email", unique=True)

            # Index on session user_id for faster lookups
            self.sessions_collection.create_index("user_id")

            # TTL index on sessions for automatic expiration
            self.sessions_collection.create_index(
                "expires_at",
                expireAfterSeconds=0  # MongoDB will delete when expires_at is passed
            )
        except Exception as e:
            print(f"Index creation note: {e}")

    def get_google_auth_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate Google OAuth authorization URL.

        Returns:
            Tuple of (authorization URL, OAuth state)
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")

        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid"
            ],
            redirect_uri=self.redirect_uri
        )

        # Generate authorization URL
        auth_url, generated_state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state,
        )

        return auth_url, generated_state

    def exchange_code_for_token(self, code: str, state: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Exchange authorization code for access token and get user info.

        Args:
            code: Authorization code from Google

        Returns:
            Tuple of (user_data, error_message)
        """
        try:
            # Create flow instance
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri],
                    }
                },
                scopes=[
                    "https://www.googleapis.com/auth/userinfo.profile",
                    "https://www.googleapis.com/auth/userinfo.email",
                    "openid"
                ],
                redirect_uri=self.redirect_uri,
                state=state,
            )

            # Fetch token
            flow.fetch_token(code=code)

            # Get user info from ID token
            credentials = flow.credentials
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                requests.Request(),
                self.client_id
            )

            user_data = {
                "email": id_info.get("email"),
                "name": id_info.get("name"),
                "profile_picture": id_info.get("picture"),
                "google_id": id_info.get("sub")
            }

            return user_data, None

        except Exception as e:
            return None, f"Authentication failed: {str(e)}"

    def create_or_update_user(self, user_data: Dict) -> str:
        """
        Create new user or update existing user in database.

        Args:
            user_data: User information from Google

        Returns:
            User ID string
        """
        email = user_data["email"]
        now = datetime.utcnow()

        # Check if user exists
        existing_user = self.users_collection.find_one({"email": email})

        if existing_user:
            # Update existing user
            self.users_collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "name": user_data["name"],
                        "profile_picture": user_data["profile_picture"],
                        "last_login": now
                    }
                }
            )
            return str(existing_user["_id"])
        else:
            # Create new user
            new_user = {
                "email": email,
                "name": user_data["name"],
                "profile_picture": user_data["profile_picture"],
                "google_id": user_data["google_id"],
                "created_at": now,
                "last_login": now,
                "message_count": 0,
                "tokens_used": 0,
                "preferences": {
                    "default_mode": "Auto",
                    "theme": "light"
                }
            }
            result = self.users_collection.insert_one(new_user)
            return str(result.inserted_id)

    def create_session(self, user_id: str, expiry_days: int = 7) -> str:
        """
        Create a new session for the user.

        Args:
            user_id: User ID
            expiry_days: Number of days until session expires

        Returns:
            Session ID string
        """
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = now + timedelta(days=expiry_days)

        session = {
            "_id": session_id,
            "user_id": user_id,
            "created_at": now,
            "expires_at": expires_at,
            "last_accessed": now
        }

        self.sessions_collection.insert_one(session)
        return session_id

    def validate_session(self, session_id: str) -> Optional[str]:
        """
        Validate a session and return user ID if valid.

        Args:
            session_id: Session ID to validate

        Returns:
            User ID if session is valid, None otherwise
        """
        if not session_id:
            return None

        try:
            session = self.sessions_collection.find_one({"_id": session_id})

            if not session:
                return None

            # Check if session is expired
            if session["expires_at"] < datetime.utcnow():
                # Delete expired session
                self.sessions_collection.delete_one({"_id": session_id})
                return None

            # Update last accessed time
            self.sessions_collection.update_one(
                {"_id": session_id},
                {"$set": {"last_accessed": datetime.utcnow()}}
            )

            return session["user_id"]

        except Exception as e:
            print(f"Session validation error: {e}")
            return None

    def logout(self, session_id: str) -> bool:
        """
        Logout user by deleting their session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.sessions_collection.delete_one({"_id": session_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Logout error: {e}")
            return False

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

    def increment_message_count(self, user_id: str):
        """Increment user's message count."""
        try:
            self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"message_count": 1}}
            )
        except Exception as e:
            print(f"Increment message count error: {e}")

    def increment_token_usage(self, user_id: str, tokens: int):
        """Increment user's token usage."""
        try:
            self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"tokens_used": tokens}}
            )
        except Exception as e:
            print(f"Increment token usage error: {e}")

    def update_user_preferences(self, user_id: str, preferences: Dict):
        """Update user preferences."""
        try:
            self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"preferences": preferences}}
            )
        except Exception as e:
            print(f"Update preferences error: {e}")
