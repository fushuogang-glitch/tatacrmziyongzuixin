// axios 实例 + token
import axios from 'axios';
import { ElMessage } from 'element-plus';

export const TOKEN_KEY = 'nuota_admin_token';

const http = axios.create({ baseURL: '', timeout: 15000 });

http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem(TOKEN_KEY) || '';
  if (token) cfg.headers = { ...cfg.headers, Authorization: `Bearer ${token}` } as any;
  return cfg;
});

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
    const msg = err.response?.data?.msg || err.message;
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      if (location.hash.indexOf('login') === -1) location.hash = '#/login';
    }
    ElMessage.error(msg || '网络异常');
    return Promise.reject(err);
  },
);

export default http;
