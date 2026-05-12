<template>
  <view class="ref">
    <view class="hero">
      <view class="code">{{ myCode?.referral_code || '——' }}</view>
      <view class="label">我的专属推荐码</view>
      <view class="copy" @tap="copy">点击复制</view>
    </view>

    <view class="section-title">推荐进度</view>
    <view class="progress">
      <text>已确认 {{ confirmed }} / 进行中 {{ pending }}</text>
    </view>

    <view class="section-title">推荐记录</view>
    <view class="card" v-for="r in list" :key="r.id">
      <view class="top">
        <text class="name">{{ r.referee?.name }}</text>
        <text class="status" :class="r.status">{{ statusLabel(r.status) }}</text>
      </view>
      <view class="info">{{ r.referee?.phone }} · {{ fmt(r.created_at) }}</view>
    </view>
    <view class="empty" v-if="!list.length">尚无推荐记录</view>

    <view class="btn-primary" @tap="goPoster">生成推荐海报</view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { api } from '../../../api';

const myCode = ref<any>(null);
const list = ref<any[]>([]);

onMounted(async () => {
  myCode.value = await api.myCode().catch(() => null);
  list.value = (await api.myRefList().catch(() => [])) || [];
});

const confirmed = computed(() => list.value.filter(r => r.status === 'confirmed').length);
const pending = computed(() => list.value.filter(r => r.status === 'pending').length);

function statusLabel(s: string) {
  return { pending: '进行中', confirmed: '已成立', invalid: '失效' }[s] || s;
}
function fmt(t?: string) { return t ? t.slice(0, 10) : '-'; }

function copy() {
  if (!myCode.value?.referral_code) return;
  uni.setClipboardData({ data: myCode.value.referral_code });
}
function goPoster() { uni.navigateTo({ url: '/pages/referral/poster/poster' }); }
</script>

<style lang="scss" scoped>
.ref { padding-bottom: 40rpx; }
.hero {
  margin: 32rpx; padding: 60rpx 40rpx; text-align: center;
  background: linear-gradient(135deg, #8c5cff 0%, #1a1a2e 100%);
  color: #fff; border-radius: 24rpx;
  .code { font-size: 72rpx; font-weight: 800; letter-spacing: 6rpx; font-family: monospace; }
  .label { margin-top: 16rpx; font-size: 26rpx; opacity: 0.8; }
  .copy {
    margin-top: 32rpx; display: inline-block; padding: 12rpx 40rpx;
    border: 2rpx solid rgba(255,255,255,0.4); border-radius: 40rpx; font-size: 26rpx;
  }
}
.section-title { padding: 20rpx 40rpx; font-size: 28rpx; color: #666; font-weight: 600; }
.progress { padding: 0 40rpx 16rpx; color: #8c5cff; font-weight: 600; }
.card .top { display: flex; justify-content: space-between; align-items: center;
  .name { font-size: 30rpx; font-weight: 600; }
  .status {
    font-size: 22rpx; padding: 4rpx 16rpx; border-radius: 20rpx;
    background: #fff7e6; color: #fa8c16;
    &.confirmed { background: #e6ffed; color: #07c160; }
    &.invalid { background: #f5f5f5; color: #999; }
  }
}
.card .info { margin-top: 12rpx; color: #999; font-size: 24rpx; }
.empty { color: #999; padding: 40rpx; text-align: center; }
.btn-primary { margin: 40rpx; }
</style>
