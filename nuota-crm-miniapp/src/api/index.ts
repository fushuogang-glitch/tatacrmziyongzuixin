// 学员相关 API
import { request } from '../utils/request';

export const api = {
  // 认证
  wxLogin: (code: string) =>
    request({ url: '/api/auth/wx-login', method: 'POST', data: { code } }),

  register: (body: any) =>
    request({ url: '/api/members/register', method: 'POST', data: body }),

  // 推荐码验证（会员推荐码 / 老师推荐码）
  verifyReferral: (code: string) =>
    request({ url: '/api/referral/verify', data: { code } }),

  // 企业邀请码验证
  verifyInvite: (code: string) =>
    request({ url: '/api/enterprise/invite/verify', data: { code } }),

  // 企业
  createEnterprise: (body: any) =>
    request({ url: '/api/enterprise/create', method: 'POST', data: body }),
  myEnterprise: () => request({ url: '/api/enterprise/mine' }),

  me: () => request({ url: '/api/members/me' }),

  // 人脸
  bindFace: (face_base64: string) =>
    request({ url: '/api/face/bind', method: 'POST', data: { face_base64 } }),

  faceStatus: () => request({ url: '/api/face/status' }),

  faceCheckin: (body: { session_id: number; face_base64: string; checkin_day?: number }) =>
    request({ url: '/api/checkin/face', method: 'POST', data: body }),

  // 场次
  availableSessions: () => request({ url: '/api/sessions/available' }),
  enrollSession: (sid: number) =>
    request({ url: `/api/sessions/${sid}/enroll`, method: 'POST' }),

  // 推荐
  myCode: () => request({ url: '/api/referrals/my-code' }),
  myRefList: () => request({ url: '/api/referrals/my-list' }),

  // 权益
  myRewards: () => request({ url: '/api/rewards/my-rewards' }),

  // 预约
  applyBooking: (body: any) =>
    request({ url: '/api/bookings/apply', method: 'POST', data: body }),
  myBookings: () => request({ url: '/api/bookings/my-bookings' }),

  // 日历排期（公开接口）
  calendarConsultants: () => request({ url: '/api/calendar/consultants' }),
  calendarSlots: (consultantId: number, startDate: string, endDate: string) =>
    request({ url: '/api/calendar/slots', data: { consultant_id: consultantId, start_date: startDate, end_date: endDate } }),

  // 手册
  getHandbook: (sid: number) => request({ url: `/api/handbooks/${sid}` }),
  saveHandbook: (sid: number, body: any) =>
    request({ url: `/api/handbooks/${sid}`, method: 'PUT', data: body }),

  // 专案服务
  listServices: (category?: string) =>
    request({ url: '/api/v1/services', data: category ? { category } : {} }),
  getService: (id: number) => request({ url: `/api/v1/services/${id}` }),
  myServicePackages: (mid: number) =>
    request({ url: '/api/v1/services/packages/my', data: { member_id: mid } }),
  createServiceOrder: (body: any) =>
    request({ url: '/api/v1/services/orders', method: 'POST', data: body }),
  myServiceOrders: (mid: number, status?: string) =>
    request({ url: '/api/v1/services/orders/my', data: { member_id: mid, ...(status ? { status } : {}) } }),
  getServiceOrder: (id: number) =>
    request({ url: `/api/v1/services/orders/${id}` }),
  rateServiceOrder: (id: number, body: { rating: number; comment?: string }) =>
    request({ url: `/api/v1/services/orders/${id}/rating`, method: 'POST', data: body }),

  // 工单执案日志（老师填写，客户只读）
  orderLogs: (id: number) =>
    request({ url: `/api/v1/services/orders/${id}/logs` }),

  // 工单实时进度（步骤条）
  orderProgress: (id: number) =>
    request({ url: `/api/v1/services/orders/${id}/progress` }),

  // 我的排期（工单+下店+手动排期）
  mySchedules: () => request({ url: '/api/members/my-schedules' }),

  // 企业学员
  staffList: () => request({ url: '/api/staff/list' }),
  staffAdd: (body: any) =>
    request({ url: '/api/staff/add', method: 'POST', data: body }),
  staffUpdate: (id: number, body: any) =>
    request({ url: `/api/staff/${id}`, method: 'PUT', data: body }),
  staffDelete: (id: number) =>
    request({ url: `/api/staff/${id}`, method: 'DELETE' }),
  staffDetail: (id: number) => request({ url: `/api/staff/${id}` }),
  staffBindFace: (id: number, face_base64: string) =>
    request({ url: `/api/staff/${id}/bindface`, method: 'POST', data: { face_base64 } }),

  // 协议签约
  getAgreement: () => request({ url: '/api/v1/agreements/current' }),
  checkAgreement: (mid: number) =>
    request({ url: '/api/v1/agreements/check', data: { member_id: mid } }),
  signAgreement: (body: { member_id: number; signature?: string }) =>
    request({ url: '/api/v1/agreements/sign', method: 'POST', data: body }),

  // 每日一念
  dailyThought: () => request({ url: '/api/daily-thought/today' }),
  dailyThoughtSaveProfile: (body: any) =>
    request({ url: '/api/daily-thought/profile', method: 'PUT', data: body }),

  // 文章/动态
  articleList: (params?: { category?: string }) =>
    request({ url: '/api/v1/articles', data: params || {} }),
  articleDetail: (id: number) =>
    request({ url: `/api/v1/articles/${id}` }),

  // 课程场次
  courseSessionList: () =>
    request({ url: '/api/v1/course-sessions' }),
  courseSessionDetail: (id: number) =>
    request({ url: `/api/v1/course-sessions/${id}` }),
  courseSessionEnroll: (id: number, body: any) =>
    request({ url: `/api/v1/course-sessions/${id}/enroll`, method: 'POST', data: body }),
  myCourseEnrollments: () =>
    request({ url: '/api/v1/course-sessions/my-enrollments' }),
};
