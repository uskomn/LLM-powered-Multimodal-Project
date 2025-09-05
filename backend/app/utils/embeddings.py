# backend/app/utils/embeddings.py
from sentence_transformers import SentenceTransformer

# 初始化 SBERT 模型
model = SentenceTransformer('all-MiniLM-L6-v2')  # 可换其他 SBERT 模型

def get_embedding(text: str):
    """生成文本的向量表示"""
    return model.encode(text).tolist()  # 转成 list 方便存储或 FAISS
