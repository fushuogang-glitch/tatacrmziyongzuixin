<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { API } from '../../api';

const router = useRouter();
const query = reactive({ page: 1, size: 20, q: '', member_type: '', status: '' });
const total = ref(0);
const rows = ref<any[]>([]);
const loading = ref(false);

const dialog = reactive({ visible: false, mode: 'create' as 'create' | 'edit', form: {} as any });
const payDialog = reactive({ visible: false, member: null as any, form: { amount: 0, pay_type: 'annual', pay_status: 'paid', remark: '' } });

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
  dialog.form = { name: '', phone: '', enterprise_name: '', city: '', role: 'boss', member_type: 'trial', referral_code: '' };
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
  payDialog.form = { amount: 36800, pay_type: 'annual', pay_status: 'paid', remark: '' };
  payDialog.visible = true;
}

async function submitPay() {
  await API.paymentCreate({ member_id: payDialog.member.id, ...payDialog.form });
  ElMessage.success('已记录缴费');
  payDialog.visible = false;
  load();
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

onMounted(load);
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
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px;">
          <el-option label="在籍" value="active" />
          <el-option label="过期" value="expired" />
          <el-option label="冻结" value="frozen" />
        </el-select>
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="openCreate">新增学员</el-button>
      </div>

      <el-table :data="rows" v-loading="loading" stripe style="margin-top: 16px;">
        <el-table-column prop="member_no" label="编号" width="130" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="phone" label="手机" width="130" />
        <el-table-column prop="enterprise_name" label="企业" min-width="160" />
        <el-table-column prop="city" label="城市" width="100" />
        <el-table-column prop="role" label="角色" width="90" />
        <el-table-column label="会员" width="90">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.member_type)">{{ typeLabel(row.member_type) }}</el-tag>
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

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增学员' : '编辑学员'" width="520px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="姓名" required><el-input v-model="dialog.form.name" /></el-form-item>
        <el-form-item label="手机号" required><el-input v-model="dialog.form.phone" :disabled="dialog.mode === 'edit'" /></el-form-item>
        <el-form-item label="企业"><el-input v-model="dialog.form.enterprise_name" /></el-form-item>
        <el-form-item label="城市"><el-input v-model="dialog.form.city" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="dialog.form.role">
            <el-option label="老板 boss" value="boss" />
            <el-option label="经理 manager" value="manager" />
            <el-option label="顾问 consultant" value="consultant" />
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
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="payDialog.visible" title="记录缴费" width="460px">
      <div v-if="payDialog.member" style="margin-bottom: 12px; color: #606266;">
        {{ payDialog.member.name }} · {{ payDialog.member.phone }}
      </div>
      <el-form :model="payDialog.form" label-width="80px">
        <el-form-item label="金额"><el-input-number v-model="payDialog.form.amount" :min="0" :step="1000" style="width: 100%;" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="payDialog.form.pay_type">
            <el-option label="试听" value="trial" />
            <el-option label="年费" value="annual" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="payDialog.form.pay_status">
            <el-option label="已支付" value="paid" />
            <el-option label="待支付" value="pending" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="payDialog.form.remark" type="textarea" /></el-form-item>
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
