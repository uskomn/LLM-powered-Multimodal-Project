from ..models.document import Document
from ..extensions import db
from ..utils.embeddings import get_embedding, serialize_embedding
from backend.app.services.retrieval_service import vector_store

def ingest_document(title: str, content: str):
    """存入数据库，并加入向量库"""
    embedding = get_embedding(content)
    if embedding is None:
        raise ValueError("生成 embedding 失败")

    doc = Document(
        filename=title,
        content=content,
        embedding=serialize_embedding(embedding)
    )
    db.session.add(doc)
    db.session.commit()

    # 入 FAISS 向量库
    vector_store.add_documents([doc])
    return doc