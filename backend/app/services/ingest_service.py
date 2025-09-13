import os
import pickle
from langchain.vectorstores import FAISS
from langchain.docstore import InMemoryDocstore
from langchain.docstore.document import Document as LC_Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from backend.app.utils.dynamic_split import dynamic_split
from backend.app.utils.embeddings import get_embedding
from backend.app.models.document import Document,File
from backend.app.extensions import db
from transformers import AutoTokenizer
import faiss

FAISS_BASE_PATH = "backend/faiss_index"
UPLOAD_STORE_PATH="backend/uploads"

tokenizer = AutoTokenizer.from_pretrained("bert-base-chinese")

def get_faiss_paths(file_id: int):
    """生成文件专属的索引路径"""
    index_path = os.path.join(FAISS_BASE_PATH, f"file_{file_id}.index")
    store_path = os.path.join(FAISS_BASE_PATH, f"file_{file_id}_store.pkl")
    return index_path, store_path

def load_faiss_index(file_id: int):
    index_path, store_path = get_faiss_paths(file_id)

    if os.path.exists(index_path) and os.path.exists(store_path):
        index = faiss.read_index(index_path)
        with open(store_path, "rb") as f:
            store = pickle.load(f)
        store.index = index
        return store
    else:
        dim = 384  # SBERT 向量维度
        index = faiss.IndexFlatL2(dim)
        docstore = InMemoryDocstore({})
        index_to_docstore_id = {}
        store = FAISS(
            embedding_function=get_embedding,
            index=index,
            docstore=docstore,
            index_to_docstore_id=index_to_docstore_id
        )
        return store

def save_faiss_index(store, file_id: int):
    index_path, store_path = get_faiss_paths(file_id)
    os.makedirs(FAISS_BASE_PATH, exist_ok=True)

    faiss.write_index(store.index, index_path)
    with open(store_path, "wb") as f:
        pickle.dump(store, f)

def ingest_document(file, content, user_id):
    os.makedirs(UPLOAD_STORE_PATH, exist_ok=True)
    filepath = os.path.join(UPLOAD_STORE_PATH, file.filename)
    file.save(filepath)

    # === 先创建 File 记录 ===
    file_record = File(filename=file.filename, user_id=user_id)
    db.session.add(file_record)
    db.session.flush()  # 拿到 file_record.id
    file_id = file_record.id

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
                file_id=file_id,
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
                    metadata={"id": doc.id,"file_id":file_id, "filename": file.filename, "user_id": user_id}
                )
            )

        db.session.commit()

        # 写入 FAISS
        store = load_faiss_index(file_id)
        store.add_documents(lc_docs)
        save_faiss_index(store,file_id)

    except Exception as e:
        db.session.rollback()
        print(f"数据库写入失败: {e}")
        raise e

    return ids