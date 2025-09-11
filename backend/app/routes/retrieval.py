from flask import Blueprint, request, jsonify
from backend.app.services.ingest_service import load_faiss_index
from rank_bm25 import BM25Okapi
import numpy as np
import jieba
from sentence_transformers import SentenceTransformer, util

search_bp = Blueprint("search", __name__, url_prefix="/search")

encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def rerank_and_fuse(query: str, results, top_k: int = 5):
    """
    对检索结果进行文档重排序 + 上下文融合
    :param query: 用户查询
    :param results: FAISS 检索得到的文档对象列表
    :param top_k: 返回文档数量
    :return: 融合后的文档对象列表
    """
    docs = [r.page_content for r in results]

    # === BM25 排序 ===
    tokenized_corpus = [list(jieba.cut(doc)) for doc in docs]

    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(list(jieba.cut(query)))

    # === BERT 向量相似度 ===
    query_vec = encoder.encode(query, convert_to_tensor=True)
    doc_vecs = encoder.encode(docs, convert_to_tensor=True)
    cosine_scores = util.cos_sim(query_vec, doc_vecs).cpu().numpy().flatten()

    # === 融合打分 ===
    fused_scores = 0.5 * bm25_scores + 0.5 * cosine_scores

    # === 重新排序 ===
    ranked_idx = np.argsort(fused_scores)[::-1][:top_k]
    ranked_results = [results[i] for i in ranked_idx]

    # === 上下文融合 ===
    fused_results = []
    skip_idx = set()
    for i, r in enumerate(ranked_results):
        if i in skip_idx:
            continue
        merged_content = [r.page_content]
        for j in range(i + 1, len(ranked_results)):
            sim = util.cos_sim(
                encoder.encode(r.page_content, convert_to_tensor=True),
                encoder.encode(ranked_results[j].page_content, convert_to_tensor=True)
            ).item()
            if sim > 0.8:  # 阈值可调
                merged_content.append(ranked_results[j].page_content)
                skip_idx.add(j)
        # 合并文本
        r.page_content = " ".join(merged_content)
        fused_results.append(r)

    return fused_results

@search_bp.route("/query_advanced", methods=["POST"])
def query_advanced():
    """
    改进版 RAG 检索接口：带 BM25 + 向量融合排序 & 上下文融合
    """
    query_text = request.json.get("query")
    if not query_text:
        return jsonify({"error": "缺少查询内容"}), 400

    store = load_faiss_index()
    results = store.similarity_search(query_text, k=10)  # 先取更多候选

    # 融合排序 + 上下文融合
    fused_results = rerank_and_fuse(query_text, results, top_k=5)

    output = [
        {
            "id": r.metadata["id"],
            "filename": r.metadata["filename"],
            "content": r.page_content
        }
        for r in fused_results
    ]
    return jsonify(output)

@search_bp.route("/query", methods=["POST"])
def query():
    query_text = request.json.get("query")
    if not query_text:
        return jsonify({"error": "缺少查询内容"}), 400

    store = load_faiss_index()
    results = store.similarity_search(query_text, k=5)
    output = [{"id": r.metadata["id"], "filename": r.metadata["filename"], "content": r.page_content} for r in results]
    return jsonify(output)
