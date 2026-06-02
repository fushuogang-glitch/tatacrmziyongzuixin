<template>
  <el-card v-loading="loading">
    <template #header>
      <span style="font-weight:600;">💳 储值</span>
      <el-button type="primary" size="small" style="float:right" @click="openCreate">新增储值</el-button>
    </template>

    <el-empty v-if="!loading && rows.length === 0" description="暂无储值记录" :image-size="80" />

    <el-table v-else :data="rows" stripe size="small" @expand-change="onExpand">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="expand-block">
            <div class="expand-head">
              <span style="font-weight:600;">本笔消耗记录</span>
            </div>
            <el-table :data="consumptions[row.id] || []" v-loading="consumLoading[row.id]" size="small">
              <el-table-column label="时间" width="160">
                <template #default="{ row: c }">{{ fmtTime(c.created_at || c.consume_time) }}</template>
              </el-table-column>
              <el-table-column label="项目" min-width="160">
                <template #default="{ row: c }">{{ c.project_name || projectName(c.project_id) || `项目#${c.project_id}` }}</template>
              </el-table-column>
              <el-table-column label="金额" width="120">
                <template #default="{ row: c }"><span style="color:#f56c6c;">-¥{{ formatNum(c.amount) }}</span></template>
              </el-table-column>
              <el-table-column label="操作人" width="120">
                <template #default="{ row: c }">{{ c.admin_name || '-' }}</template>
              </el-table-column>
              <el-table-column prop="note" label="备注" />
            </el-table>
            <el-empty v-if="(consumptions[row.id] || []).length === 0" description="暂无消耗" :image-size="40" />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="160">
        <template #default="{ row }">{{ fmtTime(row.created_at || row.recharge_time) }}</template>
      </el-table-column>
      <el-table-column label="实付金额" width="110">
        <template #default="{ row }"><span class="gold">¥{{ formatNum(row.amount) }}</span></template>
      </el-table-column>
      <el-table-column label="赠送" width="100">
        <template #default="{ row }"><span style="color:#67c23a;">+¥{{ formatNum(row.gift_amount) }}</span></template>
      </el-table-column>
      <el-table-column label="付款方式" width="100">
        <template #default="{ row }">{{ payMethodLabel(row.pay_method) }}</template>
      </el-table-column>
      <el-table-column label="剩余金额" width="120">
        <template #default="{ row }"><span style="color:#409eff;font-weight:600;">¥{{ formatNum(row.balance) }}</span></template>
      </el-table-column>
      <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openConsume(row)" :disabled="row.status === 'depleted' || Number(row.balance || 0) <= 0">
            消耗
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增储值弹窗 -->
    <el-dialog v-model="rechargeDialog.visible" title="新增储值" width="520px">
      <el-form :model="rechargeDialog.form" label-width="100px">
        <el-form-item label="实付金额">
          <el-input-number v-model="rechargeDialog.form.amount" :min="0" :precision="2" :step="100" style="width:200px" />
        </el-form-item>
        <el-form-item label="赠送金额">
          <el-input-number v-model="rechargeDialog.form.gift_amount" :min="0" :precision="2" :step="50" style="width:200px" />
          <span style="margin-left:12px;color:#909399;font-size:13px;">
            到账：<b style="color:#67c23a">¥{{ formatNum(rechargeTotal) }}</b>
          </span>
        </el-form-item>
        <el-form-item label="付款方式">
          <el-select v-model="rechargeDialog.form.pay_method" placeholder="请选择" style="width:100%">
            <el-option v-for="o in payMethods" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="rechargeDialog.form.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rechargeDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="rechargeDialog.saving" @click="saveRecharge">保存</el-button>
      </template>
    </el-dialog>

    <!-- 消耗弹窗 -->
    <el-dialog v-model="consumeDialog.visible" title="储值消耗" width="520px">
      <el-form :model="consumeDialog.form" label-width="100px">
        <el-form-item label="储值剩余">
          <span style="color:#409eff;font-weight:600;">¥{{ formatNum(consumeDialog.balance) }}</span>
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="consumeDialog.form.project_id" filterable placeholder="选择项目" style="width:100%">
            <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="`${p.name}（¥${formatNum(p.price)}）`" />
          </el-select>
        </el-form-item>
        <el-form-item label="消耗金额">
          <el-input-number v-model="consumeDialog.form.amount" :min="0" :precision="2" :step="100" style="width:200px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="consumeDialog.form.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="consumeDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="consumeDialog.saving" @click="saveConsume">确认消耗</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const props = defineProps<{ memberId: number | string }>();

const payMethods = [
  { value: 'cash', label: '现金' },
  { value: 'wechat', label: '微信' },
  { value: 'alipay', label: '支付宝' },
  { value: 'bankcard', label: '银行卡' },
  { value: 'company', label: '对公' },
  { value: 'personal', label: '个人' },
];

function payMethodLabel(v: string) { return payMethods.find(o => o.value === v)?.label || (v || '-'); }
function statusLabel(s: string) {
  return ({ active: '使用中', depleted: '已用完', refunded: '已退款', expired: '已过期' } as any)[s] || (s || '使用中');
}
function statusTag(s: string): any {
  return ({ active: 'success', depleted: 'info', refunded: 'danger', expired: 'warning' } as any)[s] || 'success';
}
function formatNum(n: any) {
  const x = Number(n || 0);
  return x.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
function fmtTime(t: any) {
  if (!t) return '-';
  return String(t).replace('T', ' ').slice(0, 16);
}

// ===== 列表 =====
const rows = ref<any[]>([]);
const loading = ref(false);
const consumptions = reactive<Record<number, any[]>>({});
const consumLoading = reactive<Record<number, boolean>>({});

async function load() {
  if (!props.memberId) return;
  loading.value = true;
  try {
    const r: any = await API.memberRecharges(Number(props.memberId));
    rows.value = r?.items || r?.list || r || [];
  } catch (e) {
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadConsumptions(rechargeId: number) {
  consumLoading[rechargeId] = true;
  try {
    const r: any = await API.rechargeConsumptions(rechargeId);
    consumptions[rechargeId] = r?.items || r?.list || r || [];
  } catch (e) {
    consumptions[rechargeId] = [];
  } finally {
    consumLoading[rechargeId] = false;
  }
}

function onExpand(row: any, expandedRows: any[]) {
  const isExpanded = expandedRows.some((r: any) => r.id === row.id);
  if (isExpanded && !consumptions[row.id]) {
    loadConsumptions(row.id);
  }
}

// ===== 项目（用于消耗弹窗下拉） =====
const projects = ref<any[]>([]);
async function loadProjects() {
  try {
    const r: any = await API.serviceList();
    projects.value = (r?.items || r || []).filter((s: any) => s.status === 'active' || !s.status);
  } catch (e) {
    projects.value = [];
  }
}
function projectName(id: number) {
  return projects.value.find(p => p.id === id)?.name || '';
}

// ===== 新增储值 =====
const rechargeDialog = reactive<any>({
  visible: false,
  saving: false,
  form: { amount: 0, gift_amount: 0, pay_method: 'wechat', note: '' },
});
const rechargeTotal = computed(() =>
  Number(rechargeDialog.form.amount || 0) + Number(rechargeDialog.form.gift_amount || 0)
);

function openCreate() {
  rechargeDialog.form = { amount: 0, gift_amount: 0, pay_method: 'wechat', note: '' };
  rechargeDialog.visible = true;
}

async function saveRecharge() {
  if (!rechargeDialog.form.amount || rechargeDialog.form.amount <= 0) {
    ElMessage.warning('请填实付金额'); return;
  }
  rechargeDialog.saving = true;
  try {
    await API.rechargeCreate({ member_id: Number(props.memberId), ...rechargeDialog.form });
    ElMessage.success('已新增储值');
    rechargeDialog.visible = false;
    load();
  } finally {
    rechargeDialog.saving = false;
  }
}

// ===== 消耗 =====
const consumeDialog = reactive<any>({
  visible: false,
  saving: false,
  rechargeId: 0,
  balance: 0,
  form: { project_id: undefined as any, amount: 0, note: '' },
});

function openConsume(row: any) {
  consumeDialog.rechargeId = row.id;
  consumeDialog.balance = Number(row.balance || 0);
  consumeDialog.form = { project_id: undefined, amount: 0, note: '' };
  consumeDialog.visible = true;
}

async function saveConsume() {
  if (!consumeDialog.form.project_id) { ElMessage.warning('请选择项目'); return; }
  if (!consumeDialog.form.amount || consumeDialog.form.amount <= 0) { ElMessage.warning('消耗金额需大于 0'); return; }
  if (consumeDialog.form.amount > consumeDialog.balance) {
    ElMessage.warning('消耗金额超过剩余'); return;
  }
  consumeDialog.saving = true;
  try {
    await API.rechargeConsume(consumeDialog.rechargeId, consumeDialog.form);
    ElMessage.success('已消耗');
    consumeDialog.visible = false;
    await load();
    await loadConsumptions(consumeDialog.rechargeId);
  } finally {
    consumeDialog.saving = false;
  }
}

watch(() => props.memberId, () => load());
onMounted(() => { load(); loadProjects(); });
</script>

<style scoped>
.gold { color: #b8860b; font-weight: 600; }
.expand-block { padding: 0 32px 12px; background: #fafbfc; }
.expand-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0;
}
</style>
