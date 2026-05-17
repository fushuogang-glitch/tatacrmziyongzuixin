<template>
  <view class="page">
    <view class="hero">
      <text class="hero-en">— ABOUT TATA —</text>
      <text class="hero-brand">TATA CONSULTING<text class="reg">®</text></text>
      <view class="hero-line"></view>
      <text class="hero-cn">塔 塔 咨 询</text>
      <text class="hero-tag">新 美 业 战 略 伙 伴</text>
    </view>

    <view class="section">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">我 们 是 谁</text>
        <text class="sec-en">Who We Are</text>
      </view>
      <text class="text">塔塔咨询 · 中国新美业战略咨询的开创者。</text>
      <text class="text">深耕中国美业 12 年，服务超 1000 家品牌门店，覆盖 28 个省市自治区。</text>
      <text class="text">以「方法论 + 老师团 + 系统化」三位一体的模式，帮助美业品牌完成从单店到连锁的战略升级。</text>
    </view>

    <view class="section">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">核 心 方 法 论</text>
        <text class="sec-en">Methodology</text>
      </view>
      <view class="method">
        <view class="m-item">
          <text class="m-num">01</text>
          <text class="m-title">三多原则</text>
          <text class="m-desc">多卖 · 多到店 · 多留客</text>
        </view>
        <view class="m-item">
          <text class="m-num">02</text>
          <text class="m-title">黄金三角</text>
          <text class="m-desc">品项 · 顾问 · 客户</text>
        </view>
        <view class="m-item">
          <text class="m-num">03</text>
          <text class="m-title">CABD 分层</text>
          <text class="m-desc">皮肤分层 12 阶定制方案</text>
        </view>
        <view class="m-item">
          <text class="m-num">04</text>
          <text class="m-title">新客 15 步</text>
          <text class="m-desc">信任度递进 · 峰终体验</text>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="sec-head">
        <view class="sec-line"></view>
        <text class="sec-title">服 务 数 据</text>
        <text class="sec-en">Data</text>
      </view>
      <view class="data-row">
        <view class="data-item">
          <text class="data-num">1000+</text>
          <text class="data-label">服务品牌</text>
        </view>
        <view class="data-item">
          <text class="data-num">28</text>
          <text class="data-label">覆盖省市</text>
        </view>
        <view class="data-item">
          <text class="data-num">12</text>
          <text class="data-label">深耕年数</text>
        </view>
      </view>
    </view>

    <view class="footer">
      <view class="footer-line"></view>
      <text class="footer-mark">— 上海嘉塔诺塔管理咨询有限公司 —</text>
      <view class="footer-line"></view>
    </view>
  </view>
</template>

<style lang="scss">
.page { background: #fff; min-height: 100vh; }
.hero {
  padding: 100rpx 48rpx 60rpx;
  text-align: center;
  background: linear-gradient(180deg, #fafaf8 0%, #fff 100%);
}
.hero-en {
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 8rpx;
  font-style: italic;
}
.hero-brand {
  display: block;
  font-size: 48rpx;
  color: #0a0a0a;
  letter-spacing: 12rpx;
  margin: 24rpx 0;
  font-weight: 500;
}
.hero-brand .reg {
  font-size: 22rpx;
  color: #c9a96e;
  vertical-align: super;
}
.hero-line {
  width: 64rpx;
  height: 2rpx;
  background: #c9a96e;
  margin: 24rpx auto;
}
.hero-cn {
  display: block;
  font-size: 36rpx;
  color: #0a0a0a;
  letter-spacing: 16rpx;
  font-weight: 500;
  margin-bottom: 16rpx;
}
.hero-tag {
  display: block;
  font-size: 24rpx;
  color: #9a9a9a;
  letter-spacing: 8rpx;
}

.section {
  padding: 60rpx 48rpx 24rpx;
}
.sec-head { display: flex; align-items: center; gap: 20rpx; margin-bottom: 32rpx; }
.sec-line { width: 48rpx; height: 1rpx; background: #c9a96e; }
.sec-title { font-size: 26rpx; letter-spacing: 12rpx; color: #0a0a0a; flex: 1; font-weight: 500; }
.sec-en { font-size: 22rpx; color: #9a9a9a; font-style: italic; }

.text {
  display: block;
  font-size: 24rpx;
  line-height: 2;
  color: #333;
  letter-spacing: 2rpx;
  margin-bottom: 12rpx;
}

.method {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
}
.m-item {
  width: calc((100% - 20rpx) / 2);
  background: linear-gradient(135deg, #faf6ed 0%, #f4ecd8 100%);
  border-radius: 20rpx;
  padding: 28rpx;
  box-sizing: border-box;
}
.m-num {
  display: block;
  font-size: 22rpx;
  color: #c9a96e;
  letter-spacing: 4rpx;
  margin-bottom: 12rpx;
  font-style: italic;
}
.m-title {
  display: block;
  font-size: 28rpx;
  color: #0a0a0a;
  letter-spacing: 4rpx;
  font-weight: 500;
  margin-bottom: 8rpx;
}
.m-desc {
  display: block;
  font-size: 22rpx;
  color: #555;
  letter-spacing: 1rpx;
  line-height: 1.6;
}

.data-row {
  display: flex;
  justify-content: space-around;
  background: linear-gradient(135deg, #0a0a0a 0%, #2a2520 100%);
  border-radius: 24rpx;
  padding: 48rpx 24rpx;
}
.data-item { text-align: center; }
.data-num {
  display: block;
  font-size: 56rpx;
  color: #c9a96e;
  font-weight: 500;
  letter-spacing: 4rpx;
  line-height: 1;
}
.data-label {
  display: block;
  font-size: 22rpx;
  color: #9a9a9a;
  letter-spacing: 4rpx;
  margin-top: 12rpx;
}

.footer {
  padding: 80rpx 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
}
.footer-line {
  width: 60rpx;
  height: 1rpx;
  background: #c9a96e;
}
.footer-mark {
  font-size: 20rpx;
  color: #c9a96e;
  letter-spacing: 4rpx;
}
</style>
