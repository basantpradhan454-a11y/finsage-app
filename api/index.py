"""
Vercel serverless entrypoint — wraps the FastAPI app from server.py
so Vercel's Python runtime can serve it.
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app  # noqa: E402

# Vercel's Python (ASGI) runtime looks for a variable named `app`
