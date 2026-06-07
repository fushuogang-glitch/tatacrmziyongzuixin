<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const loading = ref(false);
const month = ref(defaultMonth());
const branchId = ref<any>('');
const branches = ref<any[]>([]);
const items = ref<any[]>([]);
const total = ref(0);
const count = ref(0);

function defaultMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function money(v: any) {
  const n = parseFloat(v || 0);
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtTime(v: any) {
  if (!v) return '-';
  return String(v).replace('T', ' ').slice(0, 16);
}

const payMethodMap: any = {
  company_account: '对公账户',
  private_account: '私户转账',
  wecom: '企业微信',
  wechat_proxy: '微信代收',
  cash: '现金',
  wechat: '微信',
  alipay: '支付宝',
};
function methodName(m: string) { return payMethodMap[m] || m || '-'; }

async function loadBranches() {
  try {
    const d: any = await API.branchList();
    branches.value = Array.isArray(d) ? d : (d?.items || []);
  } catch { branches.value = []; }
}

async function load() {
  loading.value = true;
  try {
    const params: any = { month: month.value };
    if (branchId.value) params.branch_id = branchId.value;
    const d: any = await API.financeIncomeDetail(params);
    items.value = d?.items || [];
    total.value = d?.total || 0;
    count.value = d?.count || items.value.length;
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.msg || '加载失败');
  } finally {
    loading.value = false;
  }
}

watch([month, branchId], load);

// 默认定位到最近有收费数据的月份：从当前月往前找最多12个月，命中即停
async function locateLatestMonth() {
  const d = new Date();
  for (let i = 0; i < 12; i++) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const mm = `${y}-${m}`;
    try {
      const r: any = await API.financeIncomeDetail({ month: mm });
      if ((r?.count || (r?.items || []).length) > 0) { month.value = mm; return; }
    } catch { /* 忽略，继续往前找 */ }
    d.setMonth(d.getMonth() - 1);
  }
  // 12个月都没数据则保持当前月（month 已是默认值）
}

onMounted(async () => {
  loadBranches();
  await locateLatestMonth();
  load();
});
</script>

<template>
  <div class="inc">
    <div class="page-head">
      <div class="title">收费明细</div>
      <div class="filters">
        <el-date-picker
          v-model="month" type="month" value-format="YYYY-MM" format="YYYY-MM"
          placeholder="选择月份" :clearable="false" style="width:150px"
        />
        <el-select v-model="branchId" placeholder="全部分公司" clearable style="width:160px">
          <el-option v-for="b in branches" :key="b.id" :label="b.name" :value="b.id" />
        </el-select>
      </div>
    </div>

    <div class="summary-row">
      <div class="sm-card">
        <div class="sm-lbl">收费合计</div>
        <div class="sm-num income">¥{{ money(total) }}</div>
      </div>
      <div class="sm-card">
        <div class="sm-lbl">收费笔数</div>
        <div class="sm-num">{{ count }} 笔</div>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" stripe border style="width:100%" empty-text="暂无收费记录">
      <el-table-column label="会员" min-width="140">
        <template #default="{ row }">
          <span style="font-weight:600;">{{ row.member_name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="金额" width="140" align="right">
        <template #default="{ row }">
          <span style="color:#7c3aed; font-weight:700;">¥{{ money(row.amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="支付方式" width="120">
        <template #default="{ row }">
          <el-tag size="small" effect="light">{{ methodName(row.pay_method) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="支付时间" width="160">
        <template #default="{ row }">{{ fmtTime(row.pay_time) }}</template>
      </el-table-column>
      <el-table-column label="分公司" width="120">
        <template #default="{ row }">{{ row.branch_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '-' }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.inc { padding: 4px 2px; --np: #7c3aed; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 12px; }
.page-head .title { font-size: 20px; font-weight: 700; color: #1f2937; }
.filters { display: flex; gap: 10px; }

.summary-row { display: flex; gap: 16px; margin-bottom: 18px; }
.sm-card { background: #faf9ff; border: 1px solid #f0eefb; border-radius: 12px; padding: 12px 22px; min-width: 140px; }
.sm-lbl { font-size: 12px; color: #9ca3af; margin-bottom: 4px; }
.sm-num { font-size: 22px; font-weight: 700; color: #1f2937; }
.sm-num.income { color: var(--np); }
</style>
