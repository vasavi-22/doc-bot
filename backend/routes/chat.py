from flask import Blueprint, request, jsonify
from services.rag_pipeline import query_rag

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        # ✅ Validate input
        if not data or "message" not in data:
            return jsonify({"error": "Message is required"}), 400

        question = data["message"]

        # 🔥 Get AI response
        answer = query_rag(question)

        return jsonify({
            "success": True,
            "response": answer
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500