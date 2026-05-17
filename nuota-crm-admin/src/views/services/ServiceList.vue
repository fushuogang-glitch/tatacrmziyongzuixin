<template>
  <div class="page">
    <div class="header">
      <h2>专案服务管理</h2>
      <div class="toolbar-right">
        <!-- 分类筛选 -->
        <el-select v-model="filterCat" placeholder="全部分类" clearable style="width:140px;margin-right:12px" @change="load">
          <el-option v-for="c in cats" :key="c.val" :value="c.val" :label="c.label" />
        </el-select>
        <el-select v-model="filterBrand" placeholder="全部品牌" clearable style="width:120px;margin-right:12px" @change="load">
          <el-option value="塔塔" label="🏢 塔塔" />
          <el-option value="九木" label="🌿 九木" />
          <el-option value="九凤" label="🪷 九凤" />
        </el-select>
        <!-- 服务时长筛选 -->
        <el-select v-model="filterMode" placeholder="全部模式" clearable style="width:130px;margin-right:12px" @change="load">
          <el-option value="annual" label="1年制" />
          <el-option value="times" label="按次制" />
        </el-select>
        <!-- 单次天数筛选 -->
        <el-select v-model="filterDays" placeholder="单次天数" clearable style="width:120px;margin-right:16px" @change="load">
          <el-option v-for="d in [1,2,3,4,5]" :key="d" :value="d" :label="`${d}天`" />
        </el-select>
        <el-button type="primary" @click="openDialog()">新增服务</el-button>
      </div>
    </div>

    <el-table :data="filteredRows" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="code" label="编码" width="100" />
      <el-table-column prop="name" label="服务名称" min-width="150" />
      <el-table-column prop="brand" label="品牌" width="90">
        <template #default="{ row }">{{ row.brand || '塔塔' }}</template>
      </el-table-column>
      <el-table-column prop="category" label="分类" width="100">
        <template #default="{ row }">
          <el-tag :type="cateType(row.category)">{{ catLabel(row.category) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="服务模式" width="100">
        <template #default="{ row }">
          <el-tag :type="row.service_mode === 'annual' ? 'warning' : 'primary'" size="small">
            {{ row.service_mode === 'annual' ? '1年制' : `按次·${row.total_times || 5}次` }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="单次天数" width="90">
        <template #default="{ row }">{{ row.duration_days || 1 }}天</template>
      </el-table-column>
      <el-table-column label="单次价" width="120">
        <template #default="{ row }">¥{{ formatNum(row.price) }}</template>
      </el-table-column>
      <el-table-column label="年费套餐" width="120">
        <template #default="{ row }"><span class="gold">¥{{ formatNum(row.annual_price) }}</span></template>
      </el-table-column>
      <el-table-column prop="description" label="介绍" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '在售' : '下架' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button size="small" text @click="openDialog(row)">编辑</el-button>
          <el-button size="small" text :type="row.status === 'active' ? 'warning' : 'success'" @click="toggleService(row)">{{ row.status === 'active' ? '下架' : '上架' }}</el-button>
          <el-button size="small" text type="danger" @click="deleteService(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialog.visible" :title="dialog.id ? '编辑服务' : '新增服务'" width="600px">
      <el-form :model="dialog.form" label-width="110px">
        <el-form-item label="服务名称">
          <el-input v-model="dialog.form.name" placeholder="如：年度战略发展" />
        </el-form-item>
        <el-form-item label="编码">
          <el-input v-model="dialog.form.code" placeholder="SV-001" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="dialog.form.category" style="width:100%">
            <el-option v-for="c in cats" :key="c.val" :value="c.val" :label="c.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="品牌">
          <el-select v-model="dialog.form.brand" style="width:100%">
            <el-option value="塔塔" label="🏢 塔塔咨询" />
            <el-option value="九木" label="🌿 九木营销学院" />
            <el-option value="九凤" label="🪷 九凤产品学院" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务模式">
          <el-radio-group v-model="dialog.form.service_mode">
            <el-radio-button value="annual">1年制</el-radio-button>
            <el-radio-button value="times">按次制</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="服务次数">
          <el-input-number v-model="dialog.form.total_times" :min="1" :max="99" controls-position="right" style="width:200px" />
          <div class="form-tip">{{ dialog.form.service_mode === 'annual' ? '年度套餐包含的服务次数' : '按次制包含的服务次数' }}</div>
        </el-form-item>
        <el-form-item label="单次服务天数">
          <el-select v-model="dialog.form.duration_days" style="width:100%">
            <el-option v-for="d in [1,2,3,4,5]" :key="d" :value="d" :label="`${d}天`" />
          </el-select>
          <div class="form-tip">老师单次下店/服务的天数</div>
        </el-form-item>
        <el-form-item label="单次价(元)">
          <el-input-number v-model="dialog.form.price" :min="0" :step="1000" style="width:100%" />
        </el-form-item>
        <el-form-item label="年费价(元)">
          <el-input-number v-model="dialog.form.annual_price" :min="0" :step="1000" style="width:100%" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="dialog.form.description" type="textarea" :rows="2" placeholder="一句话服务简介" />
        </el-form-item>
        <el-form-item label="详细介绍">
          <el-input v-model="dialog.form.introduction" type="textarea" :rows="6" placeholder="产品详细介绍（支持HTML富文本，同步小程序展示）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const rows = ref<any[]>([]);
const loading = ref(false);

const filterCat = ref<string | null>(null);
const filterMode = ref<string | null>(null);
const filterDays = ref<number | null>(null);
const filterBrand = ref<string | null>(null);

const cats = [
  { val: '专案', label: '专案' },
  { val: '发展', label: '发展' },
  { val: '增长', label: '增长' },
  { val: '课程', label: '课程' },
  { val: '供应商服务', label: '供应商服务' },
];

const catColorMap: Record<string, string> = {
  '专案': 'danger',
  '发展': 'warning',
  '增长': 'success',
  '课程': 'primary',
  '供应商服务': 'info',
};

function catLabel(val: string) {
  return cats.find(c => c.val === val)?.label || val;
}
function cateType(val: string) {
  return catColorMap[val] || '';
}

const filteredRows = computed(() => {
  return rows.value.filter(r => {
    if (filterCat.value && r.category !== filterCat.value) return false;
    if (filterMode.value && r.service_mode !== filterMode.value) return false;
    if (filterDays.value && r.duration_days !== filterDays.value) return false;
    if (filterBrand.value && (r.brand || '塔塔') !== filterBrand.value) return false;
    return true;
  });
});

const dialog = reactive({
  visible: false,
  id: 0,
  form: {
    name: '', code: '', category: '发展',
    service_mode: 'annual', total_times: 5,
    duration_days: 1, price: 0, annual_price: 0, description: '', introduction: '',
  } as any,
});

async function load() {
  loading.value = true;
  try { rows.value = (await API.serviceList() as any) || []; }
  finally { loading.value = false; }
}

function openDialog(row?: any) {
  if (row) {
    dialog.id = row.id;
    dialog.form = {
      ...row,
      service_mode: row.service_mode || 'annual',
      total_times: row.total_times || 5,
      duration_days: row.duration_days || 1,
      introduction: row.introduction || '',
    };
  } else {
    dialog.id = 0;
    dialog.form = {
      name: '', code: '', category: '发展', brand: '塔塔',
      service_mode: 'annual', total_times: 5,
      duration_days: 1, price: 0, annual_price: 0, description: '', introduction: '',
    };
  }
  dialog.visible = true;
}

async function submit() {
  try {
    if (dialog.id) {
      await API.serviceUpdate(dialog.id, dialog.form);
    } else {
      await API.serviceCreate(dialog.form);
    }
    ElMessage.success('保存成功');
    dialog.visible = false;
    load();
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.msg || '保存失败';
    ElMessage.error(msg);
  }
}

function formatNum(v: any) {
  return Number(v || 0).toLocaleString();
}

async function toggleService(row: any) {
  const action = row.status === 'active' ? '下架' : '上架';
  try {
    await ElMessageBox.confirm(`确认${action}「${row.name}」？`, `${action}服务`, { type: 'warning' });
    await API.serviceToggle(row.id);
    ElMessage.success(`已${action}`);
    load();
  } catch {}
}

async function deleteService(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」？如有关联工单将自动转为下架。`, '删除服务', {
      confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'error'
    });
    await API.serviceDelete(row.id);
    ElMessage.success('已删除');
    load();
  } catch {}
}

onMounted(load);
</script>

<style scoped>
.page { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.toolbar-right { display: flex; align-items: center; }
.gold { color: #c9a96e; font-weight: 600; }
.form-tip { font-size: 12px; color: #999; margin-top: 4px; }
</style>
