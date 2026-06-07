<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Download } from '@element-plus/icons-vue';
import { API } from '../../api';

const loading = ref(false);
const month = ref(defaultMonth());
const branchId = ref<any>('');
const branches = ref<any[]>([]);

const monthly = ref<any>(null);          // 单分公司核算
const incomeItems = ref<any[]>([]);      // 收费明细
const expenseItems = ref<any[]>([]);     // 支出明细
const incomeTotal = ref(0);
const expenseTotal = ref(0);

function defaultMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}
function money(v: any) {
  const n = parseFloat(v || 0);
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

const payMethodMap: any = {
  company_account: '对公账户', private_account: '私户转账', wecom: '企业微信',
  wechat_proxy: '微信代收', cash: '现金', wechat: '微信', alipay: '支付宝',
};
function methodName(m: string) { return payMethodMap[m] || m || '其他'; }

const catMap: any = {
  rent: '房租', utility: '水电', depreciation: '折旧', insurance: '保险',
  other_fixed: '其他固定', purchase: '采购', salary: '工资', base_salary: '底薪', commission: '提成',
};
function catName(c: string) { return catMap[c] || c || '其他'; }

async function loadBranches() {
  try {
    const d: any = await API.branchList();
    branches.value = Array.isArray(d) ? d : (d?.items || []);
    if (!branchId.value && branches.value.length) branchId.value = branches.value[0].id;
  } catch { branches.value = []; }
}

async function load() {
  if (!branchId.value) return;
  loading.value = true;
  try {
    const [mm, inc, exp]: any = await Promise.all([
      API.financeBranchMonthly(branchId.value, month.value).catch(() => null),
      API.financeIncomeDetail({ month: month.value, branch_id: branchId.value }).catch(() => ({})),
      API.financeExpenseDetail({ month: month.value, branch_id: branchId.value }).catch(() => ({})),
    ]);
    monthly.value = mm;
    incomeItems.value = inc?.items || [];
    incomeTotal.value = inc?.total || incomeItems.value.reduce((s, x) => s + parseFloat(x.amount || 0), 0);
    expenseItems.value = exp?.items || [];
    expenseTotal.value = exp?.total || expenseItems.value.reduce((s, x) => s + parseFloat(x.amount || 0), 0);
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.msg || '加载失败');
  } finally {
    loading.value = false;
  }
}

// 收入按支付方式汇总
const incomeRows = computed(() => {
  const map: Record<string, number> = {};
  for (const it of incomeItems.value) {
    const k = methodName(it.pay_method);
    map[k] = (map[k] || 0) + parseFloat(it.amount || 0);
  }
  return Object.entries(map).map(([item, amount]) => ({ item, amount }));
});

// 支出按类别汇总（采购/固定成本/工资分类）
const expenseRows = computed(() => {
  const map: Record<string, number> = {};
  for (const it of expenseItems.value) {
    let k: string;
    if (it.kind === 'purchase') k = '采购';
    else k = catName(it.category);
    map[k] = (map[k] || 0) + parseFloat(it.amount || 0);
  }
  return Object.entries(map).map(([item, amount]) => ({ item, amount }));
});

const profit = computed(() => {
  if (monthly.value && monthly.value.profit !== undefined && monthly.value.profit !== null) {
    return parseFloat(monthly.value.profit || 0);
  }
  return incomeTotal.value - expenseTotal.value;
});
const breakevenPoint = computed(() => parseFloat(monthly.value?.breakeven_point || 0));
const branchName = computed(() => branches.value.find(b => b.id === branchId.value)?.name || '');

function exportCSV() {
  const rows: string[][] = [];
  rows.push([`月度核算表 - ${branchName.value} - ${month.value}`]);
  rows.push([]);
  rows.push(['区域', '科目', '金额(元)']);
  // 收入
  if (incomeRows.value.length) {
    incomeRows.value.forEach((r, i) => rows.push([i === 0 ? '收入' : '', r.item, String(Math.round(r.amount))]));
  } else {
    rows.push(['收入', '（无）', '0']);
  }
  rows.push(['', '收入小计', String(Math.round(incomeTotal.value))]);
  // 支出
  if (expenseRows.value.length) {
    expenseRows.value.forEach((r, i) => rows.push([i === 0 ? '支出' : '', r.item, String(Math.round(r.amount))]));
  } else {
    rows.push(['支出', '（无）', '0']);
  }
  rows.push(['', '支出小计', String(Math.round(expenseTotal.value))]);
  rows.push([]);
  rows.push(['', '本月盈亏', String(Math.round(profit.value))]);
  rows.push(['', '盈亏平衡点', String(Math.round(breakevenPoint.value))]);

  const csv = '\uFEFF' + rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `月度核算表_${branchName.value}_${month.value}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

watch([month, branchId], load);
onMounted(async () => { await loadBranches(); load(); });
</script>

<template>
  <div class="ms">
    <div class="page-head">
      <div class="title">月度核算表</div>
      <div class="filters">
        <el-select v-model="branchId" placeholder="选择分公司" style="width:170px">
          <el-option v-for="b in branches" :key="b.id" :label="b.name" :value="b.id" />
        </el-select>
        <el-date-picker
          v-model="month" type="month" value-format="YYYY-MM" format="YYYY-MM"
          placeholder="选择月份" :clearable="false" style="width:150px"
        />
        <el-button type="primary" :icon="Download" round @click="exportCSV">导出</el-button>
      </div>
    </div>

    <div class="statement-card" v-loading="loading">
      <div class="st-head">
        <div class="st-title">{{ branchName || '—' }} · {{ month }} 月度核算</div>
      </div>

      <table class="st-table">
        <thead>
          <tr><th class="th-area">区域</th><th>科目</th><th class="th-amt">金额</th></tr>
        </thead>
        <tbody>
          <!-- 收入区 -->
          <tr v-for="(r, i) in incomeRows" :key="'inc'+i" class="row-income">
            <td v-if="i === 0" :rowspan="incomeRows.length || 1" class="area income">收入</td>
            <td>{{ r.item }}</td>
            <td class="amt income">¥{{ money(r.amount) }}</td>
          </tr>
          <tr v-if="incomeRows.length === 0" class="row-income">
            <td class="area income">收入</td><td>（无收费记录）</td><td class="amt">¥0</td>
          </tr>
          <tr class="sub-row">
            <td></td><td class="sub-lbl">收入小计</td><td class="amt income">¥{{ money(incomeTotal) }}</td>
          </tr>

          <!-- 支出区 -->
          <tr v-for="(r, i) in expenseRows" :key="'exp'+i" class="row-expense">
            <td v-if="i === 0" :rowspan="expenseRows.length || 1" class="area expense">支出</td>
            <td>{{ r.item }}</td>
            <td class="amt expense">¥{{ money(r.amount) }}</td>
          </tr>
          <tr v-if="expenseRows.length === 0" class="row-expense">
            <td class="area expense">支出</td><td>（无支出记录）</td><td class="amt">¥0</td>
          </tr>
          <tr class="sub-row">
            <td></td><td class="sub-lbl">支出小计</td><td class="amt expense">¥{{ money(expenseTotal) }}</td>
          </tr>

          <!-- 盈亏 -->
          <tr class="total-row" :class="profit >= 0 ? 'win' : 'lose'">
            <td></td><td class="total-lbl">本月盈亏</td>
            <td class="amt total">{{ profit >= 0 ? '+' : '' }}¥{{ money(profit) }}</td>
          </tr>
          <tr class="be-row">
            <td></td><td class="sub-lbl">盈亏平衡点</td><td class="amt">¥{{ money(breakevenPoint) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.ms { padding: 4px 2px; --np: #7c3aed; --win: #10b981; --lose: #ef4444; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 12px; }
.page-head .title { font-size: 20px; font-weight: 700; color: #1f2937; }
.filters { display: flex; gap: 10px; align-items: center; }

.statement-card { background: #fff; border: 1px solid #f0eefb; border-radius: 14px; padding: 22px 24px; transition: all .22s; }
.statement-card:hover { box-shadow: 0 10px 30px rgba(124,58,237,.10); }
.st-head { margin-bottom: 16px; }
.st-title { font-size: 16px; font-weight: 700; color: #1f2937; padding-left: 10px; border-left: 4px solid var(--np); }

.st-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.st-table th, .st-table td { padding: 11px 14px; border: 1px solid #f0eefb; text-align: left; }
.st-table thead th { background: #f5f3ff; color: #6d28d9; font-weight: 700; }
.st-table .th-area { width: 90px; }
.st-table .th-amt { width: 180px; text-align: right; }

.area { font-weight: 700; vertical-align: middle; text-align: center; }
.area.income { background: #ecfdf5; color: var(--win); }
.area.expense { background: #fef2f2; color: var(--lose); }

.amt { text-align: right; font-weight: 600; color: #374151; }
.amt.income { color: var(--win); }
.amt.expense { color: var(--lose); }

.sub-row td { background: #faf9ff; }
.sub-lbl { font-weight: 700; color: #6b7280; }

.total-row td { padding: 14px; font-size: 15px; }
.total-row.win td { background: #ecfdf5; }
.total-row.lose td { background: #fef2f2; }
.total-lbl { font-weight: 800; color: #1f2937; }
.amt.total { font-size: 20px; font-weight: 800; }
.total-row.win .amt.total { color: var(--win); }
.total-row.lose .amt.total { color: var(--lose); }

.be-row td { background: #fafafa; }
</style>
