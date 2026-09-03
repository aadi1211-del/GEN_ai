import os
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Document
from app.services import rag_service

documents_bp = Blueprint("documents", __name__, template_folder="../templates")


def _allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


@documents_bp.route("/documents")
@login_required
def documents_page():
    docs = Document.query.filter_by(user_id=current_user.id).order_by(
        Document.uploaded_at.desc()
    ).all()
    return render_template("documents.html", documents=docs)


@documents_bp.route("/documents/upload", methods=["POST"])
@login_required
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are supported"}), 400

    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
    file.save(filepath)

    try:
        result = rag_service.ingest_document(filepath, safe_name, current_user.id)
    except rag_service.RAGServiceError as e:
        os.remove(filepath)
        return jsonify({"error": str(e)}), 422
    except Exception as e:  # noqa: BLE001
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Failed to process document: {e}"}), 500

    doc = Document(
        user_id=current_user.id,
        filename=safe_name,
        stored_path=filepath,
        collection_name=result["collection_name"],
        chunk_count=result["chunk_count"],
    )
    db.session.add(doc)
    db.session.commit()

    return jsonify(doc.to_dict()), 201


@documents_bp.route("/documents/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_document(doc_id):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()

    rag_service.delete_document_collection(doc.collection_name)
    if os.path.exists(doc.stored_path):
        os.remove(doc.stored_path)

    db.session.delete(doc)
    db.session.commit()
    return jsonify({"success": True})