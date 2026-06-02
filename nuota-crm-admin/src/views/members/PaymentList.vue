<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const user = useUserStore();
const isSuperAdmin = computed(() => user.role === 'super_admin');

const rows = ref<any[]>([]);
const consumptions = ref<any[]>([]);
const loading = ref(false);
const exporting = ref(false);

// 筛选
const query = reactive({ q: '', pay_status: '', pay_method: '' });

const filtered = computed(() => {
  return rows.value.filter(r => {
    if (query.pay_status && r.pay_status !== query.pay_status) return false;
    if (query.pay_method && r.pay_method !== query.pay_method) return false;
    if (query.q) {
      const kw = query.q.toLowerCase();
      const name = (r.member_name || r.member_id || '').toString().toLowerCase();
      const phone = (r.member_phone || '').toLowerCase();
      if (!name.includes(kw) && !phone.includes(kw)) return false;
    }
    return true;
  });
});

// 按 package_id 分组消耗
function getConsumptions(packageId: number) {
  return consumptions.value.filter(c => c.package_id === packageId);
}

async function load() {
  loading.value = true;
  try {
    const [d, c]: any = await Promise.all([
      API.paymentList(),
      API.consumptionList(),
    ]);
    rows.value = d || [];
    consumptions.value = c || [];
  } finally {
    loading.value = false;
  }
}

async function deletePayment(id: number) {
  try {
    await API.paymentDelete(id);
    ElMessage.success('删除成功');
    load();
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.detail || '删除失败');
  }
}

async function exportPayments() {
  exporting.value = true;
  try {
    const blob = await API.exportPayments() as any;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `收款明细_${new Date().toISOString().slice(0, 10)}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    ElMessage.error('导出失败');
  } finally {
    exporting.value = false;
  }
}

// 状态
const statusMap: any = {
  paid: { label: '已结清', tag: 'success' },
  partial: { label: '分期中', tag: 'warning' },
  pending: { label: '待付款', tag: 'info' },
  refunded: { label: '已退款', tag: 'danger' },
};
function statusLabel(s: string) { return statusMap[s]?.label || s; }
function statusTag(s: string) { return statusMap[s]?.tag || ''; }

// 类型
const typeMap: any = { trial: '体验费', annual: '年费', single: '单次', vip: 'VIP年费' };
function typeName(t: string) { return typeMap[t] || t || '-'; }

// 付款方式
const methodMap: any = {
  company_account: '对公账户',
  private_account: '私户转账',
  wecom: '企业微信',
  wechat_proxy: '微信代收',
};
function methodName(m: string) { return methodMap[m] || m || '-'; }

function modeName(m: string) {
  return m === 'installment' ? '分期' : '全款';
}

function fmt(v: any) {
  if (!v) return '-';
  return String(v).replace('T', ' ').slice(0, 16);
}

function fmtDate(v: any) {
  if (!v) return '-';
  return String(v).slice(0, 10);
}

function fmtMoney(v: any) {
  if (!v && v !== 0) return '-';
  const n = parseFloat(v);
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function ratingStars(n: number) {
  if (!n) return '待评价';
  return '⭐'.repeat(n);
}

const totalPaid = computed(() =>
  filtered.value.reduce((s, r) => s + parseFloat(r.amount || 0), 0)
);
const totalDebt = computed(() =>
  filtered.value.filter(r => r.pay_status === 'partial' || r.pay_status === 'pending')
    .reduce((s, r) => s + parseFloat(r.debt_amount || 0), 0)
);

onMounted(load);
</script>

<template>
  <div>
    <!-- 顶部标题 + 汇总 -->
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px;">
      <div>
        <div style="font-size:20px; font-weight:700; margin-bottom:10px;">收款明细</div>
        <div style="display:flex; gap:32px;">
          <div style="background:#f0f9eb; border-radius:8px; padding:10px 20px; text-align:center;">
            <div style="font-size:12px; color:#67c23a; margin-bottom:4px;">✅ 已收款合计</div>
            <div style="font-size:22px; font-weight:700; color:#67c23a;">¥{{ fmtMoney(totalPaid) }}</div>
          </div>
          <div style="background:#fdf6ec; border-radius:8px; padding:10px 20px; text-align:center;">
            <div style="font-size:12px; color:#e6a23c; margin-bottom:4px;">⏳ 欠款合计</div>
            <div style="font-size:22px; font-weight:700; color:#e6a23c;">¥{{ fmtMoney(totalDebt) }}</div>
          </div>
          <div style="background:#f5f5f5; border-radius:8px; padding:10px 20px; text-align:center;">
            <div style="font-size:12px; color:#909399; margin-bottom:4px;">📋 共</div>
            <div style="font-size:22px; font-weight:700; color:#303133;">{{ filtered.length }} 笔</div>
          </div>
        </div>
      </div>
      <el-button type="success" :loading="exporting" @click="exportPayments">⬇ 导出 Excel</el-button>
    </div>

    <!-- 筛选栏 -->
    <div style="display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap;">
      <el-input v-model="query.q" placeholder="搜索学员姓名/手机" clearable style="width:220px;" />
      <el-select v-model="query.pay_status" placeholder="状态筛选" clearable style="width:130px;">
        <el-option label="已结清" value="paid" />
        <el-option label="分期中" value="partial" />
        <el-option label="待付款" value="pending" />
        <el-option label="已退款" value="refunded" />
      </el-select>
      <el-select v-model="query.pay_method" placeholder="付款方式" clearable style="width:140px;">
        <el-option label="对公账户" value="company_account" />
        <el-option label="私户转账" value="private_account" />
        <el-option label="企业微信" value="wecom" />
        <el-option label="微信代收" value="wechat_proxy" />
      </el-select>
    </div>

    <!-- 表格（展开行显示消耗明细） -->
    <el-table :data="filtered" v-loading="loading" stripe border row-key="id" style="width:100%;">

      <!-- 展开行：消耗明细 -->
      <el-table-column type="expand" width="40">
        <template #default="{ row }">
          <div v-if="row.package_id && getConsumptions(row.package_id).length" style="padding:12px 20px 12px 60px;">
            <div style="font-weight:700; margin-bottom:10px; color:#303133;">
              📋 服务消耗明细（{{ row.pay_type_label }} · {{ row.total_times }}次 × ¥{{ fmtMoney(row.per_time_fee) }}/次）
            </div>
            <el-table :data="getConsumptions(row.package_id)" size="small" border style="width:100%;">
              <el-table-column label="期数" width="60" align="center">
                <template #default="{ row: c }">
                  <el-tag size="small" type="primary" round>第{{ c.visit_number }}期</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="服务内容" min-width="140">
                <template #default="{ row: c }">
                  <div style="font-weight:600;">{{ c.service_name }}</div>
                  <div v-if="c.service_category" style="font-size:11px; color:#909399;">{{ c.service_category }}</div>
                </template>
              </el-table-column>
              <el-table-column label="扣费" width="100" align="right">
                <template #default="{ row: c }">
                  <span style="color:#f56c6c; font-weight:700;">¥{{ fmtMoney(c.deducted_amount) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="下店日期" width="110">
                <template #default="{ row: c }">
                  {{ fmtDate(c.appoint_date) }}
                  <span v-if="c.duration_days" style="color:#909399; font-size:11px;">·{{ c.duration_days }}天</span>
                </template>
              </el-table-column>
              <el-table-column label="门店" min-width="120">
                <template #default="{ row: c }">{{ c.store_name || '-' }}</template>
              </el-table-column>
              <el-table-column label="执案老师" width="110">
                <template #default="{ row: c }">
                  <span style="color:#409eff; font-weight:500;">{{ c.consultant_name || '-' }}</span>
                  <span v-if="c.assistant_name" style="color:#909399; font-size:11px;"><br/>+{{ c.assistant_name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="满意度" width="100" align="center">
                <template #default="{ row: c }">
                  <span v-if="c.rating" :style="{ color: c.rating >= 4 ? '#67c23a' : c.rating >= 3 ? '#e6a23c' : '#f56c6c' }">
                    {{ ratingStars(c.rating) }}
                  </span>
                  <span v-else style="color:#c0c4cc;">待评价</span>
                </template>
              </el-table-column>
              <el-table-column label="执案摘要" min-width="200">
                <template #default="{ row: c }">
                  <el-tooltip v-if="c.summary && c.summary.length > 40" :content="c.summary" placement="top">
                    <span style="font-size:12px;">{{ c.summary.slice(0, 40) }}...</span>
                  </el-tooltip>
                  <span v-else-if="c.summary" style="font-size:12px;">{{ c.summary }}</span>
                  <span v-else style="color:#c0c4cc;">-</span>
                </template>
              </el-table-column>
            </el-table>
            <!-- 评价详情 -->
            <div v-for="c in getConsumptions(row.package_id).filter(x => x.rating_comment)" :key="c.id"
              style="margin-top:8px; padding:8px 12px; background:#f5f7fa; border-radius:6px; font-size:12px;">
              <span style="color:#409eff;">第{{ c.visit_number }}期评价：</span>
              <span style="color:#606266;">{{ c.rating_comment }}</span>
            </div>
          </div>
          <div v-else-if="row.package_id" style="padding:12px 20px 12px 60px; color:#909399;">
            暂无消耗记录（套餐尚未使用）
          </div>
          <div v-else style="padding:12px 20px 12px 60px; color:#c0c4cc;">
            未关联套餐（改造前的历史数据）
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="id" label="ID" width="60" />

      <el-table-column label="学员" min-width="150">
        <template #default="{ row }">
          <div style="font-weight:600;">{{ row.member_name || `ID#${row.member_id}` }}</div>
          <div v-if="row.enterprise_name" style="font-size:12px; color:#409eff;">{{ row.enterprise_name }}</div>
          <div style="font-size:12px; color:#909399;">{{ row.member_phone || '' }}</div>
        </template>
      </el-table-column>

      <el-table-column label="归属老师" width="100">
        <template #default="{ row }">
          <span style="color:#409eff;">{{ row.consultant_name || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="分公司" width="90">
        <template #default="{ row }">
          <span>{{ row.branch_name || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="合作项目" min-width="130">
        <template #default="{ row }">
          <span v-if="row.service_name" style="color:#409eff; font-weight:500;">{{ row.service_name }}</span>
          <span v-else style="color:#c0c4cc;">-</span>
        </template>
      </el-table-column>

      <el-table-column label="扣费明细" min-width="180">
        <template #default="{ row }">
          <div v-if="row.package_id">
            <div style="font-weight:600; color:#303133;">
              ¥{{ fmtMoney(row.per_time_fee) }}/次 × {{ row.total_times }}次
            </div>
            <div style="font-size:12px; color:#909399; margin-top:2px;">
              <el-tag size="small" :type="row.pay_type_label === '年费制' ? 'primary' : 'info'" style="margin-right:4px;">
                {{ row.pay_type_label }}
              </el-tag>
              已用{{ row.used_times }}次 · 剩余
              <span :style="{ color: row.remaining_times <= 1 ? '#f56c6c' : '#67c23a', fontWeight:'700' }">
                {{ row.remaining_times }}
              </span>次
            </div>
          </div>
          <span v-else style="color:#c0c4cc; font-size:12px;">未关联套餐</span>
        </template>
      </el-table-column>

      <el-table-column label="已付款" width="120">
        <template #default="{ row }">
          <span style="color:#67c23a; font-weight:700; font-size:15px;">¥{{ fmtMoney(row.amount) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="欠款" width="110">
        <template #default="{ row }">
          <span v-if="parseFloat(row.debt_amount) > 0"
            style="color:#e6a23c; font-weight:700; font-size:15px;">
            ¥{{ fmtMoney(row.debt_amount) }}
          </span>
          <span v-else style="color:#67c23a;">✓ 无欠款</span>
        </template>
      </el-table-column>

      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ typeName(row.pay_type) }}</template>
      </el-table-column>

      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.pay_status)" size="small">{{ statusLabel(row.pay_status) }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="付款时间" width="140">
        <template #default="{ row }">{{ fmt(row.pay_time) }}</template>
      </el-table-column>

      <el-table-column prop="remark" label="备注" min-width="120" />

      <el-table-column label="操作" width="80" fixed="right" v-if="isSuperAdmin">
        <template #default="{ row }">
          <el-popconfirm title="确认删除这笔缴费记录？删除后不可恢复！" confirm-button-text="删除" cancel-button-text="取消" @confirm="deletePayment(row.id)">
            <template #reference>
              <el-button type="danger" size="small" plain>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
