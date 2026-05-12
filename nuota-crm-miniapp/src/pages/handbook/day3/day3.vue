<template>
  <view class="hb">
    <view class="title">Day3 · 落地与复盘</view>
    <view class="card">
      <view class="q">一句话带走：</view>
      <textarea v-model="data.takeaway" placeholder="请输入" />
      <view class="q">30 天 SMART 行动计划：</view>
      <textarea v-model="data.plan30" placeholder="请输入" />
      <view class="q">需要诺控·塔塔下店支持的项目：</view>
      <textarea v-model="data.support" placeholder="请输入" />
    </view>
    <view class="btn-primary" @tap="save">完成并保存</view>
  </view>
</template>

<script setup lang="ts">
import { reactive, onMounted, ref } from 'vue';
import { api } from '../../../api';

const sid = ref(0);
const data = reactive<any>({ takeaway: '', plan30: '', support: '' });

onMounted(async () => {
  const list: any = await api.availableSessions().catch(() => []);
  sid.value = list?.[0]?.id || 0;
  if (sid.value) {
    const h: any = await api.getHandbook(sid.value).catch(() => null);
    Object.assign(data, h?.day3_data || {});
  }
});

async function save() {
  if (!sid.value) return uni.showToast({ title: '无场次', icon: 'none' });
  uni.showLoading({ title: '保存中' });
  try {
    await api.saveHandbook(sid.value, { day3_data: { ...data } });
    uni.showToast({ title: '手册完成' });
  } catch (_) {} finally { uni.hideLoading(); }
}
</script>

<style lang="scss" scoped>
.hb { padding: 40rpx; }
.title { font-size: 40rpx; font-weight: 700; }
.card { margin: 32rpx 0; padding: 24rpx; background: #fff; border-radius: 16rpx;
  .q { font-size: 28rpx; color: #333; margin: 24rpx 0 12rpx; font-weight: 600; }
  textarea { width: 100%; min-height: 140rpx; background: #f7f8fc; border-radius: 12rpx; padding: 20rpx; font-size: 28rpx; box-sizing: border-box; }
}
.btn-primary { margin-top: 40rpx; }
</style>
