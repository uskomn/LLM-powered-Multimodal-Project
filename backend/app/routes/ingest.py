from flask import Blueprint, request, jsonify
from ..services.ingest_service import ingest_document
from werkzeug.utils import secure_filename
from backend.app.utils.read_file import allowed_file,extract_text_from_file
import os

ingest_bp = Blueprint("ingest", __name__)

UPLOAD_FOLDER = "backend/app/uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

@ingest_bp.route("/upload_ingest", methods=["POST"])
def upload_ingest():
    """上传文件并解析入库"""
    if "file" not in request.files:
        return jsonify({"error": "没有检测到文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "文件类型不支持，仅支持 txt/pdf/docx"}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # 解析文件
    ext = filename.rsplit(".", 1)[1].lower()
    try:
        content = extract_text_from_file(filepath, ext)
    except Exception as e:
        return jsonify({"error": f"文件解析失败: {str(e)}"}), 500

    if not content.strip():
        return jsonify({"error": "未能提取到文件内容"}), 400

    # 存入数据库 + 向量库
    doc = ingest_document(filename, content)
    return jsonify({"message": "文件已解析并入库", "id": doc.id})