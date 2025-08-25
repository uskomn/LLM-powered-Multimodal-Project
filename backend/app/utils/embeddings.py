import json
from sentence_transformers import SentenceTransformer

# 这里用 MiniLM 做示例，你可以换成自己的 embedding 模型
_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def get_embedding(text: str):
    """生成文本向量"""
    vector = _model.encode(text).tolist()
    return vector

def serialize_embedding(vector):
    """存储时转为字符串"""
    return json.dumps(vector)

def deserialize_embedding(vector_str):
    """读取时转为 list"""
    return json.loads(vector_str)
