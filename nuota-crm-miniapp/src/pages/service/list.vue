<template>
  <view class="page">
    <view class="hero">
      <text class="hero-en">SERVICE LIST</text>
      <text class="hero-cn">专 案 服 务</text>
      <view class="hero-line"></view>
      <text class="hero-desc">塔塔老师团 · 年费制专案服务</text>
    </view>

    <scroll-view scroll-x class="cate-bar">
      <text :class="['cate', !category ? 'active' : '']" @tap="filter('')">全 部</text>
      <text v-for="c in categories" :key="c" :class="['cate', category === c ? 'active' : '']" @tap="filter(c)">{{ c }}</text>
    </scroll-view>

    <scroll-view scroll-y class="list">
      <view v-for="s in services" :key="s.id" class="srv-card" @tap="goDetail(s.id)">
        <view class="srv-cover" :style="coverStyle(s)">
          <text class="srv-cate">{{ s.category }}</text>
        </view>
        <view class="srv-body">
          <text class="srv-name">{{ s.name }}</text>
          <text class="srv-desc">{{ s.description }}</text>
          <view class="srv-foot">
            <view>
              <text class="srv-price-label">年费</text>
              <text class="srv-price">¥{{ formatPrice(s.annual_price) }}</text>
            </view>
            <text class="srv-duration">{{ s.duration_days }} 天 / 次</text>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../../api';

const services = ref<any[]>([]);
const categories = ['诊断', '品项', '培训', '品牌', '营销', '新店'];
const category = ref('');

async function load() {
  try {
    const r: any = await api.listServices(category.value || undefined);
    services.value = Array.isArray(r) ? r : (r?.data || []);
  } catch (e) {}
}
function filter(c: string) {
  category.value = c;
  load();
}
function goDetail(id: number) {
  uni.navigateTo({ url: `/pages/service/detail?id=${id}` });
}
function formatPrice(p: any) {
  if (!p) return '0';
  return Number(p).toLocaleString();
}
function coverStyle(s: any) {
  const colors: Record<string, string> = {
    诊断: 'linear-gradient(135deg, #c9a96e 0%, #a88a4d 100%)',
    品项: 'linear-gradient(135deg, #7b6fdf 0%, #5d52b0 100%)',
    培训: 'linear-gradient(135deg, #2a2520 0%, #0a0a0a 100%)',
    品牌: 'linear-gradient(135deg, #faf6ed 0%, #c9a96e 100%)',
    营销: 'linear-gradient(135deg, #f0eefa 0%, #7b6fdf 100%)',
    新店: 'linear-gradient(135deg, #1a1a1a 0%, #7b6fdf 100%)',
  };
  return `background: ${colors[s.category] || '#0a0a0a'}`;
}

onMounted(load);
</script>

<style lang="scss">
.page {
  background: #fff;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.hero {
  padding: 60rpx 48rpx 32rpx;
  text-align: center;
  background: linear-gradient(180deg, #fafaf8 0%, #fff 100%);
}
.hero-en {
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  font-style: italic;
}
.hero-cn {
  display: block;
  font-size: 36rpx;
  letter-spacing: 16rpx;
  color: #0a0a0a;
  margin: 12rpx 0;
  font-weight: 500;
}
.hero-line {
  width: 48rpx;
  height: 1rpx;
  background: #c9a96e;
  margin: 16rpx auto;
}
.hero-desc {
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 3rpx;
}

.cate-bar {
  white-space: nowrap;
  padding: 24rpx 48rpx;
  border-bottom: 1rpx solid #ebe8e2;
}
.cate {
  display: inline-block;
  padding: 12rpx 28rpx;
  margin-right: 16rpx;
  font-size: 24rpx;
  letter-spacing: 4rpx;
  color: #9a9a9a;
  border-radius: 28rpx;
  background: #fafaf8;
}
.cate.active {
  background: #0a0a0a;
  color: #c9a96e;
}

.list {
  flex: 1;
  padding: 32rpx 48rpx 80rpx;
}
.srv-card {
  margin-bottom: 32rpx;
  background: #fff;
  border: 1rpx solid #ebe8e2;
  border-radius: 24rpx;
  overflow: hidden;
}
.srv-cover {
  height: 200rpx;
  position: relative;
  padding: 32rpx;
  display: flex;
  align-items: flex-end;
}
.srv-cate {
  font-size: 20rpx;
  color: rgba(255,255,255,0.8);
  letter-spacing: 6rpx;
  background: rgba(0,0,0,0.3);
  padding: 6rpx 16rpx;
  border-radius: 20rpx;
}
.srv-body {
  padding: 28rpx 32rpx 32rpx;
}
.srv-name {
  display: block;
  font-size: 30rpx;
  font-weight: 500;
  color: #0a0a0a;
  letter-spacing: 4rpx;
  margin-bottom: 12rpx;
}
.srv-desc {
  display: block;
  font-size: 22rpx;
  color: #555;
  line-height: 1.6;
  letter-spacing: 1rpx;
  margin-bottom: 20rpx;
}
.srv-foot {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-top: 20rpx;
  border-top: 1rpx solid #ebe8e2;
}
.srv-price-label {
  font-size: 20rpx;
  color: #9a9a9a;
  margin-right: 12rpx;
  letter-spacing: 2rpx;
}
.srv-price {
  font-size: 34rpx;
  color: #c9a96e;
  font-weight: 500;
}
.srv-duration {
  font-size: 20rpx;
  color: #9a9a9a;
  letter-spacing: 2rpx;
}
</style>
