from flask import Blueprint, request, jsonify
from py2neo import Graph
from backend.app.utils.extract_keywords import extract_keywords
import json

# 连接 Neo4j
graph = Graph("bolt://localhost:7687", auth=("neo4j", "aqzdwsfneo"))

pra_bp = Blueprint("pra", __name__)

def path_ranking(head: str, relation: str = "", tail: str = "", top_k: int = 5):
    """
    使用 Path Ranking Algorithm (PRA) 进行推理，支持 head 和 relation 模糊匹配。
    """
    if relation:
        # 一跳指定关系
        cypher = f"""
        MATCH p = (start:Entity)-[r:{relation}]->(end:Entity)
        WHERE start.name CONTAINS '{head}'
          AND (end.name CONTAINS '{tail}' OR '{tail}' = '')
        RETURN p, start, end
        LIMIT {top_k}
        """
    else:
        # 多跳任意关系
        cypher = f"""
        MATCH p = (start:Entity)-[*1..3]->(end:Entity)
        WHERE start.name CONTAINS '{head}'
          AND (end.name CONTAINS '{tail}' OR '{tail}' = '')
        RETURN p, start, end
        LIMIT {top_k}
        """

    try:
        results = graph.run(cypher).data()
        ranked_paths = []
        for result in results:
            path_nodes = [node["name"] for node in result["p"].nodes]
            rels = [rel.__class__.__name__ for rel in result["p"].relationships]

            # === 计算随机游走概率 ===
            prob = 1.0
            for i, node in enumerate(result["p"].nodes[:-1]):
                node_name = node["name"]
                deg_query = f"""
                            MATCH (n:Entity {{name: '{node_name}'}})-[r]->()
                            RETURN count(r) AS deg
                            """
                deg_res = graph.run(deg_query).data()
                deg = deg_res[0]["deg"] if deg_res else 1
                prob *= 1.0 / deg

            inferred_relation = None
            if len(path_nodes) > 2:  # 至少两跳才算推理
                inferred_relation = f"{path_nodes[0]} -> {path_nodes[-1]}"

            ranked_paths.append({
                "path": " -> ".join(path_nodes),
                "relation_chain": " -> ".join(rels),
                "inferred_relation": inferred_relation,
                "count": 1,
                "score": prob
            })
        return ranked_paths
    except Exception as e:
        return {"error": f"Error running PRA: {str(e)}"}


def query_kg(keywords):
    """调用 search_kg 查询知识图谱"""
    results = []
    for kw in keywords:
        # 1. CONTAINS 查询
        cypher = f"""
        MATCH (e:Entity)-[r]->(n:Entity)
        WHERE e.name CONTAINS '{kw}' OR n.name CONTAINS '{kw}' OR type(r) CONTAINS '{kw}'
        RETURN e.name AS head, type(r) AS relation, n.name AS tail
        LIMIT 20
        """
        res = graph.run(cypher).data()
        results.extend(res)
    return results

@pra_bp.route("/reason_pra_test", methods=["POST"])
def reason_pra_test():
    query = request.get_json()
    query_text = query.get("query", "")
    keywords = extract_keywords(query_text)
    kg_results = query_kg(keywords)

    # 收集实体集合（head 和 tail）
    entities = set()
    for item in kg_results:
        if item.get("head"):
            entities.add(item.get("head"))
        if item.get("tail"):
            entities.add(item.get("tail"))

    candidates = []
    # 对每对实体尝试多跳推理（跳过相同实体）
    for head in entities:
        for tail in entities:
            if head == tail:
                continue
            # 不传 relation，允许任意路径；查找 head -> tail（1..3跳）
            try:
                results = path_ranking(head, relation="", tail=tail, top_k=5)
                print(results)
                # 只收集真正的推理（inferred_relation 非空）
                for r in results:
                    if r.get("inferred_relation"):
                        candidates.append(r)
            except Exception as e:
                return jsonify({"error": f"Error running PRA: {str(e)}"}), 500

    return jsonify({"candidates": candidates}), 200



@pra_bp.route("/reason_pra", methods=["POST"])
def reason_pra():
    """
    根据用户提供的 head 和 relation 返回 PRA 推理结果。
    """
    # 获取用户请求的参数
    data = request.json
    head = data.get("head", "").strip()
    relation = data.get("relation", "").strip()  # 可选，关系为空时代表通配
    tail = data.get("tail", "").strip()  # 可选，尾实体为空时代表通配
    top_k = data.get("top_k", 5)  # 返回的结果数量，默认 5 条

    if not head:
        return jsonify({"error": "Head entity is required."}), 400

    # 调用 PRA 进行推理
    try:
        results = path_ranking(head, relation, tail, top_k)
        return jsonify({"candidates": results}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
