<template>
  <view class="page">
    <view class="header">
      <text class="header-cn">人 脸 认 证</text>
      <text class="header-sub">{{ staffName }}</text>
    </view>

    <view class="content">
      <view v-if="!captured" class="camera-area">
        <camera device-position="front" flash="off" class="camera" />
        <text class="camera-tip">请将面部对准框内</text>
      </view>

      <view v-if="captured" class="result">
        <image :src="photoPath" class="preview" mode="aspectFill" />
        <text class="result-text">{{ uploading ? '正在认证...' : (success ? '认证成功 ✓' : '请拍照认证') }}</text>
      </view>

      <view class="btn-row">
        <text v-if="!captured" class="btn-capture" @tap="takePhoto">拍 照</text>
        <template v-else>
          <text class="btn-retry" @tap="retry">重 拍</text>
          <text v-if="!success" class="btn-submit" @tap="submit">确 认 提 交</text>
        </template>
      </view>

      <view v-if="success" class="success-card">
        <text class="success-icon">✓</text>
        <text class="success-text">人脸认证已完成</text>
        <text class="success-sub" @tap="goBack">返回学员列表 →</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../../api';

const staffId = ref(0);
const staffName = ref('');
const captured = ref(false);
const photoPath = ref('');
const uploading = ref(false);
const success = ref(false);

onMounted(() => {
  const pages = getCurrentPages();
  const page: any = pages[pages.length - 1];
  const options = page?.options || {};
  staffId.value = Number(options.id) || 0;
  staffName.value = decodeURIComponent(options.name || '');
});

function takePhoto() {
  const ctx = uni.createCameraContext();
  ctx.takePhoto({
    quality: 'high',
    success: (res: any) => {
      photoPath.value = res.tempImagePath;
      captured.value = true;
    },
    fail: () => {
      uni.showToast({ title: '拍照失败', icon: 'none' });
    }
  });
}

function retry() {
  captured.value = false;
  photoPath.value = '';
  success.value = false;
}

async function submit() {
  if (!photoPath.value || !staffId.value) return;
  uploading.value = true;
  try {
    // 读取图片为base64
    const fs = uni.getFileSystemManager();
    const base64 = fs.readFileSync(photoPath.value, 'base64') as string;
    await api.staffBindFace(staffId.value, base64);
    success.value = true;
    uni.showToast({ title: '认证成功' });
  } catch (e) {
    uni.showToast({ title: '认证失败', icon: 'none' });
  } finally {
    uploading.value = false;
  }
}

function goBack() {
  uni.navigateBack();
}
</script>

<style lang="scss">
.page {
  background: #fff;
  min-height: 100vh;
}
.header {
  background: linear-gradient(135deg, #0a0a0a, #2a2520);
  padding: 80rpx 48rpx 48rpx;
  text-align: center;
}
.header-cn {
  display: block;
  font-size: 36rpx;
  color: #fff;
  letter-spacing: 12rpx;
  font-weight: 500;
  margin-bottom: 16rpx;
}
.header-sub {
  display: block;
  font-size: 24rpx;
  color: #c9a96e;
  letter-spacing: 4rpx;
}

.content {
  padding: 48rpx;
}
.camera-area {
  position: relative;
  border-radius: 24rpx;
  overflow: hidden;
  margin-bottom: 40rpx;
}
.camera {
  width: 100%;
  height: 600rpx;
}
.camera-tip {
  position: absolute;
  bottom: 24rpx;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 24rpx;
  color: rgba(255,255,255,0.8);
  letter-spacing: 4rpx;
}

.preview {
  width: 100%;
  height: 600rpx;
  border-radius: 24rpx;
  margin-bottom: 24rpx;
}
.result {
  margin-bottom: 40rpx;
}
.result-text {
  display: block;
  text-align: center;
  font-size: 26rpx;
  color: #555;
  letter-spacing: 3rpx;
}

.btn-row {
  display: flex;
  gap: 24rpx;
  justify-content: center;
}
.btn-capture, .btn-submit {
  background: linear-gradient(135deg, #0a0a0a, #2a2520);
  border-radius: 48rpx;
  padding: 24rpx 64rpx;
  font-size: 28rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  font-weight: 500;
}
.btn-retry {
  border: 1rpx solid #ebe8e2;
  border-radius: 48rpx;
  padding: 24rpx 48rpx;
  font-size: 28rpx;
  color: #555;
  letter-spacing: 4rpx;
}

.success-card {
  margin-top: 60rpx;
  text-align: center;
  background: linear-gradient(135deg, #f0faf0, #e8f5e8);
  border-radius: 24rpx;
  padding: 48rpx;
}
.success-icon {
  display: block;
  font-size: 64rpx;
  color: #4caf50;
  margin-bottom: 16rpx;
}
.success-text {
  display: block;
  font-size: 28rpx;
  color: #0a0a0a;
  letter-spacing: 4rpx;
  margin-bottom: 16rpx;
}
.success-sub {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 2rpx;
}
</style>
