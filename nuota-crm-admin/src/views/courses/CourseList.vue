<template>
  <div class="page">
    <div class="header">
      <h2>📚 课程管理</h2>
      <div>
        <el-radio-group v-model="filter.tab" style="margin-right:12px;">
          <el-radio-button value="upcoming">新课程</el-radio-button>
          <el-radio-button value="past">往期课程</el-radio-button>
        </el-radio-group>
        <el-select v-model="filter.brand" placeholder="品牌" clearable style="width:120px; margin-right:8px;">
          <el-option label="九木" value="九木" />
          <el-option label="九凤" value="九凤" />
        </el-select>
        <el-button type="primary" @click="openCreate">+ 创建课程</el-button>
      </div>
    </div>

    <el-table :data="courses" border stripe style="width:100%">
      <el-table-column prop="title" label="课程名称" min-width="200" />
      <el-table-column prop="brand" label="品牌" width="80" />
      <el-table-column prop="instructor" label="讲师" width="100" />
      <el-table-column prop="location" label="地点" width="160" />
      <el-table-column label="日期" width="200">
        <template #default="{ row }">{{ row.start_date }} ~ {{ row.end_date }}</template>
      </el-table-column>
      <el-table-column label="价格" width="160" align="right">
        <template #default="{ row }">¥{{ row.price }}<span v-if="row.member_price" style="color:#c9a96e;margin-left:4px;">/ 会员¥{{ row.member_price }}</span></template>
      </el-table-column>
      <el-table-column label="报名" width="100" align="center">
        <template #default="{ row }">
          <span style="font-weight:600;">{{ row.enrolled_count }}</span> / {{ row.max_students }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/courses/${row.id}`)">详情</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'draft'" link type="success" @click="publish(row.id)">发布</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dlg.vis" :title="dlg.isEdit ? '编辑课程' : '创建课程'" width="640px">
      <el-form :model="dlg.form" label-width="100px">
        <el-form-item label="课程名称"><el-input v-model="dlg.form.title" /></el-form-item>
        <el-form-item label="品牌">
          <el-radio-group v-model="dlg.form.brand">
            <el-radio value="九木">🌿 九木营销学院</el-radio>
            <el-radio value="九凤">🪷 九凤产品学院</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分类"><el-input v-model="dlg.form.category" placeholder="如：营销/产品/管理" /></el-form-item>
        <el-form-item label="讲师"><el-input v-model="dlg.form.instructor" /></el-form-item>
        <el-form-item label="地点"><el-input v-model="dlg.form.location" /></el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="dlg.form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="dlg.form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="上课时间">
          <el-col :span="11"><el-input v-model="dlg.form.start_time" placeholder="09:00" /></el-col>
          <el-col :span="2" style="text-align:center;">~</el-col>
          <el-col :span="11"><el-input v-model="dlg.form.end_time" placeholder="17:00" /></el-col>
        </el-form-item>
        <el-form-item label="人数上限"><el-input-number v-model="dlg.form.max_students" :min="1" :max="200" /></el-form-item>
        <el-form-item label="原价(元)"><el-input-number v-model="dlg.form.price" :min="0" :precision="2" :step="100" style="width:200px" /></el-form-item>
        <el-form-item label="会员价(元)"><el-input-number v-model="dlg.form.member_price" :min="0" :precision="2" :step="100" style="width:200px" /><span style="margin-left:8px;color:#999;font-size:12px;">专案会员适用</span></el-form-item>
        <el-form-item label="课程简介"><el-input v-model="dlg.form.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="参会准备资料"><el-input v-model="dlg.form.materials" type="textarea" :rows="2" placeholder="报名后顾问发送给学员的准备资料" /></el-form-item>
        <el-form-item label="参会信息"><el-input v-model="dlg.form.travel_info" type="textarea" :rows="2" placeholder="开课前5天发送的订票/交通/住宿信息" /></el-form-item>
        <el-form-item label="提前通知天数"><el-input-number v-model="dlg.form.notify_days" :min="1" :max="30" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg.vis = false">取消</el-button>
        <el-button type="primary" @click="saveCourse">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const courses = ref<any[]>([]);
const filter = reactive({ brand: '', tab: 'upcoming' });

async function load() {
  const params: any = { tab: filter.tab };
  if (filter.brand) params.brand = filter.brand;
  const r: any = await API.courseList(params);
  courses.value = r?.data || r || [];
}

function statusType(s: string) {
  return ({ draft: 'info', published: 'success', ongoing: 'warning', ended: '' } as any)[s] || '';
}
function statusLabel(s: string) {
  return ({ draft: '草稿', published: '已发布', ongoing: '进行中', ended: '已结束' } as any)[s] || s;
}

const dlg = reactive({
  vis: false, isEdit: false, editId: 0,
  form: {
    title: '', brand: '九木', category: '', instructor: '', location: '',
    start_date: '', end_date: '', start_time: '09:00', end_time: '17:00',
    max_students: 20, price: 0, member_price: 0, description: '', materials: '', travel_info: '',
    notify_days: 5,
  }
});

function openCreate() {
  dlg.isEdit = false;
  dlg.editId = 0;
  dlg.form = {
    title: '', brand: '九木', category: '', instructor: '', location: '',
    start_date: '', end_date: '', start_time: '09:00', end_time: '17:00',
    max_students: 20, price: 0, member_price: 0, description: '', materials: '', travel_info: '',
    notify_days: 5,
  };
  dlg.vis = true;
}

function openEdit(row: any) {
  dlg.isEdit = true;
  dlg.editId = row.id;
  dlg.form = { ...row };
  dlg.vis = true;
}

async function saveCourse() {
  try {
    if (dlg.isEdit) {
      await API.courseUpdate(dlg.editId, dlg.form);
    } else {
      await API.courseCreate(dlg.form);
    }
    ElMessage.success(dlg.isEdit ? '课程已更新' : '课程已创建');
    dlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || '操作失败'); }
}

async function publish(id: number) {
  await ElMessageBox.confirm('确认发布课程？发布后学员可在小程序报名', '发布课程');
  await API.coursePublish(id);
  ElMessage.success('课程已发布');
  load();
}

watch(() => filter.brand, load);
watch(() => filter.tab, load);
onMounted(load);
</script>

<style scoped>
.page { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
