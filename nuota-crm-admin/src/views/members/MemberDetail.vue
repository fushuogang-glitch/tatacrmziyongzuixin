<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { API } from '../../api';

const route = useRoute();
const router = useRouter();
const id = Number(route.params.id);
const member = ref<any>(null);
const payments = ref<any[]>([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    member.value = await API.memberDetail(id);
    payments.value = (await API.paymentList(id) as any) || [];
  } finally {
    loading.value = false;
  }
}

function fmt(v: any) {
  if (!v) return '-';
  return String(v).replace('T', ' ').slice(0, 19);
}

onMounted(load);
</script>

<template>
  <div v-loading="loading">
    <el-page-header @back="router.back()" style="margin-bottom: 16px;">
      <template #content><span>学员详情</span></template>
    </el-page-header>
    <el-card v-if="member">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="编号">{{ member.member_no }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ member.name }}</el-descriptions-item>
        <el-descriptions-item label="手机">{{ member.phone }}</el-descriptions-item>
        <el-descriptions-item label="企业">{{ member.enterprise_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="城市">{{ member.city || '-' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ member.role || '-' }}</el-descriptions-item>
        <el-descriptions-item label="会员类型">{{ member.member_type }}</el-descriptions-item>
        <el-descriptions-item label="推荐码">{{ member.referral_code }}</el-descriptions-item>
        <el-descriptions-item label="推荐人ID">{{ member.referred_by || '-' }}</el-descriptions-item>
        <el-descriptions-item label="入学">{{ member.enroll_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="到期">{{ member.expire_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ member.status }}</el-descriptions-item>
        <el-descriptions-item label="人脸">{{ member.face_token ? '已绑定' : '未绑定' }}</el-descriptions-item>
        <el-descriptions-item label="openid">{{ member.openid || '-' }}</el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ fmt(member.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 16px;">
      <template #header><span>缴费记录</span></template>
      <el-table :data="payments" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="amount" label="金额" width="120" />
        <el-table-column prop="pay_type" label="类型" width="100" />
        <el-table-column prop="pay_status" label="状态" width="100" />
        <el-table-column label="支付时间" width="170">
          <template #default="{ row }">{{ fmt(row.pay_time) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" />
      </el-table>
    </el-card>
  </div>
</template>
