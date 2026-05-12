<template>
  <view class="list">
    <view class="title">课程场次</view>
    <view class="empty" v-if="!items.length">暂无可报名场次</view>
    <view class="item card" v-for="s in items" :key="s.id" @tap="go(s.id)">
      <view class="top">
        <text class="no">{{ s.session_no }}</text>
        <text class="status" :class="s.status">{{ statusLabel(s.status) }}</text>
      </view>
      <view class="info">{{ s.start_date }} ~ {{ s.end_date }}</view>
      <view class="info">{{ s.location || '' }}（{{ s.city || '' }}）</view>
      <view class="quota">名额：{{ s.enrolled }}/{{ s.capacity }}</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '../../../api';

const items = ref<any[]>([]);

onMounted(async () => {
  const list: any = await api.availableSessions().catch(() => []);
  items.value = list || [];
});

function statusLabel(s: string) {
  return { open: '报名中', full: '已满', closed: '已停', finished: '已结束' }[s] || s;
}

function go(id: number) {
  uni.navigateTo({ url: `/pages/sessions/detail/detail?id=${id}` });
}
</script>

<style lang="scss" scoped>
.list { padding-bottom: 40rpx; }
.title { padding: 32rpx 40rpx 0; font-size: 40rpx; font-weight: 700; }
.empty { color: #999; padding: 60rpx; text-align: center; }
.item {
  .top { display: flex; justify-content: space-between; align-items: center;
    .no { font-size: 32rpx; font-weight: 700; }
    .status {
      font-size: 22rpx; padding: 6rpx 16rpx; border-radius: 20rpx;
      background: #e6ffed; color: #07c160;
      &.full { background: #fff7e6; color: #fa8c16; }
      &.closed,&.finished { background: #f5f5f5; color: #999; }
    }
  }
  .info { color: #666; margin-top: 12rpx; font-size: 26rpx; }
  .quota { margin-top: 16rpx; color: #8c5cff; font-size: 26rpx; }
}
</style>
