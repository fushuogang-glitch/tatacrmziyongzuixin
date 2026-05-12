import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router';
import { TOKEN_KEY } from '../utils/http';

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('../views/login/Login.vue'), meta: { title: '登录' } },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('../views/dashboard/Dashboard.vue'), meta: { title: '数据看板' } },
  { path: '/members', component: () => import('../views/members/MemberList.vue'), meta: { title: '学员管理' } },
  { path: '/members/:id', component: () => import('../views/members/MemberDetail.vue'), meta: { title: '学员详情' } },
  { path: '/sessions', component: () => import('../views/sessions/SessionList.vue'), meta: { title: '场次管理' } },
  { path: '/checkins', component: () => import('../views/checkins/CheckinList.vue'), meta: { title: '签到管理' } },
  { path: '/referrals', component: () => import('../views/referrals/ReferralList.vue'), meta: { title: '推荐管理' } },
  { path: '/rewards', component: () => import('../views/rewards/RewardList.vue'), meta: { title: '权益台账' } },
  { path: '/bookings', component: () => import('../views/bookings/BookingList.vue'), meta: { title: '下店预约' } },
  { path: '/consultants', component: () => import('../views/consultants/ConsultantList.vue'), meta: { title: '顾问管理' } },
  { path: '/quota', component: () => import('../views/quota/QuotaManage.vue'), meta: { title: '名额管理' } },
];

const router = createRouter({ history: createWebHashHistory(), routes });

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (to.path !== '/login' && !token) return next('/login');
  if (to.path === '/login' && token) return next('/dashboard');
  document.title = `${to.meta?.title || ''} · 诺控·塔塔 CRM`;
  next();
});

export default router;
