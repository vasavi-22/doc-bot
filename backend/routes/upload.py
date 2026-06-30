import json
import sqlite3
from flask import Blueprint, request, jsonify, send_from_directory, g
import os

from services.document_loader import load_pdf
from services.embeddings import create_embeddings
from services.vector_store import store_vectors
from config import Config
from utils.logger import logger
from werkzeug.utils import secure_filename
import uuid
from services.chunk_metadata import build_chunk_metadata
from database import save_chunks, save_document_metadata, get_documents_by_user, delete_document_meta, get_connection
from middleware.auth_middleware import jwt_required, require_role
from pypdf import PdfReader

upload_bp = Blueprint("upload", __name__)

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
MAX_FILE_SIZE_MB = Config.MAX_FILE_SIZE_MB

# Ensure base folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def get_user_upload_folder(user_id):
    """Get or create user-specific upload folder."""
    folder = os.path.join(UPLOAD_FOLDER, f"user_{user_id}")
    os.makedirs(folder, exist_ok=True)
    return folder


@upload_bp.route("/upload", methods=["POST"])
@jwt_required
def upload_file():
    try:
        user_id = g.user_id
        user_role = g.user_role

        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files allowed"}), 400

        safe_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{safe_filename}"

        # ── Phase 8: RBAC — determine allowed_roles for document ──
        allowed_roles_raw = request.form.get("allowed_roles", "")
        if allowed_roles_raw:
            try:
                allowed_roles = json.loads(allowed_roles_raw)
                if not isinstance(allowed_roles, list):
                    allowed_roles = ["admin", "employee"]
            except (json.JSONDecodeError, TypeError):
                allowed_roles = ["admin", "employee"]
        else:
            # Default: shared with all roles
            allowed_roles = ["admin", "employee"]

        # Store in user-specific folder
        user_folder = get_user_upload_folder(user_id)
        path = os.path.join(user_folder, unique_filename)
        file.save(path)

        # Process document
        chunks = load_pdf(path)
        texts = [c["text"] for c in chunks]

        # Count actual PDF pages
        total_pages = 0
        try:
            reader = PdfReader(path)
            total_pages = len(reader.pages)
        except Exception:
            # Fallback: derive from chunk page numbers
            if chunks:
                total_pages = max(c["page_number"] for c in chunks)

        document_id = str(uuid.uuid4())

        metadata_list = build_chunk_metadata(
            chunks=chunks,
            document_id=document_id,
            filename=safe_filename,
            owner=user_id,
            category="general",
            user_id=user_id,
            tags="",
            allowed_roles=allowed_roles
        )
        embeddings = create_embeddings(texts)
        store_vectors(
            texts,
            embeddings,
            metadata_list
        )
        save_document_metadata(
            document_id=document_id,
            user_id=user_id,
            filename=unique_filename,
            original_filename=safe_filename,
            chunks=len(texts),
            owner=user_id,
            category="general",
            tags="",
            total_pages=total_pages,
            allowed_roles=allowed_roles
        )

        chunk_records = []

        for i, chunk in enumerate(chunks):
            metadata = metadata_list[i]
            chunk_records.append((
                f"{metadata['document_id']}_{i}",
                metadata["document_id"],
                user_id,
                chunk["text"],
                metadata.get("page_number"),
                metadata.get("filename"),
                user_id,
                metadata.get("category")
            ))

        save_chunks(chunk_records)

        return jsonify({
            "message": "File uploaded successfully",
            "document_id": document_id,
            "filename": unique_filename,
            "allowed_roles": allowed_roles
        })

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/documents", methods=["GET"])
@jwt_required
def get_documents():
    """Get documents for the authenticated user.
    
    Admins see all documents. Employees see their own documents.
    """
    try:
        user_id = g.user_id
        user_role = g.user_role
        
        if user_role == "admin":
            # Admin sees all documents
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT document_id, user_id, filename, original_filename, upload_time,
                           chunks, owner, category, tags, total_pages, allowed_roles
                    FROM documents ORDER BY upload_time DESC
                """)
            except sqlite3.OperationalError:
                cursor.execute("""
                    SELECT document_id, user_id, filename, original_filename, upload_time,
                           chunks, owner, category, tags, chunks as total_pages, '[]' as allowed_roles
                    FROM documents ORDER BY upload_time DESC
                """)
            rows = cursor.fetchall()
            conn.close()
        else:
            rows = get_documents_by_user(user_id)

        docs = []
        for row in rows:
            raw_total_pages = row[9] if len(row) > 9 else 0
            doc = {
                "document_id": row[0],
                "filename": row[2],
                "original_filename": row[3],
                "upload_time": row[4],
                "chunks": row[5],
                "category": row[7] if len(row) > 7 else None,
                "total_pages": raw_total_pages or row[5]
            }
            docs.append(doc)

        return jsonify({"documents": docs})

    except Exception as e:
        logger.error(f"Get documents failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/documents/<document_id>", methods=["GET"])
@jwt_required
def view_document(document_id):
    """View/download a document."""
    try:
        user_role = g.user_role

        # Look up document by ID directly
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT document_id, user_id, filename FROM documents WHERE document_id = ?",
            (document_id,)
        )
        target = cursor.fetchone()
        conn.close()

        if not target:
            return jsonify({"error": "Document not found"}), 404

        doc_user_id = target[1]
        filename = target[2]

        # Check access: admin can view any doc, others must have matching role
        if user_role != "admin":
            # Verify this user can access this document (by owner or role)
            if doc_user_id != g.user_id:
                return jsonify({"error": "Not authorized to view this document"}), 403

        user_folder = get_user_upload_folder(doc_user_id)
        path = os.path.join(user_folder, filename)

        if not os.path.exists(path):
            return jsonify({"error": "File not found on disk"}), 404

        return send_from_directory(user_folder, filename)

    except Exception as e:
        logger.error(f"View document failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/documents/<document_id>", methods=["DELETE"])
@jwt_required
@require_role("admin")
def delete_document(document_id):
    """Delete a document. Admin only."""
    try:
        # Admin can look up any document directly
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT document_id, user_id, filename FROM documents WHERE document_id = ?""",
            (document_id,)
        )
        target = cursor.fetchone()
        conn.close()

        if not target:
            return jsonify({"error": "Document not found"}), 404

        filename = target[2]
        doc_user_id = target[1]
        user_folder = get_user_upload_folder(doc_user_id)
        path = os.path.join(user_folder, filename)

        if os.path.exists(path):
            os.remove(path)

        # Delete from database
        delete_document_meta(document_id)

        return jsonify({"message": "Deleted successfully"})

    except Exception as e:
        logger.error(f"Delete document failed: {str(e)}")
        return jsonify({"error": str(e)}), 500