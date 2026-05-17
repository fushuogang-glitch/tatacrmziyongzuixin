<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);
const services = ref<any[]>([]); // 动态服务项目库
const branches = ref<any[]>([]); // 分公司列表
const dialog = reactive({ visible: false, mode: 'create' as 'create' | 'edit', form: {} as any });

async function loadServices() {
  try {
    const d: any = await API.serviceList();
    services.value = (d || []).filter((s: any) => s.status === 'active');
  } catch { services.value = []; }
}

// 按分类分组
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
  dialog.form = { name: '', phone: '', specialty: '', company: '', branch_id: null, service_ids: [], monthly_days: 14, course_days: 8, level: 'trainee', status: 'active' };
  dialog.visible = true;
}
function openEdit(row: any) {
  dialog.mode = 'edit';
  dialog.form = { ...row, service_ids: row.service_ids || [] };
  dialog.visible = true;
}

async function submit() {
  const body = {
    name: dialog.form.name,
    phone: dialog.form.phone,
    specialty: dialog.form.specialty,
    company: dialog.form.company,
    service_modules: JSON.stringify([]),  // 保留兼容旧字段
    service_ids: dialog.form.service_ids || [],
    monthly_days: dialog.form.monthly_days,
    course_days: dialog.form.course_days,
    branch_id: dialog.form.branch_id || null,
    level: dialog.form.level || 'trainee',
    status: dialog.form.status,
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

function getServiceNames(row: any) {
  const ids = row.service_ids || [];
  if (!ids.length) return '-';
  return ids.map((id: number) => {
    const s = services.value.find((sv: any) => sv.id === id);
    return s ? s.name : `#${id}`;
  }).join('、');
}

function statusTag(s: string) {
  return { active: 'success', inactive: 'info' }[s] || '';
}

const levelLabels: Record<string, string> = {
  trainee: '培训期', probation: '考核期', pm: '项目经理', pd: '项目总监',
  junior_partner: '初级合伙人', partner: '合伙人', senior_partner: '高级合伙人', founding_partner: '创始合伙人',
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

      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="id" label="ID" width="60" />
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
</style>
