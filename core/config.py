import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


@lru_cache(maxsize=1)
def _load_secrets() -> Dict[str, Any]:
    """
    Load secrets from common local `secrets.toml` locations.
    """
    if tomllib is None:
        return {}

    home_secret_path = Path.home() / ".streamlit" / "secrets.toml"
    project_secret_path = Path.cwd() / ".streamlit" / "secrets.toml"

    for path in (project_secret_path, home_secret_path):
        if not path.exists():
            continue
        try:
            with path.open("rb") as fh:
                data = tomllib.load(fh)
                if isinstance(data, dict):
                    return data
        except Exception:
            continue
    return {}


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    secrets_data = _load_secrets()
    value = secrets_data.get(key, default)
    if value is None:
        return default
    return str(value)


def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    env_value = os.getenv(key)
    if env_value not in (None, ""):
        return env_value

    secret_value = get_secret(key)
    if secret_value not in (None, ""):
        return secret_value

    return default
