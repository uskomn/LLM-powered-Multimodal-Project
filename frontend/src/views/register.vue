<template>
  <div class="register">
    <h2>用户注册</h2>
    <form @submit.prevent="handleRegister">
      <input v-model="username" type="text" placeholder="用户名" required />
      <input v-model="password" type="password" placeholder="密码" required />
      <button type="submit">注册</button>
    </form>
    <p>已有账号？<router-link to="/login">去登录</router-link></p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { register } from "../api/auth";

const username = ref("");
const password = ref("");

const handleRegister = async () => {
  try {
    const res = await register({ username: username.value, password: password.value });
    alert("注册成功，请登录！");
    console.log(res.data);
  } catch (err) {
    alert("注册失败: " + err.response?.data?.error || err.message);
  }
};
</script>

<style scoped>
.register {
  max-width: 300px;
  margin: 100px auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 6px;
}
</style>
