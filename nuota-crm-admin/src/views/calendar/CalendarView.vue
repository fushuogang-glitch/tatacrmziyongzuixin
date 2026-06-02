<template>
  <div class="calendar-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn-icon" @click="prevMonth">‹</button>
        <span class="month-title">{{ year }}年 {{ monthNames[month - 1] }}</span>
        <button class="btn-icon" @click="nextMonth">›</button>
        <button class="btn-today" @click="goToday">今天</button>
      </div>
      <div class="toolbar-right">
        <!-- 老师筛选 -->
        <select class="select-consultant" v-model="selectedConsultant" @change="loadData">
          <option :value="null">全部老师</option>
          <option v-for="c in consultants" :key="c.consultant_id" :value="c.consultant_id">
            {{ c.consultant_name }}
            <span v-if="c.busy_days > 0">（已排 {{ c.busy_days }}天）</span>
          </option>
        </select>
        <!-- 视图切换 -->
        <div class="view-tabs">
          <button :class="['tab', { active: viewMode === 'month' }]" @click="viewMode = 'month'">月</button>
          <button :class="['tab', { active: viewMode === 'week' }]" @click="viewMode = 'week'">周</button>
          <button :class="['tab', { active: viewMode === 'staff' }]" @click="viewMode = 'staff'">老师</button>
        </div>
      </div>
    </div>

    <!-- 老师行程甘特图（staff 视图） -->
    <div v-if="viewMode === 'staff'" class="gantt-wrap">
      <div class="gantt-table">
        <!-- 表头：日期列 -->
        <div class="gantt-header">
          <div class="gantt-name-col">老师</div>
          <div v-for="d in ganttDays" :key="d.dateStr"
            :class="['gantt-day-header', { 'gd-today': d.isToday, 'gd-weekend': d.isWeekend }]">
            <div class="gd-num">{{ d.day }}</div>
            <div class="gd-week">{{ d.weekDay }}</div>
          </div>
        </div>
        <!-- 每位老师一行 -->
        <div v-for="c in consultants" :key="c.consultant_id" class="gantt-row">
          <div class="gantt-name-col">
            <div class="gn-avatar">{{ c.consultant_name.slice(0, 1) }}</div>
            <div class="gn-info">
              <div class="gn-name">{{ c.consultant_name }}</div>
              <div class="gn-stat">{{ c.busy_days }}/{{ c.monthly_days || 14 }}天</div>
            </div>
          </div>
          <div v-for="d in ganttDays" :key="d.dateStr"
            :class="['gantt-cell', { 'gc-today': d.isToday, 'gc-weekend': d.isWeekend }]">
            <template v-for="ev in getStaffDayEvents(c.consultant_id, d.dateStr)" :key="ev.id">
              <div class="gantt-event" :style="{ background: ev.color }" @click="openEvent(ev)"
                :title="ev.member_name + ' · ' + ev.title">
                <span class="ge-dot"></span>
                <span class="ge-text">{{ ev.member_name }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 月视图 -->
    <div v-else-if="viewMode === 'month'" class="calendar-grid">
      <!-- 星期头 -->
      <div class="week-header">
        <div v-for="d in weekdays" :key="d" class="week-cell">{{ d }}</div>
      </div>
      <!-- 日期格子 -->
      <div class="date-grid">
        <div v-for="cell in calendarCells" :key="cell.key"
          :class="['date-cell', {
            'other-month': !cell.inMonth,
            'today': cell.isToday,
            'selected': selectedDate === cell.dateStr,
            'has-event': cell.events.length > 0,
          }]"
          @click="selectDate(cell)">
          <div class="date-num">{{ cell.day }}<span :class="['lunar-text', { 'lunar-festival': cell.isFestival }]">{{ cell.lunar }}</span></div>
          <!-- 事件点/条 -->
          <div class="event-list">
            <template v-for="(ev, i) in cell.events.slice(0, 3)" :key="ev.id">
              <div class="event-chip" :style="{ background: ev.color }"
                @click.stop="openEvent(ev)">
                <span class="event-type-dot"></span>
                <span class="event-name">
                  <template v-if="ev.type === 'course_session'">📅 {{ ev.title }} · {{ ev.member_name }}</template>
                  <template v-else>{{ ev.title }}</template>
                </span>
              </div>
            </template>
            <div v-if="cell.events.length > 3" class="event-more">
              +{{ cell.events.length - 3 }} 更多
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 周视图 -->
    <div v-else-if="viewMode === 'week'" class="week-view">
      <div class="week-header-row">
        <div class="time-col-header"></div>
        <div v-for="d in weekDays" :key="d.dateStr"
          :class="['week-day-header', { 'today': d.isToday }]">
          <div class="week-day-name">{{ d.weekDay }}</div>
          <div class="week-day-date" @click="selectDate(d)">{{ d.day }}</div>
        </div>
      </div>
      <div class="week-body">
        <div class="time-col">
          <div v-for="h in hours" :key="h" class="time-slot-label">{{ h }}:00</div>
        </div>
        <div v-for="d in weekDays" :key="d.dateStr" class="week-day-col">
          <div v-for="h in hours" :key="h" class="week-time-cell"></div>
          <!-- 全天事件 -->
          <div v-for="ev in d.events" :key="ev.id" class="week-event"
            :style="{ background: ev.color }"
            @click="openEvent(ev)">
            <div class="we-title">{{ ev.title }}</div>
            <div class="we-member">{{ ev.member_name }}</div>
            <div class="we-consultant">{{ ev.consultant_name }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧日视图抽屉（点击日期展开） -->
    <div v-if="selectedDate && dayEvents.length > 0" class="day-drawer">
      <div class="drawer-header">
        <span>{{ selectedDate }} 共 {{ dayEvents.length }} 项</span>
        <button @click="selectedDate = null" class="btn-close">✕</button>
      </div>
      <div class="drawer-body">
        <div v-for="ev in dayEvents" :key="ev.id" class="day-event-card"
          :style="{ borderLeft: `4px solid ${ev.color}` }"
          @click="openEvent(ev)">
          <div class="dec-header">
            <span class="dec-type" :style="{ color: ev.color }">{{ ev.type_label }}</span>
            <span class="dec-time">{{ ev.time_slot }}</span>
            <span class="dec-status"
              :class="`status-${ev.status}`">{{ ev.status_label }}</span>
          </div>
          <div class="dec-title">{{ ev.title }}</div>
          <div class="dec-meta">
            <span>👤 {{ ev.member_name }}</span>
            <span>🧑‍🏫 {{ ev.consultant_name }}</span>
            <span v-if="ev.store_name">📍 {{ ev.store_name }}</span>
          </div>
          <div v-if="ev.type === 'service_order' && ev.workflow_progress > 0" class="dec-progress">
            <div class="dp-bar"><div class="dp-fill" :style="{ width: ev.workflow_progress + '%' }"></div></div>
            <span>{{ ev.workflow_progress }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 事件详情弹窗 -->
    <div v-if="activeEvent" class="event-modal" @click.self="activeEvent = null">
      <div class="modal-box">
        <div class="modal-header" :style="{ borderBottom: `3px solid ${activeEvent.color}` }">
          <span class="modal-type" :style="{ color: activeEvent.color }">{{ activeEvent.type_label }}</span>
          <span class="modal-status" :class="`status-${activeEvent.status}`">{{ activeEvent.status_label }}</span>
          <button @click="activeEvent = null" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="modal-row"><label>服务内容</label><span>{{ activeEvent.title }}</span></div>
          <div class="modal-row"><label>客户</label><span>{{ activeEvent.member_name }}</span></div>
          <div class="modal-row"><label>服务老师</label><span>{{ activeEvent.consultant_name }}</span></div>
          <div class="modal-row"><label>日期</label><span>{{ activeEvent.date }}</span></div>
          <div class="modal-row" v-if="activeEvent.time_slot"><label>时段</label><span>{{ activeEvent.time_slot }}</span></div>
          <div class="modal-row" v-if="activeEvent.store_name"><label>门店</label><span>{{ activeEvent.store_name }}</span></div>
          <div class="modal-row" v-if="activeEvent.order_no"><label>工单号</label><span class="mono">{{ activeEvent.order_no }}</span></div>
          <div v-if="activeEvent.type === 'service_order' && activeEvent.workflow_progress >= 0"
            class="modal-row progress-row">
            <label>执行进度</label>
            <div class="modal-progress">
              <div class="mp-bar"><div class="mp-fill" :style="{ width: activeEvent.workflow_progress + '%' }"></div></div>
              <span>{{ activeEvent.workflow_progress }}%</span>
            </div>
          </div>
        </div>
        <div class="modal-footer" v-if="activeEvent.type === 'service_order'">
          <button class="btn-primary" @click="goToOrder(activeEvent.order_id)">查看工单详情 →</button>
        </div>
      </div>
    </div>

    <!-- 加载遮罩 -->
    <div v-if="loading" class="loading-mask">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { API as adminAPI } from '@/api/index'

const router = useRouter()

// ─── 状态 ───
const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1)
const viewMode = ref<'month' | 'week' | 'staff'>('month')
const selectedConsultant = ref<number | null>(null)
const selectedDate = ref<string | null>(null)
const activeEvent = ref<any>(null)
const loading = ref(false)

const allEvents = ref<any[]>([])
const consultants = ref<any[]>([])
const dayEvents = ref<any[]>([])

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
const hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

// ─── 农历计算 ───
const lunarInfo = [0x04bd8,0x04ae0,0x0a570,0x054d5,0x0d260,0x0d950,0x16554,0x056a0,0x09ad0,0x055d2,0x04ae0,0x0a5b6,0x0a4d0,0x0d250,0x1d255,0x0b540,0x0d6a0,0x0ada2,0x095b0,0x14977,0x04970,0x0a4b0,0x0b4b5,0x06a50,0x06d40,0x1ab54,0x02b60,0x09570,0x052f2,0x04970,0x06566,0x0d4a0,0x0ea50,0x06e95,0x05ad0,0x02b60,0x186e3,0x092e0,0x1c8d7,0x0c950,0x0d4a0,0x1d8a6,0x0b550,0x056a0,0x1a5b4,0x025d0,0x092d0,0x0d2b2,0x0a950,0x0b557,0x06ca0,0x0b550,0x15355,0x04da0,0x0a5b0,0x14573,0x052b0,0x0a9a8,0x0e950,0x06aa0,0x0aea6,0x0ab50,0x04b60,0x0aae4,0x0a570,0x05260,0x0f263,0x0d950,0x05b57,0x056a0,0x096d0,0x04dd5,0x04ad0,0x0a4d0,0x0d4d4,0x0d250,0x0d558,0x0b540,0x0b6a0,0x195a6,0x095b0,0x049b0,0x0a974,0x0a4b0,0x0b27a,0x06a50,0x06d40,0x0af46,0x0ab60,0x09570,0x04af5,0x04970,0x064b0,0x074a3,0x0ea50,0x06b58,0x05ac0,0x0ab60,0x096d5,0x092e0,0x0c960,0x0d954,0x0d4a0,0x0da50,0x07552,0x056a0,0x0abb7,0x025d0,0x092d0,0x0cab5,0x0a950,0x0b4a0,0x0baa4,0x0ad50,0x055d9,0x04ba0,0x0a5b0,0x15176,0x052b0,0x0a930,0x07954,0x06aa0,0x0ad50,0x05b52,0x04b60,0x0a6e6,0x0a4e0,0x0d260,0x0ea65,0x0d530,0x05aa0,0x076a3,0x096d0,0x04afb,0x04ad0,0x0a4d0,0x1d0b6,0x0d250,0x0d520,0x0dd45,0x0b5a0,0x056d0,0x055b2,0x049b0,0x0a577,0x0a4b0,0x0aa50,0x1b255,0x06d20,0x0ada0,0x14b63,0x09370,0x049f8,0x04970,0x064b0,0x168a6,0x0ea50,0x06b20,0x1a6c4,0x0aae0,0x092e0,0x0d2e3,0x0c960,0x0d557,0x0d4a0,0x0da50,0x05d55,0x056a0,0x0a6d0,0x055d4,0x052d0,0x0a9b8,0x0a950,0x0b4a0,0x0b6a6,0x0ad50,0x055a0,0x0aba4,0x0a5b0,0x052b0,0x0b273,0x06930,0x07337,0x06aa0,0x0ad50,0x14b55,0x04b60,0x0a570,0x054e4,0x0d160,0x0e968,0x0d520,0x0daa0,0x16aa6,0x056d0,0x04ae0,0x0a9d4,0x0a4d0,0x0d150,0x0f252,0x0d520]
const Gan = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
const Zhi = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
const Animals = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
const lunarMonthNames = ['正','二','三','四','五','六','七','八','九','十','冬','腊']
const lunarDayNames = ['初一','初二','初三','初四','初五','初六','初七','初八','初九','初十','十一','十二','十三','十四','十五','十六','十七','十八','十九','二十','廿一','廿二','廿三','廿四','廿五','廿六','廿七','廿八','廿九','三十']

// 传统节日
const lunarFestivals: Record<string, string> = {
  '1-1': '春节', '1-15': '元宵', '2-2': '龙抬头', '5-5': '端午',
  '7-7': '七夕', '7-15': '中元', '8-15': '中秋', '9-9': '重阳',
  '12-8': '腊八', '12-30': '除夕',
}
const solarFestivals: Record<string, string> = {
  '1-1': '元旦', '2-14': '情人节', '3-8': '妇女节', '3-12': '植树节',
  '4-1': '愚人节', '5-1': '劳动节', '5-4': '青年节', '6-1': '儿童节',
  '7-1': '建党节', '8-1': '建军节', '9-10': '教师节', '10-1': '国庆节',
  '12-25': '圣诞节',
}

function lYearDays(y: number) {
  let s = 348
  for (let i = 0x8000; i > 0x8; i >>= 1) s += (lunarInfo[y - 1900] & i) ? 1 : 0
  return s + leapDays(y)
}
function leapMonth(y: number) { return lunarInfo[y - 1900] & 0xf }
function leapDays(y: number) {
  if (leapMonth(y)) return (lunarInfo[y - 1900] & 0x10000) ? 30 : 29
  return 0
}
function monthDays(y: number, m: number) { return (lunarInfo[y - 1900] & (0x10000 >> m)) ? 30 : 29 }

function solarToLunar(sy: number, sm: number, sd: number) {
  const baseDate = new Date(1900, 0, 31)
  const objDate = new Date(sy, sm - 1, sd)
  let offset = Math.floor((objDate.getTime() - baseDate.getTime()) / 86400000)
  let ly = 1900
  let temp = 0
  for (; ly < 2101 && offset > 0; ly++) {
    temp = lYearDays(ly)
    offset -= temp
  }
  if (offset < 0) { offset += temp; ly-- }
  const lm_leap = leapMonth(ly)
  let isLeap = false
  let lm = 1
  for (; lm < 13 && offset > 0; lm++) {
    if (lm_leap > 0 && lm === lm_leap + 1 && !isLeap) {
      --lm; isLeap = true; temp = leapDays(ly)
    } else { temp = monthDays(ly, lm) }
    if (isLeap && lm === lm_leap + 1) isLeap = false
    offset -= temp
  }
  if (offset === 0 && lm_leap > 0 && lm === lm_leap + 1) {
    if (isLeap) isLeap = false; else { isLeap = true; --lm }
  }
  if (offset < 0) { offset += temp; --lm }
  const ld = offset + 1
  // 节日
  const lunarKey = `${lm}-${ld}`
  const solarKey = `${sm}-${sd}`
  const festival = lunarFestivals[lunarKey] || solarFestivals[solarKey] || ''
  // 显示文字：优先节日，其次初一显示月名，其次日名
  let text = ''
  if (festival) text = festival
  else if (ld === 1) text = lunarMonthNames[lm - 1] + '月'
  else text = lunarDayNames[ld - 1]
  return { year: ly, month: lm, day: ld, isLeap, text, festival }
}

// ─── 工具：本地日期格式化（避免UTC偏移） ───
function toLocalDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// ─── 计算：老师甘特图日期列 ───
const ganttDays = computed(() => {
  const lastDay = new Date(year.value, month.value, 0).getDate()
  const todayStr = toLocalDateStr(today)
  const weekLabels = ['日', '一', '二', '三', '四', '五', '六']
  return Array.from({ length: lastDay }, (_, i) => {
    const d = new Date(year.value, month.value - 1, i + 1)
    const ds = toLocalDateStr(d)
    return {
      day: i + 1,
      dateStr: ds,
      weekDay: weekLabels[d.getDay()],
      isToday: ds === todayStr,
      isWeekend: d.getDay() === 0 || d.getDay() === 6,
    }
  })
})

function getStaffDayEvents(consultantId: number, dateStr: string) {
  return allEvents.value.filter(e => e.date === dateStr && e.consultant_id === consultantId)
}

// ─── 计算：月视图格子 ───
const calendarCells = computed(() => {
  const cells = []
  const firstDay = new Date(year.value, month.value - 1, 1)
  const lastDay = new Date(year.value, month.value, 0)
  const startWeekday = firstDay.getDay()

  // 填充上月尾
  const prevLastDay = new Date(year.value, month.value - 1, 0).getDate()
  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = new Date(year.value, month.value - 2, prevLastDay - i)
    const ds = toLocalDateStr(d)
    const pdt = new Date(year.value, month.value - 2, prevLastDay - i)
    const pLunar = solarToLunar(pdt.getFullYear(), pdt.getMonth() + 1, pdt.getDate())
    cells.push({ key: `p-${ds}`, day: prevLastDay - i, dateStr: ds, inMonth: false, isToday: false, events: [], lunar: pLunar.text, isFestival: !!pLunar.festival })
  }

  // 当月
  const todayStr = toLocalDateStr(today)
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const dt = new Date(year.value, month.value - 1, d)
    const ds = toLocalDateStr(dt)
    const evs = allEvents.value.filter(e => e.date === ds)
    const lunarData = solarToLunar(year.value, month.value, d)
    cells.push({ key: ds, day: d, dateStr: ds, inMonth: true, isToday: ds === todayStr, events: evs, lunar: lunarData.text, isFestival: !!lunarData.festival })
  }

  // 填充下月头（补足6行）
  const totalCells = Math.ceil(cells.length / 7) * 7
  let nextDay = 1
  while (cells.length < totalCells) {
    const dt = new Date(year.value, month.value, nextDay)
    const ds = toLocalDateStr(dt)
    const ndt = new Date(year.value, month.value, nextDay)
    const nLunar = solarToLunar(ndt.getFullYear(), ndt.getMonth() + 1, ndt.getDate())
    cells.push({ key: `n-${ds}`, day: nextDay, dateStr: ds, inMonth: false, isToday: false, events: [], lunar: nLunar.text, isFestival: !!nLunar.festival })
    nextDay++
  }

  return cells
})

// ─── 计算：周视图 ───
const weekDays = computed(() => {
  const base = selectedDate.value ? new Date(selectedDate.value + 'T00:00:00') : new Date()
  const dayOfWeek = base.getDay()
  const weekStart = new Date(base)
  weekStart.setDate(base.getDate() - dayOfWeek)

  const todayStr = toLocalDateStr(today)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart)
    d.setDate(weekStart.getDate() + i)
    const ds = toLocalDateStr(d)
    return {
      dateStr: ds,
      day: d.getDate(),
      weekDay: weekdays[i],
      isToday: ds === todayStr,
      events: allEvents.value.filter(e => e.date === ds),
    }
  })
})

// ─── 数据加载 ───
async function loadData() {
  loading.value = true
  try {
    const [evRes, staffRes] = await Promise.all([
      adminAPI.get(`/admin/calendar/month?year=${year.value}&month=${month.value}${selectedConsultant.value ? `&consultant_id=${selectedConsultant.value}` : ''}`),
      adminAPI.get(`/admin/calendar/consultants?year=${year.value}&month=${month.value}`),
    ])
    // http拦截器已自动解包 {code:0,data:X}→X
    // evRes 已是 {events:[...], total:N}  staffRes 已是 [...]
    console.log('[Calendar] evRes=', JSON.stringify(evRes).slice(0,200))
    console.log('[Calendar] staffRes=', JSON.stringify(staffRes).slice(0,200))
    allEvents.value = evRes?.events || evRes?.data?.events || []
    consultants.value = Array.isArray(staffRes) ? staffRes : (staffRes?.data || staffRes || [])
  } catch (e) {
    console.error('日历加载失败', e)
  } finally {
    loading.value = false
  }
}

async function loadDayEvents(dateStr: string) {
  try {
    const res = await adminAPI.get(`/admin/calendar/day?day=${dateStr}${selectedConsultant.value ? `&consultant_id=${selectedConsultant.value}` : ''}`)
    dayEvents.value = res?.events || res?.data?.events || []
  } catch (e) {
    dayEvents.value = []
  }
}

// ─── 导航 ───
function prevMonth() {
  if (month.value === 1) { month.value = 12; year.value-- }
  else month.value--
  loadData()
}

function nextMonth() {
  if (month.value === 12) { month.value = 1; year.value++ }
  else month.value++
  loadData()
}

function goToday() {
  year.value = today.getFullYear()
  month.value = today.getMonth() + 1
  loadData()
}

function selectDate(cell: any) {
  selectedDate.value = cell.dateStr
  loadDayEvents(cell.dateStr)
  if (viewMode.value !== 'month') viewMode.value = 'month'
}

function selectStaff(c: any) {
  selectedConsultant.value = c.consultant_id
  viewMode.value = 'month'
  loadData()
}

function openEvent(ev: any) {
  activeEvent.value = ev
}

function goToOrder(id: number) {
  router.push(`/service-orders/${id}`)
  activeEvent.value = null
}

onMounted(loadData)
</script>

<style scoped>
.calendar-page {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0d0d0d;
  color: #e8e0d0;
  font-family: 'Noto Serif SC', serif;
}

/* ── 工具栏 ── */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid #2a2a2a;
  background: #111;
}

.toolbar-left { display: flex; align-items: center; gap: 12px; }
.toolbar-right { display: flex; align-items: center; gap: 16px; }

.month-title { font-size: 20px; font-weight: 600; letter-spacing: 0.05em; color: #e8e0d0; min-width: 160px; text-align: center; }

.btn-icon {
  width: 32px; height: 32px; border: 1px solid #333;
  background: transparent; color: #c9a96e; font-size: 20px;
  border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.btn-icon:hover { background: #1e1e1e; border-color: #c9a96e; }
.btn-today {
  padding: 6px 14px; border: 1px solid #c9a96e; background: transparent;
  color: #c9a96e; border-radius: 6px; cursor: pointer; font-size: 13px;
}
.btn-today:hover { background: rgba(201, 169, 110, 0.1); }

.select-consultant {
  padding: 6px 12px; background: #1a1a1a; border: 1px solid #333;
  color: #e8e0d0; border-radius: 6px; font-size: 13px; cursor: pointer;
}

.view-tabs { display: flex; border: 1px solid #333; border-radius: 6px; overflow: hidden; }
.tab {
  padding: 6px 16px; background: transparent; color: #888;
  border: none; cursor: pointer; font-size: 13px;
}
.tab.active { background: #c9a96e; color: #0d0d0d; font-weight: 600; }

/* ── 老师概览 ── */
.staff-overview { padding: 24px; overflow-y: auto; flex: 1; }
.staff-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.staff-card {
  background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px;
  padding: 16px; display: flex; gap: 12px; cursor: pointer;
  transition: border-color 0.2s;
}
.staff-card:hover { border-color: #c9a96e; }
.staff-card.staff-busy { border-color: #6b2020; }
.staff-avatar {
  width: 48px; height: 48px; border-radius: 50%; background: #c9a96e;
  color: #0d0d0d; font-size: 20px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.staff-info { flex: 1; }
.staff-name { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.staff-stat { display: flex; gap: 12px; font-size: 12px; margin-bottom: 8px; }
.stat-busy { color: #e6a817; }
.stat-free { color: #52c41a; }
.staff-progress {}
.progress-bar { height: 4px; background: #2a2a2a; border-radius: 2px; margin-bottom: 4px; }
.progress-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
.progress-text { font-size: 11px; color: #666; }

/* ── 月视图 ── */
.calendar-grid { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.week-header { display: grid; grid-template-columns: repeat(7, 1fr); border-bottom: 1px solid #222; }
.week-cell { padding: 6px 0; text-align: center; font-size: 12px; color: #666; letter-spacing: 0.1em; }
.date-grid { flex: 1; display: grid; grid-template-columns: repeat(7, 1fr); grid-auto-rows: 1fr; overflow-y: auto; }

.date-cell {
  border-right: 1px solid #1a1a1a; border-bottom: 1px solid #1a1a1a;
  padding: 4px 6px; cursor: pointer; min-height: 0;
  transition: background 0.15s;
}
.date-cell:hover { background: #161616; }
.date-cell.other-month { opacity: 0.3; }
.date-cell.today { background: rgba(201, 169, 110, 0.08); }
.date-cell.today .date-num { color: #c9a96e; font-weight: 700; }
.date-cell.selected { background: rgba(201, 169, 110, 0.12); }

.date-num { font-size: 18px; font-weight: 600; color: #aaa; margin-bottom: 4px; display: flex; align-items: baseline; gap: 6px; }
.lunar-text { font-size: 11px; font-weight: 400; color: #666; }
.date-cell.today .lunar-text { color: #c9a96e; }
.lunar-festival { color: #e84c4c !important; font-weight: 500; }
.event-list { display: flex; flex-direction: column; gap: 3px; }
.event-chip {
  display: flex; align-items: center; gap: 4px;
  padding: 2px 6px; border-radius: 4px; font-size: 11px;
  color: #0d0d0d; cursor: pointer; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis;
}
.event-name { overflow: hidden; text-overflow: ellipsis; }
.event-more { font-size: 11px; color: #888; padding-left: 4px; }

/* ── 周视图 ── */
.week-view { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.week-header-row { display: grid; grid-template-columns: 60px repeat(7, 1fr); border-bottom: 1px solid #222; }
.time-col-header { }
.week-day-header { padding: 10px; text-align: center; }
.week-day-header.today .week-day-date { color: #c9a96e; font-weight: 700; }
.week-day-name { font-size: 11px; color: #666; }
.week-day-date { font-size: 20px; cursor: pointer; }
.week-body { display: grid; grid-template-columns: 60px repeat(7, 1fr); flex: 1; overflow-y: auto; position: relative; }
.time-col { display: flex; flex-direction: column; }
.time-slot-label { height: 60px; display: flex; align-items: flex-start; padding-top: 4px; font-size: 11px; color: #555; padding-left: 8px; }
.week-day-col { position: relative; border-left: 1px solid #1a1a1a; }
.week-time-cell { height: 60px; border-bottom: 1px solid #111; }
.week-event {
  position: absolute; left: 4px; right: 4px; top: 8px;
  border-radius: 6px; padding: 6px 8px; cursor: pointer; z-index: 1;
}
.we-title { font-size: 12px; font-weight: 600; color: #0d0d0d; }
.we-member { font-size: 11px; color: rgba(0,0,0,0.7); }
.we-consultant { font-size: 10px; color: rgba(0,0,0,0.5); }

/* ── 日视图抽屉 ── */
.day-drawer {
  position: fixed; right: 0; top: 0; bottom: 0; width: 360px;
  background: #111; border-left: 1px solid #2a2a2a;
  display: flex; flex-direction: column; z-index: 100;
  box-shadow: -4px 0 20px rgba(0,0,0,0.5);
}
.drawer-header {
  padding: 20px 24px; display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid #2a2a2a; font-size: 15px; font-weight: 600;
}
.drawer-body { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }

.day-event-card {
  background: #1a1a1a; border-radius: 10px; padding: 14px; cursor: pointer;
  transition: background 0.15s;
}
.day-event-card:hover { background: #222; }
.dec-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.dec-type { font-size: 12px; font-weight: 600; }
.dec-time { font-size: 11px; color: #666; flex: 1; }
.dec-status { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.dec-title { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.dec-meta { display: flex; flex-wrap: wrap; gap: 10px; font-size: 12px; color: #888; }
.dec-progress { margin-top: 10px; display: flex; align-items: center; gap: 8px; }
.dp-bar { flex: 1; height: 4px; background: #2a2a2a; border-radius: 2px; }
.dp-fill { height: 100%; background: #c9a96e; border-radius: 2px; }

/* ── 事件弹窗 ── */
.event-modal {
  position: fixed; inset: 0; background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal-box {
  background: #1a1a1a; border-radius: 16px; width: 440px;
  border: 1px solid #2a2a2a; overflow: hidden;
}
.modal-header {
  padding: 20px 24px; display: flex; align-items: center; gap: 12px;
  background: #111;
}
.modal-type { font-size: 14px; font-weight: 700; }
.modal-status { font-size: 12px; padding: 3px 10px; border-radius: 10px; margin-left: auto; }
.modal-body { padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; }
.modal-row { display: flex; gap: 12px; font-size: 14px; }
.modal-row label { color: #666; width: 70px; flex-shrink: 0; }
.modal-row span { color: #e8e0d0; }
.mono { font-family: monospace; font-size: 13px; }
.progress-row { align-items: center; }
.modal-progress { flex: 1; display: flex; align-items: center; gap: 10px; }
.mp-bar { flex: 1; height: 6px; background: #2a2a2a; border-radius: 3px; }
.mp-fill { height: 100%; background: #c9a96e; border-radius: 3px; }
.modal-footer { padding: 16px 24px; border-top: 1px solid #2a2a2a; }

/* ── 甘特图 ── */
.gantt-wrap {
  flex: 1; overflow: auto; padding: 16px 24px;
}
.gantt-table {
  min-width: max-content;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  overflow: hidden;
}
.gantt-header, .gantt-row {
  display: flex;
  align-items: stretch;
}
.gantt-header {
  background: #111;
  border-bottom: 1px solid #2a2a2a;
  position: sticky; top: 0; z-index: 10;
}
.gantt-name-col {
  width: 140px; min-width: 140px;
  padding: 10px 12px;
  border-right: 1px solid #2a2a2a;
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: #c9a96e; font-weight: 600;
  position: sticky; left: 0; background: #111; z-index: 5;
}
.gantt-day-header {
  width: 52px; min-width: 52px;
  text-align: center;
  padding: 6px 2px;
  border-right: 1px solid #1e1e1e;
  font-size: 11px;
}
.gd-num { font-size: 14px; font-weight: 600; color: #e8e0d0; }
.gd-week { font-size: 10px; color: #555; margin-top: 2px; }
.gd-today .gd-num { color: #c9a96e; }
.gd-today { background: rgba(201,169,110,0.06); }
.gd-weekend { background: rgba(255,255,255,0.02); }
.gd-weekend .gd-week { color: #7b6fdf; }

.gantt-row {
  border-bottom: 1px solid #1e1e1e;
  min-height: 52px;
}
.gantt-row:last-child { border-bottom: none; }
.gantt-row .gantt-name-col {
  background: #0d0d0d;
  color: #e8e0d0;
  font-weight: 400;
}
.gn-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: linear-gradient(135deg, #c9a96e, #7b6fdf);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #0d0d0d; flex-shrink: 0;
}
.gn-info { flex: 1; min-width: 0; }
.gn-name { font-size: 13px; font-weight: 600; color: #e8e0d0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gn-stat { font-size: 10px; color: #666; margin-top: 2px; }

.gantt-cell {
  width: 52px; min-width: 52px;
  border-right: 1px solid #1e1e1e;
  padding: 3px 2px;
  display: flex; flex-direction: column; gap: 2px;
  vertical-align: top;
}
.gc-today { background: rgba(201,169,110,0.06); }
.gc-weekend { background: rgba(255,255,255,0.015); }

.gantt-event {
  padding: 2px 5px;
  border-radius: 4px;
  cursor: pointer;
  display: flex; align-items: center; gap: 3px;
  opacity: 0.9;
  transition: opacity .15s;
}
.gantt-event:hover { opacity: 1; filter: brightness(1.15); }
.ge-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: rgba(255,255,255,0.6); flex-shrink: 0;
}
.ge-text {
  font-size: 10px; color: rgba(255,255,255,0.9);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 38px;
}

/* ── 状态色 ── */
.status-pending { background: rgba(230, 168, 23, 0.15); color: #e6a817; }
.status-confirmed { background: rgba(201, 169, 110, 0.15); color: #c9a96e; }
.status-in_progress { background: rgba(74, 144, 217, 0.15); color: #4a90d9; }
.status-completed { background: rgba(82, 196, 26, 0.15); color: #52c41a; }
.status-cancelled { background: rgba(153, 153, 153, 0.1); color: #999; }

/* ── 通用 ── */
.btn-close {
  width: 28px; height: 28px; border: 1px solid #333; background: transparent;
  color: #888; border-radius: 50%; cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
}
.btn-close:hover { color: #e84c4c; border-color: #e84c4c; }
.btn-primary {
  width: 100%; padding: 12px; background: #c9a96e; color: #0d0d0d;
  border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600;
}
.btn-primary:hover { background: #d4b87a; }

.loading-mask {
  position: absolute; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 300;
}
.spinner {
  width: 36px; height: 36px; border: 3px solid #333;
  border-top-color: #c9a96e; border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
