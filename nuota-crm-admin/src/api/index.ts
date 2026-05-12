// 管理后台 API
import http from '../utils/http';

export const API = {
  // 登录
  login: (username: string, password: string) =>
    http.post('/admin/auth/login', { username, password }),

  // 看板
  dashboard: () => http.get('/admin/dashboard'),

  // 学员
  memberList: (params: any) => http.get('/admin/members', { params }),
  memberCreate: (body: any) => http.post('/admin/members', body),
  memberUpdate: (id: number, body: any) => http.put(`/admin/members/${id}`, body),
  memberDetail: (id: number) => http.get(`/admin/members/${id}`),

  // 缴费
  paymentCreate: (body: any) => http.post('/admin/payments', body),
  paymentList: (member_id?: number) =>
    http.get('/admin/payments', { params: member_id ? { member_id } : {} }),

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

  // 名额
  quotaMonthly: (year: number, month: number) =>
    http.get('/admin/quota/monthly', { params: { year, month } }),
  quotaSet: (year: number, month: number, cap: number) =>
    http.put('/admin/quota/set', null, { params: { year, month, cap } }),
};
