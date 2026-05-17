import { defineStore } from 'pinia';
import { TOKEN_KEY } from '../utils/http';

export const useUserStore = defineStore('user', {
  state: () => ({
    token: (localStorage.getItem(TOKEN_KEY) || '') as string,
    username: (localStorage.getItem('nuota_admin_username') || '') as string,
    realName: (localStorage.getItem('nuota_admin_realname') || '') as string,
    role: (localStorage.getItem('nuota_admin_role') || '') as string,
    consultantId: Number(localStorage.getItem('nuota_consultant_id') || '0'),
  }),
  actions: {
    setLogin(payload: { token: string; user?: any; role?: string; consultantId?: number }) {
      this.token = payload.token || '';
      this.role = payload.role || 'admin';
      this.username = payload.user?.username || payload.user?.phone || '';
      this.realName = payload.user?.real_name || payload.user?.name || '';
      this.consultantId = payload.consultantId || 0;
      localStorage.setItem(TOKEN_KEY, this.token);
      localStorage.setItem('nuota_admin_username', this.username);
      localStorage.setItem('nuota_admin_realname', this.realName);
      localStorage.setItem('nuota_admin_role', this.role);
      localStorage.setItem('nuota_consultant_id', String(this.consultantId));
    },
    logout() {
      this.token = '';
      this.username = '';
      this.realName = '';
      this.role = '';
      this.consultantId = 0;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem('nuota_admin_username');
      localStorage.removeItem('nuota_admin_realname');
      localStorage.removeItem('nuota_admin_role');
      localStorage.removeItem('nuota_consultant_id');
    },
  },
});
