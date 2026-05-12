<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const sessions = ref<any[]>([]);
const currentSid = ref<number | null>(null);
const rows = ref<any[]>([]);
const loading = ref(false);
const manualDialog = reactive({ visible: false, form: { member_id: 0, session_id: 0, checkin_day: 1 } });

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

function openManual() {
  manualDialog.form = { member_id: 0, session_id: currentSid.value || 0, checkin_day: 1 };
  manualDialog.visible = true;
}

async function submitManual() {
  const f = manualDialog.form;
  if (!f.member_id || !f.session_id || !f.checkin_day) {
    ElMessage.warning('请完整填写');
    return;
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

onMounted(async () => { await loadSessions(); await loadCheckins(); });
</script>

<template>
  <div>
    <el-card>
      <div class="toolbar">
        <el-select v-model="currentSid" placeholder="选择场次" style="width: 260px;">
          <el-option v-for="s in sessions" :key="s.id" :value="s.id" :label="`${s.session_no}（${s.start_date} · ${s.city || ''}）`" />
        </el-select>
        <el-button @click="loadCheckins">刷新</el-button>
        <el-button type="primary" @click="openManual">手动签到</el-button>
      </div>

      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="member_no" label="学员编号" width="140" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="phone" label="手机" width="130" />
        <el-table-column label="打卡日" width="100">
          <template #default="{ row }">Day {{ row.checkin_day }}</template>
        </el-table-column>
        <el-table-column label="方式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.method === 'face' ? 'success' : 'info'">
              {{ row.method === 'face' ? '刷脸' : '手动' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间">
          <template #default="{ row }">{{ fmt(row.checkin_time) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="manualDialog.visible" title="手动签到" width="400px">
      <el-form :model="manualDialog.form" label-width="90px">
        <el-form-item label="学员ID" required>
          <el-input-number v-model="manualDialog.form.member_id" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="场次ID" required>
          <el-input-number v-model="manualDialog.form.session_id" :min="1" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="打卡日" required>
          <el-select v-model="manualDialog.form.checkin_day" style="width: 100%;">
            <el-option :value="1" label="Day 1" />
            <el-option :value="2" label="Day 2" />
            <el-option :value="3" label="Day 3" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitManual">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; }
</style>
