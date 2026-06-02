<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  data: any;          // 后端 GET 返回的 data
  /** 'member' 显示「服务接待指导方案」；'talent' 显示「带教指导方案」并展示匹配客户名单 */
  scene: 'member' | 'talent';
}>();

const emit = defineEmits<{ (e: 'jump-member', id: number): void }>();

const status = computed(() => props.data?.status || 'analyzed');

// 四色性格
const colorList = computed(() => {
  const c = props.data?.color_analysis || {};
  return [
    { key: 'red', label: '红·支配', value: Number(c.red || 0), color: '#ef4444' },
    { key: 'yellow', label: '黄·影响', value: Number(c.yellow || 0), color: '#f59e0b' },
    { key: 'blue', label: '蓝·分析', value: Number(c.blue || 0), color: '#3b82f6' },
    { key: 'green', label: '绿·稳定', value: Number(c.green || 0), color: '#10b981' },
  ];
});
const dominant = computed(() => props.data?.color_analysis?.dominant || '');
const colorTraits = computed(() => props.data?.color_analysis?.traits || '');

// MBTI
const mbti = computed(() => props.data?.mbti || {});
const mbtiDimsRaw = computed(() => mbti.value?.dims || {});
const mbtiDims = computed(() => [
  { k: 'energy',   label: '能量来源', v: mbtiDimsRaw.value?.energy },
  { k: 'mind',     label: '信息接收', v: mbtiDimsRaw.value?.mind },
  { k: 'nature',   label: '决策方式', v: mbtiDimsRaw.value?.nature },
  { k: 'tactics',  label: '生活方式', v: mbtiDimsRaw.value?.tactics },
  { k: 'identity', label: '自我认同', v: mbtiDimsRaw.value?.identity },
].filter(d => d.v));

// 八字
const bazi = computed(() => props.data?.bazi || {});
const baziPillars = computed(() => bazi.value?.pillars || []);

const matchedMembers = computed(() => props.data?.matched_members || []);

const guideText = computed(() =>
  props.scene === 'talent'
    ? props.data?.teaching_guide
    : props.data?.service_guide
);
const guideTitle = computed(() =>
  props.scene === 'talent' ? '🎓 带教指导方案' : '💝 服务接待指导方案'
);

function fmt(s?: string) {
  if (!s) return '';
  return s.replace(/T/, ' ').replace(/\.\d+Z?$/, '');
}
</script>

<template>
  <!-- 状态：pending -->
  <div v-if="status === 'pending'" class="da-pending">
    <div class="da-pending-icon">⏳</div>
    <div class="da-pending-title">已提交·等塔才分析</div>
    <div class="da-pending-tip">
      原始资料已交给塔才（智能体）·一般 1~5 分钟内回写分析结果·稍后刷新即可查看
    </div>
  </div>

  <!-- 状态：analyzed -->
  <div v-else class="da-view">
    <!-- 总结 -->
    <el-card v-if="data?.summary" class="da-card da-summary" shadow="never">
      <div class="da-section-title">🌟 综合画像</div>
      <div class="da-summary-text">{{ data.summary }}</div>
    </el-card>

    <!-- 四色性格 -->
    <el-card v-if="data?.color_analysis" class="da-card" shadow="never">
      <div class="da-section-title">
        🎨 四色性格分析
        <span v-if="dominant" class="da-color-dominant">主色调：{{ dominant }}</span>
      </div>

      <div class="da-color-grid">
        <div v-for="c in colorList" :key="c.key" class="da-color-item">
          <div class="da-color-label" :style="{ color: c.color }">
            <span class="da-color-dot" :style="{ background: c.color }"></span>
            {{ c.label }}
          </div>
          <div class="da-color-bar-wrap">
            <div
              class="da-color-bar"
              :style="{ width: c.value + '%', background: c.color }"
            ></div>
          </div>
          <div class="da-color-val">{{ c.value }}</div>
        </div>
      </div>

      <div v-if="colorTraits" class="da-color-traits">
        <span class="da-tag-label">特质：</span>{{ colorTraits }}
      </div>
    </el-card>

    <!-- MBTI -->
    <el-card v-if="data?.mbti" class="da-card" shadow="never">
      <div class="da-section-title">🧬 MBTI 人格类型</div>
      <div class="da-mbti-row">
        <div class="da-mbti-type">{{ mbti.type || '--' }}</div>
        <div class="da-mbti-dims">
          <div v-for="d in mbtiDims" :key="d.k" class="da-mbti-dim">
            <span class="da-mbti-dim-label">{{ d.label }}</span>
            <span class="da-mbti-dim-val">{{ d.v }}</span>
          </div>
        </div>
      </div>
      <div v-if="mbti.desc" class="da-mbti-desc">{{ mbti.desc }}</div>
    </el-card>

    <!-- 八字 -->
    <el-card v-if="data?.bazi" class="da-card" shadow="never">
      <div class="da-section-title">🀄 八字命理</div>

      <el-table v-if="baziPillars.length" :data="baziPillars" size="small" border style="width:100%; margin-bottom:12px;">
        <el-table-column prop="柱位" label="柱位" width="80" align="center" />
        <el-table-column prop="天干" label="天干" align="center" />
        <el-table-column prop="地支" label="地支" align="center" />
        <el-table-column prop="主星" label="主星" align="center" />
        <el-table-column prop="纳音" label="纳音" align="center" />
      </el-table>

      <div v-if="bazi.features" class="da-bazi-row">
        <span class="da-tag-label">命局特征：</span>{{ bazi.features }}
      </div>
      <div v-if="bazi.shensha" class="da-bazi-row">
        <span class="da-tag-label">神煞：</span>{{ bazi.shensha }}
      </div>
      <div v-if="bazi.dayun" class="da-bazi-row">
        <span class="da-tag-label">大运：</span>{{ bazi.dayun }}
      </div>
      <div v-if="bazi.liunian" class="da-bazi-row">
        <span class="da-tag-label">流年：</span>{{ bazi.liunian }}
      </div>
    </el-card>

    <!-- 特殊习惯 -->
    <el-card v-if="data?.special_habits" class="da-card" shadow="never">
      <div class="da-section-title">🔍 特殊习惯 / 注意点</div>
      <div class="da-pre">{{ data.special_habits }}</div>
    </el-card>

    <!-- 服务/带教指导方案（突出） -->
    <el-card v-if="guideText" class="da-card da-guide" shadow="never">
      <div class="da-section-title da-guide-title">{{ guideTitle }}</div>
      <div class="da-pre da-guide-text">{{ guideText }}</div>
    </el-card>

    <!-- 老师专属：匹配客户名单 -->
    <el-card v-if="scene === 'talent' && matchedMembers.length" class="da-card" shadow="never">
      <div class="da-section-title">🎯 高匹配客户名单</div>
      <el-table :data="matchedMembers" size="small" border>
        <el-table-column prop="member_id" label="ID" width="80" />
        <el-table-column prop="name" label="客户姓名" width="140" />
        <el-table-column prop="reason" label="匹配理由" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="emit('jump-member', row.member_id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 元信息 -->
    <div v-if="data?.analyzed_by || data?.analyzed_at" class="da-meta">
      分析人：{{ data?.analyzed_by || '塔才' }}
      <span style="margin-left:16px;">分析时间：{{ fmt(data?.analyzed_at) }}</span>
    </div>
  </div>
</template>

<style scoped>
.da-pending {
  text-align: center;
  padding: 60px 20px;
  background: linear-gradient(135deg, #fff8e1 0%, #fff3cd 100%);
  border: 1px dashed #f6c84d;
  border-radius: 12px;
}
.da-pending-icon { font-size: 48px; margin-bottom: 12px; }
.da-pending-title { font-size: 18px; font-weight: 600; color: #b45309; margin-bottom: 6px; }
.da-pending-tip { font-size: 13px; color: #92400e; }

.da-view { display: flex; flex-direction: column; gap: 14px; }
.da-card { border-radius: 12px; }
.da-card :deep(.el-card__body) { padding: 18px; }
.da-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.da-summary {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border: 1px solid #e9d8fd;
}
.da-summary-text {
  font-size: 14px; line-height: 1.8; color: #4c1d95;
}
.da-color-dominant {
  margin-left: auto; font-size: 12px; color: #7c3aed;
  background: #ede9fe; padding: 2px 10px; border-radius: 10px;
}

.da-color-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px 24px;
}
.da-color-item {
  display: grid; grid-template-columns: 90px 1fr 36px; align-items: center; gap: 10px;
}
.da-color-label { font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.da-color-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.da-color-bar-wrap {
  height: 12px; background: #f3f4f6; border-radius: 6px; overflow: hidden;
}
.da-color-bar {
  height: 100%; border-radius: 6px; transition: width .4s;
}
.da-color-val { font-size: 13px; color: #606266; text-align: right; font-variant-numeric: tabular-nums; }
.da-color-traits {
  margin-top: 14px; padding: 10px 12px; background: #fafafa;
  border-radius: 6px; font-size: 13px; line-height: 1.7; color: #525252;
}

.da-mbti-row {
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap; margin-bottom: 10px;
}
.da-mbti-type {
  font-size: 42px; font-weight: 800; letter-spacing: 4px;
  color: #7c3aed; min-width: 140px;
  text-shadow: 0 2px 6px rgba(124,58,237,0.2);
}
.da-mbti-dims {
  flex: 1; display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px;
}
.da-mbti-dim {
  background: #f8f9fa; padding: 8px 10px; border-radius: 6px;
}
.da-mbti-dim-label { font-size: 12px; color: #909399; display: block; }
.da-mbti-dim-val { font-size: 14px; color: #303133; font-weight: 600; }
.da-mbti-desc {
  background: #f3f4f6; padding: 12px; border-radius: 8px;
  font-size: 13px; line-height: 1.7; color: #4b5563;
}

.da-bazi-row {
  font-size: 13px; line-height: 1.8; color: #303133; padding: 4px 0;
}

.da-tag-label {
  font-weight: 600; color: #6b46c1; margin-right: 4px;
}
.da-pre {
  white-space: pre-wrap; word-break: break-word;
  font-size: 13px; line-height: 1.8; color: #303133;
}

.da-guide {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border: 2px solid #fb923c;
  position: relative;
}
.da-guide-title {
  color: #c2410c; font-size: 16px;
}
.da-guide-text {
  background: #fff; padding: 14px; border-radius: 8px;
  border-left: 4px solid #fb923c;
}

.da-meta {
  text-align: right; font-size: 12px; color: #909399; margin-top: 4px;
}
</style>
