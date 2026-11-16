"""
app/core/rate_limit.py
======================
Shared SlowAPI rate limiter singleton.
Defined here (not in main.py) to avoid circular imports when
API routers need to apply @limiter.limit() decorators.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
