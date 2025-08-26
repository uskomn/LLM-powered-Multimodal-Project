<template>
  <div class="login">
    <h2>用户登录</h2>
    <form @submit.prevent="handleLogin">
      <input v-model="username" type="text" placeholder="用户名" required />
      <input v-model="password" type="password" placeholder="密码" required />
      <button type="submit">登录</button>
    </form>
    <p>还没有账号？<router-link to="/register">去注册</router-link></p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { login } from "../api/auth";

const username = ref("");
const password = ref("");

const handleLogin = async () => {
  try {
    const res = await login({ username: username.value, password: password.value });
    alert("登录成功！");
    console.log(res.data);
    // 这里可以存 JWT 或跳转页面
  } catch (err) {
    alert("登录失败: " + err.response?.data?.error || err.message);
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
