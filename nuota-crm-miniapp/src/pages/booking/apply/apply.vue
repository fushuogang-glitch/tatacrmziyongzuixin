<template>
  <view class="apply">
    <view class="title">申请下店</view>

    <view class="form">
      <view class="row">
        <text class="label">期望日期</text>
        <picker mode="date" :value="form.preferred_date" @change="onDate">
          <view class="picker">{{ form.preferred_date || '选择日期' }}</view>
        </picker>
      </view>
      <view class="row">
        <text class="label">城市</text>
        <input v-model="form.city" placeholder="如：武汉" />
      </view>
      <view class="row">
        <text class="label">门店地址</text>
        <input v-model="form.address" placeholder="详细地址" />
      </view>
      <view class="row">
        <text class="label">时长</text>
        <picker :range="days" @change="onDays">
          <view class="picker">{{ form.duration_days }} 天</view>
        </picker>
      </view>
      <view class="row">
        <text class="label">备注</text>
        <input v-model="form.remark" placeholder="诉求 / 重点（可选）" />
      </view>
    </view>

    <view class="btn-primary" @tap="submit">提交申请</view>
  </view>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { api } from '../../../api';
import { onLoad } from '@dcloudio/uni-app';

const form = reactive<any>({
  reward_id: 0, preferred_date: '', city: '', address: '',
  duration_days: 2, remark: '',
});
const days = [1, 2, 3];

onLoad((opt: any) => { form.reward_id = Number(opt?.reward_id || 0); });

function onDate(e: any) { form.preferred_date = e.detail.value; }
function onDays(e: any) { form.duration_days = days[e.detail.value]; }

async function submit() {
  if (!form.reward_id) return uni.showToast({ title: '缺少权益', icon: 'none' });
  if (!form.preferred_date) return uni.showToast({ title: '请选日期', icon: 'none' });
  uni.showLoading({ title: '提交中' });
  try {
    await api.applyBooking(form);
    uni.showToast({ title: '已提交' });
    setTimeout(() => uni.redirectTo({ url: '/pages/booking/list/list' }), 800);
  } catch (_) {} finally { uni.hideLoading(); }
}
</script>

<style lang="scss" scoped>
.apply { padding: 40rpx; }
.title { font-size: 44rpx; font-weight: 700; margin-bottom: 40rpx; }
.form { background: #fff; border-radius: 16rpx; padding: 20rpx 32rpx;
  .row { display: flex; align-items: center; padding: 28rpx 0;
    border-bottom: 1rpx solid #eee;
    &:last-child { border-bottom: none; }
    .label { width: 160rpx; color: #666; font-size: 28rpx; }
    input, .picker { flex: 1; font-size: 30rpx; }
  }
}
.btn-primary { margin-top: 60rpx; }
</style>
