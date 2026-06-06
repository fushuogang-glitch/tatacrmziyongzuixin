<template>
  <view class="page">
    <scroll-view scroll-y class="scroll">
      <view class="hero">
        <text class="eyebrow">DAILY THOUGHT</text>
        <text class="title">每 日 一 念</text>
        <text class="date">{{ data.date || '今日' }}</text>
      </view>

      <view class="word-card">
        <text class="word">{{ data.word || '生发' }}</text>
        <text class="meaning">{{ data.meaning || '今日宜顺势而为，先整理，再推进。' }}</text>
      </view>

      <view class="grid">
        <view class="mini-card">
          <text class="mini-label">每日黄历 · 宜</text>
          <text class="mini-text">{{ data.almanac?.good || '沟通复盘、客户回访、整理账目' }}</text>
        </view>
        <view class="mini-card dark">
          <text class="mini-label">每日黄历 · 忌</text>
          <text class="mini-text">{{ data.almanac?.avoid || '仓促承诺、情绪决策、跳过复盘' }}</text>
        </view>
      </view>

      <view class="section">
        <text class="sec-title">每 月 运 势 解 读</text>
        <text class="sec-sub">基于你填写的生辰信息生成，并同步保存到后台</text>
      </view>
      <view class="fortune-card">
        <text>{{ data.monthly_fortune || '填写生辰八字后，将生成本月经营启发。' }}</text>
      </view>

      <view class="section">
        <text class="sec-title">生 辰 八 字</text>
        <text class="sec-sub">仅用于文化娱乐与经营复盘启发</text>
      </view>
      <view class="form-card">
        <view class="field">
          <text class="label">出生日期</text>
          <picker mode="date" :value="form.birth_date" @change="onDateChange">
            <view class="picker">{{ form.birth_date || '请选择出生日期' }}</view>
          </picker>
        </view>
        <view class="field">
          <text class="label">出生时辰/时间</text>
          <input class="input" v-model="form.birth_time" placeholder="如：子时 / 23:30" placeholder-class="ph" />
        </view>
        <view class="field">
          <text class="label">八字文本</text>
          <textarea class="textarea" v-model="form.bazi_text" placeholder="如：甲子 乙丑 丙寅 丁卯，可留空" placeholder-class="ph" />
        </view>
        <button class="save-btn" :loading="saving" @tap="save">生成并保存月度解读</button>
      </view>

      <view class="profile-card" v-if="profile.mbti || profile.color_personality || profile.teacher_notes">
        <text class="profile-title">老师补充画像</text>
        <text v-if="profile.color_personality">颜色性格：{{ profile.color_personality }}</text>
        <text v-if="profile.mbti">MBTI：{{ profile.mbti }}</text>
        <text v-if="profile.teacher_notes">老师备注：{{ profile.teacher_notes }}</text>
      </view>

      <view class="disclaimer">{{ data.disclaimer || '每日一念仅作文化娱乐与经营启发参考。' }}</view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { api } from '../../api';

const data = reactive<any>({ almanac: {}, profile: {} });
const profile = reactive<any>({});
const form = reactive({
  birth_date: '',
  birth_time: '',
  bazi_text: '',
});
const saving = ref(false);

function applyProfile(p: any) {
  Object.assign(profile, p || {});
  form.birth_date = p?.birth_date || '';
  form.birth_time = p?.birth_time || '';
  form.bazi_text = p?.bazi_text || '';
}

async function load() {
  const res: any = await api.dailyThought();
  Object.assign(data, res || {});
  applyProfile(res?.profile || {});
}

function onDateChange(e: any) {
  form.birth_date = e.detail.value;
}

async function save() {
  saving.value = true;
  try {
    const p: any = await api.dailyThoughtSaveProfile({
      birth_date: form.birth_date || null,
      birth_time: form.birth_time || null,
      bazi_text: form.bazi_text || null,
    });
    applyProfile(p);
    await load();
    uni.showToast({ title: '已生成月度解读', icon: 'success' });
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style lang="scss">
.page { min-height: 100vh; background: #f7f4ee; color: #1a1a1a; }
.scroll { min-height: 100vh; }
.hero {
  padding: 80rpx 44rpx 36rpx;
  background: linear-gradient(135deg, #15120d 0%, #40301c 100%);
  color: #fff;
}
.eyebrow { display: block; color: #d8b56d; font-size: 22rpx; letter-spacing: 6rpx; }
.title { display: block; margin-top: 18rpx; font-size: 48rpx; letter-spacing: 10rpx; }
.date { display: block; margin-top: 18rpx; color: rgba(255,255,255,.68); font-size: 24rpx; }
.word-card {
  margin: -20rpx 28rpx 24rpx;
  padding: 42rpx 36rpx;
  border-radius: 28rpx;
  background: #fff;
  box-shadow: 0 12rpx 36rpx rgba(60, 45, 22, .08);
}
.word { display: block; font-size: 78rpx; color: #b58a3a; letter-spacing: 18rpx; text-align: center; }
.meaning { display: block; margin-top: 20rpx; font-size: 28rpx; line-height: 1.75; color: #5f5548; text-align: center; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18rpx; padding: 0 28rpx; }
.mini-card { background: #fff; border-radius: 22rpx; padding: 28rpx; min-height: 150rpx; }
.mini-card.dark { background: #24211c; color: #fff; }
.mini-label { display: block; color: #b58a3a; font-size: 22rpx; margin-bottom: 14rpx; }
.mini-text { display: block; font-size: 28rpx; line-height: 1.6; }
.section { padding: 34rpx 32rpx 16rpx; }
.sec-title { display: block; font-size: 28rpx; letter-spacing: 8rpx; font-weight: 600; }
.sec-sub { display: block; margin-top: 8rpx; font-size: 22rpx; color: #9a8d78; }
.fortune-card, .form-card, .profile-card {
  margin: 0 28rpx 24rpx;
  padding: 30rpx;
  border-radius: 24rpx;
  background: #fff;
  font-size: 28rpx;
  line-height: 1.75;
}
.field { margin-bottom: 24rpx; }
.label { display: block; font-size: 24rpx; color: #8a7b66; margin-bottom: 10rpx; }
.picker, .input, .textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 82rpx;
  padding: 22rpx;
  border-radius: 16rpx;
  background: #f8f5ef;
  font-size: 28rpx;
}
.textarea { height: 150rpx; }
.ph { color: #c5b8a6; }
.save-btn {
  margin-top: 10rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 44rpx;
  background: #1a1a1a;
  color: #d8b56d;
  font-size: 28rpx;
  letter-spacing: 4rpx;
}
.profile-title { display: block; color: #b58a3a; font-weight: 600; margin-bottom: 12rpx; }
.profile-card text { display: block; margin-bottom: 8rpx; }
.disclaimer { padding: 8rpx 36rpx 48rpx; color: #a59a88; font-size: 22rpx; line-height: 1.6; text-align: center; }
</style>
