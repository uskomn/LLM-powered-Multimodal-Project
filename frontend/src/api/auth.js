import axios from "./axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000", // 后端 Flask 地址
  timeout: 10000,
});

// 登录
export function login(username, password) {
  return api.post("/auth/login", { username, password });
}

// 注册
export function register(username, password) {
  return api.post("/auth/register", { username, password });
}

export default api;