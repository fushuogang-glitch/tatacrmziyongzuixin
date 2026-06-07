<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Money, Wallet, TrendCharts, OfficeBuilding, Coin } from '@element-plus/icons-vue';
import { API } from '../../api';

const router = useRouter();
const loading = ref(false);
const month = ref(defaultMonth());
const summary = ref<any>({
  total_income: 0, total_fixed_cost: 0, total_variable_cost: 0,
  total_cost: 0, total_profit: 0, branch_count: 0, profitable_count: 0,
});
const branches = ref<any[]>([]);

function defaultMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function money(v: any) {
  const n = parseFloat(v || 0);
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function rate(v: any) {
  const n = parseFloat(v || 0);
  return (n <= 1 ? n * 100 : n).toFixed(1);
}

function rateNum(v: any) {
  const n = parseFloat(v || 0);
  return Math.min(100, Math.max(0, n <= 1 ? n * 100 : n));
}

// 利润率展示：×100 保留 1 位小数加 %，null 显示 —
function pct(v: any) {
  if (v === null || v === undefined || v === '') return '—';
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  return (n * 100).toFixed(1) + '%';
}
function pctNum(v: any) {
  if (v === null || v === undefined || v === '') return null;
  const n = parseFloat(v);
  return isNaN(n) ? null : n;
}

async function load() {
  loading.value = true;
  try {
    const d: any = await API.financeOverview(month.value);
    summary.value = d?.summary || summary.value;
    branches.value = d?.branches || [];
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.msg || '加载失败');
  } finally {
    loading.value = false;
  }
}

function gotoBreakeven(b: any) {
  router.push({ path: '/finance/breakeven', query: { branch_id: b.branch_id, month: month.value } });
}

watch(month, load);
onMounted(load);
</script>

<template>
  <div class="fin-ov">
    <div class="page-head">
      <div class="title">财务总览</div>
      <el-date-picker
        v-model="month" type="month" value-format="YYYY-MM" format="YYYY-MM"
        placeholder="选择月份" :clearable="false" style="width:160px"
      />
    </div>

    <div class="stat-row" v-loading="loading">
      <div class="stat-card s1">
        <el-icon class="ic"><Money /></el-icon>
        <div><div class="num">¥{{ money(summary.total_income) }}</div><div class="lbl">总收入</div></div>
      </div>
      <div class="stat-card s2">
        <el-icon class="ic"><Wallet /></el-icon>
        <div><div class="num">¥{{ money(summary.total_cost) }}</div><div class="lbl">总成本</div></div>
      </div>
      <div class="stat-card" :class="summary.total_profit >= 0 ? 's3' : 's3r'">
        <el-icon class="ic"><TrendCharts /></el-icon>
        <div><div class="num">¥{{ money(summary.total_profit) }}</div><div class="lbl">总利润</div></div>
      </div>
      <div class="stat-card s5">
        <el-icon class="ic"><Coin /></el-icon>
        <div><div class="num">¥{{ money(summary.total_consumption) }}</div><div class="lbl">总消耗额</div></div>
      </div>
      <div class="stat-card s4">
        <el-icon class="ic"><OfficeBuilding /></el-icon>
        <div><div class="num">{{ summary.profitable_count }}/{{ summary.branch_count }}</div><div class="lbl">盈利分公司数</div></div>
      </div>
    </div>

    <div class="rate-row" v-if="summary.profit_rate_income != null || summary.profit_rate_consumption != null">
      <div class="rate-pill">营业额利润率 <b class="win">{{ pct(summary.profit_rate_income) }}</b></div>
      <div class="rate-pill">消耗额利润率 <b :class="(pctNum(summary.profit_rate_consumption) ?? 0) < 0 ? 'lose' : 'win'">{{ pct(summary.profit_rate_consumption) }}</b></div>
    </div>

    <div class="section-title">各分公司盈亏</div>
    <div class="card-grid" v-loading="loading">
      <div v-for="b in branches" :key="b.branch_id" class="br-card" @click="gotoBreakeven(b)">
        <div class="br-head">
          <div class="br-name"><el-icon><OfficeBuilding /></el-icon><span>{{ b.branch_name }}</span></div>
          <el-tag size="small" effect="light" round>{{ b.city || '—' }}</el-tag>
        </div>
        <div class="br-rows">
          <div class="r"><span class="k">收入</span><span class="v income">¥{{ money(b.income) }}</span></div>
          <div class="r"><span class="k">固定成本</span><span class="v">¥{{ money(b.fixed_cost) }}</span></div>
          <div class="r"><span class="k">变动成本</span><span class="v">¥{{ money(b.variable_cost) }}</span></div>
          <div class="r"><span class="k">盈亏</span>
            <span class="v profit" :class="b.is_profit ? 'win' : 'lose'">
              {{ b.profit >= 0 ? '+' : '' }}¥{{ money(b.profit) }}
            </span>
          </div>
          <div class="r"><span class="k">盈亏平衡点</span><span class="v">¥{{ money(b.breakeven_point) }}</span></div>
          <div class="r"><span class="k">消耗额</span><span class="v consume">¥{{ money(b.consumption) }}</span></div>
          <div class="r"><span class="k">营业额利润率</span><span class="v rate-win">{{ pct(b.profit_rate_income) }}</span></div>
          <div class="r"><span class="k">消耗额利润率</span><span class="v" :class="(pctNum(b.profit_rate_consumption) ?? 0) < 0 ? 'rate-lose' : 'rate-win'">{{ pct(b.profit_rate_consumption) }}</span></div>
        </div>
        <div class="achieve">
          <div class="ac-top">
            <span>达成率</span>
            <span class="ac-pct" :class="b.is_profit ? 'win' : 'lose'">{{ rate(b.achieve_rate) }}%</span>
          </div>
          <el-progress
            :percentage="rateNum(b.achieve_rate)" :show-text="false"
            :stroke-width="8" :color="b.is_profit ? '#10b981' : '#7c3aed'"
          />
        </div>
      </div>
      <el-empty v-if="!loading && branches.length === 0" description="暂无分公司财务数据" style="grid-column:1/-1" />
    </div>
  </div>
</template>

<style scoped>
.fin-ov { padding: 4px 2px; --np: #7c3aed; --win: #10b981; --lose: #ef4444; }

.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.page-head .title { font-size: 20px; font-weight: 700; color: #1f2937; }

.stat-row { display: grid; grid-template-columns: repeat(5,1fr); gap: 14px; margin-bottom: 24px; }
@media (max-width: 1100px) { .stat-row { grid-template-columns: repeat(3,1fr); } }
.stat-card { display: flex; align-items: center; gap: 14px; padding: 18px 20px; border-radius: 14px; color: #fff; box-shadow: 0 6px 18px rgba(0,0,0,.06); }
.stat-card .ic { font-size: 30px; opacity: .92; }
.stat-card .num { font-size: 24px; font-weight: 700; line-height: 1.1; }
.stat-card .lbl { font-size: 13px; opacity: .9; margin-top: 2px; }
.s1 { background: linear-gradient(135deg,#7c3aed,#a855f7); }
.s2 { background: linear-gradient(135deg,#6366f1,#818cf8); }
.s3 { background: linear-gradient(135deg,#10b981,#34d399); }
.s3r { background: linear-gradient(135deg,#ef4444,#f87171); }
.s4 { background: linear-gradient(135deg,#8b5cf6,#c084fc); }
.s5 { background: linear-gradient(135deg,#d97706,#f59e0b); }

.rate-row { display: flex; gap: 12px; margin: -10px 0 22px; flex-wrap: wrap; }
.rate-pill { background: #faf9ff; border: 1px solid #f0eefb; border-radius: 10px; padding: 8px 16px; font-size: 13px; color: #6b7280; }
.rate-pill b { margin-left: 6px; font-size: 15px; }
.rate-pill b.win { color: var(--win); }
.rate-pill b.lose { color: var(--lose); }

.section-title { font-size: 15px; font-weight: 700; color: #1f2937; margin: 4px 0 14px; padding-left: 10px; border-left: 4px solid var(--np); }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px,1fr)); gap: 14px; min-height: 80px; }

.br-card { background: #fff; border: 1px solid #f0eefb; border-radius: 14px; padding: 16px 18px; cursor: pointer; transition: all .22s; }
.br-card:hover { box-shadow: 0 10px 30px rgba(124,58,237,.16); border-color: #ddd6fe; transform: translateY(-3px); }

.br-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.br-name { display: flex; align-items: center; gap: 6px; font-size: 16px; font-weight: 700; color: #1f2937; }
.br-name .el-icon { color: var(--np); }

.br-rows .r { display: flex; justify-content: space-between; font-size: 13px; line-height: 2; }
.br-rows .k { color: #b0b3bb; }
.br-rows .v { color: #374151; font-weight: 600; }
.br-rows .v.income { color: var(--np); }
.br-rows .v.profit.win { color: var(--win); }
.br-rows .v.profit.lose { color: var(--lose); }
.br-rows .v.consume { color: #d97706; }
.br-rows .v.rate-win { color: var(--win); }
.br-rows .v.rate-lose { color: var(--lose); }

.achieve { margin-top: 12px; padding-top: 12px; border-top: 1px dashed #f0eefb; }
.ac-top { display: flex; justify-content: space-between; font-size: 12px; color: #9ca3af; margin-bottom: 6px; }
.ac-pct { font-weight: 700; }
.ac-pct.win { color: var(--win); }
.ac-pct.lose { color: var(--np); }
</style>
