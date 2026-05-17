<template>
  <view class="page">
    <view class="head">
      <text class="head-en">APPOINT</text>
      <text class="head-cn">预 约 专 案</text>
    </view>

    <!-- 服务信息 -->
    <view class="service-info" v-if="service.name">
      <text class="si-label">服务项目</text>
      <text class="si-name">{{ service.name }}</text>
    </view>

    <!-- 老师选择 -->
    <view class="section">
      <view class="section-title">选择服务老师</view>
      <scroll-view scroll-x class="teacher-scroll">
        <view class="teacher-list">
          <view v-for="c in consultants" :key="c.consultant_id"
            :class="['teacher-card', { active: selectedConsultant === c.consultant_id }]"
            @tap="selectConsultant(c)">
            <view class="tc-avatar">{{ c.consultant_name.slice(0, 1) }}</view>
            <text class="tc-name">{{ c.consultant_name }}</text>
            <text class="tc-free">剩余 {{ c.free_days }}天</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <!-- 日历选择 -->
    <view class="section" v-if="selectedConsultant">
      <view class="section-title">选择预约日期</view>
      <!-- 月份导航 -->
      <view class="cal-nav">
        <text class="cal-nav-btn" @tap="prevCalMonth">‹</text>
        <text class="cal-month-title">{{ calYear }}年{{ calMonth }}月</text>
        <text class="cal-nav-btn" @tap="nextCalMonth">›</text>
      </view>
      <!-- 星期头 -->
      <view class="cal-week-header">
        <text v-for="w in weekdays" :key="w" class="cal-week-cell">{{ w }}</text>
      </view>
      <!-- 日期格子 -->
      <view class="cal-grid">
        <view v-for="cell in calendarCells" :key="cell.key"
          :class="['cal-cell', {
            'other-month': !cell.inMonth,
            'today': cell.isToday,
            'selected': appointDate === cell.dateStr,
            'available': cell.inMonth && cell.available,
            'unavailable': cell.inMonth && !cell.available,
            'past': cell.past,
          }]"
          @tap="cell.inMonth && cell.available && !cell.past ? selectDate(cell.dateStr) : null">
          <text class="cal-day">{{ cell.day }}</text>
          <view v-if="cell.inMonth && !cell.past" class="cal-dot"
            :style="{ background: cell.available ? '#52c41a' : '#e84c4c' }"></view>
        </view>
      </view>
      <view class="cal-legend">
        <view class="legend-item"><view class="legend-dot" style="background:#52c41a"></view><text>可预约</text></view>
        <view class="legend-item"><view class="legend-dot" style="background:#e84c4c"></view><text>已排满</text></view>
      </view>
    </view>

    <!-- 时段选择 -->
    <view class="section" v-if="appointDate">
      <view class="section-title">选择服务时段</view>
      <view class="time-slots">
        <view v-for="(slot, i) in timeSlots" :key="i"
          :class="['time-slot', { active: timeIdx === i }]"
          @tap="timeIdx = i">
          <text class="ts-text">{{ slot }}</text>
        </view>
      </view>
    </view>

    <!-- 门店信息 -->
    <view class="section" v-if="appointDate">
      <view class="section-title">门店信息</view>
      <view class="form">
        <view class="form-row">
          <text class="label">门店名称</text>
          <input class="input" v-model="storeName" placeholder="请输入门店名称" />
        </view>
        <view class="form-row">
          <text class="label">门店地址</text>
          <input class="input" v-model="storeAddress" placeholder="请输入详细地址" />
        </view>
        <view class="form-row last">
          <text class="label">备注</text>
          <input class="input" v-model="remark" placeholder="其他说明（选填）" />
        </view>
      </view>
    </view>

    <view class="tip" v-if="appointDate">
      <text class="tip-icon">◆</text>
      <text class="tip-text">提交后 24 小时内老师确认档期 · 留意小程序通知</text>
    </view>

    <!-- 提交 -->
    <view class="bottom" v-if="appointDate && storeName">
      <view class="submit-info">
        <text class="si-date">{{ appointDate }} {{ timeSlots[timeIdx] }}</text>
        <text class="si-consultant">{{ consultantName }}</text>
      </view>
      <button class="btn" :disabled="loading" @tap="submit">
        {{ loading ? '提交中...' : '确认预约' }}
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api';

// ─── 状态 ───
const service = ref<any>({});
const service_id = ref(0);
const consultants = ref<any[]>([]);
const selectedConsultant = ref<number | null>(null);
const consultantName = ref('');
const appointDate = ref('');
const timeSlots = ['09:00-12:00', '14:00-17:00', '19:00-21:00'];
const timeIdx = ref(0);
const storeName = ref('');
const storeAddress = ref('');
const remark = ref('');
const loading = ref(false);

// 日历
const today = new Date();
const calYear = ref(today.getFullYear());
const calMonth = ref(today.getMonth() + 1);
const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
const availableSlots = ref<Record<string, boolean>>({});

// ─── 日历格子 ───
const calendarCells = computed(() => {
  const cells = [];
  const firstDay = new Date(calYear.value, calMonth.value - 1, 1);
  const lastDay = new Date(calYear.value, calMonth.value, 0);
  const startWeekday = firstDay.getDay();
  const todayStr = today.toISOString().slice(0, 10);

  // 补上月尾
  const prevLast = new Date(calYear.value, calMonth.value - 1, 0).getDate();
  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = new Date(calYear.value, calMonth.value - 2, prevLast - i);
    cells.push({ key: `p${d.toISOString().slice(0, 10)}`, day: prevLast - i, dateStr: d.toISOString().slice(0, 10), inMonth: false, isToday: false, available: false, past: false });
  }

  // 当月
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const dt = new Date(calYear.value, calMonth.value - 1, d);
    const ds = dt.toISOString().slice(0, 10);
    const past = ds < todayStr;
    cells.push({
      key: ds, day: d, dateStr: ds, inMonth: true,
      isToday: ds === todayStr,
      available: availableSlots.value[ds] !== false, // 默认可用
      past,
    });
  }

  // 补下月头
  const total = Math.ceil(cells.length / 7) * 7;
  let n = 1;
  while (cells.length < total) {
    const dt = new Date(calYear.value, calMonth.value, n++);
    cells.push({ key: `n${dt.toISOString().slice(0, 10)}`, day: dt.getDate(), dateStr: dt.toISOString().slice(0, 10), inMonth: false, isToday: false, available: false, past: false });
  }

  return cells;
});

// ─── 加载老师列表 ───
async function loadConsultants() {
  try {
    const res = await uni.request({
      url: `${(api as any).baseURL || 'https://api.nuotaai.com'}/admin/calendar/consultants?year=${calYear.value}&month=${calMonth.value}`,
      method: 'GET',
    }) as any;
    consultants.value = res?.data?.data || [];
  } catch (e) {
    // 降级：用服务器无鉴权端点
    consultants.value = [];
  }
}

// ─── 加载老师空闲时段 ───
async function loadSlots() {
  if (!selectedConsultant.value) return;
  const firstDay = `${calYear.value}-${String(calMonth.value).padStart(2, '0')}-01`;
  const lastDay = new Date(calYear.value, calMonth.value, 0).toISOString().slice(0, 10);
  try {
    const res = await uni.request({
      url: `${(api as any).baseURL || 'https://api.nuotaai.com'}/admin/calendar/available-slots?consultant_id=${selectedConsultant.value}&start_date=${firstDay}&end_date=${lastDay}`,
      method: 'GET',
    }) as any;
    const slots: any[] = res?.data?.data?.slots || [];
    const map: Record<string, boolean> = {};
    slots.forEach((s: any) => { map[s.date] = s.available; });
    availableSlots.value = map;
  } catch (e) {
    availableSlots.value = {};
  }
}

function selectConsultant(c: any) {
  selectedConsultant.value = c.consultant_id;
  consultantName.value = c.consultant_name;
  appointDate.value = '';
  loadSlots();
}

function selectDate(ds: string) {
  appointDate.value = ds;
}

function prevCalMonth() {
  if (calMonth.value === 1) { calMonth.value = 12; calYear.value--; }
  else calMonth.value--;
  loadSlots();
}

function nextCalMonth() {
  if (calMonth.value === 12) { calMonth.value = 1; calYear.value++; }
  else calMonth.value++;
  loadSlots();
}

// ─── 提交预约 ───
async function submit() {
  const member = uni.getStorageSync('member');
  if (!member?.id) { uni.showToast({ title: '请先登录', icon: 'none' }); return; }
  if (!selectedConsultant.value) { uni.showToast({ title: '请选择服务老师', icon: 'none' }); return; }
  if (!appointDate.value || !storeName.value) { uni.showToast({ title: '请填写日期和门店', icon: 'none' }); return; }
  loading.value = true;
  try {
    await api.createServiceOrder({
      member_id: member.id,
      service_id: service_id.value,
      appoint_date: appointDate.value,
      appoint_time: timeSlots[timeIdx.value],
      consultant_id: selectedConsultant.value,
      store_name: storeName.value,
      store_address: storeAddress.value,
      remark: remark.value,
    });
    uni.showToast({ title: '预约成功！', icon: 'success' });
    setTimeout(() => uni.navigateBack(), 1200);
  } catch (e: any) {
    uni.showToast({ title: e?.msg || '预约失败，请重试', icon: 'none' });
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  // @ts-ignore
  const pages = getCurrentPages();
  // @ts-ignore
  const query = pages[pages.length - 1]?.options || {};
  service_id.value = Number(query.service_id);

  if (service_id.value) {
    api.getService(service_id.value).then((r: any) => { service.value = r || {}; });
  }
  loadConsultants();
});
</script>

<style lang="scss">
.page { background: #fafaf8; min-height: 100vh; padding-bottom: 200rpx; }

/* 头部 */
.head { padding: 80rpx 48rpx 40rpx; text-align: center; background: #fff; border-bottom: 1rpx solid #ebe8e2; }
.head-en { font-size: 22rpx; color: #c9a96e; letter-spacing: 8rpx; font-style: italic; }
.head-cn { display: block; font-size: 40rpx; color: #0a0a0a; letter-spacing: 16rpx; font-weight: 500; margin-top: 12rpx; }

/* 服务名 */
.service-info {
  background: #fff; padding: 28rpx 48rpx; display: flex; align-items: center;
  border-bottom: 1rpx solid #ebe8e2; gap: 16rpx;
}
.si-label { font-size: 22rpx; color: #999; letter-spacing: 2rpx; }
.si-name { font-size: 28rpx; color: #0a0a0a; font-weight: 500; }

/* 分区 */
.section { background: #fff; margin-top: 16rpx; padding: 32rpx 48rpx; }
.section-title { font-size: 22rpx; letter-spacing: 6rpx; color: #c9a96e; margin-bottom: 24rpx; }

/* 老师 */
.teacher-scroll { white-space: nowrap; }
.teacher-list { display: flex; gap: 20rpx; padding-bottom: 8rpx; }
.teacher-card {
  display: inline-flex; flex-direction: column; align-items: center; gap: 8rpx;
  padding: 20rpx 28rpx; border: 1rpx solid #ebe8e2; border-radius: 16rpx;
  background: #fafaf8; transition: all 0.2s; min-width: 120rpx;
}
.teacher-card.active { border-color: #c9a96e; background: #fdf6e8; }
.tc-avatar {
  width: 72rpx; height: 72rpx; border-radius: 50%; background: #c9a96e;
  color: #fff; font-size: 30rpx; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.tc-name { font-size: 24rpx; color: #0a0a0a; font-weight: 500; }
.tc-free { font-size: 18rpx; color: #52c41a; }

/* 日历 */
.cal-nav { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16rpx; }
.cal-nav-btn { font-size: 40rpx; color: #c9a96e; padding: 0 16rpx; }
.cal-month-title { font-size: 28rpx; font-weight: 600; color: #0a0a0a; }
.cal-week-header { display: grid; grid-template-columns: repeat(7, 1fr); margin-bottom: 8rpx; }
.cal-week-cell { text-align: center; font-size: 20rpx; color: #999; padding: 8rpx 0; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4rpx; }
.cal-cell {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 16rpx 0; border-radius: 12rpx; position: relative;
}
.cal-cell.other-month { opacity: 0.25; }
.cal-cell.past { opacity: 0.35; }
.cal-cell.today .cal-day { color: #c9a96e; font-weight: 700; }
.cal-cell.selected { background: #0a0a0a; border-radius: 12rpx; }
.cal-cell.selected .cal-day { color: #c9a96e; }
.cal-cell.available:not(.past):not(.selected):active { background: #fdf6e8; }
.cal-cell.unavailable { opacity: 0.5; }
.cal-day { font-size: 26rpx; color: #0a0a0a; line-height: 1; }
.cal-dot { width: 8rpx; height: 8rpx; border-radius: 50%; margin-top: 6rpx; }
.cal-legend { display: flex; justify-content: center; gap: 40rpx; margin-top: 20rpx; }
.legend-item { display: flex; align-items: center; gap: 8rpx; font-size: 20rpx; color: #999; }
.legend-dot { width: 12rpx; height: 12rpx; border-radius: 50%; }

/* 时段 */
.time-slots { display: flex; gap: 20rpx; flex-wrap: wrap; }
.time-slot {
  padding: 16rpx 28rpx; border: 1rpx solid #ebe8e2; border-radius: 10rpx;
  background: #fafaf8;
}
.time-slot.active { border-color: #c9a96e; background: #fdf6e8; }
.ts-text { font-size: 24rpx; color: #0a0a0a; }

/* 表单 */
.form {}
.form-row {
  padding: 28rpx 0; border-bottom: 1rpx solid #ebe8e2;
  display: flex; align-items: center; gap: 16rpx;
}
.form-row.last { border-bottom: none; }
.label { font-size: 24rpx; color: #0a0a0a; width: 140rpx; flex-shrink: 0; letter-spacing: 2rpx; }
.input { flex: 1; font-size: 24rpx; color: #333; text-align: right; }

/* 提示 */
.tip { margin: 20rpx 32rpx; background: #fdf6e8; border-radius: 16rpx; padding: 24rpx 28rpx; display: flex; align-items: center; gap: 16rpx; }
.tip-icon { color: #c9a96e; font-size: 20rpx; }
.tip-text { font-size: 22rpx; color: #a88a4d; letter-spacing: 1rpx; }

/* 底部 */
.bottom {
  position: fixed; left: 0; right: 0; bottom: 0;
  padding: 20rpx 48rpx 60rpx; background: #fff; border-top: 1rpx solid #ebe8e2;
}
.submit-info { display: flex; justify-content: space-between; margin-bottom: 16rpx; }
.si-date { font-size: 24rpx; color: #0a0a0a; font-weight: 500; }
.si-consultant { font-size: 22rpx; color: #c9a96e; }
.btn {
  display: block; width: 100%; background: #0a0a0a; color: #c9a96e;
  border: none; border-radius: 48rpx; padding: 28rpx;
  font-size: 30rpx; letter-spacing: 8rpx; text-align: center;
}
</style>
