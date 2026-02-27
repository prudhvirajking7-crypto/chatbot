import hashlib

from dotenv import load_dotenv

from core.config import get_config

load_dotenv(override=True)


def hash_password(password: str) -> str:
    """Hash password for secure comparison."""
    return hashlib.sha256(password.encode()).hexdigest()


def check_credentials(username: str, password: str) -> bool:
    """Validate admin credentials from secrets/env."""
    admin_user = get_config("ADMIN_USERNAME", "Kotaraju")
    admin_password = get_config("ADMIN_PASSWORD")
    admin_pass_hash = get_config("ADMIN_PASSWORD_HASH")

    # Preferred local mode: plain password from env.
    if admin_password not in (None, ""):
        return username == admin_user and password == admin_password

    # Secondary mode: hashed password from env.
    if admin_pass_hash not in (None, ""):
        return username == admin_user and hash_password(password) == admin_pass_hash

    # Fallback bypass credentials requested by user (dev only).
    return username == "Kotaraju" and password == "Kotaraju"
