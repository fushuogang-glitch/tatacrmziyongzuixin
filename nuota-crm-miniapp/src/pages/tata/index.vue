<template>
  <view class="page">
    <!-- 顶部品牌头 -->
    <view class="brand-head">
      <view class="brand-mark">TATA CONSULTING<text class="reg">®</text></view>
      <view class="brand-tag">塔 塔 咨 询 · 新 美 业 战 略 伙 伴</view>
    </view>

    <!-- 灵光一点：首页浮现金句卡（淡入·TATA水印·可分享） -->
    <view v-if="lingguang.quote && showLingguang" class="lingguang-mask" @tap="showLingguang=false">
      <view class="lingguang-card" :style="{ background: lgBg }" @tap.stop="">
        <text class="lg-eyebrow">灵 光 一 点</text>
        <text class="lg-quote">{{ lingguang.quote }}</text>
        <view class="lg-divider"></view>
        <view class="lg-foot">
          <text class="lg-color" v-if="lingguang.lucky_color">今日宜 · {{ lingguang.lucky_color }}</text>
          <text class="lg-mark">{{ lingguang.watermark || 'TATA' }}</text>
        </view>
        <view class="lg-actions">
          <button class="lg-btn" open-type="share">分享</button>
          <text class="lg-close" @tap="showLingguang=false">轻触收起</text>
        </view>
      </view>
    </view>

    <scroll-view scroll-y class="scroll">
      <!-- 每日一念·智能入口：未填生辰→引导卡；已填→当日展示 -->
      <!-- 态一：未填生辰·引导开启（带说明） -->
      <view class="dy-intro" v-if="daily.profile && !daily.profile.birth_date" @tap="go('/pages/daily-thought/index')">
        <view class="dy-intro-deco"></view>
        <text class="dy-intro-eyebrow">每 日 一 念</text>
        <text class="dy-intro-title">✨ 开启你的专属每日一念</text>
        <text class="dy-intro-desc">留下生辰，每天为你测算专属运势、今日幸运色与一念箴言，助你顺势而为。</text>
        <view class="dy-intro-btn">立 即 开 启 →</view>
      </view>

      <!-- 态二：已填生辰·当日每日一念 -->
      <view class="daily-card" @tap="go('/pages/daily-thought/index')" v-else-if="daily.word">
        <view class="daily-main">
          <text class="daily-label">每日一念 · {{ daily.date }}</text>
          <text class="daily-word">{{ daily.word }}</text>
          <text class="daily-meaning">{{ (lingguang && lingguang.quote) || daily.meaning }}</text>
          <view class="daily-tags" v-if="lingguang && lingguang.lucky_color">
            <text class="daily-tag">今日宜 · {{ lingguang.lucky_color }}</text>
          </view>
        </view>
        <text class="daily-arr">→</text>
      </view>

      <!-- 预约入口 -->
      <view class="section">
        <view class="sec-head">
          <view class="sec-line"></view>
          <text class="sec-title">预  约</text>
          <text class="sec-en">Booking</text>
        </view>
      </view>
      <view class="booking-row">
        <view class="booking-card b1" @tap="go('/pages/service/index')">
          <view class="booking-deco"></view>
          <text class="booking-tag">SERVICE</text>
          <text class="booking-name">专 案 排 期 预 约</text>
          <view class="booking-sub">
            <text>{{ consultantCount }}位老师在线</text>
            <text class="arr">→</text>
          </view>
        </view>
        <view class="booking-card b2" @tap="go('/pages/sessions/list/list')">
          <view class="booking-deco"></view>
          <text class="booking-tag">COURSE</text>
          <text class="booking-name">课 程 报 名</text>
          <view class="booking-sub">
            <text>本月{{ sessionCount }}场开课</text>
            <text class="arr">→</text>
          </view>
        </view>
      </view>

      <!-- 了解塔塔 -->
      <view class="section">
        <view class="sec-head">
          <view class="sec-line"></view>
          <text class="sec-title">了 解 塔 塔</text>
          <text class="sec-en">About</text>
        </view>
      </view>
      <view class="intro-row">
        <view class="intro-card intro-i1" @tap="go('/pages/about/brand')">
          <view class="intro-img i1"></view>
          <view class="intro-body">
            <text class="intro-name">塔 塔 旗 下 品 牌</text>
            <text class="intro-desc">塔塔咨询 · 九木营销学院 · 九凤产品学院 · 诺塔智控</text>
          </view>
          <text class="intro-arr">→</text>
        </view>
        <view class="intro-card intro-i3" @tap="go('/pages/sessions/list/list')">
          <view class="intro-img i3"></view>
          <view class="intro-body">
            <text class="intro-name">塔 塔 课 程 介 绍</text>
            <text class="intro-desc">系统课程 · 录播体系 · 随时学习</text>
          </view>
          <text class="intro-arr">→</text>
        </view>
        <view class="intro-card intro-i2" @tap="go('/pages/service/list')">
          <view class="intro-img i2"></view>
          <view class="intro-body">
            <text class="intro-name">塔 塔 产 品 介 绍</text>
            <text class="intro-desc">门店诊断 · 定制方案 · 执案跟进</text>
          </view>
          <text class="intro-arr">→</text>
        </view>
      </view>

      <!-- 事件动态 -->
      <view class="section">
        <view class="sec-head">
          <view class="sec-line"></view>
          <text class="sec-title">事 件 动 态</text>
          <text class="sec-en">Insights</text>
        </view>
      </view>
      <view class="event-tabs">
        <text :class="['event-tab', activeTab === 'promo' ? 'active' : '']" @tap="activeTab = 'promo'">会员动态</text>
        <text :class="['event-tab', activeTab === 'news' ? 'active' : '']" @tap="activeTab = 'news'">行业动态</text>
        <text :class="['event-tab', activeTab === 'culture' ? 'active' : '']" @tap="activeTab = 'culture'">企业文化</text>
        <text :class="['event-tab', activeTab === 'video' ? 'active' : '']" @tap="activeTab = 'video'">课程直播</text>
      </view>

      <!-- 文章列表 -->
      <view v-for="(ev, i) in filteredList" :key="i" class="event-item" @tap="onArticleTap(ev)">
        <view class="event-meta">
          <text>{{ ev.date }}</text>
          <view class="event-dot"></view>
          <text>{{ ev.tag }}</text>
        </view>
        <text class="event-title">{{ ev.title }}</text>
        <text class="event-sub">{{ ev.sub }}</text>
        <text v-if="activeTab === 'video'" class="event-arr">▶</text>
      </view>

      <!-- 空状态 -->
      <view v-if="filteredList.length === 0" class="empty-tip">
        暂无内容，CRM后台发布后自动显示
      </view>

      <view class="footer">
        <text class="footer-en">— TATA CONSULTING® —</text>
        <text class="footer-cn">上海嘉塔诺塔管理咨询有限公司</text>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api';

const consultantCount = ref(4);
const sessionCount = ref(3);
const activeTab = ref('promo');

// 四个分类的文章数据
const promoItems = ref<any[]>([]);
const newsItems = ref<any[]>([]);
const cultureItems = ref<any[]>([]);
const videoItems = ref<any[]>([]);
const daily = ref<any>({});
const lingguang = ref<any>({});
const showLingguang = ref(false);

// 灵光卡背景：今日幸运色淡雅渐变（低饱和·不抢字）
const lgBg = computed(() => {
  const hex = lingguang.value.lucky_color_hex || '#c9a96e';
  return `linear-gradient(155deg, #fbf8f1 0%, ${hex}22 55%, ${hex}38 100%)`;
});

// 按当前Tab过滤
const filteredList = computed(() => {
  switch (activeTab.value) {
    case 'promo': return promoItems.value;
    case 'news': return newsItems.value;
    case 'culture': return cultureItems.value;
    case 'video': return videoItems.value;
    default: return [];
  }
});

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
  return `${months[d.getMonth()]} · ${String(d.getDate()).padStart(2, '0')}`;
}

function mapArticles(arr: any[], defaultTag: string) {
  return arr.map((a: any) => ({
    id: a.id,
    date: a.published_at ? formatDate(a.published_at) : '',
    tag: a.brand || defaultTag,
    title: a.title,
    sub: a.summary || '',
  }));
}

async function loadArticles() {
  try {
    // 会员动态
    const r1: any = await api.articleList({ category: 'promo' });
    promoItems.value = mapArticles(Array.isArray(r1) ? r1 : (r1?.data || []), 'NEWS');

    // 行业动态
    const r2: any = await api.articleList({ category: 'news' });
    newsItems.value = mapArticles(Array.isArray(r2) ? r2 : (r2?.data || []), 'TREND');

    // 企业文化
    const r3: any = await api.articleList({ category: 'culture' });
    cultureItems.value = mapArticles(Array.isArray(r3) ? r3 : (r3?.data || []), 'CULTURE');

    // 课程直播
    const r4: any = await api.articleList({ category: 'video' });
    videoItems.value = mapArticles(Array.isArray(r4) ? r4 : (r4?.data || []), 'VIDEO');
  } catch (e) {
    // 静默失败
  }
}

async function loadDaily() {
  try {
    const d: any = await api.dailyThought();
    daily.value = d || {};
    if (d?.lingguang?.quote) {
      lingguang.value = d.lingguang;
      // 每日一次：同一天只浮现一次，不打扰
      const today = d.date || '';
      const seen = uni.getStorageSync('lg_seen_date');
      if (seen !== today) {
        showLingguang.value = true;
        uni.setStorageSync('lg_seen_date', today);
      }
    }
  } catch (e) {
    daily.value = {};
  }
}

// 分享转发（友圈/好友）携带金句
function onShareAppMessage() {
  return {
    title: lingguang.value.quote || '灵光一点 · TATA',
    path: '/pages/tata/index',
  };
}
defineExpose({ onShareAppMessage });

function onArticleTap(ev: any) {
  if (!ev.id) return;
  if (activeTab.value === 'video') {
    // 课程直播 → 打开视频号
    uni.openChannelsUserProfile?.({
      finderUserName: 'sph4oMIY5VNmo2L',
      fail: () => {
        uni.navigateTo({ url: `/pages/article/detail?id=${ev.id}` });
      },
    });
  } else {
    uni.navigateTo({ url: `/pages/article/detail?id=${ev.id}` });
  }
}

function go(url: string) {
  uni.navigateTo({ url, fail: () => uni.switchTab({ url }) });
}

onMounted(async () => {
  loadDaily();
  loadArticles();
  // 检查协议签约
  try {
    const member = uni.getStorageSync('member');
    if (member?.id) {
      const r: any = await api.checkAgreement(member.id);
      if (!r?.signed) {
        uni.redirectTo({ url: '/pages/agreement/sign' });
      }
    }
  } catch (e) {}
});
</script>

<style lang="scss">
.page {
  background: #fff;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, "PingFang SC", "Noto Serif SC", sans-serif;
}
.brand-head {
  padding: 60rpx 56rpx 32rpx;
  border-bottom: 1rpx solid #ebe8e2;
}
/* 灵光一点·浮现卡 */
.lingguang-mask {
  position: fixed;
  left: 0; top: 0; right: 0; bottom: 0;
  background: rgba(20, 16, 10, 0.45);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: lg-fade 0.5s ease;
}
@keyframes lg-fade { from { opacity: 0; } to { opacity: 1; } }
.lingguang-card {
  width: 600rpx;
  border-radius: 36rpx;
  padding: 70rpx 56rpx 48rpx;
  box-shadow: 0 30rpx 80rpx rgba(40, 30, 15, 0.28);
  animation: lg-rise 0.7s cubic-bezier(.2,.8,.2,1);
  position: relative;
  overflow: hidden;
}
@keyframes lg-rise {
  from { opacity: 0; transform: translateY(40rpx) scale(0.94); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.lg-eyebrow {
  display: block;
  text-align: center;
  font-size: 24rpx;
  letter-spacing: 14rpx;
  color: #b08a4e;
  margin-bottom: 44rpx;
}
.lg-quote {
  display: block;
  text-align: center;
  font-size: 50rpx;
  line-height: 1.7;
  letter-spacing: 6rpx;
  color: #2a2218;
  font-family: "Noto Serif SC", "Songti SC", serif;
  font-weight: 500;
}
.lg-divider {
  width: 56rpx;
  height: 2rpx;
  background: #c9a96e;
  margin: 44rpx auto 28rpx;
}
.lg-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 6rpx;
}
.lg-color {
  font-size: 22rpx;
  color: #8a7a5c;
  letter-spacing: 2rpx;
}
.lg-mark {
  font-size: 24rpx;
  letter-spacing: 4rpx;
  color: #c9a96e;
  font-weight: 600;
  font-style: italic;
}
.lg-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32rpx;
  margin-top: 40rpx;
}
.lg-btn {
  background: #2a2218;
  color: #e8cf9a;
  font-size: 26rpx;
  letter-spacing: 6rpx;
  border-radius: 40rpx;
  padding: 4rpx 0;
  width: 200rpx;
  line-height: 2.6;
  margin: 0;
}
.lg-btn::after { border: none; }
.lg-close {
  font-size: 22rpx;
  color: #a89878;
  letter-spacing: 2rpx;
}

/* 每日一念·引导态 */
.dy-intro {
  margin: 28rpx 28rpx 8rpx;
  padding: 40rpx 36rpx 36rpx;
  border-radius: 28rpx;
  background: linear-gradient(140deg, #211c16 0%, #4c3922 60%, #6b4f2a 100%);
  position: relative;
  overflow: hidden;
}
.dy-intro-deco {
  position: absolute;
  right: -50rpx; top: -50rpx;
  width: 200rpx; height: 200rpx;
  border-radius: 50%;
  background: rgba(201,169,110,.12);
}
.dy-intro-eyebrow {
  display: block;
  font-size: 22rpx;
  letter-spacing: 12rpx;
  color: #c9a96e;
  margin-bottom: 18rpx;
}
.dy-intro-title {
  display: block;
  font-size: 36rpx;
  color: #fff;
  letter-spacing: 2rpx;
  font-weight: 500;
  margin-bottom: 16rpx;
}
.dy-intro-desc {
  display: block;
  font-size: 24rpx;
  line-height: 1.7;
  color: rgba(255,255,255,.7);
  letter-spacing: 1rpx;
  margin-bottom: 28rpx;
}
.dy-intro-btn {
  display: inline-block;
  background: #c9a96e;
  color: #211c16;
  font-size: 26rpx;
  letter-spacing: 6rpx;
  padding: 14rpx 40rpx;
  border-radius: 40rpx;
  font-weight: 600;
}
.daily-main { flex: 1; }
.daily-tags { margin-top: 14rpx; }
.daily-tag {
  display: inline-block;
  font-size: 20rpx;
  color: #c9a96e;
  border: 1rpx solid rgba(201,169,110,.4);
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
  letter-spacing: 2rpx;
}
.daily-card {
  margin: 28rpx 28rpx 8rpx;
  padding: 28rpx 30rpx;
  border-radius: 26rpx;
  background: linear-gradient(135deg, #211c16 0%, #4c3922 100%);
  color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 10rpx 30rpx rgba(30, 22, 12, .12);
}
.daily-label {
  display: block;
  color: #c9a96e;
  font-size: 22rpx;
  letter-spacing: 3rpx;
}
.daily-word {
  display: block;
  margin-top: 10rpx;
  font-size: 44rpx;
  letter-spacing: 10rpx;
}
.daily-meaning {
  display: block;
  margin-top: 8rpx;
  max-width: 560rpx;
  color: rgba(255,255,255,.72);
  font-size: 24rpx;
  line-height: 1.5;
}
.daily-arr { color: #c9a96e; font-size: 42rpx; padding-left: 20rpx; }
.brand-mark {
  font-size: 40rpx;
  letter-spacing: 10rpx;
  color: #0a0a0a;
  font-weight: 500;
}
.brand-mark .reg {
  font-size: 20rpx;
  color: #c9a96e;
  vertical-align: super;
  margin-left: 4rpx;
  letter-spacing: 0;
}
.brand-tag {
  font-size: 22rpx;
  color: #9a9a9a;
  margin-top: 14rpx;
  letter-spacing: 6rpx;
}
.scroll {
  flex: 1;
}

/* section 通用 */
.section {
  padding: 40rpx 48rpx 24rpx;
}
.sec-head {
  display: flex;
  align-items: center;
  gap: 20rpx;
}
.sec-line {
  width: 48rpx;
  height: 1rpx;
  background: #c9a96e;
}
.sec-title {
  font-size: 26rpx;
  letter-spacing: 12rpx;
  color: #0a0a0a;
  font-weight: 500;
  flex: 1;
}
.sec-en {
  font-size: 22rpx;
  color: #9a9a9a;
  font-style: italic;
  letter-spacing: 3rpx;
}

/* 预约入口 */
.booking-row {
  display: flex;
  gap: 24rpx;
  padding: 0 48rpx;
}
.booking-card {
  flex: 1;
  height: 256rpx;
  border-radius: 28rpx;
  padding: 36rpx 32rpx;
  position: relative;
  overflow: hidden;
}
.booking-card.b1 {
  background: linear-gradient(135deg, #0a0a0a 0%, #2a2520 100%);
  color: #c9a96e;
}
.booking-card.b2 {
  background: linear-gradient(135deg, #7b6fdf 0%, #5d52b0 100%);
  color: #fff;
}
.booking-tag {
  display: block;
  font-size: 20rpx;
  letter-spacing: 6rpx;
  opacity: 0.6;
  margin-bottom: 16rpx;
}
.booking-name {
  display: block;
  font-size: 30rpx;
  font-weight: 500;
  letter-spacing: 6rpx;
}
.booking-sub {
  position: absolute;
  bottom: 28rpx;
  left: 32rpx;
  right: 32rpx;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  font-size: 20rpx;
  opacity: 0.7;
}
.booking-sub .arr {
  font-size: 28rpx;
  opacity: 0.9;
}
.booking-deco {
  position: absolute;
  right: -40rpx;
  top: -40rpx;
  width: 160rpx;
  height: 160rpx;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
}
.booking-card.b1 .booking-deco {
  background: rgba(201,169,110,0.1);
}

/* 了解塔塔 */
.intro-row {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding: 0 48rpx;
}
.intro-card {
  height: 200rpx;
  border-radius: 28rpx;
  padding: 36rpx 40rpx;
  display: flex;
  align-items: center;
  position: relative;
}
.intro-i1 { background: linear-gradient(135deg, #faf6ed 0%, #f4ecd8 100%); }
.intro-i2 { background: linear-gradient(135deg, #f0eefa 0%, #e8e2f7 100%); }
.intro-i3 { background: linear-gradient(135deg, #fafaf8 0%, #f0ede4 100%); }
.intro-img {
  width: 128rpx;
  height: 128rpx;
  border-radius: 20rpx;
  margin-right: 32rpx;
  flex-shrink: 0;
}
.intro-img.i1 { background: linear-gradient(135deg, #c9a96e 0%, #a88a4d 100%); }
.intro-img.i2 { background: linear-gradient(135deg, #7b6fdf 0%, #5d52b0 100%); }
.intro-img.i3 { background: linear-gradient(135deg, #2a2520 0%, #0a0a0a 100%); }
.intro-body { flex: 1; }
.intro-name {
  display: block;
  font-size: 28rpx;
  font-weight: 500;
  letter-spacing: 4rpx;
  color: #0a0a0a;
  margin-bottom: 12rpx;
}
.intro-desc {
  display: block;
  font-size: 22rpx;
  color: #555;
  letter-spacing: 1rpx;
}
.intro-arr {
  color: #c9a96e;
  font-size: 32rpx;
}

/* 事件动态 */
.event-tabs {
  display: flex;
  padding: 0 48rpx;
  border-bottom: 1rpx solid #ebe8e2;
  margin-bottom: 16rpx;
}
.event-tab {
  padding: 20rpx 0;
  margin-right: 48rpx;
  font-size: 24rpx;
  letter-spacing: 4rpx;
  color: #9a9a9a;
  position: relative;
}
.event-tab.active {
  color: #0a0a0a;
}
.event-tab.active::after {
  content: "";
  position: absolute;
  bottom: -1rpx;
  left: 0; right: 0;
  height: 2rpx;
  background: #c9a96e;
}
.event-item {
  padding: 32rpx 48rpx;
  border-bottom: 1rpx solid #ebe8e2;
  position: relative;
}
.event-meta {
  display: flex;
  align-items: center;
  gap: 16rpx;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 3rpx;
  margin-bottom: 12rpx;
}
.event-dot {
  width: 8rpx; height: 8rpx;
  border-radius: 50%;
  background: #c9a96e;
}
.event-title {
  display: block;
  font-size: 26rpx;
  color: #0a0a0a;
  line-height: 1.6;
  letter-spacing: 2rpx;
}
.event-sub {
  display: block;
  font-size: 20rpx;
  color: #9a9a9a;
  margin-top: 8rpx;
  letter-spacing: 1rpx;
}
.event-arr {
  position: absolute;
  right: 48rpx;
  top: 50%;
  transform: translateY(-50%);
  color: #c9a96e;
  font-size: 28rpx;
}
.empty-tip {
  padding: 60rpx 48rpx;
  text-align: center;
  color: #ccc;
  font-size: 24rpx;
}

.footer {
  padding: 60rpx 48rpx 80rpx;
  text-align: center;
}
.footer-en {
  display: block;
  font-size: 20rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  margin-bottom: 12rpx;
  font-style: italic;
}
.footer-cn {
  display: block;
  font-size: 20rpx;
  color: #9a9a9a;
  letter-spacing: 4rpx;
}
</style>
