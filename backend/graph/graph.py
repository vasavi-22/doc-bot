"""
Phase 12 — Multi-Agent Graph Assembly

Connects specialized agents into a directed graph with conditional edges:

    START
      ↓
    query_agent (Query Understanding)
      ↓
    question_rewriter (history-aware rewrite)
      ↓
    retrieval_agent
      ↓
    need_more_search? ←─────────────┐
      ├── need_more → retrieve_more ──┘
      └── sufficient
              ↓
          metadata_filter
              ↓
          reranker_agent
              ↓
          verification_agent
              ↓
          verification_result?
              ├── abstain → END (early exit)
              └── verified
                      ↓
                  memory_manager
                      ↓
                  answer_agent ←──────────┐
                      ↓                    │
                  citation_agent           │
                      ↓                    │
                  validator                │
                      ↓                    │
                  should_retry? ───────────┘
                      ↓
                     END

Each agent has a single responsibility and is independently observable.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from config import Config
from utils.logger import logger

from .state import RAGState
from .nodes import (
    query_agent,
    question_rewriter,
    retrieval_agent,
    retrieve_more,
    metadata_filter,
    reranker_agent,
    verification_agent,
    memory_manager,
    answer_agent,
    citation_agent,
    validator,
)
from .router import need_more_search, verification_result, should_retry


# ── Node name constants ─────────────────────────────────────────────────────

NODE_QUERY = "query_agent"
NODE_REWRITER = "question_rewriter"
NODE_RETRIEVAL = "retrieval_agent"
NODE_RETRIEVE_MORE = "retrieve_more"
NODE_FILTER = "metadata_filter"
NODE_RERANKER = "reranker_agent"
NODE_VERIFICATION = "verification_agent"
NODE_MEMORY = "memory_manager"
NODE_ANSWER = "answer_agent"
NODE_CITATION = "citation_agent"
NODE_VALIDATOR = "validator"


def build_rag_graph() -> StateGraph:
    """Build the multi-agent LangGraph state machine."""
    builder = StateGraph(RAGState)

    # ── Register agent nodes ──
    builder.add_node(NODE_QUERY, query_agent)
    builder.add_node(NODE_REWRITER, question_rewriter)
    builder.add_node(NODE_RETRIEVAL, retrieval_agent)
    builder.add_node(NODE_RETRIEVE_MORE, retrieve_more)
    builder.add_node(NODE_FILTER, metadata_filter)
    builder.add_node(NODE_RERANKER, reranker_agent)
    builder.add_node(NODE_VERIFICATION, verification_agent)
    builder.add_node(NODE_MEMORY, memory_manager)
    builder.add_node(NODE_ANSWER, answer_agent)
    builder.add_node(NODE_CITATION, citation_agent)
    builder.add_node(NODE_VALIDATOR, validator)

    # ── Flow: START → Query Agent → Rewriter → Retrieval Agent ──
    builder.add_edge(START, NODE_QUERY)
    builder.add_edge(NODE_QUERY, NODE_REWRITER)
    builder.add_edge(NODE_REWRITER, NODE_RETRIEVAL)

    # ── Conditional: Retrieval Agent → Need More Search? ──
    builder.add_conditional_edges(
        NODE_RETRIEVAL,
        need_more_search,
        {
            "sufficient": NODE_FILTER,
            "need_more": NODE_RETRIEVE_MORE,
        }
    )

    # ── Loop: retrieve_more → retrieval_agent ──
    builder.add_edge(NODE_RETRIEVE_MORE, NODE_RETRIEVAL)

    # ── Flow: Filter → Reranker Agent → Verification Agent ──
    builder.add_edge(NODE_FILTER, NODE_RERANKER)
    builder.add_edge(NODE_RERANKER, NODE_VERIFICATION)

    # ── Conditional: Verification → Verified or Abstain? ──
    builder.add_conditional_edges(
        NODE_VERIFICATION,
        verification_result,
        {
            "verified": NODE_MEMORY,
            "abstain": END,
        }
    )

    # ── Flow: Memory → Answer Agent → Citation Agent → Validator ──
    builder.add_edge(NODE_MEMORY, NODE_ANSWER)
    builder.add_edge(NODE_ANSWER, NODE_CITATION)
    builder.add_edge(NODE_CITATION, NODE_VALIDATOR)

    # ── Conditional: Validator → Retry or End? ──
    builder.add_conditional_edges(
        NODE_VALIDATOR,
        should_retry,
        {
            "regenerate": NODE_ANSWER,
            "end": END,
        }
    )

    return builder


def get_rag_graph() -> StateGraph:
    """Get or create the singleton compiled graph."""
    if not hasattr(get_rag_graph, "_graph"):
        builder = build_rag_graph()
        memory = MemorySaver()
        get_rag_graph._graph = builder.compile(checkpointer=memory)
        logger.info("Phase 12 Multi-Agent graph compiled successfully")
    return get_rag_graph._graph


def run_rag_pipeline(state: RAGState, config: dict = None) -> RAGState:
    """Run the multi-agent RAG pipeline.

    Args:
        state: Initial state from create_initial_state().
        config: Optional config with recursion_limit, thread_id.

    Returns:
        Final state after all agents complete.
    """
    graph = get_rag_graph()
    cfg = config or {"recursion_limit": 25}

    if "configurable" not in cfg:
        cfg["configurable"] = {}
    if "thread_id" not in cfg["configurable"]:
        import uuid
        cfg["configurable"]["thread_id"] = str(uuid.uuid4())

    result = graph.invoke(state, cfg)
    return result
