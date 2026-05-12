<template>
  <view class="detail" v-if="data">
    <view class="card">
      <view class="no">{{ data.session_no }}</view>
      <view class="info">📅 {{ data.start_date }} ~ {{ data.end_date }}</view>
      <view class="info">📍 {{ data.location }}（{{ data.city }}）</view>
      <view class="info">👥 已报名 {{ data.enrolled }} / {{ data.capacity }}</view>
    </view>
    <view class="btn-primary" @tap="enroll" v-if="data.status === 'open'">立即报名</view>
    <view class="btn-ghost" v-else>当前不可报名（{{ data.status }}）</view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../../../api';
import { onLoad } from '@dcloudio/uni-app';

const id = ref(0);
const data = ref<any>(null);

onLoad((opt: any) => { id.value = Number(opt?.id || 0); });

async function refresh() {
  const all: any = await api.availableSessions().catch(() => []);
  data.value = (all || []).find((s: any) => s.id === id.value) || null;
}

onMounted(refresh);

async function enroll() {
  uni.showLoading({ title: '报名中' });
  try {
    await api.enrollSession(id.value);
    uni.showToast({ title: '报名成功' });
    refresh();
  } catch (_) {} finally { uni.hideLoading(); }
}
</script>

<style lang="scss" scoped>
.detail { padding-bottom: 40rpx; }
.card .no { font-size: 40rpx; font-weight: 700; }
.card .info { margin-top: 16rpx; color: #666; font-size: 28rpx; }
.btn-primary, .btn-ghost { margin: 40rpx; }
.btn-ghost {
  text-align: center; padding: 24rpx 0;
  border: 1rpx solid #ddd; border-radius: 12rpx; color: #999;
}
</style>
