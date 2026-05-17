<template>
  <div class="page">
    <div class="header">
      <h2>📰 内容管理</h2>
      <div>
        <el-radio-group v-model="filter.category" style="margin-right:12px;" @change="load">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="culture">企业文化</el-radio-button>
          <el-radio-button value="news">行业动态</el-radio-button>
          <el-radio-button value="promo">会员动态</el-radio-button>
          <el-radio-button value="video">视频号</el-radio-button>
        </el-radio-group>
        <el-select v-model="filter.status" placeholder="状态" clearable style="width:100px; margin-right:8px;" @change="load">
          <el-option label="已发布" value="published" />
          <el-option label="草稿" value="draft" />
        </el-select>
        <el-button type="primary" @click="openCreate">+ 发布内容</el-button>
      </div>
    </div>

    <el-table :data="articles" border stripe style="width:100%">
      <el-table-column prop="title" label="标题" min-width="240">
        <template #default="{ row }">
          <div>{{ row.title }}</div>
          <div v-if="row.summary" style="font-size:12px;color:#999;margin-top:4px;">{{ row.summary.slice(0, 60) }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="category_label" label="分类" width="100" />
      <el-table-column prop="brand" label="品牌" width="80" />
      <el-table-column prop="author" label="作者" width="80" />
      <el-table-column label="视频" width="60" align="center">
        <template #default="{ row }">
          <span v-if="row.video_channel_url">📺</span>
        </template>
      </el-table-column>
      <el-table-column prop="view_count" label="浏览" width="70" align="center" />
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
            {{ row.status === 'published' ? '已发布' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="发布时间" width="160">
        <template #default="{ row }">{{ row.published_at ? row.published_at.slice(0, 16).replace('T', ' ') : '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'draft'" link type="success" @click="publish(row.id)">发布</el-button>
          <el-button v-if="row.status === 'published'" link type="warning" @click="unpublish(row.id)">下架</el-button>
          <el-button link type="danger" @click="del(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dlg.vis" :title="dlg.isEdit ? '编辑内容' : '发布内容'" width="720px" top="3vh">
      <el-form :model="dlg.form" label-width="110px">
        <el-form-item label="标题"><el-input v-model="dlg.form.title" /></el-form-item>
        <el-form-item label="分类">
          <el-radio-group v-model="dlg.form.category">
            <el-radio value="culture">🏢 企业文化</el-radio>
            <el-radio value="news">📰 行业动态</el-radio>
            <el-radio value="promo">🏆 会员动态</el-radio>
            <el-radio value="video">📺 视频号</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="品牌">
          <el-radio-group v-model="dlg.form.brand">
            <el-radio value="塔塔">塔塔咨询</el-radio>
            <el-radio value="九木">九木营销学院</el-radio>
            <el-radio value="九凤">九凤产品学院</el-radio>
            <el-radio value="诺塔">诺塔智控</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="摘要"><el-input v-model="dlg.form.summary" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="正文内容">
          <div style="margin-bottom:8px;">
            <el-button size="small" @click="insertTag('h2')">H2标题</el-button>
            <el-button size="small" @click="insertTag('h3')">H3标题</el-button>
            <el-button size="small" @click="insertTag('p')">段落</el-button>
            <el-button size="small" @click="insertTag('blockquote')">引用</el-button>
            <el-button size="small" @click="insertTag('strong')">加粗</el-button>
            <el-button size="small" type="primary" @click="insertImage">🖼 插入图片</el-button>
          </div>
          <el-input v-model="dlg.form.content" type="textarea" :rows="12" ref="contentRef" />
          <div v-if="dlg.form.content && dlg.form.content.includes('<')" style="margin-top:8px;padding:12px;border:1px solid #eee;border-radius:8px;max-height:300px;overflow:auto;">
            <div style="font-size:12px;color:#999;margin-bottom:8px;">↓ 预览</div>
            <div v-html="dlg.form.content" style="font-size:14px;line-height:2;"></div>
          </div>
        </el-form-item>
        <el-form-item label="封面图">
          <div style="display:flex;gap:8px;align-items:center;">
            <el-input v-model="dlg.form.cover_image" placeholder="图片URL或点击上传" style="flex:1;" />
            <el-button type="primary" @click="uploadCover">上传封面</el-button>
          </div>
          <img v-if="dlg.form.cover_image" :src="fullUrl(dlg.form.cover_image)" style="max-width:200px;max-height:120px;margin-top:8px;border-radius:8px;" />
        </el-form-item>
        <el-form-item label="视频号链接"><el-input v-model="dlg.form.video_channel_url" placeholder="视频号视频链接" /></el-form-item>
        <el-form-item label="视频URL"><el-input v-model="dlg.form.video_url" placeholder="直链视频URL（可选）" /></el-form-item>
        <el-form-item label="作者"><el-input v-model="dlg.form.author" style="width:200px" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="dlg.form.tags" placeholder="用逗号分隔，如：AI,美业,门店管理" /></el-form-item>
        <el-form-item label="排序权重"><el-input-number v-model="dlg.form.sort_order" :min="0" :max="999" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg.vis = false">取消</el-button>
        <el-button @click="save('draft')">保存草稿</el-button>
        <el-button type="primary" @click="save('published')">保存并发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import http from '../../utils/http';

const articles = ref<any[]>([]);
const filter = reactive({ category: '', status: '' });

async function load() {
  const params: any = {};
  if (filter.category) params.category = filter.category;
  if (filter.status) params.status = filter.status;
  const r: any = await API.articleList(params);
  articles.value = r?.data || r || [];
}

const dlg = reactive({
  vis: false, isEdit: false, editId: 0,
  form: {
    title: '', category: 'news', brand: '塔塔', summary: '', content: '',
    cover_image: '', video_url: '', video_channel_url: '',
    author: '', tags: '', sort_order: 0,
  }
});

function openCreate() {
  dlg.isEdit = false; dlg.editId = 0;
  dlg.form = {
    title: '', category: 'news', brand: '塔塔', summary: '', content: '',
    cover_image: '', video_url: '', video_channel_url: '',
    author: '', tags: '', sort_order: 0,
  };
  dlg.vis = true;
}

function openEdit(row: any) {
  dlg.isEdit = true; dlg.editId = row.id;
  dlg.form = { ...row };
  dlg.vis = true;
}

async function save(status: string) {
  if (!dlg.form.title) { ElMessage.warning('请输入标题'); return; }
  dlg.form.status = status;
  try {
    if (dlg.isEdit) {
      await API.articleUpdate(dlg.editId, dlg.form);
    } else {
      await API.articleCreate(dlg.form);
    }
    ElMessage.success(status === 'published' ? '已发布' : '已保存草稿');
    dlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || '操作失败'); }
}

async function publish(id: number) {
  await API.articlePublish(id);
  ElMessage.success('已发布');
  load();
}

async function unpublish(id: number) {
  await API.articleUnpublish(id);
  ElMessage.success('已下架');
  load();
}

async function del(id: number) {
  await ElMessageBox.confirm('确认删除？', '删除内容');
  await API.articleDelete(id);
  ElMessage.success('已删除');
  load();
}

// 图片上传
const BASE = import.meta.env.VITE_API_BASE || '';
function fullUrl(path: string) {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return BASE + path;
}

async function doUpload(): Promise<string | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) { resolve(null); return; }
      const form = new FormData();
      form.append('file', file);
      try {
        const r: any = await http.post('/admin/upload/image', form, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        const url = r?.data?.url || r?.url;
        if (url) { resolve(url); } else { ElMessage.error('上传失败'); resolve(null); }
      } catch (e) { ElMessage.error('上传失败'); resolve(null); }
    };
    input.click();
  });
}

async function uploadCover() {
  const url = await doUpload();
  if (url) { dlg.form.cover_image = url; ElMessage.success('封面上传成功'); }
}

async function insertImage() {
  const url = await doUpload();
  if (url) {
    const imgTag = `<img src="${fullUrl(url)}" style="max-width:100%;border-radius:8px;margin:12px 0;" />`;
    dlg.form.content = (dlg.form.content || '') + '\n' + imgTag + '\n';
  }
}

function insertTag(tag: string) {
  const map: any = {
    h2: '<h2>标题</h2>',
    h3: '<h3>小标题</h3>',
    p: '<p>段落文字</p>',
    blockquote: '<blockquote>引用文字</blockquote>',
    strong: '<strong>加粗文字</strong>',
  };
  dlg.form.content = (dlg.form.content || '') + '\n' + (map[tag] || '') + '\n';
}

onMounted(load);
</script>

<style scoped>
.page { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
</style>
