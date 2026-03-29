import os
import sys

# Ensure repo root is on the path so app.py and sub-packages are importable
_here = os.path.dirname(os.path.abspath(__file__))           # netlify/functions/
_repo = os.path.dirname(os.path.dirname(_here))              # repo root
if _repo not in sys.path:
    sys.path.insert(0, _repo)

from app import handler  # Mangum-wrapped FastAPI app
