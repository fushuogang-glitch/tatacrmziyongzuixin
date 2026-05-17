// axios 实例 + token
import axios from 'axios';
import { ElMessage } from 'element-plus';

export const TOKEN_KEY = 'nuota_admin_token';

const BASE = import.meta.env.VITE_API_BASE || '';
const http = axios.create({ baseURL: BASE, timeout: 15000 });

http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem(TOKEN_KEY) || '';
  if (token) cfg.headers = { ...cfg.headers, Authorization: `Bearer ${token}` } as any;
  return cfg;
});

// 防抖：同一秒内只弹一次 401 提示
let _401Timer: ReturnType<typeof setTimeout> | null = null;
let _401Count = 0;

http.interceptors.response.use(
  (res) => {
    const body = res.data;
    if (body && typeof body.code === 'number') {
      if (body.code === 0) return body.data;
      ElMessage.error(body.msg || '接口异常');
      return Promise.reject(body);
    }
    return res.data;
  },
  (err) => {
    const status = err.response?.status;
    const msg = err.response?.data?.detail || err.response?.data?.msg || err.message;

    if (status === 401) {
      _401Count++;
      // 500ms 内收集所有 401，只处理一次
      if (_401Timer) clearTimeout(_401Timer);
      _401Timer = setTimeout(() => {
        const token = localStorage.getItem(TOKEN_KEY);
        const onLogin = location.hash.indexOf('login') !== -1;
        // 只有在已登录状态下连续 401 才视为 token 过期，踢回登录
        if (!onLogin && !token) {
          // token 本来就没有，忽略
        } else if (!onLogin && token) {
          // token 有但服务端拒绝 → 真正过期
          localStorage.removeItem(TOKEN_KEY);
          ElMessage.error('登录已过期，请重新登录');
          setTimeout(() => { location.hash = '#/login'; }, 1000);
        }
        _401Count = 0;
        _401Timer = null;
      }, 500);
      // 静默处理，不弹错误
      return Promise.reject(err);
    }

    if (status !== 401) {
      const isNetworkErr = !err.response && (err.message === 'Network Error' || err.code === 'ERR_NETWORK');
      ElMessage.error(isNetworkErr ? '网络连接失败，请检查网络后重试' : (msg || '请求异常，请稍后重试'));
    }
    return Promise.reject(err);
  },
);

export default http;
