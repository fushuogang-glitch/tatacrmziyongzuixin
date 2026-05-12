<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const status = ref('');
const rows = ref<any[]>([]);
const loading = ref(false);
const consultants = ref<any[]>([]);

const confirmDialog = reactive({ visible: false, bid: 0, form: { consultant_id: 0 as number | null, confirmed_date: '' } });
const completeDialog = reactive({ visible: false, bid: 0, form: { member_rating: 5 as number | null } });

async function load() {
  loading.value = true;
  try {
    rows.value = (await API.bookingList(status.value || undefined) as any) || [];
  } finally {
    loading.value = false;
  }
}

async function loadConsultants() {
  consultants.value = (await API.consultantList() as any) || [];
}

function openConfirm(row: any) {
  confirmDialog.bid = row.id;
  confirmDialog.form = { consultant_id: null, confirmed_date: row.preferred_date || '' };
  confirmDialog.visible = true;
}
async function submitConfirm() {
  if (!confirmDialog.form.consultant_id || !confirmDialog.form.confirmed_date) {
    ElMessage.warning('请完整填写');
    return;
  }
  await API.bookingConfirm(confirmDialog.bid, confirmDialog.form);
  ElMessage.success('预约已确认');
  confirmDialog.visible = false;
  load();
}

function openComplete(row: any) {
  completeDialog.bid = row.id;
  completeDialog.form = { member_rating: 5 };
  completeDialog.visible = true;
}
async function submitComplete() {
  await API.bookingComplete(completeDialog.bid, completeDialog.form);
  ElMessage.success('已标记完成');
  completeDialog.visible = false;
  load();
}

async function cancel(row: any) {
  await ElMessageBox.confirm(`取消预约 #${row.id}？权益将回退为可用。`, '提示', { type: 'warning' });
  await API.bookingCancel(row.id);
  ElMessage.success('已取消');
  load();
}

function statusTag(s: string) {
  return { pending: 'warning', confirmed: 'success', completed: 'info', cancelled: 'danger' }[s] || '';
}

function fmt(v: any) {
  if (!v) return '-';
  return String(v).replace('T', ' ').slice(0, 19);
}

onMounted(async () => { await loadConsultants(); await load(); });
</script>

<template>
  <div>
    <el-card>
      <div class="toolbar">
        <el-select v-model="status" placeholder="状态筛选" clearable style="width: 160px;" @change="load">
          <el-option label="待确认" value="pending" />
          <el-option label="已确认" value="confirmed" />
          <el-option label="已完成" value="completed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-button @click="load">刷新</el-button>
      </div>
      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="学员" min-width="180">
          <template #default="{ row }">
            {{ row.member?.name }} · {{ row.member?.phone }}
          </template>
        </el-table-column>
        <el-table-column prop="city" label="城市" width="100" />
        <el-table-column prop="address" label="地址" min-width="180" />
        <el-table-column prop="preferred_date" label="期望日期" width="120" />
        <el-table-column prop="confirmed_date" label="确认日期" width="120" />
        <el-table-column prop="consultant_id" label="顾问ID" width="90" />
        <el-table-column prop="duration_days" label="天数" width="70" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="member_rating" label="评分" width="70" />
        <el-table-column label="申请时间" width="170">
          <template #default="{ row }">{{ fmt(row.apply_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="240">
          <template #default="{ row }">
            <el-button link type="primary" v-if="row.status === 'pending'" @click="openConfirm(row)">确认+排顾问</el-button>
            <el-button link type="success" v-if="row.status === 'confirmed'" @click="openComplete(row)">标记完成</el-button>
            <el-button link type="danger" v-if="row.status !== 'completed' && row.status !== 'cancelled'" @click="cancel(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="confirmDialog.visible" title="确认预约" width="420px">
      <el-form :model="confirmDialog.form" label-width="90px">
        <el-form-item label="顾问" required>
          <el-select v-model="confirmDialog.form.consultant_id" style="width: 100%;">
            <el-option v-for="c in consultants" :key="c.id" :value="c.id" :label="`${c.name}（${c.phone || ''}）`" />
          </el-select>
        </el-form-item>
        <el-form-item label="确认日期" required>
          <el-date-picker v-model="confirmDialog.form.confirmed_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitConfirm">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="completeDialog.visible" title="标记完成" width="400px">
      <el-form :model="completeDialog.form" label-width="90px">
        <el-form-item label="学员评分">
          <el-rate v-model="completeDialog.form.member_rating" :max="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="completeDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitComplete">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; }
</style>
