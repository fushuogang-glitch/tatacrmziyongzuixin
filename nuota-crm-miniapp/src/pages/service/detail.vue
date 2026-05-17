<template>
  <view class="page">
    <view class="hero" :style="coverStyle">
      <text class="hero-cate">{{ service.category }}</text>
      <text class="hero-name">{{ service.name }}</text>
      <text class="hero-en">{{ service.code }}</text>
    </view>

    <view class="meta-row">
      <view class="meta-item">
        <text class="meta-label">YEAR</text>
        <text class="meta-num">¥{{ formatPrice(service.annual_price) }}</text>
        <text class="meta-sub">年费套餐</text>
      </view>
      <view class="meta-divider"></view>
      <view class="meta-item">
        <text class="meta-label">DURATION</text>
        <text class="meta-num">{{ service.duration_days }} 天</text>
        <text class="meta-sub">单次时长</text>
      </view>
    </view>

    <view class="section">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">服 务 说 明</text>
        <text class="sec-en">Description</text>
      </view>
      <text class="desc">{{ service.description }}</text>
    </view>

    <view class="section">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">服 务 流 程</text>
        <text class="sec-en">Workflow</text>
      </view>
      <view class="flow">
        <view v-for="(s, i) in flow" :key="i" class="flow-step">
          <view class="flow-dot">{{ i + 1 }}</view>
          <view class="flow-body">
            <text class="flow-title">{{ s.title }}</text>
            <text class="flow-desc">{{ s.desc }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="bottom">
      <button class="btn" @tap="appoint">立即预约</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api';

const service = ref<any>({});
const id = ref(0);

const flow = [
  { title: '提交预约', desc: '选择日期 · 服务老师 · 门店地址' },
  { title: '老师确认', desc: '24小时内确认档期与方案' },
  { title: '下店执案', desc: '诊断 · 方案 · 执行 · 复盘' },
  { title: '满意度评价', desc: '完成后提交评价反馈' },
];

const coverStyle = computed(() => {
  const colors: Record<string, string> = {
    诊断: 'linear-gradient(135deg, #c9a96e 0%, #a88a4d 100%)',
    品项: 'linear-gradient(135deg, #7b6fdf 0%, #5d52b0 100%)',
    培训: 'linear-gradient(135deg, #2a2520 0%, #0a0a0a 100%)',
    品牌: 'linear-gradient(135deg, #faf6ed 0%, #c9a96e 100%)',
    营销: 'linear-gradient(135deg, #f0eefa 0%, #7b6fdf 100%)',
    新店: 'linear-gradient(135deg, #1a1a1a 0%, #7b6fdf 100%)',
  };
  return `background: ${colors[service.value.category] || '#0a0a0a'}`;
});

function formatPrice(p: any) {
  if (!p) return '0';
  return Number(p).toLocaleString();
}
function appoint() {
  uni.navigateTo({ url: `/pages/service/appoint?service_id=${id.value}` });
}

onMounted(() => {
  const opts = (uni.getLaunchOptionsSync && uni.getLaunchOptionsSync()) || {};
  // @ts-ignore
  const pages = getCurrentPages();
  // @ts-ignore
  const query = pages[pages.length - 1]?.options || {};
  id.value = Number(query.id);
  if (id.value) {
    api.getService(id.value).then((r: any) => {
      service.value = r || {};
    });
  }
});
</script>

<style lang="scss">
.page { background: #fff; min-height: 100vh; padding-bottom: 160rpx; }
.hero {
  height: 360rpx;
  padding: 60rpx 48rpx 32rpx;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  color: #fff;
}
.hero-cate {
  font-size: 22rpx;
  letter-spacing: 6rpx;
  background: rgba(0,0,0,0.3);
  padding: 8rpx 20rpx;
  border-radius: 24rpx;
  align-self: flex-start;
  margin-bottom: 16rpx;
}
.hero-name {
  display: block;
  font-size: 44rpx;
  letter-spacing: 8rpx;
  font-weight: 500;
  margin-bottom: 8rpx;
}
.hero-en {
  display: block;
  font-size: 22rpx;
  opacity: 0.7;
  letter-spacing: 4rpx;
  font-style: italic;
}

.meta-row {
  display: flex;
  align-items: center;
  padding: 32rpx 48rpx;
  border-bottom: 1rpx solid #ebe8e2;
}
.meta-item { flex: 1; text-align: center; }
.meta-divider {
  width: 1rpx;
  height: 80rpx;
  background: #ebe8e2;
}
.meta-label {
  display: block;
  font-size: 20rpx;
  color: #c9a96e;
  letter-spacing: 4rpx;
  font-style: italic;
}
.meta-num {
  display: block;
  font-size: 40rpx;
  color: #0a0a0a;
  font-weight: 500;
  margin: 8rpx 0;
}
.meta-sub {
  display: block;
  font-size: 20rpx;
  color: #9a9a9a;
  letter-spacing: 2rpx;
}

.section {
  padding: 40rpx 48rpx 24rpx;
}
.sec-head {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 24rpx;
}
.sec-line { width: 48rpx; height: 1rpx; background: #c9a96e; }
.sec-title { font-size: 26rpx; letter-spacing: 12rpx; color: #0a0a0a; flex: 1; font-weight: 500; }
.sec-en { font-size: 22rpx; color: #9a9a9a; font-style: italic; }

.desc {
  font-size: 24rpx;
  line-height: 1.9;
  color: #333;
  letter-spacing: 1rpx;
}

.flow { padding: 16rpx 0; }
.flow-step {
  display: flex;
  gap: 24rpx;
  margin-bottom: 32rpx;
}
.flow-dot {
  width: 48rpx; height: 48rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #c9a96e 0%, #a88a4d 100%);
  color: #fff;
  font-size: 22rpx;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.flow-body { flex: 1; padding-top: 6rpx; }
.flow-title {
  display: block;
  font-size: 26rpx;
  color: #0a0a0a;
  font-weight: 500;
  letter-spacing: 3rpx;
  margin-bottom: 4rpx;
}
.flow-desc {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 1rpx;
}

.bottom {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  background: #fff;
  padding: 24rpx 48rpx 60rpx;
  border-top: 1rpx solid #ebe8e2;
}
.btn {
  background: #0a0a0a;
  color: #c9a96e;
  border: none;
  border-radius: 48rpx;
  padding: 24rpx;
  font-size: 30rpx;
  letter-spacing: 8rpx;
  font-weight: 500;
}
</style>
