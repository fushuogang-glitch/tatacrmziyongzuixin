<template>
  <view class="page">
    <view class="brand-head">
      <text class="brand-mark">TATA CONSULTING<text class="reg">®</text></text>
      <text class="brand-tag">课 程 · 年 度 系 统 培 训</text>
    </view>

    <scroll-view scroll-y class="scroll">
      <!-- 课程列表 -->
      <view class="hero">
        <text class="hero-en">COURSES</text>
        <text class="hero-cn">年 度 课 程</text>
        <view class="hero-line"></view>
        <text class="hero-desc">新美业系统培训 · 年费制服务</text>
      </view>

      <view v-if="loading" class="loading-wrap">
        <view class="spinner"></view>
      </view>

      <view v-else>
        <view v-if="sessions.length === 0" class="empty">
          <text class="empty-icon">◇</text>
          <text class="empty-text">暂无开放场次</text>
          <text class="empty-sub">敬请期待下期开课通知</text>
        </view>

        <view v-for="s in sessions" :key="s.id" class="course-card" @tap="goDetail(s.id)">
          <view class="cc-badge" :class="badgeClass(s.status)">{{ statusLabel(s.status) }}</view>
          <view class="cc-main">
            <view class="cc-top">
              <text class="cc-no">{{ s.session_no }}</text>
              <text class="cc-quota">{{ s.enrolled || 0 }}/{{ s.capacity || 30 }} 人</text>
            </view>
            <text class="cc-title">塔塔战略课 · {{ s.session_no }}</text>
            <view class="cc-meta">
              <text class="cc-date">📅 {{ s.start_date }} ~ {{ s.end_date }}</text>
              <text class="cc-loc" v-if="s.location">📍 {{ s.location }}{{ s.city ? ' · ' + s.city : '' }}</text>
            </view>
            <view class="cc-footer">
              <view class="cc-price-group">
                <text class="cc-price-label">体验价</text>
                <text class="cc-price">¥ {{ s.trial_price ? s.trial_price.toLocaleString() : '面议' }}</text>
                <text class="cc-price-full" v-if="s.annual_price">年费 ¥{{ (s.annual_price/10000).toFixed(0) }}万</text>
              </view>
              <view class="cc-btn" :class="s.status === 'open' ? 'btn-active' : 'btn-closed'">
                {{ s.status === 'open' ? '立即报名 →' : '查看详情 →' }}
              </view>
            </view>
          </view>
          <!-- 进度条 -->
          <view class="cc-progress">
            <view class="cc-prog-fill" :style="{ width: Math.min(100, ((s.enrolled||0)/(s.capacity||30))*100) + '%',
              background: (s.enrolled||0)/(s.capacity||30) > 0.8 ? '#e84c4c' : '#c9a96e' }"></view>
          </view>
        </view>

        <!-- 课程亮点 -->
        <view class="highlights">
          <view class="section-head">
            <view class="sec-line"></view>
            <text class="sec-title">课 程 亮 点</text>
            <text class="sec-en">Highlights</text>
          </view>
          <view class="hl-grid">
            <view v-for="h in highlights" :key="h.icon" class="hl-card">
              <text class="hl-icon">{{ h.icon }}</text>
              <text class="hl-title">{{ h.title }}</text>
              <text class="hl-desc">{{ h.desc }}</text>
            </view>
          </view>
        </view>

        <!-- 课程大纲 -->
        <view class="outline">
          <view class="section-head">
            <view class="sec-line"></view>
            <text class="sec-title">三 天 大 纲</text>
            <text class="sec-en">Syllabus</text>
          </view>
          <view v-for="(day, i) in syllabus" :key="i" class="day-block">
            <view class="day-header">
              <text class="day-label">DAY {{ i+1 }}</text>
              <text class="day-title">{{ day.title }}</text>
            </view>
            <view v-for="(item, j) in day.items" :key="j" class="day-item">
              <view class="di-dot"></view>
              <text class="di-text">{{ item }}</text>
            </view>
          </view>
        </view>

        <!-- 讲师团队 -->
        <view class="teachers-section">
          <view class="section-head">
            <view class="sec-line"></view>
            <text class="sec-title">讲 师 团 队</text>
            <text class="sec-en">Faculty</text>
          </view>
          <view class="teacher-row">
            <view v-for="t in teachers" :key="t.name" class="teacher-card">
              <view class="tc-avatar" :style="{ background: t.color }">{{ t.name.slice(0,1) }}</view>
              <text class="tc-name">{{ t.name }}</text>
              <text class="tc-title">{{ t.title }}</text>
            </view>
          </view>
        </view>
      </view>

      <view class="page-footer">
        <text class="pf-en">— TATA CONSULTING® —</text>
        <text class="pf-cn">上海嘉塔诺塔管理咨询有限公司</text>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../../../api';

const sessions = ref<any[]>([]);
const loading = ref(true);

const highlights = [
  { icon: '🎯', title: '系统方法论', desc: '塔塔核心体系\n黄金三角·三多' },
  { icon: '👥', title: '现场互动', desc: '案例研讨\n实操演练' },
  { icon: '📋', title: '手册随行', desc: '专属课程手册\n现场领取Day1-3' },
  { icon: '🔗', title: '持续支持', desc: '课后老师群\n下店辅导资格' },
];

const syllabus = [
  {
    title: '战略认知 · 门店诊断',
    items: ['新美业赛道判断与机会', '门店经营死循环与正循环', '黄金三角：品项×流量×团队', '现场门店诊断演练'],
  },
  {
    title: '品项搭建 · 营销设计',
    items: ['三多核心：多品项×多顾客×多频次', 'CABD 顾客分层管理', '大促设计：峰终体验管理', '定价哲学与价值塑造'],
  },
  {
    title: '团队打造 · 落地规划',
    items: ['顾问岗能力画像与招聘', '信任度递进15步流程', '新客成交实操演练', '90天落地计划制定'],
  },
];

const teachers = [
  { name: '付熙锐', title: '塔塔咨询创始人', color: '#c9a96e' },
  { name: '刘静', title: '资深战略顾问', color: '#7b6fdf' },
  { name: '王芳', title: '品项体系专家', color: '#4a90d9' },
];

function statusLabel(s: string) {
  return { open: '报名中', full: '名额已满', closed: '报名截止', finished: '已结束' }[s] || s;
}
function badgeClass(s: string) {
  return { open: 'badge-open', full: 'badge-full', closed: 'badge-closed', finished: 'badge-done' }[s] || '';
}
function goDetail(id: number) {
  uni.navigateTo({ url: `/pages/sessions/detail/detail?id=${id}` });
}

onMounted(async () => {
  try {
    const list: any = await api.availableSessions().catch(() => []);
    sessions.value = list || [];
    // 演示数据
    if (!sessions.value.length) {
      sessions.value = [
        { id: 1, session_no: 'S2026-05', start_date: '2026-05-28', end_date: '2026-05-30', location: '武汉', city: '湖北', status: 'open', enrolled: 18, capacity: 30, trial_price: 8800, annual_price: 380000 },
        { id: 2, session_no: 'S2026-06', start_date: '2026-06-18', end_date: '2026-06-20', location: '上海', city: '上海', status: 'open', enrolled: 6, capacity: 30, trial_price: 8800, annual_price: 380000 },
        { id: 3, session_no: 'S2026-04', start_date: '2026-04-10', end_date: '2026-04-12', location: '茅山', city: '江苏', status: 'finished', enrolled: 28, capacity: 30, trial_price: 8800, annual_price: 380000 },
      ];
    }
  } finally { loading.value = false; }
});
</script>

<style lang="scss">
.page { background: #fafaf8; min-height: 100vh; display: flex; flex-direction: column; }
.brand-head { padding: 60rpx 48rpx 20rpx; text-align: center; background: #fff; border-bottom: 1rpx solid #ebe8e2; }
.brand-mark { font-size: 32rpx; letter-spacing: 8rpx; color: #0a0a0a; font-weight: 500; }
.brand-mark .reg { font-size: 16rpx; color: #c9a96e; vertical-align: super; }
.brand-tag { display: block; font-size: 20rpx; color: #9a9a9a; margin-top: 8rpx; letter-spacing: 6rpx; }
.scroll { flex: 1; }

.hero { padding: 40rpx 48rpx 32rpx; background: #fff; text-align: center; border-bottom: 1rpx solid #ebe8e2; }
.hero-en { display: block; font-size: 20rpx; color: #c9a96e; letter-spacing: 6rpx; font-style: italic; }
.hero-cn { display: block; font-size: 36rpx; letter-spacing: 14rpx; color: #0a0a0a; font-weight: 500; margin-top: 8rpx; }
.hero-line { width: 40rpx; height: 1rpx; background: #c9a96e; margin: 20rpx auto; }
.hero-desc { display: block; font-size: 20rpx; color: #9a9a9a; letter-spacing: 3rpx; }

.loading-wrap { display: flex; justify-content: center; padding: 80rpx; }
.spinner { width: 48rpx; height: 48rpx; border: 3rpx solid #ebe8e2; border-top-color: #c9a96e; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.empty { text-align: center; padding: 100rpx 48rpx; }
.empty-icon { display: block; font-size: 60rpx; color: #c9a96e; margin-bottom: 24rpx; }
.empty-text { display: block; font-size: 28rpx; color: #0a0a0a; letter-spacing: 4rpx; }
.empty-sub { display: block; font-size: 22rpx; color: #9a9a9a; margin-top: 12rpx; letter-spacing: 2rpx; }

.course-card { margin: 24rpx 32rpx 0; background: #fff; border-radius: 24rpx; overflow: hidden; box-shadow: 0 4rpx 24rpx rgba(0,0,0,0.06); }
.cc-badge { padding: 12rpx 24rpx; font-size: 20rpx; letter-spacing: 3rpx; display: inline-block; }
.badge-open { background: rgba(201,169,110,0.12); color: #a88a4d; }
.badge-full { background: rgba(232,76,76,0.1); color: #e84c4c; }
.badge-closed { background: #f3f3f3; color: #9a9a9a; }
.badge-done { background: #f3f3f3; color: #bbb; }
.cc-main { padding: 0 32rpx 28rpx; }
.cc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12rpx; }
.cc-no { font-size: 22rpx; color: #c9a96e; letter-spacing: 2rpx; }
.cc-quota { font-size: 20rpx; color: #9a9a9a; }
.cc-title { display: block; font-size: 30rpx; font-weight: 500; color: #0a0a0a; letter-spacing: 3rpx; margin-bottom: 16rpx; }
.cc-meta { display: flex; flex-direction: column; gap: 8rpx; margin-bottom: 24rpx; }
.cc-date, .cc-loc { font-size: 22rpx; color: #555; letter-spacing: 1rpx; }
.cc-footer { display: flex; justify-content: space-between; align-items: flex-end; }
.cc-price-group {}
.cc-price-label { font-size: 18rpx; color: #9a9a9a; letter-spacing: 2rpx; }
.cc-price { display: block; font-size: 36rpx; color: #a88a4d; font-weight: 500; line-height: 1.2; }
.cc-price-full { display: block; font-size: 18rpx; color: #bbb; text-decoration: line-through; }
.cc-btn { padding: 16rpx 28rpx; border-radius: 40rpx; font-size: 22rpx; letter-spacing: 2rpx; }
.btn-active { background: #0a0a0a; color: #c9a96e; }
.btn-closed { background: #f3f3f3; color: #9a9a9a; }
.cc-progress { height: 4rpx; background: #ebe8e2; }
.cc-prog-fill { height: 100%; border-radius: 2rpx; transition: width 0.5s; }

.section-head { display: flex; align-items: center; gap: 16rpx; padding: 36rpx 48rpx 20rpx; }
.sec-line { width: 36rpx; height: 1rpx; background: #c9a96e; }
.sec-title { font-size: 24rpx; letter-spacing: 10rpx; color: #0a0a0a; font-weight: 500; flex: 1; }
.sec-en { font-size: 20rpx; color: #9a9a9a; font-style: italic; }

.highlights { background: #fff; margin-top: 24rpx; }
.hl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rpx; background: #ebe8e2; margin: 0 48rpx; border-radius: 16rpx; overflow: hidden; }
.hl-card { background: #fff; padding: 28rpx; text-align: center; }
.hl-icon { display: block; font-size: 48rpx; margin-bottom: 12rpx; }
.hl-title { display: block; font-size: 24rpx; font-weight: 500; color: #0a0a0a; letter-spacing: 3rpx; margin-bottom: 8rpx; }
.hl-desc { display: block; font-size: 20rpx; color: #9a9a9a; line-height: 1.6; letter-spacing: 1rpx; white-space: pre-line; }

.outline { background: #fff; margin-top: 24rpx; padding-bottom: 32rpx; }
.day-block { margin: 0 48rpx 24rpx; }
.day-header { display: flex; align-items: center; gap: 20rpx; margin-bottom: 16rpx; }
.day-label { font-size: 18rpx; letter-spacing: 2rpx; color: #c9a96e; background: rgba(201,169,110,0.1); padding: 6rpx 16rpx; border-radius: 8rpx; }
.day-title { font-size: 26rpx; font-weight: 500; color: #0a0a0a; letter-spacing: 3rpx; }
.day-item { display: flex; align-items: flex-start; gap: 16rpx; padding: 10rpx 0; border-bottom: 1rpx solid #f3f3f3; }
.di-dot { width: 8rpx; height: 8rpx; border-radius: 50%; background: #c9a96e; margin-top: 12rpx; flex-shrink: 0; }
.di-text { font-size: 24rpx; color: #333; letter-spacing: 1rpx; line-height: 1.6; }

.teachers-section { background: #fff; margin-top: 24rpx; padding-bottom: 32rpx; }
.teacher-row { display: flex; gap: 24rpx; padding: 0 48rpx; overflow-x: auto; }
.teacher-card { display: flex; flex-direction: column; align-items: center; gap: 12rpx; min-width: 140rpx; }
.tc-avatar { width: 96rpx; height: 96rpx; border-radius: 50%; color: #fff; font-size: 36rpx; font-weight: 700; display: flex; align-items: center; justify-content: center; }
.tc-name { font-size: 26rpx; font-weight: 500; color: #0a0a0a; letter-spacing: 3rpx; }
.tc-title { font-size: 20rpx; color: #9a9a9a; letter-spacing: 1rpx; text-align: center; }

.page-footer { padding: 60rpx 48rpx 80rpx; text-align: center; }
.pf-en { display: block; font-size: 18rpx; color: #c9a96e; letter-spacing: 6rpx; font-style: italic; margin-bottom: 8rpx; }
.pf-cn { display: block; font-size: 18rpx; color: #9a9a9a; letter-spacing: 3rpx; }
</style>
