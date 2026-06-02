<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const user = useUserStore();
const loading = ref(false);
const activeTab = ref('pending');
const rows = ref<any[]>([]);
const reviewDialog = reactive({ visible: false, row: null as any, action: '', note: '', level: 'trainee', position: '', branch_id: null as number | null });
const transferDialog = reactive({
  visible: false,
  fromId: 0,
  fromName: '',
  toId: null as number | null,
  memberIds: null as number[] | null,
});
const consultants = ref<any[]>([]);
const branches = ref<any[]>([]);

const levelOptions = [
  { value: 'probation', label: '考核期 P' },
  { value: 'trainee', label: '培训期 T' },
  { value: 'pm', label: '项目经理 PM' },
  { value: 'pd', label: '项目总监 PD' },
  { value: 'jp', label: '初级合伙人 JP' },
  { value: 'mp', label: '中级合伙人 MP' },
  { value: 'sp', label: '高级合伙人 SP' },
  { value: 'fp', label: '创始合伙人 FP' },
];

const positionOptions = [
  '人力组织总监', '运营总监', '教学总监',
  '品牌总监', '客服总监', '技术总监', '分公司负责人'
];

import { reactive } from 'vue';

async function loadApps(status = 'pending') {
  loading.value = true;
  try {
    const res: any = await API.get(`/admin/consultant-auth/applications?status=${status}`);
    rows.value = Array.isArray(res) ? res : (res?.data || []);
  } catch (e) {
    ElMessage.error('加载失败');
  } finally {
    loading.value = false;
  }
}

async function loadConsultants() {
  try {
    const res: any = await API.get('/admin/consultants');
    consultants.value = Array.isArray(res) ? res : (res?.data || []);
  } catch { }
}

async function loadBranches() {
  try {
    const res: any = await API.get('/admin/branches');
    branches.value = Array.isArray(res) ? res : (res?.data || []);
  } catch { }
}

function openReview(row: any, action: string) {
  reviewDialog.row = row;
  reviewDialog.action = action;
  reviewDialog.note = '';
  reviewDialog.level = 'trainee';
  reviewDialog.position = '';
  reviewDialog.branch_id = null;
  reviewDialog.visible = true;
  loadBranches();
}

async function submitReview() {
  loading.value = true;
  try {
    const source = reviewDialog.row.source || 'application';
    await API.post(`/admin/consultant-auth/applications/${reviewDialog.row.id}/review?source=${source}`, {
      action: reviewDialog.action,
      note: reviewDialog.note,
      level: reviewDialog.level,
      position: reviewDialog.position || null,
      branch_id: reviewDialog.branch_id || null,
    });
    ElMessage.success(reviewDialog.action === 'approve' ? '已通过审核' : '已拒绝');
    reviewDialog.visible = false;
    loadApps(activeTab.value);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败');
  } finally {
    loading.value = false;
  }
}

function openTransfer(row: any) {
  transferDialog.fromId = row.id;
  transferDialog.fromName = row.name;
  transferDialog.toId = null;
  transferDialog.memberIds = null;
  transferDialog.visible = true;
  loadConsultants();
}

async function submitTransfer() {
  if (!transferDialog.toId) { ElMessage.warning('请选择接手老师'); return; }
  await ElMessageBox.confirm(
    `确认将【${transferDialog.fromName}】名下所有客户转绑给所选老师？`,
    '客户转绑确认', { type: 'warning' }
  );
  loading.value = true;
  try {
    const res: any = await API.post('/admin/consultant-auth/transfer-members', {
      from_consultant_id: transferDialog.fromId,
      to_consultant_id: transferDialog.toId,
      member_ids: transferDialog.memberIds,
    });
    ElMessage.success(res.data?.msg || '转绑成功');
    transferDialog.visible = false;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '转绑失败');
  } finally {
    loading.value = false;
  }
}

async function genInviteCode(consultantId: number, name: string) {
  try {
    const res: any = await API.post(`/admin/consultant-auth/invite-code/${consultantId}`);
    const d = res.data;
    await ElMessageBox.alert(
      `<div style="font-size:14px">
        <p><b>老师：</b>${name}</p>
        <p><b>邀请码：</b><code style="background:#f5f5f5;padding:2px 8px;border-radius:4px">${d.code}</code></p>
        <p><b>邀请链接：</b><a href="${d.miniapp_url}" target="_blank" style="color:#c9a96e;word-break:break-all">${d.miniapp_url}</a></p>
        <p style="color:#909399;font-size:12px">可截图发给客户，客户扫码/点击注册后自动绑定该老师</p>
      </div>`,
      '邀请码已生成', { dangerouslyUseHTMLString: true }
    );
  } catch (e: any) {
    ElMessage.error('生成失败');
  }
}

async function departConsultant(row: any) {
  const activeList = consultants.value.filter(c => c.id !== row.id && c.status === 'active');
  let toId: number | null = null;
  if (activeList.length > 0) {
    const { value } = await ElMessageBox.prompt(
      `确认将【${row.name}】标记为离职？\n数据保留，客户可自动转绑。\n输入接手老师ID（可留空）：`,
      '老师离职', { type: 'warning', inputValue: '' }
    );
    toId = value ? parseInt(value) : null;
  } else {
    await ElMessageBox.confirm(`确认将【${row.name}】标记为离职？数据将保留。`, '老师离职', { type: 'warning' });
  }
  loading.value = true;
  try {
    const res: any = await API.post(`/admin/consultant-auth/depart/${row.id}`, { to_consultant_id: toId });
    ElMessage.success(res?.data?.msg || '已标记离职');
    loadConsultants();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败');
  } finally { loading.value = false; }
}

onMounted(() => {
  loadApps('pending');
  loadConsultants();
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>老师管理</h2>
    </div>

    <el-tabs v-model="activeTab" @tab-change="loadApps(activeTab)">
      <el-tab-pane label="待审核" name="pending" />
      <el-tab-pane label="已通过" name="approved" />
      <el-tab-pane label="已拒绝" name="rejected" />
      <el-tab-pane label="在职老师" name="active" />
    </el-tabs>

    <!-- 申请列表 -->
    <el-table v-if="activeTab !== 'active'" :data="rows" v-loading="loading" style="margin-top:12px">
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="company" label="所属公司" min-width="160" />
      <el-table-column prop="specialty" label="专业领域" min-width="120" />
      <el-table-column prop="created_at" label="申请时间" width="160" />
      <el-table-column prop="review_note" label="审核备注" min-width="120" />
      <el-table-column label="操作" width="180" v-if="activeTab === 'pending'">
        <template #default="{ row }">
          <el-button size="small" type="success" @click="openReview(row, 'approve')">通过</el-button>
          <el-button size="small" type="danger" @click="openReview(row, 'reject')">拒绝</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 在职老师列表 + 转绑/邀请码操作 -->
    <el-table v-else :data="consultants" v-loading="loading" style="margin-top:12px">
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="company" label="所属公司" min-width="160" />
      <el-table-column prop="specialty" label="专业领域" min-width="120" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
            {{ row.status === 'active' ? '在职' : '离职' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button size="small" @click="genInviteCode(row.id, row.name)">推荐码</el-button>
          <el-button size="small" type="warning" @click="openTransfer(row)">转绑客户</el-button>
          <el-button size="small" type="danger" @click="departConsultant(row)">离职</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 审核弹窗 -->
    <el-dialog v-model="reviewDialog.visible" :title="reviewDialog.action === 'approve' ? '通过申请' : '拒绝申请'" width="480px">
      <el-form label-position="top">
        <el-form-item v-if="reviewDialog.action === 'approve'" label="归属分公司">
          <el-select v-model="reviewDialog.branch_id" placeholder="请选择分公司" style="width:100%" clearable>
            <el-option v-for="b in branches" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="reviewDialog.action === 'approve'" label="级别">
          <el-select v-model="reviewDialog.level" style="width:100%">
            <el-option v-for="l in levelOptions" :key="l.value" :label="l.label" :value="l.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="reviewDialog.action === 'approve'" label="岗位（可选）">
          <el-select v-model="reviewDialog.position" placeholder="可不选" style="width:100%" clearable>
            <el-option v-for="p in positionOptions" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注（可选）">
          <el-input v-model="reviewDialog.note" type="textarea" :rows="3" placeholder="审核说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialog.visible = false">取消</el-button>
        <el-button :type="reviewDialog.action === 'approve' ? 'success' : 'danger'"
          :loading="loading" @click="submitReview">
          确认{{ reviewDialog.action === 'approve' ? '通过' : '拒绝' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 转绑弹窗 -->
    <el-dialog v-model="transferDialog.visible" title="客户转绑" width="440px">
      <p style="color:#666;margin-bottom:16px">将【{{ transferDialog.fromName }}】名下所有客户转给：</p>
      <el-form label-position="top">
        <el-form-item label="接手老师">
          <el-select v-model="transferDialog.toId" placeholder="请选择" style="width:100%" filterable>
            <el-option
              v-for="c in consultants.filter(c => c.id !== transferDialog.fromId && c.status === 'active')"
              :key="c.id" :label="`${c.name}（${c.company || ''}）`" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="transferDialog.visible = false">取消</el-button>
        <el-button type="warning" :loading="loading" @click="submitTransfer">确认转绑</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { padding: 24px; }
.page-header { display: flex; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 20px; }
</style>
