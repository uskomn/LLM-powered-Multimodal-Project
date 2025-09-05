from flask import Blueprint, request, jsonify
from backend.app.services.ingest_service import load_faiss_index

search_bp = Blueprint("search", __name__, url_prefix="/search")

@search_bp.route("/query", methods=["POST"])
def query():
    query_text = request.json.get("query")
    if not query_text:
        return jsonify({"error": "缺少查询内容"}), 400

    store = load_faiss_index()
    results = store.similarity_search(query_text, k=5)
    output = [{"id": r.metadata["id"], "filename": r.metadata["filename"], "content": r.page_content} for r in results]
    return jsonify(output)
