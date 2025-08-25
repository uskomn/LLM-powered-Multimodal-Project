from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

import faiss
import numpy as np

dimension = 768  # 向量维度（取决于你用的 embeddings 模型）
index = faiss.IndexFlatL2(dimension)  # L2 距离索引