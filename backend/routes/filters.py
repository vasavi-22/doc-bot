from flask import Blueprint, jsonify, g
from middleware.auth_middleware import jwt_required
from database import get_user_categories, get_user_tags, get_documents_by_user
from utils.logger import logger

filters_bp = Blueprint("filters", __name__, url_prefix="/api/filters")


@filters_bp.route("", methods=["GET"])
@jwt_required
def get_filters():
    """Return available metadata filters for the current user.

    Returns categories, tags, and documents the user can filter by.
    """
    try:
        user_id = g.user_id
        categories = get_user_categories(user_id)
        tags = get_user_tags(user_id)
        doc_rows = get_documents_by_user(user_id)

        documents = []
        for row in doc_rows:
            raw_total_pages = row[9] if len(row) > 9 else 0
            documents.append({
                "document_id": row[0],
                "filename": row[2],
                "original_filename": row[3],
                "category": row[7],
                "tags": row[8],
                "total_pages": raw_total_pages or row[5]
            })

        return jsonify({
            "categories": categories,
            "tags": tags,
            "documents": documents
        }), 200

    except Exception as e:
        logger.error(f"Get filters failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
