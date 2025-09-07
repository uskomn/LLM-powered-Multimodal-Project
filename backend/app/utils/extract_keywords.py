import re
import jieba
import jieba.posseg as pseg

# 可扩展的疑问词/停用词
STOPWORDS = {"什么", "多少", "多长", "怎么样", "如何", "吗", "呢", "是", "有", "的", "和", "在", "对", "为", "请", "告诉"}

def extract_keywords(query: str):
    """
    升级版关键词抽取：jieba 分词 + 词性过滤
    """
    # 预清理：去掉常见疑问表达
    query = re.sub(r"(是多长|是多少|有什么|怎么|如何|吗|呢)", "", query)
    query = query.strip()

    if not query:
        return []

    # 分词 + 词性
    words = pseg.cut(query)

    # 只保留名词/专有名词/地名/机构名
    keywords = [
        w for w, flag in words
        if (flag.startswith("n") or flag in ("nt", "nz", "ns"))
        and w not in STOPWORDS
        and len(w) > 1
    ]

    # 如果没找到关键词，就退化为整句
    if not keywords:
        keywords = [query]

    return keywords

def extract_triplet(query: str):
    """
    升级版 query → (head, relation, tail) 抽取
    - head: 实体名（公司/人/机构）
    - relation: 关系（时间/服务领域/职位等）
    - tail: 可选的补充信息
    """
    # 去掉疑问表达
    query = re.sub(r"(是多长|是多少|有什么|怎么|如何|吗|呢)", "", query).strip()
    if not query:
        return None, None, None

    words = list(pseg.cut(query))

    head, relation, tail = None, None, None

    # 简单规则：第一个机构名/专有名词 → head
    for w, flag in words:
        if flag in ("nt", "nz", "nr", "ns"):  # 机构名/专名/人名/地名
            head = w
            break

    # 规则：常见关系关键词
    relation_candidates = ["工作时间", "服务领域", "职位", "部门", "地点", "负责人", "薪资"]
    for rel in relation_candidates:
        if rel in query:
            relation = rel
            break

    # 如果句子里还有其他名词，可能是 tail
    if not relation:
        for w, flag in words:
            if flag.startswith("n") and w != head and w not in STOPWORDS:
                relation = w
                break

    if not tail:
        tail = ""

    return head, relation, tail