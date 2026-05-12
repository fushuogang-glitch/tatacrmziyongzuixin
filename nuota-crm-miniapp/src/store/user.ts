// 全局状态：用户
import { defineStore } from 'pinia';
import { USER_KEY, TOKEN_KEY } from '../utils/config';

export const useUserStore = defineStore('user', {
  state: () => ({
    user: (uni.getStorageSync(USER_KEY) as any) || null,
    token: (uni.getStorageSync(TOKEN_KEY) as string) || '',
  }),
  actions: {
    setUser(u: any) {
      this.user = u;
      uni.setStorageSync(USER_KEY, u);
    },
    setToken(t: string) {
      this.token = t;
      uni.setStorageSync(TOKEN_KEY, t);
    },
    logout() {
      this.user = null;
      this.token = '';
      uni.removeStorageSync(USER_KEY);
      uni.removeStorageSync(TOKEN_KEY);
    },
  },
});
