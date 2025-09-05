import axios from "./axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000", // 后端 Flask 地址
  timeout: 10000,
});

// 文档检索
export function queryDocs(query) {
  return api.post("/retrieval/query", { query });
}

export default api;