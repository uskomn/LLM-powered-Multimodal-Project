from py2neo import Graph

graph = Graph("bolt://localhost:7687", auth=("neo4j", "aqzdwsfneo"))

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