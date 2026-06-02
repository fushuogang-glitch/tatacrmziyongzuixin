<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);
const services = ref<any[]>([]);
const branches = ref<any[]>([]);
const dialog = reactive({ visible: false, mode: 'create' as 'create' | 'edit', form: {} as any });
const avatarUploading = ref(false);
const expandedRows = ref<number[]>([]);
const statsCache = ref<Record<number, any>>({});
const statsLoading = ref<Record<number, boolean>>({});
const statsMonthStr = ref(`${new Date().getFullYear()}-${String(new Date().getMonth()+1).padStart(2,'0')}`);
const statsMonth = computed({
  get: () => statsMonthStr.value,
  set: (v: string) => { statsMonthStr.value = v; }
});
const statsYear = computed(() => parseInt(statsMonthStr.value.split('-')[0]));
const statsMonthNum = computed(() => parseInt(statsMonthStr.value.split('-')[1]));

const BASE_URL = import.meta.env.VITE_API_BASE || '';

async function loadServices() {
  try {
    const d: any = await API.serviceList();
    services.value = (d || []).filter((s: any) => s.status === 'active');
  } catch { services.value = []; }
}

const servicesByCategory = computed(() => {
  const map: Record<string, any[]> = {};
  for (const s of services.value) {
    const cat = s.category || '其他';
    if (!map[cat]) map[cat] = [];
    map[cat].push(s);
  }
  return map;
});

async function load() {
  loading.value = true;
  try {
    rows.value = (await API.consultantList() as any) || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  dialog.mode = 'create';
  dialog.form = { name: '', phone: '', specialty: '', company: '', branch_id: null, service_ids: [], monthly_days: 14, course_days: 8, level: 'trainee', status: 'active', avatar: '', position: null, referrer_id: null, mentor_id: null };
  dialog.visible = true;
}
function openEdit(row: any) {
  dialog.mode = 'edit';
  dialog.form = { ...row, service_ids: row.service_ids || [], avatar: row.avatar || '', position: row.position || null, referrer_id: row.referrer_id || null, mentor_id: row.mentor_id || null };
  dialog.visible = true;
}

async function handleAvatarUpload(file: any) {
  avatarUploading.value = true;
  try {
    const res: any = await API.uploadImage(file.raw || file);
    dialog.form.avatar = res.url;
    ElMessage.success('头像上传成功');
  } catch (e) {
    ElMessage.error('上传失败');
  } finally {
    avatarUploading.value = false;
  }
  return false; // 阻止默认上传
}

function avatarUrl(url: string) {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return BASE_URL + url;
}

async function submit() {
  const body: any = {
    name: dialog.form.name,
    phone: dialog.form.phone,
    specialty: dialog.form.specialty,
    company: dialog.form.company,
    service_modules: JSON.stringify([]),
    service_ids: dialog.form.service_ids || [],
    monthly_days: dialog.form.monthly_days,
    course_days: dialog.form.course_days,
    branch_id: dialog.form.branch_id || null,
    level: dialog.form.level || 'trainee',
    status: dialog.form.status,
    avatar: dialog.form.avatar || null,
    position: dialog.form.position || null,
    referrer_id: dialog.form.referrer_id || null,
    mentor_id: dialog.form.mentor_id || null,
  };
  if (dialog.mode === 'create') {
    await API.consultantCreate(body);
    ElMessage.success('新增成功');
  } else {
    await API.consultantUpdate(dialog.form.id, body);
    ElMessage.success('保存成功');
  }
  dialog.visible = false;
  load();
}

function statusTag(s: string) {
  return { active: 'success', inactive: 'info' }[s] || '';
}

const levelLabels: Record<string, string> = {
  trainee: '培训期 T', probation: '考核期 P', pm: '项目经理 PM', pd: '项目总监 PD',
  junior_partner: '初级合伙人 JP', partner: '中级合伙人 MP', senior_partner: '高级合伙人 SP', founding_partner: '创始合伙人 FP',
};
function levelLabel(l: string) { return levelLabels[l] || l || '培训期'; }
function levelTag(l: string) {
  if (['founding_partner', 'senior_partner'].includes(l)) return 'danger';
  if (['partner', 'junior_partner'].includes(l)) return 'warning';
  if (['pd', 'pm'].includes(l)) return 'success';
  return 'info';
}

const categoryColors: Record<string, string> = {
  '专案': '#e6a23c',
  '课程': '#409eff',
  '发展': '#67c23a',
  '增长': '#f56c6c',
  '供应商服务': '#909399',
};

async function loadBranches() {
  try { branches.value = (await API.branchList('active') as any) || []; } catch { branches.value = []; }
}

onMounted(() => { load(); loadServices(); loadBranches(); });

async function loadStats(cid: number) {
  if (statsCache.value[cid]) return;
  statsLoading.value[cid] = true;
  try {
    const res: any = await API.get(`/admin/consultants/${cid}/monthly-stats?year=${statsYear.value}&month=${statsMonthNum.value}`);
    statsCache.value[cid] = res?.data || res || {};
  } catch { statsCache.value[cid] = {}; }
  finally { statsLoading.value[cid] = false; }
}

function handleExpand(row: any, expanded: any[]) {
  const isExpanded = expanded.some((r: any) => r.id === row.id);
  if (isExpanded) {
    loadStats(row.id);
  }
}

async function changeStatsMonth(cid: number) {
  // 清除所有缓存，切换月份后重新加载
  statsCache.value = {};
  await loadStats(cid);
}
</script>

<template>
  <div>
    <el-card>
      <div class="toolbar">
        <el-button type="primary" @click="openCreate">新增老师</el-button>
        <el-button @click="load">刷新</el-button>
      </div>

      <el-alert type="info" :closable="false" style="margin-top: 12px;"
        title="名额规则：每位老师每月可下店次数 = (22工作日 - 课程日 - 2缓冲日) ÷ 2天 ≈ 6次" />

      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;" @expand-change="handleExpand" row-key="id">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="stats-panel" v-loading="statsLoading[row.id]">
              <div class="stats-month-picker">
                <el-date-picker v-model="statsMonthStr" type="month" value-format="YYYY-MM" format="YYYY年MM月"
                  size="small" style="width:160px" @change="changeStatsMonth(row.id)" />
              </div>
              <el-table :data="[statsCache[row.id]]" v-if="statsCache[row.id]" size="small" border style="width:100%">
                <el-table-column label="主案天数" align="center" width="80">
                  <template #default="{ row: s }">{{ s.main_days || 0 }}</template>
                </el-table-column>
                <el-table-column label="助理天数" align="center" width="80">
                  <template #default="{ row: s }">{{ s.assist_days || 0 }}</template>
                </el-table-column>
                <el-table-column label="归属会员" align="center" width="80">
                  <template #default="{ row: s }">{{ s.member_count || 0 }}</template>
                </el-table-column>
                <el-table-column label="跟进客户" align="center" width="80">
                  <template #default="{ row: s }">{{ s.active_clients || 0 }}</template>
                </el-table-column>
                <el-table-column label="主案客户" align="center" width="80">
                  <template #default="{ row: s }">{{ s.main_clients || 0 }}</template>
                </el-table-column>
                <el-table-column label="助理客户" align="center" width="80">
                  <template #default="{ row: s }">{{ s.assist_clients || 0 }}</template>
                </el-table-column>
                <el-table-column label="销售额" align="center" width="100">
                  <template #default="{ row: s }">¥{{ (s.sales || 0).toLocaleString() }}</template>
                </el-table-column>
                <el-table-column label="消耗额" align="center" width="100">
                  <template #default="{ row: s }">¥{{ (s.consumption || 0).toLocaleString() }}</template>
                </el-table-column>
                <el-table-column label="课程报名" align="center" width="80">
                  <template #default="{ row: s }">{{ s.course_enrolled || 0 }}</template>
                </el-table-column>
                <el-table-column label="课程参加" align="center" width="80">
                  <template #default="{ row: s }">{{ s.course_attended || 0 }}</template>
                </el-table-column>
              </el-table>
              <div v-else style="color:#999;padding:20px;text-align:center;">暂无数据</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="头像" width="70" align="center">
          <template #default="{ row }">
            <el-avatar v-if="row.avatar" :src="avatarUrl(row.avatar)" :size="40" />
            <el-avatar v-else :size="40" style="background:#c9a96e;font-size:16px;">{{ row.name?.charAt(0) || '?' }}</el-avatar>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="phone" label="手机" width="130" />
        <el-table-column prop="specialty" label="专业领域" width="130" />
        <el-table-column label="所属分公司" width="130">
          <template #default="{ row }">
            {{ row.branch_name || row.company || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="级别" width="110">
          <template #default="{ row }">
            <el-tag :type="levelTag(row.level)" size="small">{{ levelLabel(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="负责服务模块" min-width="250">
          <template #default="{ row }">
            <template v-if="row.service_ids && row.service_ids.length">
              <el-tag v-for="sid in row.service_ids" :key="sid" size="small" style="margin: 2px 4px 2px 0;"
                :color="categoryColors[services.find(s => s.id === sid)?.category] || '#409eff'" effect="dark">
                {{ services.find(s => s.id === sid)?.name || `#${sid}` }}
              </el-tag>
            </template>
            <span v-else style="color: #c0c4cc;">未配置</span>
          </template>
        </el-table-column>
        <el-table-column label="每月下店" width="90" align="center">
          <template #default="{ row }">{{ row.monthly_days }}天</template>
        </el-table-column>
        <el-table-column label="课程占用" width="90" align="center">
          <template #default="{ row }">{{ row.course_days }}天</template>
        </el-table-column>
        <el-table-column label="推荐码" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.referral_code" type="warning" effect="plain" style="font-family:monospace;letter-spacing:1px;">{{ row.referral_code }}</el-tag>
            <span v-else style="color:#c0c4cc">未生成</span>
          </template>
        </el-table-column>
        <el-table-column label="推荐人" width="90">
          <template #default="{ row }">{{ row.referrer_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="带教人" width="90">
          <template #default="{ row }">{{ row.mentor_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="岗位" width="140">
          <template #default="{ row }">{{ row.position || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ row.status === 'active' ? '在岗' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="80">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增老师' : '编辑老师'" width="580px">
      <el-form :model="dialog.form" label-width="130px">
        <el-form-item label="头像">
          <div class="avatar-upload">
            <el-upload
              class="avatar-uploader"
              :show-file-list="false"
              :auto-upload="false"
              accept="image/*"
              @change="handleAvatarUpload"
            >
              <el-avatar v-if="dialog.form.avatar" :src="avatarUrl(dialog.form.avatar)" :size="80" />
              <div v-else class="avatar-placeholder">
                <el-icon :size="28"><Plus /></el-icon>
                <span>上传头像</span>
              </div>
            </el-upload>
            <span v-if="avatarUploading" style="color:#409eff;font-size:12px;margin-left:12px;">上传中...</span>
          </div>
        </el-form-item>
        <el-form-item label="姓名" required><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="手机"><el-input v-model="dialog.form.phone" /></el-form-item>
        <el-form-item label="专业领域"><el-input v-model="dialog.form.specialty" placeholder="如：皮肤管理、仪器操作" /></el-form-item>
        <el-form-item label="所属分公司">
          <el-select v-model="dialog.form.branch_id" placeholder="请选择分公司" style="width:100%" clearable>
            <el-option v-for="b in branches" :key="b.id" :label="b.short_name || b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责服务模块">
          <div class="service-select-box">
            <template v-for="(items, cat) in servicesByCategory" :key="cat">
              <div class="service-category">
                <span class="cat-label" :style="{ color: categoryColors[cat] || '#606266' }">{{ cat }}</span>
              </div>
              <el-checkbox-group v-model="dialog.form.service_ids">
                <el-checkbox v-for="s in items" :key="s.id" :value="s.id" style="width: 100%; margin-bottom: 4px;">
                  {{ s.name }}
                </el-checkbox>
              </el-checkbox-group>
            </template>
          </div>
        </el-form-item>
        <el-form-item label="每月可下店天数"><el-input-number v-model="dialog.form.monthly_days" :min="0" :max="31" /></el-form-item>
        <el-form-item label="每月课程占用"><el-input-number v-model="dialog.form.course_days" :min="0" :max="31" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="dialog.form.status">
            <el-option label="在岗" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="dialog.form.level" placeholder="请选择" style="width:100%">
            <el-option label="🌱 培训期" value="trainee" />
            <el-option label="📝 考核期" value="probation" />
            <el-option label="💼 项目经理" value="pm" />
            <el-option label="📣 项目总监" value="pd" />
            <el-option label="⭐ 初级合伙人" value="junior_partner" />
            <el-option label="🌟 合伙人" value="partner" />
            <el-option label="👑 高级合伙人" value="senior_partner" />
            <el-option label="💎 创始合伙人" value="founding_partner" />
          </el-select>
        </el-form-item>
        <el-form-item label="推荐码" v-if="dialog.mode === 'edit' && dialog.form.referral_code">
          <el-input :model-value="dialog.form.referral_code" disabled style="font-family:monospace;letter-spacing:2px;" />
          <div style="font-size:12px;color:#909399;margin-top:4px">老师专属推荐码，新客注册时输入可自动归属到该老师</div>
        </el-form-item>
        <el-form-item label="岗位">
          <el-select v-model="dialog.form.position" placeholder="无岗位" clearable style="width:100%">
            <el-option label="人力组织总监" value="人力组织总监" />
            <el-option label="销售总监" value="销售总监" />
            <el-option label="品牌线上运营总监" value="品牌线上运营总监" />
            <el-option label="财务总监" value="财务总监" />
            <el-option label="运营总经理" value="运营总经理" />
            <el-option label="运营总助" value="运营总助" />
            <el-option label="分公司总经理（人才发展官）" value="分公司总经理（人才发展官）" />
          </el-select>
        </el-form-item>
        <el-form-item label="推荐人">
          <el-select v-model="dialog.form.referrer_id" placeholder="无推荐人" clearable filterable style="width:100%">
            <el-option v-for="c in rows.filter(r => r.id !== dialog.form.id)" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="带教人（师父）">
          <el-select v-model="dialog.form.mentor_id" placeholder="无带教人" clearable filterable style="width:100%">
            <el-option v-for="c in rows.filter(r => r.id !== dialog.form.id)" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; }
.service-select-box {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
}
.service-category {
  margin-top: 8px;
  margin-bottom: 4px;
}
.service-category:first-child { margin-top: 0; }
.cat-label {
  font-weight: 600;
  font-size: 13px;
}
.avatar-upload {
  display: flex;
  align-items: center;
}
.avatar-uploader {
  cursor: pointer;
}
.avatar-placeholder {
  width: 80px;
  height: 80px;
  border: 2px dashed #dcdfe6;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 12px;
  gap: 4px;
  transition: border-color 0.3s;
}
.avatar-placeholder:hover {
  border-color: #c9a96e;
  color: #c9a96e;
}
.stats-panel {
  padding: 16px 24px;
  background: #fafafa;
  border-radius: 8px;
}
.stats-month-picker {
  margin-bottom: 8px;
}
</style>
