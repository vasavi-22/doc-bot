import json
from flask import Blueprint, jsonify, g
from middleware.auth_middleware import jwt_required
from database import get_user_categories, get_user_tags, get_documents_by_user, get_connection
from utils.logger import logger

filters_bp = Blueprint("filters", __name__, url_prefix="/api/filters")


def _get_role_visible_documents(user_role, user_id):
    """Get documents that the user can see based on their role.
    
    Admins can see all documents. Employees can only see documents
    where their role is in the allowed_roles list OR they are the owner.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if user_role == "admin":
            # Admin sees all documents (across all users)
            cursor.execute("""
                SELECT document_id, user_id, filename, original_filename, upload_time,
                       chunks, owner, category, tags, total_pages, allowed_roles
                FROM documents ORDER BY upload_time DESC
            """)
        else:
            # Employee sees only their own documents
            cursor.execute("""
                SELECT document_id, user_id, filename, original_filename, upload_time,
                       chunks, owner, category, tags, total_pages, allowed_roles
                FROM documents
                WHERE user_id = ?
                ORDER BY upload_time DESC
            """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception:
        conn.close()
        return []


@filters_bp.route("", methods=["GET"])
@jwt_required
def get_filters():
    """Return available metadata filters for the current user.

    Returns categories, tags, and documents the user can filter by.
    Admins see all documents. Employees see role-accessible documents.
    """
    try:
        user_id = g.user_id
        user_role = g.user_role
        
        # ── Phase 8: RBAC — role-aware document listing ──
        doc_rows = _get_role_visible_documents(user_role, user_id)
        
        # Extract categories and tags from the visible documents
        categories = sorted(set(row[7] for row in doc_rows if row[7] and row[7] != "general"))
        
        all_tags = set()
        for row in doc_rows:
            tags_str = row[8]
            if tags_str:
                for tag in tags_str.split(","):
                    tag = tag.strip()
                    if tag:
                        all_tags.add(tag)
        tags = sorted(all_tags)

        documents = []
        for row in doc_rows:
            raw_total_pages = row[9] if len(row) > 9 else 0
            raw_allowed_roles = row[10] if len(row) > 10 else None
            try:
                allowed_roles = json.loads(raw_allowed_roles) if raw_allowed_roles else ["admin", "employee"]
            except (json.JSONDecodeError, TypeError):
                allowed_roles = ["admin", "employee"]
            
            documents.append({
                "document_id": row[0],
                "filename": row[2],
                "original_filename": row[3],
                "category": row[7],
                "tags": row[8],
                "total_pages": raw_total_pages or row[5],
                "allowed_roles": allowed_roles
            })

        return jsonify({
            "categories": categories,
            "tags": tags,
            "documents": documents,
            "user_role": user_role
        }), 200

    except Exception as e:
        logger.error(f"Get filters failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
