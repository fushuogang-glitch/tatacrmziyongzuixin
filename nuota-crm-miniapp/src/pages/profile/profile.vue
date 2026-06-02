<template>
  <view class="profile">
    <view class="header">
      <view class="name">{{ user?.name || '——' }}</view>
      <view class="phone">{{ user?.phone }}</view>
    </view>

    <view class="card">
      <view class="row"><text>学员编号</text><text>{{ user?.member_no || '-' }}</text></view>
      <view class="row"><text>会员类型</text><text>{{ typeLabel }}</text></view>
      <view class="row"><text>入学日期</text><text>{{ user?.enroll_date || '-' }}</text></view>
      <view class="row"><text>到期日期</text><text>{{ user?.expire_date || '-' }}</text></view>
      <view class="row"><text>推荐码</text><text class="code">{{ user?.referral_code || '-' }}</text></view>
      <!-- 人脸绑定暂时隐藏
      <view class="row"><text>人脸绑定</text><text :class="user?.face_bound ? 'ok':'no'">{{ user?.face_bound ? '已绑定':'未绑定' }}</text></view>
      -->
    </view>

    <view class="btns">
      <!-- 人脸绑定暂时隐藏
      <view class="btn-primary" @tap="bindFace" v-if="!user?.face_bound">去绑定人脸</view>
      -->
      <view class="btn-ghost" @tap="logout">退出登录</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useUserStore } from '../../store/user';
import { api } from '../../api';

const store = useUserStore();
const user = computed(() => store.user);
const typeLabel = computed(() => {
  const t = store.user?.member_type;
  return t === 'annual' ? '年费' : t === 'vip' ? 'VIP' : '试听';
});

function bindFace() { uni.navigateTo({ url: '/pages/face/bind/bind' }); }
function logout() {
  store.logout();
  uni.reLaunch({ url: '/pages/login/login' });
}

onMounted(async () => {
  try {
    const u: any = await api.me();
    store.setUser(u);
  } catch (_) {}
});
</script>

<style lang="scss" scoped>
.profile { padding-bottom: 60rpx; }
.header {
  background: linear-gradient(135deg, #1a1a2e 0%, #8c5cff 100%);
  padding: 80rpx 40rpx; color: #fff;
  .name { font-size: 44rpx; font-weight: 700; }
  .phone { margin-top: 12rpx; font-size: 28rpx; opacity: 0.8; }
}
.card .row {
  display: flex; justify-content: space-between;
  padding: 28rpx 0; font-size: 28rpx;
  border-bottom: 1rpx solid #eee;
  &:last-child { border-bottom: none; }
  .ok { color: #07c160; } .no { color: #f56c6c; }
  .code { font-family: monospace; color: #8c5cff; font-weight: 700; }
}
.btns { padding: 40rpx; }
.btn-primary { margin-bottom: 20rpx; }
.btn-ghost {
  text-align: center; padding: 24rpx 0;
  border: 1rpx solid #ddd; border-radius: 12rpx; color: #666;
}
</style>
