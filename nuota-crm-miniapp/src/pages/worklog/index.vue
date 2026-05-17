<template>
  <view class="page">
    <view class="header">
      <text class="header-title">执 案 日 志</text>
      <text class="header-sub">{{ order.order_no }}</text>
    </view>

    <scroll-view scroll-y class="scroll">
      <!-- 工单摘要 -->
      <view class="order-card">
        <view class="oc-row">
          <text class="oc-label">服务项目</text>
          <text class="oc-val">{{ order.service_name || '专案服务' }}</text>
        </view>
        <view class="oc-row">
          <text class="oc-label">客户</text>
          <text class="oc-val">{{ order.member_name || '—' }}</text>
        </view>
        <view class="oc-row">
          <text class="oc-label">门店</text>
          <text class="oc-val">{{ order.store_name || '—' }}</text>
        </view>
        <view class="oc-row last">
          <text class="oc-label">预约时间</text>
          <text class="oc-val">{{ order.appoint_date }} {{ order.appoint_time }}</text>
        </view>
      </view>

      <!-- 执行阶段 -->
      <view class="section-block">
        <text class="block-title">执 行 阶 段</text>
        <view class="stage-tabs">
          <view v-for="s in stages" :key="s.value"
            :class="['stage-tab', { active: currentStage === s.value }]"
            @tap="currentStage = s.value">
            <text class="st-text">{{ s.label }}</text>
          </view>
        </view>
      </view>

      <!-- 执行进度 -->
      <view class="section-block">
        <view class="prog-header">
          <text class="block-title">执 行 进 度</text>
          <text class="prog-num">{{ progress }}%</text>
        </view>
        <view class="prog-bar-wrap">
          <view class="prog-bar">
            <view class="prog-fill" :style="{ width: progress + '%' }"></view>
          </view>
        </view>
        <view class="prog-btns">
          <view v-for="p in [0,25,50,75,100]" :key="p"
            :class="['prog-btn', { active: progress === p }]"
            @tap="progress = p">{{ p }}%</view>
        </view>
      </view>

      <!-- 今日工作内容 -->
      <view class="section-block">
        <text class="block-title">今 日 工 作 内 容</text>
        <textarea class="log-textarea" v-model="content"
          placeholder="请详细描述今日执案内容：&#10;· 与谁沟通了什么&#10;· 发现了哪些问题&#10;· 采取了哪些行动&#10;· 客户反应如何"
          maxlength="2000" />
        <text class="char-count">{{ content.length }}/2000</text>
      </view>

      <!-- 发现问题 -->
      <view class="section-block">
        <text class="block-title">发 现 问 题</text>
        <textarea class="log-textarea small" v-model="issues"
          placeholder="记录门店现存问题（选填）" maxlength="500" />
      </view>

      <!-- 下一步计划 -->
      <view class="section-block">
        <text class="block-title">下 一 步 计 划</text>
        <textarea class="log-textarea small" v-model="nextPlan"
          placeholder="下次执案/跟进计划（选填）" maxlength="500" />
      </view>

      <!-- 照片上传 -->
      <view class="section-block">
        <view class="photo-header">
          <text class="block-title">现 场 照 片</text>
          <text class="photo-count">{{ photos.length }}/9</text>
        </view>
        <view class="photo-grid">
          <view v-for="(p, i) in photos" :key="i" class="photo-item" @longpress="removePhoto(i)">
            <image :src="p" mode="aspectFill" class="photo-img" />
            <view class="photo-del" @tap.stop="removePhoto(i)">✕</view>
          </view>
          <view v-if="photos.length < 9" class="photo-add" @tap="addPhoto">
            <text class="pa-icon">+</text>
            <text class="pa-text">添加照片</text>
          </view>
        </view>
      </view>

      <!-- 客户签字确认（可选） -->
      <view class="section-block">
        <view class="confirm-row">
          <text class="block-title">客 户 已 确 认</text>
          <view :class="['toggle', { on: clientConfirmed }]" @tap="clientConfirmed = !clientConfirmed">
            <view class="toggle-ball"></view>
          </view>
        </view>
        <text class="confirm-tip">开启后表示客户已现场确认本次服务内容</text>
      </view>

      <view style="height: 160rpx;"></view>
    </scroll-view>

    <!-- 底部操作 -->
    <view class="bottom-bar">
      <button class="btn-save" @tap="saveDraft" :disabled="saving">暂存草稿</button>
      <button class="btn-submit" @tap="submit" :disabled="saving || !content">
        {{ saving ? '提交中...' : '提交日志' }}
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../../api';

const order = ref<any>({});
const orderId = ref(0);
const saving = ref(false);
const currentStage = ref('diagnosis');
const progress = ref(0);
const content = ref('');
const issues = ref('');
const nextPlan = ref('');
const photos = ref<string[]>([]);
const clientConfirmed = ref(false);

const stages = [
  { value: 'diagnosis', label: '诊断' },
  { value: 'plan', label: '方案' },
  { value: 'execute', label: '执行' },
  { value: 'review', label: '复盘' },
];

function addPhoto() {
  uni.chooseImage({
    count: 9 - photos.value.length,
    sizeType: ['compressed'],
    sourceType: ['camera', 'album'],
    success: (res) => {
      photos.value = [...photos.value, ...res.tempFilePaths].slice(0, 9);
    },
  });
}

function removePhoto(i: number) {
  uni.showModal({
    title: '删除照片',
    content: '确认删除这张照片？',
    success: (r) => { if (r.confirm) photos.value.splice(i, 1); },
  });
}

async function saveDraft() {
  saving.value = true;
  try {
    await submitLog('draft');
    uni.showToast({ title: '已暂存', icon: 'success' });
  } finally { saving.value = false; }
}

async function submit() {
  if (!content.value.trim()) {
    uni.showToast({ title: '请填写工作内容', icon: 'none' });
    return;
  }
  uni.showModal({
    title: '确认提交',
    content: `提交后将通知客户，当前进度 ${progress.value}%，是否确认？`,
    success: async (r) => {
      if (!r.confirm) return;
      saving.value = true;
      try {
        await submitLog('submitted');
        uni.showToast({ title: '日志已提交', icon: 'success' });
        setTimeout(() => uni.navigateBack(), 1200);
      } catch (e: any) {
        uni.showToast({ title: e?.msg || '提交失败', icon: 'none' });
      } finally { saving.value = false; }
    },
  });
}

async function submitLog(status: string) {
  const member = uni.getStorageSync('member');
  await uni.request({
    url: `${(api as any).baseURL || 'https://api.nuotaai.com'}/admin/services/orders/${orderId.value}/work-logs`,
    method: 'POST',
    header: { Authorization: `Bearer ${uni.getStorageSync('token')}` },
    data: {
      content: content.value,
      issues: issues.value,
      next_plan: nextPlan.value,
      stage: currentStage.value,
      progress: progress.value,
      photos: photos.value,
      client_confirmed: clientConfirmed.value,
      status,
    },
  });
  // 同步更新工单进度
  await uni.request({
    url: `${(api as any).baseURL || 'https://api.nuotaai.com'}/admin/services/orders/${orderId.value}/progress`,
    method: 'PUT',
    header: { Authorization: `Bearer ${uni.getStorageSync('token')}` },
    data: { workflow_stage: currentStage.value, workflow_progress: progress.value },
  });
}

onMounted(async () => {
  // @ts-ignore
  const pages = getCurrentPages();
  // @ts-ignore
  const query = pages[pages.length - 1]?.options || {};
  orderId.value = Number(query.order_id);
  // 演示数据
  order.value = {
    order_no: query.order_no || 'SO-2026-001',
    service_name: query.service_name || '门店全案诊断',
    member_name: query.member_name || '猫猫',
    store_name: query.store_name || '武汉一二一旗舰店',
    appoint_date: query.appoint_date || '2026-05-13',
    appoint_time: query.appoint_time || '14:00-17:00',
  };
  progress.value = Number(query.progress || 0);
  currentStage.value = query.stage || 'diagnosis';
});
</script>

<style lang="scss">
.page { background: #fafaf8; min-height: 100vh; display: flex; flex-direction: column; }

.header { padding: 60rpx 48rpx 24rpx; background: #0a0a0a; }
.header-title { display: block; font-size: 36rpx; font-weight: 500; color: #c9a96e; letter-spacing: 8rpx; }
.header-sub { display: block; font-size: 20rpx; color: #666; margin-top: 8rpx; letter-spacing: 3rpx; font-family: monospace; }

.scroll { flex: 1; }

.order-card { margin: 24rpx 32rpx; background: #fff; border-radius: 20rpx; overflow: hidden; }
.oc-row { display: flex; justify-content: space-between; align-items: center; padding: 24rpx 32rpx; border-bottom: 1rpx solid #f3f3f3; }
.oc-row.last { border-bottom: none; }
.oc-label { font-size: 24rpx; color: #9a9a9a; letter-spacing: 2rpx; }
.oc-val { font-size: 24rpx; color: #0a0a0a; font-weight: 500; text-align: right; max-width: 60%; }

.section-block { background: #fff; margin-top: 16rpx; padding: 28rpx 32rpx; }
.block-title { display: block; font-size: 22rpx; letter-spacing: 6rpx; color: #c9a96e; margin-bottom: 20rpx; }

.stage-tabs { display: flex; gap: 16rpx; }
.stage-tab { flex: 1; padding: 18rpx; text-align: center; border: 1rpx solid #ebe8e2; border-radius: 12rpx; background: #fafaf8; }
.stage-tab.active { border-color: #0a0a0a; background: #0a0a0a; }
.stage-tab.active .st-text { color: #c9a96e; }
.st-text { font-size: 24rpx; color: #555; letter-spacing: 3rpx; }

.prog-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16rpx; }
.prog-num { font-size: 28rpx; font-weight: 600; color: #c9a96e; }
.prog-bar-wrap { margin-bottom: 20rpx; }
.prog-bar { height: 8rpx; background: #ebe8e2; border-radius: 4rpx; overflow: hidden; }
.prog-fill { height: 100%; background: linear-gradient(90deg, #c9a96e 0%, #7b6fdf 100%); border-radius: 4rpx; transition: width 0.3s; }
.prog-btns { display: flex; gap: 12rpx; }
.prog-btn { flex: 1; padding: 14rpx; text-align: center; border: 1rpx solid #ebe8e2; border-radius: 10rpx; font-size: 22rpx; color: #555; background: #fafaf8; }
.prog-btn.active { border-color: #c9a96e; background: rgba(201,169,110,0.1); color: #a88a4d; font-weight: 600; }

.log-textarea { width: 100%; min-height: 200rpx; background: #fafaf8; border: 1rpx solid #ebe8e2; border-radius: 12rpx; padding: 20rpx; font-size: 26rpx; color: #333; line-height: 1.7; box-sizing: border-box; }
.log-textarea.small { min-height: 120rpx; }
.char-count { display: block; text-align: right; font-size: 20rpx; color: #bbb; margin-top: 8rpx; }

.photo-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20rpx; }
.photo-count { font-size: 22rpx; color: #9a9a9a; }
.photo-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16rpx; }
.photo-item { position: relative; aspect-ratio: 1; border-radius: 12rpx; overflow: hidden; }
.photo-img { width: 100%; height: 100%; }
.photo-del { position: absolute; top: 8rpx; right: 8rpx; width: 36rpx; height: 36rpx; background: rgba(0,0,0,0.6); border-radius: 50%; color: #fff; font-size: 18rpx; display: flex; align-items: center; justify-content: center; }
.photo-add { aspect-ratio: 1; border: 2rpx dashed #c9a96e; border-radius: 12rpx; display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(201,169,110,0.04); }
.pa-icon { font-size: 48rpx; color: #c9a96e; line-height: 1; }
.pa-text { font-size: 20rpx; color: #c9a96e; margin-top: 8rpx; letter-spacing: 2rpx; }

.confirm-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12rpx; }
.toggle { width: 88rpx; height: 48rpx; border-radius: 24rpx; background: #e0e0e0; position: relative; transition: background 0.3s; }
.toggle.on { background: #c9a96e; }
.toggle-ball { position: absolute; top: 6rpx; left: 6rpx; width: 36rpx; height: 36rpx; border-radius: 50%; background: #fff; transition: transform 0.3s; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.2); }
.toggle.on .toggle-ball { transform: translateX(40rpx); }
.confirm-tip { font-size: 22rpx; color: #9a9a9a; letter-spacing: 1rpx; }

.bottom-bar { position: fixed; left: 0; right: 0; bottom: 0; padding: 16rpx 32rpx 60rpx; background: #fff; border-top: 1rpx solid #ebe8e2; display: flex; gap: 24rpx; }
.btn-save { flex: 1; padding: 24rpx; background: #fafaf8; border: 1rpx solid #ebe8e2; border-radius: 48rpx; font-size: 28rpx; color: #555; letter-spacing: 3rpx; }
.btn-submit { flex: 1.5; padding: 24rpx; background: #0a0a0a; border: none; border-radius: 48rpx; font-size: 28rpx; color: #c9a96e; letter-spacing: 4rpx; }
.btn-submit[disabled] { background: #f3f3f3; color: #bbb; }
</style>
