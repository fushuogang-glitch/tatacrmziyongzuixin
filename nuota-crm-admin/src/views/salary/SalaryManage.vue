<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const loading = ref(false);
const records = ref<any[]>([]);
const configs = ref<any[]>([]);
const positions = ref<any[]>([]);
const activeTab = ref('records');
const monthStr = ref(`${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`);
const yearNum = computed(() => parseInt(monthStr.value.split('-')[0]));
const monthNum = computed(() => parseInt(monthStr.value.split('-')[1]));
const configDialog = ref(false);
const editingConfig = ref<any>({});

const levelLabels: Record<string, string> = {
  probation: '考核期 P', trainee: '培训期 T', pm: '项目经理 PM', pd: '项目总监 PD',
  junior_partner: '初级合伙人 JP', partner: '中级合伙人 MP', senior_partner: '高级合伙人 SP', founding_partner: '创始合伙人 FP',
};

async function loadRecords() {
  loading.value = true;
  try {
    const res: any = await API.get(`/admin/salary/records?year=${yearNum.value}&month=${monthNum.value}`);
    records.value = Array.isArray(res) ? res : (res?.data || []);
  } catch { records.value = []; }
  finally { loading.value = false; }
}

async function loadConfigs() {
  try {
    const res: any = await API.get('/admin/salary/configs');
    configs.value = Array.isArray(res) ? res : (res?.data || []);
  } catch { configs.value = []; }
}

async function loadPositions() {
  try {
    const res: any = await API.get('/admin/salary/positions');
    positions.value = Array.isArray(res) ? res : (res?.data || []);
  } catch { positions.value = []; }
}

async function calculate() {
  await ElMessageBox.confirm(`确认计算 ${yearNum.value}年${monthNum.value}月 所有老师工资？`, '工资计算', { type: 'warning' });
  loading.value = true;
  try {
    await API.post('/admin/salary/calculate', { year: yearNum.value, month: monthNum.value });
    ElMessage.success('计算完成');
    await loadRecords();
  } catch (e: any) {
    ElMessage.error('计算失败');
  } finally { loading.value = false; }
}

async function confirmAll() {
  await ElMessageBox.confirm('确认全部工资？确认后不可修改', '批量确认', { type: 'warning' });
  try {
    await API.post('/admin/salary/records/confirm-all', { year: yearNum.value, month: monthNum.value });
    ElMessage.success('全部确认');
    await loadRecords();
  } catch { ElMessage.error('操作失败'); }
}

async function confirmOne(id: number) {
  try {
    await API.post(`/admin/salary/records/${id}/confirm`);
    ElMessage.success('已确认');
    await loadRecords();
  } catch { ElMessage.error('操作失败'); }
}

function openConfigEdit(row: any) {
  editingConfig.value = { ...row };
  configDialog.value = true;
}

async function saveConfig() {
  try {
    await API.put(`/admin/salary/configs/${editingConfig.value.level}`, editingConfig.value);
    ElMessage.success('已保存');
    configDialog.value = false;
    await loadConfigs();
  } catch { ElMessage.error('保存失败'); }
}

const totalSalary = computed(() => records.value.reduce((s, r) => s + (r.total_salary || 0), 0));
const totalCommission = computed(() => records.value.reduce((s, r) => s + (r.commission_amount || 0), 0));

onMounted(() => { loadRecords(); loadConfigs(); loadPositions(); });
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>💰 工资管理</h2>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="月度工资" name="records" />
      <el-tab-pane label="薪资配置" name="configs" />
      <el-tab-pane label="岗位津贴" name="positions" />
    </el-tabs>

    <!-- 月度工资 -->
    <div v-if="activeTab === 'records'">
      <div class="toolbar">
        <el-date-picker v-model="monthStr" type="month" value-format="YYYY-MM" format="YYYY年MM月"
          style="width:180px" @change="loadRecords" />
        <el-button type="primary" @click="calculate" :loading="loading">🔄 计算本月工资</el-button>
        <el-button type="success" @click="confirmAll" :disabled="records.length === 0">✅ 全部确认</el-button>
        <div class="toolbar-summary">
          <span>合计应发：<b style="color:#e6a23c;font-size:18px">¥{{ totalSalary.toLocaleString() }}</b></span>
          <span style="margin-left:24px">提成合计：<b>¥{{ totalCommission.toLocaleString() }}</b></span>
        </div>
      </div>

      <el-table :data="records" v-loading="loading" stripe style="margin-top:16px" show-summary :summary-method="() => []">
        <el-table-column prop="consultant_name" label="老师" width="90" fixed />
        <el-table-column label="级别" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ levelLabels[row.level] || row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="base_salary" label="底薪" width="80" align="right" />
        <el-table-column prop="social_subsidy" label="社保补贴" width="90" align="right" />
        <el-table-column label="出差补助" width="90" align="right">
          <template #default="{ row }">{{ row.travel_allowance || '-' }}</template>
        </el-table-column>
        <el-table-column label="执案津贴" width="110" align="right">
          <template #default="{ row }">
            <span v-if="row.main_days > 0">{{ row.daily_allowance_total }}（{{ row.main_days }}天）</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="助理津贴" width="110" align="right">
          <template #default="{ row }">
            <span v-if="row.assist_days > 0">{{ row.assist_allowance_total }}（{{ row.assist_days }}天）</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="回款提成" width="140" align="right">
          <template #default="{ row }">
            <div v-if="row.commission_amount > 0">
              <div style="color:#e6a23c;font-weight:600">¥{{ row.commission_amount.toLocaleString() }}</div>
              <div style="font-size:11px;color:#999">回款¥{{ row.commission_base.toLocaleString() }} × {{ (row.commission_rate * 100).toFixed(0) }}%</div>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="position_allowance" label="岗位/管理" width="100" align="right">
          <template #default="{ row }">{{ row.position_allowance > 0 ? row.position_allowance : '-' }}</template>
        </el-table-column>
        <el-table-column label="应发合计" width="110" align="right" fixed="right">
          <template #default="{ row }">
            <b style="color:#303133;font-size:16px">¥{{ row.total_salary.toLocaleString() }}</b>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center" fixed="right">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'confirmed'" type="success" size="small">已确认</el-tag>
            <el-button v-else size="small" type="warning" @click="confirmOne(row.id)">确认</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 薪资配置 -->
    <div v-if="activeTab === 'configs'">
      <el-alert type="info" :closable="false" style="margin-bottom:16px"
        title="各级别薪资标准配置，修改后下次计算工资时生效" />
      <el-table :data="configs" stripe>
        <el-table-column label="级别" width="120">
          <template #default="{ row }">{{ row.level_label }}</template>
        </el-table-column>
        <el-table-column prop="base_salary" label="底薪/月" width="90" align="right" />
        <el-table-column prop="social_subsidy" label="社保补贴/月" width="100" align="right" />
        <el-table-column prop="travel_allowance" label="出差补助/企业" width="110" align="right" />
        <el-table-column prop="daily_allowance" label="执案津贴/天" width="100" align="right" />
        <el-table-column label="回款提成" width="90" align="right">
          <template #default="{ row }">{{ row.commission_rate > 0 ? (row.commission_rate * 100).toFixed(0) + '%' : '/' }}</template>
        </el-table-column>
        <el-table-column prop="branch_mgmt" label="分公司/月" width="90" align="right" />
        <el-table-column prop="dept_mgmt" label="部门/公司/月" width="110" align="right" />
        <el-table-column prop="course_invite" label="课程邀约" width="90" align="right" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="primary" @click="openConfigEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 岗位津贴 -->
    <div v-if="activeTab === 'positions'">
      <el-alert type="info" :closable="false" style="margin-bottom:16px"
        title="老师担任对应岗位后，额外获得该岗位月津贴" />
      <el-table :data="positions" stripe>
        <el-table-column prop="position" label="岗位名称" width="250" />
        <el-table-column prop="allowance_type" label="类型" width="120">
          <template #default="{ row }">{{ row.allowance_type === 'branch' ? '分公司级' : '部门级' }}</template>
        </el-table-column>
        <el-table-column prop="monthly_amount" label="月津贴" width="120" align="right" />
      </el-table>
    </div>

    <!-- 配置编辑弹窗 -->
    <el-dialog v-model="configDialog" :title="`编辑薪资 - ${editingConfig.level_label}`" width="500px">
      <el-form :model="editingConfig" label-width="130px">
        <el-form-item label="底薪/月"><el-input-number v-model="editingConfig.base_salary" :min="0" :step="500" /></el-form-item>
        <el-form-item label="社保补贴/月"><el-input-number v-model="editingConfig.social_subsidy" :min="0" :step="500" /></el-form-item>
        <el-form-item label="出差补助/企业"><el-input-number v-model="editingConfig.travel_allowance" :min="0" :step="100" /></el-form-item>
        <el-form-item label="执案津贴/天"><el-input-number v-model="editingConfig.daily_allowance" :min="0" :step="100" /></el-form-item>
        <el-form-item label="回款提成比例"><el-input-number v-model="editingConfig.commission_rate" :min="0" :max="1" :step="0.01" :precision="2" /><span style="margin-left:8px;color:#999">{{ (editingConfig.commission_rate * 100).toFixed(0) }}%</span></el-form-item>
        <el-form-item label="分公司/月"><el-input-number v-model="editingConfig.branch_mgmt" :min="0" :step="500" /></el-form-item>
        <el-form-item label="部门/公司/月"><el-input-number v-model="editingConfig.dept_mgmt" :min="0" :step="500" /></el-form-item>
        <el-form-item label="课程邀约"><el-input-number v-model="editingConfig.course_invite" :min="0" :step="500" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialog = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { padding: 24px; }
.page-header { display: flex; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 20px; }
.toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.toolbar-summary { margin-left: auto; color: #606266; }
</style>
