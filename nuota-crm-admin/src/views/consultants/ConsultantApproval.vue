<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const user = useUserStore();
const loading = ref(false);
const activeTab = ref('pending');
const rows = ref<any[]>([]);
const reviewDialog = reactive({ visible: false, row: null as any, action: '', note: '' });
const transferDialog = reactive({
  visible: false,
  fromId: 0,
  fromName: '',
  toId: null as number | null,
  memberIds: null as number[] | null,
});
const consultants = ref<any[]>([]);

import { reactive } from 'vue';

async function loadApps(status = 'pending') {
  loading.value = true;
  try {
    const res: any = await API.get(`/admin/consultant-auth/applications?status=${status}`);
    rows.value = res.data || [];
  } catch (e) {
    ElMessage.error('加载失败');
  } finally {
    loading.value = false;
  }
}

async function loadConsultants() {
  try {
    const res: any = await API.get('/admin/consultants');
    consultants.value = res.data || [];
  } catch { }
}

function openReview(row: any, action: string) {
  reviewDialog.row = row;
  reviewDialog.action = action;
  reviewDialog.note = '';
  reviewDialog.visible = true;
}

async function submitReview() {
  loading.value = true;
  try {
    await API.post(`/admin/consultant-auth/applications/${reviewDialog.row.id}/review`, {
      action: reviewDialog.action,
      note: reviewDialog.note,
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
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="genInviteCode(row.id, row.name)">邀请码</el-button>
          <el-button size="small" type="warning" @click="openTransfer(row)">转绑客户</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 审核弹窗 -->
    <el-dialog v-model="reviewDialog.visible" :title="reviewDialog.action === 'approve' ? '通过申请' : '拒绝申请'" width="400px">
      <el-form label-position="top">
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
