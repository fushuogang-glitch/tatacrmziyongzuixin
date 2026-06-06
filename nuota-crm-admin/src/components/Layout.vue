<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '../store/user';
import { API } from '../api';
import NotifBell from './NotifBell.vue';

const route = useRoute();
const router = useRouter();
const user = useUserStore();

const badges = ref<Record<string, number>>({});
const viewportWidth = ref(typeof window === 'undefined' ? 1440 : window.innerWidth);
const mobileDrawerVisible = ref(false);

// 分组菜单
const menuGroups = [
  {
    label: '总览', icon: 'Odometer',
    items: [
      { path: '/dashboard', title: '经营驾驶舱', icon: 'DataLine', adminOnly: true },
      { path: '/calendar', title: '日历看板', icon: 'Calendar' },
      { path: '/my-dashboard', title: '我的看板', icon: 'TrendCharts', consultantOnly: true },
    ],
  },
  {
    label: '项目管理', icon: 'Briefcase',
    items: [
      { path: '/course-sessions', title: '课程场次', icon: 'Calendar', adminOnly: true },
      { path: '/services', title: '专案服务', icon: 'Briefcase', adminOnly: true },
      { path: '/service-orders', title: '服务工单', icon: 'Document' },
    ],
  },
  {
    label: '采购管理', icon: 'Box',
    items: [
      { path: '/purchases', title: '采购管理', icon: 'Box', adminOnly: true },
    ],
  },
  {
    label: '会员运营', icon: 'UserFilled',
    items: [
      { path: '/customers', title: '客户管理', icon: 'OfficeBuilding' },
      { path: '/members', title: '会员/学员', icon: 'User' },
      { path: '/payments', title: '收款明细', icon: 'Money' },
      { path: '/referrals', title: '推荐管理', icon: 'Share', adminOnly: true },
      { path: '/rewards', title: '权益台账', icon: 'Present', adminOnly: true },
    ],
  },
  {
    label: '下店执案', icon: 'MapLocation',
    items: [
      { path: '/bookings', title: '预约管理', icon: 'Location' },
      { path: '/schedules', title: '老师排期', icon: 'Calendar' },
      { path: '/quota', title: '名额管理', icon: 'PieChart', adminOnly: true },
    ],
  },
  {
    label: '组织管理', icon: 'Management',
    items: [
      { path: '/branches', title: '分公司管理', icon: 'OfficeBuilding', adminOnly: true },
      { path: '/consultants', title: '老师管理', icon: 'Avatar', adminOnly: true },
      { path: '/consultant-approval', title: '老师审核', icon: 'CircleCheck', adminOnly: true },
      { path: '/salary', title: '工资管理', icon: 'Money', adminOnly: true },
      { path: '/promotion', title: '晋级管理', icon: 'TrendCharts', adminOnly: true },
      { path: '/talent-analysis', title: '老师人才分析', icon: 'MagicStick', adminOnly: true },
    ],
  },
  {
    label: '内容管理', icon: 'Document',
    items: [
      { path: '/articles', title: '内容管理', icon: 'Notebook' },
      { path: '/banners', title: '广告位管理', icon: 'Picture', adminOnly: true },
    ],
  },
  {
    label: '系统设置', icon: 'Setting',
    items: [
      { path: '/users', title: '账号管理', icon: 'Setting', superOnly: true },
      { path: '/operation-logs', title: '操作日志', icon: 'Document', superOnly: true },
      { path: '/recycle-bin', title: '回收站', icon: 'Delete', superOnly: true },
    ],
  },
];

// 展开所有平铺项用于路由匹配
const allItems = menuGroups.flatMap(g => g.items);

const active = computed(() => {
  const hit = allItems.find(m => route.path.startsWith(m.path));
  return hit?.path || '/dashboard';
});

// 过滤：权限不够的菜单不显示
function filterItems(items: any[]) {
  return items.filter(m => {
    if (m.superOnly && user.role !== 'super_admin') return false;
    if (m.adminOnly && user.role === 'consultant') return false;
    if (m.consultantOnly && user.role !== 'consultant') return false;
    return true;
  });
}

// 过滤后有子项的分组才显示
const visibleGroups = computed(() =>
  menuGroups.map(g => ({ ...g, items: filterItems(g.items) })).filter(g => g.items.length > 0)
);

// 默认展开当前路由所在的分组
const defaultOpeneds = computed(() => {
  const idx = visibleGroups.value.findIndex(g => g.items.some(m => route.path.startsWith(m.path)));
  return idx >= 0 ? [`group-${idx}`] : ['group-0'];
});
const drawerDefaultOpeneds = computed(() => {
  const idx = visibleGroups.value.findIndex(g => g.items.some(m => route.path.startsWith(m.path)));
  return idx >= 0 ? [`mobile-group-${idx}`] : ['mobile-group-0'];
});

const isMobile = computed(() => viewportWidth.value <= 767);
const isTablet = computed(() => viewportWidth.value > 767 && viewportWidth.value <= 1180);
const asideWidth = computed(() => {
  if (isMobile.value) return '0px';
  return isTablet.value ? '190px' : '220px';
});

function updateViewport() {
  viewportWidth.value = window.innerWidth;
  if (!isMobile.value) mobileDrawerVisible.value = false;
}

function handleLogout() {
  user.logout();
  router.push('/login');
}

function handleMenuSelect() {
  if (isMobile.value) mobileDrawerVisible.value = false;
}

// 角标路径映射：red = 待处理（红），green = 进行中（绿）
const badgePathMap: Record<string, { red: string; green?: string }> = {
  '/bookings': { red: 'bookings' },
  '/service-orders': { red: 'service-orders', green: 'service-orders-active' },
  '/schedules': { red: 'schedules', green: 'schedules-active' },
  '/course-sessions': { red: 'course-sessions' },
  '/members': { red: 'members' },
  '/rewards': { red: 'rewards' },
  '/consultant-approval': { red: 'consultant-approval' },
};

function getBadge(path: string): number {
  const keys = badgePathMap[path];
  if (!keys) return 0;
  return (badges.value[keys.red] || 0) + (badges.value[keys.green || ''] || 0);
}

function getBadgeColor(path: string): string {
  const keys = badgePathMap[path];
  if (!keys) return 'red';
  const red = badges.value[keys.red] || 0;
  const green = badges.value[keys.green || ''] || 0;
  if (red > 0) return 'red';
  if (green > 0) return 'green';
  return 'red';
}

function getBadgeRed(path: string): number {
  const keys = badgePathMap[path];
  return keys ? (badges.value[keys.red] || 0) : 0;
}

function getBadgeGreen(path: string): number {
  const keys = badgePathMap[path];
  return keys?.green ? (badges.value[keys.green] || 0) : 0;
}

function getGroupBadge(items: any[]): number {
  return items.reduce((sum: number, m: any) => sum + getBadgeRed(m.path), 0);
}
function getGroupBadgeGreen(items: any[]): number {
  return items.reduce((sum: number, m: any) => sum + getBadgeGreen(m.path), 0);
}

async function loadBadges() {
  try {
    const r: any = await API.menuBadges();
    badges.value = r?.data || r || {};
  } catch { badges.value = {}; }
}

onMounted(() => {
  window.addEventListener('resize', updateViewport);
  loadBadges();
  setInterval(loadBadges, 30000); // 每30秒刷新
});

onUnmounted(() => {
  window.removeEventListener('resize', updateViewport);
});
</script>

<template>
  <el-container class="app-shell">
    <el-aside v-show="!isMobile" :width="asideWidth" class="aside">
      <div class="logo">
        <span class="logo-main">TATA CONSULTING®</span>
        <span class="logo-sub">塔塔咨询 CRM</span>
      </div>
      <el-menu :default-active="active" :default-openeds="defaultOpeneds" router class="menu" :unique-opened="false" @select="handleMenuSelect">
        <template v-for="(g, gi) in visibleGroups" :key="gi">
          <!-- 分组只有1项时直接平铺 -->
          <el-menu-item v-if="g.items.length === 1" :index="g.items[0].path">
            <el-icon><component :is="g.items[0].icon" /></el-icon>
            <template #title>
              <span style="flex:1">{{ g.items[0].title }}</span>
              <span v-if="getBadgeRed(g.items[0].path) > 0" class="menu-num menu-num-red">{{ getBadgeRed(g.items[0].path) > 99 ? '99+' : getBadgeRed(g.items[0].path) }}</span>
              <span v-if="getBadgeGreen(g.items[0].path) > 0" class="menu-num menu-num-green">{{ getBadgeGreen(g.items[0].path) > 99 ? '99+' : getBadgeGreen(g.items[0].path) }}</span>
            </template>
          </el-menu-item>
          <!-- 多项时折叠 -->
          <el-sub-menu v-else :index="`group-${gi}`">
            <template #title>
              <el-icon><component :is="g.icon" /></el-icon>
              <span style="flex:1">{{ g.label }}</span>
              <span v-if="getGroupBadge(g.items) > 0" class="menu-num menu-num-red">{{ getGroupBadge(g.items) > 99 ? '99+' : getGroupBadge(g.items) }}</span>
              <span v-else-if="getGroupBadgeGreen(g.items) > 0" class="menu-num menu-num-green">{{ getGroupBadgeGreen(g.items) > 99 ? '99+' : getGroupBadgeGreen(g.items) }}</span>
            </template>
            <el-menu-item v-for="m in g.items" :key="m.path" :index="m.path">
              <el-icon><component :is="m.icon" /></el-icon>
              <template #title>
                <span style="flex:1">{{ m.title }}</span>
                <span v-if="getBadgeRed(m.path) > 0" class="menu-num menu-num-red">{{ getBadgeRed(m.path) > 99 ? '99+' : getBadgeRed(m.path) }}</span>
                <span v-if="getBadgeGreen(m.path) > 0" class="menu-num menu-num-green">{{ getBadgeGreen(m.path) > 99 ? '99+' : getBadgeGreen(m.path) }}</span>
              </template>
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button v-if="isMobile" text class="mobile-menu-btn" @click="mobileDrawerVisible = true">
            <el-icon><Menu /></el-icon>
          </el-button>
          <div class="title">{{ route.meta?.title }}</div>
        </div>
        <div class="user">
          <NotifBell v-if="user.role !== 'consultant'" />
          <span class="user-name">{{ user.realName || user.username || '管理员' }}</span>
          <el-tag size="small" style="margin-left:6px"
            :type="user.role === 'super_admin' ? 'danger' : user.role === 'consultant' ? 'success' : 'warning'">
            {{ user.role === 'super_admin' ? '超级管理员' : user.role === 'consultant' ? '老师' : '管理员' }}
          </el-tag>
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

  <el-drawer
    v-model="mobileDrawerVisible"
    direction="ltr"
    size="82%"
    :with-header="false"
    custom-class="mobile-drawer"
  >
    <div class="logo drawer-logo">
      <span class="logo-main">TATA CONSULTING®</span>
      <span class="logo-sub">塔塔咨询 CRM</span>
    </div>
    <el-menu :default-active="active" :default-openeds="drawerDefaultOpeneds" router class="menu drawer-menu" :unique-opened="false" @select="handleMenuSelect">
      <template v-for="(g, gi) in visibleGroups" :key="gi">
        <el-menu-item v-if="g.items.length === 1" :index="g.items[0].path">
          <el-icon><component :is="g.items[0].icon" /></el-icon>
          <template #title>
            <span style="flex:1">{{ g.items[0].title }}</span>
            <span v-if="getBadgeRed(g.items[0].path) > 0" class="menu-num menu-num-red">{{ getBadgeRed(g.items[0].path) > 99 ? '99+' : getBadgeRed(g.items[0].path) }}</span>
            <span v-if="getBadgeGreen(g.items[0].path) > 0" class="menu-num menu-num-green">{{ getBadgeGreen(g.items[0].path) > 99 ? '99+' : getBadgeGreen(g.items[0].path) }}</span>
          </template>
        </el-menu-item>
        <el-sub-menu v-else :index="`mobile-group-${gi}`">
          <template #title>
            <el-icon><component :is="g.icon" /></el-icon>
            <span style="flex:1">{{ g.label }}</span>
            <span v-if="getGroupBadge(g.items) > 0" class="menu-num menu-num-red">{{ getGroupBadge(g.items) > 99 ? '99+' : getGroupBadge(g.items) }}</span>
            <span v-else-if="getGroupBadgeGreen(g.items) > 0" class="menu-num menu-num-green">{{ getGroupBadgeGreen(g.items) > 99 ? '99+' : getGroupBadgeGreen(g.items) }}</span>
          </template>
          <el-menu-item v-for="m in g.items" :key="m.path" :index="m.path">
            <el-icon><component :is="m.icon" /></el-icon>
            <template #title>
              <span style="flex:1">{{ m.title }}</span>
              <span v-if="getBadgeRed(m.path) > 0" class="menu-num menu-num-red">{{ getBadgeRed(m.path) > 99 ? '99+' : getBadgeRed(m.path) }}</span>
              <span v-if="getBadgeGreen(m.path) > 0" class="menu-num menu-num-green">{{ getBadgeGreen(m.path) > 99 ? '99+' : getBadgeGreen(m.path) }}</span>
            </template>
          </el-menu-item>
        </el-sub-menu>
      </template>
    </el-menu>
  </el-drawer>
</template>

<style scoped>
.app-shell { height: 100vh; min-width: 0; }
.aside { background: #1f2d3d; color: #fff; overflow-y: auto; }
.logo { padding: 24px 20px; border-bottom: 1px solid #2d3e52; }
.logo-main { display: block; font-size: 18px; font-weight: 700; letter-spacing: 2px; color: #fff; }
.logo-sub { display: block; margin-top: 4px; font-size: 12px; color: #8ea0b5; }
.menu { border: 0; background: transparent; }
.menu :deep(.el-menu-item) { color: #c0ccda; }
.menu :deep(.el-menu-item.is-active) { background: #409EFF !important; color: #fff; }
.menu :deep(.el-menu-item:hover) { background: #2d3e52; }
.menu :deep(.el-sub-menu__title) { color: #c0ccda; }
.menu :deep(.el-sub-menu__title:hover) { background: #2d3e52; }
.menu :deep(.el-sub-menu .el-menu) { background: #1a2738; }
.menu :deep(.el-sub-menu .el-menu-item) { padding-left: 48px !important; font-size: 13px; }
.header { display: flex; justify-content: space-between; align-items: center; background: #fff; border-bottom: 1px solid #ebeef5; }
.header-left { display: flex; align-items: center; min-width: 0; }
.mobile-menu-btn { margin-right: 8px; font-size: 18px; }
.title { font-size: 16px; font-weight: 600; }
.user { color: #606266; font-size: 14px; cursor: pointer; white-space: nowrap; }
.user-name { margin-left: 12px; }
.main { padding: 20px; background: #f5f7fa; min-width: 0; overflow-x: hidden; }
.menu-num { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; border-radius: 10px; color: #fff; font-size: 11px; font-weight: 500; line-height: 1; margin-left: 6px; }
.menu-num-red { background: #f56c6c; }
.menu-num-green { background: #67c23a; }

.drawer-logo { background: #1f2d3d; }
.drawer-menu { min-height: calc(100vh - 82px); }

@media (max-width: 1180px) {
  .logo { padding: 20px 14px; }
  .logo-main { font-size: 15px; letter-spacing: 1px; }
  .menu :deep(.el-sub-menu .el-menu-item) { padding-left: 38px !important; }
  .main { padding: 16px; }
}

@media (max-width: 767px) {
  .app-shell { height: 100dvh; }
  .header { height: 52px; padding: 0 10px; }
  .title { font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .user-name { display: none; }
  .main { padding: 10px; }
}
</style>
