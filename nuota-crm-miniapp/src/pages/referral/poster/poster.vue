<template>
  <view class="poster">
    <view class="card-body">
      <view class="brand">诺控·塔塔 学员推荐</view>
      <view class="hero">
        <view class="name">{{ user?.name }}</view>
        <view class="enterprise">{{ user?.enterprise_name || '' }}</view>
      </view>
      <view class="code-box">
        <text class="code">{{ user?.referral_code }}</text>
        <text class="tip">报名时填写我的推荐码，双方得权益</text>
      </view>
      <view class="footer">武汉诺塔智控科技有限公司</view>
    </view>
    <view class="btn-primary" @tap="save">保存海报</view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useUserStore } from '../../../store/user';

const store = useUserStore();
const user = computed(() => store.user);

function save() {
  uni.showToast({ title: '请长按海报保存', icon: 'none' });
}
</script>

<style lang="scss" scoped>
.poster { padding: 40rpx; }
.card-body {
  background: linear-gradient(135deg, #1a1a2e 0%, #8c5cff 100%);
  color: #fff; border-radius: 32rpx; padding: 80rpx 40rpx;
  text-align: center;
  .brand { font-size: 28rpx; opacity: 0.8; letter-spacing: 2rpx; }
  .hero { margin: 80rpx 0 120rpx;
    .name { font-size: 64rpx; font-weight: 700; }
    .enterprise { margin-top: 20rpx; font-size: 28rpx; opacity: 0.7; }
  }
  .code-box {
    .code { font-size: 80rpx; font-weight: 800; letter-spacing: 8rpx; font-family: monospace; }
    .tip { display: block; margin-top: 20rpx; font-size: 24rpx; opacity: 0.8; }
  }
  .footer { margin-top: 80rpx; font-size: 22rpx; opacity: 0.5; }
}
.btn-primary { margin-top: 40rpx; }
</style>
