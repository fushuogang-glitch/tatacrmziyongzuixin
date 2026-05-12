<template>
  <view class="bind">
    <view class="title">绑定人脸</view>
    <view class="desc">请将正脸对准摄像头，光线充足、无遮挡。绑定成功后即可刷脸签到。</view>

    <view class="preview" @tap="shoot">
      <image v-if="preview" :src="preview" mode="aspectFill" />
      <view v-else class="placeholder">
        <text class="icon">📷</text>
        <text>点击拍照</text>
      </view>
    </view>

    <view class="btn-primary" @tap="submit" v-if="preview">提交绑定</view>
    <view class="btn-ghost" @tap="shoot">重新拍照</view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { api } from '../../../api';
import { useUserStore } from '../../../store/user';

const preview = ref('');
const base64 = ref('');

function shoot() {
  uni.chooseImage({
    count: 1, sourceType: ['camera'], sizeType: ['compressed'],
    success: (res) => {
      const path = res.tempFilePaths[0];
      preview.value = path;
      // #ifdef MP-WEIXIN
      uni.getFileSystemManager().readFile({
        filePath: path, encoding: 'base64',
        success: (r: any) => { base64.value = r.data as string; },
      });
      // #endif
      // #ifdef H5
      const reader = new FileReader();
      fetch(path).then(r => r.blob()).then(b => {
        reader.onload = () => { base64.value = String(reader.result).split(',')[1]; };
        reader.readAsDataURL(b);
      });
      // #endif
    },
  });
}

const store = useUserStore();

async function submit() {
  if (!base64.value) return uni.showToast({ title: '请先拍照', icon: 'none' });
  uni.showLoading({ title: '上传中' });
  try {
    await api.bindFace(base64.value);
    const u: any = await api.me();
    store.setUser(u);
    uni.showToast({ title: '绑定成功' });
    setTimeout(() => uni.navigateBack(), 800);
  } catch (_) {}
  finally { uni.hideLoading(); }
}
</script>

<style lang="scss" scoped>
.bind { padding: 40rpx; }
.title { font-size: 44rpx; font-weight: 700; }
.desc { color: #666; margin-top: 16rpx; font-size: 26rpx; line-height: 1.6; }
.preview {
  margin: 60rpx auto; width: 480rpx; height: 480rpx;
  border-radius: 50%;
  overflow: hidden;
  background: #f0f0f5;
  display: flex; align-items: center; justify-content: center;
  image { width: 100%; height: 100%; }
  .placeholder {
    color: #999; font-size: 28rpx;
    text-align: center;
    .icon { font-size: 100rpx; display: block; margin-bottom: 20rpx; }
  }
}
.btn-primary { margin: 0 auto 24rpx; width: 80%; }
.btn-ghost {
  text-align: center; padding: 24rpx 0;
  border: 1rpx solid #ddd; border-radius: 12rpx; color: #666;
  margin: 0 auto; width: 80%;
}
</style>
