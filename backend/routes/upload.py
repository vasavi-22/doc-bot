from flask import Blueprint, request, jsonify
import os

from services.document_loader import load_pdf
from services.embeddings import create_embeddings
from services.vector_store import store_vectors

upload_bp = Blueprint("upload", __name__)

UPLOAD_FOLDER = "data/uploads"

# ✅ Ensure folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        # process document
        text_chunks = load_pdf(path)
        embeddings = create_embeddings(text_chunks)
        store_vectors(text_chunks, embeddings)

        return jsonify({
            "message": "File uploaded successfully",
            "filename": file.filename
        })

    except Exception as e:
        print("UPLOAD ERROR:", str(e))
        return jsonify({"error": str(e)}), 500
    

# 📄 Get all documents
@upload_bp.route("/documents", methods=["GET"])
def get_documents():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify({"documents": files})


# ❌ Delete document
@upload_bp.route("/documents/<filename>", methods=["DELETE"])
def delete_document(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(path):
        os.remove(path)
        return jsonify({"message": "Deleted successfully"})
    else:
        return jsonify({"error": "File not found"}), 404