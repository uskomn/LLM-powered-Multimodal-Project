import os
import requests
from flask import Blueprint, request, jsonify

rag_bp = Blueprint("rag", __name__)

DEEPSEEK_API_KEY = "sk-8cbf10f456ae40aba1be330eaa3c2397"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
SEARCH_API_URL = "http://127.0.0.1:5000/retrieval/search"

# 会话记忆
conversation_history = {}

@rag_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data.get("query", "").strip()
    session_id = data.get("session_id", "default")  # 没传就用 default

    if not query:
        return jsonify({"error": "query is required"}), 400

    # 获取历史对话
    history = conversation_history.get(session_id, [])

    try:
        search_resp = requests.post(SEARCH_API_URL, json={"query": query})
        search_resp.raise_for_status()
        search_results = search_resp.json().get("results", [])
        context_texts = "\n".join([r["content"] for r in search_results])

        messages = [{"role": "system", "content": "你是知识问答助手，请结合已知信息回答用户问题。"}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": f"问题: {query}\n知识库内容:\n{context_texts}"})

        print(DEEPSEEK_API_KEY)
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

        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        conversation_history[session_id] = history

        return jsonify({
            "answer": answer,
            "retrieval": search_results,
            "history": history[-10:]  # 返回最近10条对话
        }), 200

    except Exception as e:
        return jsonify({"error": "chat failed", "details": str(e)}), 500
