<template>
  <div class="page">
    <div class="header">
      <h2>📦 采购管理</h2>
      <div class="toolbar-right">
        <el-date-picker
          v-model="filterRange"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width:260px;margin-right:12px"
          @change="load"
        />
        <el-select v-model="filterType" placeholder="全部类型" clearable style="width:140px;margin-right:12px" @change="load">
          <el-option v-for="o in typeOpts" :key="o.value" :value="o.value" :label="o.label" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="报销状态" clearable style="width:140px;margin-right:16px" @change="load">
          <el-option v-for="o in statusOpts" :key="o.value" :value="o.value" :label="o.label" />
        </el-select>
        <el-button type="primary" @click="openDialog()">新增采购</el-button>
      </div>
    </div>

    <el-table :data="rows" v-loading="loading" stripe>
      <el-table-column label="采购时间" width="120">
        <template #default="{ row }">{{ row.purchase_date || '-' }}</template>
      </el-table-column>
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag :type="typeTag(row.type)" size="small">{{ typeLabel(row.type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分公司" width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.branch_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="item_name" label="物品名称" min-width="160" show-overflow-tooltip />
      <el-table-column label="数量" width="80">
        <template #default="{ row }">{{ row.quantity }}</template>
      </el-table-column>
      <el-table-column label="单价" width="110">
        <template #default="{ row }">¥{{ formatNum(row.unit_price) }}</template>
      </el-table-column>
      <el-table-column label="总价" width="120">
        <template #default="{ row }"><span class="gold">¥{{ formatNum(totalOf(row)) }}</span></template>
      </el-table-column>
      <el-table-column prop="supplier" label="供应商" min-width="120" show-overflow-tooltip />
      <el-table-column label="报销状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="采购人" width="100">
        <template #default="{ row }">{{ row.purchaser_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="reimburser" label="报销人" width="100">
        <template #default="{ row }">{{ row.reimburser || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click="openDialog(row)">编辑</el-button>
          <el-button
            size="small"
            text
            :type="row.status === 'reimbursed' ? 'info' : 'success'"
            @click="reimburse(row)"
            :disabled="row.status === 'reimbursed'"
          >报销</el-button>
          <el-button v-if="isSuper" size="small" text type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :page-sizes="[20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="load"
        @size-change="load"
      />
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog v-model="dialog.visible" :title="dialog.id ? '编辑采购' : '新增采购'" width="640px">
      <el-form :model="dialog.form" label-width="100px">
        <el-form-item label="分公司" required>
          <el-select v-model="dialog.form.branch_id" placeholder="请选择分公司" style="width:100%" filterable>
            <el-option v-for="b in branches" :key="b.id" :value="b.id" :label="b.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="采购类型">
          <el-select v-model="dialog.form.type" placeholder="请选择" style="width:100%">
            <el-option v-for="o in typeOpts" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="物品名称">
          <el-input v-model="dialog.form.item_name" placeholder="如：会议室投影仪" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="dialog.form.quantity" :min="1" :max="999999" style="width:160px" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="dialog.form.unit_price" :min="0" :precision="2" :step="100" style="width:200px" />
          <span style="margin-left:12px;color:#909399;font-size:13px;">
            合计：<b style="color:#f56c6c">¥{{ formatNum(dialogTotal) }}</b>
          </span>
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="dialog.form.supplier" placeholder="供应商名称" />
        </el-form-item>
        <el-form-item label="采购时间">
          <el-date-picker v-model="dialog.form.purchase_date" type="date" value-format="YYYY-MM-DD" style="width:200px" />
        </el-form-item>
        <el-form-item label="发票状态">
          <el-radio-group v-model="dialog.form.invoice_status">
            <el-radio value="none">无发票</el-radio>
            <el-radio value="pending">待开</el-radio>
            <el-radio value="received">已收票</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="发票号" v-if="dialog.form.invoice_status === 'received'">
          <el-input v-model="dialog.form.invoice_no" placeholder="可选" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dialog.form.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const user = useUserStore();
const isSuper = computed(() => user.role === 'super_admin');

const typeOpts = [
  { value: 'goods', label: '商品' },
  { value: 'equipment', label: '设备' },
  { value: 'combo', label: '组货' },
  { value: 'other', label: '其它' },
];
const statusOpts = [
  { value: 'pending', label: '待报销' },
  { value: 'reimbursed', label: '已报销' },
];

function typeLabel(v: string) { return typeOpts.find(o => o.value === v)?.label || v || '-'; }
function statusLabel(v: string) { return statusOpts.find(o => o.value === v)?.label || (v || '待报销'); }
function typeTag(v: string): any {
  return ({ goods: 'primary', equipment: 'warning', combo: 'success', other: 'info' } as any)[v] || 'info';
}
function statusTag(v: string): any {
  return v === 'reimbursed' ? 'success' : 'warning';
}
function formatNum(n: any) {
  const x = Number(n || 0);
  return x.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
function totalOf(row: any) {
  if (row.total_price != null) return Number(row.total_price);
  return Number(row.quantity || 0) * Number(row.unit_price || 0);
}

// ========= 列表 =========
const rows = ref<any[]>([]);
const loading = ref(false);
const branches = ref<any[]>([]);

async function loadBranches() {
  try {
    const d: any = await API.branchList();
    branches.value = Array.isArray(d) ? d : (d?.items || []);
  } catch {
    branches.value = [];
  }
}
const page = ref(1);
const size = ref(20);
const total = ref(0);
const filterRange = ref<string[] | null>(null);
const filterType = ref('');
const filterStatus = ref('');

async function load() {
  loading.value = true;
  try {
    const params: any = { page: page.value, size: size.value };
    if (filterType.value) params.type = filterType.value;
    if (filterStatus.value) params.status = filterStatus.value;
    if (filterRange.value && filterRange.value.length === 2) {
      params.from = filterRange.value[0];
      params.to = filterRange.value[1];
    }
    const r: any = await API.purchaseList(params);
    rows.value = r?.items || r?.list || r || [];
    total.value = r?.total || rows.value.length;
  } catch (e) {
    rows.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

// ========= 弹窗 =========
const dialog = reactive<any>({
  visible: false,
  saving: false,
  id: 0 as number,
  form: {
    branch_id: '' as any,
    type: 'goods',
    item_name: '',
    quantity: 1,
    unit_price: 0,
    supplier: '',
    purchase_date: new Date().toISOString().slice(0, 10),
    invoice_status: 'none',
    invoice_no: '',
    note: '',
  },
});
const dialogTotal = computed(() => Number(dialog.form.quantity || 0) * Number(dialog.form.unit_price || 0));

function openDialog(row?: any) {
  if (row) {
    dialog.id = row.id;
    dialog.form = {
      branch_id: row.branch_id ?? '',
      type: row.type || 'goods',
      item_name: row.item_name || '',
      quantity: row.quantity || 1,
      unit_price: row.unit_price || 0,
      supplier: row.supplier || '',
      purchase_date: row.purchase_date || new Date().toISOString().slice(0, 10),
      invoice_status: row.invoice_status || 'none',
      invoice_no: row.invoice_no || '',
      note: row.note || '',
    };
  } else {
    dialog.id = 0;
    dialog.form = {
      branch_id: '',
      type: 'goods',
      item_name: '',
      quantity: 1,
      unit_price: 0,
      supplier: '',
      purchase_date: new Date().toISOString().slice(0, 10),
      invoice_status: 'none',
      invoice_no: '',
      note: '',
    };
  }
  dialog.visible = true;
}

async function save() {
  if (!dialog.form.branch_id) { ElMessage.warning('请选择分公司'); return; }
  if (!dialog.form.item_name) { ElMessage.warning('请填物品名称'); return; }
  if (!dialog.form.quantity || dialog.form.quantity <= 0) { ElMessage.warning('数量需大于 0'); return; }
  dialog.saving = true;
  try {
    if (dialog.id) {
      await API.purchaseUpdate(dialog.id, dialog.form);
      ElMessage.success('已更新');
    } else {
      await API.purchaseCreate(dialog.form);
      ElMessage.success('已新增');
    }
    dialog.visible = false;
    load();
  } finally {
    dialog.saving = false;
  }
}

async function reimburse(row: any) {
  try {
    await ElMessageBox.confirm(`确认对「${row.item_name}」标记为已报销？`, '报销确认', { type: 'warning' });
    await API.purchaseUpdate(row.id, { ...row, status: 'reimbursed' });
    ElMessage.success('已标记为已报销');
    load();
  } catch (e: any) {
    if (e !== 'cancel') {/* swallow */}
  }
}

async function del(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除采购记录「${row.item_name}」？`, '删除确认', { type: 'warning' });
    await API.purchaseDelete(row.id);
    ElMessage.success('已删除');
    load();
  } catch (e: any) {
    if (e !== 'cancel') {/* swallow */}
  }
}

onMounted(() => { loadBranches(); load(); });
</script>

<style scoped>
.page { padding: 4px; }
.header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
}
.header h2 { margin: 0; font-size: 18px; }
.toolbar-right { display: flex; align-items: center; flex-wrap: wrap; }
.gold { color: #b8860b; font-weight: 600; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
