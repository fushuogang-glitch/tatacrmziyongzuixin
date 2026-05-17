<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const now = new Date();
const filter = reactive({ year: now.getFullYear(), month: now.getMonth() + 1 });
const summary = ref<any>({ cap: 0, used: 0, remaining: 0 });
const loading = ref(false);
const consultants = ref<any[]>([]);

const setDialog = reactive({ visible: false, cap: 0 });

async function load() {
  loading.value = true;
  try {
    summary.value = await API.quotaMonthly(filter.year, filter.month);
    consultants.value = (await API.consultantList() as any) || [];
  } finally {
    loading.value = false;
  }
}

function openSet() {
  setDialog.cap = summary.value.cap || 0;
  setDialog.visible = true;
}

async function submitSet() {
  await API.quotaSet(filter.year, filter.month, setDialog.cap);
  ElMessage.success('已设置');
  setDialog.visible = false;
  load();
}

const percent = computed(() => {
  const c = summary.value.cap || 0;
  if (!c) return 0;
  return Math.min(100, Math.round((summary.value.used / c) * 100));
});

const active = computed(() => consultants.value.filter(c => c.status === 'active'));

onMounted(load);
</script>

<template>
  <div v-loading="loading">
    <el-card>
      <template #header>
        <span>月度名额</span>
      </template>
      <div class="toolbar">
        <el-date-picker
          v-model="filter.year"
          type="year"
          value-format="YYYY"
          placeholder="年"
          style="width: 120px;"
          @change="(v) => { filter.year = Number(v); load(); }"
        />
        <el-select v-model="filter.month" style="width: 120px;" @change="load">
          <el-option v-for="m in 12" :key="m" :label="`${m} 月`" :value="m" />
        </el-select>
        <el-button type="primary" @click="openSet">设置上限</el-button>
        <el-button @click="load">刷新</el-button>
      </div>

      <el-row :gutter="16" style="margin-top: 20px;">
        <el-col :span="8">
          <el-card shadow="hover"><div class="metric"><div class="l">本月上限</div><div class="v">{{ summary.cap }}</div></div></el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover"><div class="metric"><div class="l">已占用</div><div class="v warn">{{ summary.used }}</div></div></el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover"><div class="metric"><div class="l">剩余</div><div class="v ok">{{ summary.remaining }}</div></div></el-card>
        </el-col>
      </el-row>

      <div style="margin-top: 24px;">
        <div style="margin-bottom: 8px; color: #909399;">名额使用进度</div>
        <el-progress :percentage="percent" :stroke-width="18" />
      </div>

      <el-alert type="info" :closable="false" style="margin-top: 24px;"
        :title="`默认上限 = 活跃老师数 × 6 = ${active.length} × 6 = ${active.length * 6}（可手动覆盖）`" />
    </el-card>

    <el-dialog v-model="setDialog.visible" title="设置月度上限" width="360px">
      <el-form label-width="80px">
        <el-form-item label="年月">{{ filter.year }} 年 {{ filter.month }} 月</el-form-item>
        <el-form-item label="上限">
          <el-input-number v-model="setDialog.cap" :min="0" :step="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="setDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitSet">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.metric { text-align: center; padding: 8px 0; }
.metric .l { font-size: 13px; color: #909399; }
.metric .v { font-size: 32px; font-weight: 700; color: #1f2d3d; margin-top: 8px; }
.metric .v.ok { color: #67C23A; }
.metric .v.warn { color: #E6A23C; }
</style>
