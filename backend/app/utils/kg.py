import pdfplumber
import re
import hanlp
import json
import requests

hanlp_parser = hanlp.load('CTB9_TOK_ELECTRA_BASE')  # 或 'CTB9_POS_ALBERT_BASE'
hanlp_ner = hanlp.load('MSRA_NER_ELECTRA_SMALL_ZH')

STOPWORDS = {"公司", "企业", "集团"}  # 可扩充

def hanlp_extract_triples(text: str):
    """
    使用 HanLP + NER + 规则抽取中文三元组
    """
    triples = []

    # 文本清洗
    text = re.sub(r'\s+', ' ', text)  # 去掉多余空格和换行
    text = re.sub(r'[·●•]', '', text)  # 去掉奇怪符号

    # NER 提取实体
    ner_doc = hanlp_ner(text)
    entities = [ent[0] for ent in ner_doc if ent[1] in ('PERSON', 'ORG', 'LOC')]

    # 依存句法解析
    doc = hanlp_parser(text)

    for token in doc:
        if hasattr(token, 'head') and hasattr(token, 'deprel'):
            dep_label = token.deprel
            head_idx = token.head
            dep_word = token.text
            head_word = doc[head_idx - 1].text if head_idx > 0 else ""
            if dep_label in ('SBV', 'VOB') and head_word and dep_word:
                # 只保留包含实体的关系
                if any(e in head_word for e in entities) or any(e in dep_word for e in entities):
                    triples.append([head_word, dep_label, dep_word])

    # 正则补充属性句式
    pattern_list = [
        re.compile(r"(.+?)的(.+?)是(.+?)。?"),  # X 的 Y 是 Z
        re.compile(r"(.+?)于(.+?)成立"),       # X 于 Y 成立
        re.compile(r"(.+?)在(.+?)工作")        # X 在 Y 工作
    ]
    for pattern in pattern_list:
        for match in pattern.finditer(text):
            triples.append([match.group(1), match.group(2), match.group(3)])

    # 去重
    triples = [list(t) for t in set(tuple(x) for x in triples)]

    # 打印调试
    print("hanlp抽取三元组:", triples)
    return triples


def extract_triples(text: str,DEEPSEEK_API_KEY:str,DEEPSEEK_API_URL:str):
    """大模型抽取 + HanLP 补充"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""
    从以下文本中抽取知识三元组，格式为 ["实体1", "关系", "实体2"] 或 ["实体", "属性", "值"]。
    只返回 JSON 数组，不要多余解释。

    文本: {text}
    """
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    triples = []
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        triples = json.loads(content)
    except Exception:
        triples = []
    # # Fallback 或 融合 HanLP
    # rule_triples = hanlp_extract_triples(text)
    # triples.extend(rule_triples)
    # print(triples)
    #
    # # 去重
    # triples = [list(t) for t in set(tuple(x) for x in triples)]
    return triples


def pdf_to_text_chunks(file_path, chunk_size=1000, overlap=100):
    """提取 PDF 并分块"""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
