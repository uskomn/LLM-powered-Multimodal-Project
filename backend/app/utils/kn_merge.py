import torch
from transformers import BertTokenizer, BertModel
import numpy as np
from collections import defaultdict
from scipy.optimize import linear_sum_assignment

# ===== 初始化 BERT =====
MODEL_NAME = "bert-base-chinese"  # 中文可换 "hfl/chinese-roberta-wwm-ext"
tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
bert_model = BertModel.from_pretrained(MODEL_NAME)
bert_model.eval()

def get_embedding(text: str):
    """获取文本的 BERT 向量表示（取 [CLS] 向量）"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=32)
    with torch.no_grad():
        outputs = bert_model(**inputs)
    return outputs.last_hidden_state[:, 0, :].numpy().flatten()

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8)

def fuse_triples(triples, entity_threshold=0.95, relation_threshold=0.95):
    """
    知识融合（BERT 语义相似度）
    :param triples: 输入三元组 [[h, r, t], ...]
    :param entity_threshold: 实体相似度阈值
    :param relation_threshold: 关系相似度阈值
    :return: 融合后的三元组
    """
    # === Step 1. 收集实体和关系 ===
    entities = set()
    relations = set()
    for h, r, t in triples:
        entities.add(h)
        entities.add(t)
        relations.add(r)

    # === Step 2. 计算 BERT 向量 ===
    entity_vecs = {e: get_embedding(e) for e in entities}
    relation_vecs = {r: get_embedding(r) for r in relations}

    # === Step 3. 实体对齐 ===
    entity_map = {}
    entity_list = list(entities)
    for i in range(len(entity_list)):
        for j in range(i + 1, len(entity_list)):
            sim = cosine_similarity(entity_vecs[entity_list[i]], entity_vecs[entity_list[j]])
            if sim >= entity_threshold:
                entity_map[entity_list[j]] = entity_list[i]

    # === Step 4. 关系对齐 ===
    relation_map = {}
    relation_list = list(relations)
    for i in range(len(relation_list)):
        for j in range(i + 1, len(relation_list)):
            sim = cosine_similarity(relation_vecs[relation_list[i]], relation_vecs[relation_list[j]])
            if sim >= relation_threshold:
                relation_map[relation_list[j]] = relation_list[i]

    # === Step 5. 替换并去重 ===
    fused_triples = set()
    for h, r, t in triples:
        h_new = entity_map.get(h, h)
        t_new = entity_map.get(t, t)
        r_new = relation_map.get(r, r)
        fused_triples.add((h_new, r_new, t_new))

    # === Step 6. 冲突消解（多数投票） ===
    knowledge = defaultdict(lambda: defaultdict(int))
    for h, r, t in fused_triples:
        knowledge[(h, r)][t] += 1

    final_triples = []
    for (h, r), tails in knowledge.items():
        best_t = max(tails.items(), key=lambda x: x[1])[0]
        final_triples.append([h, r, best_t])

    return final_triples

def knowledge_fusion(triples, entity_threshold=0.9):
    """
    属性归类 → 聚合子图 → 阈值匹配
    :param triples: 输入三元组 [[h, r, t], ...]
    :param entity_threshold: 实体对齐阈值
    :return: 融合后的知识（实体 -> {关系: [tail/属性...] }）
    """
    # === Step 1. 属性归类 ===
    knowledge = defaultdict(lambda: defaultdict(list))
    entities = set()

    for h, r, t in triples:
        # 简单启发式：如果关系看起来像属性，就存为属性值
        if r in ["是", "旨在帮助了解", "更新方式", "责任"]:
            knowledge[h][r].append(t)
        else:
            knowledge[h][r].append(t)
        entities.add(h)
        entities.add(t)

    # === Step 2. 聚合子图（合并相同 head 的所有关系）===
    entity_list = list(entities)
    entity_vecs = {e: get_embedding(e) for e in entity_list}

    # === Step 3. 阈值匹配（全局实体对齐）===
    entity_map = {}
    for i in range(len(entity_list)):
        for j in range(i + 1, len(entity_list)):
            sim = cosine_similarity(entity_vecs[entity_list[i]], entity_vecs[entity_list[j]])
            if sim >= entity_threshold:
                # 把 j 对齐到 i
                entity_map[entity_list[j]] = entity_list[i]

    # === Step 4. 替换并融合 ===
    fused_knowledge = defaultdict(lambda: defaultdict(list))
    for h, rels in knowledge.items():
        h_new = entity_map.get(h, h)
        for r, tails in rels.items():
            for t in tails:
                t_new = entity_map.get(t, t)
                fused_knowledge[h_new][r].append(t_new)

        # === Step 5. 去重 ===
    for h, rels in fused_knowledge.items():
        for r in rels:
            fused_knowledge[h][r] = list(set(rels[r]))

        # === Step 6. 转换为三元组列表，方便存储到 Neo4j ===
    final_triples = []
    for h, rels in fused_knowledge.items():
        for r, tails in rels.items():
            for t in tails:
                final_triples.append([h, r, t])

    return final_triples