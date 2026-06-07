<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import { API } from '../../api';

const loading = ref(false);
const month = ref(defaultMonth());
const branchId = ref<any>('');
const branches = ref<any[]>([]);
const items = ref<any[]>([]);

function defaultMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function money(v: any) {
  const n = parseFloat(v || 0);
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

const CATEGORIES = [
  { value: 'rent', label: '房租', tag: 'primary' },
  { value: 'utility', label: '水电', tag: 'success' },
  { value: 'depreciation', label: '折旧', tag: 'warning' },
  { value: 'insurance', label: '保险', tag: 'info' },
  { value: 'other_fixed', label: '其他', tag: '' },
];
function catLabel(c: string) { return CATEGORIES.find(x => x.value === c)?.label || c || '-'; }
function catTag(c: string) { return CATEGORIES.find(x => x.value === c)?.tag || ''; }
function branchName(id: any) { return branches.value.find(b => b.id === id)?.name || `#${id}`; }

async function loadBranches() {
  try {
    const d: any = await API.branchList();
    branches.value = Array.isArray(d) ? d : (d?.items || []);
  } catch { branches.value = []; }
}

async function load() {
  loading.value = true;
  try {
    const params: any = { month: month.value };
    if (branchId.value) params.branch_id = branchId.value;
    const d: any = await API.financeFixedCosts(params);
    items.value = d?.items || [];
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.msg || '加载失败');
  } finally {
    loading.value = false;
  }
}

/* ── 新增/编辑 ── */
const dlgVisible = ref(false);
const editing = ref(false);
const form = reactive<any>({
  id: null, branch_id: '', cost_month: defaultMonth(), category: 'rent', item: '', amount: 0, remark: '',
});
function resetForm() {
  Object.assign(form, {
    id: null, branch_id: branchId.value || '', cost_month: month.value,
    category: 'rent', item: '', amount: 0, remark: '',
  });
}
function openCreate() { resetForm(); editing.value = false; dlgVisible.value = true; }
function openEdit(row: any) {
  Object.assign(form, {
    id: row.id, branch_id: row.branch_id, cost_month: row.cost_month,
    category: row.category, item: row.item, amount: parseFloat(row.amount || 0), remark: row.remark || '',
  });
  editing.value = true; dlgVisible.value = true;
}
async function submitForm() {
  if (!form.branch_id) return ElMessage.warning('请选择分公司');
  if (!form.cost_month) return ElMessage.warning('请选择成本月份');
  if (!form.item) return ElMessage.warning('请填写科目名称');
  const body: any = {
    branch_id: form.branch_id,
    cost_month: form.cost_month,
    category: form.category,
    item: form.item,
    amount: form.amount,
    remark: form.remark,
  };
  try {
    if (editing.value && form.id) {
      await API.financeFixedCostUpdate(form.id, body);
      ElMessage.success('已保存');
    } else {
      await API.financeFixedCostCreate(body);
      ElMessage.success('已新增');
    }
    dlgVisible.value = false;
    load();
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.msg || '保存失败');
  }
}
async function removeRow(row: any) {
  try {
    await API.financeFixedCostDelete(row.id);
    ElMessage.success('已删除');
    load();
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.msg || '删除失败');
  }
}

watch([month, branchId], load);
onMounted(() => { loadBranches(); load(); });
</script>

<template>
  <div class="fc">
    <div class="page-head">
      <div class="title">固定成本录入</div>
      <div class="filters">
        <el-date-picker
          v-model="month" type="month" value-format="YYYY-MM" format="YYYY-MM"
          placeholder="选择月份" :clearable="false" style="width:150px"
        />
        <el-select v-model="branchId" placeholder="全部分公司" clearable style="width:160px">
          <el-option v-for="b in branches" :key="b.id" :label="b.name" :value="b.id" />
        </el-select>
        <el-button type="primary" :icon="Plus" round @click="openCreate">新增固定成本</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" stripe border style="width:100%" empty-text="暂无固定成本记录">
      <el-table-column label="分公司" min-width="120">
        <template #default="{ row }">{{ row.branch_name || branchName(row.branch_id) }}</template>
      </el-table-column>
      <el-table-column label="月份" width="110">
        <template #default="{ row }">{{ row.cost_month }}</template>
      </el-table-column>
      <el-table-column label="类别" width="100">
        <template #default="{ row }">
          <el-tag :type="catTag(row.category)" size="small" effect="light">{{ catLabel(row.category) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="科目" prop="item" min-width="140">
        <template #default="{ row }">{{ row.item || '-' }}</template>
      </el-table-column>
      <el-table-column label="金额" width="140" align="right">
        <template #default="{ row }">
          <span style="color:#7c3aed; font-weight:700;">¥{{ money(row.amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="备注" prop="remark" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确认删除这条固定成本？" confirm-button-text="删除" cancel-button-text="取消" @confirm="removeRow(row)">
            <template #reference>
              <el-button size="small" type="danger" plain>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dlgVisible" :title="editing ? '编辑固定成本' : '新增固定成本'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="分公司" required>
          <el-select v-model="form.branch_id" placeholder="选择分公司" style="width:100%">
            <el-option v-for="b in branches" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="成本月份" required>
          <el-date-picker
            v-model="form.cost_month" type="month" value-format="YYYY-MM" format="YYYY-MM"
            placeholder="选择月份" :clearable="false" style="width:100%"
          />
        </el-form-item>
        <el-form-item label="类别" required>
          <el-select v-model="form.category" style="width:100%">
            <el-option v-for="c in CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="科目名称" required>
          <el-input v-model="form.item" placeholder="如：门店租金 / 物业费" />
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="form.amount" :min="0" :step="100" :precision="2" controls-position="right" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgVisible=false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.fc { padding: 4px 2px; --np: #7c3aed; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 12px; }
.page-head .title { font-size: 20px; font-weight: 700; color: #1f2937; }
.filters { display: flex; gap: 10px; align-items: center; }
</style>
