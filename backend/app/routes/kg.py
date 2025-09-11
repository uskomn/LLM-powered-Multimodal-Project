import os
import re
from backend.app.utils.extract_keywords import extract_keywords
from backend.app.utils.kg import pdf_to_text_chunks,extract_triples
from backend.app.utils.kn_merge import fuse_triples,knowledge_fusion
from backend.app.utils.kn_merge_plus import fuse_triples_plus
from backend.app.utils.dynamic_split import dynamic_split
from flask import Blueprint, request, jsonify
from py2neo import Graph, Node, Relationship

kg_bp = Blueprint("kg", __name__)

# 连接 Neo4j
graph = Graph("bolt://localhost:7687", auth=("neo4j", "aqzdwsfneo"))

# 大模型 API 配置
DEEPSEEK_API_KEY = "sk-8cbf10f456ae40aba1be330eaa3c2397"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def normalize_relation(rel: str):
    rel = rel.strip()
    rel = re.sub(r'\W+', '_', rel)  # 非字母数字全部替换为 _
    rel = rel.upper() or "RELATED"
    return rel

def save_triples_to_neo4j(triples, doc_name):
    """存储某文档的三元组到 Neo4j"""
    doc_node = Node("Document", name=doc_name)
    graph.merge(doc_node, "Document", "name")

    for t in triples:
        if len(t) != 3:
            continue
        head, relation, tail = t
        node1 = Node("Entity", name=head)
        node2 = Node("Entity", name=tail)
        graph.merge(node1, "Entity", "name")
        graph.merge(node2, "Entity", "name")

        # 关系类型规范化
        rel_type = normalize_relation(relation)
        rel = Relationship(node1, rel_type, node2)
        graph.merge(rel)

        # 文档包含三元组对应实体
        graph.merge(Relationship(doc_node, "CONTAINS", node1))
        graph.merge(Relationship(doc_node, "CONTAINS", node2))


@kg_bp.route("/upload_pdf_build_kg", methods=["POST"])
def upload_pdf_build_kg():
    """上传 PDF，分块解析并构建知识图谱"""
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]

    upload_dir = "backend/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)

    try:
        # 1. PDF → 分块文本
        chunks = pdf_to_text_chunks(file_path,chunk_size=128,overlap=10)
        # chunks=dynamic_split(file_path,max_tokens=128,overlap=10)
        print("分块完成")
        print(f"{len(chunks)}文本块")

        all_triples = []
        for i, chunk in enumerate(chunks, 1):
            triples = extract_triples(chunk,DEEPSEEK_API_KEY, DEEPSEEK_API_URL)
            if triples:
                all_triples.extend(triples)
        final_triples=knowledge_fusion(all_triples)
        save_triples_to_neo4j(final_triples,file.filename)

        return jsonify({
            "filename": file.filename,
            "total_chunks": len(chunks),
            "triples_count": len(final_triples),
            "triples": final_triples
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@kg_bp.route("/search_kg", methods=["POST"])
def search_kg():
    query = request.json.get("query")
    if not query:
        return jsonify({"error": "query is required"}), 400

    keywords = extract_keywords(query)
    if not keywords:
        return jsonify({"results": []})

    results = []
    for kw in keywords:
        # 1. 全文索引查节点
        cypher_fulltext = f"""
        CALL db.index.fulltext.queryNodes("entityIndex", $kw) YIELD node, score
        MATCH (node)-[r]->(n:Entity)
        RETURN node.name AS head, type(r) AS relation, n.name AS tail
        LIMIT 20
        """
        try:
            res = graph.run(cypher_fulltext, kw=kw).data()
        except Exception:
            res = []

        # 2. 回退到 CONTAINS（支持 节点 + 关系）
        if not res:
            cypher_contains = f"""
            MATCH (e:Entity)-[r]->(n:Entity)
            WHERE e.name CONTAINS '{kw}' 
               OR n.name CONTAINS '{kw}' 
               OR type(r) CONTAINS '{kw}'
            RETURN e.name AS head, type(r) AS relation, n.name AS tail
            LIMIT 20
            """
            res = graph.run(cypher_contains).data()

        results.extend(res)

    return jsonify({"query": query, "keywords": keywords, "results": results})
