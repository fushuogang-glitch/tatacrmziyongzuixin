<script setup lang="ts">
import { reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { Plus, Close } from '@element-plus/icons-vue';
import { API } from '../../api';

const props = defineProps<{
  // 提交方法：返回 Promise，由父组件指定（客户 or 老师）
  submitter: (body: { raw_text: string; raw_images: string[] }) => Promise<any>;
  /** 已存在的原始资料（可二次编辑） */
  initialText?: string;
  initialImages?: string[];
}>();

const emit = defineEmits<{ (e: 'submitted'): void }>();

const form = reactive({
  raw_text: props.initialText || '',
  raw_images: [...(props.initialImages || [])] as string[],
});
const submitting = ref(false);

async function handleUpload(options: any) {
  try {
    const url: any = await API.uploadImage(options.file);
    form.raw_images.push(url);
    ElMessage.success('图片上传成功');
  } catch {
    ElMessage.error('图片上传失败');
  }
}

function removeImage(idx: number) {
  form.raw_images.splice(idx, 1);
}

async function submit() {
  if (!form.raw_text.trim() && form.raw_images.length === 0) {
    ElMessage.warning('请至少填写文字或上传图片');
    return;
  }
  submitting.value = true;
  try {
    await props.submitter({
      raw_text: form.raw_text.trim(),
      raw_images: form.raw_images,
    });
    ElMessage.success('已提交·等塔才回写分析结果');
    emit('submitted');
  } catch {
    /* http 拦截器已弹错 */
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="da-form">
    <div class="da-form-title">📥 录入原始资料</div>
    <div class="da-form-tip">
      把客户/老师的真实表达、八字、出生信息、平时行为习惯、职业经历等原始材料贴这里。
      塔才（智能体）会自动回写四色性格、MBTI、八字命理、服务/带教指导方案。
    </div>

    <el-input
      v-model="form.raw_text"
      type="textarea"
      :rows="6"
      placeholder="例：女·1995-08-12 上午 10:20 出生于杭州·喜欢自由·不爱被安排·朋友多·常说话像段子·……"
    />

    <div class="da-upload-row">
      <div
        v-for="(img, idx) in form.raw_images"
        :key="idx"
        class="da-thumb"
      >
        <el-image :src="img" :preview-src-list="[img]" fit="cover" style="width:90px;height:90px;border-radius:8px;" />
        <el-button
          type="danger"
          circle
          size="small"
          class="da-thumb-del"
          @click="removeImage(idx)"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <el-upload
        :auto-upload="true"
        :show-file-list="false"
        :http-request="handleUpload"
        accept="image/*"
      >
        <div class="da-upload-btn">
          <el-icon><Plus /></el-icon>
          <span>上传图片</span>
        </div>
      </el-upload>
    </div>

    <div style="text-align:right; margin-top:12px;">
      <el-button type="primary" :loading="submitting" @click="submit">
        🚀 提交·交给塔才分析
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.da-form {
  background: linear-gradient(135deg, #f8f5ff 0%, #f3f0ff 100%);
  border: 1px solid #e9d8fd;
  border-radius: 12px;
  padding: 18px;
}
.da-form-title {
  font-size: 15px;
  font-weight: 600;
  color: #6b46c1;
  margin-bottom: 6px;
}
.da-form-tip {
  font-size: 12px;
  color: #8a7baa;
  margin-bottom: 12px;
  line-height: 1.6;
}
.da-upload-row {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.da-thumb {
  position: relative;
}
.da-thumb-del {
  position: absolute;
  top: -8px;
  right: -8px;
  padding: 4px;
  min-height: 0;
  width: 22px;
  height: 22px;
}
.da-upload-btn {
  width: 90px;
  height: 90px;
  border: 2px dashed #c4b5fd;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #7c3aed;
  font-size: 12px;
  gap: 4px;
  cursor: pointer;
  transition: all .2s;
  background: #fff;
}
.da-upload-btn:hover {
  border-color: #7c3aed;
  background: #faf7ff;
}
</style>
