<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);
const total = ref(0);
const query = reactive({ page: 1, size: 50, target_type: '' });

const typeOptions = [
  { label: '全部', value: '' },
  { label: '👤 客户', value: 'member' },
  { label: '👩‍🏫 老师', value: 'consultant' },
  { label: '📋 工单', value: 'service_order' },
  { label: '📅 排期', value: 'schedule' },
  { label: '💰 缴费', value: 'payment' },
  { label: '🔑 账号', value: 'admin_user' },
];

async function load() {
  loading.value = true;
  try {
    const params: any = { page: query.page, size: query.size };
    if (query.target_type) params.target_type = query.target_type;
    const d: any = await API.operationLogs(params);
    rows.value = d.items || [];
    total.value = d.total || 0;
  } finally {
    loading.value = false;
  }
}

function typeIcon(t: string) {
  const m: Record<string, string> = {
    member: '👤', consultant: '👩‍🏫', service_order: '📋',
    schedule: '📅', payment: '💰', admin_user: '🔑',
  };
  return m[t] || '📌';
}

function actionColor(a: string) {
  if (a.includes('新增') || a.includes('创建')) return '#67c23a';
  if (a.includes('删除') || a.includes('取消')) return '#f56c6c';
  if (a.includes('编辑') || a.includes('修改')) return '#e6a23c';
  if (a.includes('恢复')) return '#409eff';
  return '#909399';
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
        <div style="font-size:20px; font-weight:700;">📝 操作日志</div>
        <div style="display:flex; gap:10px;">
          <el-select v-model="query.target_type" placeholder="类别筛选" clearable style="width:140px;" @change="load">
            <el-option v-for="o in typeOptions" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
        </div>
      </div>

      <el-table :data="rows" v-loading="loading" stripe size="small">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作人" width="100" prop="admin_name" />
        <el-table-column label="类别" width="90">
          <template #default="{ row }">
            <span>{{ typeIcon(row.target_type) }} {{ row.target_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <span :style="{ color: actionColor(row.action), fontWeight: 600 }">{{ row.action }}</span>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="300" prop="detail" show-overflow-tooltip />
        <el-table-column label="目标ID" width="80" prop="target_id" />
      </el-table>

      <el-pagination
        style="margin-top:16px; display:flex; justify-content:flex-end;"
        v-model:current-page="query.page" v-model:page-size="query.size"
        :total="total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next"
        @current-change="load" @size-change="load"
      />
    </el-card>
  </div>
</template>
