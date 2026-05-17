<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const router = useRouter();
const user = useUserStore();
const loading = ref(false);
const tab = ref<'login' | 'register'>('login');

const loginForm = reactive({ username: '', password: '' });
const regForm = reactive({
  name: '', phone: '', password: '', confirmPassword: '',
  company: '',
});

const companies = [
  '上海嘉塔诺塔管理咨询有限公司',
  '武汉塔塔咨询有限公司',
  '南京塔塔咨询有限公司',
];

// 统一登录：先尝试 admin_users 表，再尝试 consultant 表
async function onLogin() {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请填写手机号和密码'); return;
  }
  loading.value = true;
  try {
    // 第一步：尝试后台账号（admin_users 表）
    let data: any = null;
    let isConsultant = false;
    try {
      data = await API.login(loginForm.username, loginForm.password);
    } catch {
      // admin 登录失败，尝试老师接口
      try {
        const res: any = await API.post('/consultant-auth/login', {
          phone: loginForm.username,
          password: loginForm.password,
        });
        data = { token: res.data.token, user: res.data.consultant, role: 'consultant', consultantId: res.data.consultant?.id };
        isConsultant = true;
      } catch {
        throw new Error('手机号或密码错误');
      }
    }
    // 第二步：存 token 再跳转，避免页面加载时 token 还没存
    user.setLogin({ token: data.token, user: data.user, role: data.role, consultantId: data.consultantId });
    ElMessage.success('登录成功');
    // 等 300ms 确保 token 写入 + 拦截器稳定后再跳转
    await new Promise(r => setTimeout(r, 300));
    const dest = isConsultant || data.role === 'consultant' ? '/my-dashboard' : '/dashboard';
    await router.push(dest);
  } catch (e: any) {
    ElMessage.error(e?.message || e?.response?.data?.detail || '手机号或密码错误');
  } finally {
    loading.value = false;
  }
}

async function onRegister() {
  if (!regForm.name || !regForm.phone || !regForm.password) {
    ElMessage.warning('请填写姓名、手机号和密码'); return;
  }
  if (regForm.password !== regForm.confirmPassword) {
    ElMessage.error('两次密码不一致'); return;
  }
  loading.value = true;
  try {
    await API.post('/admin/register', {
      name: regForm.name,
      phone: regForm.phone,
      password: regForm.password,
      company: regForm.company,
    });
    ElMessage.success('注册成功！等待管理员分配权限后即可登录');
    tab.value = 'login';
    loginForm.username = regForm.phone;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '注册失败');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="card">
      <div class="brand">
        <div class="brand-logo">TATA CONSULTING<sup>®</sup></div>
        <div class="brand-sub">诺控 · 学员管理系统</div>
      </div>

      <div class="tabs">
        <button :class="['tab-btn', tab === 'login' && 'active']" @click="tab = 'login'">登 录</button>
        <button :class="['tab-btn', tab === 'register' && 'active']" @click="tab = 'register'">注 册</button>
      </div>

      <!-- 登录 -->
      <el-form v-if="tab === 'login'" label-position="top" @submit.prevent="onLogin">
        <el-form-item label="手机号">
          <el-input v-model="loginForm.username" placeholder="请输入手机号" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码"
            show-password @keyup.enter="onLogin" />
        </el-form-item>
        <el-button type="primary" :loading="loading" style="width:100%;margin-top:8px" @click="onLogin">
          登 录
        </el-button>
        <div class="sub-tip">登录后权限由超级管理员分配</div>
      </el-form>

      <!-- 注册 -->
      <el-form v-else label-position="top" @submit.prevent="onRegister">
        <el-form-item label="姓名">
          <el-input v-model="regForm.name" placeholder="请输入真实姓名" clearable />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="regForm.phone" placeholder="请输入手机号" clearable />
        </el-form-item>
        <el-form-item label="所属分公司">
          <el-select v-model="regForm.company" placeholder="请选择（可选）" clearable style="width:100%">
            <el-option v-for="c in companies" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="设置密码">
          <el-input v-model="regForm.password" type="password" placeholder="请设置密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="regForm.confirmPassword" type="password" placeholder="再次输入密码" show-password />
        </el-form-item>
        <div class="reg-tip">注册后需超级管理员分配角色才能正常使用</div>
        <el-button type="primary" :loading="loading" style="width:100%;margin-top:8px" @click="onRegister">
          提交注册
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(150deg, #0a0a0a 0%, #1a1410 50%, #0d0d0d 100%);
}
.card {
  width: 400px; padding: 36px 32px; background: #fff;
  border-radius: 16px; box-shadow: 0 24px 60px rgba(0,0,0,0.4);
}
.brand { text-align: center; margin-bottom: 20px; }
.brand-logo {
  font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
  font-size: 20px; font-weight: 700; letter-spacing: 3px; color: #0a0a0a;
}
.brand-logo sup { font-size: 11px; }
.brand-sub { margin-top: 5px; font-size: 12px; color: #909399; letter-spacing: 1px; }

.tabs {
  display: flex; gap: 4px; background: #f5f5f5;
  border-radius: 8px; padding: 4px; margin-bottom: 20px;
}
.tab-btn {
  flex: 1; border: none; background: transparent; padding: 8px 0;
  border-radius: 6px; cursor: pointer; font-size: 14px; color: #666; transition: all .2s;
}
.tab-btn.active {
  background: #fff; color: #0a0a0a; font-weight: 600;
  box-shadow: 0 1px 4px rgba(0,0,0,0.12);
}
.sub-tip { text-align: center; font-size: 12px; color: #bbb; margin-top: 10px; }
.reg-tip {
  font-size: 12px; color: #c9a96e; text-align: center;
  padding: 7px; background: #fdf8f0; border-radius: 6px; margin-bottom: 4px;
}
</style>
