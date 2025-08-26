import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000", // 后端 Flask 地址
  timeout: 5000,
});

// 登录
export function login(data) {
  return api.post("/auth/login", data);
}

// 注册
export function register(data) {
  return api.post("/auth/register", data);
}
