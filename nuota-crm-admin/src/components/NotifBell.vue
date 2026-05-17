<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { API, TOKEN_KEY } from '../api';

const router = useRouter();
const unreadCount = ref(0);
const notifications = ref<any[]>([]);
const visible = ref(false);
const loading = ref(false);
let timer: ReturnType<typeof setInterval> | null = null;

const ntypeIcon: Record<string, string> = {
  booking: '📅',
  order: '📋',
  application: '👤',
  info: '📢',
};
const ntypeColor: Record<string, string> = {
  booking: '#7b6fdf',
  order: '#c9a96e',
  application: '#4a90d9',
  info: '#52c41a',
};

async function fetchUnread() {
  try {
    const res: any = await API.get('/admin/notifications?unread_only=true&limit=5');
    unreadCount.value = res.data?.unread_count || 0;
    if (visible.value) {
      notifications.value = res.data?.items || [];
    }
  } catch { }
}

async function openPanel() {
  visible.value = !visible.value;
  if (visible.value) {
    loading.value = true;
    try {
      const res: any = await API.get('/admin/notifications?limit=30');
      notifications.value = res.data?.items || [];
      unreadCount.value = res.data?.unread_count || 0;
    } finally {
      loading.value = false;
    }
  }
}

async function markRead(id: number) {
  await API.post(`/admin/notifications/read/${id}`);
  const n = notifications.value.find(n => n.id === id);
  if (n) { n.is_read = true; unreadCount.value = Math.max(0, unreadCount.value - 1); }
}

async function markAllRead() {
  await API.post('/admin/notifications/read-all');
  notifications.value.forEach(n => n.is_read = true);
  unreadCount.value = 0;
}

function handleClick(n: any) {
  markRead(n.id);
  if (n.ref_type === 'consultant_application') {
    router.push('/consultant-approval');
  } else if (n.ref_type === 'service_order') {
    router.push('/service-orders');
  } else if (n.ref_type === 'visit_booking') {
    router.push('/bookings');
  }
  visible.value = false;
}

onMounted(() => {
  // 延迟 800ms 再拉，确保登录后 token 已写入 localStorage
  setTimeout(() => {
    if (localStorage.getItem(TOKEN_KEY)) fetchUnread();
  }, 800);
  timer = setInterval(() => {
    if (localStorage.getItem(TOKEN_KEY)) fetchUnread();
  }, 30000);
});
onUnmounted(() => { if (timer) clearInterval(timer); });
</script>

<template>
  <div class="notif-wrap">
    <!-- 铃铛按钮 -->
    <button class="bell-btn" @click="openPanel">
      <span class="bell-icon">🔔</span>
      <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>

    <!-- 通知面板 -->
    <div v-if="visible" class="notif-panel" v-loading="loading">
      <div class="panel-header">
        <span class="ph-title">消息通知</span>
        <span v-if="unreadCount > 0" class="ph-unread">{{ unreadCount }} 条未读</span>
        <button v-if="unreadCount > 0" class="ph-read-all" @click="markAllRead">全部已读</button>
        <button class="ph-close" @click="visible = false">✕</button>
      </div>
      <div class="panel-body">
        <div v-if="notifications.length === 0" class="empty">暂无通知</div>
        <div v-for="n in notifications" :key="n.id"
          :class="['notif-item', { unread: !n.is_read }]"
          @click="handleClick(n)">
          <div class="ni-icon" :style="{ color: ntypeColor[n.ntype] || '#888' }">
            {{ ntypeIcon[n.ntype] || '📢' }}
          </div>
          <div class="ni-content">
            <div class="ni-title">{{ n.title }}</div>
            <div class="ni-body" v-if="n.body">{{ n.body }}</div>
            <div class="ni-time">{{ n.created_at }}</div>
          </div>
          <div v-if="!n.is_read" class="ni-dot"></div>
        </div>
      </div>
    </div>

    <!-- 点击外部关闭 -->
    <div v-if="visible" class="overlay" @click="visible = false"></div>
  </div>
</template>

<style scoped>
.notif-wrap { position: relative; }

.bell-btn {
  position: relative;
  width: 36px; height: 36px;
  border: none; background: transparent;
  cursor: pointer; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
  transition: background .15s;
}
.bell-btn:hover { background: rgba(255,255,255,0.08); }
.badge {
  position: absolute;
  top: 2px; right: 2px;
  min-width: 16px; height: 16px;
  background: #e84c4c;
  color: #fff; font-size: 10px; font-weight: 700;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  padding: 0 3px;
  line-height: 1;
}

.notif-panel {
  position: absolute;
  top: 44px; right: 0;
  width: 360px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.4);
  z-index: 1000;
  overflow: hidden;
}
.panel-header {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 16px;
  border-bottom: 1px solid #2a2a2a;
  background: #111;
}
.ph-title { font-size: 14px; font-weight: 700; color: #e8e0d0; flex: 1; }
.ph-unread { font-size: 12px; color: #c9a96e; }
.ph-read-all {
  font-size: 12px; color: #7b6fdf; background: none;
  border: none; cursor: pointer; padding: 0;
}
.ph-read-all:hover { text-decoration: underline; }
.ph-close {
  width: 22px; height: 22px; border: none; background: none;
  color: #666; cursor: pointer; font-size: 12px; border-radius: 50%;
}
.ph-close:hover { color: #e84c4c; }

.panel-body { max-height: 420px; overflow-y: auto; }
.empty { padding: 32px; text-align: center; color: #555; font-size: 13px; }

.notif-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #1e1e1e;
  cursor: pointer;
  transition: background .15s;
  position: relative;
}
.notif-item:hover { background: rgba(255,255,255,0.04); }
.notif-item.unread { background: rgba(201,169,110,0.05); }
.notif-item:last-child { border-bottom: none; }

.ni-icon { font-size: 18px; flex-shrink: 0; margin-top: 2px; }
.ni-content { flex: 1; min-width: 0; }
.ni-title { font-size: 13px; font-weight: 600; color: #e8e0d0; line-height: 1.4; }
.ni-body { font-size: 12px; color: #888; margin-top: 3px; line-height: 1.4;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ni-time { font-size: 11px; color: #555; margin-top: 4px; }
.ni-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #c9a96e; flex-shrink: 0; margin-top: 6px;
}

.overlay {
  position: fixed; inset: 0; z-index: 999;
}
</style>
