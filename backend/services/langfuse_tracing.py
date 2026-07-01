"""Tracing wrappers that instrument the RAG pipeline with LangFuse spans.

All functions are safe to call even if LangFuse is not configured — they
become no-ops that still return the normal result.

Usage in pipeline code:
    from services.langfuse_tracing import trace_embedding, trace_retrieval, ...
    with trace_embedding(client, trace, question) as span:
        embedding = model.encode(question)
"""

import time
import logging
import json

logger = logging.getLogger(__name__)


def safe_trace(client, name, **kwargs):
    """Create a LangFuse trace safely — returns a no-op if client is None."""
    if client is None:
        return _NoOpSpan()
    try:
        return client.trace(name=name, **kwargs)
    except Exception as e:
        logger.warning(f"LangFuse trace creation failed: {e}")
        return _NoOpSpan()


def safe_span(parent, name, **kwargs):
    """Create a LangFuse span safely — returns a no-op if parent is None."""
    if parent is None or isinstance(parent, _NoOpSpan):
        return _NoOpSpan()
    try:
        if hasattr(parent, 'span'):
            return parent.span(name=name, **kwargs)
        return parent.span(name=name, **kwargs)
    except Exception as e:
        logger.warning(f"LangFuse span creation failed: {e}")
        return _NoOpSpan()


def safe_generation(parent, name, **kwargs):
    """Create a LangFuse generation span safely — no-op if parent is None."""
    if parent is None or isinstance(parent, _NoOpSpan):
        return _NoOpSpan()
    try:
        return parent.generation(name=name, **kwargs)
    except Exception as e:
        logger.warning(f"LangFuse generation creation failed: {e}")
        return _NoOpSpan()


def end_span(span):
    """End a LangFuse span safely."""
    if span is not None and not isinstance(span, _NoOpSpan):
        try:
            span.end()
        except Exception:
            pass


def end_trace(trace):
    """End a LangFuse trace safely."""
    if trace is not None and not isinstance(trace, _NoOpSpan):
        try:
            trace.end()
        except Exception:
            pass


class _NoOpSpan:
    """No-op context manager that replaces LangFuse spans when client is off."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def end(self):
        pass

    def update(self, **kwargs):
        pass

    def generation(self, **kwargs):
        return self

    def span(self, **kwargs):
        return self
