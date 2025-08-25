from flask import Blueprint, request, jsonify
from backend.app.services.retrieval_service import vector_store

retrieval_bp = Blueprint("retrieval_bp", __name__)

@retrieval_bp.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        raw_results = vector_store.search(query, top_k=5)

        # 去重
        seen_ids = set()
        results = []
        for doc in raw_results:
            if doc["id"] in seen_ids:
                continue
            seen_ids.add(doc["id"])
            results.append(doc)

        return jsonify({"results": results}), 200
    except Exception as e:
        return jsonify({
            "error": "搜索失败",
            "details": str(e)
        }), 500
