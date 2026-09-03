from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ChatMessage, ChatSession, Document
from app.services.ai_service import generate_response
from app.services import rag_service


chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/dashboard")
@login_required
def dashboard():
    sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
    return render_template("dashboard.html", sessions=sessions, documents=documents)


@chat_bp.route("/chat")
@login_required
def chat_page():
    sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
    session_id = request.args.get("session_id", type=int)
    active_session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first() if session_id else None
    return render_template("chat.html", sessions=sessions, documents=documents, active_session=active_session)


@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def send_message():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    session_id = payload.get("session_id")
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first() if session_id else None
    raw_document_id = payload.get("document_id")
    try:
        document_id = int(raw_document_id) if raw_document_id else None
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid document selection."}), 400
    document = Document.query.filter_by(id=document_id, user_id=current_user.id).first() if document_id else None
    if document_id and document is None:
        return jsonify({"error": "Selected document was not found."}), 404

    if session is None:
        session = ChatSession(user_id=current_user.id, title=message[:150], document_id=document.id if document else None)
        db.session.add(session)
        db.session.flush()
    elif document is not None and session.document_id != document.id:
        session.document_id = document.id

    history = [{"role": item.role, "content": item.content} for item in session.messages]
    context = None
    if session.document_id:
        document = Document.query.filter_by(id=session.document_id, user_id=current_user.id).first()
        if document:
            try:
                context = rag_service.retrieve_context(document.collection_name, message)
            except rag_service.RAGServiceError as error:
                db.session.rollback()
                return jsonify({"error": str(error)}), 422

    result = generate_response(message, history, context)
    db.session.add(ChatMessage(session_id=session.id, role="user", content=message))
    db.session.add(ChatMessage(session_id=session.id, role="assistant", content=result["reply"]))
    db.session.commit()
    return jsonify({**result, "session_id": session.id})