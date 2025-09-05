import axios from "./axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000", // 后端 Flask 地址
  timeout: 10000,
});

// 大模型问答
export function chatWithLLM(query, session_id = null) {
  return api.post("/rag/chat", { query, session_id });
}

export default api;