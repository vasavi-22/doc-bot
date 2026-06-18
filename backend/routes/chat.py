from flask import Blueprint, request, jsonify
from services.rag_pipeline import query_rag
from utils.logger import logger

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        # Validate input
        if not data or "message" not in data:
            logger.info("Chat request received")
            return jsonify({"error": "Message is required"}), 400

        question = data["message"]

        document_id = data.get("document_id")
        category = data.get("category")
        owner = data.get("owner")

        # Get AI response
        answer = query_rag(question=question, document_id=document_id, category=category, owner=owner)

        # return jsonify({
        #     "success": True,
        #     "response": answer
        # })

        return jsonify(answer)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500