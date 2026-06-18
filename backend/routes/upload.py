from flask import Blueprint, request, jsonify
import os

from services.document_loader import load_pdf
from services.embeddings import create_embeddings
from services.vector_store import store_vectors
from config import Config
from utils.logger import logger
from werkzeug.utils import secure_filename
import uuid
from services.document_metadata import save_document_metadata
from services.chunk_metadata import build_chunk_metadata
from database import save_chunks

upload_bp = Blueprint("upload", __name__)

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
MAX_FILE_SIZE_MB = Config.MAX_FILE_SIZE_MB

# Ensure folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error":"Only PDF files allowed"}),400

        safe_filename = secure_filename(file.filename)
        unique_filename = (f"{uuid.uuid4()}_{safe_filename}")
        path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(path)

        # process document
        
        chunks = load_pdf(path)
        texts = [c["text"] for c in chunks]

        document_id = str(uuid.uuid4())

        metadata_list = build_chunk_metadata(
            chunks=chunks,
            document_id=document_id,
            filename=safe_filename,
            owner="default",
            category="general"
        )
        embeddings = create_embeddings(texts)
        store_vectors(
            texts,
            embeddings,
            metadata_list
        )
        save_document_metadata(
            document_id=document_id,
            filename=unique_filename,
            chunks=len(texts),
            owner="default",
            category="general",
            tags=""
        )

        chunk_records = []

        for i, chunk in enumerate(chunks):

            metadata = metadata_list[i]

            chunk_records.append((
                f"{metadata['document_id']}_{i}",
                metadata["document_id"],
                chunk["text"],
                metadata.get("page_number"),
                metadata.get("filename"),
                metadata.get("owner"),
                metadata.get("category")
            ))

        save_chunks(chunk_records)

        return jsonify({
            "message": "File uploaded successfully",
            "document_id": document_id,
            "filename": unique_filename
        })

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({
            "error": str(e)
        }), 500
    
ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".",1)[1].lower()
        in ALLOWED_EXTENSIONS
    )

# Get all documents
@upload_bp.route("/documents", methods=["GET"])
def get_documents():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify({"documents": files})


# Delete document
@upload_bp.route("/documents/<filename>", methods=["DELETE"])
def delete_document(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(path):
        os.remove(path)
        return jsonify({"message": "Deleted successfully"})
    else:
        return jsonify({"error": "File not found"}), 404