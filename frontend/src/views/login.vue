<template>
  <div class="login">
    <h2>用户登录</h2>
    <form @submit.prevent="handleLogin"></form>
      <input v-model="username" type="text" placeholder="用户名" />
      <input v-model="password" type="password" placeholder="密码" />
      <button @click="handleLogin">登录</button>
    <p>
      没有账号？ <router-link to="/register">去注册</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { login } from "../api/auth.js";
import { useRouter } from "vue-router";

const username = ref("");
const password = ref("");
const router = useRouter();

const handleLogin = async () => {
  try {
    const res = await login(username.value, password.value);
    localStorage.setItem("token", res.data.token); // 保存 JWT
    router.push("/"); // 跳转首页
  } catch (err) {
    alert("登录失败：" + (err.response?.data?.msg || err.message));
  }
};
</script>

<style scoped>
.login {
  max-width: 300px;
  margin: 100px auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 6px;
}
</style>
