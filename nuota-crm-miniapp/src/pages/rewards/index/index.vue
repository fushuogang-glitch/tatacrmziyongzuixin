<template>
  <view class="rewards">
    <view class="title">我的权益</view>
    <view class="empty" v-if="!items.length">暂无权益</view>
    <view class="card" v-for="r in items" :key="r.id">
      <view class="top">
        <text class="badge" :class="r.status">{{ label(r.status) }}</text>
        <text class="source">{{ r.source === 'referral' ? '推荐所得' : r.source }}</text>
      </view>
      <view class="name">下店权益 × 1（2 天）</view>
      <view class="time" v-if="r.activate_time">激活：{{ fmt(r.activate_time) }}</view>
      <view class="time" v-if="r.expire_time">到期：{{ fmt(r.expire_time) }}</view>
      <view class="btn-primary" v-if="r.status === 'available'" @tap="apply(r.id)">申请下店</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../../../api';
import { onShow } from '@dcloudio/uni-app';

const items = ref<any[]>([]);

async function load() {
  items.value = (await api.myRewards().catch(() => [])) || [];
}
onMounted(load);
onShow(load);

function label(s: string) {
  return { available: '可使用', booked: '预约中', used: '已使用', expired: '已过期' }[s] || s;
}
function fmt(t?: string) { return t ? t.replace('T', ' ').slice(0, 16) : '-'; }

function apply(id: number) {
  uni.navigateTo({ url: `/pages/booking/apply/apply?reward_id=${id}` });
}
</script>

<style lang="scss" scoped>
.rewards { padding-bottom: 40rpx; }
.title { padding: 32rpx 40rpx 0; font-size: 40rpx; font-weight: 700; }
.empty { color: #999; padding: 60rpx; text-align: center; }
.card {
  .top { display: flex; justify-content: space-between; align-items: center;
    .badge {
      font-size: 22rpx; padding: 6rpx 16rpx; border-radius: 20rpx;
      background: #e6ffed; color: #07c160;
      &.booked { background: #fff7e6; color: #fa8c16; }
      &.used,&.expired { background: #f5f5f5; color: #999; }
    }
    .source { color: #999; font-size: 24rpx; }
  }
  .name { margin-top: 20rpx; font-size: 32rpx; font-weight: 600; }
  .time { margin-top: 8rpx; color: #666; font-size: 24rpx; }
  .btn-primary { margin-top: 24rpx; }
}
</style>
