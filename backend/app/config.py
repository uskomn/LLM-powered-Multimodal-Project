import os

class Config:
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://root:aqzdwsf@localhost:3306/llm_multimodel?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "aeijcmejsiefmeiaeigr")

    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "..", "data")
    UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
    VECTOR_DIR = os.path.join(DATA_DIR, "vectorstores")

    # deepseek
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-8cbf10f456ae40aba1be330eaa3c2397")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_EMBEDDING = os.getenv("DEEPSEEK_EMBEDDING", "text-embedding-3-small")

    FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "backend/faiss_index/index.faiss")

    # 本地 HuggingFace 嵌入模型
    HF_EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    # 文本切分
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))

    # 检索参数
    TOP_K = int(os.getenv("TOP_K", 4))
