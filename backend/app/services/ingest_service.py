import os
import pickle
from langchain.vectorstores import FAISS
from langchain.docstore import InMemoryDocstore
from langchain.docstore.document import Document as LC_Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from backend.app.utils.dynamic_split import dynamic_split
from backend.app.utils.embeddings import get_embedding
from backend.app.models.document import Document
from backend.app.extensions import db
from transformers import AutoTokenizer
import faiss

FAISS_INDEX_PATH = "backend/faiss_index/faiss.index"
FAISS_STORE_PATH = "backend/faiss_index/faiss_store.pkl"
UPLOAD_STORE_PATH="backend/uploads"

tokenizer = AutoTokenizer.from_pretrained("bert-base-chinese")

def load_faiss_index():
    if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(FAISS_STORE_PATH):
        index = faiss.read_index(FAISS_INDEX_PATH)
        with open(FAISS_STORE_PATH, "rb") as f:
            store = pickle.load(f)
        store.index = index
        return store
    else:
        dim = 384  # SBERT 向量维度
        index = faiss.IndexFlatL2(dim)
        docstore = InMemoryDocstore({})       # 空 docstore
        index_to_docstore_id = {}             # 空映射
        store = FAISS(
            embedding_function=get_embedding,
            index=index,
            docstore=docstore,
            index_to_docstore_id=index_to_docstore_id
        )
        return store

def save_faiss_index(store):
    faiss.write_index(store.index, FAISS_INDEX_PATH)
    with open(FAISS_STORE_PATH, "wb") as f:
        pickle.dump(store, f)

def ingest_document(file, content, user_id):
    os.makedirs(UPLOAD_STORE_PATH, exist_ok=True)
    filepath = os.path.join(UPLOAD_STORE_PATH, file.filename)
    file.save(filepath)

    # splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    # chunks = splitter.split_text(content)

    chunks=dynamic_split(content,max_tokens=500,overlap=50)

    lc_docs = []
    ids = []
    try:
        for chunk in chunks:
            if not chunk.strip():
                continue

            # 保存到数据库
            doc = Document(
                filename=file.filename,
                content=chunk,
                user_id=user_id
            )
            db.session.add(doc)
            db.session.flush()  # 确保 doc.id 可用
            ids.append(doc.id)
            lc_docs.append(
                LC_Document(
                    page_content=chunk,
                    metadata={"id": doc.id, "filename": file.filename, "user_id": user_id}
                )
            )

        db.session.commit()

        # 写入 FAISS
        store = load_faiss_index()
        store.add_documents(lc_docs)
        save_faiss_index(store)

    except Exception as e:
        db.session.rollback()
        print(f"数据库写入失败: {e}")
        raise e

    return ids