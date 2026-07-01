"""
Phase 11 — Graph Assembly

Connects nodes and routers into a directed graph with conditional edges:

    START
      ↓
    rewrite_question
      ↓
    retriever
      ↓
    need_more_search? ←─────────┐
      ├── need_more → retrieve_more ──┘
      └── sufficient
              ↓
          reranker
              ↓
          generator ←──────────┐
              ↓                 │
          validator             │
              ↓                 │
          should_retry? ────────┘
              ↓
             END

This provides agent-like behavior while remaining easy to debug.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from config import Config
from utils.logger import logger

from .state import RAGState
from .nodes import (
    rewrite_question,
    retriever,
    retrieve_more,
    reranker,
    generator,
    validator,
)
from .router import need_more_search, should_retry


def build_rag_graph() -> StateGraph:
    """Build the LangGraph state machine.

    Returns an uncompiled StateGraph ready for optional checkpointing.
    """
    builder = StateGraph(RAGState)

    # ── Register nodes ──
    builder.add_node("rewrite_question", rewrite_question)
    builder.add_node("retriever", retriever)
    builder.add_node("retrieve_more", retrieve_more)
    builder.add_node("reranker", reranker)
    builder.add_node("generator", generator)
    builder.add_node("validator", validator)

    # ── Linear edge: START → rewrite_question → retriever ──
    builder.add_edge(START, "rewrite_question")
    builder.add_edge("rewrite_question", "retriever")

    # ── Conditional edge: retriever → need_more_search? ──
    #   - "sufficient" → reranker
    #   - "need_more" → retrieve_more (which loops back to retriever)
    builder.add_conditional_edges(
        "retriever",
        need_more_search,
        {
            "sufficient": "reranker",
            "need_more": "retrieve_more",
        }
    )

    # ── Loop edge: retrieve_more → retriever ──
    builder.add_edge("retrieve_more", "retriever")

    # ── Linear flow: reranker → generator → validator ──
    builder.add_edge("reranker", "generator")
    builder.add_edge("generator", "validator")

    # ── Conditional edge: validator → should_retry? ──
    #   - "regenerate" → generator (loop back with validation feedback)
    #   - "end" → END
    builder.add_conditional_edges(
        "validator",
        should_retry,
        {
            "regenerate": "generator",
            "end": END,
        }
    )

    return builder


def get_rag_graph() -> StateGraph:
    """Get or create the singleton compiled RAG graph with MemorySaver."""
    if not hasattr(get_rag_graph, "_graph"):
        builder = build_rag_graph()
        memory = MemorySaver()
        get_rag_graph._graph = builder.compile(checkpointer=memory)
        logger.info("LangGraph RAG pipeline compiled successfully")
    return get_rag_graph._graph


def run_rag_pipeline(state: RAGState, config: dict = None) -> RAGState:
    """Run the full RAG pipeline using the LangGraph state machine.

    Args:
        state: Initial state created with create_initial_state().
        config: Optional config dict (recursion_limit, thread_id, etc.).

    Returns:
        Final state after the graph completes.
    """
    graph = get_rag_graph()
    cfg = config or {"recursion_limit": 25}

    # Use a unique thread_id for each invocation
    if "configurable" not in cfg:
        cfg["configurable"] = {}
    if "thread_id" not in cfg["configurable"]:
        import uuid
        cfg["configurable"]["thread_id"] = str(uuid.uuid4())

    result = graph.invoke(state, cfg)
    return result
