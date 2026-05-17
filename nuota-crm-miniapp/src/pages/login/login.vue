<template>
  <view class="page">
    <!-- 顶部留白 + 品牌 -->
    <view class="brand-area">
      <view class="brand-logo">
        <text class="logo-t">T</text>
      </view>
      <text class="brand-name">TATA CONSULTING<text class="reg">®</text></text>
      <text class="brand-slogan">塔 塔 咨 询 · 新 美 业 战 略 伙 伴</text>
    </view>

    <!-- 欢迎语 -->
    <view class="welcome">
      <text class="welcome-en">WELCOME</text>
      <view class="welcome-line"></view>
      <text class="welcome-cn">欢 迎 加 入 塔 塔 会 员 体 系</text>
      <text class="welcome-desc">专案服务 · 课程培训 · 推荐收益 · 专属权益</text>
    </view>

    <!-- 登录按钮 -->
    <view class="login-area">
      <button class="btn-login" open-type="getUserInfo" @tap="handleLogin">
        <text class="btn-icon">📱</text>
        <text class="btn-text">手 机 号 快 捷 登 录</text>
      </button>

      <text class="login-tip">首次登录需完善个人信息</text>
    </view>

    <!-- 底部 -->
    <view class="footer">
      <text class="footer-en">— TATA CONSULTING® —</text>
      <text class="footer-cn">上海嘉塔诺塔管理咨询有限公司</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { api } from '../../api';
import { useUserStore } from '../../store/user';

const store = useUserStore();

async function handleLogin() {
  uni.showLoading({ title: '登录中...' });
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
      uni.setStorageSync('member', res.user);
      uni.reLaunch({ url: '/pages/tata/index' });
    }
  } catch (e) {
    uni.showToast({ title: '登录失败，请重试', icon: 'none' });
  } finally {
    uni.hideLoading();
  }
}
</script>

<style lang="scss">
.page {
  background: #fff;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, "PingFang SC", "Noto Serif SC", sans-serif;
}

/* 品牌区域 */
.brand-area {
  padding: 160rpx 48rpx 48rpx;
  text-align: center;
}
.brand-logo {
  width: 120rpx;
  height: 120rpx;
  background: linear-gradient(135deg, #0a0a0a 0%, #2a2520 100%);
  border-radius: 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 40rpx;
}
.logo-t {
  color: #c9a96e;
  font-size: 56rpx;
  font-weight: 600;
  letter-spacing: 0;
}
.brand-name {
  display: block;
  font-size: 36rpx;
  letter-spacing: 8rpx;
  color: #0a0a0a;
  font-weight: 500;
}
.brand-name .reg {
  font-size: 18rpx;
  color: #c9a96e;
  vertical-align: super;
  margin-left: 4rpx;
  letter-spacing: 0;
}
.brand-slogan {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  margin-top: 16rpx;
  letter-spacing: 6rpx;
}

/* 欢迎区域 */
.welcome {
  padding: 64rpx 48rpx 48rpx;
  text-align: center;
}
.welcome-en {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 12rpx;
  font-style: italic;
  margin-bottom: 20rpx;
}
.welcome-line {
  width: 64rpx;
  height: 1rpx;
  background: #c9a96e;
  margin: 0 auto 20rpx;
}
.welcome-cn {
  display: block;
  font-size: 30rpx;
  letter-spacing: 8rpx;
  color: #0a0a0a;
  font-weight: 500;
  margin-bottom: 16rpx;
}
.welcome-desc {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 3rpx;
  line-height: 1.8;
}

/* 登录按钮区域 */
.login-area {
  padding: 48rpx;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.btn-login {
  width: 100%;
  background: linear-gradient(135deg, #0a0a0a 0%, #2a2520 100%);
  color: #c9a96e;
  border: none;
  border-radius: 48rpx;
  padding: 28rpx 0;
  font-size: 30rpx;
  letter-spacing: 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  box-shadow: 0 8rpx 32rpx rgba(10, 10, 10, 0.15);
}
.btn-login::after {
  border: none;
}
.btn-icon {
  font-size: 36rpx;
}
.btn-text {
  font-size: 30rpx;
  letter-spacing: 8rpx;
}
.login-tip {
  display: block;
  margin-top: 24rpx;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 2rpx;
}

/* 底部 */
.footer {
  padding: 48rpx 48rpx 80rpx;
  text-align: center;
}
.footer-en {
  display: block;
  font-size: 20rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  margin-bottom: 12rpx;
  font-style: italic;
}
.footer-cn {
  display: block;
  font-size: 20rpx;
  color: #9a9a9a;
  letter-spacing: 4rpx;
}
</style>
