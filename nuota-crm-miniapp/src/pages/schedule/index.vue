<template>
  <view class="page">
    <!-- 顶部 hero -->
    <view class="hero">
      <text class="hero-en">MY SCHEDULE</text>
      <text class="hero-title">我 的 排 期</text>
      <view class="hero-summary">
        <view class="sum-item">
          <text class="sum-num">{{ upcoming }}</text>
          <text class="sum-label">即将到来</text>
        </view>
        <view class="sum-item">
          <text class="sum-num">{{ inProgress }}</text>
          <text class="sum-label">进行中</text>
        </view>
        <view class="sum-item">
          <text class="sum-num">{{ completed }}</text>
          <text class="sum-label">已完成</text>
        </view>
      </view>
    </view>

    <!-- Tab切换 -->
    <view class="tabs">
      <view v-for="t in tabs" :key="t.key"
            :class="['tab', activeTab === t.key ? 'active' : '']"
            @tap="activeTab = t.key">
        <text>{{ t.label }}</text>
      </view>
    </view>

    <!-- 排期列表 -->
    <view class="list">
      <view v-if="!filteredItems.length" class="empty">
        <text class="empty-icon">📅</text>
        <text class="empty-text">暂无排期</text>
      </view>

      <view v-for="item in filteredItems" :key="item.id + '-' + item.type"
            class="card" @tap="goDetail(item)">
        <view class="card-top">
          <view class="card-date-box">
            <text class="card-month">{{ formatMonth(item.date) }}</text>
            <text class="card-day">{{ formatDay(item.date) }}</text>
          </view>
          <view class="card-info">
            <text class="card-title">{{ item.title || item.service_name || '排期' }}</text>
            <text class="card-sub">{{ item.consultant_name || '' }} · {{ item.store_name || item.city || '' }}</text>
          </view>
          <view :class="['card-badge', badgeClass(item)]">
            <text>{{ item.status_label || item.status }}</text>
          </view>
        </view>

        <!-- 进度条 -->
        <view v-if="item.workflow_progress != null && item.workflow_progress > 0" class="card-progress">
          <view class="card-pbar">
            <view class="card-pfill" :style="{ width: item.workflow_progress + '%' }"></view>
          </view>
          <text class="card-ptext">{{ item.workflow_stage || '' }} · {{ item.workflow_progress }}%</text>
        </view>

        <view class="card-type">
          <text :class="['type-tag', item.type]">{{ typeLabel(item.type) }}</text>
          <text class="card-time" v-if="item.appoint_time">{{ item.appoint_time }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api';

const items = ref<any[]>([]);
const activeTab = ref('all');

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'upcoming', label: '即将到来' },
  { key: 'active', label: '进行中' },
  { key: 'done', label: '已完成' },
];

const upcoming = computed(() =>
  items.value.filter(i => ['pending', 'confirmed', 'accepted'].includes(i.status)).length);
const inProgress = computed(() =>
  items.value.filter(i => ['preparing', 'in_progress', 'follow_up'].includes(i.status)).length);
const completed = computed(() =>
  items.value.filter(i => i.status === 'completed').length);

const filteredItems = computed(() => {
  if (activeTab.value === 'all') return items.value;
  if (activeTab.value === 'upcoming')
    return items.value.filter(i => ['pending', 'confirmed', 'accepted'].includes(i.status));
  if (activeTab.value === 'active')
    return items.value.filter(i => ['preparing', 'in_progress', 'follow_up'].includes(i.status));
  return items.value.filter(i => i.status === 'completed' || i.status === 'cancelled');
});

function formatMonth(d: string) {
  if (!d) return '';
  const months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
  const parts = d.split('-');
  return months[Number(parts[1]) - 1] || '';
}

function formatDay(d: string) {
  if (!d) return '';
  return String(Number(d.split('-')[2]));
}

function badgeClass(item: any) {
  const s = item.status;
  if (['in_progress', 'preparing', 'follow_up'].includes(s)) return 'active';
  if (['pending', 'confirmed', 'accepted'].includes(s)) return 'upcoming';
  if (s === 'completed') return 'done';
  return 'other';
}

function typeLabel(t: string) {
  const m: Record<string, string> = {
    service_order: '专案服务',
    visit_booking: '下店预约',
    manual_schedule: '排期安排',
  };
  return m[t] || '排期';
}

function goDetail(item: any) {
  if (item.type === 'service_order' && item.order_id) {
    uni.navigateTo({ url: `/pages/service/order-detail?id=${item.order_id}` });
  } else if (item.type === 'visit_booking') {
    uni.navigateTo({ url: `/pages/booking/list/list` });
  }
}

onMounted(async () => {
  try {
    const res: any = await api.mySchedules();
    items.value = Array.isArray(res) ? res : [];
    // 按日期排序，最近的在前
    items.value.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
  } catch (e) {
    items.value = [];
  }
});
</script>

<style lang="scss">
.page { background: #fff; min-height: 100vh; }

.hero {
  padding: 60rpx 48rpx 36rpx;
  background: linear-gradient(135deg, #0a0a0a 0%, #2a2520 100%);
  color: #fff;
}
.hero-en { display: block; font-size: 20rpx; color: #9a9a9a; letter-spacing: 6rpx; margin-bottom: 8rpx; }
.hero-title { display: block; font-size: 40rpx; letter-spacing: 12rpx; font-weight: 500; }
.hero-summary {
  display: flex;
  gap: 40rpx;
  margin-top: 32rpx;
}
.sum-item { text-align: center; }
.sum-num { display: block; font-size: 44rpx; color: #c9a96e; font-weight: 600; }
.sum-label { display: block; font-size: 20rpx; color: #9a9a9a; letter-spacing: 4rpx; margin-top: 4rpx; }

.tabs {
  display: flex;
  padding: 24rpx 48rpx;
  gap: 24rpx;
  border-bottom: 1rpx solid #ebe8e2;
}
.tab {
  padding: 12rpx 28rpx;
  font-size: 24rpx;
  color: #9a9a9a;
  border-radius: 28rpx;
  letter-spacing: 3rpx;
}
.tab.active {
  background: #0a0a0a;
  color: #c9a96e;
}

.list { padding: 24rpx 48rpx; }
.empty { text-align: center; padding: 80rpx 0; }
.empty-icon { font-size: 80rpx; display: block; margin-bottom: 16rpx; }
.empty-text { font-size: 24rpx; color: #9a9a9a; letter-spacing: 4rpx; }

.card {
  padding: 28rpx 0;
  border-bottom: 1rpx solid #f5f0e8;
}
.card:last-child { border-bottom: none; }
.card-top {
  display: flex;
  align-items: flex-start;
  gap: 24rpx;
}
.card-date-box {
  width: 80rpx;
  text-align: center;
  flex-shrink: 0;
}
.card-month { display: block; font-size: 18rpx; color: #c9a96e; letter-spacing: 2rpx; }
.card-day { display: block; font-size: 44rpx; font-weight: 600; color: #0a0a0a; line-height: 1.1; }
.card-info { flex: 1; }
.card-title {
  display: block;
  font-size: 28rpx;
  font-weight: 500;
  color: #0a0a0a;
  letter-spacing: 3rpx;
  margin-bottom: 6rpx;
}
.card-sub { display: block; font-size: 22rpx; color: #9a9a9a; }
.card-badge {
  padding: 6rpx 18rpx;
  border-radius: 20rpx;
  font-size: 20rpx;
  flex-shrink: 0;
  letter-spacing: 2rpx;
}
.card-badge.upcoming { background: rgba(123,111,223,0.1); color: #7b6fdf; }
.card-badge.active { background: rgba(201,169,110,0.12); color: #c9a96e; }
.card-badge.done { background: #e6ffed; color: #07c160; }
.card-badge.other { background: #f5f5f5; color: #999; }

.card-progress { margin-top: 16rpx; padding-left: 104rpx; }
.card-pbar {
  height: 6rpx;
  background: #ebe8e2;
  border-radius: 3rpx;
  overflow: hidden;
}
.card-pfill {
  height: 100%;
  background: linear-gradient(90deg, #c9a96e, #7b6fdf);
}
.card-ptext {
  display: block;
  text-align: right;
  font-size: 18rpx;
  color: #c9a96e;
  margin-top: 6rpx;
}

.card-type {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 12rpx;
  padding-left: 104rpx;
}
.type-tag {
  font-size: 18rpx;
  padding: 4rpx 14rpx;
  border-radius: 12rpx;
  letter-spacing: 2rpx;
}
.type-tag.service_order { background: rgba(201,169,110,0.1); color: #c9a96e; }
.type-tag.visit_booking { background: rgba(123,111,223,0.1); color: #7b6fdf; }
.type-tag.manual_schedule { background: rgba(24,144,255,0.1); color: #1890ff; }
.card-time { font-size: 20rpx; color: #9a9a9a; }
</style>
