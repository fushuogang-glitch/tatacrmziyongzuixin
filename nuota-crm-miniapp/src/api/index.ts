// 学员相关 API
import { request } from '../utils/request';

export const api = {
  // 认证
  wxLogin: (code: string) =>
    request({ url: '/api/auth/wx-login', method: 'POST', data: { code } }),

  register: (body: any) =>
    request({ url: '/api/members/register', method: 'POST', data: body }),

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

  // 手册
  getHandbook: (sid: number) => request({ url: `/api/handbooks/${sid}` }),
  saveHandbook: (sid: number, body: any) =>
    request({ url: `/api/handbooks/${sid}`, method: 'PUT', data: body }),
};
