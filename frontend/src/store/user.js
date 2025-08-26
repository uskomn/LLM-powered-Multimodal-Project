import { defineStore } from 'pinia';
import { login, register } from '@/api/auth';

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    role: localStorage.getItem('role') || '',
    userId: localStorage.getItem('userId') || null,
  }),
  actions: {
    async loginUser(data) {
      const res = await login(data);
      const { access_token, role, user_id } = res.data;

      this.token = access_token;
      this.role = role;
      this.userId = user_id;

      localStorage.setItem('token', access_token);
      localStorage.setItem('role', role);
      localStorage.setItem('userId', user_id);

      return res;
    },
    async registerUser(data) {
      const res = await register(data);
      // 注册成功，后端只返回用户信息，不返回token
      return res;
    },
    logout() {
      this.token = '';
      this.role = '';
      this.userId = null;
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      localStorage.removeItem('userId');
    }
  }
});
