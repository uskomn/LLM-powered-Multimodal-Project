import axios from "./axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000", // 后端 Flask 地址
  timeout: 10000,
});

// 上传文档
export function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/ingest/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export default api;