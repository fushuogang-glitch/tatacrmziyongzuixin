<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);
const total = ref(0);
const query = reactive({ page: 1, size: 50, target_type: '' });

const typeOptions = [
  { label: '全部', value: '' },
  { label: '👤 客户', value: 'member' },
  { label: '👩‍🏫 老师', value: 'consultant' },
  { label: '📅 排期', value: 'schedule' },
];

async function load() {
  loading.value = true;
  try {
    const params: any = { page: query.page, size: query.size };
    if (query.target_type) params.target_type = query.target_type;
    const d: any = await API.recycleBin(params);
    rows.value = d.items || [];
    total.value = d.total || 0;
  } finally {
    loading.value = false;
  }
}

async function restore(row: any) {
  try {
    await ElMessageBox.confirm(
      `确认恢复「${row.target_name}」？恢复后将回到原位置。`,
      '♻️ 恢复确认',
      { confirmButtonText: '确认恢复', cancelButtonText: '取消', type: 'info' }
    );
    await API.recycleRestore(row.id);
    ElMessage.success(`${row.target_name} 已恢复`);
    load();
  } catch {}
}

function typeIcon(t: string) {
  const m: Record<string, string> = {
    member: '👤', consultant: '👩‍🏫', schedule: '📅',
    service_order: '📋', payment: '💰',
  };
  return m[t] || '📌';
}

function typeName(t: string) {
  const m: Record<string, string> = {
    member: '客户', consultant: '老师', schedule: '排期',
    service_order: '工单', payment: '缴费',
  };
  return m[t] || t;
}

function fmt(v: string) {
  if (!v) return '-';
  return v.replace('T', ' ').slice(0, 19);
}

onMounted(() => load());
</script>

<template>
  <div>
    <el-card>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <div style="font-size:20px; font-weight:700;">🗑️ 回收站</div>
        <div style="display:flex; gap:10px;">
          <el-select v-model="query.target_type" placeholder="类别筛选" clearable style="width:140px;" @change="load">
            <el-option v-for="o in typeOptions" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
        </div>
      </div>

      <el-empty v-if="!loading && rows.length === 0" description="回收站是空的 ✨" :image-size="80" />

      <el-table v-else :data="rows" v-loading="loading" stripe size="small">
        <el-table-column label="类别" width="100">
          <template #default="{ row }">
            <span>{{ typeIcon(row.target_type) }} {{ typeName(row.target_type) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="名称" min-width="200" prop="target_name" />
        <el-table-column label="删除人" width="100" prop="deleted_by_name" />
        <el-table-column label="删除时间" width="170">
          <template #default="{ row }">{{ fmt(row.deleted_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="restore(row)">♻️ 恢复</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination v-if="total > query.size"
        style="margin-top:16px; display:flex; justify-content:flex-end;"
        v-model:current-page="query.page" v-model:page-size="query.size"
        :total="total" :page-sizes="[20, 50]" layout="total, prev, pager, next"
        @current-change="load" @size-change="load"
      />
    </el-card>
  </div>
</template>
