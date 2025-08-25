import os

class Config:
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://root:aqzdwsf@localhost:3306/llm_multimodel?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "aeijcmejsiefmeiaeigr")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "backend/app/faiss_index")
