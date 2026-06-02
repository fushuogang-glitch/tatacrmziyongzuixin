<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ArrowLeft } from '@element-plus/icons-vue';
import { API } from '../../api';
import DeepAnalysisView from '../../components/deep-analysis/DeepAnalysisView.vue';
import DeepAnalysisForm from '../../components/deep-analysis/DeepAnalysisForm.vue';

const router = useRouter();

// 三种视图：list / detail / create
const view = ref<'list' | 'detail' | 'create'>('list');

// 列表
const listLoading = ref(false);
const listRows = ref<any[]>([]);
const search = reactive({ keyword: '', status: '' });

async function loadList() {
  listLoading.value = true;
  try {
    const params: any = {};
    if (search.keyword) params.keyword = search.keyword;
    if (search.status) params.status = search.status;
    const res: any = await API.talentAnalysisList(params);
    listRows.value = Array.isArray(res) ? res : (res?.list || res?.items || []);
  } catch {
    listRows.value = [];
  } finally {
    listLoading.value = false;
  }
}

// 详情
const detailLoading = ref(false);
const detailData = ref<any>(null);
const currentConsultant = ref<any>(null);
const showEditForm = ref(false);

async function openDetail(row: any) {
  currentConsultant.value = row;
  view.value = 'detail';
  showEditForm.value = false;
  detailLoading.value = true;
  detailData.value = null;
  try {
    const res: any = await API.consultantTalentAnalysis(row.consultant_id || row.id);
    detailData.value = res || null;
  } finally {
    detailLoading.value = false;
  }
}

const detailSubmitter = (body: { raw_text: string; raw_images: string[] }) => {
  const cid = currentConsultant.value?.consultant_id || currentConsultant.value?.id;
  return API.consultantTalentAnalysisSubmit(cid, body);
};

async function onDetailSubmitted() {
  showEditForm.value = false;
  if (currentConsultant.value) {
    await openDetail(currentConsultant.value);
  }
}

// 新增
const createForm = reactive({ consultant_id: 0 });
const consultantOptions = ref<any[]>([]);

async function openCreate() {
  view.value = 'create';
  createForm.consultant_id = 0;
  if (consultantOptions.value.length === 0) {
    try {
      const res: any = await API.consultantList();
      consultantOptions.value = Array.isArray(res) ? res : (res?.list || res?.items || []);
    } catch {
      consultantOptions.value = [];
    }
  }
}

const createSubmitter = (body: { raw_text: string; raw_images: string[] }) => {
  if (!createForm.consultant_id) {
    ElMessage.warning('请先选择老师');
    return Promise.reject(new Error('no consultant'));
  }
  return API.consultantTalentAnalysisSubmit(createForm.consultant_id, body);
};

async function onCreateSubmitted() {
  ElMessage.success('已提交·等塔才回写');
  view.value = 'list';
  await loadList();
}

// 跳转客户详情
function jumpMember(id: number) {
  router.push(`/members/${id}`);
}

function statusTag(s: string) {
  if (s === 'analyzed') return 'success';
  if (s === 'pending') return 'warning';
  return 'info';
}
function statusLabel(s: string) {
  if (s === 'analyzed') return '✅ 已分析';
  if (s === 'pending') return '⏳ 分析中';
  return '— 未录入';
}

function fmt(s?: string) {
  if (!s) return '-';
  return s.replace(/T/, ' ').replace(/\.\d+Z?$/, '');
}

const headerTitle = computed(() => {
  if (view.value === 'list') return '🎯 老师人才模型分析';
  if (view.value === 'detail') {
    const name = currentConsultant.value?.real_name || currentConsultant.value?.name || '';
    return `🎯 ${name} · 人才模型详情`;
  }
  return '📥 录入老师原始资料';
});

onMounted(loadList);
</script>

<template>
  <div class="talent-page">
    <!-- 头部 -->
    <div class="talent-header">
      <el-button v-if="view !== 'list'" link @click="view = 'list'; loadList()">
        <el-icon><ArrowLeft /></el-icon>
        返回列表
      </el-button>
      <div class="talent-title">{{ headerTitle }}</div>
      <div style="margin-left:auto;">
        <el-button v-if="view === 'list'" type="primary" @click="openCreate">
          📥 录入老师原始资料
        </el-button>
      </div>
    </div>

    <!-- 列表 -->
    <el-card v-if="view === 'list'" v-loading="listLoading">
      <div style="display:flex; gap:10px; margin-bottom:14px;">
        <el-input
          v-model="search.keyword"
          placeholder="搜索老师姓名 / 手机"
          clearable
          style="width:220px;"
          @keyup.enter="loadList"
        />
        <el-select v-model="search.status" placeholder="状态" clearable style="width:140px;" @change="loadList">
          <el-option label="已分析" value="analyzed" />
          <el-option label="分析中" value="pending" />
        </el-select>
        <el-button type="primary" @click="loadList">查询</el-button>
      </div>

      <el-table :data="listRows" stripe>
        <el-table-column prop="consultant_id" label="ID" width="80" />
        <el-table-column label="老师姓名" min-width="140">
          <template #default="{ row }">
            {{ row.real_name || row.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="手机" width="140">
          <template #default="{ row }">
            {{ row.phone || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="MBTI" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.mbti_type" class="mbti-mini">{{ row.mbti_type }}</span>
            <span v-else style="color:#c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="主性格" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.dominant_color">{{ row.dominant_color }}</span>
            <span v-else style="color:#c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分析时间" width="170">
          <template #default="{ row }">{{ fmt(row.analyzed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="listRows.length === 0 && !listLoading" description="暂无老师分析记录" />
    </el-card>

    <!-- 详情 -->
    <div v-if="view === 'detail'" v-loading="detailLoading">
      <div style="margin-bottom:14px; text-align:right;">
        <el-button
          v-if="detailData && !showEditForm"
          type="primary"
          plain
          @click="showEditForm = true"
        >📝 重新录入资料</el-button>
        <el-button v-if="showEditForm" @click="showEditForm = false">取消</el-button>
      </div>

      <el-card v-if="showEditForm || !detailData" style="margin-bottom:14px;">
        <DeepAnalysisForm
          :submitter="detailSubmitter"
          :initial-text="detailData?.raw_text || ''"
          :initial-images="detailData?.raw_images || []"
          @submitted="onDetailSubmitted"
        />
      </el-card>

      <DeepAnalysisView
        v-if="detailData"
        :data="detailData"
        scene="talent"
        @jump-member="jumpMember"
      />
    </div>

    <!-- 新增（选老师 + 录入） -->
    <el-card v-if="view === 'create'">
      <el-form label-width="100px" style="max-width:600px; margin-bottom:18px;">
        <el-form-item label="选择老师" required>
          <el-select
            v-model="createForm.consultant_id"
            placeholder="请选择老师"
            filterable
            style="width:100%;"
          >
            <el-option
              v-for="c in consultantOptions"
              :key="c.id"
              :label="(c.real_name || c.name || '') + (c.phone ? ` · ${c.phone}` : '')"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <DeepAnalysisForm
        :submitter="createSubmitter"
        @submitted="onCreateSubmitted"
      />
    </el-card>
  </div>
</template>

<style scoped>
.talent-page { padding: 6px 0; }
.talent-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 16px;
}
.talent-title {
  font-size: 18px; font-weight: 600; color: #303133;
}
.mbti-mini {
  display: inline-block; padding: 2px 8px;
  background: #ede9fe; color: #6b46c1;
  border-radius: 4px; font-size: 12px; font-weight: 600; letter-spacing: 1px;
}
</style>
