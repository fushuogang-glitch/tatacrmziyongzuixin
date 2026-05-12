// 请求封装（带 JWT + 统一错误处理）
import { BASE_URL, TOKEN_KEY } from './config';

export interface Resp<T = any> {
  code: number;
  msg: string;
  data: T;
}

export function getToken(): string {
  return (uni.getStorageSync(TOKEN_KEY) as string) || '';
}

export function setToken(token: string): void {
  uni.setStorageSync(TOKEN_KEY, token);
}

export function clearToken(): void {
  uni.removeStorageSync(TOKEN_KEY);
}

function buildHeader(custom: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  const base: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) base.Authorization = `Bearer ${token}`;
  return { ...base, ...custom };
}

export function request<T = any>(opts: {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  data?: any;
  header?: Record<string, string>;
}): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + opts.url,
      method: opts.method || 'GET',
      data: opts.data,
      header: buildHeader(opts.header),
      success: (res: any) => {
        const body = res.data as Resp<T>;
        if (res.statusCode >= 200 && res.statusCode < 300) {
          if (body && body.code === 0) {
            resolve(body.data);
          } else {
            uni.showToast({ title: (body && body.msg) || '接口异常', icon: 'none' });
            reject(body);
          }
        } else if (res.statusCode === 401) {
          clearToken();
          uni.reLaunch({ url: '/pages/login/login' });
          reject(res);
        } else {
          uni.showToast({ title: `HTTP ${res.statusCode}`, icon: 'none' });
          reject(res);
        }
      },
      fail: (err) => {
        uni.showToast({ title: '网络异常', icon: 'none' });
        reject(err);
      },
    });
  });
}
