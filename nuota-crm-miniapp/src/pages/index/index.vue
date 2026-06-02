<template>
  <view class="home">
    <!-- 学员证 -->
    <view class="member-card">
      <view class="brand">诺控·塔塔 · 学员证</view>
      <view class="name">{{ user?.name || '未登录' }}</view>
      <view class="meta">
        <text>{{ user?.member_no || '——' }}</text>
        <text class="type">{{ typeLabel }}</text>
      </view>
      <view class="expire" v-if="user?.expire_date">有效期至 {{ user.expire_date }}</view>
    </view>

    <!-- 快捷入口 -->
    <view class="grid">
      <!-- 扫脸签到暂时隐藏
      <view class="grid-item" @tap="go('/pages/face/checkin/checkin')">
        <text class="icon">📷</text><text>扫脸签到</text>
      </view>
      -->
      <view class="grid-item" @tap="go('/pages/sessions/list/list')">
        <text class="icon">📅</text><text>课程报名</text>
      </view>
      <view class="grid-item" @tap="go('/pages/referral/index/index')">
        <text class="icon">🤝</text><text>推荐中心</text>
      </view>
      <view class="grid-item" @tap="go('/pages/rewards/index/index')">
        <text class="icon">🎁</text><text>我的权益</text>
      </view>
      <view class="grid-item" @tap="go('/pages/booking/list/list')">
        <text class="icon">🏪</text><text>下店预约</text>
      </view>
      <view class="grid-item" @tap="go('/pages/handbook/day1/day1')">
        <text class="icon">📖</text><text>课程手册</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useUserStore } from '../../store/user';
import { api } from '../../api';

const store = useUserStore();
const user = computed(() => store.user);
const typeLabel = computed(() => {
  const t = store.user?.member_type;
  return t === 'annual' ? '年费' : t === 'vip' ? 'VIP' : '试听';
});

function go(url: string) {
  uni.navigateTo({ url }).catch(() => uni.switchTab({ url }));
}

onMounted(async () => {
  if (!store.token) {
    uni.reLaunch({ url: '/pages/login/login' });
    return;
  }
  try {
    const u: any = await api.me();
    store.setUser(u);
  } catch (_) { /* 401 已重定向 */ }
});
</script>

<style lang="scss" scoped>
.home { padding-bottom: 60rpx; }

.member-card {
  margin: 32rpx;
  padding: 48rpx 40rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #1a1a2e 0%, #3d3d6b 50%, #8c5cff 100%);
  color: #fff;
  box-shadow: 0 8rpx 40rpx rgba(26,26,46,0.3);

  .brand { font-size: 26rpx; opacity: 0.8; letter-spacing: 2rpx; }
  .name { font-size: 52rpx; margin-top: 20rpx; font-weight: 700; }
  .meta {
    margin-top: 20rpx;
    display: flex; justify-content: space-between; align-items: center;
    font-size: 26rpx; opacity: 0.9;
    .type {
      background: rgba(255,255,255,0.2);
      padding: 6rpx 18rpx; border-radius: 20rpx;
    }
  }
  .expire { margin-top: 16rpx; font-size: 24rpx; opacity: 0.7; }
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20rpx;
  padding: 0 32rpx;

  .grid-item {
    background: #fff;
    border-radius: 16rpx;
    padding: 40rpx 0;
    text-align: center;
    box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
    .icon { font-size: 60rpx; display: block; margin-bottom: 16rpx; }
  }
}
</style>
