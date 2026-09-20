"""Vercel Serverless Function entrypoint for HireFlow FastAPI app."""

import sys
from pathlib import Path

# Add project root directory to Python path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from hireflow.api.routes import app

# Vercel looks for `app` ASGI instance
__all__ = ["app"]
