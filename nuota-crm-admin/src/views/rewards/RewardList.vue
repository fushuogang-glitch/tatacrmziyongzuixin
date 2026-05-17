<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { API } from '../../api';

const tiers = ref<any[]>([]);
const loading = ref(false);
const filterTier = ref('');

const TIER_EMOJI: Record<string, string> = {
  kindergarten: '⚔️', primary: '💰', junior: '🏮', senior: '🔮',
  college: '🛡️', bachelor: '⭐', master: '🌙', doctor: '☀️', postdoc: '💜',
};

// SVG内联图标 —— 黑金风格星宿徽章
const TIER_SVG: Record<string, string> = {
  kindergarten: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#1a1a1a" stroke="#c9a96e" stroke-width="1.5"/><path d="M20 8l3 9h9l-7 5.5 2.5 8.5-7.5-5-7.5 5 2.5-8.5L8 17h9z" fill="none" stroke="#c9a96e" stroke-width="1.2"/><line x1="14" y1="26" x2="26" y2="14" stroke="#c9a96e" stroke-width="1.2"/><line x1="14" y1="14" x2="26" y2="26" stroke="#c9a96e" stroke-width="1.2"/></svg>`,
  primary: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#1a1a1a" stroke="#c9a96e" stroke-width="1.5"/><rect x="13" y="14" width="14" height="14" rx="2" fill="none" stroke="#c9a96e" stroke-width="1.2"/><line x1="13" y1="19" x2="27" y2="19" stroke="#c9a96e" stroke-width="1"/><circle cx="20" cy="11" r="2.5" fill="none" stroke="#c9a96e" stroke-width="1.2"/></svg>`,
  junior: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#1a1a1a" stroke="#c9a96e" stroke-width="1.5"/><path d="M20 10c-5 0-9 4-9 9s9 13 9 13 9-8 9-13-4-9-9-9z" fill="none" stroke="#c9a96e" stroke-width="1.2"/><circle cx="20" cy="19" r="3" fill="#c9a96e" opacity="0.3"/></svg>`,
  senior: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#1a1a1a" stroke="#c9a96e" stroke-width="1.5"/><circle cx="20" cy="20" r="8" fill="none" stroke="#c9a96e" stroke-width="1.2"/><circle cx="20" cy="20" r="3" fill="#c9a96e" opacity="0.4"/><line x1="20" y1="8" x2="20" y2="12" stroke="#c9a96e" stroke-width="1"/><line x1="20" y1="28" x2="20" y2="32" stroke="#c9a96e" stroke-width="1"/><line x1="8" y1="20" x2="12" y2="20" stroke="#c9a96e" stroke-width="1"/><line x1="28" y1="20" x2="32" y2="20" stroke="#c9a96e" stroke-width="1"/></svg>`,
  college: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#1a1a1a" stroke="#c9a96e" stroke-width="1.5"/><path d="M12 16l8-5 8 5v10l-8 5-8-5z" fill="none" stroke="#c9a96e" stroke-width="1.2"/><line x1="20" y1="11" x2="20" y2="31" stroke="#c9a96e" stroke-width="0.8" opacity="0.5"/></svg>`,
  bachelor: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#1a1a1a" stroke="#c9a96e" stroke-width="1.5"/><polygon points="20,8 23,16 32,16 25,21 27,30 20,25 13,30 15,21 8,16 17,16" fill="none" stroke="#c9a96e" stroke-width="1.2"/><circle cx="20" cy="18" r="2" fill="#c9a96e" opacity="0.5"/></svg>`,
  master: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#0d0d1a" stroke="#c9a96e" stroke-width="1.5"/><path d="M20 10a10 10 0 0 1 0 20" fill="none" stroke="#c9a96e" stroke-width="1.5"/><path d="M20 13a7 7 0 0 0 0 14" fill="#c9a96e" opacity="0.15"/><circle cx="16" cy="17" r="1" fill="#c9a96e" opacity="0.6"/><circle cx="23" cy="23" r="0.8" fill="#c9a96e" opacity="0.4"/></svg>`,
  doctor: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#1a1408" stroke="#c9a96e" stroke-width="1.5"/><circle cx="20" cy="20" r="6" fill="#c9a96e" opacity="0.2" stroke="#c9a96e" stroke-width="1.2"/><line x1="20" y1="8" x2="20" y2="14" stroke="#c9a96e" stroke-width="1.2"/><line x1="20" y1="26" x2="20" y2="32" stroke="#c9a96e" stroke-width="1.2"/><line x1="8" y1="20" x2="14" y2="20" stroke="#c9a96e" stroke-width="1.2"/><line x1="26" y1="20" x2="32" y2="20" stroke="#c9a96e" stroke-width="1.2"/><line x1="11.5" y1="11.5" x2="15.8" y2="15.8" stroke="#c9a96e" stroke-width="1"/><line x1="24.2" y1="24.2" x2="28.5" y2="28.5" stroke="#c9a96e" stroke-width="1"/><line x1="28.5" y1="11.5" x2="24.2" y2="15.8" stroke="#c9a96e" stroke-width="1"/><line x1="15.8" y1="24.2" x2="11.5" y2="28.5" stroke="#c9a96e" stroke-width="1"/></svg>`,
  postdoc: `<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="18" fill="#120820" stroke="#c9a96e" stroke-width="2"/><polygon points="20,7 23,16 32,16 25,22 27,31 20,26 13,31 15,22 8,16 17,16" fill="none" stroke="#c9a96e" stroke-width="1.5"/><circle cx="20" cy="19" r="4" fill="#7b2d8e" opacity="0.4" stroke="#c9a96e" stroke-width="0.8"/><circle cx="20" cy="19" r="1.5" fill="#c9a96e" opacity="0.6"/></svg>`,
};

const TIER_COLORS: Record<string, string> = {
  kindergarten: '#708090', primary: '#4a7c9b', junior: '#5a8a6e', senior: '#8b6fcf',
  college: '#5b8daf', bachelor: '#c9a96e', master: '#6b7db3', doctor: '#d4952a', postdoc: '#9b3da0',
};

async function load() {
  loading.value = true;
  try {
    tiers.value = (await API.membersByTier() as any) || [];
  } finally {
    loading.value = false;
  }
}

const filteredTiers = computed(() => {
  if (!filterTier.value) return tiers.value;
  return tiers.value.filter((t: any) => t.tier_code === filterTier.value);
});

const totalMembers = computed(() => tiers.value.reduce((s: number, t: any) => s + t.count, 0));

function typeLabel(t: string) {
  return { trial: '试听', annual: '年费', vip: 'VIP' }[t] || t;
}
function typeTag(t: string) {
  return { trial: 'info', annual: 'success', vip: 'warning' }[t] || '';
}
function statusTag(s: string) {
  return { active: 'success', expired: 'info', frozen: 'danger' }[s] || '';
}

onMounted(load);
</script>

<template>
  <div>
    <el-card>
      <div class="header-bar">
        <div class="title-section">
          <h2 style="margin: 0; font-size: 20px;">权益台账</h2>
          <span style="color: #909399; font-size: 14px; margin-left: 12px;">共 {{ totalMembers }} 名学员</span>
        </div>
        <div class="toolbar">
          <el-select v-model="filterTier" placeholder="筛选等级" clearable style="width: 160px;" @change="() => {}">
            <el-option v-for="t in tiers" :key="t.tier_code"
              :label="`${TIER_EMOJI[t.tier_code] || ''} ${t.tier_name}（${t.count}人）`"
              :value="t.tier_code" />
          </el-select>
          <el-button @click="load" :loading="loading">刷新</el-button>
        </div>
      </div>
    </el-card>

    <div v-loading="loading" class="tier-grid">
      <el-card v-for="tier in filteredTiers" :key="tier.tier_code" class="tier-card" shadow="hover"
        :style="{ borderLeftColor: TIER_COLORS[tier.tier_code] || '#c9a96e' }">
        <template #header>
          <div class="tier-header">
            <div class="tier-title">
              <span class="tier-icon" v-html="TIER_SVG[tier.tier_code]"></span>
              <span class="tier-name">{{ tier.tier_name }}</span>
              <el-tag :color="TIER_COLORS[tier.tier_code]" style="color: #fff; border: none; margin-left: 8px;">
                Lv.{{ tier.tier_level }}
              </el-tag>
              <span class="tier-count">{{ tier.count }} 人</span>
            </div>
          </div>
          <div v-if="tier.benefits && tier.benefits.length" class="benefits-list">
            <span v-for="(b, i) in tier.benefits" :key="i" class="benefit-tag">✦ {{ b }}</span>
          </div>
          <div v-else class="benefits-list">
            <span class="benefit-tag benefit-none">暂无特殊权益</span>
          </div>
        </template>

        <div v-if="tier.members.length === 0" class="empty-tier">
          <span style="color: #c0c4cc;">暂无学员</span>
        </div>
        <el-table v-else :data="tier.members" stripe size="small" :show-header="true">
          <el-table-column prop="member_no" label="编号" width="130" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="phone" label="手机" width="130" />
          <el-table-column prop="enterprise_name" label="企业" min-width="140" />
          <el-table-column prop="city" label="城市" width="90" />
          <el-table-column label="会员" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="typeTag(row.member_type)">{{ typeLabel(row.member_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="statusTag(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title-section { display: flex; align-items: baseline; }
.toolbar { display: flex; gap: 12px; }

.tier-grid {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.tier-card {
  border-left: 4px solid #409eff;
}
.tier-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tier-title {
  display: flex;
  align-items: center;
  gap: 6px;
}
.tier-icon { width: 36px; height: 36px; display: inline-flex; flex-shrink: 0; }
.tier-icon svg { width: 100%; height: 100%; }
.tier-name { font-size: 18px; font-weight: 600; }
.tier-count {
  margin-left: 12px;
  color: #909399;
  font-size: 14px;
}
.benefits-list {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.benefit-tag {
  font-size: 12px;
  color: #e6a817;
  background: #fdf6e3;
  padding: 2px 8px;
  border-radius: 4px;
}
.benefit-none {
  color: #c0c4cc;
  background: #f5f5f5;
}
.empty-tier {
  text-align: center;
  padding: 24px 0;
}
</style>
