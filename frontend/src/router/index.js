import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/login.vue'
import Register from '../views/register.vue'
import Main from '../views/main.vue'

const routes = [
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: "/", component: Main },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("token");
  if (to.path !== "/login" && to.path !== "/register" && !token) {
    next("/login");
  } else {
    next();
  }
});

export default router
