<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const router = useRouter();
const user = useUserStore();
const loading = ref(false);
const form = reactive({ username: 'admin', password: 'admin123' });

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请填写账号和密码');
    return;
  }
  loading.value = true;
  try {
    const data: any = await API.login(form.username, form.password);
    user.setLogin({ token: data.token, user: data.user, role: data.role });
    ElMessage.success('登录成功');
    router.push('/dashboard');
  } catch (e) {
    // http拦截器已弹提示
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="card">
      <div class="brand">
        <div class="brand-main">诺控·塔塔</div>
        <div class="brand-sub">学员管理系统 · 管理后台</div>
      </div>
      <el-form :model="form" label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="账号">
          <el-input v-model="form.username" placeholder="请输入账号" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password @keyup.enter="onSubmit" />
        </el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%;" @click="onSubmit">登录</el-button>
      </el-form>
      <div class="tips">默认账号：admin / admin123（首次启动自动创建）</div>
    </div>
  </div>
</template>

<style scoped>
.login-page { height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #409EFF 100%); }
.card { width: 360px; padding: 36px 32px; background: #fff; border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.15); }
.brand { text-align: center; margin-bottom: 28px; }
.brand-main { font-size: 24px; font-weight: 700; letter-spacing: 3px; color: #1f2d3d; }
.brand-sub { margin-top: 6px; font-size: 13px; color: #909399; }
.tips { margin-top: 16px; font-size: 12px; color: #c0c4cc; text-align: center; }
</style>
