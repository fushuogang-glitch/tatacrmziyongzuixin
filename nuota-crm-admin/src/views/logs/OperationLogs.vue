<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);
const total = ref(0);
const page = ref(1);

async function load() {
  loading.value = true;
  try {
    const res = await API.request('GET', `/admin/operation-logs?page=${page.value}&size=50`) as any;
    rows.value = res.items || [];
    total.value = res.total || 0;
  } finally {
    loading.value = false;
  }
}

function actionTag(action: string) {
  if (action.includes('新增')) return 'success';
  if (action.includes('修改')) return 'warning';
  if (action.includes('停用') || action.includes('删除')) return 'danger';
  return 'info';
}

onMounted(load);
</script>

<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>操作日志</span>
          <el-button @click="load" size="small">刷新</el-button>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" stripe>
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ row.created_at?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column prop="admin_name" label="操作人" width="120" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-tag :type="actionTag(row.action)" size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="对象类型" width="100" />
        <el-table-column prop="target_id" label="对象ID" width="80" />
        <el-table-column prop="detail" label="详情" min-width="200" />
      </el-table>

      <el-pagination
        v-model:current-page="page"
        :total="total"
        :page-size="50"
        layout="total, prev, pager, next"
        style="margin-top:16px"
        @current-change="load"
      />
    </el-card>
  </div>
</template>
