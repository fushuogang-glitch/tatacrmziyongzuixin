// 管理后台 API
import http from '../utils/http';
export { TOKEN_KEY } from '../utils/http';

export const API = {
  // 登录
  login: (username: string, password: string) =>
    http.post('/admin/auth/login', { username, password }),

  // 看板
  dashboard: () => http.get('/admin/dashboard'),
  dashboardV2: (year?: number, month?: number) =>
    http.get('/admin/dashboard/v2', { params: { ...(year ? { year } : {}), ...(month ? { month } : {}) } }),
  dashboardCockpit: (targetDate?: string) =>
    http.get('/admin/dashboard/cockpit', { params: targetDate ? { target_date: targetDate } : {} }),

  // 学员
  memberList: (params: any) => http.get('/admin/members', { params }),
  // 客户管理面板（卡片视图）
  customerList: (params?: any) => http.get('/admin/customers', { params: params || {} }),
  customerFilters: () => http.get('/admin/customers/filters'),
  customerStats: () => http.get('/admin/customers/stats'),
  customerCreate: (body: any) => http.post('/admin/customers', body),
  customerUpdate: (id: number, body: any) => http.put(`/admin/customers/${id}`, body),
  phoneGrantApply: (body: any) => http.post('/admin/customers/phone-grant/apply', body),
  phoneGrantPending: () => http.get('/admin/customers/phone-grant/pending'),
  phoneGrantReview: (body: any) => http.post('/admin/customers/phone-grant/review', body),
  memberCreate: (body: any) => http.post('/admin/members', body),
  memberUpdate: (id: number, body: any) => http.put(`/admin/members/${id}`, body),
  memberDetail: (id: number) => http.get(`/admin/members/${id}`),
  memberDelete: (id: number) => http.delete(`/admin/members/${id}`),

  // 缴费
  paymentCreate: (body: any) => http.post('/admin/payments', body),
  paymentDelete: (id: number) => http.delete(`/admin/payments/${id}`),
  paymentList: (member_id?: number) =>
    http.get('/admin/payments', { params: member_id ? { member_id } : {} }),
  consumptionList: (params?: any) =>
    http.get('/admin/services/consumptions', { params: params || {} }),

  // 场次
  sessionList: () => http.get('/admin/sessions'),
  sessionCreate: (body: any) => http.post('/admin/sessions', body),
  sessionUpdate: (id: number, body: any) => http.put(`/admin/sessions/${id}`, body),
  sessionStatus: (id: number, status_value: string) =>
    http.put(`/admin/sessions/${id}/status`, null, { params: { status_value } }),

  // 签到
  checkinList: (sid: number) => http.get(`/admin/checkins/${sid}`),
  manualCheckin: (member_id: number, session_id: number, checkin_day: number) =>
    http.post('/admin/checkins/manual', null, {
      params: { member_id, session_id, checkin_day },
    }),

  // 推荐 / 权益
  referralList: () => http.get('/admin/referrals'),
  referralConfirm: (id: number) => http.put(`/admin/referrals/${id}/confirm`),
  rewardList: (status?: string) =>
    http.get('/admin/rewards', { params: status ? { status } : {} }),

  // 会员等级台账
  membersByTier: () => http.get('/admin/members/by-tier'),

  // 预约
  bookingList: (status?: string) =>
    http.get('/admin/bookings', { params: status ? { status } : {} }),
  bookingConfirm: (id: number, body: any) =>
    http.put(`/admin/bookings/${id}/confirm`, body),
  bookingComplete: (id: number, body: any) =>
    http.put(`/admin/bookings/${id}/complete`, body),
  bookingCancel: (id: number) => http.put(`/admin/bookings/${id}/cancel`),

  // 顾问
  consultantList: () => http.get('/admin/consultants'),
  consultantCreate: (body: any) => http.post('/admin/consultants', body),
  consultantUpdate: (id: number, body: any) => http.put(`/admin/consultants/${id}`, body),

  // 文件上传
  uploadImage: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return http.post('/admin/upload/image', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  // 老师排期
  scheduleList: (params: { consultant_id?: number; year?: number; month?: number } = {}) =>
    http.get('/admin/schedules', { params }),
  scheduleCreate: (body: any) => http.post('/admin/schedules', body),
  scheduleBatchCreate: (body: any) => http.post('/admin/schedules/batch', body),
  scheduleUpdate: (id: number, body: any) => http.put(`/admin/schedules/${id}`, body),
  scheduleDelete: (id: number) => http.delete(`/admin/schedules/${id}`),

  // 分公司
  branchList: (status?: string) => http.get('/admin/branches', { params: status ? { status } : {} }),
  branchCreate: (body: any) => http.post('/admin/branches', body),
  branchUpdate: (id: number, body: any) => http.put(`/admin/branches/${id}`, body),
  branchDelete: (id: number) => http.delete(`/admin/branches/${id}`),

  // 名额
  quotaMonthly: (year: number, month: number) =>
    http.get('/admin/quota/monthly', { params: { year, month } }),
  quotaSet: (year: number, month: number, cap: number) =>
    http.put('/admin/quota/set', null, { params: { year, month, cap } }),

  // 专案服务管理
  serviceList: () => http.get('/admin/services'),
  serviceCreate: (body: any) => http.post('/admin/services', body),
  serviceUpdate: (id: number, body: any) => http.put(`/admin/services/${id}`, body),
  serviceDelete: (id: number) => http.delete(`/admin/services/${id}`),
  serviceToggle: (id: number) => http.put(`/admin/services/${id}/toggle`),

  // 服务工单
  serviceOrderList: (params: { status?: string; consultant_id?: number } = {}) =>
    http.get('/admin/services/orders', { params }),
  serviceOrderUpdate: (id: number, body: any) =>
    http.put(`/admin/services/orders/${id}`, body),
  serviceOrderLogs: (id: number) =>
    http.get(`/admin/services/orders/${id}/work-logs`),
  serviceOrderAddLog: (id: number, body: any) =>
    http.post(`/admin/services/orders/${id}/work-logs`, body),

  // 工单流程引擎 API
  serviceOrderWorkflow: (id: number) =>
    http.get(`/admin/services/orders/${id}/workflow`),
  serviceOrderConfirm: (id: number, body: any) =>
    http.put(`/admin/services/orders/${id}/confirm`, body),
  serviceOrderAccept: (id: number, body: any) =>
    http.put(`/admin/services/orders/${id}/accept`, body),
  serviceOrderPrepare: (id: number, body: any) =>
    http.put(`/admin/services/orders/${id}/prepare`, body),
  serviceOrderStart: (id: number, body: any) =>
    http.put(`/admin/services/orders/${id}/start`, body),
  serviceOrderDayLog: (id: number, body: any) =>
    http.post(`/admin/services/orders/${id}/day-log`, body),
  serviceOrderReport: (id: number, body: any) =>
    http.put(`/admin/services/orders/${id}/report`, body),
  serviceOrderFollowup: (id: number, body: any) =>
    http.post(`/admin/services/orders/${id}/followup`, body),
  serviceOrderComplete: (id: number) =>
    http.put(`/admin/services/orders/${id}/complete`),
  serviceOrderCancel: (id: number) =>
    http.put(`/admin/services/orders/${id}/cancel`),

  // 通用方法（用于新接口）
  get: (url: string, config?: any) => http.get(url, config),
  post: (url: string, body?: any, config?: any) => http.post(url, body, config),
  put: (url: string, body?: any) => http.put(url, body),

  // 跟进记录
  followupList: (memberId: number) => http.get(`/admin/members/${memberId}/followups`),
  followupAdd: (memberId: number, body: any) => http.post(`/admin/members/${memberId}/followups`, body),
  followupDelete: (id: number) => http.delete(`/admin/followups/${id}`),
  dailyThoughtProfile: (memberId: number) => http.get(`/admin/daily-thought/members/${memberId}/profile`),
  dailyThoughtProfileSave: (memberId: number, body: any) =>
    http.put(`/admin/daily-thought/members/${memberId}/profile`, body),

  // 操作日志
  operationLogs: (params?: any) => http.get('/admin/operation-logs', { params }),

  // 回收站
  recycleBin: (params?: any) => http.get('/admin/recycle-bin', { params }),
  recycleRestore: (id: number) => http.post(`/admin/recycle-bin/${id}/restore`),

  // 数据导出（返回blob）
  exportMembers: () => http.get('/admin/export/members', { responseType: 'blob' }),
  exportPayments: () => http.get('/admin/export/payments', { responseType: 'blob' }),
  menuBadges: () => http.get('/admin/stats/menu-badges'),

  // 课程管理
  courseList: (params?: any) => http.get('/admin/courses', { params }),
  courseCreate: (data: any) => http.post('/admin/courses', data),
  courseDetail: (id: number) => http.get(`/admin/courses/${id}`),
  courseUpdate: (id: number, data: any) => http.put(`/admin/courses/${id}`, data),
  coursePublish: (id: number) => http.put(`/admin/courses/${id}/publish`),
  courseEnrollments: (params?: any) => http.get('/admin/courses/enrollments', { params }),
  courseEnrollContact: (id: number, data: any) => http.put(`/admin/courses/enrollments/${id}/contact`, data),
  courseEnrollNotify: (id: number) => http.put(`/admin/courses/enrollments/${id}/notify`),
  courseEnrollCheckin: (id: number, method: string) => http.put(`/admin/courses/enrollments/${id}/checkin`, null, { params: { method } }),
  courseEnrollFollowup: (id: number, data: any) => http.post(`/admin/courses/enrollments/${id}/followup`, data),
  courseEnrollComplete: (id: number) => http.put(`/admin/courses/enrollments/${id}/complete`),
  courseEnd: (id: number) => http.put(`/admin/courses/${id}/end`),
  courseReview: (id: number, data: any) => http.put(`/admin/courses/${id}/review`, data),

  // 内容管理
  articleList: (params?: any) => http.get('/admin/articles', { params }),
  articleCreate: (data: any) => http.post('/admin/articles', data),
  articleUpdate: (id: number, data: any) => http.put(`/admin/articles/${id}`, data),
  articlePublish: (id: number) => http.put(`/admin/articles/${id}/publish`),
  articleUnpublish: (id: number) => http.put(`/admin/articles/${id}/unpublish`),
  articleDelete: (id: number) => http.delete(`/admin/articles/${id}`),

  // 课程场次管理
  courseSessionList: (params?: any) => http.get('/admin/course-sessions', { params }),
  courseSessionCreate: (data: any) => http.post('/admin/course-sessions', data),
  courseSessionUpdate: (id: number, data: any) => http.put(`/admin/course-sessions/${id}`, data),
  courseSessionDelete: (id: number) => http.delete(`/admin/course-sessions/${id}`),
  courseSessionEnd: (id: number) => http.put(`/admin/course-sessions/${id}/end`),
  courseSessionEnrollments: (id: number) => http.get(`/admin/course-sessions/${id}/enrollments`),
  courseSessionAddEnrollment: (id: number, data: any) => http.post(`/admin/course-sessions/${id}/enrollments`, data),
  courseSessionCheckin: (id: number, data: any) => http.post(`/admin/course-sessions/${id}/checkin`, data),
  courseEnrollmentPay: (id: number, data: any) => http.put(`/admin/course-sessions/enrollments/${id}/pay`, data),
  courseEnrollmentDeal: (id: number, data: any) => http.put(`/admin/course-sessions/enrollments/${id}/deal`, data),
  courseEnrollmentFollowup: (id: number, data: any) => http.post(`/admin/course-sessions/enrollments/${id}/followup`, data),

  // 采购管理
  purchaseList: (params?: any) => http.get('/admin/purchases', { params: params || {} }),
  purchaseCreate: (body: any) => http.post('/admin/purchases', body),
  purchaseUpdate: (id: number, body: any) => http.put(`/admin/purchases/${id}`, body),
  purchaseDelete: (id: number) => http.delete(`/admin/purchases/${id}`),

  // 会员储值
  memberRecharges: (memberId: number) => http.get(`/admin/members/${memberId}/recharges`),
  rechargeCreate: (body: any) => http.post('/admin/recharges', body),
  rechargeConsume: (id: number, body: any) => http.post(`/admin/recharges/${id}/consume`, body),
  rechargeConsumptions: (id: number) => http.get(`/admin/recharges/${id}/consumptions`),

  // 会员深度分析（塔才回写）
  memberDeepAnalysis: (memberId: number) => http.get(`/admin/members/${memberId}/deep-analysis`),
  memberDeepAnalysisSubmit: (memberId: number, body: { raw_text: string; raw_images?: string[] }) =>
    http.post(`/admin/members/${memberId}/deep-analysis`, body),

  // 老师人才模型分析
  talentAnalysisList: (params?: any) => http.get('/admin/talent-analysis', { params: params || {} }),
  consultantTalentAnalysis: (consultantId: number) =>
    http.get(`/admin/consultants/${consultantId}/talent-analysis`),
  consultantTalentAnalysisSubmit: (consultantId: number, body: { raw_text: string; raw_images?: string[] }) =>
    http.post(`/admin/consultants/${consultantId}/talent-analysis`, body),

  // 财务管理 v2.2
  financeOverview: (month: string) => http.get('/admin/finance/overview', { params: { month } }),
  financeBranchMonthly: (bid: number, month: string) => http.get(`/admin/finance/branch/${bid}/monthly`, { params: { month } }),
  financeBreakeven: (bid: number, month: string) => http.get(`/admin/finance/branch/${bid}/breakeven`, { params: { month } }),
  financeBreakevenConfig: (bid: number) => http.get(`/admin/finance/branch/${bid}/breakeven-config`),
  financeBreakevenConfigSet: (bid: number, body: any) => http.put(`/admin/finance/branch/${bid}/breakeven-config`, body),
  financeIncomeDetail: (params: any) => http.get('/admin/finance/income-detail', { params }),
  financeExpenseDetail: (params: any) => http.get('/admin/finance/expense-detail', { params }),
  financeFixedCosts: (params?: any) => http.get('/admin/finance/fixed-costs', { params: params || {} }),
  financeFixedCostCreate: (body: any) => http.post('/admin/finance/fixed-costs', body),
  financeFixedCostUpdate: (id: number, body: any) => http.put(`/admin/finance/fixed-costs/${id}`, body),
  financeFixedCostDelete: (id: number) => http.delete(`/admin/finance/fixed-costs/${id}`),
};
