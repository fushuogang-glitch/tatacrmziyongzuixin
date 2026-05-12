<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { API } from '../../api';

const data = reactive<any>({
  total_members: 0,
  new_this_month: 0,
  trial_conv: 0,
  year_income: 0,
  month_income: 0,
  refer_conv: 0,
  month_visit: 0,
  reward_pending: 0,
});
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const d: any = await API.dashboard();
    Object.assign(data, d);
  } finally {
    loading.value = false;
  }
}

function yuan(v: number) {
  if (!v) return '¥0';
  if (v >= 10000) return `¥${(v / 10000).toFixed(2)}万`;
  return `¥${v.toFixed(2)}`;
}

onMounted(load);
</script>

<template>
  <div v-loading="loading">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="metric">
          <div class="label">总学员数</div>
          <div class="value">{{ data.total_members }}</div>
          <div class="sub">累计注册</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric">
          <div class="label">本月新增</div>
          <div class="value">{{ data.new_this_month }}</div>
          <div class="sub">本月新学员</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric">
          <div class="label">试听转正率</div>
          <div class="value">{{ data.trial_conv }}%</div>
          <div class="sub">trial → annual</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric">
          <div class="label">推荐转化率</div>
          <div class="value">{{ data.refer_conv }}%</div>
          <div class="sub">推荐已确认比</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="6">
        <el-card class="metric income">
          <div class="label">年度收入</div>
          <div class="value">{{ yuan(data.year_income) }}</div>
          <div class="sub">当年缴费累计</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric income">
          <div class="label">本月收入</div>
          <div class="value">{{ yuan(data.month_income) }}</div>
          <div class="sub">本月缴费累计</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric">
          <div class="label">本月下店</div>
          <div class="value">{{ data.month_visit }}</div>
          <div class="sub">已确认 / 已完成</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric warn">
          <div class="label">权益待兑</div>
          <div class="value">{{ data.reward_pending }}</div>
          <div class="sub">available 状态</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px;">
      <template #header>
        <span>快捷操作</span>
      </template>
      <el-space wrap>
        <el-button type="primary" @click="$router.push('/members')">学员管理</el-button>
        <el-button @click="$router.push('/sessions')">场次管理</el-button>
        <el-button @click="$router.push('/bookings')">下店预约</el-button>
        <el-button @click="$router.push('/referrals')">推荐管理</el-button>
        <el-button @click="$router.push('/quota')">名额管理</el-button>
        <el-button @click="load">刷新看板</el-button>
      </el-space>
    </el-card>
  </div>
</template>

<style scoped>
.metric { text-align: center; }
.metric .label { font-size: 13px; color: #909399; }
.metric .value { font-size: 32px; font-weight: 700; margin: 12px 0 6px; color: #1f2d3d; }
.metric .sub { font-size: 12px; color: #c0c4cc; }
.metric.income .value { color: #67C23A; }
.metric.warn .value { color: #E6A23C; }
</style>
