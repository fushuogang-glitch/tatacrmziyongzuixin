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
    rows.value = (await API.consultantList() as any) || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  dialog.mode = 'create';
  dialog.form = { name: '', phone: '', monthly_days: 14, course_days: 8, status: 'active' };
  dialog.visible = true;
}
function openEdit(row: any) {
  dialog.mode = 'edit';
  dialog.form = { ...row };
  dialog.visible = true;
}

async function submit() {
  const body = {
    name: dialog.form.name,
    phone: dialog.form.phone,
    monthly_days: dialog.form.monthly_days,
    course_days: dialog.form.course_days,
    status: dialog.form.status,
  };
  if (dialog.mode === 'create') {
    await API.consultantCreate(body);
    ElMessage.success('新增成功');
  } else {
    await API.consultantUpdate(dialog.form.id, body);
    ElMessage.success('保存成功');
  }
  dialog.visible = false;
  load();
}

function statusTag(s: string) {
  return { active: 'success', inactive: 'info' }[s] || '';
}

onMounted(load);
</script>

<template>
  <div>
    <el-card>
      <div class="toolbar">
        <el-button type="primary" @click="openCreate">新增顾问</el-button>
        <el-button @click="load">刷新</el-button>
      </div>

      <el-alert type="info" :closable="false" style="margin-top: 12px;"
        title="名额规则：每位顾问每月可下店次数 = (22工作日 - 课程日 - 2缓冲日) ÷ 2天 ≈ 6次" />

      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="phone" label="手机" width="140" />
        <el-table-column prop="monthly_days" label="每月可下店天数" width="150" />
        <el-table-column prop="course_days" label="每月课程占用" width="130" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增顾问' : '编辑顾问'" width="480px">
      <el-form :model="dialog.form" label-width="130px">
        <el-form-item label="姓名" required><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="手机"><el-input v-model="dialog.form.phone" /></el-form-item>
        <el-form-item label="每月可下店天数"><el-input-number v-model="dialog.form.monthly_days" :min="0" :max="31" /></el-form-item>
        <el-form-item label="每月课程占用"><el-input-number v-model="dialog.form.course_days" :min="0" :max="31" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="dialog.form.status">
            <el-option label="在岗" value="active" />
            <el-option label="停用" value="inactive" />
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
