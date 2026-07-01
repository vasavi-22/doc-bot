"""Centralized LangFuse client — singleton pattern.

All tracing in the app goes through this service.
If LangFuse is not configured or unavailable, all calls are no-ops
so the pipeline never breaks.
"""

import os
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_langfuse():
    """Get or create the LangFuse singleton client.

    Returns None if LangFuse is disabled or misconfigured,
    so callers can safely wrap with `if client:`.
    """
    enabled = os.getenv("LANGFUSE_ENABLED", "true").lower() in ("true", "1", "yes")
    if not enabled:
        logger.info("LangFuse is disabled via LANGFUSE_ENABLED env var")
        return None

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        logger.warning("LangFuse not configured: missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY")
        return None

    try:
        from langfuse import Langfuse
        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            # Flush every 10s or 50 events — whichever comes first
            flush_at=50,
            flush_interval=10,
        )
        logger.info(f"LangFuse initialized (host={host})")
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize LangFuse: {e}")
        return None
