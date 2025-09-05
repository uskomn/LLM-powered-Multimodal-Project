<template>
  <div class="main">
    <h2>智能问答系统</h2>

    <div>
      <input v-model="query" placeholder="请输入问题..." />
      <button @click="ask">提问</button>
      <p>回答：{{ answer }}</p>
    </div>

    <div>
      <h3>上传文件</h3>
      <input type="file" @change="handleFile" />
      <button @click="upload">上传</button>
    </div>

    <button @click="logout">退出登录</button>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { chatWithLLM} from "../api/chat.js";
import {uploadDocument} from "../api/ingest";
import { useRouter } from "vue-router";

const query = ref("");
const answer = ref("");
const file = ref(null);
const router = useRouter();

const ask = async () => {
  try {
    const res = await chatWithLLM(query.value);
    answer.value = res.data.answer;
  } catch (err) {
    alert("问答失败：" + err.message);
  }
};

const handleFile = (e) => {
  file.value = e.target.files[0];
};

const upload = async () => {
  if (!file.value) return alert("请选择文件！");
  const formData = new FormData();
  formData.append("file", file.value);
  try {
    await uploadDocument(formData);
    alert("上传成功");
  } catch (err) {
    alert("上传失败：" + err.message);
  }
};

const logout = () => {
  localStorage.removeItem("token");
  router.push("/login");
};
</script>
