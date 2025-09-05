# chat.py
import uuid
from flask import Blueprint, request, jsonify
import requests
from datetime import datetime
from backend.app.extensions import db
from backend.app.models.conversation import Conversation, Message
from backend.app.models.user import User
from backend.app.core.security import require_role
from flask_jwt_extended import get_jwt_identity

DEEPSEEK_API_KEY = "sk-8cbf10f456ae40aba1be330eaa3c2397"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
QUERY_API_URL = "http://127.0.0.1:5000/retrieval/query"

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat", methods=["POST"])
@require_role(['admin', 'user'], action_desc="大模型对话")
def chat():
    current_user_id = get_jwt_identity()  # 当前用户ID
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    query_text = data.get("query", "").strip()
    conversation_id = data.get("conversation_id")  # int类型，可选

    if not query_text:
        return jsonify({"error": "query is required"}), 400

    # 创建新会话
    if not conversation_id:
        conversation = Conversation(
            user_id=current_user_id,
            session_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
        db.session.add(conversation)
        db.session.commit()
        conversation_id = conversation.id
    else:
        # 查询已有会话，确保属于当前用户
        conversation = Conversation.query.filter_by(id=conversation_id, user_id=current_user_id).first()
        if not conversation:
            conversation = Conversation(
                user_id=current_user_id,
                session_id=str(uuid.uuid4()),
                created_at=datetime.utcnow()
            )
            db.session.add(conversation)
            db.session.commit()
            conversation_id = conversation.id

    # 保存用户消息
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=query_text,
        created_at=datetime.utcnow()
    )
    db.session.add(user_msg)
    db.session.commit()

    # 调用 query 接口检索相关文档
    try:
        search_resp = requests.post(QUERY_API_URL, json={"query": query_text})
        search_resp.raise_for_status()
        search_results = search_resp.json()
    except Exception as e:
        return jsonify({"error": "retrieval failed", "details": str(e)}), 500

    # 组合 context
    context_texts = "\n".join([r.get("content", "") if isinstance(r, dict) else str(r) for r in search_results])

    # 构造 DeepSeek 消息
    messages = [
        {"role": "system", "content": "你是知识问答助手，请结合已知文档回答问题。"},
        {"role": "user", "content": f"问题: {query_text}\n知识库内容:\n{context_texts}"}
    ]

    # 调用大模型接口
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7
        }
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
    except Exception as e:
        return jsonify({"error": "LLM call failed", "details": str(e)}), 500

    # 保存助手消息
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        created_at=datetime.utcnow()
    )
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({
        "conversation_id": conversation_id,
        "answer": answer,
        "retrieved_docs": search_results
    })
