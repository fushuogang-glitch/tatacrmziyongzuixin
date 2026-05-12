<template>
  <view class="checkin">
    <view class="title">扫脸签到</view>

    <view class="picker-row">
      <text>选择场次</text>
      <picker :range="sessions" range-key="session_no" @change="onPick" v-if="sessions.length">
        <view class="picker">{{ curLabel }}</view>
      </picker>
      <text v-else class="empty">暂无可签到场次</text>
    </view>

    <view class="preview" @tap="shoot">
      <image v-if="preview" :src="preview" mode="aspectFill" />
      <view v-else class="placeholder"><text class="icon">📷</text><text>点击拍照</text></view>
    </view>

    <view class="btn-primary" @tap="submit" v-if="preview">开始签到</view>

    <view v-if="result" class="success">
      ✅ Day{{ result.day }} 签到成功<br/>{{ result.checkin_time }}
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { api } from '../../../api';

const sessions = ref<any[]>([]);
const selIdx = ref(0);
const preview = ref('');
const base64 = ref('');
const result = ref<any>(null);
const curLabel = computed(() => sessions.value[selIdx.value]?.session_no || '选择');

onMounted(async () => {
  try {
    const list: any = await api.availableSessions();
    sessions.value = list || [];
  } catch (_) {}
});

function onPick(e: any) { selIdx.value = e.detail.value; }

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

async function submit() {
  const sid = sessions.value[selIdx.value]?.id;
  if (!sid) return uni.showToast({ title: '请选择场次', icon: 'none' });
  if (!base64.value) return uni.showToast({ title: '请先拍照', icon: 'none' });
  uni.showLoading({ title: '识别中' });
  try {
    const r: any = await api.faceCheckin({ session_id: sid, face_base64: base64.value });
    result.value = r;
    uni.showToast({ title: r.repeat ? '今日已签到' : '签到成功' });
  } catch (_) {}
  finally { uni.hideLoading(); }
}
</script>

<style lang="scss" scoped>
.checkin { padding: 40rpx; }
.title { font-size: 44rpx; font-weight: 700; }
.picker-row {
  margin-top: 40rpx; background: #fff; border-radius: 12rpx;
  padding: 24rpx 32rpx; display: flex; justify-content: space-between; align-items: center;
  font-size: 28rpx;
  .picker { color: #8c5cff; font-weight: 600; }
  .empty { color: #999; font-size: 24rpx; }
}
.preview {
  margin: 60rpx auto; width: 480rpx; height: 480rpx; border-radius: 24rpx;
  overflow: hidden; background: #f0f0f5;
  display: flex; align-items: center; justify-content: center;
  image { width: 100%; height: 100%; }
  .placeholder { color: #999; text-align: center;
    .icon { font-size: 100rpx; display: block; margin-bottom: 20rpx; }
  }
}
.btn-primary { width: 80%; margin: 0 auto; }
.success {
  margin: 40rpx auto 0; text-align: center; color: #07c160; font-size: 32rpx;
  font-weight: 600; line-height: 1.8;
}
</style>
