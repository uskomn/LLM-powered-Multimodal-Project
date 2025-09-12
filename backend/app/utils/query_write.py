import requests

DEEPSEEK_API_KEY = "sk-8cbf10f456ae40aba1be330eaa3c2397"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 查询重写
def query_rewrite(query_text: str) -> str:
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",  # 注意这里加了空格
        "Content-Type": "application/json"
    }

    prompt = f"""
    你是一个检索查询改写助手。
    任务：将用户问题改写为**更清晰、完整的检索查询**，保证语义完整，不要只输出关键词。
    要求：
    1. 必须是自然语言句子。
    2. 保留用户问题中的关键信息。
    3. 不要回答问题，只生成改写后的查询。

    用户问题：{query_text}
    请输出改写后的检索查询：
    """

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print("请求失败:", e)
        return query_text  # 失败时返回原始 query

