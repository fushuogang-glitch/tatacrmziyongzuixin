<template>
  <view class="page">
    <view class="brand-head">
      <text class="brand-mark">TATA CONSULTING<text class="reg">®</text></text>
      <text class="brand-tag">深 度 服 务 · 专 案 跟 进</text>
    </view>

    <scroll-view scroll-y class="scroll">
      <view class="hero">
        <text class="hero-en">SERVICE BOOKING</text>
        <text class="hero-cn">专 案 预 约</text>
        <view class="hero-line"></view>
        <text class="hero-desc">日历看板 · 老师筛选 · 工单跟进 · 满意度评价</text>
      </view>

      <view class="calendar-card" @tap="go('/pages/service/list')">
        <view class="cal-icon">
          <text class="m">{{ todayMonth }}</text>
          <text class="d">{{ todayDay }}</text>
        </view>
        <view class="cal-body">
          <text class="cal-title">日 历 看 板</text>
          <text class="cal-sub">查看所有老师档期 · 实时预约</text>
        </view>
        <text class="cal-arr">→</text>
      </view>

      <view class="section">
        <view class="sec-head">
          <view class="sec-line"></view>
          <text class="sec-title">我 的 服 务</text>
          <text class="sec-en">My Service</text>
        </view>
      </view>

      <view v-if="orders.length === 0" class="empty">
        <text>暂无服务工单</text>
        <text class="empty-sub">点击上方日历看板预约</text>
      </view>

      <view v-for="o in orders" :key="o.id" class="service-card" @tap="goDetail(o.id)">
        <view class="sc-head">
          <text :class="['sc-status', statusClass(o.status)]">{{ statusLabel(o.status) }}</text>
          <text class="sc-time">{{ o.appoint_date }} {{ o.appoint_time }}</text>
        </view>
        <text class="sc-name">{{ o.service_name || '专案服务' }}</text>
        <text class="sc-teacher">老师：{{ o.consultant_name || '待分配' }} · {{ o.store_name || '门店待定' }}</text>
        <view class="sc-bar">
          <view class="sc-bar-fill" :style="{ width: (o.workflow_progress || 0) + '%' }"></view>
        </view>
      </view>

      <view class="footer">
        <text class="footer-en">— TATA CONSULTING® —</text>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../../api';

const orders = ref<any[]>([]);
const todayMonth = ref('MAY');
const todayDay = ref('15');

function statusClass(s: string) {
  return s === 'in_progress' ? 's1'
    : s === 'pending' || s === 'confirmed' ? 's2'
    : 's3';
}
function statusLabel(s: string) {
  const m: Record<string, string> = {
    pending: '待确认', confirmed: '已确认', accepted: '老师已接单',
    preparing: '执案准备', in_progress: '执 案 中',
    reporting: '报告提交', follow_up: '执案跟进',
    completed: '已 完 成', cancelled: '已取消'
  };
  return m[s] || s;
}
function go(url: string) {
  uni.navigateTo({ url });
}
function goDetail(id: number) {
  uni.navigateTo({ url: `/pages/service/order-detail?id=${id}` });
}

onMounted(async () => {
  const now = new Date();
  todayMonth.value = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'][now.getMonth()];
  todayDay.value = String(now.getDate()).padStart(2, '0');

  try {
    const member = uni.getStorageSync('member');
    if (member?.id) {
      const r: any = await api.myServiceOrders(member.id);
      orders.value = r || [];
    } else {
      // 演示数据
      orders.value = [
        { id: 1, service_name: '门店全案诊断', consultant_name: '刘静', store_name: '武汉一二一旗舰店', appoint_date: '2026-05-13', appoint_time: '14:00', status: 'in_progress', workflow_progress: 65 },
        { id: 2, service_name: '品项体系重构', consultant_name: '王芳', store_name: '长沙Q+新颜二店', appoint_date: '2026-05-16', appoint_time: '10:00', status: 'confirmed', workflow_progress: 0 },
        { id: 3, service_name: '团队信任度建设', consultant_name: '张媛', store_name: '满意度 4.9', appoint_date: '2026-05-05', appoint_time: '', status: 'completed', workflow_progress: 100 },
      ];
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
}
.brand-head {
  padding: 60rpx 48rpx 32rpx;
  text-align: center;
  border-bottom: 1rpx solid #ebe8e2;
}
.brand-mark {
  font-size: 32rpx;
  letter-spacing: 8rpx;
  color: #0a0a0a;
  font-weight: 500;
}
.brand-mark .reg {
  font-size: 16rpx;
  color: #c9a96e;
  vertical-align: super;
  margin-left: 4rpx;
}
.brand-tag {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  margin-top: 12rpx;
  letter-spacing: 6rpx;
}

.scroll { flex: 1; }

.hero {
  padding: 48rpx 48rpx 32rpx;
  background: linear-gradient(180deg, #fafaf8 0%, #fff 100%);
  text-align: center;
  border-bottom: 1rpx solid #ebe8e2;
}
.hero-en {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  margin-bottom: 12rpx;
  font-style: italic;
}
.hero-cn {
  display: block;
  font-size: 36rpx;
  letter-spacing: 16rpx;
  color: #0a0a0a;
  font-weight: 500;
}
.hero-line {
  width: 48rpx;
  height: 1rpx;
  background: #c9a96e;
  margin: 24rpx auto;
}
.hero-desc {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 3rpx;
  line-height: 1.8;
}

.calendar-card {
  margin: 40rpx 48rpx 0;
  background: linear-gradient(135deg, #faf6ed 0%, #f4ecd8 100%);
  border-radius: 28rpx;
  padding: 36rpx 40rpx;
  display: flex;
  align-items: center;
}
.cal-icon {
  width: 96rpx; height: 96rpx;
  background: #fff;
  border-radius: 20rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-right: 28rpx;
}
.cal-icon .m { font-size: 18rpx; color: #c9a96e; letter-spacing: 2rpx; }
.cal-icon .d { font-size: 36rpx; color: #0a0a0a; font-weight: 500; line-height: 1.2; }
.cal-body { flex: 1; }
.cal-title {
  display: block;
  font-size: 28rpx;
  letter-spacing: 6rpx;
  color: #0a0a0a;
  font-weight: 500;
  margin-bottom: 8rpx;
}
.cal-sub {
  display: block;
  font-size: 20rpx;
  color: #555;
  letter-spacing: 2rpx;
}
.cal-arr {
  color: #c9a96e;
  font-size: 32rpx;
}

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
  flex: 1;
  font-weight: 500;
}
.sec-en {
  font-size: 22rpx;
  color: #9a9a9a;
  font-style: italic;
}

.empty {
  text-align: center;
  padding: 80rpx 48rpx;
  color: #9a9a9a;
  display: flex;
  flex-direction: column;
}
.empty-sub {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  margin-top: 16rpx;
  letter-spacing: 2rpx;
}

.service-card {
  margin: 0 48rpx 24rpx;
  background: #fff;
  border: 1rpx solid #ebe8e2;
  border-radius: 24rpx;
  padding: 32rpx;
}
.sc-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}
.sc-status {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  padding: 6rpx 20rpx;
  border-radius: 20rpx;
}
.sc-status.s1 { background: #faf6ed; color: #a88a4d; }
.sc-status.s2 { background: #f0eefa; color: #5d52b0; }
.sc-status.s3 { background: #f3f3f3; color: #9a9a9a; }
.sc-time {
  font-size: 20rpx;
  color: #9a9a9a;
  letter-spacing: 1rpx;
}
.sc-name {
  display: block;
  font-size: 26rpx;
  letter-spacing: 4rpx;
  color: #0a0a0a;
  margin-bottom: 8rpx;
  font-weight: 500;
}
.sc-teacher {
  display: block;
  font-size: 22rpx;
  color: #555;
  letter-spacing: 1rpx;
}
.sc-bar {
  margin-top: 20rpx;
  height: 4rpx;
  background: #ebe8e2;
  border-radius: 2rpx;
  overflow: hidden;
}
.sc-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #c9a96e 0%, #7b6fdf 100%);
  border-radius: 2rpx;
}

.footer {
  padding: 60rpx 48rpx 80rpx;
  text-align: center;
}
.footer-en {
  font-size: 20rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  font-style: italic;
}
</style>
