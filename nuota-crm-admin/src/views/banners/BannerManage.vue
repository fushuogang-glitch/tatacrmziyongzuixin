<template>
  <div>
    <h2 style="margin-bottom:16px">广告位管理</h2>
    <div style="margin-bottom:12px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <el-select v-model="position" placeholder="全部位置" clearable size="small" style="width:180px" @change="loadBanners">
        <el-option label="小程序首页轮播" value="home_carousel" />
        <el-option label="深度服务页" value="service_page" />
        <el-option label="课程页" value="course_page" />
        <el-option label="个人中心" value="profile_page" />
      </el-select>
      <el-select v-model="displayType" placeholder="全部形式" clearable size="small" style="width:140px" @change="loadBanners">
        <el-option label="轮播Banner" value="carousel" />
        <el-option label="四宫格卡片" value="grid" />
      </el-select>
      <el-button type="primary" size="small" @click="showAdd('carousel')">+ 轮播广告</el-button>
      <el-button type="warning" size="small" @click="showAdd('grid')">+ 四宫格卡片</el-button>
    </div>

    <!-- 预览区域 -->
    <div v-if="gridGroups.length" style="margin-bottom:20px">
      <div v-for="g in gridGroups" :key="g.key" style="margin-bottom:16px">
        <div style="font-size:13px;color:#909399;margin-bottom:8px">四宫格组：{{ g.key }} · {{ posLabel[g.items[0]?.position] }}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:400px">
          <div v-for="item in g.items" :key="item.id"
               style="background:#1a1a1a;border-radius:12px;padding:20px 16px;text-align:center;position:relative">
            <div style="font-size:28px;margin-bottom:6px">{{ item.icon || '📌' }}</div>
            <div style="color:#c9a96e;font-size:14px;font-weight:bold">{{ item.title }}</div>
            <div style="color:#999;font-size:11px;margin-top:4px">{{ item.subtitle }}</div>
            <el-tag v-if="!item.is_active" type="danger" size="small"
                    style="position:absolute;top:6px;right:6px">已关闭</el-tag>
          </div>
        </div>
      </div>
    </div>

    <el-table :data="banners" v-loading="loading" stripe border size="small">
      <el-table-column prop="id" label="ID" width="50" />
      <el-table-column label="形式" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.display_type === 'grid' ? 'warning' : ''" size="small">
            {{ row.display_type === 'grid' ? '四宫格' : '轮播' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="封面/图标" width="100" align="center">
        <template #default="{ row }">
          <span v-if="row.display_type === 'grid'" style="font-size:24px">{{ row.icon || '📌' }}</span>
          <el-image v-else-if="row.image_url" :src="row.image_url" fit="cover" style="width:70px;height:35px;border-radius:4px" />
          <span v-else style="color:#ccc">无图</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="120" />
      <el-table-column label="副标题" min-width="140">
        <template #default="{ row }">
          <span style="font-size:12px;color:#606266">{{ row.subtitle || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="位置" width="120">
        <template #default="{ row }">{{ posLabel[row.position] || row.position }}</template>
      </el-table-column>
      <el-table-column label="分组" width="100">
        <template #default="{ row }">
          <span style="font-size:12px;color:#909399">{{ row.group_key || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序" width="60" align="center" />
      <el-table-column label="链接" min-width="160">
        <template #default="{ row }">
          <span style="font-size:12px;color:#909399">{{ row.link_url || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="70" align="center">
        <template #default="{ row }">
          <el-switch v-model="row.is_active" @change="toggleActive(row)" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button size="small" plain @click="showEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" plain @click="delBanner(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialog.show" :title="dialogTitle" width="520px">
      <el-form label-width="80px" size="small">
        <el-form-item label="展示形式">
          <el-radio-group v-model="dialog.form.display_type">
            <el-radio-button label="carousel">轮播Banner</el-radio-button>
            <el-radio-button label="grid">四宫格卡片</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="dialog.form.title" :placeholder="dialog.form.display_type === 'grid' ? '如：ESPA' : '广告标题'" />
        </el-form-item>
        <el-form-item v-if="dialog.form.display_type === 'grid'" label="图标">
          <el-input v-model="dialog.form.icon" placeholder="Emoji图标，如 💎 🧬 🌿 ⚡" style="width:200px" />
          <span style="font-size:24px;margin-left:12px">{{ dialog.form.icon || '📌' }}</span>
        </el-form-item>
        <el-form-item v-if="dialog.form.display_type === 'grid'" label="副标题">
          <el-input v-model="dialog.form.subtitle" placeholder="如：英国高端院线护肤" />
        </el-form-item>
        <el-form-item v-if="dialog.form.display_type === 'grid'" label="分组标识">
          <el-input v-model="dialog.form.group_key" placeholder="同组4张卡片用同一个标识，如 partners" />
          <div style="font-size:11px;color:#909399;margin-top:4px">同一组的4张卡片会显示为2×2四宫格</div>
        </el-form-item>
        <el-form-item label="位置">
          <el-select v-model="dialog.form.position" style="width:100%">
            <el-option label="小程序首页轮播" value="home_carousel" />
            <el-option label="深度服务页" value="service_page" />
            <el-option label="课程页" value="course_page" />
            <el-option label="个人中心" value="profile_page" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dialog.form.display_type !== 'grid'" label="图片URL">
          <el-input v-model="dialog.form.image_url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="跳转链接">
          <el-input v-model="dialog.form.link_url" placeholder="小程序页面路径或外链（可选）" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="dialog.form.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.show = false">取消</el-button>
        <el-button type="primary" @click="saveBanner">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/utils/http'

const posLabel = { home_carousel: '首页轮播', service_page: '深度服务页', course_page: '课程页', profile_page: '个人中心' }

const banners = ref([])
const loading = ref(false)
const position = ref('')
const displayType = ref('')

// 按group_key聚合四宫格预览
const gridGroups = computed(() => {
  const map = {}
  banners.value.filter(b => b.display_type === 'grid').forEach(b => {
    const k = b.group_key || 'default'
    if (!map[k]) map[k] = { key: k, items: [] }
    map[k].items.push(b)
  })
  return Object.values(map)
})

async function loadBanners() {
  loading.value = true
  try {
    const params = {}
    if (position.value) params.position = position.value
    if (displayType.value) params.display_type = displayType.value
    const res = await http.get('/admin/banners', { params })
    banners.value = Array.isArray(res) ? res : (res && res.data) || []
  } finally { loading.value = false }
}

const dialog = ref({ show: false, mode: 'add', form: {} })

const dialogTitle = computed(() => {
  const dt = dialog.value.form.display_type === 'grid' ? '四宫格卡片' : '轮播广告'
  return dialog.value.mode === 'add' ? `新增${dt}` : `编辑${dt}`
})

function showAdd(type) {
  dialog.value = {
    show: true, mode: 'add',
    form: {
      title: '', position: 'service_page', image_url: '', link_url: '',
      sort_order: 0, display_type: type,
      icon: '', subtitle: '', group_key: ''
    }
  }
}
function showEdit(row) {
  dialog.value = { show: true, mode: 'edit', form: { ...row } }
}

async function saveBanner() {
  const f = dialog.value.form
  if (dialog.value.mode === 'add') {
    await http.post('/admin/banners', f)
    ElMessage.success('已新增')
  } else {
    await http.put(`/admin/banners/${f.id}`, f)
    ElMessage.success('已更新')
  }
  dialog.value.show = false
  loadBanners()
}

async function toggleActive(row) {
  await http.put(`/admin/banners/${row.id}`, { is_active: row.is_active })
}

async function delBanner(row) {
  await ElMessageBox.confirm(`确定删除「${row.title}」？`, '删除', { type: 'warning' })
  await http.delete(`/admin/banners/${row.id}`)
  ElMessage.success('已删除')
  loadBanners()
}

onMounted(loadBanners)
</script>
