<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const user = useUserStore();
const loading = ref(false);
const data = ref<any>(null);
const curYear = new Date().getFullYear();
const curMonth = new Date().getMonth() + 1;
const selYear = ref(curYear);
const selMonth = ref(curMonth);

const months = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}月`, value: i + 1 }));

async function loadDashboard() {
  loading.value = true;
  try {
    const res: any = await API.get(
      `/consultant-auth/dashboard?year=${selYear.value}&month=${selMonth.value}`
    );
    data.value = res.data;
  } catch (e: any) {
    console.error('看板加载失败', e);
  } finally {
    loading.value = false;
  }
}

const ms = computed(() => data.value?.month_stats || {});
const ys = computed(() => data.value?.year_stats || {});
const upcoming = computed(() => data.value?.upcoming_visits || []);
const clients = computed(() => data.value?.month_clients || []);

const tierLabel: Record<string, string> = {
  primary: '小学生', junior: '初中生', senior: '高中生', college: '大学生', teacher: '老师'
};
const tierColor: Record<string, string> = {
  primary: '#666', junior: '#7b6fdf', senior: '#4a90d9', college: '#c9a96e', teacher: '#e84c4c'
};

const promo = computed(() => data.value?.promotion_progress || null);
const promoSalesPct = computed(() => {
  if (!promo.value?.sales) return 0;
  const { actual, target } = promo.value.sales;
  return target > 0 ? Math.min(100, Math.round(actual / target * 100)) : 100;
});
const promoWorkDaysPct = computed(() => {
  if (!promo.value?.work_days) return 0;
  const { actual, target } = promo.value.work_days;
  return target > 0 ? Math.min(100, Math.round(actual / target * 100)) : 100;
});
const promoMenteesPct = computed(() => {
  if (!promo.value?.mentees) return 0;
  const { actual, target } = promo.value.mentees;
  return target > 0 ? Math.min(100, Math.round(actual / target * 100)) : 100;
});

onMounted(loadDashboard);
</script>

<template>
  <div class="dashboard" v-loading="loading">
    <!-- 欢迎语 -->
    <div class="welcome-line">{{ data?.consultant?.name || user.realName }} 老师！Hello，你辛苦了！</div>
    <div class="welcome-line-en">Hello, Teacher {{ data?.consultant?.name || user.realName }}! Thank you for your hard work!</div>
    <!-- 使命愿景横幅 -->
    <div class="mission-banner">
      <div class="mission-inner">
        <span class="mission-icon">✨</span>
        <span class="mission-text">愿景：成为中国美业最值得信赖的战略合伙人</span>
        <span class="mission-divider">|</span>
        <span class="mission-text">使命：帮助老板成为老板，推动老板成为企业家</span>
      </div>
    </div>

    <!-- 顶部月份筛选 -->
    <div class="top-bar">
      <div class="welcome">
        <div class="welcome-sub">{{ data?.consultant?.company }} · {{ data?.consultant?.specialty }}</div>
      </div>
      <div class="month-picker">
        <el-select v-model="selYear" style="width:90px" @change="loadDashboard">
          <el-option v-for="y in [curYear-1, curYear, curYear+1]" :key="y" :label="`${y}年`" :value="y" />
        </el-select>
        <el-select v-model="selMonth" style="width:80px;margin-left:8px" @change="loadDashboard">
          <el-option v-for="m in months" :key="m.value" :label="m.label" :value="m.value" />
        </el-select>
      </div>
    </div>

    <div v-if="data" class="content">
      <!-- 核心指标卡 -->
      <div class="stat-grid">
        <div class="stat-card gold">
          <div class="sc-value">{{ ms.visit_days ?? 0 }}</div>
          <div class="sc-label">本月出差天数</div>
          <div class="sc-sub">今年累计 {{ ys.visit_days ?? 0 }} 天</div>
        </div>
        <div class="stat-card purple">
          <div class="sc-value">{{ ms.visit_stores ?? 0 }}</div>
          <div class="sc-label">本月下店次数</div>
          <div class="sc-sub">{{ (ms.visit_cities || []).join(' / ') || '暂无' }}</div>
        </div>
        <div class="stat-card blue">
          <div class="sc-value">¥{{ Number(ms.revenue || 0).toLocaleString() }}</div>
          <div class="sc-label">本月业绩</div>
          <div class="sc-sub">{{ ms.order_count ?? 0 }} 个专案工单</div>
        </div>
        <div class="stat-card green">
          <div class="sc-value">{{ ms.served_clients ?? 0 }}</div>
          <div class="sc-label">服务客户数</div>
          <div class="sc-sub">新客户 {{ ms.new_clients ?? 0 }} 位</div>
        </div>
      </div>

      <!-- 晋级进度 -->
      <div class="section promo-section" v-if="promo">
        <div class="section-title">🚀 晋级进度（{{ promo.year }}年度）</div>
        <div class="promo-header">
          <span class="promo-current">当前：<strong>{{ promo.current_level_name }}</strong></span>
          <span class="promo-arrow">→</span>
          <span class="promo-next">下一级：<strong>{{ promo.next_level_name }}</strong></span>
        </div>
        <div class="promo-bars" v-if="promo.next_level">
          <!-- 销售额 -->
          <div class="promo-bar-item">
            <div class="pb-label">
              <span>💰 年度销售</span>
              <span class="pb-nums">
                ¥{{ (promo.sales.actual / 10000).toFixed(1) }}万
                <span class="pb-target">/ {{ (promo.sales.target / 10000).toFixed(0) }}万</span>
                <span class="pb-gap" v-if="promo.sales.gap > 0">还差 {{ (promo.sales.gap / 10000).toFixed(1) }}万</span>
                <span class="pb-done" v-else>✅ 达标</span>
              </span>
            </div>
            <el-progress :percentage="promoSalesPct" :stroke-width="12" 
              :color="promoSalesPct >= 100 ? '#67c23a' : '#409eff'" />
          </div>
          <!-- 执案天数 -->
          <div class="promo-bar-item">
            <div class="pb-label">
              <span>📅 执案天数</span>
              <span class="pb-nums">
                {{ promo.work_days.actual }}天
                <span class="pb-target">/ {{ promo.work_days.target }}天</span>
                <span class="pb-gap" v-if="promo.work_days.gap > 0">还差 {{ promo.work_days.gap }}天</span>
                <span class="pb-done" v-else>✅ 达标</span>
              </span>
            </div>
            <el-progress :percentage="promoWorkDaysPct" :stroke-width="12" 
              :color="promoWorkDaysPct >= 100 ? '#67c23a' : '#409eff'" />
          </div>
          <!-- 带队人数 -->
          <div class="promo-bar-item" v-if="promo.mentees.target > 0">
            <div class="pb-label">
              <span>👥 带队人数</span>
              <span class="pb-nums">
                {{ promo.mentees.actual }}人
                <span class="pb-target">/ {{ promo.mentees.target }}人</span>
                <span class="pb-gap" v-if="promo.mentees.gap > 0">还差 {{ promo.mentees.gap }}人</span>
                <span class="pb-done" v-else>✅ 达标</span>
              </span>
            </div>
            <el-progress :percentage="promoMenteesPct" :stroke-width="12" 
              :color="promoMenteesPct >= 100 ? '#67c23a' : '#409eff'" />
          </div>
        </div>
        <div v-else class="promo-max">🌟 恭喜！您已达到最高级别！</div>
      </div>

      <!-- 年度城市足迹 -->
      <div class="section" v-if="(ys.visit_cities || []).length > 0">
        <div class="section-title">📍 今年足迹</div>
        <div class="city-tags">
          <span v-for="city in ys.visit_cities" :key="city" class="city-tag">{{ city }}</span>
        </div>
      </div>

      <!-- 近期下店计划 -->
      <div class="section">
        <div class="section-title">📅 近期下店计划（30天内）</div>
        <div v-if="upcoming.length === 0" class="empty-tip">暂无下店安排</div>
        <div v-else class="visit-list">
          <div v-for="v in upcoming" :key="v.id" class="visit-item">
            <div class="vi-date">{{ v.confirmed_date }}</div>
            <div class="vi-info">
              <div class="vi-city">📍 {{ v.city || '待确认城市' }}</div>
              <div class="vi-addr" v-if="v.address">{{ v.address }}</div>
              <div class="vi-days">共 {{ v.duration_days }} 天</div>
            </div>
            <div :class="['vi-status', `vs-${v.status}`]">
              {{ v.status === 'confirmed' ? '已确认' : '待确认' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 本月客户 -->
      <div class="section">
        <div class="section-title">👥 本月服务客户（{{ clients.length }} 位）</div>
        <div v-if="clients.length === 0" class="empty-tip">本月暂无服务记录</div>
        <div v-else class="client-grid">
          <div v-for="c in clients" :key="c.id" class="client-card">
            <div class="cc-avatar">{{ c.name?.slice(0, 1) }}</div>
            <div class="cc-info">
              <div class="cc-name">{{ c.name }}</div>
              <div class="cc-meta">{{ c.enterprise_name || c.city || '—' }}</div>
            </div>
            <div class="cc-tier" :style="{ color: tierColor[c.member_tier] || '#666' }">
              {{ tierLabel[c.member_tier] || c.member_tier }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="empty-page">
      <div>暂无数据</div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 24px;
  min-height: 100vh;
  background: #f5f6fa;
}

/* 使命愿景横幅 */
.mission-banner {
  background: linear-gradient(135deg, #1a2a3a, #2d3e52);
  border-radius: 14px;
  padding: 6px 24px;
  margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.mission-welcome {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 6px;
  letter-spacing: 1px;
}
.welcome-line {
  text-align: center;
  font-size: 18px;
  color: #666;
  margin-bottom: 2px;
}
.welcome-line-en {
  text-align: center;
  font-size: 12px;
  color: #aaa;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
}
.mission-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}
.mission-icon { font-size: 18px; }
.mission-text {
  font-size: 13px;
  color: #c9a96e;
  font-weight: 600;
  letter-spacing: 1px;
}
.mission-divider {
  color: #4a5568;
  margin: 0 4px;
}
.welcome-mission {
  font-size: 12px;
  color: #c9a96e;
  margin-top: 4px;
  font-weight: 500;
}

.top-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}
.welcome-name { font-size: 22px; font-weight: 700; color: #0a0a0a; }
.welcome-sub { font-size: 13px; color: #888; margin-top: 4px; }
.month-picker { display: flex; align-items: center; }

/* 指标卡 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  padding: 20px 24px;
  border-radius: 14px;
  color: #fff;
  position: relative;
  overflow: hidden;
}
.stat-card::after {
  content: '';
  position: absolute;
  right: -20px; bottom: -20px;
  width: 80px; height: 80px;
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
}
.gold { background: linear-gradient(135deg, #b8860b, #c9a96e); }
.purple { background: linear-gradient(135deg, #5b4fcf, #7b6fdf); }
.blue { background: linear-gradient(135deg, #1a6eb5, #4a90d9); }
.green { background: linear-gradient(135deg, #1a7a3a, #52c41a); }
.sc-value { font-size: 32px; font-weight: 800; line-height: 1; }
.sc-label { font-size: 13px; opacity: 0.9; margin-top: 8px; }
.sc-sub { font-size: 11px; opacity: 0.7; margin-top: 4px; }

/* 区块 */
.section {
  background: #fff;
  border-radius: 14px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #0a0a0a;
  margin-bottom: 16px;
}
.empty-tip { color: #bbb; font-size: 13px; text-align: center; padding: 20px 0; }

/* 城市标签 */
.city-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.city-tag {
  padding: 4px 14px;
  background: #f0f0f0;
  border-radius: 20px;
  font-size: 13px;
  color: #333;
}

/* 下店列表 */
.visit-list { display: flex; flex-direction: column; gap: 10px; }
.visit-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #f0f0f0;
}
.vi-date { font-size: 13px; font-weight: 700; color: #c9a96e; min-width: 90px; }
.vi-info { flex: 1; }
.vi-city { font-size: 13px; font-weight: 600; color: #333; }
.vi-addr { font-size: 12px; color: #888; margin-top: 2px; }
.vi-days { font-size: 11px; color: #aaa; margin-top: 2px; }
.vi-status { font-size: 12px; padding: 3px 10px; border-radius: 10px; }
.vs-confirmed { background: #f0fce0; color: #52c41a; }
.vs-pending { background: #fff8e0; color: #e6a817; }

/* 客户网格 */
.client-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.client-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #f0f0f0;
}
.cc-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, #c9a96e, #7b6fdf);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.cc-info { flex: 1; min-width: 0; }
.cc-name { font-size: 13px; font-weight: 600; color: #0a0a0a; }
.cc-meta { font-size: 11px; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cc-tier { font-size: 11px; font-weight: 600; flex-shrink: 0; }

.empty-page { text-align: center; color: #bbb; padding: 80px 0; }

/* 晋级进度 */
.promo-section { border: 2px solid #f0e6d0; background: linear-gradient(135deg, #fffdf7, #fff); }
.promo-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; font-size: 15px; }
.promo-current { color: #666; }
.promo-current strong { color: #c9a96e; font-size: 16px; }
.promo-arrow { color: #ccc; font-size: 18px; }
.promo-next strong { color: #409eff; font-size: 16px; }
.promo-bars { display: flex; flex-direction: column; gap: 14px; }
.promo-bar-item { }
.pb-label { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 13px; color: #333; }
.pb-nums { font-weight: 600; }
.pb-target { color: #909399; font-weight: 400; margin-left: 4px; }
.pb-gap { color: #e84c4c; font-size: 12px; margin-left: 8px; }
.pb-done { color: #67c23a; font-size: 12px; margin-left: 8px; }
.promo-max { text-align: center; font-size: 18px; padding: 20px; color: #c9a96e; font-weight: 700; }
</style>
