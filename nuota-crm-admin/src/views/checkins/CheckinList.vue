<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const sessions = ref<any[]>([]);
const currentSid = ref<number | null>(null);
const rows = ref<any[]>([]);
const loading = ref(false);

// 扫脸签到
const faceMode = ref(false);
const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const faceLoading = ref(false);
const faceResult = ref<any>(null);
const faceError = ref('');
const autoScan = ref(false);
let autoTimer: ReturnType<typeof setInterval> | null = null;
let stream: MediaStream | null = null;

// 手动签到弹窗
const manualDialog = reactive({ visible: false, form: { member_id: 0, session_id: 0, checkin_day: 1 } });
const memberOptions = ref<any[]>([]);

// 录脸弹窗
const bindDialog = reactive({
  visible: false,
  memberId: null as number | null,
  loading: false,
});
const bindVideoRef = ref<HTMLVideoElement | null>(null);
const bindCanvasRef = ref<HTMLCanvasElement | null>(null);
let bindStream: MediaStream | null = null;

async function loadSessions() {
  sessions.value = (await API.sessionList() as any) || [];
  if (sessions.value.length && !currentSid.value) {
    currentSid.value = sessions.value[0].id;
  }
}

async function loadCheckins() {
  if (!currentSid.value) return;
  loading.value = true;
  try {
    rows.value = (await API.checkinList(currentSid.value) as any) || [];
  } finally {
    loading.value = false;
  }
}

watch(currentSid, loadCheckins);

// ─── 摄像头控制 ───
async function startCamera() {
  faceMode.value = true;
  faceResult.value = null;
  faceError.value = '';
  await new Promise(r => setTimeout(r, 100)); // 等DOM渲染
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

// ─── 拍照+识别 ───
async function captureAndCheckin() {
  if (!videoRef.value || !canvasRef.value || !currentSid.value) return;
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

    // 转base64（去掉data:image/jpeg;base64,前缀）
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    const base64 = dataUrl.split(',')[1];

    // 调kiosk签到接口
    const res: any = await API.post('/api/checkin/kiosk', {
      session_id: currentSid.value,
      face_base64: base64,
    });

    // 接口返回直接是data（拦截器解包）
    const data = res?.data || res;
    faceResult.value = data;

    if (data?.repeat) {
      ElMessage.warning(data.msg || '今日已签到');
    } else {
      ElMessage.success(data?.msg || '签到成功！');
      loadCheckins();
    }

    // 签到成功后3秒自动清除结果，准备下一位
    setTimeout(() => {
      faceResult.value = null;
    }, 3500);

  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.msg || e?.message || '识别失败';
    faceError.value = detail;
    ElMessage.error(detail);
    // 失败后2秒清除错误，继续扫描
    setTimeout(() => { faceError.value = ''; }, 2500);
  } finally {
    faceLoading.value = false;
  }
}

// ─── 自动连续扫描 ───
function startAutoScan() {
  autoScan.value = true;
  autoTimer = setInterval(() => {
    if (!faceLoading.value && !faceResult.value) {
      captureAndCheckin();
    }
  }, 3000); // 每3秒自动拍一张
}

function stopAutoScan() {
  autoScan.value = false;
  if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
}

// ─── 手动签到 ───
async function loadMembers() {
  try {
    const res: any = await API.memberList({ limit: 200 });
    memberOptions.value = (res?.items || res || []);
  } catch { memberOptions.value = []; }
}

function openManual() {
  manualDialog.form = { member_id: 0, session_id: currentSid.value || 0, checkin_day: 1 };
  manualDialog.visible = true;
  loadMembers();
}

async function submitManual() {
  const f = manualDialog.form;
  if (!f.member_id || !f.session_id || !f.checkin_day) {
    ElMessage.warning('请完整填写'); return;
  }
  await API.manualCheckin(f.member_id, f.session_id, f.checkin_day);
  ElMessage.success('签到已记录');
  manualDialog.visible = false;
  loadCheckins();
}

function fmt(v: any) {
  if (!v) return '-';
  return String(v).replace('T', ' ').slice(0, 19);
}

// ─── 录脸 ───
async function openBindFace() {
  bindDialog.visible = true;
  bindDialog.memberId = null;
  bindDialog.loading = false;
  await loadMembers();
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

onMounted(async () => { await loadSessions(); await loadCheckins(); });
onUnmounted(() => { stopCamera(); });
</script>

<template>
  <div class="checkin-page">
    <!-- 顶部工具栏 -->
    <div class="top-bar">
      <div class="title-row">
        <span class="page-title">📋 签到管理</span>
      </div>
      <div class="toolbar">
        <el-select v-model="currentSid" placeholder="选择场次" style="width: 280px;">
          <el-option v-for="s in sessions" :key="s.id" :value="s.id"
            :label="`${s.session_no}（${s.start_date} · ${s.city || ''}）`" />
        </el-select>
        <el-button @click="loadCheckins">刷新</el-button>
        <el-button type="success" @click="startCamera" :disabled="faceMode">
          📷 扫脸签到
        </el-button>
        <el-button type="primary" @click="openManual">✍️ 手动签到</el-button>
        <el-button type="warning" @click="openBindFace">🙎 录入人脸</el-button>
      </div>
    </div>

    <!-- 扫脸签到区域 -->
    <div v-if="faceMode" class="face-zone">
      <div class="face-header">
        <span class="face-title">🎯 扫脸签到模式</span>
        <div class="face-actions">
          <el-button v-if="!autoScan" type="warning" size="small" @click="startAutoScan">
            🔄 自动连续扫描
          </el-button>
          <el-button v-else type="info" size="small" @click="stopAutoScan">
            ⏸ 停止自动
          </el-button>
          <el-button type="danger" size="small" @click="stopCamera">✕ 关闭摄像头</el-button>
        </div>
      </div>

      <div class="face-body">
        <!-- 摄像头画面 -->
        <div class="camera-wrap">
          <video ref="videoRef" autoplay playsinline muted class="camera-video"></video>
          <canvas ref="canvasRef" style="display:none;"></canvas>

          <!-- 扫描框动画 -->
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

        <!-- 手动拍照按钮（非自动模式） -->
        <div v-if="!autoScan" class="capture-btn-wrap">
          <el-button type="primary" size="large" round :loading="faceLoading"
            @click="captureAndCheckin" style="width:200px;">
            📸 拍照签到
          </el-button>
        </div>
        <div v-else class="auto-hint">
          自动模式运行中，每3秒自动拍摄识别...
        </div>
      </div>
    </div>

    <!-- 签到记录表 -->
    <el-card style="margin-top: 16px;">
      <template #header>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span>签到记录</span>
          <el-tag type="info" size="small">共 {{ rows.length }} 条</el-tag>
        </div>
      </template>
      <el-table :data="rows" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="member_no" label="学员编号" width="130" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="phone" label="手机" width="130" />
        <el-table-column label="打卡日" width="90">
          <template #default="{ row }">
            <el-tag size="small">Day {{ row.checkin_day }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="方式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.method?.includes('face') ? 'success' : 'info'" size="small">
              {{ row.method?.includes('face') ? '🤖 刷脸' : '✍️ 手动' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="签到时间">
          <template #default="{ row }">{{ fmt(row.checkin_time) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 手动签到弹窗 -->
    <el-dialog v-model="manualDialog.visible" title="✍️ 手动签到" width="440px">
      <el-form :model="manualDialog.form" label-width="90px">
        <el-form-item label="选择学员" required>
          <el-select v-model="manualDialog.form.member_id" filterable placeholder="搜索学员姓名/手机" style="width:100%;">
            <el-option v-for="m in memberOptions" :key="m.id" :value="m.id"
              :label="`${m.name}（${m.phone || m.member_no || ''}）`" />
          </el-select>
        </el-form-item>
        <el-form-item label="场次">
          <el-select v-model="manualDialog.form.session_id" style="width:100%;" disabled>
            <el-option v-for="s in sessions" :key="s.id" :value="s.id"
              :label="`${s.session_no}（${s.start_date}）`" />
          </el-select>
        </el-form-item>
        <el-form-item label="打卡日" required>
          <el-select v-model="manualDialog.form.checkin_day" style="width: 100%;">
            <el-option :value="1" label="Day 1 · 第一天" />
            <el-option :value="2" label="Day 2 · 第二天" />
            <el-option :value="3" label="Day 3 · 第三天" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitManual">确认签到</el-button>
      </template>
    </el-dialog>

    <!-- 录脸弹窗 -->
    <el-dialog v-model="bindDialog.visible" title="🙎 录入学员人脸" width="560px" @close="closeBindFace">
      <div style="margin-bottom:16px;">
        <el-select v-model="bindDialog.memberId" filterable placeholder="搜索学员姓名/手机" style="width:100%;">
          <el-option v-for="m in memberOptions" :key="m.id" :value="m.id"
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
        <el-button type="primary" :loading="bindDialog.loading" @click="captureAndBind">
          📸 拍照录入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.checkin-page { padding: 0; }
.top-bar { margin-bottom: 16px; }
.page-title { font-size: 18px; font-weight: 700; }
.toolbar { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }

/* ── 扫脸区域 ── */
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
  width: 480px;
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

/* 扫描框 */
.scan-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.scan-frame {
  width: 220px; height: 260px;
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

/* 识别状态 */
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
