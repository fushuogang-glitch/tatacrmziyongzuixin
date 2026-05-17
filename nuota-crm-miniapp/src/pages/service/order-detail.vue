<template>
  <view class="page">
    <view class="hero">
      <view :class="['status-tag', statusClass]">{{ statusLabel }}</view>
      <text class="order-no">{{ order.order_no }}</text>
      <text class="service-name">{{ order.service_name || '专案服务' }}</text>
    </view>

    <view class="info">
      <view class="info-row">
        <text class="info-label">预约时间</text>
        <text class="info-value">{{ order.appoint_date }} · {{ order.appoint_time }}</text>
      </view>
      <view class="info-row">
        <text class="info-label">服务天数</text>
        <text class="info-value">{{ progress.days || 1 }} 天 （{{ progress.date_start }} ~ {{ progress.date_end }}）</text>
      </view>
      <view class="info-row">
        <text class="info-label">服务老师</text>
        <text class="info-value">{{ order.consultant_name || '待分配' }}</text>
      </view>
      <view v-if="order.assistant_name" class="info-row">
        <text class="info-label">助理老师</text>
        <text class="info-value">{{ order.assistant_name }}</text>
      </view>
      <view class="info-row">
        <text class="info-label">服务门店</text>
        <text class="info-value">{{ order.store_name }}</text>
      </view>
      <view class="info-row last">
        <text class="info-label">门店地址</text>
        <text class="info-value">{{ order.store_address || '待补充' }}</text>
      </view>
    </view>

    <!-- 步骤条 -->
    <view class="section">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">服 务 进 度</text>
        <text class="sec-en">Progress</text>
      </view>

      <view class="steps">
        <view v-for="(s, i) in progress.steps || []" :key="s.key"
              :class="['step', s.done ? 'done' : '', currentStepKey === s.key ? 'current' : '']">
          <view class="step-dot">
            <text v-if="s.done" class="step-check">✓</text>
            <text v-else class="step-num">{{ i + 1 }}</text>
          </view>
          <text class="step-label">{{ s.label }}</text>
          <view v-if="i < (progress.steps || []).length - 1" class="step-line"
                :class="{ active: s.done }"></view>
        </view>
      </view>

      <view class="progress-bar">
        <view class="progress-fill" :style="{ width: (progress.workflow_progress || 0) + '%' }"></view>
      </view>
      <text class="progress-text">{{ progress.workflow_progress || 0 }}% · {{ progress.workflow_stage || '预约确认' }}</text>
    </view>

    <!-- 执案日志 -->
    <view class="section" v-if="logs.length">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">执 案 日 志</text>
        <text class="sec-en">Work Logs</text>
      </view>

      <view class="logs">
        <view v-for="(l, i) in logs" :key="l.id || i" class="log-item">
          <view class="log-dot"></view>
          <view class="log-body">
            <view class="log-header">
              <text class="log-stage">{{ l.stage }}</text>
              <text v-if="l.day_number" class="log-day">Day{{ l.day_number }}</text>
            </view>
            <text class="log-content">{{ l.content }}</text>
            <text v-if="l.findings" class="log-extra">📋 发现：{{ l.findings }}</text>
            <text v-if="l.decisions" class="log-extra">📌 决策：{{ l.decisions }}</text>
            <text v-if="l.next_actions" class="log-extra">🎯 下一步：{{ l.next_actions }}</text>
            <view v-if="l.images && l.images.length" class="log-images">
              <image v-for="(img, j) in l.images" :key="j" :src="img" mode="aspectFill"
                     class="log-img" @tap="previewImg(img, l.images)" />
            </view>
            <text class="log-time">{{ l.author ? l.author + ' · ' : '' }}{{ l.created_at }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 空日志提示 -->
    <view class="section" v-if="!logs.length && loaded">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">执 案 日 志</text>
        <text class="sec-en">Work Logs</text>
      </view>
      <view class="empty-tip">
        <text class="empty-icon">📝</text>
        <text class="empty-text">老师还未填写执案日志</text>
      </view>
    </view>

    <!-- 已评价展示 -->
    <view v-if="order.rating" class="section">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">满 意 度 评 价</text>
        <text class="sec-en">Rating</text>
      </view>
      <view class="rated-card">
        <view class="rated-stars">
          <text v-for="i in 5" :key="i" :class="['star', order.rating >= i ? 'on' : '']">★</text>
        </view>
        <text v-if="order.rating_comment" class="rated-comment">"{{ order.rating_comment }}"</text>
        <text class="rated-time">{{ order.rated_at }}</text>
      </view>
    </view>

    <!-- 未评价按钮 -->
    <view v-if="order.status === 'completed' && !order.rating" class="bottom">
      <button class="btn" @tap="showRating = true">提交满意度评价</button>
    </view>

    <view v-if="showRating" class="modal">
      <view class="modal-card">
        <text class="modal-title">满 意 度 评 价</text>
        <view class="stars">
          <text v-for="i in 5" :key="i" :class="['star', rating >= i ? 'on' : '']" @tap="rating = i">★</text>
        </view>
        <textarea class="comment" v-model="comment" placeholder="留下您的评价..." />
        <view class="modal-btns">
          <button class="modal-cancel" @tap="showRating = false">取消</button>
          <button class="modal-submit" @tap="submitRating">提交</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api';

const order = ref<any>({});
const id = ref(0);
const logs = ref<any[]>([]);
const progress = ref<any>({});
const loaded = ref(false);
const showRating = ref(false);
const rating = ref(5);
const comment = ref('');

const statusClass = computed(() => {
  const s = order.value.status;
  if (s === 'in_progress' || s === 'preparing' || s === 'accepted') return 's1';
  if (s === 'pending' || s === 'confirmed') return 's2';
  if (s === 'follow_up' || s === 'reporting') return 's1';
  return 's3';
});

const statusLabel = computed(() => {
  const m: Record<string, string> = {
    pending: '待确认', confirmed: '已确认', accepted: '老师已接单',
    preparing: '执案准备中', in_progress: '执案中',
    reporting: '报告提交', follow_up: '执案跟进',
    completed: '已完成', cancelled: '已取消',
  };
  return m[order.value.status] || order.value.status;
});

const currentStepKey = computed(() => {
  const steps = progress.value.steps || [];
  // 找最后一个done=true的step
  for (let i = steps.length - 1; i >= 0; i--) {
    if (steps[i].done) return steps[i].key;
  }
  return steps[0]?.key || '';
});

async function load() {
  if (!id.value) return;
  // 三个接口并发
  const [orderRes, logsRes, progressRes] = await Promise.all([
    api.getServiceOrder(id.value).catch(() => null),
    api.orderLogs(id.value).catch(() => []),
    api.orderProgress(id.value).catch(() => ({})),
  ]);
  order.value = orderRes || {};
  logs.value = Array.isArray(logsRes) ? logsRes : [];
  progress.value = progressRes || {};
  loaded.value = true;
}

function previewImg(current: string, urls: string[]) {
  uni.previewImage({ current, urls });
}

async function submitRating() {
  try {
    await api.rateServiceOrder(id.value, { rating: rating.value, comment: comment.value });
    uni.showToast({ title: '评价成功', icon: 'success' });
    showRating.value = false;
    load();
  } catch (e: any) {
    uni.showToast({ title: e?.msg || '评价失败', icon: 'none' });
  }
}

onMounted(() => {
  // @ts-ignore
  const pages = getCurrentPages();
  // @ts-ignore
  const query = pages[pages.length - 1]?.options || {};
  id.value = Number(query.id);
  load();
});
</script>

<style lang="scss">
.page { background: #fff; min-height: 100vh; padding-bottom: 160rpx; }
.hero {
  padding: 60rpx 48rpx 40rpx;
  background: linear-gradient(135deg, #0a0a0a 0%, #2a2520 100%);
  color: #fff;
}
.status-tag {
  display: inline-block;
  padding: 8rpx 24rpx;
  border-radius: 24rpx;
  font-size: 22rpx;
  letter-spacing: 4rpx;
  background: rgba(201,169,110,0.15);
  color: #c9a96e;
  margin-bottom: 24rpx;
}
.status-tag.s1 { background: rgba(201,169,110,0.2); }
.status-tag.s2 { background: rgba(123,111,223,0.2); color: #b8a7ff; }
.order-no {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 4rpx;
  font-style: italic;
  margin-bottom: 12rpx;
}
.service-name {
  display: block;
  font-size: 40rpx;
  letter-spacing: 8rpx;
  font-weight: 500;
}

.info { padding: 0 48rpx; }
.info-row {
  padding: 28rpx 0;
  border-bottom: 1rpx solid #ebe8e2;
  display: flex;
  justify-content: space-between;
}
.info-row.last { border-bottom: none; }
.info-label { font-size: 24rpx; color: #9a9a9a; letter-spacing: 3rpx; }
.info-value { font-size: 24rpx; color: #0a0a0a; }

.section { padding: 40rpx 48rpx 24rpx; }
.sec-head { display: flex; align-items: center; gap: 20rpx; margin-bottom: 24rpx; }
.sec-line { width: 48rpx; height: 1rpx; background: #c9a96e; }
.sec-title { font-size: 26rpx; letter-spacing: 12rpx; color: #0a0a0a; flex: 1; font-weight: 500; }
.sec-en { font-size: 22rpx; color: #9a9a9a; font-style: italic; }

/* 步骤条 */
.steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 32rpx;
  padding: 0 8rpx;
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
}
.step-dot {
  width: 44rpx; height: 44rpx;
  border-radius: 50%;
  background: #ebe8e2;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12rpx;
  z-index: 1;
}
.step.done .step-dot { background: #c9a96e; }
.step.current .step-dot {
  background: #0a0a0a;
  box-shadow: 0 0 0 6rpx rgba(201,169,110,0.3);
}
.step-check { color: #fff; font-size: 22rpx; }
.step-num { color: #9a9a9a; font-size: 20rpx; }
.step.current .step-num { color: #c9a96e; }
.step-label {
  font-size: 18rpx;
  color: #9a9a9a;
  text-align: center;
  letter-spacing: 1rpx;
  line-height: 1.4;
}
.step.done .step-label { color: #0a0a0a; }
.step.current .step-label { color: #c9a96e; font-weight: 600; }
.step-line {
  position: absolute;
  top: 22rpx;
  left: 50%;
  width: 100%;
  height: 2rpx;
  background: #ebe8e2;
  z-index: 0;
}
.step-line.active { background: #c9a96e; }

.progress-bar {
  height: 8rpx;
  background: #ebe8e2;
  border-radius: 4rpx;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #c9a96e 0%, #7b6fdf 100%);
}
.progress-text {
  display: block;
  text-align: right;
  font-size: 22rpx;
  color: #c9a96e;
  margin-top: 12rpx;
  letter-spacing: 2rpx;
}

/* 日志 */
.logs { margin-top: 8rpx; }
.log-item {
  display: flex;
  gap: 20rpx;
  padding-bottom: 28rpx;
  position: relative;
}
.log-item::before {
  content: '';
  position: absolute;
  left: 11rpx;
  top: 24rpx;
  bottom: -8rpx;
  width: 2rpx;
  background: #ebe8e2;
}
.log-item:last-child::before { display: none; }
.log-dot {
  width: 24rpx; height: 24rpx;
  border-radius: 50%;
  background: #c9a96e;
  margin-top: 8rpx;
  flex-shrink: 0;
  z-index: 1;
}
.log-body { flex: 1; }
.log-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 8rpx;
}
.log-stage {
  font-size: 24rpx;
  font-weight: 500;
  color: #0a0a0a;
  letter-spacing: 3rpx;
}
.log-day {
  font-size: 20rpx;
  color: #c9a96e;
  background: rgba(201,169,110,0.12);
  padding: 4rpx 14rpx;
  border-radius: 16rpx;
}
.log-content {
  display: block;
  font-size: 22rpx;
  color: #555;
  line-height: 1.6;
  margin-bottom: 6rpx;
}
.log-extra {
  display: block;
  font-size: 22rpx;
  color: #777;
  line-height: 1.6;
  margin-bottom: 4rpx;
}
.log-images {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
  flex-wrap: wrap;
}
.log-img {
  width: 160rpx; height: 160rpx;
  border-radius: 12rpx;
}
.log-time { font-size: 20rpx; color: #9a9a9a; margin-top: 8rpx; display: block; }

/* 空日志 */
.empty-tip {
  text-align: center;
  padding: 40rpx 0;
}
.empty-icon { font-size: 60rpx; display: block; margin-bottom: 12rpx; }
.empty-text { font-size: 24rpx; color: #9a9a9a; letter-spacing: 4rpx; }

.bottom {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  padding: 24rpx 48rpx 60rpx;
  background: #fff;
  border-top: 1rpx solid #ebe8e2;
}
.btn {
  background: #0a0a0a;
  color: #c9a96e;
  border: none;
  border-radius: 48rpx;
  padding: 24rpx;
  font-size: 30rpx;
  letter-spacing: 8rpx;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}
.modal-card {
  background: #fff;
  width: 600rpx;
  border-radius: 24rpx;
  padding: 48rpx;
}
.modal-title {
  display: block;
  text-align: center;
  font-size: 28rpx;
  letter-spacing: 8rpx;
  margin-bottom: 32rpx;
  font-weight: 500;
}
.stars {
  display: flex;
  justify-content: center;
  gap: 16rpx;
  margin-bottom: 32rpx;
}
.star { font-size: 60rpx; color: #ebe8e2; }
.star.on { color: #c9a96e; }
.comment {
  width: 100%;
  min-height: 160rpx;
  border: 1rpx solid #ebe8e2;
  border-radius: 16rpx;
  padding: 20rpx;
  font-size: 24rpx;
  box-sizing: border-box;
}
.modal-btns {
  display: flex;
  gap: 16rpx;
  margin-top: 32rpx;
}
.modal-cancel, .modal-submit {
  flex: 1;
  padding: 20rpx;
  border-radius: 40rpx;
  font-size: 26rpx;
  border: none;
}
.modal-cancel { background: #f5f5f5; color: #666; }
.modal-submit { background: #0a0a0a; color: #c9a96e; }

.rated-card {
  background: linear-gradient(135deg, #faf8f4, #f5f0e8);
  border-radius: 16rpx;
  padding: 32rpx;
  text-align: center;
}
.rated-stars {
  display: flex;
  justify-content: center;
  gap: 8rpx;
  margin-bottom: 16rpx;
}
.rated-comment {
  display: block;
  font-size: 24rpx;
  color: #666;
  line-height: 1.8;
  margin-top: 12rpx;
  font-style: italic;
}
.rated-time {
  display: block;
  font-size: 20rpx;
  color: #9a9a9a;
  margin-top: 12rpx;
}
</style>
