<template>
  <view class="reg">
    <view class="title">完善信息</view>
    <view class="form">
      <view class="row">
        <text class="label">姓名</text>
        <input v-model="form.name" placeholder="请输入姓名" />
      </view>
      <view class="row">
        <text class="label">手机号</text>
        <input v-model="form.phone" type="number" maxlength="11" placeholder="11 位手机号" />
      </view>
      <view class="row">
        <text class="label">企业</text>
        <input v-model="form.enterprise_name" placeholder="企业名称（可选）" />
      </view>
      <view class="row">
        <text class="label">城市</text>
        <input v-model="form.city" placeholder="所在城市（可选）" />
      </view>
      <view class="row">
        <text class="label">角色</text>
        <picker :range="roles" range-key="label" @change="onRole">
          <view class="picker">{{ roleLabel }}</view>
        </picker>
      </view>
      <view class="row">
        <text class="label">推荐码</text>
        <input v-model="form.referral_code" placeholder="如有推荐人请填写" />
      </view>
    </view>

    <view class="btn-primary" @tap="submit">提交并绑定人脸</view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue';
import { api } from '../../api';
import { useUserStore } from '../../store/user';

const store = useUserStore();

const roles = [
  { label: '老板', value: 'boss' },
  { label: '店长', value: 'manager' },
  { label: '顾问', value: 'consultant' },
];

const form = reactive<any>({
  name: '', phone: '',
  enterprise_name: '', city: '',
  role: 'boss',
  member_type: 'trial',
  referral_code: '',
});

const roleLabel = computed(() => roles.find(r => r.value === form.role)?.label || '请选择');

function onRole(e: any) {
  form.role = roles[e.detail.value].value;
}

async function submit() {
  if (!form.name || !/^1\d{10}$/.test(form.phone)) {
    return uni.showToast({ title: '请填写完整信息', icon: 'none' });
  }
  uni.showLoading({ title: '提交中' });
  try {
    const res: any = await api.register({
      name: form.name, phone: form.phone,
      enterprise_name: form.enterprise_name, city: form.city,
      role: form.role, member_type: form.member_type,
      referral_code: form.referral_code || undefined,
    });
    store.setToken(res.token);
    store.setUser(res.user);
    uni.redirectTo({ url: '/pages/face/bind/bind' });
  } catch (_) { /* 已 toast */ }
  finally { uni.hideLoading(); }
}
</script>

<style lang="scss" scoped>
.reg { padding: 40rpx; }
.title { font-size: 44rpx; font-weight: 700; margin-bottom: 40rpx; }
.form {
  background: #fff; border-radius: 16rpx; padding: 20rpx 32rpx;
  .row {
    display: flex; align-items: center;
    padding: 28rpx 0; border-bottom: 1rpx solid #eee;
    &:last-child { border-bottom: none; }
    .label { width: 140rpx; color: #666; font-size: 28rpx; }
    input, .picker { flex: 1; font-size: 30rpx; }
    .picker { color: #333; }
  }
}
.btn-primary { margin-top: 60rpx; }
</style>
