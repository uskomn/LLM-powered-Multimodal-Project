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
from backend.app.services.retrieval_service import is_complex_query
from py2neo import Graph
from flask_jwt_extended import get_jwt_identity

DEEPSEEK_API_KEY = "sk-8cbf10f456ae40aba1be330eaa3c2397"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
QUERY_API_URL = "http://127.0.0.1:5000/retrieval/query"
QUERY_ADVANCED_API_URL="http://127.0.0.1:5000/retrieval/query_advanced_sonquery"
PRA_API_URL="http://127.0.0.1:5000/PRA/reason_pra_test"
KG_API_URL="http://127.0.0.1:5000/kg/query"

graph = Graph("bolt://localhost:7687", auth=("neo4j", "aqzdwsfneo"))

chat_bp = Blueprint("chat", __name__)

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

def call_deepseek_chat(query_text,context_texts):
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
    return answer


@chat_bp.route("/chat", methods=["POST"])
@require_role(['admin', 'user'], action_desc="大模型对话")
def chat():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    query_text = data.get("query", "").strip()
    file_id=data.get("file_id")
    conversation_id = data.get("conversation_id")  # int类型，可选
    if not query_text:
        return jsonify({"error": "query is required"}), 400
    if not file_id:
        return jsonify({"error":"file_id is required"}),400

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

    is_complex=is_complex_query(query_text)
    answer=""
    answer_a,answer_b=None,None
    if not is_complex:
        hybrid_context = []

        # RAG 检索
        try:
            search_resp = requests.post(QUERY_API_URL, json={"query": query_text,"file_id":file_id})
            search_resp.raise_for_status()
            rag_results = search_resp.json()
        except Exception as e:
            rag_results = [{"content": f"error: {str(e)}"}]
        hybrid_context.extend(rag_results)

        keywords = extract_keywords(query_text)
        kg_results = query_kg(keywords)
        hybrid_context.extend(kg_results)

        try:
            pra_resp = requests.post(PRA_API_URL,json={"query": query_text})
            pra_resp.raise_for_status()
            pra_results = pra_resp.json().get("candidates", [])
        except Exception as e:
            pra_results = [{"content": f"调用PRA接口失败: {str(e)}"}]

        hybrid_context.extend(pra_results)

        context_texts="\n".join([str(r) for r in hybrid_context])

        answer = call_deepseek_chat(query_text, context_texts)

        # 保存助手消息
        assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=answer,
                                created_at=datetime.utcnow())
        db.session.add(assistant_msg)
        db.session.commit()

    else:
        try:
            hybrid_context = []

            search_resp = requests.post(QUERY_API_URL, json={"query": query_text, "file_id": file_id})
            search_resp.raise_for_status()
            rag_results = search_resp.json()
            hybrid_context.extend(rag_results)

            keywords = extract_keywords(query_text)
            kg_results = query_kg(keywords)
            hybrid_context.extend(kg_results)

            pra_resp = requests.post(PRA_API_URL,  json={"query": query_text})
            pra_resp.raise_for_status()
            pra_results = pra_resp.json().get("candidates", [])
            hybrid_context.extend(pra_results)

            context_texts_a = "\n".join([str(r) for r in hybrid_context])
            answer_a = call_deepseek_chat(query_text, context_texts_a)

        except Exception as e:
            answer_a = f"方法A失败: {str(e)}"

            # 方法 B: 子查询拆解
        try:
            result = requests.post(QUERY_ADVANCED_API_URL, json={"query": query_text, "file_id": file_id})
            result.raise_for_status()
            result = result.json()
            answer_b = result.get("final_answer", "")
        except Exception as e:
            answer_b = f"方法B失败: {str(e)}"

    return jsonify({
        "conversation_id": conversation_id,
        "query_type": "complex" if is_complex else "simple",
        "answer": answer if not is_complex else None,
        "answer_a": answer_a if is_complex else None,
        "answer_b": answer_b if is_complex else None
    })