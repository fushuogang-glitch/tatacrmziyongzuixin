<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { API } from '../../api';
import DeepAnalysisView from '../../components/deep-analysis/DeepAnalysisView.vue';
import DeepAnalysisForm from '../../components/deep-analysis/DeepAnalysisForm.vue';

const props = defineProps<{ memberId: number }>();

const loading = ref(false);
const data = ref<any>(null);
const showForm = ref(false);

async function load() {
  loading.value = true;
  try {
    const res: any = await API.memberDeepAnalysis(props.memberId);
    data.value = res || null;
    // 没数据 → 默认展开录入；有数据 → 默认折叠录入（点按钮重新录入）
    showForm.value = !data.value;
  } finally {
    loading.value = false;
  }
}

const submit = (body: { raw_text: string; raw_images: string[] }) =>
  API.memberDeepAnalysisSubmit(props.memberId, body);

async function onSubmitted() {
  showForm.value = false;
  await load();
}

onMounted(load);
</script>

<template>
  <el-card v-loading="loading" style="margin-bottom: 16px;">
    <template #header>
      <div style="display:flex; align-items:center;">
        <span style="font-weight:600; font-size:16px;">🔮 会员深度分析</span>
        <span style="margin-left:8px; font-size:12px; color:#909399;">
          四色性格 · MBTI · 八字命理 · 服务接待指导方案
        </span>
        <span style="margin-left:auto;">
          <el-button
            v-if="data && !showForm"
            size="small"
            type="primary"
            plain
            @click="showForm = true"
          >📝 重新录入资料</el-button>
          <el-button
            v-if="data && showForm"
            size="small"
            @click="showForm = false"
          >取消</el-button>
        </span>
      </div>
    </template>

    <!-- 录入区 -->
    <DeepAnalysisForm
      v-if="showForm"
      :submitter="submit"
      :initial-text="data?.raw_text || ''"
      :initial-images="data?.raw_images || []"
      @submitted="onSubmitted"
      style="margin-bottom: 16px;"
    />

    <!-- 展示区 -->
    <DeepAnalysisView v-if="data" :data="data" scene="member" />

    <!-- 完全空态 -->
    <el-empty
      v-if="!data && !showForm"
      description="暂无深度分析记录"
      :image-size="80"
    >
      <el-button type="primary" @click="showForm = true">📥 录入资料</el-button>
    </el-empty>
  </el-card>
</template>
