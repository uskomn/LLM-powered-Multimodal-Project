from flask_sqlalchemy import SQLAlchemy
import faiss
import os
from backend.app.config import Config

db = SQLAlchemy()

# 初始化 FAISS 索引（向量维度需和 DeepSeek embedding 一致，比如 1536）
embedding_dim = 1536
if os.path.exists(Config.FAISS_INDEX_PATH):
    faiss_index = faiss.read_index(Config.FAISS_INDEX_PATH)
else:
    faiss_index = faiss.IndexFlatL2(embedding_dim)  # 简单 L2 距离索引
