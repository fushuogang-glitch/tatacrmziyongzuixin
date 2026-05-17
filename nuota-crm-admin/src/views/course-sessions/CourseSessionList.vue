<script setup lang="ts">
import { onMounted, onUnmounted, ref, reactive, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const sessions = ref<any[]>([]);
const services = ref<any[]>([]);
const members = ref<any[]>([]);
const loading = ref(false);
const filter = reactive({ status: '' });

// 场次弹窗
const dialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  form: {} as any,
});

// 报名列表弹窗
const enrollDialog = reactive({
  visible: false,
  session: null as any,
  enrollments: [] as any[],
  loading: false,
});

// 添加报名弹窗
const addEnrollDialog = reactive({
  visible: false,
  form: { member_id: null as number | null, price_type: 'normal' },
});

// 签到弹窗（手动选人签到）
const checkinDialog = reactive({
  visible: false,
  sessionId: 0,
  form: { member_id: null as number | null, day_number: 1, checkin_type: 'manual' },
});

// 跟进弹窗
const followupDialog = reactive({
  visible: false,
  enrollmentId: 0,
  form: { content: '', result: '', next_action: '' },
});

// ─── 扫脸签到 ───
const faceMode = ref(false);
const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const faceLoading = ref(false);
const faceResult = ref<any>(null);
const faceError = ref('');
const autoScan = ref(false);
let autoTimer: ReturnType<typeof setInterval> | null = null;
let stream: MediaStream | null = null;

// ─── 录脸弹窗 ───
const bindDialog = reactive({
  visible: false,
  memberId: null as number | null,
  loading: false,
});
const bindVideoRef = ref<HTMLVideoElement | null>(null);
const bindCanvasRef = ref<HTMLCanvasElement | null>(null);
let bindStream: MediaStream | null = null;

const filtered = computed(() => {
  return sessions.value.filter(s => {
    if (filter.status && s.status !== filter.status) return false;
    return true;
  });
});

async function load() {
  loading.value = true;
  try {
    const [s, svc, m]: any = await Promise.all([
      API.courseSessionList(),
      API.serviceList(),
      API.memberList({ page: 1, page_size: 500 }),
    ]);
    sessions.value = s || [];
    services.value = svc || [];
    members.value = (m?.items || m || []);
  } finally {
    loading.value = false;
  }
}

function statusLabel(s: string) {
  return { enrolling: '报名中', ongoing: '进行中', ended: '已结束', cancelled: '已取消' }[s] || s;
}
function statusType(s: string) {
  return { enrolling: 'success', ongoing: 'primary', ended: 'info', cancelled: 'danger' }[s] || '';
}
function fmtMoney(v: any) {
  if (!v && v !== 0) return '-';
  return parseFloat(v).toLocaleString('zh-CN');
}

function openCreate() {
  dialog.mode = 'create';
  dialog.form = {
    service_id: null, title: '', edition: 1,
    city: '', venue: '', start_date: '', end_date: '',
    duration_days: 3, capacity: 30,
    normal_price: null, trial_price: null,
    description: '',
    highlights: '',
    target_audience: '',
  };
  dialog.visible = true;
}

function openEdit(row: any) {
  dialog.mode = 'edit';
  dialog.form = { ...row };
  dialog.visible = true;
}

async function submitSession() {
  if (!dialog.form.service_id) { ElMessage.warning('请选择课程产品'); return; }
  if (!dialog.form.start_date) { ElMessage.warning('请选择开课日期'); return; }
  try {
    if (dialog.mode === 'create') {
      await API.courseSessionCreate(dialog.form);
      ElMessage.success('场次创建成功');
    } else {
      await API.courseSessionUpdate(dialog.form.id, dialog.form);
      ElMessage.success('保存成功');
    }
    dialog.visible = false;
    load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败');
  }
}

async function endSession(row: any) {
  await ElMessageBox.confirm(`确认结课「${row.title}」？\n结课后场次变灰，未成交客户自动进入跟进流程。`, '结课确认');
  await API.courseSessionEnd(row.id);
  ElMessage.success('已结课');
  load();
}

async function deleteSession(row: any) {
  await ElMessageBox.confirm(`确认删除「${row.title}」？`, '删除确认');
  await API.courseSessionDelete(row.id);
  ElMessage.success('已删除');
  load();
}

// ─── 报名管理 ───
async function openEnrollments(row: any) {
  enrollDialog.session = row;
  enrollDialog.loading = true;
  enrollDialog.visible = true;
  // 进入报名弹窗时关闭扫脸
  stopCamera();
  try {
    enrollDialog.enrollments = await API.courseSessionEnrollments(row.id) as any || [];
  } finally {
    enrollDialog.loading = false;
  }
}

function onEnrollDialogClose() {
  stopCamera();
}

function openAddEnroll() {
  addEnrollDialog.form = { member_id: null, price_type: 'normal' };
  addEnrollDialog.visible = true;
}

async function submitEnroll() {
  if (!addEnrollDialog.form.member_id) { ElMessage.warning('请选择会员'); return; }
  try {
    await API.courseSessionAddEnrollment(enrollDialog.session.id, addEnrollDialog.form);
    ElMessage.success('报名成功');
    addEnrollDialog.visible = false;
    openEnrollments(enrollDialog.session);
    load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '报名失败');
  }
}

// ─── 手动签到 ───
function openCheckin() {
  checkinDialog.sessionId = enrollDialog.session.id;
  checkinDialog.form = {
    member_id: null,
    day_number: 1,
    checkin_type: 'manual',
  };
  checkinDialog.visible = true;
}

async function submitCheckin() {
  if (!checkinDialog.form.member_id) { ElMessage.warning('请选择签到会员'); return; }
  try {
    await API.courseSessionCheckin(checkinDialog.sessionId, checkinDialog.form);
    ElMessage.success('签到成功');
    checkinDialog.visible = false;
    openEnrollments(enrollDialog.session);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '签到失败');
  }
}

// ─── 扫脸签到（集成在报名弹窗内）───
async function startCamera() {
  if (!enrollDialog.session?.id) { ElMessage.warning('请先打开一个场次'); return; }
  faceMode.value = true;
  faceResult.value = null;
  faceError.value = '';
  await new Promise(r => setTimeout(r, 200));
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: 640, height: 480 }
    });
    if (videoRef.value) {
      videoRef.value.srcObject = stream;
    }
  } catch (e: any) {
    faceError.value = '无法访问摄像头：' + (e.message || '请检查浏览器权限');
  }
}

function stopCamera() {
  stopAutoScan();
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  faceMode.value = false;
  faceResult.value = null;
  faceError.value = '';
}

async function captureAndCheckin() {
  if (!videoRef.value || !canvasRef.value || !enrollDialog.session?.id) return;
  faceLoading.value = true;
  faceResult.value = null;
  faceError.value = '';

  try {
    const video = videoRef.value;
    const canvas = canvasRef.value;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    const base64 = dataUrl.split(',')[1];

    // 调kiosk签到接口（传session_id用旧场次id，也兼容课程场次id）
    const res: any = await API.post('/api/checkin/kiosk', {
      session_id: enrollDialog.session.id,
      face_base64: base64,
      course_session: true,  // 标记是课程场次签到
    });
    const data = res?.data || res;
    faceResult.value = data;

    if (data?.repeat) {
      ElMessage.warning(data.msg || '今日已签到');
    } else {
      ElMessage.success(data?.msg || '签到成功！');
      // 刷新报名列表
      openEnrollments(enrollDialog.session);
    }

    setTimeout(() => { faceResult.value = null; }, 3500);
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.msg || e?.message || '识别失败';
    faceError.value = detail;
    ElMessage.error(detail);
    setTimeout(() => { faceError.value = ''; }, 2500);
  } finally {
    faceLoading.value = false;
  }
}

function startAutoScan() {
  autoScan.value = true;
  autoTimer = setInterval(() => {
    if (!faceLoading.value && !faceResult.value) {
      captureAndCheckin();
    }
  }, 3000);
}

function stopAutoScan() {
  autoScan.value = false;
  if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
}

// ─── 录脸 ───
async function openBindFace() {
  bindDialog.visible = true;
  bindDialog.memberId = null;
  bindDialog.loading = false;
  await new Promise(r => setTimeout(r, 200));
  try {
    bindStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: 640, height: 480 }
    });
    if (bindVideoRef.value) bindVideoRef.value.srcObject = bindStream;
  } catch (e: any) {
    ElMessage.error('无法打开摄像头: ' + (e.message || ''));
  }
}

function closeBindFace() {
  if (bindStream) { bindStream.getTracks().forEach(t => t.stop()); bindStream = null; }
  bindDialog.visible = false;
}

async function captureAndBind() {
  if (!bindDialog.memberId) { ElMessage.warning('请先选择学员'); return; }
  if (!bindVideoRef.value || !bindCanvasRef.value) return;
  bindDialog.loading = true;
  try {
    const video = bindVideoRef.value;
    const canvas = bindCanvasRef.value;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d')!.drawImage(video, 0, 0, canvas.width, canvas.height);
    const base64 = canvas.toDataURL('image/jpeg', 0.85).split(',')[1];

    const res: any = await API.post('/admin/checkins/bind-face', {
      member_id: bindDialog.memberId,
      face_base64: base64,
    });
    const data = res?.data || res;
    ElMessage.success(data?.msg || '人脸录入成功！');
    closeBindFace();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.msg || '录脸失败');
  } finally {
    bindDialog.loading = false;
  }
}

// ─── 确认付费 / 标记签单 / 跟进 ───
async function confirmPay(e: any) {
  await API.courseEnrollmentPay(e.id, { amount: e.paid_amount });
  ElMessage.success('已确认付费');
  openEnrollments(enrollDialog.session);
}

async function markDeal(e: any) {
  await API.courseEnrollmentDeal(e.id, {});
  ElMessage.success('已标记现场签单');
  openEnrollments(enrollDialog.session);
}

function openFollowup(e: any) {
  followupDialog.enrollmentId = e.id;
  followupDialog.form = { content: '', result: '', next_action: '' };
  followupDialog.visible = true;
}

async function submitFollowup() {
  await API.courseEnrollmentFollowup(followupDialog.enrollmentId, followupDialog.form);
  ElMessage.success('跟进记录已保存');
  followupDialog.visible = false;
  openEnrollments(enrollDialog.session);
}

function svcName(id: number) {
  const s = services.value.find((x: any) => x.id === id);
  return s ? s.name : '-';
}

onMounted(load);
onUnmounted(() => { stopCamera(); closeBindFace(); });
</script>

<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
      <div style="font-size:20px; font-weight:700;">📅 课程场次管理</div>
      <el-button type="primary" @click="openCreate">+ 创建场次</el-button>
    </div>

    <div style="display:flex; gap:12px; margin-bottom:16px;">
      <el-select v-model="filter.status" placeholder="状态筛选" clearable style="width:140px;">
        <el-option label="报名中" value="enrolling" />
        <el-option label="进行中" value="ongoing" />
        <el-option label="已结束" value="ended" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
    </div>

    <el-table :data="filtered" v-loading="loading" stripe border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="课程场次" min-width="200">
        <template #default="{ row }">
          <div style="font-weight:700;">{{ row.title }}</div>
          <div style="font-size:12px; color:#909399;">{{ svcName(row.service_id) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="城市/场地" min-width="150">
        <template #default="{ row }">
          <div>{{ row.city || '-' }}</div>
          <div style="font-size:12px; color:#909399;">{{ row.venue || '' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="日期" width="180">
        <template #default="{ row }">
          {{ row.start_date }} ~ {{ row.end_date }}
          <div style="font-size:12px; color:#909399;">{{ row.duration_days }}天</div>
        </template>
      </el-table-column>
      <el-table-column label="价格" width="150">
        <template #default="{ row }">
          <div style="color:#f56c6c; font-weight:600;">正常 ¥{{ fmtMoney(row.normal_price) }}</div>
          <div style="color:#e6a23c; font-size:12px;" v-if="row.trial_price">试听 ¥{{ fmtMoney(row.trial_price) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="报名" width="100" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEnrollments(row)">
            <span style="font-size:18px; font-weight:700;">{{ row.enrolled_count }}</span>
            <span style="color:#909399;">/{{ row.capacity }}</span>
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="签到" width="70" align="center">
        <template #default="{ row }">{{ row.checkin_count || 0 }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="自动化" width="120">
        <template #default="{ row }">
          <div style="font-size:11px;">
            <span :style="{ color: row.survey_sent ? '#67c23a' : '#c0c4cc' }">📋T-20</span>
            <span :style="{ color: row.ticket_remind_sent ? '#67c23a' : '#c0c4cc', marginLeft: '6px' }">✈️T-10</span>
            <span :style="{ color: row.notify_sent ? '#67c23a' : '#c0c4cc', marginLeft: '6px' }">📢T-5</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="warning" @click="endSession(row)" v-if="row.status === 'ongoing'">结课</el-button>
          <el-button link type="danger" @click="deleteSession(row)" v-if="row.enrolled_count === 0">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑场次弹窗 -->
    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '创建课程场次' : '编辑场次'" width="600px">
      <el-form :model="dialog.form" label-width="100px">
        <el-form-item label="课程产品">
          <el-select v-model="dialog.form.service_id" style="width:100%" filterable placeholder="选择关联的专案服务">
            <el-option v-for="s in services" :key="s.id" :value="s.id" :label="`${s.name} · ¥${s.price||0}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="场次名称"><el-input v-model="dialog.form.title" placeholder="第1期·三业运营实战课" /></el-form-item>
        <el-form-item label="期数"><el-input-number v-model="dialog.form.edition" :min="1" /></el-form-item>
        <div style="display:flex; gap:12px;">
          <el-form-item label="城市" style="flex:1"><el-input v-model="dialog.form.city" placeholder="武汉" /></el-form-item>
          <el-form-item label="天数"><el-input-number v-model="dialog.form.duration_days" :min="1" :max="30" /></el-form-item>
        </div>
        <el-form-item label="场地"><el-input v-model="dialog.form.venue" placeholder="武汉光谷万达嘉华酒店" /></el-form-item>
        <div style="display:flex; gap:12px;">
          <el-form-item label="开课日期" style="flex:1">
            <el-date-picker v-model="dialog.form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item>
          <el-form-item label="结课日期" style="flex:1">
            <el-date-picker v-model="dialog.form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item>
        </div>
        <el-form-item label="名额上限"><el-input-number v-model="dialog.form.capacity" :min="1" style="width:100%;" /></el-form-item>
        <div style="display:flex; gap:12px;">
          <el-form-item label="正常价格" style="flex:1"><el-input-number v-model="dialog.form.normal_price" :min="0" :step="1000" style="width:100%;" /></el-form-item>
          <el-form-item label="试听价格" style="flex:1"><el-input-number v-model="dialog.form.trial_price" :min="0" :step="100" style="width:100%;" /></el-form-item>
        </div>
        <el-form-item label="课程介绍"><el-input v-model="dialog.form.description" type="textarea" rows="3" /></el-form-item>
        <el-form-item label="课程亮点"><el-input v-model="dialog.form.highlights" type="textarea" rows="4" placeholder="每行一个亮点，格式：emoji,标题,描述
例如：
🎯,系统方法论,塔塔核心体系
👥,现场互动,案例研讨实操" /><div style="font-size:12px;color:#999;margin-top:4px;">每行一个亮点，用逗号分隔：emoji,标题,描述</div></el-form-item>
        <el-form-item label="适合人群"><el-input v-model="dialog.form.target_audience" type="textarea" rows="2" placeholder="每行一个，例如：
门店主
合伙人
店长" /><div style="font-size:12px;color:#999;margin-top:4px;">每行一个岗位/人群</div></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitSession">{{ dialog.mode === 'create' ? '创建' : '保存' }}</el-button>
      </template>
    </el-dialog>

    <!-- ═══ 报名管理弹窗（集成签到） ═══ -->
    <el-dialog v-model="enrollDialog.visible" :title="`${enrollDialog.session?.title || ''} — 报名 & 签到`"
      width="95%" top="3vh" @close="onEnrollDialogClose">

      <!-- 工具栏 -->
      <div style="display:flex; gap:10px; margin-bottom:16px; flex-wrap:wrap;">
        <el-button type="primary" @click="openAddEnroll">+ 添加报名</el-button>
        <el-button type="success" @click="startCamera" :disabled="faceMode">📷 扫脸签到</el-button>
        <el-button @click="openCheckin">✋ 手动签到</el-button>
        <el-button type="warning" @click="openBindFace">🙎 录入人脸</el-button>
      </div>

      <!-- ═══ 扫脸签到区域（嵌入报名弹窗内） ═══ -->
      <div v-if="faceMode" class="face-zone">
        <div class="face-header">
          <span class="face-title">🎯 扫脸签到 — {{ enrollDialog.session?.title }}</span>
          <div class="face-actions">
            <el-button v-if="!autoScan" type="warning" size="small" @click="startAutoScan">🔄 自动连续扫描</el-button>
            <el-button v-else type="info" size="small" @click="stopAutoScan">⏸ 停止自动</el-button>
            <el-button type="danger" size="small" @click="stopCamera">✕ 关闭摄像头</el-button>
          </div>
        </div>
        <div class="face-body">
          <div class="camera-wrap">
            <video ref="videoRef" autoplay playsinline muted class="camera-video"></video>
            <canvas ref="canvasRef" style="display:none;"></canvas>
            <!-- 扫描框 -->
            <div class="scan-overlay">
              <div class="scan-frame">
                <div class="corner tl"></div>
                <div class="corner tr"></div>
                <div class="corner bl"></div>
                <div class="corner br"></div>
                <div v-if="autoScan" class="scan-line"></div>
              </div>
            </div>
            <!-- 识别状态 -->
            <div v-if="faceLoading" class="face-status loading">
              <div class="spinner-sm"></div> 识别中...
            </div>
            <div v-else-if="faceResult && !faceResult.repeat" class="face-status success">
              ✅ {{ faceResult.member_name }} 签到成功（第{{ faceResult.day }}天）
            </div>
            <div v-else-if="faceResult && faceResult.repeat" class="face-status warning">
              ⚠️ {{ faceResult.member_name }} 今日已签到
            </div>
            <div v-else-if="faceError" class="face-status error">
              ❌ {{ faceError }}
            </div>
            <div v-else class="face-status hint">
              请学员正面看向摄像头
            </div>
          </div>
          <div v-if="!autoScan" class="capture-btn-wrap">
            <el-button type="primary" size="large" round :loading="faceLoading" @click="captureAndCheckin" style="width:200px;">
              📸 拍照签到
            </el-button>
          </div>
          <div v-else class="auto-hint">自动模式运行中，每3秒自动拍摄识别...</div>
        </div>
      </div>

      <!-- 报名清单 -->
      <el-table :data="enrollDialog.enrollments" v-loading="enrollDialog.loading" stripe border size="small" style="margin-top:12px;">
        <el-table-column label="会员" min-width="140">
          <template #default="{ row }">
            <div style="font-weight:600;">{{ row.member_name }}</div>
            <div style="font-size:11px; color:#409eff;">{{ row.enterprise_name }}</div>
            <div style="font-size:11px; color:#909399;">{{ row.member_phone }}</div>
          </template>
        </el-table-column>
        <el-table-column label="归属老师" width="90">
          <template #default="{ row }"><span style="color:#409eff;">{{ row.consultant_name || '-' }}</span></template>
        </el-table-column>
        <el-table-column label="价格类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.price_type === 'trial' ? 'warning' : 'primary'" size="small">
              {{ row.price_type === 'trial' ? '试听' : '正常' }}
            </el-tag>
            <div style="font-weight:600; color:#f56c6c;">¥{{ fmtMoney(row.paid_amount) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="付费" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.pay_status === 'paid'" type="success" size="small">已付</el-tag>
            <el-button v-else link type="warning" size="small" @click="confirmPay(row)">确认付费</el-button>
          </template>
        </el-table-column>
        <el-table-column label="签到" width="120">
          <template #default="{ row }">
            <span v-if="row.checkin_total">{{ row.checkin_total }}天</span>
            <span v-else style="color:#c0c4cc;">未签到</span>
            <div v-for="ci in (row.checkins||[])" :key="ci.id" style="font-size:10px; color:#909399;">
              Day{{ ci.day_number }} {{ ci.checkin_type === 'face' ? '🤳' : '✋' }}
              <span v-if="ci.face_score" style="color:#67c23a;">{{ ci.face_score }}分</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="{enrolled:'info',paid:'',checked_in:'success',completed:'primary',follow_up:'warning',closed:'danger'}[row.status]||''" size="small">
              {{ {enrolled:'已报名',paid:'已付费',checked_in:'已签到',completed:'已完成',follow_up:'跟进中',closed:'已关闭'}[row.status]||row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="签单" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.signed_deal" style="color:#67c23a; font-weight:700;">✅ 签单</span>
            <el-button v-else link type="success" size="small" @click="markDeal(row)">标记签单</el-button>
          </template>
        </el-table-column>
        <el-table-column label="跟进" min-width="160">
          <template #default="{ row }">
            <div>跟进{{ row.followup_count || 0 }}次</div>
            <div v-if="row.next_followup_date" style="font-size:11px; color:#e6a23c;">下次: {{ row.next_followup_date }}</div>
            <div v-for="f in (row.followups||[]).slice(0,2)" :key="f.id" style="font-size:10px; color:#606266; margin-top:2px;">
              {{ f.content?.slice(0, 30) }}{{ f.content?.length > 30 ? '...' : '' }}
            </div>
            <el-button link type="primary" size="small" @click="openFollowup(row)" style="margin-top:4px;">+ 跟进</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 添加报名弹窗 -->
    <el-dialog v-model="addEnrollDialog.visible" title="添加报名" width="400px">
      <el-form :model="addEnrollDialog.form" label-width="80px">
        <el-form-item label="会员">
          <el-select v-model="addEnrollDialog.form.member_id" filterable placeholder="搜索选择会员" style="width:100%">
            <el-option v-for="m in members" :key="m.id" :value="m.id" :label="`${m.name} · ${m.enterprise_name||''} · ${m.phone||''}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格类型">
          <el-radio-group v-model="addEnrollDialog.form.price_type">
            <el-radio value="normal">正常价 ¥{{ fmtMoney(enrollDialog.session?.normal_price) }}</el-radio>
            <el-radio value="trial">试听价 ¥{{ fmtMoney(enrollDialog.session?.trial_price) }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addEnrollDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitEnroll">确认报名</el-button>
      </template>
    </el-dialog>

    <!-- 手动签到弹窗 -->
    <el-dialog v-model="checkinDialog.visible" title="✋ 手动签到" width="420px">
      <el-form :model="checkinDialog.form" label-width="90px">
        <el-form-item label="选择学员">
          <el-select v-model="checkinDialog.form.member_id" filterable placeholder="搜索选择" style="width:100%">
            <el-option v-for="e in enrollDialog.enrollments" :key="e.member_id" :value="e.member_id" :label="`${e.member_name} · ${e.enterprise_name||''}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="签到天">
          <el-input-number v-model="checkinDialog.form.day_number" :min="1" :max="enrollDialog.session?.duration_days || 5" />
        </el-form-item>
        <el-form-item label="方式">
          <el-radio-group v-model="checkinDialog.form.checkin_type">
            <el-radio value="manual">✋ 手动</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkinDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitCheckin">确认签到</el-button>
      </template>
    </el-dialog>

    <!-- 跟进弹窗 -->
    <el-dialog v-model="followupDialog.visible" title="添加跟进记录" width="500px">
      <el-form :model="followupDialog.form" label-width="80px">
        <el-form-item label="跟进内容"><el-input v-model="followupDialog.form.content" type="textarea" rows="3" placeholder="和客户沟通了什么？" /></el-form-item>
        <el-form-item label="结果">
          <el-select v-model="followupDialog.form.result" placeholder="跟进结果" style="width:100%">
            <el-option label="有意向" value="interested" />
            <el-option label="暂不考虑" value="not_now" />
            <el-option label="明确拒绝" value="rejected" />
            <el-option label="已签单 🎉" value="signed" />
          </el-select>
        </el-form-item>
        <el-form-item label="下一步"><el-input v-model="followupDialog.form.next_action" placeholder="下次跟进计划" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="followupDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitFollowup">保存</el-button>
      </template>
    </el-dialog>

    <!-- 录脸弹窗 -->
    <el-dialog v-model="bindDialog.visible" title="🙎 录入学员人脸" width="560px" @close="closeBindFace">
      <div style="margin-bottom:16px;">
        <el-select v-model="bindDialog.memberId" filterable placeholder="搜索学员姓名/手机" style="width:100%;">
          <el-option v-for="m in members" :key="m.id" :value="m.id"
            :label="`${m.name}（${m.phone || m.member_no || ''}）`" />
        </el-select>
      </div>
      <div style="text-align:center; background:#000; border-radius:12px; overflow:hidden; position:relative;">
        <video ref="bindVideoRef" autoplay playsinline muted style="width:100%; display:block;"></video>
        <canvas ref="bindCanvasRef" style="display:none;"></canvas>
        <div style="position:absolute; bottom:12px; left:50%; transform:translateX(-50%); color:#aaa; font-size:13px; background:rgba(0,0,0,0.5); padding:4px 16px; border-radius:12px;">
          请学员正面看向摄像头
        </div>
      </div>
      <template #footer>
        <el-button @click="closeBindFace">取消</el-button>
        <el-button type="primary" :loading="bindDialog.loading" @click="captureAndBind">📸 拍照录入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ── 扫脸区域（嵌入报名弹窗内） ── */
.face-zone {
  background: #0d0d0d;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid #2a2a2a;
}
.face-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: #111;
  border-bottom: 1px solid #2a2a2a;
}
.face-title { color: #c9a96e; font-size: 15px; font-weight: 600; }
.face-actions { display: flex; gap: 8px; }

.face-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.camera-wrap {
  position: relative;
  width: 420px;
  max-width: 100%;
  border-radius: 12px;
  overflow: hidden;
  background: #000;
}
.camera-video {
  width: 100%;
  display: block;
  border-radius: 12px;
}

.scan-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.scan-frame {
  width: 200px; height: 240px;
  position: relative;
  border: 2px solid rgba(201, 169, 110, 0.4);
  border-radius: 16px;
}
.corner {
  position: absolute;
  width: 24px; height: 24px;
  border-color: #c9a96e;
  border-style: solid;
}
.tl { top: -2px; left: -2px; border-width: 3px 0 0 3px; border-radius: 8px 0 0 0; }
.tr { top: -2px; right: -2px; border-width: 3px 3px 0 0; border-radius: 0 8px 0 0; }
.bl { bottom: -2px; left: -2px; border-width: 0 0 3px 3px; border-radius: 0 0 0 8px; }
.br { bottom: -2px; right: -2px; border-width: 0 3px 3px 0; border-radius: 0 0 8px 0; }

.scan-line {
  position: absolute;
  left: 10%; right: 10%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #c9a96e, transparent);
  animation: scanMove 2s ease-in-out infinite;
}
@keyframes scanMove {
  0% { top: 10%; }
  50% { top: 85%; }
  100% { top: 10%; }
}

.face-status {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  backdrop-filter: blur(8px);
  white-space: nowrap;
}
.face-status.hint { background: rgba(0,0,0,0.5); color: #aaa; }
.face-status.loading { background: rgba(201,169,110,0.2); color: #c9a96e; display: flex; align-items: center; gap: 8px; }
.face-status.success { background: rgba(82,196,26,0.2); color: #52c41a; font-size: 16px; }
.face-status.warning { background: rgba(230,162,60,0.2); color: #e6a23c; }
.face-status.error { background: rgba(245,108,108,0.2); color: #f56c6c; }

.spinner-sm {
  width: 16px; height: 16px;
  border: 2px solid rgba(201,169,110,0.3);
  border-top-color: #c9a96e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.capture-btn-wrap { margin-top: 16px; }
.auto-hint { margin-top: 12px; color: #c9a96e; font-size: 13px; }
</style>
