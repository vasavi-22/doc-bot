"""API routes for the Phase 9 Evaluation Dashboard.

Endpoints:
    GET  /api/evaluation/runs       — List all evaluation runs
    GET  /api/evaluation/runs/<id>  — Get a single run with results
    POST /api/evaluation/run        — Trigger a new evaluation run (admin only)
"""

import uuid
import logging
from flask import Blueprint, jsonify, g
from middleware.auth_middleware import jwt_required, require_role
from database import get_eval_runs, get_eval_run
from utils.logger import logger

evaluation_bp = Blueprint("evaluation", __name__, url_prefix="/api/evaluation")


@evaluation_bp.route("/runs", methods=["GET"])
@jwt_required
def list_runs():
    """Get recent evaluation runs."""
    try:
        runs = get_eval_runs(limit=20)
        return jsonify({"runs": runs}), 200
    except Exception as e:
        logger.error(f"Failed to list evaluation runs: {e}")
        return jsonify({"error": str(e)}), 500


@evaluation_bp.route("/runs/<run_id>", methods=["GET"])
@jwt_required
def get_run(run_id):
    """Get a single evaluation run with its per-question results."""
    try:
        run = get_eval_run(run_id)
        if not run:
            return jsonify({"error": "Evaluation run not found"}), 404
        return jsonify({"run": run}), 200
    except Exception as e:
        logger.error(f"Failed to get evaluation run: {e}")
        return jsonify({"error": str(e)}), 500


@evaluation_bp.route("/run", methods=["POST"])
@jwt_required
@require_role("admin")
def trigger_run():
    """Trigger a new evaluation run (admin only, runs in foreground for now)."""
    try:
        from evaluation.run_evaluation import run_evaluation
        import threading

        run_id = str(uuid.uuid4())

        def _run():
            try:
                run_evaluation()
            except Exception as e:
                logger.error(f"Background evaluation failed: {e}")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return jsonify({
            "message": "Evaluation started in background",
            "run_id": run_id
        }), 202

    except Exception as e:
        logger.error(f"Failed to trigger evaluation: {e}")
        return jsonify({"error": str(e)}), 500
