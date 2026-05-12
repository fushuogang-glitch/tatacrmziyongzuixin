<template>
  <view class="login">
    <view class="logo">诺控·塔塔</view>
    <view class="slogan">学员管理系统</view>

    <button class="btn-wx" open-type="getUserInfo" @tap="handleLogin">
      <text>📱  微信一键登录</text>
    </button>

    <view class="tip">首次进入需填写姓名、手机号，绑定人脸后即可扫脸签到。</view>
  </view>
</template>

<script setup lang="ts">
import { api } from '../../api';
import { useUserStore } from '../../store/user';

const store = useUserStore();

async function handleLogin() {
  uni.showLoading({ title: '登录中' });
  try {
    const { code } = await new Promise<UniApp.LoginRes>((resolve, reject) => {
      uni.login({ provider: 'weixin', success: resolve, fail: reject });
    });
    const res: any = await api.wxLogin(code);
    store.setToken(res.token);
    if (res.need_register) {
      uni.reLaunch({ url: '/pages/register/register' });
    } else {
      store.setUser(res.user);
      uni.reLaunch({ url: '/pages/index/index' });
    }
  } catch (e) {
    uni.showToast({ title: '登录失败', icon: 'none' });
  } finally {
    uni.hideLoading();
  }
}
</script>

<style lang="scss" scoped>
.login {
  padding: 200rpx 60rpx;
  text-align: center;
}
.logo {
  font-size: 80rpx; font-weight: 800;
  background: linear-gradient(135deg, #1a1a2e 0%, #8c5cff 100%);
  -webkit-background-clip: text;
  color: transparent;
}
.slogan { margin-top: 20rpx; color: #666; font-size: 30rpx; }
.btn-wx {
  margin-top: 160rpx;
  background: #07c160; color: #fff;
  border-radius: 50rpx; padding: 24rpx 0;
  font-size: 32rpx;
}
.tip { margin-top: 40rpx; color: #999; font-size: 24rpx; }
</style>
