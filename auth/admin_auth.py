import hashlib
from pathlib import Path

from dotenv import load_dotenv

from core.config import get_config

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=True)


def hash_password(password: str) -> str:
    """Hash password for secure comparison."""
    return hashlib.sha256(password.encode()).hexdigest()


def check_credentials(username: str, password: str) -> bool:
    """Validate admin credentials from environment variables."""
    admin_user = get_config("ADMIN_USERNAME")
    admin_password = get_config("ADMIN_PASSWORD")
    admin_pass_hash = get_config("ADMIN_PASSWORD_HASH")

    if not admin_user:
        return False

    # Preferred: plain password from env
    if admin_password not in (None, ""):
        return username == admin_user and password == admin_password

    # Secondary: hashed password from env
    if admin_pass_hash not in (None, ""):
        return username == admin_user and hash_password(password) == admin_pass_hash

    return False
