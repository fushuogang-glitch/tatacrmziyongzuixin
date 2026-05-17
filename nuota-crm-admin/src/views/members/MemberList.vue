<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const router = useRouter();
const user = useUserStore();
const isAdmin = computed(() => user.role !== 'consultant');
const query = reactive({ page: 1, size: 20, q: '', member_type: '', status: '', tier: '' });
const total = ref(0);
const rows = ref<any[]>([]);
const loading = ref(false);
const exporting = ref(false);
const consultants = ref<any[]>([]); // 老师列表
const services = ref<any[]>([]); // 合作项目列表

async function loadConsultants() {
  try {
    const d: any = await API.consultantList();
    consultants.value = d.items || d || [];
  } catch { consultants.value = []; }
  try {
    const s: any = await API.serviceList();
    services.value = s || [];
  } catch { services.value = []; }
}

async function exportMembers() {
  exporting.value = true;
  try {
    const blob = await API.exportMembers() as any;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `学员列表_${new Date().toISOString().slice(0,10)}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    ElMessage.error('导出失败');
  } finally {
    exporting.value = false;
  }
}

const dialog = reactive({ visible: false, mode: 'create' as 'create' | 'edit', form: {} as any });
const payDialog = reactive({
  visible: false,
  member: null as any,
  form: {
    amount: 0, debt_amount: 0,
    pay_mode: 'full', pay_method: null as string | null,
    pay_type: 'annual', pay_status: 'paid',
    consultant_id: null as number | null,
    service_id: null as number | null,
    total_times: 6,
    remark: '',
    due_date: null as string | null,
  }
});

async function load() {
  loading.value = true;
  try {
    const d: any = await API.memberList(query);
    rows.value = d.items || [];
    total.value = d.total || 0;
  } finally {
    loading.value = false;
  }
}

function onSearch() { query.page = 1; load(); }

function openCreate() {
  dialog.mode = 'create';
  dialog.form = {
    name: '', phone: '', enterprise_name: '', city: '', role: 'boss',
    member_type: 'trial', referral_code: '',
    store_count: 1, store_type: '', pre_annual_revenue: null,
    consultant_id: null,
    cooperation_years: 0,
    gender: 'female',
    birthday: null,
    co_manager_name: '',
    co_manager_phone: '',
    // 首次付款
    first_payment_amount: null, first_payment_debt: 0,
    first_payment_mode: 'full', first_payment_method: null,
    first_payment_remark: '',
  };
  dialog.visible = true;
}

function openEdit(row: any) {
  dialog.mode = 'edit';
  dialog.form = { ...row };
  dialog.visible = true;
}

async function submit() {
  if (!dialog.form.name || !dialog.form.phone) {
    ElMessage.warning('姓名、手机号必填');
    return;
  }
  if (dialog.mode === 'create') {
    await API.memberCreate(dialog.form);
    ElMessage.success('新增成功');
  } else {
    await API.memberUpdate(dialog.form.id, dialog.form);
    ElMessage.success('保存成功');
  }
  dialog.visible = false;
  load();
}

function openPay(row: any) {
  payDialog.member = row;
  payDialog.form = {
    amount: 36800, debt_amount: 0,
    pay_mode: 'full', pay_method: null,
    pay_type: 'annual', pay_status: 'paid',
    consultant_id: row.consultant_id || null,
    service_id: null as number | null,
    total_times: 6,
    due_date: null,
    remark: ''
  };
  payDialog.visible = true;
}

async function submitPay() {
  if (!payDialog.form.amount) { ElMessage.warning('请填写付款金额'); return; }
  await API.paymentCreate({ member_id: payDialog.member.id, ...payDialog.form });
  ElMessage.success('已记录缴费' + (payDialog.form.pay_type === 'trial' ? '' : `，自动创建套餐 ${payDialog.form.total_times}次`));
  payDialog.visible = false;
  load();
}

function onPayTypeChange(val: string) {
  if (val === 'annual') {
    payDialog.form.total_times = 6;
  } else if (val === 'single') {
    payDialog.form.total_times = 1;
  } else {
    payDialog.form.total_times = 1;
  }
}

function typeTag(t: string) {
  return { trial: 'info', annual: 'success', vip: 'warning' }[t] || '';
}
function typeLabel(t: string) {
  return { trial: '试听', annual: '年费', vip: 'VIP' }[t] || t;
}
function statusTag(s: string) {
  return { active: 'success', expired: 'info', frozen: 'danger' }[s] || '';
}
function roleName(r: string) {
  const m: Record<string, string> = { boss: '👑 老板', partner: '🤝 合伙人', store_manager: '🏪 店长', operations_gm: '📊 运营总经理', manager: '👔 经理' };
  return m[r] || r || '—';
}
function tierName(t: string) {
  const m: Record<string, string> = { kindergarten: '⚔️七杀星·南斗度厄', primary: '💰天相星·南斗司禄', junior: '🏮天同星·南斗益算', senior: '🔮天机星·南斗上生', college: '🛡️天梁星·南斗延寿', bachelor: '⭐天府星·南斗司命', master: '🌙太阴元君', doctor: '☀️日宫太阳帝君', postdoc: '💜紫微大帝' };
  return m[t] || t || '⚔️七杀星';
}

const storeTypes = [
  '双美', '生美', '医疗美容', '大健康机构', '养生',
  '美甲美睾', '仪器供应商', '产品供应商', '医美供应商', '仪器销售商',
];

onMounted(() => { load(); loadConsultants(); });
</script>

<template>
  <div>
    <el-card>
      <div class="toolbar">
        <el-input v-model="query.q" placeholder="搜索姓名/手机/编号/企业" clearable style="width: 260px;" @keyup.enter="onSearch" />
        <el-select v-model="query.member_type" placeholder="会员类型" clearable style="width: 140px;">
          <el-option label="试听" value="trial" />
          <el-option label="年费" value="annual" />
          <el-option label="VIP" value="vip" />
        </el-select>
        <el-select v-model="query.tier" placeholder="会员等级" clearable style="width: 140px;">
          <el-option label="⚔️L1 七杀星·南斗度厄" value="kindergarten" />
          <el-option label="💰L2 天相星·南斗司禄" value="primary" />
          <el-option label="🏮L3 天同星·南斗益算" value="junior" />
          <el-option label="🔮L4 天机星·南斗上生" value="senior" />
          <el-option label="🛡️L5 天梁星·南斗延寿" value="college" />
          <el-option label="⭐L6 天府星·南斗司命" value="bachelor" />
          <el-option label="🌙L7 太阴元君" value="master" />
          <el-option label="☀️L8 日宫太阳帝君" value="doctor" />
          <el-option label="💜L9 紫微大帝" value="postdoc" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px;">
          <el-option label="在籍" value="active" />
          <el-option label="过期" value="expired" />
          <el-option label="冻结" value="frozen" />
        </el-select>
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="openCreate">新增学员</el-button>
        <el-button type="success" v-if="isAdmin" :loading="exporting" @click="exportMembers">⬇ 导出 Excel</el-button>
      </div>

      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="member_no" label="编号" width="130" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="phone" label="手机" width="130" />
        <el-table-column prop="enterprise_name" label="企业" min-width="160" />
        <el-table-column prop="city" label="城市" width="100" />
        <el-table-column label="性别" width="70">
          <template #default="{ row }">
            <span>{{ row.gender === 'male' ? '♂' : '♀' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <span>{{ roleName(row.role) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="等级" width="110">
          <template #default="{ row }">
            <span>{{ tierName(row.member_tier) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="副负责人" width="140">
          <template #default="{ row }">
            <span v-if="row.co_manager_name">{{ row.co_manager_name }}</span>
            <span v-else style="color:#c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="referral_code" label="推荐码" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/members/${row.id}`)">详情</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="success" @click="openPay(row)">缴费</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        style="margin-top: 16px; justify-content: flex-end; display: flex;"
        v-model:current-page="query.page" v-model:page-size="query.size"
        :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next"
        @current-change="load" @size-change="load"
      />
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增学员' : '编辑学员'" width="580px">
      <el-form :model="dialog.form" label-width="100px">
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="姓名" required><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="手机号" required><el-input v-model="dialog.form.phone" :disabled="dialog.mode === 'edit'" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="dialog.form.gender">
            <el-radio value="female">♀ 女士</el-radio>
            <el-radio value="male">♂ 先生</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="生日">
          <el-date-picker v-model="dialog.form.birthday" type="date" value-format="YYYY-MM-DD" placeholder="选择生日" style="width:100%" />
        </el-form-item>
        <el-form-item label="企业"><el-input v-model="dialog.form.enterprise_name" /></el-form-item>
        <el-form-item label="门店数量">
          <el-select v-model="dialog.form.store_count" style="width:100%">
            <el-option v-for="n in 100" :key="n" :value="n" :label="`${n} 家`" />
          </el-select>
        </el-form-item>
        <el-form-item label="门店性质">
          <el-select v-model="dialog.form.store_type" style="width:100%" clearable placeholder="请选择">
            <el-option v-for="t in storeTypes" :key="t" :value="t" :label="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="合作前产值">
          <el-input-number v-model="dialog.form.pre_annual_revenue" :min="0" :step="100000" style="width:100%" placeholder="元/年" />
          <div style="font-size:12px;color:#999;margin-top:4px">合作前上一年度门店总产值（元）</div>
        </el-form-item>
        <el-form-item label="城市"><el-input v-model="dialog.form.city" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="dialog.form.role">
            <el-option label="👑 老板" value="boss" />
            <el-option label="🤝 合伙人" value="partner" />
            <el-option label="🏪 店长" value="store_manager" />
            <el-option label="📊 运营总经理" value="operations_gm" />
            <el-option label="👔 经理" value="manager" />
            <el-option label="老师 consultant" value="consultant" />
          </el-select>
        </el-form-item>
        <el-form-item label="会员类型">
          <el-select v-model="dialog.form.member_type">
            <el-option label="试听" value="trial" />
            <el-option label="年费" value="annual" />
            <el-option label="VIP" value="vip" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dialog.mode === 'create'" label="推荐码"><el-input v-model="dialog.form.referral_code" placeholder="可选" /></el-form-item>
        <el-form-item v-if="dialog.mode === 'edit'" label="状态">
          <el-select v-model="dialog.form.status">
            <el-option label="在籍" value="active" />
            <el-option label="过期" value="expired" />
            <el-option label="冻结" value="frozen" />
          </el-select>
        </el-form-item>

        <el-divider v-if="isAdmin" content-position="left">归属老师</el-divider>
        <el-form-item v-if="isAdmin" label="归属老师">
          <el-select v-model="dialog.form.consultant_id" style="width:100%" clearable placeholder="请选择归属老师">
            <el-option v-for="c in consultants" :key="c.id" :value="c.id" :label="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="合作年限">
          <el-input-number v-model="dialog.form.cooperation_years" :min="0" :max="50" style="width:100%" />
        </el-form-item>

        <el-divider content-position="left">副负责人（合伙人/总经理）</el-divider>
        <el-form-item label="副负责人姓名">
          <el-input v-model="dialog.form.co_manager_name" placeholder="如无可留空" />
        </el-form-item>
        <el-form-item label="副负责人手机">
          <el-input v-model="dialog.form.co_manager_phone" placeholder="副负责人登录小程序用此手机号" />
        </el-form-item>

        <template v-if="dialog.mode === 'create'">
          <el-divider content-position="left">首次付款（选填）</el-divider>
          <el-form-item label="付费模式">
            <el-radio-group v-model="dialog.form.first_payment_mode">
              <el-radio value="full">全款</el-radio>
              <el-radio value="installment">分期</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="付款方式">
            <el-select v-model="dialog.form.first_payment_method" style="width:100%" clearable placeholder="请选择">
              <el-option label="对公账户" value="company_account" />
              <el-option label="私户转账" value="private_account" />
              <el-option label="企业微信" value="wecom" />
              <el-option label="微信代收" value="wechat_proxy" />
            </el-select>
          </el-form-item>
          <el-form-item label="付款金额">
            <el-input-number v-model="dialog.form.first_payment_amount" :min="0" :step="1000" style="width:100%" placeholder="实际到账金额" />
          </el-form-item>
          <el-form-item label="欠款金额">
            <el-input-number v-model="dialog.form.first_payment_debt" :min="0" :step="1000" style="width:100%" placeholder="0 表示无欠款" />
          </el-form-item>
          <el-form-item label="补款截止日">
            <el-date-picker v-model="dialog.form.first_payment_due_date" type="date"
              value-format="YYYY-MM-DD" placeholder="选择补款截止日期" style="width:100%" />
            <div style="font-size:12px;color:#e6a817;margin-top:4px">📅 到期前一天系统自动提醒老师追款</div>
          </el-form-item>
          <el-form-item label="备注"><el-input v-model="dialog.form.first_payment_remark" type="textarea" rows="2" /></el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="payDialog.visible" title="记录缴费" width="560px">
      <div v-if="payDialog.member" style="margin-bottom:12px;color:#606266;font-weight:500;">
        {{ payDialog.member.name }} · {{ payDialog.member.phone }}
        <span v-if="payDialog.member.enterprise_name" style="color:#409eff;margin-left:8px;">{{ payDialog.member.enterprise_name }}</span>
      </div>
      <el-form :model="payDialog.form" label-width="90px">
        <el-form-item label="归属老师" v-if="isAdmin">
          <el-select v-model="payDialog.form.consultant_id" style="width:100%" clearable placeholder="请选择老师">
            <el-option v-for="c in consultants" :key="c.id" :value="c.id" :label="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="合作项目">
          <el-select v-model="payDialog.form.service_id" style="width:100%" clearable placeholder="选择关联专案/服务" filterable>
            <el-option v-for="s in services" :key="s.id" :value="s.id" :label="`${s.name} · ¥${s.price || 0}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="收费类型">
          <el-radio-group v-model="payDialog.form.pay_type" @change="onPayTypeChange">
            <el-radio value="annual">年费制（打包）</el-radio>
            <el-radio value="single">单次制</el-radio>
            <el-radio value="trial">体验费</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="付费模式">
          <el-radio-group v-model="payDialog.form.pay_mode">
            <el-radio value="full">全款</el-radio>
            <el-radio value="installment">分期</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="付款方式">
          <el-select v-model="payDialog.form.pay_method" style="width:100%" clearable placeholder="请选择">
            <el-option label="对公账户" value="company_account" />
            <el-option label="私户转账" value="private_account" />
            <el-option label="企业微信" value="wecom" />
            <el-option label="微信代收" value="wechat_proxy" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款金额"><el-input-number v-model="payDialog.form.amount" :min="0" :step="1000" style="width:100%;" /></el-form-item>
        <el-form-item label="服务次数" v-if="payDialog.form.pay_type !== 'trial'">
          <el-input-number v-model="payDialog.form.total_times" :min="1" :max="100" style="width:100%;" />
          <div style="font-size:12px;color:#409eff;margin-top:4px" v-if="payDialog.form.amount && payDialog.form.total_times">
            💰 每次扣费：¥{{ Math.round(payDialog.form.amount / payDialog.form.total_times).toLocaleString() }}
            <span v-if="payDialog.form.pay_type === 'annual'">（年费制固定扣费，客户任选品项）</span>
          </div>
        </el-form-item>
        <el-form-item label="欠款金额"><el-input-number v-model="payDialog.form.debt_amount" :min="0" :step="1000" style="width:100%;" /><div style="font-size:12px;color:#999;margin-top:4px">分期未收款项，0 表示已结清</div></el-form-item>
        <el-form-item label="补款截止日">
          <el-date-picker v-model="payDialog.form.due_date" type="date"
            value-format="YYYY-MM-DD" placeholder="选择补款截止日期" style="width:100%" />
          <div style="font-size:12px;color:#e6a817;margin-top:4px">📅 到期前一天自动提醒老师</div>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="payDialog.form.remark" type="textarea" rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="payDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitPay">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; flex-wrap: wrap; }
</style>
