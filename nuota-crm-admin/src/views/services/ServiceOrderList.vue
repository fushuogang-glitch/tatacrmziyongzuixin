<template>
  <div class="page">
    <div class="header">
      <h2>服务工单</h2>
      <el-radio-group v-model="status" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="pending">待确认</el-radio-button>
        <el-radio-button label="confirmed">已确认</el-radio-button>
        <el-radio-button label="accepted">已接单</el-radio-button>
        <el-radio-button label="preparing">执案准备</el-radio-button>
        <el-radio-button label="in_progress">执案中</el-radio-button>
        <el-radio-button label="reporting">待审核</el-radio-button>
        <el-radio-button label="follow_up">跟进中</el-radio-button>
        <el-radio-button label="completed">已完成</el-radio-button>
      </el-radio-group>
    </div>

    <el-table :data="rows" v-loading="loading" stripe @row-click="goDetail">
      <el-table-column prop="order_no" label="工单号" width="180" />
      <el-table-column prop="member_id" label="会员ID" width="80" />
      <el-table-column prop="service_id" label="服务" width="80" />
      <el-table-column prop="appoint_date" label="预约日期" width="120" />
      <el-table-column prop="appoint_time" label="时段" width="120" />
      <el-table-column prop="store_name" label="门店" min-width="150" />
      <el-table-column prop="consultant_id" label="老师" width="80" />
      <el-table-column prop="workflow_stage" label="当前阶段" width="120" />
      <el-table-column label="进度" width="120">
        <template #default="{ row }">
          <el-progress :percentage="row.workflow_progress || 0" :stroke-width="6" />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="满意度" width="100">
        <template #default="{ row }">
          <span v-if="row.rating" class="rating">★ {{ row.rating }}</span>
          <span v-else class="dim">—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);
const status = ref('');
const router = useRouter();

async function load() {
  loading.value = true;
  try {
    rows.value = (await API.serviceOrderList(status.value ? { status: status.value } : {}) as any) || [];
  } finally {
    loading.value = false;
  }
}

function goDetail(row: any) {
  router.push(`/service-orders/${row.id}`);
}

function statusType(s: string): any {
  return ({ pending: 'warning', confirmed: 'primary', accepted: '', preparing: 'warning',
    in_progress: '', reporting: 'success', follow_up: 'warning', completed: 'success', cancelled: 'info' } as any)[s] || '';
}
function statusLabel(s: string) {
  return ({ pending: '待确认', confirmed: '已确认', accepted: '已接单', preparing: '执案准备',
    in_progress: '执案中', reporting: '待审核', follow_up: '跟进中', completed: '整体结束', cancelled: '已取消' } as any)[s] || s;
}

onMounted(load);
</script>

<style scoped>
.page { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.rating { color: #c9a96e; font-weight: 600; }
.dim { color: #999; }
:deep(.el-table__row) { cursor: pointer; }
</style>
