import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router';
import { TOKEN_KEY } from '../utils/http';

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('../views/login/Login.vue'), meta: { title: '登录' } },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('../views/dashboard/Dashboard.vue'), meta: { title: '数据看板' } },
  { path: '/my-dashboard', component: () => import('../views/dashboard/ConsultantDashboard.vue'), meta: { title: '我的看板' } },
  { path: '/customers', component: () => import('../views/customers/CustomerBoard.vue'), meta: { title: '客户管理' } },
  { path: '/members', component: () => import('../views/members/MemberList.vue'), meta: { title: '学员管理' } },
  { path: '/members/:id', component: () => import('../views/members/MemberDetail.vue'), meta: { title: '学员详情' } },
  { path: '/payments', component: () => import('../views/members/PaymentList.vue'), meta: { title: '收款明细' } },
  { path: '/sessions', component: () => import('../views/sessions/SessionList.vue'), meta: { title: '场次管理' } },
  { path: '/checkins', component: () => import('../views/checkins/CheckinList.vue'), meta: { title: '签到管理' } },
  { path: '/referrals', component: () => import('../views/referrals/ReferralList.vue'), meta: { title: '推荐管理' } },
  { path: '/rewards', component: () => import('../views/rewards/RewardList.vue'), meta: { title: '权益台账' } },
  { path: '/bookings', component: () => import('../views/bookings/BookingList.vue'), meta: { title: '预约管理' } },
  { path: '/services', component: () => import('../views/services/ServiceList.vue'), meta: { title: '专案服务' } },
  { path: '/service-orders', component: () => import('../views/services/ServiceOrderList.vue'), meta: { title: '服务工单' } },
  { path: '/service-orders/:id', component: () => import('../views/services/ServiceOrderDetail.vue'), meta: { title: '工单详情' } },
  { path: '/consultants', component: () => import('../views/consultants/ConsultantList.vue'), meta: { title: '老师管理' } },
  { path: '/consultant-approval', component: () => import('../views/consultants/ConsultantApproval.vue'), meta: { title: '老师审核' } },
  { path: '/users', component: () => import('../views/users/UserManage.vue'), meta: { title: '账号管理' } },
  { path: '/quota', component: () => import('../views/quota/QuotaManage.vue'), meta: { title: '名额管理' } },
  { path: '/calendar', component: () => import('../views/calendar/CalendarView.vue'), meta: { title: '日历看板' } },
  { path: '/schedules', component: () => import('../views/schedule/ScheduleManage.vue'), meta: { title: '老师排期' } },
  { path: '/branches', component: () => import('../views/branch/BranchManage.vue'), meta: { title: '分公司管理' } },
  { path: '/operation-logs', component: () => import('../views/system/OperationLogs.vue'), meta: { title: '操作日志' } },
  { path: '/recycle-bin', component: () => import('../views/system/RecycleBin.vue'), meta: { title: '回收站' } },
  { path: '/courses', component: () => import('../views/courses/CourseList.vue'), meta: { title: '课程管理' } },
  { path: '/courses/:id', component: () => import('../views/courses/CourseDetail.vue'), meta: { title: '课程详情' } },
  { path: '/course-sessions', component: () => import('../views/course-sessions/CourseSessionList.vue'), meta: { title: '课程场次' } },
  { path: '/articles', component: () => import('../views/articles/ArticleList.vue'), meta: { title: '内容管理' } },
  { path: '/salary', component: () => import('../views/salary/SalaryManage.vue'), meta: { title: '工资管理' } },
  { path: '/promotion', component: () => import('../views/promotion/PromotionManage.vue'), meta: { title: '晋级管理' } },
  { path: '/banners', component: () => import('../views/banners/BannerManage.vue'), meta: { title: '广告位管理' } },
  { path: '/purchases', component: () => import('../views/purchases/PurchaseList.vue'), meta: { title: '采购管理' } },
  { path: '/talent-analysis', component: () => import('../views/talent/TalentAnalysis.vue'), meta: { title: '老师人才模型分析' } },
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
