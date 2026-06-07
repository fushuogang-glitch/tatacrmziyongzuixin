<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const route = useRoute();
const loading = ref(false);
const saving = ref(false);
const month = ref((route.query.month as string) || defaultMonth());
const branchId = ref<any>(route.query.branch_id ? Number(route.query.branch_id) : '');
const branches = ref<any[]>([]);
const data = ref<any>(null);
const explain = ref('');

const config = reactive<any>({
  commission_rate: 0,
  variable_extra_rate: 0,
  default_variable_rate: 0,
});

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

async function loadBranches() {
  try {
    const d: any = await API.branchList();
    branches.value = Array.isArray(d) ? d : (d?.items || []);
    if (!branchId.value && branches.value.length) branchId.value = branches.value[0].id;
  } catch { branches.value = []; }
}

async function load() {
  if (!branchId.value) { data.value = null; return; }
  loading.value = true;
  try {
    const bk: any = await API.financeBreakeven(branchId.value, month.value);
    data.value = bk;
    explain.value = bk?.explain || '';
    try {
      const cfg: any = await API.financeBreakevenConfig(branchId.value);
      config.commission_rate = cfg?.commission_rate ?? 0;
      config.variable_extra_rate = cfg?.variable_extra_rate ?? 0;
      config.default_variable_rate = cfg?.default_variable_rate ?? 0;
    } catch {}
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.msg || '加载失败');
  } finally {
    loading.value = false;
  }
}

async function saveConfig() {
  if (!branchId.value) return ElMessage.warning('请先选择分公司');
  saving.value = true;
  try {
    await API.financeBreakevenConfigSet(branchId.value, {
      commission_rate: config.commission_rate,
      variable_extra_rate: config.variable_extra_rate,
      default_variable_rate: config.default_variable_rate,
    });
    ElMessage.success('参数已保存');
    load();
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.msg || '保存失败');
  } finally {
    saving.value = false;
  }
}

watch([month, branchId], load);
onMounted(async () => { await loadBranches(); load(); });
</script>

<template>
  <div class="bk">
    <div class="page-head">
      <div class="title">盈亏平衡核算</div>
      <div class="filters">
        <el-select v-model="branchId" placeholder="选择分公司" style="width:170px">
          <el-option v-for="b in branches" :key="b.id" :label="b.name" :value="b.id" />
        </el-select>
        <el-date-picker
          v-model="month" type="month" value-format="YYYY-MM" format="YYYY-MM"
          placeholder="选择月份" :clearable="false" style="width:150px"
        />
      </div>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!loading && !data" description="请选择分公司查看核算" />

      <div v-else-if="data" class="layout">
        <!-- 左：核算大卡 -->
        <div class="main-card">
          <div class="bk-grid">
            <div class="bk-block income">
              <div class="bk-lbl">收入</div>
              <div class="bk-val">¥{{ money(data.income) }}</div>
            </div>
            <div class="bk-block">
              <div class="bk-lbl">固定成本</div>
              <div class="bk-val">¥{{ money(data.fixed_cost) }}</div>
              <div class="bk-sub">
                <span>底薪 ¥{{ money(data.fixed_breakdown?.base_salary) }}</span>
                <span>房租水电等 ¥{{ money(data.fixed_breakdown?.rent_utility_other) }}</span>
              </div>
            </div>
            <div class="bk-block">
              <div class="bk-lbl">变动成本</div>
              <div class="bk-val">¥{{ money(data.variable_cost) }}</div>
              <div class="bk-sub">
                <span>采购 ¥{{ money(data.variable_breakdown?.purchase) }}</span>
                <span>提成 ¥{{ money(data.variable_breakdown?.commission) }}</span>
              </div>
            </div>
            <div class="bk-block">
              <div class="bk-lbl">变动成本率</div>
              <div class="bk-val">{{ rate(data.variable_rate) }}%</div>
            </div>
          </div>

          <div class="rate-strip">
            <div class="rs-block">
              <div class="rs-lbl">消耗额</div>
              <div class="rs-val consume">¥{{ money(data.consumption) }}</div>
            </div>
            <div class="rs-block">
              <div class="rs-lbl">按营业额利润率</div>
              <div class="rs-val" :class="(pctNum(data.profit_rate_income) ?? 0) < 0 ? 'lose' : 'win'">{{ pct(data.profit_rate_income) }}</div>
            </div>
            <div class="rs-block">
              <div class="rs-lbl">按消耗额利润率</div>
              <div class="rs-val" :class="(pctNum(data.profit_rate_consumption) ?? 0) < 0 ? 'lose' : 'win'">{{ pct(data.profit_rate_consumption) }}</div>
            </div>
          </div>

          <div class="breakeven-hero">
            <div class="be-lbl">盈亏平衡点（月收入需达到）</div>
            <div class="be-num">¥{{ money(data.breakeven_point) }}</div>
            <div class="be-gap" v-if="!data.is_profit">
              距盈亏平衡还差 <b>¥{{ money(data.gap_to_breakeven) }}</b>
            </div>
            <div class="be-gap win" v-else>已越过盈亏平衡点 ✓</div>
          </div>

          <div class="achieve">
            <div class="ac-top">
              <span>达成率</span>
              <span class="ac-pct" :class="data.is_profit ? 'win' : 'lose'">{{ rate(data.achieve_rate) }}%</span>
            </div>
            <el-progress
              :percentage="rateNum(data.achieve_rate)" :show-text="false"
              :stroke-width="12" :color="data.is_profit ? '#10b981' : '#7c3aed'"
            />
          </div>

          <div class="profit-row" :class="data.is_profit ? 'win' : 'lose'">
            <span>当月盈亏</span>
            <span class="p-num">{{ data.profit >= 0 ? '+' : '' }}¥{{ money(data.profit) }}</span>
          </div>

          <div v-if="data.formula" class="formula">公式：{{ data.formula }}</div>
          <div v-if="explain" class="explain">{{ explain }}</div>
        </div>

        <!-- 右：参数设置 -->
        <div class="cfg-card">
          <div class="cfg-title">盈亏平衡参数设置</div>
          <el-form label-position="top">
            <el-form-item label="提成率 (commission_rate)">
              <el-input-number v-model="config.commission_rate" :min="0" :max="1" :step="0.01" :precision="3" controls-position="right" style="width:100%" />
              <div class="cfg-hint">小数表示，如 0.15 = 15%</div>
            </el-form-item>
            <el-form-item label="额外变动率 (variable_extra_rate)">
              <el-input-number v-model="config.variable_extra_rate" :min="0" :max="1" :step="0.01" :precision="3" controls-position="right" style="width:100%" />
            </el-form-item>
            <el-form-item label="默认变动成本率 (default_variable_rate)">
              <el-input-number v-model="config.default_variable_rate" :min="0" :max="1" :step="0.01" :precision="3" controls-position="right" style="width:100%" />
              <div class="cfg-hint">无采购数据时按此比率估算变动成本</div>
            </el-form-item>
            <el-button type="primary" :loading="saving" style="width:100%" @click="saveConfig">保存参数</el-button>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bk { padding: 4px 2px; --np: #7c3aed; --win: #10b981; --lose: #ef4444; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 12px; }
.page-head .title { font-size: 20px; font-weight: 700; color: #1f2937; }
.filters { display: flex; gap: 10px; }

.layout { display: grid; grid-template-columns: 1fr 300px; gap: 16px; align-items: start; }

.main-card { background: #fff; border: 1px solid #f0eefb; border-radius: 14px; padding: 22px 24px; }
.main-card:hover { box-shadow: 0 10px 30px rgba(124,58,237,.10); }

.bk-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 14px; }
.bk-block { background: #faf9ff; border: 1px solid #f0eefb; border-radius: 12px; padding: 14px 16px; }
.bk-block.income { background: linear-gradient(135deg,#f5f3ff,#ede9fe); }
.bk-lbl { font-size: 13px; color: #9ca3af; margin-bottom: 6px; }
.bk-val { font-size: 22px; font-weight: 700; color: #1f2937; }
.bk-block.income .bk-val { color: var(--np); }

.rate-strip { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin-top: 14px; }
.rs-block { background: #faf9ff; border: 1px solid #f0eefb; border-radius: 12px; padding: 14px 16px; text-align: center; }
.rs-lbl { font-size: 13px; color: #9ca3af; margin-bottom: 6px; }
.rs-val { font-size: 22px; font-weight: 700; color: #1f2937; }
.rs-val.consume { color: #d97706; }
.rs-val.win { color: var(--win); }
.rs-val.lose { color: var(--lose); }
.bk-sub { display: flex; flex-direction: column; gap: 2px; margin-top: 8px; font-size: 12px; color: #8b8e98; }

.breakeven-hero { margin-top: 18px; text-align: center; background: linear-gradient(135deg,#7c3aed,#a855f7); border-radius: 14px; padding: 22px; color: #fff; }
.be-lbl { font-size: 13px; opacity: .9; }
.be-num { font-size: 38px; font-weight: 800; margin: 6px 0; letter-spacing: .5px; }
.be-gap { font-size: 13px; opacity: .95; }
.be-gap.win { font-weight: 600; }

.achieve { margin-top: 18px; }
.ac-top { display: flex; justify-content: space-between; font-size: 13px; color: #9ca3af; margin-bottom: 8px; }
.ac-pct { font-weight: 700; font-size: 15px; }
.ac-pct.win { color: var(--win); }
.ac-pct.lose { color: var(--np); }

.profit-row { display: flex; justify-content: space-between; align-items: center; margin-top: 18px; padding: 14px 18px; border-radius: 12px; font-size: 15px; font-weight: 600; }
.profit-row.win { background: #ecfdf5; color: var(--win); }
.profit-row.lose { background: #fef2f2; color: var(--lose); }
.profit-row .p-num { font-size: 22px; font-weight: 800; }

.formula { margin-top: 16px; font-size: 13px; color: #6d28d9; background: #f5f3ff; padding: 10px 14px; border-radius: 10px; }
.explain { margin-top: 10px; font-size: 13px; line-height: 1.7; color: #6b7280; background: #fafafa; padding: 12px 14px; border-radius: 10px; white-space: pre-wrap; }

.cfg-card { background: #fff; border: 1px solid #f0eefb; border-radius: 14px; padding: 20px; }
.cfg-title { font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 14px; padding-left: 10px; border-left: 4px solid var(--np); }
.cfg-hint { font-size: 12px; color: #b0b3bb; margin-top: 4px; }

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
}
</style>
