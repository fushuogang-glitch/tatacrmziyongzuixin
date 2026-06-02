<template>
  <view class="page">
    <view class="header">
      <text class="header-en">REGISTRATION</text>
      <view class="header-line"></view>
      <text class="header-cn">完 善 个 人 信 息</text>
      <text class="header-desc">填写后即可开通塔塔会员权益</text>
    </view>

    <!-- 模式切换 -->
    <view class="mode-switch">
      <view :class="['mode-tab', mode === 'referral' ? 'active' : '']" @tap="switchMode('referral')">
        <text class="mode-icon">🏢</text>
        <text class="mode-text">推荐码注册</text>
        <text class="mode-desc">会员推荐 / 老师推荐</text>
      </view>
      <view :class="['mode-tab', mode === 'invite' ? 'active' : '']" @tap="switchMode('invite')">
        <text class="mode-icon">👤</text>
        <text class="mode-text">员工加入</text>
        <text class="mode-desc">用邀请码加入企业</text>
      </view>
    </view>

    <view class="form">
      <!-- ===== 推荐码模式 ===== -->
      <template v-if="mode === 'referral'">
        <view class="form-group">
          <text class="form-label">推 荐 码</text>
          <text class="form-required">*</text>
          <input class="form-input" v-model="form.referral_code"
                 placeholder="输入推荐码" placeholder-class="ph"
                 @blur="verifyReferral" />
        </view>

        <!-- 推荐来源提示 -->
        <view class="ref-info" v-if="refInfo">
          <view class="ref-info-icon">✓</view>
          <view class="ref-info-body">
            <text class="ref-info-hint">{{ refInfo.hint }}</text>
            <text class="ref-info-detail" v-if="refInfo.enterprise_name">企业：{{ refInfo.enterprise_name }}</text>
          </view>
        </view>

        <view class="form-group">
          <text class="form-label">姓 名</text>
          <text class="form-required">*</text>
          <input class="form-input" v-model="form.name" placeholder="请输入您的姓名" placeholder-class="ph" />
        </view>

        <view class="form-group">
          <text class="form-label">手 机 号</text>
          <text class="form-required">*</text>
          <input class="form-input" v-model="form.phone" type="number" maxlength="11" placeholder="11位手机号码" placeholder-class="ph" />
        </view>

        <view class="form-group">
          <text class="form-label">企 业</text>
          <text class="form-required">*</text>
          <input class="form-input" v-model="form.enterprise_name" placeholder="您的品牌/企业名称" placeholder-class="ph" />
        </view>

        <view class="form-group last">
          <text class="form-label">城 市</text>
          <text class="form-required">*</text>
          <input class="form-input" v-model="form.city" placeholder="所在城市" placeholder-class="ph" />
        </view>
      </template>

      <!-- ===== 邀请码模式 ===== -->
      <template v-else>
        <view class="form-group">
          <text class="form-label">邀 请 码</text>
          <text class="form-required">*</text>
          <input class="form-input" v-model="form.invite_code" maxlength="6"
                 placeholder="输入6位企业邀请码" placeholder-class="ph"
                 @blur="verifyInvite" />
        </view>

        <!-- 企业信息提示 -->
        <view class="enterprise-info" v-if="inviteInfo">
          <text class="ei-label">即将加入</text>
          <text class="ei-name">{{ inviteInfo.enterprise_name }}</text>
          <text class="ei-role">（{{ roleMap[inviteInfo.role] || inviteInfo.role }}）</text>
        </view>

        <view class="form-group">
          <text class="form-label">姓 名</text>
          <text class="form-required">*</text>
          <input class="form-input" v-model="form.name" placeholder="请输入您的姓名" placeholder-class="ph" />
        </view>

        <view class="form-group last">
          <text class="form-label">手 机 号</text>
          <text class="form-required">*</text>
          <input class="form-input" v-model="form.phone" type="number" maxlength="11" placeholder="11位手机号码" placeholder-class="ph" />
        </view>
      </template>
    </view>

    <view class="btn-area">
      <button class="btn-submit" @tap="submit">
        {{ mode === 'referral' ? '注 册 成 为 会 员' : '加 入 企 业' }}
      </button>
      <text class="btn-tip" v-if="mode === 'referral'">推荐码可向塔塔老师或会员老板索取</text>
      <text class="btn-tip" v-else>请向您的老板索取6位邀请码</text>
    </view>

    <view class="footer">
      <text class="footer-en">— TATA CONSULTING® —</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { api } from '../../api';
import { useUserStore } from '../../store/user';

const store = useUserStore();
const mode = ref<'referral' | 'invite'>('referral');
const refInfo = ref<any>(null);
const inviteInfo = ref<any>(null);

const roleMap: Record<string, string> = {
  boss: '老板', manager: '店长', consultant: '顾问',
};

const form = reactive<any>({
  name: '',
  phone: '',
  enterprise_name: '',
  city: '',
  referral_code: '',
  invite_code: '',
});

function switchMode(m: string) {
  mode.value = m as any;
  refInfo.value = null;
  inviteInfo.value = null;
}

// 验证推荐码
async function verifyReferral() {
  const code = (form.referral_code || '').trim();
  if (code.length < 3) { refInfo.value = null; return; }
  try {
    const res: any = await api.verifyReferral(code);
    refInfo.value = res;
  } catch (e: any) {
    refInfo.value = null;
    uni.showToast({ title: e?.msg || '推荐码无效', icon: 'none' });
  }
}

// 验证邀请码
async function verifyInvite() {
  const code = (form.invite_code || '').trim();
  if (code.length < 4) { inviteInfo.value = null; return; }
  try {
    const res: any = await api.verifyInvite(code);
    inviteInfo.value = res;
  } catch (e: any) {
    inviteInfo.value = null;
    if (code.length >= 6) {
      uni.showToast({ title: e?.msg || '邀请码无效', icon: 'none' });
    }
  }
}

async function submit() {
  if (!form.name.trim()) {
    return uni.showToast({ title: '请输入姓名', icon: 'none' });
  }
  if (!/^1\d{10}$/.test(form.phone)) {
    return uni.showToast({ title: '请输入正确手机号', icon: 'none' });
  }

  if (mode.value === 'referral') {
    if (!form.referral_code.trim()) {
      return uni.showToast({ title: '请输入推荐码', icon: 'none' });
    }
    if (!refInfo.value) {
      return uni.showToast({ title: '请先验证推荐码', icon: 'none' });
    }
    if (!form.enterprise_name.trim()) {
      return uni.showToast({ title: '请输入企业名称', icon: 'none' });
    }
    if (!form.city.trim()) {
      return uni.showToast({ title: '请输入所在城市', icon: 'none' });
    }
  } else {
    if (!form.invite_code.trim()) {
      return uni.showToast({ title: '请输入邀请码', icon: 'none' });
    }
    if (!inviteInfo.value) {
      return uni.showToast({ title: '请先验证邀请码', icon: 'none' });
    }
  }

  uni.showLoading({ title: '提交中...' });
  try {
    const payload: any = {
      name: form.name,
      phone: form.phone,
      member_type: 'trial',
    };

    if (mode.value === 'referral') {
      payload.referral_code = form.referral_code.trim();
      payload.enterprise_name = form.enterprise_name;
      payload.city = form.city;
      payload.role = 'boss';
      payload.create_enterprise = true;
    } else {
      payload.invite_code = form.invite_code.toUpperCase();
      payload.role = inviteInfo.value.role;
    }

    const res: any = await api.register(payload);
    store.setToken(res.token);
    store.setUser(res.user);
    uni.setStorageSync('member', res.user);

    const msg = mode.value === 'referral' ? '注册成功！' : `已加入${inviteInfo.value?.enterprise_name || '企业'}`;
    uni.showToast({ title: msg, icon: 'success', duration: 1500 });

    setTimeout(() => {
      // 人脸绑定暂时隐藏，直接跳转会员中心
      uni.switchTab({ url: '/pages/member/index' });
    }, 1500);
  } catch (_) { /* 已 toast */ }
  finally { uni.hideLoading(); }
}
</script>

<style lang="scss">
.page {
  background: #fff;
  min-height: 100vh;
  font-family: -apple-system, "PingFang SC", "Noto Serif SC", sans-serif;
}

.header {
  padding: 80rpx 48rpx 48rpx;
  text-align: center;
  background: linear-gradient(180deg, #fafaf8 0%, #fff 100%);
  border-bottom: 1rpx solid #ebe8e2;
}
.header-en {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 8rpx;
  font-style: italic;
  margin-bottom: 16rpx;
}
.header-line {
  width: 48rpx;
  height: 1rpx;
  background: #c9a96e;
  margin: 0 auto 16rpx;
}
.header-cn {
  display: block;
  font-size: 36rpx;
  letter-spacing: 12rpx;
  color: #0a0a0a;
  font-weight: 500;
  margin-bottom: 12rpx;
}
.header-desc {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 3rpx;
}

.mode-switch {
  display: flex;
  padding: 32rpx 48rpx 0;
  gap: 24rpx;
}
.mode-tab {
  flex: 1;
  padding: 28rpx 20rpx;
  border: 2rpx solid #ebe8e2;
  border-radius: 20rpx;
  text-align: center;
  transition: all 0.3s;
}
.mode-tab.active {
  border-color: #c9a96e;
  background: linear-gradient(135deg, #faf8f4 0%, #fff 100%);
  box-shadow: 0 4rpx 16rpx rgba(201, 169, 110, 0.15);
}
.mode-icon {
  display: block;
  font-size: 48rpx;
  margin-bottom: 8rpx;
}
.mode-text {
  display: block;
  font-size: 28rpx;
  font-weight: 500;
  color: #0a0a0a;
  letter-spacing: 4rpx;
  margin-bottom: 8rpx;
}
.mode-tab.active .mode-text {
  color: #c9a96e;
}
.mode-desc {
  display: block;
  font-size: 20rpx;
  color: #9a9a9a;
  letter-spacing: 1rpx;
}

/* 推荐码来源提示 */
.ref-info {
  margin: 16rpx 48rpx;
  padding: 20rpx 28rpx;
  background: linear-gradient(135deg, #f0faf0 0%, #fafff8 100%);
  border-left: 4rpx solid #52c41a;
  border-radius: 8rpx;
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
}
.ref-info-icon {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: #52c41a;
  color: #fff;
  font-size: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 4rpx;
}
.ref-info-body {
  flex: 1;
}
.ref-info-hint {
  display: block;
  font-size: 28rpx;
  color: #0a0a0a;
  font-weight: 500;
}
.ref-info-detail {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  margin-top: 6rpx;
}

/* 企业信息卡 */
.enterprise-info {
  margin: 16rpx 48rpx;
  padding: 20rpx 28rpx;
  background: #faf8f4;
  border-left: 4rpx solid #c9a96e;
  border-radius: 8rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.ei-label {
  font-size: 22rpx;
  color: #9a9a9a;
}
.ei-name {
  font-size: 28rpx;
  color: #0a0a0a;
  font-weight: 500;
}
.ei-role {
  font-size: 22rpx;
  color: #c9a96e;
}

.form {
  padding: 16rpx 48rpx;
}
.form-group {
  padding: 32rpx 0;
  border-bottom: 1rpx solid #ebe8e2;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}
.form-group.last {
  border-bottom: none;
}
.form-label {
  font-size: 26rpx;
  letter-spacing: 6rpx;
  color: #0a0a0a;
  font-weight: 500;
  width: 160rpx;
}
.form-required {
  color: #c9a96e;
  font-size: 28rpx;
  margin-right: 16rpx;
}
.form-input {
  flex: 1;
  font-size: 28rpx;
  color: #0a0a0a;
  letter-spacing: 2rpx;
}
.ph {
  color: #c0c0c0;
  letter-spacing: 1rpx;
}

.btn-area {
  padding: 48rpx;
  text-align: center;
}
.btn-submit {
  background: linear-gradient(135deg, #0a0a0a 0%, #2a2520 100%);
  color: #c9a96e;
  border: none;
  border-radius: 48rpx;
  padding: 28rpx 0;
  font-size: 30rpx;
  letter-spacing: 8rpx;
  box-shadow: 0 8rpx 32rpx rgba(10, 10, 10, 0.15);
}
.btn-submit::after {
  border: none;
}
.btn-tip {
  display: block;
  margin-top: 20rpx;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 2rpx;
}

.footer {
  padding: 32rpx 48rpx 80rpx;
  text-align: center;
}
.footer-en {
  font-size: 20rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  font-style: italic;
}
</style>
