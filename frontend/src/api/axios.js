import axios from "axios";

const instance = axios.create({
  baseURL: "http://127.0.0.1:5000",  // 后端 Flask 地址
});

// 请求拦截器：自动加上 JWT
instance.interceptors.request.use((config) => {
  const token = localStorage.getItem("token"); // 登录时保存的 token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

instance.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login"; // 重新登录
    }
    return Promise.reject(err);
  }
);

export default instance;
