<template>
  <view class="page">
    <scroll-view scroll-y class="scroll">
      <!-- 会员卡 -->
      <view class="member-hero">
        <text class="m-greet">— {{ greetEn }} —</text>
        <text class="m-name">{{ name }}  {{ honorific }}</text>
        <view class="m-level">◆ {{ tierLabel }}  {{ tierEn }}</view>

        <view class="m-balance">
          <view>
            <text class="m-bal-label">ENTERPRISE</text>
            <text class="m-ent-name">{{ enterpriseName || '—' }}</text>
          </view>
          <view class="m-stats-group">
            <view class="m-times">
              <text class="m-times-en">YEAR</text>
              <text class="m-times-num">{{ serviceOrderCount }} 次</text>
              <text class="m-times-cn">已服务</text>
            </view>
            <view class="m-times">
              <text class="m-times-en">JOINED</text>
              <text class="m-times-num">{{ cooperationYears }} 年</text>
              <text class="m-times-cn">已合作</text>
            </view>
          </view>
        </view>
      </view>

      <view class="stats-row">
        <view class="stat">
          <text class="stat-num">{{ serviceOrderCount }} 次</text>
          <text class="stat-label">YEAR · 年度下店</text>
        </view>
        <view class="stat purple">
          <text class="stat-num">{{ referCount }}</text>
          <text class="stat-label">REFER · 推荐学员</text>
        </view>
      </view>

      <view class="refer-card" @tap="go('/pages/referral/index/index')">
        <text class="refer-label">REFERRAL INCOME</text>
        <text class="refer-title">推 荐 收 益</text>
        <view class="refer-num-row">
          <view>
            <text class="refer-num">¥ {{ referIncome }}</text>
            <text class="refer-sub">本年累计 · {{ referCount }}位学员</text>
          </view>
          <view class="refer-arrow">→</view>
        </view>
      </view>

      <view class="section">
        <view class="sec-head">
          <view class="sec-line"></view>
          <text class="sec-title">会 员 中 心</text>
          <text class="sec-en">Center</text>
        </view>
      </view>

      <view class="list-row" @tap="go('/pages/staff/list')">
        <text class="list-l">企 业 学 员</text>
        <text class="list-r gold">{{ staffCount }} 人 →</text>
      </view>
      <view class="list-row" @tap="go('/pages/service/index')">
        <text class="list-l">服 务 记 录</text>
        <text class="list-r">{{ serviceOrderCount }} 次 →</text>
      </view>
      <view class="list-row" @tap="go('/pages/schedule/index')">
        <text class="list-l">我 的 排 期</text>
        <text class="list-r gold">查看全部 →</text>
      </view>
      <view class="list-row" @tap="go('/pages/sessions/list/list')">
        <text class="list-l">课 程 记 录</text>
        <text class="list-r">{{ courseCount }} 门 →</text>
      </view>
      <view class="list-row" @tap="go('/pages/referral/index/index')">
        <text class="list-l">推 荐 学 员</text>
        <text class="list-r gold">{{ referCount }} 位 →</text>
      </view>
      <view class="list-row" @tap="go('/pages/rewards/index/index')">
        <text class="list-l">会 员 权 益</text>
        <text class="list-r">{{ tierLabel }} →</text>
      </view>
      <view class="list-row" @tap="go('/pages/daily-thought/index')">
        <text class="list-l">每 日 一 念</text>
        <text class="list-r gold">黄历 / 一卦 →</text>
      </view>
      <!-- 人脸认证入口暂时隐藏（待接入国家网络身份认证后恢复）
      <view class="list-row" @tap="go('/pages/face/bind/bind')" v-if="false">
        <text class="list-l">人 脸 认 证</text>
        <text class="list-r">{{ faceBound ? '已绑定' : '去绑定' }} →</text>
      </view>
      -->
      <view class="list-row" @tap="go('/pages/agreement/sign')">
        <text class="list-l">服 务 协 议</text>
        <text class="list-r">v1.0 →</text>
      </view>
      <view class="list-row" @tap="go('/pages/about/brand')">
        <text class="list-l">关 于 塔 塔</text>
        <text class="list-r">→</text>
      </view>
      <button class="list-row last cs-btn" open-type="contact">
        <text class="list-l">联 系 客 服</text>
        <text class="list-r gold">在线咨询 →</text>
      </button>

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

const name = ref('');
const honorific = ref('先生');
const enterpriseName = ref('');
const cooperationYears = ref(0);
const serviceOrderCount = ref(0);
const staffCount = ref(0);
const annualSpending = ref(0);
const referCount = ref(0);
const referIncome = ref('0');
const courseCount = ref(0);
const faceBound = ref(false);
const tier = ref('primary');

const greetEn = computed(() => {
  const h = new Date().getHours();
  if (h < 6) return 'GOOD NIGHT';
  if (h < 12) return 'GOOD MORNING';
  if (h < 18) return 'GOOD AFTERNOON';
  return 'GOOD EVENING';
});

const tierLabel = computed(() => {
  const m: Record<string, string> = {
    kindergarten: '幼苗', primary: '新芽', junior: '银卡',
    senior: '金卡', college: '铂金', master: '钻石',
    doctor: '黑金', postdoc: '至尊', teacher: '导师'
  };
  return m[tier.value] || '新芽';
});
const tierEn = computed(() => {
  const m: Record<string, string> = {
    kindergarten: 'SEEDLING', primary: 'SPROUT', junior: 'SILVER',
    senior: 'GOLD', college: 'PLATINUM', master: 'DIAMOND',
    doctor: 'BLACK GOLD', postdoc: 'SUPREME', teacher: 'MENTOR'
  };
  return m[tier.value] || 'SPROUT';
});

function go(url: string) {
  uni.navigateTo({ url, fail: () => uni.switchTab({ url }) });
}

onMounted(async () => {
  try {
    const r: any = await api.me();
    if (r) {
      name.value = r.name || '';
      tier.value = r.member_tier || 'primary';
      enterpriseName.value = r.enterprise_name || '';
      cooperationYears.value = r.cooperation_years || 0;
      serviceOrderCount.value = r.service_order_count || 0;
      staffCount.value = r.staff_count || 0;
      annualSpending.value = r.annual_spending || 0;
      faceBound.value = !!r.face_bound;
      referCount.value = r.referral_count || 0;
      referIncome.value = String(r.referral_income || 0);
      courseCount.value = r.course_count || 0;
    }
  } catch (e) {}
});
</script>

<style lang="scss">
.page {
  background: #fff;
  min-height: 100vh;
}
.scroll {
  min-height: 100vh;
}
.member-hero {
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #2a2520 100%);
  padding: 80rpx 48rpx 64rpx;
  color: #fff;
  position: relative;
  overflow: hidden;
}
.m-greet {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  margin-bottom: 20rpx;
  font-style: italic;
}
.m-name {
  display: block;
  font-size: 36rpx;
  font-weight: 500;
  letter-spacing: 6rpx;
  margin-bottom: 28rpx;
}
.m-level {
  display: inline-block;
  padding: 8rpx 24rpx;
  border: 1rpx solid #c9a96e;
  border-radius: 28rpx;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 4rpx;
}
.m-balance {
  margin-top: 48rpx;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.m-bal-label {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 4rpx;
  margin-bottom: 12rpx;
}
.m-ent-name {
  display: block;
  font-size: 48rpx;
  color: #c9a96e;
  font-weight: 400;
  letter-spacing: 6rpx;
  line-height: 1;
}
.m-stats-group {
  display: flex;
  gap: 32rpx;
  align-items: flex-end;
}
.m-times {
  text-align: right;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 3rpx;
}
.m-times-en { display: block; }
.m-times-num {
  display: block;
  color: #fff;
  font-size: 32rpx;
  font-weight: 500;
  margin: 6rpx 0;
}
.m-times-cn { display: block; }

.stats-row {
  display: flex;
  padding: 0 48rpx;
  margin: 40rpx 0;
  gap: 24rpx;
}
.stat {
  flex: 1;
  background: linear-gradient(135deg, #faf6ed 0%, #f4ecd8 100%);
  border-radius: 24rpx;
  padding: 28rpx;
  text-align: center;
}
.stat.purple {
  background: linear-gradient(135deg, #f0eefa 0%, #e8e2f7 100%);
}
.stat-num {
  display: block;
  font-size: 44rpx;
  color: #a88a4d;
  font-weight: 500;
  line-height: 1;
}
.stat.purple .stat-num { color: #5d52b0; }
.stat-label {
  display: block;
  font-size: 20rpx;
  color: #555;
  margin-top: 12rpx;
  letter-spacing: 3rpx;
}

.refer-card {
  margin: 0 48rpx 32rpx;
  background: linear-gradient(135deg, #c9a96e 0%, #7b6fdf 100%);
  border-radius: 28rpx;
  padding: 36rpx;
  color: #fff;
}
.refer-label {
  display: block;
  font-size: 22rpx;
  letter-spacing: 6rpx;
  opacity: 0.85;
  margin-bottom: 12rpx;
}
.refer-title {
  display: block;
  font-size: 28rpx;
  letter-spacing: 4rpx;
  margin-bottom: 28rpx;
  font-weight: 500;
}
.refer-num-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.refer-num {
  display: block;
  font-size: 52rpx;
  font-weight: 500;
  line-height: 1;
}
.refer-sub {
  display: block;
  font-size: 20rpx;
  opacity: 0.85;
  margin-top: 8rpx;
  letter-spacing: 1rpx;
}
.refer-arrow {
  background: rgba(255,255,255,0.2);
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  color: #fff;
}

.section {
  padding: 24rpx 48rpx;
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
  flex: 1;
  font-weight: 500;
}
.sec-en {
  font-size: 22rpx;
  color: #9a9a9a;
  font-style: italic;
}

.list-row {
  padding: 28rpx 48rpx;
  border-bottom: 1rpx solid #ebe8e2;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.list-row.last { border-bottom: none; }
.list-l {
  font-size: 26rpx;
  letter-spacing: 4rpx;
  color: #0a0a0a;
}
.list-r {
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 1rpx;
}
.list-r.gold { color: #a88a4d; }

.cs-btn {
  background: none;
  border: none;
  border-radius: 0;
  margin: 0;
  padding: 28rpx 48rpx;
  border-bottom: none;
  line-height: normal;
  font-size: inherit;
  text-align: left;
}
.cs-btn::after {
  border: none;
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
