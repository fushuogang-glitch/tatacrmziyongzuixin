<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { TOKEN_KEY, API } from '../../api';

const d = reactive<any>({
  member: {}, consultant: {}, finance: {}, analysis: {},
  year: 0, month: 0,
});
const loading = ref(false);
const selectedYear = ref(new Date().getFullYear());
const selectedMonth = ref(new Date().getMonth() + 1);

async function load() {
  loading.value = true;
  try {
    const res: any = await API.dashboardV2(selectedYear.value, selectedMonth.value);
    Object.assign(d, res);
  } finally {
    loading.value = false;
  }
}

function yuan(v: number) {
  if (!v) return '¥0';
  if (v >= 10000) return `¥${(v / 10000).toFixed(1)}万`;
  return `¥${v.toLocaleString()}`;
}

const months = [1,2,3,4,5,6,7,8,9,10,11,12];

onMounted(() => { if (localStorage.getItem(TOKEN_KEY)) load(); });
</script>

<template>
  <div v-loading="loading" class="dash">
    <!-- 顶部筛选 -->
    <div class="filter-bar">
      <h2 class="page-title">📊 数 据 看 板</h2>
      <div class="filter-right">
        <el-select v-model="selectedYear" size="small" style="width: 100px" @change="load">
          <el-option v-for="y in [2025,2026,2027]" :key="y" :label="y+'年'" :value="y" />
        </el-select>
        <el-select v-model="selectedMonth" size="small" style="width: 90px" @change="load">
          <el-option v-for="m in months" :key="m" :label="m+'月'" :value="m" />
        </el-select>
        <el-button size="small" type="primary" @click="load" :icon="'Refresh'">刷新</el-button>
      </div>
    </div>

    <!-- ═══ 一、会员/学员 ═══ -->
    <div class="section-title">🏪 会员 / 学员</div>
    <div class="stat-grid g5">
      <div class="card gold">
        <div class="card-num">{{ d.member?.month_service_stores || 0 }}</div>
        <div class="card-unit">家</div>
        <div class="card-label">本月服务店家</div>
      </div>
      <div class="card">
        <div class="card-num">{{ d.member?.month_service_days || 0 }}</div>
        <div class="card-unit">天</div>
        <div class="card-label">服务天数</div>
      </div>
      <div class="card purple">
        <div class="card-num">{{ d.member?.month_referrals || 0 }}</div>
        <div class="card-unit">位</div>
        <div class="card-label">客户推荐数</div>
      </div>
      <div class="card">
        <div class="card-num">{{ d.member?.month_course_attendees || 0 }}</div>
        <div class="card-unit">人</div>
        <div class="card-label">课程参加人数</div>
      </div>
      <div class="card green">
        <div class="card-num">{{ d.member?.month_tier_upgrades || 0 }}</div>
        <div class="card-unit">家</div>
        <div class="card-label">权益升级店数</div>
      </div>
    </div>

    <!-- ═══ 二、老师 ═══ -->
    <div class="section-title">👨‍🏫 老师</div>
    <div class="stat-grid g5">
      <div class="card">
        <div class="card-num">{{ d.consultant?.active_count || 0 }}</div>
        <div class="card-unit">人</div>
        <div class="card-label">出差老师</div>
      </div>
      <div class="card gold">
        <div class="card-num">{{ d.consultant?.service_stores || 0 }}</div>
        <div class="card-unit">家</div>
        <div class="card-label">服务店家</div>
      </div>
      <div class="card">
        <div class="card-num">{{ d.consultant?.travel_days || 0 }}</div>
        <div class="card-unit">天</div>
        <div class="card-label">出差天数</div>
      </div>
      <div class="card purple">
        <div class="card-num">{{ d.consultant?.assigned_members || 0 }}</div>
        <div class="card-unit">家</div>
        <div class="card-label">归属客户</div>
      </div>
      <div class="card purple">
        <div class="card-num">{{ d.consultant?.followed_members || 0 }}</div>
        <div class="card-unit">家</div>
        <div class="card-label">跟进客户</div>
      </div>
      <div class="card green">
        <div class="card-num sm">{{ yuan(d.consultant?.sales || 0) }}</div>
        <div class="card-label">销售金额</div>
      </div>
      <div class="card orange">
        <div class="card-num sm">{{ yuan(d.consultant?.consumed || 0) }}</div>
        <div class="card-label">消耗金额</div>
      </div>
      <div class="card muted">
        <div class="card-num">{{ d.consultant?.rest_days || 0 }}</div>
        <div class="card-unit">天</div>
        <div class="card-label">休息天数</div>
      </div>
    </div>

    <!-- ═══ 三、财务数据 ═══ -->
    <div class="section-title">💰 财务数据</div>
    <div class="stat-grid g5" style="margin-bottom: 12px;">
      <div class="card green">
        <div class="card-num sm">{{ yuan(d.finance?.total_sales || 0) }}</div>
        <div class="card-label">总销售金额</div>
      </div>
      <div class="card orange">
        <div class="card-num sm">{{ yuan(d.finance?.total_consumed || 0) }}</div>
        <div class="card-label">总消耗金额</div>
      </div>
      <div class="card red">
        <div class="card-num sm">{{ yuan(d.finance?.total_debt || 0) }}</div>
        <div class="card-label">欠款总额</div>
      </div>
      <div class="card">
        <div class="card-num">{{ d.finance?.total_stores || 0 }}</div>
        <div class="card-unit">家</div>
        <div class="card-label">服务家数</div>
      </div>
      <div class="card">
        <div class="card-num">{{ d.finance?.total_travel_days || 0 }}</div>
        <div class="card-unit">天</div>
        <div class="card-label">出差总天数</div>
      </div>
    </div>

    <!-- 分公司明细 -->
    <el-table v-if="d.finance?.branches?.length" :data="d.finance.branches" border size="small"
              style="margin-bottom: 20px;" :header-cell-style="{background:'#fafafa',fontWeight:600}">
      <el-table-column prop="short_name" label="分公司" width="100" />
      <el-table-column prop="city" label="城市" width="70" />
      <el-table-column prop="consultant_count" label="老师在岗" width="85" align="center" />
      <el-table-column label="销售金额" width="110" align="right">
        <template #default="{ row }"><span class="green-text">{{ yuan(row.sales) }}</span></template>
      </el-table-column>
      <el-table-column label="消耗金额" width="110" align="right">
        <template #default="{ row }">{{ yuan(row.consumed) }}</template>
      </el-table-column>
      <el-table-column label="欠款" width="110" align="right">
        <template #default="{ row }"><span :style="row.debt > 0 ? 'color:#F56C6C' : ''">{{ yuan(row.debt) }}</span></template>
      </el-table-column>
      <el-table-column prop="stores" label="服务家数" width="85" align="center" />
      <el-table-column prop="travel_days" label="出差天数" width="85" align="center" />
    </el-table>
    <div v-else class="empty-hint">暂无分公司数据（请在「分公司管理」中添加分公司并关联老师）</div>

    <!-- ═══ 四、数据分析 ═══ -->
    <div class="section-title">📈 数据分析</div>
    <div class="stat-grid g5" style="margin-bottom: 12px;">
      <div class="card">
        <div class="card-num">{{ d.analysis?.trial_conv || 0 }}%</div>
        <div class="card-label">试听转化率</div>
      </div>
      <div class="card purple">
        <div class="card-num">{{ d.analysis?.referral_conv || 0 }}%</div>
        <div class="card-label">推荐转化率</div>
      </div>
    </div>

    <!-- 排名表格 - 紧凑网格 -->
    <div class="rank-grid">
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">🏆 客户推荐</span></template>
        <div v-if="!d.analysis?.referral_rank?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.referral_rank || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.name }}</span>
          <span class="rank-val">{{ r.count }}次</span>
        </div>
      </el-card>
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">✈️ 出差天数</span></template>
        <div v-if="!d.analysis?.consultant_days_rank?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.consultant_days_rank || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.name }}</span>
          <span class="rank-val">{{ r.days }}天</span>
        </div>
      </el-card>
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">📋 服务案例</span></template>
        <div v-if="!d.analysis?.consultant_cases_rank?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.consultant_cases_rank || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.name }}</span>
          <span class="rank-val">{{ r.cases }}单</span>
        </div>
      </el-card>
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">💰 销售额</span></template>
        <div v-if="!d.analysis?.consultant_sales_rank?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.consultant_sales_rank || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.name }}</span>
          <span class="rank-val green-text">{{ yuan(r.sales) }}</span>
        </div>
      </el-card>
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">🔥 消耗额</span></template>
        <div v-if="!d.analysis?.consultant_consumed_rank?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.consultant_consumed_rank || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.name }}</span>
          <span class="rank-val">{{ r.count }}次</span>
        </div>
      </el-card>
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">🏢 分公司</span></template>
        <div v-if="!d.analysis?.branch_rank?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.branch_rank || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.short_name || r.name }}</span>
          <span class="rank-val green-text">{{ yuan(r.sales) }}</span>
        </div>
      </el-card>
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">👥 归属客户</span></template>
        <div v-if="!d.analysis?.consultant_assigned_rank?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.consultant_assigned_rank || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.name }}</span>
          <span class="rank-val">{{ r.count }}家</span>
        </div>
      </el-card>
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">📞 跟进客户</span></template>
        <div v-if="!d.analysis?.consultant_followed_rank?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.consultant_followed_rank || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.name }}</span>
          <span class="rank-val">{{ r.count }}家</span>
        </div>
      </el-card>
      <el-card shadow="never" class="rank-card">
        <template #header><span class="rank-title">🎯 成交率</span></template>
        <div v-if="!d.analysis?.consultant_conversion?.length" class="rank-empty">暂无数据</div>
        <div v-for="(r, i) in (d.analysis?.consultant_conversion || []).slice(0, 5)" :key="i" class="rank-row">
          <span class="rank-idx" :class="i < 3 ? 'top' : ''">{{ i + 1 }}</span>
          <span class="rank-name">{{ r.name }}</span>
          <span class="rank-val">{{ r.rate }}%<span class="rank-sub">{{ r.paid }}/{{ r.assigned }}</span></span>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.dash { padding: 0 4px; }
.filter-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-title { font-size: 17px; font-weight: 500; letter-spacing: 3px; margin: 0; }
.filter-right { display: flex; gap: 6px; align-items: center; }
.section-title { font-size: 13px; font-weight: 500; color: #606266; margin: 14px 0 8px; padding-left: 2px; letter-spacing: 2px; }

/* 统一grid布局 - 5列 */
.stat-grid { display: grid; gap: 10px; }
.stat-grid.g5 { grid-template-columns: repeat(5, 1fr); }

.card {
  background: #fff; border: 1px solid #ebeef5; border-radius: 6px;
  padding: 10px 8px; text-align: center; transition: box-shadow 0.2s;
}
.card:hover { box-shadow: 0 1px 8px rgba(0,0,0,0.04); }
.card-num { font-size: 22px; font-weight: 600; color: #303133; line-height: 1.2; }
.card-num.sm { font-size: 17px; }
.card-unit { font-size: 11px; color: #909399; font-weight: 400; }
.card-label { font-size: 11px; color: #909399; margin-top: 3px; letter-spacing: 1px; }
.card.gold { border-left: 3px solid #c9a96e; }
.card.gold .card-num { color: #c9a96e; }
.card.green { border-left: 3px solid #67C23A; }
.card.green .card-num { color: #67C23A; }
.card.purple { border-left: 3px solid #7b6fdf; }
.card.purple .card-num { color: #7b6fdf; }
.card.orange { border-left: 3px solid #E6A23C; }
.card.orange .card-num { color: #E6A23C; }
.card.red { border-left: 3px solid #F56C6C; }
.card.red .card-num { color: #F56C6C; }
.card.muted { border-left: 3px solid #C0C4CC; }
.card.muted .card-num { color: #909399; }

.rank-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.rank-card { margin-bottom: 0; }
.rank-card :deep(.el-card__header) { padding: 8px 12px; }
.rank-card :deep(.el-card__body) { padding: 4px 12px 8px; }
.rank-title { font-size: 13px; font-weight: 500; }
.rank-row { display: flex; align-items: center; padding: 3px 0; border-bottom: 1px solid #f8f8f8; }
.rank-row:last-child { border-bottom: none; }
.rank-idx { width: 20px; height: 20px; line-height: 20px; text-align: center; border-radius: 50%; font-size: 11px; color: #909399; background: #f5f5f5; margin-right: 8px; flex-shrink: 0; }
.rank-idx.top { background: #c9a96e; color: #fff; }
.rank-name { flex: 1; font-size: 13px; }
.rank-val { font-size: 13px; font-weight: 500; color: #303133; }
.green-text { color: #67C23A !important; }
.rank-empty { text-align: center; color: #C0C4CC; padding: 6px 0; font-size: 11px; }
.empty-hint { text-align: center; color: #C0C4CC; font-size: 12px; padding: 10px 0; }
.rank-sub { font-size: 10px; color: #909399; font-weight: 400; margin-left: 3px; }
</style>
