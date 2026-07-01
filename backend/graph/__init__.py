"""
Multi-Agent RAG Pipeline — Phase 12

Each agent has a single responsibility:
  Query Agent → Retrieval Agent → Metadata Filter → Reranker Agent
  → Verification Agent → Memory Manager → Answer Agent → Citation Agent

Supports conditional execution, early termination on insufficient evidence,
and per-agent LangFuse observability.
"""

from .graph import build_rag_graph, get_rag_graph, run_rag_pipeline
from .state import create_initial_state, RAGState

__all__ = [
    "build_rag_graph",
    "get_rag_graph",
    "run_rag_pipeline",
    "create_initial_state",
    "RAGState",
]

# Backward-compatible legacy aliases (Phase 11 -> Phase 12)
create_graph = build_rag_graph
