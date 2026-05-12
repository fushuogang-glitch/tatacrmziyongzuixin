<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    rows.value = (await API.referralList() as any) || [];
  } finally {
    loading.value = false;
  }
}

async function confirm(row: any) {
  await ElMessageBox.confirm(`确认推荐 #${row.id} 成立？将自动下发权益。`, '提示', { type: 'warning' });
  await API.referralConfirm(row.id);
  ElMessage.success('已确认');
  load();
}

function statusTag(s: string) {
  return { pending: 'warning', confirmed: 'success', invalid: 'info' }[s] || '';
}
function rewardStatusTag(s: string) {
  return { pending: 'info', activated: 'success', used: '', expired: 'danger' }[s] || '';
}

function fmt(v: any) {
  if (!v) return '-';
  return String(v).replace('T', ' ').slice(0, 19);
}

onMounted(load);
</script>

<template>
  <div>
    <el-card>
      <div class="toolbar">
        <el-button @click="load">刷新</el-button>
      </div>
      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="referrer_id" label="推荐人ID" width="100" />
        <el-table-column prop="referee_id" label="被推荐人ID" width="110" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="reward_type" label="权益类型" width="130" />
        <el-table-column label="权益状态" width="120">
          <template #default="{ row }"><el-tag :type="rewardStatusTag(row.reward_status)">{{ row.reward_status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="确认时间" width="180">
          <template #default="{ row }">{{ fmt(row.confirm_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="120">
          <template #default="{ row }">
            <el-button link type="success" :disabled="row.status === 'confirmed'" @click="confirm(row)">
              {{ row.status === 'confirmed' ? '已确认' : '手动确认' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; }
</style>
