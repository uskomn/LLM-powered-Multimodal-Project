import requests

DEEPSEEK_API_KEY = "sk-8cbf10f456ae40aba1be330eaa3c2397"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 判断提问是简单问题还是复杂问题
def is_complex_query(query_text: str) -> bool:
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
你是一个问题分类器。
请判断下面的问题是【简单问题】还是【复杂问题】：

复杂问题的标准：
1. 需要分解为多个子问题才能回答
2. 涉及推理、比较、因果分析
3. 需要逐步整合多个信息源

简单问题的标准：
1. 单一事实/定义/属性查询
2. 可以直接通过一次检索回答

问题: {query_text}

请只输出 "复杂" 或 "简单"。
"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个分类器，只能回答 简单 或 复杂"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        result = data["choices"][0]["message"]["content"].strip()
        return result.startswith("复杂")
    except requests.exceptions.RequestException as e:
        print("请求失败:", e)
        # 默认走简单逻辑，避免接口挂掉时全失败
        return False

# 调用deepseek回答问题
def call_deepseek(prompt: str) -> str:
    """
    通用 DeepSeek LLM 调用封装
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个智能助手，请根据上下文回答问题"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print("请求失败:", e)
        return ""

# 将问题切分为子问题
def decompose_query(query: str):
    """
    调用 DeepSeek 将复杂问题分解为子问题
    """
    prompt = f"""
请将以下问题分解为 3-5 个循序渐进的子问题：
问题：{query}
只输出子问题列表，每个子问题单独一行。
"""
    result = call_deepseek(prompt)
    # 简单处理：按行分割
    sub_queries = [line.strip("-•123456. ") for line in result.split("\n") if line.strip()]
    return sub_queries


