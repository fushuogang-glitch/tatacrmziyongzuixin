<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';
import { useRouter } from 'vue-router';
import { useUserStore } from '../../store/user';

const router = useRouter();
const user = useUserStore();
const status = ref('pending');
const rows = ref<any[]>([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const r: any = await API.serviceOrderList(status.value ? { status: status.value } : {});
    rows.value = (r || []);
  } finally {
    loading.value = false;
  }
}

function statusLabel(s: string) {
  const m: Record<string, string> = {
    pending: '待确认', confirmed: '待老师接单', accepted: '老师已接单',
    preparing: '执案准备', in_progress: '执案中', follow_up: '跟进中',
    completed: '已完成', cancelled: '已取消'
  };
  return m[s] || s;
}

function statusType(s: string) {
  if (s === 'pending') return 'warning';
  if (s === 'confirmed') return 'info';
  if (s === 'completed') return 'success';
  if (s === 'cancelled') return 'danger';
  if (s === 'in_progress') return '';
  return 'info';
}

function goDetail(row: any) {
  router.push(`/service-orders/${row.id}`);
}

function fmt(v: any) {
  if (!v) return '—';
  return String(v).replace('T', ' ').slice(0, 16);
}

const isTeacher = user.role === 'consultant';

onMounted(load);
</script>

<template>
  <div>
    <el-card>
      <div class="toolbar">
        <el-select v-model="status" placeholder="状态筛选" clearable style="width: 180px;" @change="load">
          <el-option label="全部" value="" />
          <el-option label="待管理员确认" value="pending" />
          <el-option label="待老师接单" value="confirmed" />
          <el-option label="老师已接单" value="accepted" />
          <el-option label="执案中" value="in_progress" />
          <el-option label="已完成" value="completed" />
        </el-select>
        <el-button @click="load">刷新</el-button>
        <div style="flex:1"></div>
        <el-tag v-if="!isTeacher" type="info" effect="plain" style="font-size:12px;">
          会员预约 → 管理员确认 → 老师接单 → 自动排期+工单
        </el-tag>
        <el-tag v-else type="warning" effect="plain" style="font-size:12px;">
          分配给你的预约会显示在这里，请及时确认接单
        </el-tag>
      </div>

      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="id" label="#" width="60" />
        <el-table-column label="会员" min-width="160">
          <template #default="{ row }">
            <div style="font-weight:500;">{{ row.member_name || '—' }}</div>
            <div style="font-size:12px;color:#999;">{{ row.enterprise_name || '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="服务项目" min-width="140">
          <template #default="{ row }">{{ row.service_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="老师" width="110">
          <template #default="{ row }">
            <span :style="{ color: row.consultant_name ? '#333' : '#e6a23c' }">
              {{ row.consultant_name || '待分配' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="预约日期" width="120">
          <template #default="{ row }">{{ row.appoint_date || '—' }}</template>
        </el-table-column>
        <el-table-column label="门店" width="130">
          <template #default="{ row }">{{ row.store_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="160">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="140">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending' && !isTeacher" link type="primary" @click="goDetail(row)">
              去确认
            </el-button>
            <el-button v-else-if="row.status === 'confirmed' && isTeacher" link type="warning" @click="goDetail(row)">
              确认接单
            </el-button>
            <el-button v-else-if="row.status === 'confirmed' && !isTeacher" link type="info" @click="goDetail(row)">
              等待老师接单
            </el-button>
            <el-button v-else link type="default" @click="goDetail(row)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
</style>
