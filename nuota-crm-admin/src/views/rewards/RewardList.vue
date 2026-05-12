<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { API } from '../../api';

const status = ref('');
const rows = ref<any[]>([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    rows.value = (await API.rewardList(status.value || undefined) as any) || [];
  } finally {
    loading.value = false;
  }
}

function statusTag(s: string) {
  return { available: 'success', booked: 'warning', used: 'info', expired: 'danger' }[s] || '';
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
        <el-select v-model="status" placeholder="状态筛选" clearable style="width: 160px;" @change="load">
          <el-option label="可用" value="available" />
          <el-option label="已预约" value="booked" />
          <el-option label="已使用" value="used" />
          <el-option label="已过期" value="expired" />
        </el-select>
        <el-button @click="load">刷新</el-button>
      </div>
      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="学员" min-width="200">
          <template #default="{ row }">
            {{ row.member?.name }} · {{ row.member?.phone }}
            <span style="color: #909399; margin-left: 6px;">{{ row.member?.member_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="120" />
        <el-table-column prop="referral_id" label="关联推荐" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="激活时间" width="180">
          <template #default="{ row }">{{ fmt(row.activate_time) }}</template>
        </el-table-column>
        <el-table-column label="到期时间" width="180">
          <template #default="{ row }">{{ fmt(row.expire_time) }}</template>
        </el-table-column>
        <el-table-column label="使用时间" width="180">
          <template #default="{ row }">{{ fmt(row.used_time) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; }
</style>
