<template>
  <view class="page">
    <view class="head">
      <text class="brand-mark">TATA CONSULTING<text class="reg">®</text></text>
      <text class="brand-tag">会 员 服 务 协 议</text>
      <text class="meta">版本 {{ version }} · 生效日期 {{ effectiveDate }}</text>
    </view>

    <scroll-view scroll-y class="body">
      <text class="content">{{ content }}</text>

      <view class="footer-mark">
        <view class="line"></view>
        <text class="mark">— 上海嘉塔诺塔管理咨询有限公司 —</text>
        <view class="line"></view>
      </view>
    </scroll-view>

    <view class="bottom">
      <view class="checker" @tap="agreed = !agreed">
        <view :class="['ck-box', agreed ? 'on' : '']">{{ agreed ? '✓' : '' }}</view>
        <text class="ck-text">我已仔细阅读并同意以上全部条款</text>
      </view>
      <view class="btn-row">
        <button class="btn-refuse" @tap="refuse">不同意</button>
        <button :class="['btn-agree', agreed ? '' : 'disabled']" :disabled="!agreed || loading" @tap="agree">{{ loading ? '签约中...' : '同意签约' }}</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../../api';

const version = ref('v1.0');
const effectiveDate = ref('2026-05-13');
const content = ref('');
const agreed = ref(false);
const loading = ref(false);

async function loadAgreement() {
  try {
    const r: any = await api.getAgreement();
    if (r?.data) {
      version.value = r.data.version;
      effectiveDate.value = r.data.effective_date;
      content.value = r.data.content;
    }
  } catch (e) {
    content.value = '协议加载失败，请退出重试。';
  }
}

async function agree() {
  if (!agreed.value) return;
  loading.value = true;
  try {
    const member = uni.getStorageSync('member');
    if (!member?.id) {
      uni.showToast({ title: '请先登录', icon: 'none' });
      uni.redirectTo({ url: '/pages/login/login' });
      return;
    }
    await api.signAgreement({ member_id: member.id });
    uni.showToast({ title: '签约成功', icon: 'success' });
    setTimeout(() => uni.switchTab({ url: '/pages/tata/index' }), 600);
  } catch (e: any) {
    uni.showToast({ title: e?.msg || '签约失败', icon: 'none' });
  } finally {
    loading.value = false;
  }
}

function refuse() {
  uni.showModal({
    title: '退出小程序',
    content: '不同意协议将无法使用本小程序，是否退出？',
    confirmText: '退出',
    confirmColor: '#0a0a0a',
    success: (res) => {
      if (res.confirm) {
        // @ts-ignore
        uni.exitMiniProgram && uni.exitMiniProgram();
      }
    }
  });
}

onMounted(() => {
  loadAgreement();
});
</script>

<style lang="scss">
.page {
  background: #fff;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.head {
  padding: 80rpx 48rpx 32rpx;
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
}
.brand-tag {
  display: block;
  font-size: 26rpx;
  color: #0a0a0a;
  margin: 16rpx 0 8rpx;
  letter-spacing: 8rpx;
  font-weight: 500;
}
.meta {
  display: block;
  font-size: 20rpx;
  color: #9a9a9a;
  letter-spacing: 3rpx;
  font-style: italic;
}

.body {
  flex: 1;
  padding: 32rpx 48rpx 280rpx;
}
.content {
  display: block;
  font-size: 24rpx;
  line-height: 1.9;
  color: #333;
  letter-spacing: 1rpx;
  white-space: pre-wrap;
}
.footer-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 60rpx;
  gap: 16rpx;
}
.footer-mark .line {
  width: 48rpx;
  height: 1rpx;
  background: #c9a96e;
}
.mark {
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 4rpx;
  font-weight: 500;
}

.bottom {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  background: #fff;
  padding: 32rpx 48rpx 60rpx;
  border-top: 1rpx solid #ebe8e2;
}
.checker {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 24rpx;
}
.ck-box {
  width: 32rpx;
  height: 32rpx;
  border-radius: 6rpx;
  border: 2rpx solid #7b6fdf;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  color: transparent;
}
.ck-box.on {
  background: #7b6fdf;
  color: #fff;
}
.ck-text {
  font-size: 24rpx;
  color: #333;
  letter-spacing: 1rpx;
}
.btn-row {
  display: flex;
  gap: 20rpx;
}
.btn-refuse, .btn-agree {
  flex: 1;
  padding: 24rpx 0;
  border-radius: 48rpx;
  font-size: 28rpx;
  letter-spacing: 4rpx;
  border: none;
  line-height: 1;
}
.btn-refuse {
  background: #f5f5f5;
  color: #666;
}
.btn-agree {
  background: #0a0a0a;
  color: #c9a96e;
  font-weight: 500;
}
.btn-agree.disabled {
  opacity: 0.4;
}
</style>
