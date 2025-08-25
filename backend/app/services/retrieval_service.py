import os
import faiss
import numpy as np
from backend.app.models.document import Document
from backend.app.utils.embeddings import get_embedding
from backend.app.config import Config

INDEX_PATH = os.path.join(Config.FAISS_INDEX_PATH, "docs.index")
DOC_IDS_PATH = os.path.join(Config.FAISS_INDEX_PATH, "doc_ids.txt")

class VectorStore:
    def __init__(self, dim=384):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.doc_ids = []
        os.makedirs(Config.FAISS_INDEX_PATH, exist_ok=True)
        self.load()

    def add_documents(self, documents):
        vectors = []
        ids = []
        for doc in documents:
            if doc.id in self.doc_ids:
                continue  # 已存在则跳过
            emb = get_embedding(doc.content)
            if emb is not None:
                vectors.append(emb)
                ids.append(doc.id)
        if vectors:
            vectors = np.array(vectors, dtype="float32")
            self.index.add(vectors)
            self.doc_ids.extend(ids)
            self.save()

    def save(self):
        faiss.write_index(self.index, INDEX_PATH)
        with open(DOC_IDS_PATH, "w", encoding="utf-8") as f:
            f.write(",".join(map(str, self.doc_ids)))

    def load(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(DOC_IDS_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            with open(DOC_IDS_PATH, "r", encoding="utf-8") as f:
                self.doc_ids = list(map(int, f.read().split(",")))

    def search(self, query, top_k=5):
        emb = get_embedding(query)
        if emb is None or len(self.doc_ids) == 0:
            return []
        emb = np.array([emb], dtype="float32")
        D, I = self.index.search(emb, top_k)
        results = []
        for idx in I[0]:
            if idx < len(self.doc_ids):
                doc = Document.query.get(self.doc_ids[idx])
                if doc:
                    results.append({
                        "id": doc.id,
                        "title": doc.filename,
                        "content": doc.content
                    })
        return results


# 全局实例
vector_store = VectorStore()
