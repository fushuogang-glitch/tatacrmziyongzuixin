<template>
  <view class="list">
    <view class="title">我的预约</view>
    <view class="empty" v-if="!items.length">暂无预约</view>
    <view class="card" v-for="b in items" :key="b.id">
      <view class="top">
        <text class="date">{{ b.confirmed_date || b.preferred_date }}</text>
        <text class="status" :class="b.status">{{ label(b.status) }}</text>
      </view>
      <view class="info">📍 {{ b.city || '' }} · {{ b.address || '' }}</view>
      <view class="info">⏱ {{ b.duration_days }} 天</view>
      <view class="info" v-if="b.remark">备注：{{ b.remark }}</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../../../api';

const items = ref<any[]>([]);

onMounted(async () => {
  items.value = (await api.myBookings().catch(() => [])) || [];
});

function label(s: string) {
  return { pending: '待审核', confirmed: '已确认', completed: '已完成', cancelled: '已取消' }[s] || s;
}
</script>

<style lang="scss" scoped>
.list { padding-bottom: 40rpx; }
.title { padding: 32rpx 40rpx 0; font-size: 40rpx; font-weight: 700; }
.empty { color: #999; padding: 60rpx; text-align: center; }
.card .top { display: flex; justify-content: space-between; align-items: center;
  .date { font-size: 32rpx; font-weight: 700; }
  .status {
    font-size: 22rpx; padding: 4rpx 16rpx; border-radius: 20rpx;
    background: #fff7e6; color: #fa8c16;
    &.confirmed { background: #e6f7ff; color: #1890ff; }
    &.completed { background: #e6ffed; color: #07c160; }
    &.cancelled { background: #f5f5f5; color: #999; }
  }
}
.card .info { margin-top: 12rpx; color: #666; font-size: 26rpx; }
</style>
