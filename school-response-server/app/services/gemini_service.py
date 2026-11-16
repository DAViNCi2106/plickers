"""
app/services/gemini_service.py
==============================
Google Gemini AI service powered by the official google-genai SDK.
Used for:
- Generating quiz questions & answer sets
- AI-assisted student roster parsing and card allocation
- Intelligent response verification from camera scans
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None

def get_gemini_client():
    global _client
    if _client is not None:
        return _client

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set in environment or .env")
        return None

    try:
        from google import genai
        _client = genai.Client(api_key=api_key)
        return _client
    except Exception as exc:
        logger.error(f"Failed to initialize google-genai client: {exc}")
        return None


def generate_content(prompt: str, model: Optional[str] = None) -> Optional[str]:
    """Generates text content using Gemini."""
    client = get_gemini_client()
    if not client:
        return None

    target_model = model or settings.GEMINI_MODEL or "gemini-3.8-flash"
    try:
        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
        )
        return response.text
    except Exception as exc:
        logger.error(f"Gemini generate_content failed ({target_model}): {exc}")
        return None
