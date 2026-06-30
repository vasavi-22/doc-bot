from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import jwt_required, require_role
from database import get_all_users, get_user_by_id, update_user_role
from utils.logger import logger

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/users", methods=["GET"])
@jwt_required
@require_role("admin")
def list_users():
    """List all users (admin only)."""
    try:
        users = get_all_users()
        # Strip password_hash from response
        safe_users = []
        for user in users:
            safe_users.append({
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "created_at": user["created_at"]
            })
        return jsonify({"users": safe_users}), 200
    except Exception as e:
        logger.error(f"List users failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/users/<user_id>/role", methods=["PATCH"])
@jwt_required
@require_role("admin")
def change_user_role(user_id):
    """Change a user's role (admin only)."""
    try:
        data = request.get_json()
        if not data or "role" not in data:
            return jsonify({"error": "Role is required"}), 400

        new_role = data["role"].strip().lower()
        if new_role not in ("admin", "employee"):
            return jsonify({"error": "Role must be 'admin' or 'employee'"}), 400

        # Don't allow changing own role (prevent lockout)
        if user_id == g.user_id:
            return jsonify({"error": "Cannot change your own role"}), 400

        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        update_user_role(user_id, new_role)
        logger.info(f"Admin {g.user_id} changed user {user_id} role to {new_role}")

        return jsonify({
            "message": f"User role updated to {new_role}",
            "user": {
                "id": user_id,
                "name": user["name"],
                "email": user["email"],
                "role": new_role
            }
        }), 200

    except Exception as e:
        logger.error(f"Change role failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/users/<user_id>", methods=["DELETE"])
@jwt_required
@require_role("admin")
def delete_user(user_id):
    """Delete a user (admin only)."""
    try:
        if user_id == g.user_id:
            return jsonify({"error": "Cannot delete your own account"}), 400

        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        # Delete user's data
        cursor.execute("DELETE FROM messages WHERE chat_id IN (SELECT id FROM chats WHERE user_id = ?)", (user_id,))
        cursor.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM chunks WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM documents WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        logger.info(f"Admin {g.user_id} deleted user {user_id}")
        return jsonify({"message": "User deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Delete user failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
