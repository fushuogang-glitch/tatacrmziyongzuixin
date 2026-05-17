<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const user = useUserStore();
const loading = ref(false);
const rows = ref<any[]>([]);
const filterStatus = ref('');
const assignDialog = reactive({
  visible: false,
  uid: 0,
  name: '',
  role: 'admin',
  company: '',
});

const companies = [
  '上海嘉塔诺塔管理咨询有限公司',
  '武汉塔塔咨询有限公司',
  '南京塔塔咨询有限公司',
];
const roleLabel: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '分公司管理员',
  consultant: '老师',
  pending: '待分配',
};
const roleTagType: Record<string, string> = {
  super_admin: 'danger',
  admin: 'warning',
  consultant: 'success',
  pending: 'info',
};
const statusLabel: Record<string, string> = {
  active: '正常', pending: '待激活', disabled: '已停用',
};

async function loadUsers() {
  loading.value = true;
  try {
    const res: any = await API.get(`/admin/users${filterStatus.value ? '?status=' + filterStatus.value : ''}`);
    rows.value = res || [];
  } catch { ElMessage.error('加载失败'); }
  finally { loading.value = false; }
}

function openAssign(row: any) {
  assignDialog.uid = row.id;
  assignDialog.name = row.real_name || row.username;
  assignDialog.role = row.role === 'pending' ? 'admin' : row.role;
  assignDialog.company = row.company || '';
  assignDialog.visible = true;
}

async function submitAssign() {
  loading.value = true;
  try {
    const res: any = await API.post(`/admin/users/${assignDialog.uid}/assign-role`, {
      role: assignDialog.role,
      company: assignDialog.company,
    });
    ElMessage.success(res.data?.msg || '分配成功');
    assignDialog.visible = false;
    loadUsers();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败');
  } finally { loading.value = false; }
}

async function disableUser(row: any) {
  await ElMessageBox.confirm(`确认停用「${row.real_name}」的账号？`, '停用确认', { type: 'warning' });
  try {
    await API.post(`/admin/users/${row.id}/disable`);
    ElMessage.success('已停用');
    loadUsers();
  } catch (e: any) { ElMessage.error('操作失败'); }
}

onMounted(loadUsers);
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>账号管理</h2>
      <div class="toolbar">
        <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width:120px" @change="loadUsers">
          <el-option label="待激活" value="pending" />
          <el-option label="正常" value="active" />
          <el-option label="已停用" value="disabled" />
        </el-select>
        <el-button @click="loadUsers" :loading="loading">刷新</el-button>
      </div>
    </div>

    <el-table :data="rows" v-loading="loading">
      <el-table-column prop="real_name" label="姓名" width="100" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="company" label="所属公司" min-width="160" show-overflow-tooltip />
      <el-table-column label="角色" width="130">
        <template #default="{ row }">
          <el-tag :type="roleTagType[row.role] || 'info'" size="small">
            {{ roleLabel[row.role] || row.role }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : row.status === 'pending' ? 'warning' : 'danger'" size="small">
            {{ statusLabel[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="140" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openAssign(row)"
            v-if="row.role !== 'super_admin' || user.role === 'super_admin'">
            分配角色
          </el-button>
          <el-button size="small" type="danger" @click="disableUser(row)"
            v-if="row.status === 'active' && row.role !== 'super_admin'">
            停用
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分配角色弹窗 -->
    <el-dialog v-model="assignDialog.visible" title="分配角色" width="400px">
      <div style="margin-bottom:16px;color:#666;font-size:14px">
        为「<b style="color:#0a0a0a">{{ assignDialog.name }}</b>」分配系统角色
      </div>
      <el-form label-position="top">
        <el-form-item label="角色">
          <el-radio-group v-model="assignDialog.role" style="display:flex;flex-direction:column;gap:8px">
            <el-radio value="super_admin">超级管理员（九哥专属，全部权限）</el-radio>
            <el-radio value="admin">分公司管理员（管理本公司老师和数据）</el-radio>
            <el-radio value="consultant">老师（查看自己的工单和行程）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="所属分公司" v-if="assignDialog.role !== 'super_admin'">
          <el-select v-model="assignDialog.company" placeholder="请选择" style="width:100%">
            <el-option v-for="c in companies" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="submitAssign">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { padding: 24px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 20px; }
.toolbar { display: flex; gap: 8px; }
</style>
