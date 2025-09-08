# chat.py
import uuid
import json
from flask import Blueprint, request, jsonify
import requests
from datetime import datetime
from backend.app.extensions import db
from backend.app.models.conversation import Conversation, Message
from backend.app.models.user import User
from backend.app.core.security import require_role
from backend.app.utils.extract_keywords import extract_keywords
from backend.app.utils.path_ranking import path_ranking
from py2neo import Graph
from flask_jwt_extended import get_jwt_identity

DEEPSEEK_API_KEY = "sk-8cbf10f456ae40aba1be330eaa3c2397"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
QUERY_API_URL = "http://127.0.0.1:5000/retrieval/query"
KG_API_URL="http://127.0.0.1:5000/kg/query"

graph = Graph("bolt://localhost:7687", auth=("neo4j", "aqzdwsfneo"))

chat_bp = Blueprint("chat", __name__)

def classify_query(query_text: str) -> str:
    """调用 LLM 判断 query 类型"""
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    prompt = f"""
    你是一个智能助手，需要判断用户的问题属于哪种类型。
    类型只有三类：
    1. fact —— 精确事实问题，需要用知识图谱精确检索
    2. rag —— 开放模糊问答，需要走语义检索
    3. hybrid —— 复杂组合问题，需要同时结合知识图谱和语义检索
    用户问题: {query_text}
    请只返回一个单词: fact / rag / hybrid
    """
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    classification = response.json()["choices"][0]["message"]["content"].strip().lower()
    return classification if classification in ["fact", "rag", "hybrid"] else "rag"


def query_kg(keywords):
    """调用 search_kg 查询知识图谱"""
    results = []
    for kw in keywords:
        # 1. CONTAINS 查询
        cypher = f"""
        MATCH (e:Entity)-[r]->(n:Entity)
        WHERE e.name CONTAINS '{kw}' OR n.name CONTAINS '{kw}' OR type(r) CONTAINS '{kw}'
        RETURN e.name AS head, type(r) AS relation, n.name AS tail
        LIMIT 20
        """
        res = graph.run(cypher).data()
        results.extend(res)
    return results


def reason_pra_candidates(kg_results, top_k=5):
    """调用 PRA 做推理"""
    candidates = []
    for item in kg_results:
        head = item.get("head")
        relation = item.get("relation")
        tail = item.get("tail", "")
        try:
            pra_res = path_ranking(head, relation, tail, top_k)
            candidates.extend(pra_res)
        except Exception as e:
            print(str(e))
            continue
    return candidates


@chat_bp.route("/chat", methods=["POST"])
@require_role(['admin', 'user'], action_desc="大模型对话")
def chat():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    query_text = data.get("query", "").strip()
    conversation_id = data.get("conversation_id")  # int类型，可选
    if not query_text:
        return jsonify({"error": "query is required"}), 400

    # 创建或查询会话
    if not conversation_id:
        conversation = Conversation(user_id=current_user_id, session_id=str(uuid.uuid4()), created_at=datetime.utcnow())
        db.session.add(conversation)
        db.session.commit()
        conversation_id = conversation.id
    else:
        conversation = Conversation.query.filter_by(id=conversation_id, user_id=current_user_id).first()
        if not conversation:
            conversation = Conversation(user_id=current_user_id, session_id=str(uuid.uuid4()), created_at=datetime.utcnow())
            db.session.add(conversation)
            db.session.commit()
            conversation_id = conversation.id

    # 保存用户消息
    user_msg = Message(conversation_id=conversation_id, role="user", content=query_text, created_at=datetime.utcnow())
    db.session.add(user_msg)
    db.session.commit()

    # 分类问题类型
    query_type = classify_query(query_text)

    retrieved_context = []

    if query_type in ["fact", "hybrid"]:
        keywords = extract_keywords(query_text)
        kg_results = query_kg(keywords)
        retrieved_context.extend(kg_results)
        if query_type == "hybrid":
            pra_results = reason_pra_candidates(kg_results)
            retrieved_context.extend(pra_results)

    if query_type in ["rag", "hybrid"]:
        # RAG 检索
        try:
            search_resp = requests.post(QUERY_API_URL, json={"query": query_text})
            search_resp.raise_for_status()
            rag_results = search_resp.json()
        except Exception as e:
            rag_results = [{"content": f"error: {str(e)}"}]
        retrieved_context.extend(rag_results)

    # 构造 LLM prompt
    context_texts = "\n".join([str(r) for r in retrieved_context])
    messages = [
        {"role": "system", "content": "你是知识问答助手，请结合已知文档回答问题。"},
        {"role": "user", "content": f"问题: {query_text}\n知识库内容:\n{context_texts}"}
    ]

    # 调用 LLM
    try:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "deepseek-chat", "messages": messages, "temperature": 0.7}
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"LLM call failed: {str(e)}"

    # 保存助手消息
    assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=answer, created_at=datetime.utcnow())
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({
        "conversation_id": conversation_id,
        "query_type": query_type,
        "answer": answer,
        "retrieved_context": retrieved_context
    })