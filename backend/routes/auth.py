from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import jwt_required
from services.auth_service import register_user, login_user, get_current_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")

        success, result = register_user(name, email, password)

        if not success:
            return jsonify(result), 400

        return jsonify(result), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login and receive a JWT token."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        email = data.get("email", "").strip()
        password = data.get("password", "")

        success, result = login_user(email, password)

        if not success:
            return jsonify(result), 401

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me():
    """Get current authenticated user info."""
    try:
        user = get_current_user(g.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": user}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
