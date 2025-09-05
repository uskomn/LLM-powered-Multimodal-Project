from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from backend.app.services.ingest_service import ingest_document
from backend.app.utils.file_loader import read_file_content
from backend.app.core.security import require_role

ingest_bp = Blueprint("ingest", __name__, url_prefix="/ingest")

@ingest_bp.route("/upload", methods=["POST"])
@require_role(['admin','user'],action_desc="上传文件")
def upload_document():
    user_id=get_jwt_identity()
    file = request.files["file"]
    content = read_file_content(file)
    doc_ids = ingest_document(file, content, user_id)
    return jsonify({"message": "文档上传成功", "doc_ids": doc_ids})
