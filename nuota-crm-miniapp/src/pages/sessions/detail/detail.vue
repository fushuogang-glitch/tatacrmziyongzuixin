<template>
  <view class="page">
    <scroll-view scroll-y class="scroll" @scroll="onScroll">
      <!-- 封面 -->
      <view class="cover" :style="{ background: 'linear-gradient(160deg, #0a0a0a 0%, #2a2520 60%, #1a1060 100%)' }">
        <view class="cover-overlay"></view>
        <view class="cover-content">
          <text class="cover-tag">{{ session.session_no }}</text>
          <text class="cover-title">塔塔战略课</text>
          <text class="cover-sub">新美业 · 系统培训 · 现场签到</text>
          <view class="cover-meta">
            <text>📅 {{ session.start_date }} ~ {{ session.end_date }}</text>
            <text v-if="session.location">📍 {{ session.location }} · {{ session.city }}</text>
          </view>
        </view>
        <view class="cover-badge" :class="badgeClass(session.status)">{{ statusLabel(session.status) }}</view>
      </view>

      <!-- 关键信息卡 -->
      <view class="info-strip">
        <view class="is-item">
          <text class="is-val">{{ session.enrolled || 0 }}/{{ session.capacity || 30 }}</text>
          <text class="is-label">已报名</text>
        </view>
        <view class="is-divider"></view>
        <view class="is-item">
          <text class="is-val">3</text>
          <text class="is-label">课程天数</text>
        </view>
        <view class="is-divider"></view>
        <view class="is-item">
          <text class="is-val price-val">{{ session.trial_price ? '¥' + (session.trial_price/10000).toFixed(1) + '万' : '面议' }}</text>
          <text class="is-label">体验价</text>
        </view>
      </view>

      <!-- 课程介绍 -->
      <view class="section-block">
        <view class="section-head">
          <view class="sec-line"></view>
          <text class="sec-title">课 程 介 绍</text>
        </view>
        <text class="intro-text">
          塔塔战略课是塔塔咨询面向新美业门店主、管理者的年度核心课程。以「黄金三角」战略框架为核心，结合三多理论、CABD顾客分层、信任度递进体系，帮助学员从底层逻辑重构门店经营认知。

          课程采用案例研讨+现场演练模式，每期限额30人，确保深度互动质量。
        </text>
      </view>

      <!-- 三天大纲 -->
      <view class="section-block">
        <view class="section-head">
          <view class="sec-line"></view>
          <text class="sec-title">三 天 大 纲</text>
        </view>
        <view v-for="(day, i) in syllabus" :key="i" class="day-card" :class="{ active: expandedDay === i }" @tap="expandedDay = expandedDay === i ? -1 : i">
          <view class="dc-header">
            <view class="dc-day">DAY {{ i+1 }}</view>
            <text class="dc-title">{{ day.title }}</text>
            <text class="dc-arrow">{{ expandedDay === i ? '∧' : '∨' }}</text>
          </view>
          <view class="dc-items" v-if="expandedDay === i">
            <view v-for="(item, j) in day.items" :key="j" class="dc-item">
              <view class="dci-dot"></view>
              <text class="dci-text">{{ item }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 适合人群 -->
      <view class="section-block">
        <view class="section-head">
          <view class="sec-line"></view>
          <text class="sec-title">适 合 人 群</text>
        </view>
        <view class="tags-wrap">
          <view v-for="t in audience" :key="t" class="tag">{{ t }}</view>
        </view>
      </view>

      <!-- 价格详情 -->
      <view class="section-block price-block">
        <view class="section-head">
          <view class="sec-line"></view>
          <text class="sec-title">费 用 说 明</text>
        </view>
        <view class="price-table">
          <view class="pt-row">
            <text class="pt-label">体验价（限购1次）</text>
            <text class="pt-val gold">¥ {{ session.trial_price ? session.trial_price.toLocaleString() : '8,800' }}</text>
          </view>
          <view class="pt-row">
            <text class="pt-label">年费会员（含多次入场）</text>
            <text class="pt-val">¥ {{ session.annual_price ? (session.annual_price/10000).toFixed(0) + '万起' : '38万起' }}</text>
          </view>
          <view class="pt-row last">
            <text class="pt-label">包含内容</text>
            <text class="pt-val small">课程手册 · 午餐茶歇 · 课后群</text>
          </view>
        </view>
      </view>

      <!-- 报名须知 -->
      <view class="section-block">
        <view class="section-head">
          <view class="sec-line"></view>
          <text class="sec-title">报 名 须 知</text>
        </view>
        <view class="notice-list">
          <view v-for="n in notices" :key="n" class="notice-item">
            <text class="n-dot">◆</text>
            <text class="n-text">{{ n }}</text>
          </view>
        </view>
      </view>

      <view style="height: 160rpx;"></view>
    </scroll-view>

    <!-- 底部操作栏 -->
    <view class="bottom-bar" :class="{ 'bar-shadow': scrolled }">
      <view class="bar-price">
        <text class="bp-label">体验价</text>
        <text class="bp-num">¥{{ session.trial_price ? session.trial_price.toLocaleString() : '8,800' }}</text>
      </view>
      <button v-if="session.status === 'open'" class="bar-btn" :disabled="enrolling" @tap="enroll">
        {{ enrolled ? '✓ 已报名' : enrolling ? '处理中...' : '立即报名' }}
      </button>
      <view v-else class="bar-btn bar-btn-disabled">{{ statusLabel(session.status) }}</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../../../api';

const session = ref<any>({ status: 'open', enrolled: 0, capacity: 30 });
const loading = ref(true);
const enrolling = ref(false);
const enrolled = ref(false);
const expandedDay = ref(0);
const scrolled = ref(false);
let sessionId = 0;

const syllabus = [
  { title: '战略认知 · 门店诊断', items: ['新美业赛道判断与机会', '门店经营死循环与正循环', '黄金三角：品项×流量×团队', '现场门店诊断演练'] },
  { title: '品项搭建 · 营销设计', items: ['三多核心：多品项×多顾客×多频次', 'CABD顾客分层管理', '大促设计：峰终体验管理', '定价哲学与价值塑造'] },
  { title: '团队打造 · 落地规划', items: ['顾问岗能力画像与招聘', '信任度递进15步流程', '新客成交实操演练', '90天落地计划制定'] },
];
const audience = ['门店主', '合伙人', '店长', '区域负责人', '计划扩张的创业者'];
const notices = [
  '体验价每人限购一次，购买后不退',
  '课程手册仅限已报名学员领取',
  '迟到超过1小时视为缺席，不补课不退费',
  '如需开发票请在报名时备注',
];

function statusLabel(s: string) {
  return { open: '报名中', full: '名额已满', closed: '报名截止', finished: '已结束' }[s] || s;
}
function badgeClass(s: string) {
  return { open: 'badge-open', full: 'badge-full' }[s] || 'badge-done';
}
function onScroll(e: any) {
  scrolled.value = e.detail.scrollTop > 20;
}

async function enroll() {
  const member = uni.getStorageSync('member');
  if (!member?.id) {
    uni.showToast({ title: '请先登录', icon: 'none' });
    setTimeout(() => uni.navigateTo({ url: '/pages/login/login' }), 800);
    return;
  }
  // 人脸认证检查暂时关闭（待接入国家网络身份认证后恢复）
  // if (!member.face_bound) {
  //   uni.showModal({ title: '需要人脸认证', content: '报名后需扫脸签到，请先完成人脸绑定', confirmText: '去绑定', success: (r) => { if (r.confirm) uni.navigateTo({ url: '/pages/face/bind/bind' }); } });
  //   return;
  // }
  enrolling.value = true;
  try {
    await api.enroll(sessionId);
    enrolled.value = true;
    uni.showToast({ title: '报名成功！', icon: 'success' });
    session.value.enrolled = (session.value.enrolled || 0) + 1;
  } catch (e: any) {
    uni.showToast({ title: e?.msg || '报名失败', icon: 'none' });
  } finally {
    enrolling.value = false;
  }
}

onMounted(async () => {
  // @ts-ignore
  const pages = getCurrentPages();
  // @ts-ignore
  const query = pages[pages.length - 1]?.options || {};
  sessionId = Number(query.id);
  try {
    const list: any = await api.availableSessions().catch(() => []);
    const found = (list || []).find((s: any) => s.id === sessionId);
    if (found) session.value = found;
    else session.value = { id: sessionId, session_no: 'S2026-05', start_date: '2026-05-28', end_date: '2026-05-30', location: '武汉', city: '湖北', status: 'open', enrolled: 18, capacity: 30, trial_price: 8800, annual_price: 380000 };
  } finally { loading.value = false; }
});
</script>

<style lang="scss">
.page { background: #fafaf8; min-height: 100vh; display: flex; flex-direction: column; }
.scroll { flex: 1; }

.cover { position: relative; height: 480rpx; display: flex; align-items: flex-end; overflow: hidden; }
.cover-overlay { position: absolute; inset: 0; background: linear-gradient(to bottom, transparent 30%, rgba(0,0,0,0.7)); }
.cover-content { position: relative; z-index: 1; padding: 48rpx; flex: 1; }
.cover-tag { display: block; font-size: 18rpx; color: #c9a96e; letter-spacing: 4rpx; margin-bottom: 12rpx; }
.cover-title { display: block; font-size: 48rpx; font-weight: 500; color: #fff; letter-spacing: 6rpx; line-height: 1.2; }
.cover-sub { display: block; font-size: 22rpx; color: rgba(255,255,255,0.7); letter-spacing: 3rpx; margin-top: 8rpx; }
.cover-meta { margin-top: 20rpx; display: flex; flex-direction: column; gap: 6rpx; font-size: 20rpx; color: rgba(255,255,255,0.8); }
.cover-badge { position: absolute; top: 80rpx; right: 32rpx; z-index: 2; padding: 8rpx 20rpx; border-radius: 20rpx; font-size: 20rpx; letter-spacing: 2rpx; }
.badge-open { background: rgba(201,169,110,0.9); color: #0a0a0a; }
.badge-full { background: rgba(232,76,76,0.9); color: #fff; }
.badge-done { background: rgba(0,0,0,0.5); color: #999; }

.info-strip { background: #fff; display: flex; align-items: center; padding: 28rpx 0; }
.is-item { flex: 1; text-align: center; }
.is-val { display: block; font-size: 32rpx; font-weight: 500; color: #0a0a0a; line-height: 1.2; }
.is-val.price-val { color: #a88a4d; }
.is-label { display: block; font-size: 18rpx; color: #9a9a9a; margin-top: 4rpx; letter-spacing: 2rpx; }
.is-divider { width: 1rpx; height: 60rpx; background: #ebe8e2; }

.section-block { background: #fff; margin-top: 16rpx; padding: 0 0 32rpx; }
.section-head { display: flex; align-items: center; gap: 16rpx; padding: 32rpx 48rpx 20rpx; }
.sec-line { width: 32rpx; height: 1rpx; background: #c9a96e; flex-shrink: 0; }
.sec-title { font-size: 24rpx; letter-spacing: 10rpx; color: #0a0a0a; font-weight: 500; }

.intro-text { display: block; padding: 0 48rpx; font-size: 26rpx; color: #333; line-height: 1.8; letter-spacing: 1rpx; white-space: pre-line; }

.day-card { margin: 0 48rpx 16rpx; border: 1rpx solid #ebe8e2; border-radius: 16rpx; overflow: hidden; }
.day-card.active { border-color: #c9a96e; }
.dc-header { display: flex; align-items: center; gap: 16rpx; padding: 24rpx 28rpx; background: #fff; }
.dc-day { font-size: 18rpx; letter-spacing: 2rpx; color: #c9a96e; background: rgba(201,169,110,0.1); padding: 6rpx 14rpx; border-radius: 8rpx; flex-shrink: 0; }
.dc-title { flex: 1; font-size: 26rpx; color: #0a0a0a; font-weight: 500; letter-spacing: 2rpx; }
.dc-arrow { font-size: 24rpx; color: #c9a96e; }
.dc-items { padding: 0 28rpx 20rpx; border-top: 1rpx solid #f3f3f3; }
.dc-item { display: flex; gap: 16rpx; padding: 16rpx 0; border-bottom: 1rpx solid #f9f9f7; }
.dci-dot { width: 8rpx; height: 8rpx; border-radius: 50%; background: #c9a96e; margin-top: 12rpx; flex-shrink: 0; }
.dci-text { font-size: 24rpx; color: #333; letter-spacing: 1rpx; line-height: 1.6; }

.tags-wrap { display: flex; flex-wrap: wrap; gap: 16rpx; padding: 0 48rpx; }
.tag { padding: 12rpx 24rpx; border: 1rpx solid #ebe8e2; border-radius: 40rpx; font-size: 22rpx; color: #555; letter-spacing: 2rpx; }

.price-table { margin: 0 48rpx; border: 1rpx solid #ebe8e2; border-radius: 16rpx; overflow: hidden; }
.pt-row { display: flex; justify-content: space-between; align-items: center; padding: 24rpx 28rpx; border-bottom: 1rpx solid #f3f3f3; }
.pt-row.last { border-bottom: none; }
.pt-label { font-size: 24rpx; color: #555; letter-spacing: 1rpx; }
.pt-val { font-size: 26rpx; color: #0a0a0a; font-weight: 500; }
.pt-val.gold { color: #a88a4d; font-size: 30rpx; }
.pt-val.small { font-size: 22rpx; color: #9a9a9a; }

.notice-list { padding: 0 48rpx; display: flex; flex-direction: column; gap: 16rpx; }
.notice-item { display: flex; gap: 16rpx; align-items: flex-start; }
.n-dot { color: #c9a96e; font-size: 18rpx; margin-top: 6rpx; }
.n-text { flex: 1; font-size: 24rpx; color: #555; line-height: 1.7; letter-spacing: 1rpx; }

.bottom-bar {
  position: fixed; left: 0; right: 0; bottom: 0;
  padding: 16rpx 48rpx 60rpx; background: #fff;
  display: flex; align-items: center; gap: 24rpx;
  border-top: 1rpx solid #ebe8e2;
  transition: box-shadow 0.2s;
}
.bottom-bar.bar-shadow { box-shadow: 0 -8rpx 32rpx rgba(0,0,0,0.08); }
.bar-price { flex: 1; }
.bp-label { display: block; font-size: 18rpx; color: #9a9a9a; letter-spacing: 2rpx; }
.bp-num { display: block; font-size: 40rpx; color: #a88a4d; font-weight: 500; line-height: 1.2; }
.bar-btn {
  flex: 1.2; padding: 24rpx; text-align: center;
  background: #0a0a0a; color: #c9a96e;
  border: none; border-radius: 48rpx;
  font-size: 28rpx; letter-spacing: 4rpx;
}
.bar-btn-disabled { background: #f3f3f3; color: #9a9a9a; }
</style>
