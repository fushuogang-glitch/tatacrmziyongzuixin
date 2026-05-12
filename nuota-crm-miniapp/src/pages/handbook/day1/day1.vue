<template>
  <view class="hb">
    <view class="title">Day1 · 破冰与诊断</view>
    <view class="tip">填写后自动保存；课程结束由老师签字确认。</view>

    <view class="card">
      <view class="q">今日对品牌最深的一个洞察：</view>
      <textarea v-model="data.insight" placeholder="请输入" />
      <view class="q">Day1 行动计划（最少 3 条）：</view>
      <textarea v-model="data.plan" placeholder="每行一条" />
      <view class="q">作业：</view>
      <textarea v-model="data.homework" placeholder="请输入" />
    </view>

    <view class="btns">
      <view class="btn-primary" @tap="save">保存</view>
      <view class="btn-ghost" @tap="next">下一天 →</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, onMounted, ref } from 'vue';
import { api } from '../../../api';

const sid = ref(0);
const data = reactive<any>({ insight: '', plan: '', homework: '' });

onMounted(async () => {
  const list: any = await api.availableSessions().catch(() => []);
  sid.value = list?.[0]?.id || 0;
  if (sid.value) {
    const h: any = await api.getHandbook(sid.value).catch(() => null);
    Object.assign(data, h?.day1_data || {});
  }
});

async function save() {
  if (!sid.value) return uni.showToast({ title: '无场次', icon: 'none' });
  uni.showLoading({ title: '保存中' });
  try {
    await api.saveHandbook(sid.value, { day1_data: { ...data } });
    uni.showToast({ title: '已保存' });
  } catch (_) {} finally { uni.hideLoading(); }
}
function next() { uni.redirectTo({ url: '/pages/handbook/day2/day2' }); }
</script>

<style lang="scss" scoped>
.hb { padding: 40rpx; }
.title { font-size: 40rpx; font-weight: 700; }
.tip { color: #999; font-size: 24rpx; margin-top: 12rpx; }
.card { margin: 32rpx 0; padding: 24rpx; background: #fff; border-radius: 16rpx;
  .q { font-size: 28rpx; color: #333; margin: 24rpx 0 12rpx; font-weight: 600; }
  textarea { width: 100%; min-height: 140rpx; background: #f7f8fc; border-radius: 12rpx; padding: 20rpx; font-size: 28rpx; box-sizing: border-box; }
}
.btns { display: flex; gap: 20rpx; }
.btn-primary, .btn-ghost { flex: 1; text-align: center; padding: 24rpx 0; border-radius: 12rpx; }
.btn-ghost { border: 1rpx solid #ddd; color: #666; }
</style>
