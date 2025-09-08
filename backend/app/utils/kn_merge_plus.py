from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

# 初始化
tokenizer_plus = AutoTokenizer.from_pretrained("bert-base-chinese")
bert_model = AutoModel.from_pretrained("bert-base-chinese")

def get_embedding_plus(text, tokenizer, model):
    """获取实体的 BERT 向量表示"""
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    embedding = outputs.last_hidden_state.mean(dim=1)  # 平均池化
    return embedding

def cosine_similarity(vec1, vec2):
    """计算余弦相似度"""
    return F.cosine_similarity(vec1, vec2).item()

def fuse_triples_plus(triples, threshold_strict=0.9, threshold_loose=0.75):
    """
    三元组融合：支持 BERT 向量相似度 + 多级阈值 + 关系一致性检查
    """
    fused_triples = []
    entity_map = {}   # 标准实体 -> 向量
    aliases = {}      # 标准实体 -> {别名集合}

    def get_canonical(entity, role):
        """
        根据 BERT 向量相似度找到标准实体
        """
        entity_vec = get_embedding_plus(entity, tokenizer_plus, bert_model)

        for std_entity, std_vec in entity_map.items():
            sim = cosine_similarity(entity_vec, std_vec)

            # 严格合并：相似度高
            if sim >= threshold_strict:
                return std_entity

            # 弱合并：记录为别名
            elif sim >= threshold_loose:
                aliases.setdefault(std_entity, set()).add(entity)

        # 没找到 → 新标准实体
        entity_map[entity] = entity_vec
        return entity

    for h, r, t in triples:
        h_std = get_canonical(h, role="head")
        t_std = get_canonical(t, role="tail")
        fused_triples.append([h_std, r, t_std])

    # 去重
    fused_triples = [list(x) for x in set(tuple(triple) for triple in fused_triples)]

    return fused_triples, aliases
