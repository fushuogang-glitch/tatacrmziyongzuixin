<template>
  <view class="page">
    <!-- 头部 -->
    <view class="header">
      <text class="header-en">ENTERPRISE STAFF</text>
      <text class="header-cn">企 业 学 员 管 理</text>
      <view class="header-line"></view>
      <text class="header-desc">添加学员信息 · 人脸认证 · 参训管理</text>
    </view>

    <scroll-view scroll-y class="scroll">
      <!-- 统计卡 -->
      <view class="stat-card">
        <view class="stat-item">
          <text class="stat-num">{{ staffList.length }}</text>
          <text class="stat-label">学员总数</text>
        </view>
        <view class="stat-divider"></view>
        <view class="stat-item">
          <text class="stat-num">{{ faceBoundCount }}</text>
          <text class="stat-label">已认证</text>
        </view>
        <view class="stat-divider"></view>
        <view class="stat-item">
          <text class="stat-num">{{ staffList.length - faceBoundCount }}</text>
          <text class="stat-label">待认证</text>
        </view>
      </view>

      <!-- 学员列表 -->
      <view v-if="staffList.length === 0" class="empty">
        <text class="empty-icon">👥</text>
        <text class="empty-text">暂无学员</text>
        <text class="empty-sub">点击下方按钮添加企业学员</text>
      </view>

      <view v-for="s in staffList" :key="s.id" class="staff-card" @tap="viewStaff(s)">
        <view class="staff-avatar">
          <text class="avatar-text">{{ s.name?.charAt(0) || '?' }}</text>
          <view v-if="s.face_bound" class="face-badge">✓</view>
        </view>
        <view class="staff-info">
          <text class="staff-name">{{ s.name }}</text>
          <text class="staff-pos">{{ s.position || '未设置职位' }}</text>
          <text class="staff-phone">{{ s.phone || '未填手机' }}</text>
        </view>
        <view class="staff-actions">
          <view v-if="!s.face_bound" class="face-btn" @tap.stop="goFaceBind(s)">
            <text class="face-btn-text">人脸认证</text>
          </view>
          <text v-else class="face-done">已认证 ✓</text>
        </view>
      </view>

      <view style="height: 160rpx;"></view>
    </scroll-view>

    <!-- 添加按钮 -->
    <view class="fab" @tap="showAdd = true">
      <text class="fab-text">+ 添加学员</text>
    </view>

    <!-- 添加/编辑弹窗 -->
    <view v-if="showAdd" class="modal-mask" @tap="showAdd = false">
      <view class="modal" @tap.stop>
        <text class="modal-title">{{ editId ? '编辑学员' : '添加学员' }}</text>
        <view class="form-group">
          <text class="form-label">姓名 *</text>
          <input class="form-input" v-model="form.name" placeholder="请输入姓名" />
        </view>
        <view class="form-group">
          <text class="form-label">手机号</text>
          <input class="form-input" v-model="form.phone" placeholder="请输入手机号" type="number" />
        </view>
        <view class="form-group">
          <text class="form-label">职位 *</text>
          <view class="pos-tags">
            <text 
              v-for="p in positions" :key="p" 
              :class="['pos-tag', form.position === p ? 'active' : '']"
              @tap="form.position = p"
            >{{ p }}</text>
          </view>
          <input class="form-input" v-model="form.position" placeholder="或手动输入职位" />
        </view>
        <view class="form-group">
          <text class="form-label">身份证号（选填）</text>
          <input class="form-input" v-model="form.id_card" placeholder="请输入身份证号" />
        </view>
        <view class="modal-btns">
          <text class="btn-cancel" @tap="closeModal">取消</text>
          <text class="btn-confirm" @tap="submitStaff">{{ editId ? '保存' : '添加' }}</text>
        </view>
      </view>
    </view>

    <!-- 学员详情弹窗 -->
    <view v-if="showDetail" class="modal-mask" @tap="showDetail = false">
      <view class="modal detail-modal" @tap.stop>
        <view class="detail-avatar">
          <text class="detail-avatar-text">{{ currentStaff?.name?.charAt(0) || '?' }}</text>
        </view>
        <text class="detail-name">{{ currentStaff?.name }}</text>
        <text class="detail-pos">{{ currentStaff?.position || '未设置' }}</text>
        <view class="detail-rows">
          <view class="detail-row">
            <text class="detail-label">手机号</text>
            <text class="detail-value">{{ currentStaff?.phone || '未填写' }}</text>
          </view>
          <view class="detail-row">
            <text class="detail-label">人脸认证</text>
            <text :class="['detail-value', currentStaff?.face_bound ? 'green' : 'red']">
              {{ currentStaff?.face_bound ? '已认证' : '未认证' }}
            </text>
          </view>
          <view class="detail-row">
            <text class="detail-label">身份证</text>
            <text class="detail-value">{{ currentStaff?.id_card || '未填写' }}</text>
          </view>
        </view>
        <view class="modal-btns">
          <text class="btn-cancel" @tap="editStaff(currentStaff!)">编辑</text>
          <text class="btn-danger" @tap="removeStaff(currentStaff!.id)">移除</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { api } from '../../api';

interface Staff {
  id: number;
  name: string;
  phone?: string;
  position?: string;
  id_card?: string;
  face_bound: boolean;
  status: string;
}

const staffList = ref<Staff[]>([]);
const showAdd = ref(false);
const showDetail = ref(false);
const editId = ref<number | null>(null);
const currentStaff = ref<Staff | null>(null);

const positions = ['店长', '顾问', '美容师', '前台', '经理', '其他'];

const form = ref({
  name: '',
  phone: '',
  position: '',
  id_card: ''
});

const faceBoundCount = computed(() => staffList.value.filter(s => s.face_bound).length);

async function loadStaff() {
  try {
    const r: any = await api.staffList();
    if (r && Array.isArray(r)) {
      staffList.value = r;
    }
  } catch (e) {}
}

function closeModal() {
  showAdd.value = false;
  editId.value = null;
  form.value = { name: '', phone: '', position: '', id_card: '' };
}

async function submitStaff() {
  if (!form.value.name) {
    uni.showToast({ title: '请输入姓名', icon: 'none' });
    return;
  }
  if (!form.value.position) {
    uni.showToast({ title: '请选择职位', icon: 'none' });
    return;
  }
  try {
    if (editId.value) {
      await api.staffUpdate(editId.value, form.value);
      uni.showToast({ title: '保存成功' });
    } else {
      await api.staffAdd(form.value);
      uni.showToast({ title: '添加成功' });
    }
    closeModal();
    loadStaff();
  } catch (e) {
    uni.showToast({ title: '操作失败', icon: 'none' });
  }
}

function viewStaff(s: Staff) {
  currentStaff.value = s;
  showDetail.value = true;
}

function editStaff(s: Staff) {
  showDetail.value = false;
  editId.value = s.id;
  form.value = {
    name: s.name,
    phone: s.phone || '',
    position: s.position || '',
    id_card: s.id_card || ''
  };
  showAdd.value = true;
}

async function removeStaff(id: number) {
  uni.showModal({
    title: '确认移除',
    content: '确定要移除该学员吗？',
    success: async (res) => {
      if (res.confirm) {
        try {
          await api.staffDelete(id);
          uni.showToast({ title: '已移除' });
          showDetail.value = false;
          loadStaff();
        } catch (e) {
          uni.showToast({ title: '操作失败', icon: 'none' });
        }
      }
    }
  });
}

function goFaceBind(s: Staff) {
  uni.navigateTo({
    url: `/pages/staff/face-bind?id=${s.id}&name=${encodeURIComponent(s.name)}`
  });
}

onMounted(() => {
  loadStaff();
});
</script>

<style lang="scss">
.page {
  background: #fff;
  min-height: 100vh;
  position: relative;
}
.header {
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #2a2520 100%);
  padding: 80rpx 48rpx 48rpx;
  text-align: center;
  color: #fff;
}
.header-en {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 6rpx;
  margin-bottom: 16rpx;
  font-style: italic;
}
.header-cn {
  display: block;
  font-size: 36rpx;
  letter-spacing: 12rpx;
  font-weight: 500;
}
.header-line {
  width: 48rpx;
  height: 1rpx;
  background: #c9a96e;
  margin: 24rpx auto;
}
.header-desc {
  display: block;
  font-size: 22rpx;
  color: rgba(255,255,255,0.5);
  letter-spacing: 3rpx;
}

.scroll {
  flex: 1;
}

.stat-card {
  display: flex;
  margin: 32rpx 48rpx;
  background: linear-gradient(135deg, #faf6ed, #f4ecd8);
  border-radius: 24rpx;
  padding: 32rpx 0;
}
.stat-item {
  flex: 1;
  text-align: center;
}
.stat-num {
  display: block;
  font-size: 44rpx;
  color: #a88a4d;
  font-weight: 500;
  line-height: 1;
}
.stat-label {
  display: block;
  font-size: 20rpx;
  color: #555;
  margin-top: 12rpx;
  letter-spacing: 2rpx;
}
.stat-divider {
  width: 1rpx;
  background: #d4c9b0;
}

.empty {
  text-align: center;
  padding: 120rpx 48rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.empty-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
}
.empty-text {
  font-size: 28rpx;
  color: #0a0a0a;
  letter-spacing: 4rpx;
  margin-bottom: 12rpx;
}
.empty-sub {
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 2rpx;
}

.staff-card {
  display: flex;
  align-items: center;
  margin: 0 48rpx;
  padding: 28rpx 0;
  border-bottom: 1rpx solid #ebe8e2;
}
.staff-avatar {
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #0a0a0a, #2a2520);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 24rpx;
  position: relative;
}
.avatar-text {
  font-size: 32rpx;
  color: #c9a96e;
  font-weight: 500;
}
.face-badge {
  position: absolute;
  right: -4rpx;
  bottom: -4rpx;
  width: 32rpx;
  height: 32rpx;
  border-radius: 50%;
  background: #4caf50;
  color: #fff;
  font-size: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.staff-info {
  flex: 1;
}
.staff-name {
  display: block;
  font-size: 28rpx;
  color: #0a0a0a;
  font-weight: 500;
  letter-spacing: 2rpx;
  margin-bottom: 6rpx;
}
.staff-pos {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 2rpx;
  margin-bottom: 4rpx;
}
.staff-phone {
  display: block;
  font-size: 20rpx;
  color: #9a9a9a;
  letter-spacing: 1rpx;
}
.staff-actions {
  margin-left: 16rpx;
}
.face-btn {
  background: linear-gradient(135deg, #0a0a0a, #2a2520);
  border-radius: 28rpx;
  padding: 10rpx 24rpx;
}
.face-btn-text {
  font-size: 20rpx;
  color: #c9a96e;
  letter-spacing: 2rpx;
}
.face-done {
  font-size: 20rpx;
  color: #4caf50;
  letter-spacing: 1rpx;
}

.fab {
  position: fixed;
  bottom: 60rpx;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #c9a96e, #a88a4d);
  border-radius: 48rpx;
  padding: 24rpx 64rpx;
  box-shadow: 0 8rpx 32rpx rgba(201, 169, 110, 0.4);
}
.fab-text {
  font-size: 28rpx;
  color: #fff;
  letter-spacing: 4rpx;
  font-weight: 500;
}

// 弹窗
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  width: 600rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 48rpx;
}
.modal-title {
  display: block;
  font-size: 32rpx;
  font-weight: 500;
  letter-spacing: 4rpx;
  color: #0a0a0a;
  text-align: center;
  margin-bottom: 40rpx;
}
.form-group {
  margin-bottom: 28rpx;
}
.form-label {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 2rpx;
  margin-bottom: 12rpx;
}
.form-input {
  width: 100%;
  border: 1rpx solid #ebe8e2;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  font-size: 26rpx;
  color: #0a0a0a;
  box-sizing: border-box;
}
.pos-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-bottom: 16rpx;
}
.pos-tag {
  font-size: 22rpx;
  color: #555;
  border: 1rpx solid #ebe8e2;
  border-radius: 28rpx;
  padding: 8rpx 24rpx;
  letter-spacing: 2rpx;
}
.pos-tag.active {
  background: #0a0a0a;
  color: #c9a96e;
  border-color: #0a0a0a;
}
.modal-btns {
  display: flex;
  gap: 24rpx;
  margin-top: 40rpx;
}
.btn-cancel {
  flex: 1;
  text-align: center;
  padding: 20rpx;
  border: 1rpx solid #ebe8e2;
  border-radius: 12rpx;
  font-size: 26rpx;
  color: #555;
  letter-spacing: 2rpx;
}
.btn-confirm {
  flex: 1;
  text-align: center;
  padding: 20rpx;
  background: linear-gradient(135deg, #0a0a0a, #2a2520);
  border-radius: 12rpx;
  font-size: 26rpx;
  color: #c9a96e;
  letter-spacing: 2rpx;
}
.btn-danger {
  flex: 1;
  text-align: center;
  padding: 20rpx;
  background: #ff4444;
  border-radius: 12rpx;
  font-size: 26rpx;
  color: #fff;
  letter-spacing: 2rpx;
}

// 详情弹窗
.detail-modal {
  text-align: center;
}
.detail-avatar {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #0a0a0a, #2a2520);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24rpx;
}
.detail-avatar-text {
  font-size: 48rpx;
  color: #c9a96e;
  font-weight: 500;
}
.detail-name {
  display: block;
  font-size: 32rpx;
  font-weight: 500;
  letter-spacing: 4rpx;
  margin-bottom: 8rpx;
}
.detail-pos {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 3rpx;
  margin-bottom: 32rpx;
}
.detail-rows {
  text-align: left;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #ebe8e2;
}
.detail-label {
  font-size: 24rpx;
  color: #9a9a9a;
  letter-spacing: 2rpx;
}
.detail-value {
  font-size: 24rpx;
  color: #0a0a0a;
  letter-spacing: 1rpx;
}
.detail-value.green { color: #4caf50; }
.detail-value.red { color: #ff4444; }
</style>
