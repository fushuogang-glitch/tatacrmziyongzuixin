<template>
  <view class="apply">
    <view class="hdr">申请下店</view>

    <!-- 选老师 -->
    <view class="section">
      <view class="section-title">选择老师</view>
      <scroll-view scroll-x class="teacher-scroll">
        <view
          v-for="t in teachers" :key="t.id"
          :class="['teacher-card', { active: form.consultant_id === t.id }]"
          @tap="pickTeacher(t)"
        >
          <view class="t-avatar">{{ t.name?.[0] || '师' }}</view>
          <view class="t-name">{{ t.name }}</view>
          <view class="t-spec">{{ t.specialty || '全科' }}</view>
        </view>
      </scroll-view>
    </view>

    <!-- 日历选日期 -->
    <view class="section">
      <view class="section-title">
        选择日期
        <text class="legend">
          <text class="dot green"></text>可约
          <text class="dot red"></text>忙碌
          <text class="dot gray"></text>休假
        </text>
      </view>

      <!-- 月份切换 -->
      <view class="month-nav">
        <view class="nav-btn" @tap="prevMonth">◀</view>
        <text class="month-label">{{ calYear }}年{{ calMonth }}月</text>
        <view class="nav-btn" @tap="nextMonth">▶</view>
      </view>

      <!-- 星期头 -->
      <view class="weekdays">
        <text v-for="w in ['日','一','二','三','四','五','六']" :key="w" class="wd">{{ w }}</text>
      </view>

      <!-- 日期格子 -->
      <view class="cal-grid">
        <view
          v-for="(cell, idx) in calCells" :key="idx"
          :class="[
            'cal-cell',
            cell.status,
            { selected: cell.date === form.preferred_date, empty: !cell.day, today: cell.isToday }
          ]"
          @tap="cell.day && cell.status === 'available' && pickDate(cell.date)"
        >
          <text class="day-num">{{ cell.day || '' }}</text>
          <text v-if="cell.day && cell.status === 'busy'" class="tag">忙</text>
          <text v-if="cell.day && cell.status === 'leave'" class="tag">休</text>
        </view>
      </view>

      <!-- 选中提示 -->
      <view v-if="form.preferred_date" class="pick-hint">
        已选：{{ form.preferred_date }}（{{ form.duration_days }}天）
      </view>
    </view>

    <!-- 其他信息 -->
    <view class="section">
      <view class="section-title">预约信息</view>
      <view class="form">
        <view class="row">
          <text class="label">城市</text>
          <input v-model="form.city" placeholder="如：武汉" />
        </view>
        <view class="row">
          <text class="label">门店地址</text>
          <input v-model="form.address" placeholder="详细地址" />
        </view>
        <view class="row">
          <text class="label">时长</text>
          <picker :range="days" @change="onDays">
            <view class="picker">{{ form.duration_days }} 天</view>
          </picker>
        </view>
        <view class="row">
          <text class="label">备注</text>
          <input v-model="form.remark" placeholder="诉求 / 重点（可选）" />
        </view>
      </view>
    </view>

    <view class="btn-primary" @tap="submit">提交申请</view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref, computed, watch } from 'vue';
import { api } from '../../../api';
import { onLoad } from '@dcloudio/uni-app';

const form = reactive<any>({
  reward_id: 0, preferred_date: '', city: '', address: '',
  duration_days: 2, remark: '', consultant_id: 0,
});
const days = [1, 2, 3];

// --- 老师列表 ---
const teachers = ref<any[]>([]);
async function loadTeachers() {
  try {
    const res: any = await api.calendarConsultants();
    teachers.value = res?.data || res || [];
  } catch (_) {}
}

function pickTeacher(t: any) {
  form.consultant_id = t.id;
  form.preferred_date = '';
  loadSlots();
}

// --- 月份 & 排期 ---
const now = new Date();
const calYear = ref(now.getFullYear());
const calMonth = ref(now.getMonth() + 1);
const slots = ref<any[]>([]);

function prevMonth() {
  if (calMonth.value === 1) { calYear.value--; calMonth.value = 12; }
  else calMonth.value--;
  loadSlots();
}
function nextMonth() {
  if (calMonth.value === 12) { calYear.value++; calMonth.value = 1; }
  else calMonth.value++;
  loadSlots();
}

async function loadSlots() {
  if (!form.consultant_id) return;
  const y = calYear.value, m = calMonth.value;
  const startDate = `${y}-${String(m).padStart(2, '0')}-01`;
  const lastDay = new Date(y, m, 0).getDate();
  const endDate = `${y}-${String(m).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
  try {
    const res: any = await api.calendarSlots(form.consultant_id, startDate, endDate);
    slots.value = res?.data?.slots || res?.slots || [];
  } catch (_) {
    slots.value = [];
  }
}

// 构建日历格子
const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
const calCells = computed(() => {
  const y = calYear.value, m = calMonth.value;
  const firstDow = new Date(y, m - 1, 1).getDay(); // 0=Sun
  const totalDays = new Date(y, m, 0).getDate();
  const slotMap: Record<string, any> = {};
  for (const s of slots.value) slotMap[s.date] = s;

  const cells: any[] = [];
  // 前面空白
  for (let i = 0; i < firstDow; i++) cells.push({ day: 0, date: '', status: '' });
  // 日期
  for (let d = 1; d <= totalDays; d++) {
    const ds = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const s = slotMap[ds];
    cells.push({
      day: d,
      date: ds,
      status: s ? s.status : (form.consultant_id ? 'available' : ''),
      isToday: ds === todayStr,
    });
  }
  return cells;
});

function pickDate(d: string) { form.preferred_date = d; }

function onDays(e: any) { form.duration_days = days[e.detail.value]; }

onLoad((opt: any) => {
  form.reward_id = Number(opt?.reward_id || 0);
  loadTeachers();
});

async function submit() {
  if (!form.reward_id) return uni.showToast({ title: '缺少权益', icon: 'none' });
  if (!form.consultant_id) return uni.showToast({ title: '请选择老师', icon: 'none' });
  if (!form.preferred_date) return uni.showToast({ title: '请选择日期', icon: 'none' });
  uni.showLoading({ title: '提交中' });
  try {
    await api.applyBooking(form);
    uni.showToast({ title: '已提交，等待确认' });
    setTimeout(() => uni.redirectTo({ url: '/pages/booking/list/list' }), 800);
  } catch (_) {} finally { uni.hideLoading(); }
}
</script>

<style lang="scss" scoped>
.apply { padding: 32rpx; background: #f5f5f5; min-height: 100vh; }
.hdr { font-size: 44rpx; font-weight: 700; margin-bottom: 32rpx; color: #1a1a2e; }

.section { background: #fff; border-radius: 20rpx; padding: 28rpx; margin-bottom: 24rpx; }
.section-title {
  font-size: 30rpx; font-weight: 600; color: #333; margin-bottom: 20rpx;
  display: flex; align-items: center; justify-content: space-between;
  .legend { font-size: 22rpx; color: #999; display: flex; gap: 12rpx; align-items: center;
    .dot { width: 16rpx; height: 16rpx; border-radius: 50%; display: inline-block; margin-right: 4rpx; }
    .green { background: #52c41a; }
    .red { background: #e74c3c; }
    .gray { background: #95a5a6; }
  }
}

/* 老师横滑 */
.teacher-scroll { white-space: nowrap; }
.teacher-card {
  display: inline-flex; flex-direction: column; align-items: center;
  width: 140rpx; padding: 16rpx 0; border-radius: 16rpx; margin-right: 16rpx;
  border: 2rpx solid #eee; transition: all .2s;
  &.active { border-color: #c9a96e; background: rgba(201,169,110,.08); }
  .t-avatar {
    width: 72rpx; height: 72rpx; border-radius: 50%; background: linear-gradient(135deg,#c9a96e,#e8d5a3);
    color: #fff; font-size: 30rpx; display: flex; align-items: center; justify-content: center;
  }
  .t-name { font-size: 26rpx; font-weight: 600; margin-top: 8rpx; color: #333; }
  .t-spec { font-size: 20rpx; color: #999; }
}

/* 月份导航 */
.month-nav {
  display: flex; align-items: center; justify-content: center; gap: 32rpx; margin-bottom: 16rpx;
  .nav-btn { font-size: 28rpx; color: #c9a96e; padding: 8rpx 16rpx; }
  .month-label { font-size: 30rpx; font-weight: 600; }
}

/* 星期头 */
.weekdays { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; margin-bottom: 8rpx;
  .wd { font-size: 22rpx; color: #999; }
}

/* 日历格子 */
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6rpx; }
.cal-cell {
  position: relative; aspect-ratio: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; border-radius: 12rpx;
  transition: all .15s; font-size: 28rpx;

  &.available { background: #f0faf0; color: #333; }
  &.busy { background: #fef0f0; color: #e74c3c; }
  &.leave { background: #f0f0f0; color: #95a5a6; }
  &.empty { background: transparent; }
  &.today .day-num { font-weight: 700; text-decoration: underline; }
  &.selected { background: #c9a96e !important; color: #fff !important;
    .tag { color: #fff; }
  }
  &.available:active { transform: scale(.92); }

  .tag { font-size: 18rpx; margin-top: 2rpx; }
}

.pick-hint { text-align: center; font-size: 26rpx; color: #c9a96e; margin-top: 16rpx; }

/* 表单 */
.form {
  .row { display: flex; align-items: center; padding: 24rpx 0;
    border-bottom: 1rpx solid #f0f0f0;
    &:last-child { border-bottom: none; }
    .label { width: 150rpx; color: #666; font-size: 28rpx; }
    input, .picker { flex: 1; font-size: 28rpx; }
  }
}

.btn-primary {
  margin-top: 40rpx; height: 88rpx; line-height: 88rpx; text-align: center;
  background: linear-gradient(135deg, #c9a96e, #e8d5a3); color: #fff;
  font-size: 32rpx; font-weight: 600; border-radius: 44rpx; letter-spacing: 4rpx;
}
</style>
