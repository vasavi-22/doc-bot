"""Evaluation runner — orchestrates the full pipeline.

Usage:
    python -m evaluation.run_evaluation              # full eval
    python -m evaluation.run_evaluation --retrieval-only  # skip answer generation/eval
    python -m evaluation.run_evaluation --dataset my_dataset.json

Pipeline:
    1. Load dataset (questions, expected answers, expected docs)
    2. For each question:
       a. Retrieve chunks via hybrid search
       b. Compute retrieval metrics (Recall@K, Precision@K, MRR, Hit Rate)
       c. If not retrieval-only: generate answer via RAG pipeline
       d. LLM-as-a-Judge: score Faithfulness, Relevance, Groundedness
       e. Compute Answer Similarity
    3. Aggregate results and save to database
    4. Save report to reports/latest.json
"""

import json
import uuid
import time
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Ensure backend root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics.retrieval_metrics import evaluate_retrieval
from evaluation.metrics.answer_metrics import answer_similarity
from evaluation.evaluator import evaluate_answer
from services.hybrid_retriever import hybrid_search
from services.reranker import rerank
from services.rag_pipeline import query_rag
from config import Config
from database import save_eval_run, get_connection

DATASET_PATH = Path(__file__).parent / "dataset.json"
REPORTS_DIR = Path(__file__).parent / "reports"
RETRIEVAL_TOP_K = getattr(Config, "RETRIEVAL_TOP_K", 20)
TOP_K_RESULTS = getattr(Config, "TOP_K_RESULTS", 5)


def load_dataset(path=None):
    """Load the evaluation dataset from JSON."""
    path = path or DATASET_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} evaluation questions from {path}")
    return data


def retrieve_for_question(question, top_k=RETRIEVAL_TOP_K):
    """Run hybrid retrieval + reranking for a single question.

    Uses admin role to ensure all documents are searched.

    Returns the pre-reranking matches (for retrieval metrics) and
    post-reranking matches (for context building).
    """
    matches = hybrid_search(question, top_k=top_k, user_role="admin")
    # Apply score threshold
    scored = [m for m in matches if m.get("score", 0) > 0.15]

    if not scored:
        return [], []

    reranked = rerank(question, scored, top_k=TOP_K_RESULTS)
    return scored, reranked


def build_context_from_reranked(reranked):
    """Build a context string and sources list from reranked chunks."""
    context_parts = []
    sources = []
    for match in reranked:
        meta = match.get("metadata", {})
        text = meta.get("text", "")
        fname = meta.get("filename", "Unknown")
        page = meta.get("page_number", "N/A")
        context_parts.append(f"Document: {fname}\nPage: {page}\n\n{text}")
        sources.append({"filename": fname, "page": page})

    context_limit = getattr(Config, "CONTEXT_LIMIT", 3000)
    return "\n\n".join(context_parts)[:context_limit], sources


def run_evaluation(dataset_path=None, retrieval_only=False):
    """Run the full evaluation pipeline.

    Args:
        dataset_path: Optional path to dataset JSON. Defaults to dataset.json.
        retrieval_only: If True, skip answer generation and answer-level metrics.

    Returns:
        dict: Summary of the evaluation run.
    """
    dataset = load_dataset(dataset_path)
    run_id = str(uuid.uuid4())
    run_date = datetime.now(timezone.utc).isoformat()

    all_results = []
    total_start = time.time()

    for i, item in enumerate(dataset):
        qid = item["id"]
        question = item["question"]
        expected_answer = item.get("expected_answer", "")
        expected_docs = item.get("expected_documents", [])
        category = item.get("category", "")

        logger.info(f"[{i+1}/{len(dataset)}] Evaluating: {question[:80]}...")

        try:
            start_time = time.time()

            # Step 1: Retrieve
            pre_rerank, post_rerank = retrieve_for_question(question)

            # Step 2: Retrieval metrics
            retrieval_scores = evaluate_retrieval(pre_rerank, expected_docs)

            # Build context from reranked results
            context, sources = build_context_from_reranked(post_rerank)

            elapsed = round(time.time() - start_time, 3)
            retrieved_docs_json = json.dumps(
                [m.get("metadata", {}).get("filename", "") for m in pre_rerank[:10]]
            )

            result = {
                "id": str(uuid.uuid4()),
                "question_id": qid,
                "question": question,
                "expected_documents": json.dumps(expected_docs),
                "category": category,
                "retrieval_recall_5": retrieval_scores.get("recall@5", 0),
                "retrieval_precision_5": retrieval_scores.get("precision@5", 0),
                "retrieval_mrr": retrieval_scores.get("mrr", 0),
                "retrieval_hit_rate": retrieval_scores.get("hit_rate", 0),
                "latency_seconds": elapsed,
                "retrieved_docs": retrieved_docs_json,
                "expected_answer": expected_answer,
                "answer": "",
                "faithfulness": 0,
                "relevance": 0,
                "groundedness": 0,
                "answer_similarity": 0,
                "error": "",
            }

            # Step 3: Generate answer + evaluate (unless retrieval-only)
            if not retrieval_only and context.strip():
                answer_start = time.time()
                try:
                    rag_result = query_rag(question)
                    if "error" not in rag_result:
                        generated_answer = rag_result.get("answer", "")
                        result["answer"] = generated_answer

                        # Step 4: LLM-as-a-Judge
                        eval_scores = evaluate_answer(question, context, generated_answer)
                        result["faithfulness"] = eval_scores.get("faithfulness", 0)
                        result["relevance"] = eval_scores.get("relevance", 0)
                        result["groundedness"] = eval_scores.get("groundedness", 0)

                        # Step 5: Answer Similarity
                        sim = answer_similarity(generated_answer, expected_answer)
                        result["answer_similarity"] = sim

                        answer_elapsed = round(time.time() - answer_start, 3)
                        result["latency_seconds"] = round(elapsed + answer_elapsed, 3)
                    else:
                        result["error"] = rag_result.get("error", "RAG failed")
                except Exception as e:
                    result["error"] = str(e)
                    logger.error(f"Answer generation failed for {qid}: {e}")

            all_results.append(result)

        except Exception as e:
            logger.error(f"Evaluation failed for {qid}: {e}")
            all_results.append({
                "id": str(uuid.uuid4()),
                "question_id": qid,
                "question": question,
                "expected_documents": json.dumps(expected_docs),
                "category": category,
                "retrieval_recall_5": 0,
                "retrieval_precision_5": 0,
                "retrieval_mrr": 0,
                "retrieval_hit_rate": 0,
                "faithfulness": 0,
                "relevance": 0,
                "groundedness": 0,
                "answer_similarity": 0,
                "answer": "",
                "expected_answer": expected_answer,
                "latency_seconds": 0,
                "retrieved_docs": "[]",
                "error": str(e),
            })

    # Aggregate scores
    total = len(all_results)
    valid_retrieval = [r for r in all_results if r.get("retrieval_recall_5", 0) > 0 or not r.get("error")]
    valid_answer = [r for r in all_results if r.get("faithfulness", 0) > 0 or not r.get("error")]

    summary = {
        "run_id": run_id,
        "run_date": run_date,
        "retriever_version": "hybrid",
        "embedding_model": "all-MiniLM-L6-v2",
        "reranker": "BAAI/bge-reranker-base",
        "num_questions": total,
        "overall_recall_5": round(sum(r["retrieval_recall_5"] for r in all_results) / total, 4) if total else 0,
        "overall_precision_5": round(sum(r["retrieval_precision_5"] for r in all_results) / total, 4) if total else 0,
        "overall_mrr": round(sum(r["retrieval_mrr"] for r in all_results) / total, 4) if total else 0,
        "overall_hit_rate": round(sum(r["retrieval_hit_rate"] for r in all_results) / total, 4) if total else 0,
        "overall_faithfulness": round(sum(r["faithfulness"] for r in valid_answer) / len(valid_answer), 4) if valid_answer else 0,
        "overall_relevance": round(sum(r["relevance"] for r in valid_answer) / len(valid_answer), 4) if valid_answer else 0,
        "overall_groundedness": round(sum(r["groundedness"] for r in valid_answer) / len(valid_answer), 4) if valid_answer else 0,
        "overall_answer_similarity": round(sum(r["answer_similarity"] for r in valid_answer) / len(valid_answer), 4) if valid_answer else 0,
        "avg_latency_seconds": round(sum(r["latency_seconds"] for r in all_results) / total, 3) if total else 0,
        "notes": "retrieval_only" if retrieval_only else "full",
    }

    # Save to database
    try:
        save_eval_run(run_id, summary, all_results)
        logger.info(f"Saved evaluation run {run_id} to database")
    except Exception as e:
        logger.error(f"Failed to save to database: {e}")

    # Save report to disk
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report = {**summary, "results": all_results}
    report_path = REPORTS_DIR / "latest.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Save to history
    history_path = REPORTS_DIR / "history" / f"{run_id}.json"
    with open(history_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    total_time = round(time.time() - total_start, 2)
    logger.info(f"\n{'='*50}")
    logger.info(f"Evaluation complete in {total_time}s")
    logger.info(f"  Questions: {total}")
    logger.info(f"  Recall@5:   {summary['overall_recall_5']:.2%}")
    logger.info(f"  Precision@5: {summary['overall_precision_5']:.2%}")
    logger.info(f"  MRR:        {summary['overall_mrr']:.4f}")
    logger.info(f"  Hit Rate:   {summary['overall_hit_rate']:.2%}")
    if not retrieval_only:
        logger.info(f"  Faithfulness:  {summary['overall_faithfulness']:.2%}")
        logger.info(f"  Relevance:     {summary['overall_relevance']:.2%}")
        logger.info(f"  Groundedness:  {summary['overall_groundedness']:.2%}")
        logger.info(f"  Answer Sim:    {summary['overall_answer_similarity']:.2%}")
    logger.info(f"{'='*50}")

    return summary


if __name__ == "__main__":
    retrieval_only = "--retrieval-only" in sys.argv
    dataset_arg = None
    for arg in sys.argv:
        if arg.startswith("--dataset="):
            dataset_arg = arg.split("=", 1)[1]

    run_evaluation(dataset_path=dataset_arg, retrieval_only=retrieval_only)
