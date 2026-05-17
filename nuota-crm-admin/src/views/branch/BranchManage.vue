<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);
const filterStatus = ref('');

const dialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  form: {} as any,
});

async function load() {
  loading.value = true;
  try {
    rows.value = (await API.branchList(filterStatus.value || undefined) as any) || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  dialog.mode = 'create';
  dialog.form = {
    name: '', short_name: '', city: '',
    address: '', contact_name: '', contact_phone: '',
    established_date: '', status: 'active', remark: '',
  };
  dialog.visible = true;
}

function openEdit(row: any) {
  dialog.mode = 'edit';
  dialog.form = { ...row };
  dialog.visible = true;
}

async function submit() {
  if (!dialog.form.name) { ElMessage.warning('分公司名称必填'); return; }
  if (dialog.mode === 'create') {
    await API.branchCreate(dialog.form);
    ElMessage.success('新增成功');
  } else {
    await API.branchUpdate(dialog.form.id, dialog.form);
    ElMessage.success('保存成功');
  }
  dialog.visible = false;
  load();
}

async function closeBranch(row: any) {
  await ElMessageBox.confirm(`确认关闭「${row.name}」？关闭后仍可重新激活。`, '提示', { type: 'warning' });
  await API.branchDelete(row.id);
  ElMessage.success('已关闭');
  load();
}

async function reactivate(row: any) {
  await API.branchUpdate(row.id, { status: 'active' });
  ElMessage.success('已重新激活');
  load();
}

function statusTag(s: string) {
  return s === 'active' ? 'success' : 'info';
}
function statusLabel(s: string) {
  return s === 'active' ? '运营中' : '已关闭';
}

onMounted(load);
</script>

<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
      <div style="font-size:20px; font-weight:700;">🏢 分公司管理</div>
      <el-button type="primary" @click="openCreate">+ 新增分公司</el-button>
    </div>

    <div style="display:flex; gap:12px; margin-bottom:16px;">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width:130px;" @change="load">
        <el-option label="运营中" value="active" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <span style="color:#909399; line-height:32px;">共 {{ rows.length }} 家</span>
    </div>

    <el-table :data="rows" v-loading="loading" stripe border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="分公司名称" min-width="160">
        <template #default="{ row }">
          <div style="font-weight:600;">{{ row.name }}</div>
          <div style="font-size:12px; color:#909399;">{{ row.short_name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="city" label="城市" width="100" />
      <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />
      <el-table-column label="负责人" width="130">
        <template #default="{ row }">
          <div>{{ row.contact_name || '-' }}</div>
          <div style="font-size:12px; color:#909399;">{{ row.contact_phone || '' }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="established_date" label="成立日期" width="110" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'active'" link type="danger" @click="closeBranch(row)">关闭</el-button>
          <el-button v-else link type="success" @click="reactivate(row)">激活</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增分公司' : '编辑分公司'" width="520px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="分公司名称" required>
          <el-input v-model="dialog.form.name" placeholder="如：塔塔咨询上海分公司" />
        </el-form-item>
        <el-form-item label="简称">
          <el-input v-model="dialog.form.short_name" placeholder="如：上海" />
        </el-form-item>
        <el-form-item label="城市">
          <el-input v-model="dialog.form.city" placeholder="所在城市" />
        </el-form-item>
        <el-form-item label="详细地址">
          <el-input v-model="dialog.form.address" placeholder="详细地址" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="dialog.form.contact_name" placeholder="负责人姓名" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="dialog.form.contact_phone" placeholder="负责人手机" />
        </el-form-item>
        <el-form-item label="成立日期">
          <el-date-picker v-model="dialog.form.established_date" type="date"
            value-format="YYYY-MM-DD" placeholder="选择成立日期" style="width:100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="dialog.form.status">
            <el-radio value="active">运营中</el-radio>
            <el-radio value="closed">已关闭</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dialog.form.remark" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
