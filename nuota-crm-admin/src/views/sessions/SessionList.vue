<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);
const dialog = reactive({ visible: false, mode: 'create' as 'create' | 'edit', form: {} as any });

async function load() {
  loading.value = true;
  try {
    rows.value = (await API.sessionList() as any) || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  dialog.mode = 'create';
  dialog.form = { session_no: '', start_date: '', end_date: '', location: '', city: '', capacity: 100, status: 'open' };
  dialog.visible = true;
}
function openEdit(row: any) {
  dialog.mode = 'edit';
  dialog.form = { ...row };
  dialog.visible = true;
}

async function submit() {
  const body = { ...dialog.form };
  if (dialog.mode === 'create') {
    await API.sessionCreate(body);
    ElMessage.success('新建成功');
  } else {
    await API.sessionUpdate(body.id, body);
    ElMessage.success('保存成功');
  }
  dialog.visible = false;
  load();
}

async function changeStatus(row: any, v: string) {
  await API.sessionStatus(row.id, v);
  ElMessage.success('已更新');
  load();
}

function statusTag(s: string) {
  return { open: 'success', full: 'warning', closed: 'info', finished: '' }[s] || '';
}
function statusLabel(s: string) {
  return { open: '报名中', full: '已满', closed: '已关闭', finished: '已结束' }[s] || s;
}

onMounted(load);
</script>

<template>
  <div>
    <el-card>
      <div class="toolbar">
        <el-button type="primary" @click="openCreate">新建场次</el-button>
        <el-button @click="load">刷新</el-button>
      </div>
      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="session_no" label="期号" width="140" />
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120" />
        <el-table-column prop="location" label="场地" min-width="180" />
        <el-table-column prop="city" label="城市" width="100" />
        <el-table-column label="报名进度" width="140">
          <template #default="{ row }">
            {{ row.enrolled }} / {{ row.capacity }}
            <el-progress :percentage="Math.min(100, Math.round((row.enrolled / row.capacity) * 100))" :show-text="false" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="changeStatus(row, 'closed')" v-if="row.status !== 'closed'">关闭</el-button>
            <el-button link type="success" @click="changeStatus(row, 'open')" v-if="row.status !== 'open'">开放</el-button>
            <el-button link type="info" @click="changeStatus(row, 'finished')" v-if="row.status !== 'finished'">结束</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新建场次' : '编辑场次'" width="520px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="期号" required><el-input v-model="dialog.form.session_no" placeholder="如 2026-07-001" /></el-form-item>
        <el-form-item label="开始日期"><el-date-picker v-model="dialog.form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" /></el-form-item>
        <el-form-item label="结束日期"><el-date-picker v-model="dialog.form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" /></el-form-item>
        <el-form-item label="场地"><el-input v-model="dialog.form.location" /></el-form-item>
        <el-form-item label="城市"><el-input v-model="dialog.form.city" /></el-form-item>
        <el-form-item label="容量"><el-input-number v-model="dialog.form.capacity" :min="1" :step="10" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="dialog.form.status">
            <el-option label="报名中" value="open" />
            <el-option label="已满" value="full" />
            <el-option label="已关闭" value="closed" />
            <el-option label="已结束" value="finished" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; }
</style>
