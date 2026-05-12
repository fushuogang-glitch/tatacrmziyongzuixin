<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '../store/user';

const route = useRoute();
const router = useRouter();
const user = useUserStore();

const menu = [
  { path: '/dashboard', title: '数据看板', icon: 'DataLine' },
  { path: '/members', title: '学员管理', icon: 'User' },
  { path: '/sessions', title: '场次管理', icon: 'Calendar' },
  { path: '/checkins', title: '签到管理', icon: 'Check' },
  { path: '/referrals', title: '推荐管理', icon: 'Share' },
  { path: '/rewards', title: '权益台账', icon: 'Present' },
  { path: '/bookings', title: '下店预约', icon: 'Location' },
  { path: '/consultants', title: '顾问管理', icon: 'Avatar' },
  { path: '/quota', title: '名额管理', icon: 'PieChart' },
];

const active = computed(() => {
  const hit = menu.find(m => route.path.startsWith(m.path));
  return hit?.path || '/dashboard';
});

function handleLogout() {
  user.logout();
  router.push('/login');
}
</script>

<template>
  <el-container style="height: 100vh;">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <span class="logo-main">诺控·塔塔</span>
        <span class="logo-sub">CRM 管理后台</span>
      </div>
      <el-menu :default-active="active" router class="menu">
        <el-menu-item v-for="m in menu" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <template #title>{{ m.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="title">{{ route.meta?.title }}</div>
        <div class="user">
          <span>{{ user.realName || user.username || '管理员' }}</span>
          <el-dropdown @command="handleLogout">
            <el-icon style="margin-left: 8px;"><ArrowDown /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.aside { background: #1f2d3d; color: #fff; }
.logo { padding: 24px 20px; border-bottom: 1px solid #2d3e52; }
.logo-main { display: block; font-size: 18px; font-weight: 700; letter-spacing: 2px; color: #fff; }
.logo-sub { display: block; margin-top: 4px; font-size: 12px; color: #8ea0b5; }
.menu { border: 0; background: transparent; }
.menu :deep(.el-menu-item) { color: #c0ccda; }
.menu :deep(.el-menu-item.is-active) { background: #409EFF !important; color: #fff; }
.menu :deep(.el-menu-item:hover) { background: #2d3e52; }
.header { display: flex; justify-content: space-between; align-items: center; background: #fff; border-bottom: 1px solid #ebeef5; }
.title { font-size: 16px; font-weight: 600; }
.user { color: #606266; font-size: 14px; cursor: pointer; }
.main { padding: 20px; background: #f5f7fa; }
</style>
