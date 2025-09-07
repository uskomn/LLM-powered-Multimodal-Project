from flask import Blueprint, request, jsonify
from py2neo import Graph
import json

# 连接 Neo4j
graph = Graph("bolt://localhost:7687", auth=("neo4j", "aqzdwsfneo"))

pra_bp = Blueprint("pra", __name__)

def path_ranking(head: str, relation: str = "", tail: str = "", top_k: int = 5):
    """
    使用 Path Ranking Algorithm (PRA) 进行推理，支持 head 和 relation 模糊匹配。
    """
    # Cypher 查询
    cypher = f"""
    MATCH p = (start:Entity)-[r:{relation}]->(end:Entity)
    WHERE start.name CONTAINS '{head}'
    AND (end.name CONTAINS '{tail}' OR '{tail}' = '')
    RETURN p, r, start, end
    ORDER BY length(p) DESC
    LIMIT {top_k}
    """

    try:
        results = graph.run(cypher).data()
        ranked_paths = []

        for result in results:
            path = [node["name"] for node in result["p"].nodes]
            relation = [r.type for r in result["p"].relationships]
            score = len(path)  # 可以根据路径长度或其他指标计算 score
            ranked_paths.append({
                "path": " -> ".join(path),
                "relation": " -> ".join(relation),
                "score": score
            })

        return ranked_paths

    except Exception as e:
        return {"error": f"Error running PRA: {str(e)}"}

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
