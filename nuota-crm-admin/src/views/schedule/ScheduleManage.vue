<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const user = useUserStore();
const isConsultant = user.role === 'consultant';

const consultants = ref<any[]>([]);
const schedules = ref<any[]>([]);
const loading = ref(false);

const query = reactive({ consultant_id: null as number | null, year: new Date().getFullYear(), month: new Date().getMonth() + 1 });

// 新增对话框
const dialog = reactive({
  visible: false,
  form: {
    consultant_id: null as number | null,
    assistant_id: null as number | null,
    member_id: null as number | null,
    service_id: null as number | null,
    dates: [] as string[],
    city: '',
    schedule_type: 'available',
    title: '',
    remark: '',
    order_id: null as number | null,
  }
});

// 月份切换
const months = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}月`, value: i + 1 }));
const years = Array.from({ length: 3 }, (_, i) => new Date().getFullYear() + i - 1);

async function load() {
  loading.value = true;
  try {
    const params: any = { year: query.year, month: query.month };
    if (query.consultant_id) params.consultant_id = query.consultant_id;
    schedules.value = (await API.scheduleList(params) as any) || [];
  } finally {
    loading.value = false;
  }
}

async function loadConsultants() {
  const d: any = await API.consultantList();
  consultants.value = (d.items || d || []).filter((c: any) => c.status !== 'inactive');
}

// 工单列表（用于排期关联）
const orders = ref<any[]>([]);
async function loadOrders() {
  try {
    orders.value = (await API.serviceOrderList({ }) as any) || [];
  } catch (_) { orders.value = []; }
}

const members = ref<any[]>([]);
async function loadMembers() {
  try {
    const r: any = await API.memberList({});
    members.value = r?.items || r || [];
  } catch (_) { members.value = []; }
}

const services = ref<any[]>([]);
async function loadServices() {
  try {
    services.value = (await API.serviceList() as any) || [];
  } catch (_) { services.value = []; }
}

// 按老师分组展示
const grouped = computed(() => {
  const map: Record<string, any[]> = {};
  for (const s of schedules.value) {
    const key = s.consultant_name || `老师#${s.consultant_id}`;
    if (!map[key]) map[key] = [];
    map[key].push(s);
  }
  return Object.entries(map).map(([name, items]) => ({ name, items }));
});

// 日历格子（当月所有日期）
const calDays = computed(() => {
  const days = [];
  const y = query.year, m = query.month;
  const total = new Date(y, m, 0).getDate();
  for (let d = 1; d <= total; d++) {
    const ds = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    days.push(ds);
  }
  return days;
});

// 某天某老师的排期
function getSchedule(consultantName: string, dateStr: string) {
  return schedules.value.find(s =>
    (s.consultant_name || `老师#${s.consultant_id}`) === consultantName &&
    s.schedule_date === dateStr
  );
}

function openAdd() {
  dialog.form = {
    consultant_id: isConsultant ? user.consultantId : query.consultant_id,
    assistant_id: null,
    member_id: null,
    service_id: null,
    dates: [],
    city: '',
    schedule_type: 'available',
    title: '',
    remark: '',
    order_id: null,
  };
  loadOrders();
  loadMembers();
  loadServices();
  dialog.visible = true;
}

async function submit() {
  if (!dialog.form.consultant_id) { ElMessage.warning('请选择老师'); return; }
  if (!dialog.form.dates.length) { ElMessage.warning('请选择日期（可多选）'); return; }
  await API.scheduleBatchCreate({
    consultant_id: dialog.form.consultant_id,
    assistant_id: dialog.form.assistant_id || undefined,
    member_id: dialog.form.member_id || undefined,
    service_id: dialog.form.service_id || undefined,
    dates: dialog.form.dates,
    city: dialog.form.city,
    schedule_type: dialog.form.schedule_type,
    title: dialog.form.title,
    remark: dialog.form.remark,
    order_id: dialog.form.order_id || undefined,
  });
  const msg = dialog.form.schedule_type === 'busy' && !dialog.form.order_id
    ? `已录入 ${dialog.form.dates.length} 天排期，工单已自动创建`
    : `已录入 ${dialog.form.dates.length} 天排期`;
  ElMessage.success(msg);
  dialog.visible = false;
  load();
}

async function deleteSchedule(id: number) {
  await ElMessageBox.confirm('确认删除这条排期？', '提示', { type: 'warning' });
  await API.scheduleDelete(id);
  ElMessage.success('已删除');
  load();
}

function typeLabel(t: string, orderId?: number) {
  if (t === 'busy' && orderId) return '执案';
  return { available: '可约', busy: '忙碌', leave: '休假' }[t] || t;
}
function typeColor(t: string, orderId?: number) {
  if (t === 'busy' && orderId) return '#409eff'; // 执案蓝
  return { available: '#67c23a', busy: '#f56c6c', leave: '#909399' }[t] || '#409eff';
}

function prevMonth() {
  if (query.month === 1) { query.year--; query.month = 12; }
  else query.month--;
  load();
}
function nextMonth() {
  if (query.month === 12) { query.year++; query.month = 1; }
  else query.month++;
  load();
}

onMounted(() => { loadConsultants(); load(); });
</script>

<template>
  <div>
    <!-- 顶部工具栏 -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
      <div style="font-size:20px; font-weight:700;">📅 老师排期管理</div>
      <el-button type="primary" @click="openAdd">+ 新增排期</el-button>
    </div>

    <!-- 月份切换 + 筛选 -->
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px; flex-wrap:wrap;">
      <el-button @click="prevMonth">‹ 上月</el-button>
      <span style="font-size:16px; font-weight:600; min-width:90px; text-align:center;">
        {{ query.year }}年{{ query.month }}月
      </span>
      <el-button @click="nextMonth">下月 ›</el-button>
      <el-divider direction="vertical" />
      <el-select v-model="query.consultant_id" placeholder="筛选老师" clearable style="width:140px;" @change="load">
        <el-option v-for="c in consultants" :key="c.id" :value="c.id" :label="c.name" />
      </el-select>
    </div>

    <!-- 日历式排期表 -->
    <el-card v-loading="loading">
      <div v-if="!schedules.length && !loading" style="text-align:center; padding:40px; color:#909399;">
        本月暂无排期，点击「新增排期」添加
      </div>

      <div v-for="g in grouped" :key="g.name" style="margin-bottom:24px;">
        <div style="font-size:15px; font-weight:600; color:#303133; margin-bottom:10px; padding-left:4px;">
          👤 {{ g.name }}
          <span style="font-size:12px; color:#909399; margin-left:8px;">共 {{ g.items.length }} 天</span>
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:6px;">
          <div v-for="s in g.items" :key="s.id"
            style="border-radius:6px; padding:6px 10px; font-size:13px; cursor:default; position:relative;"
            :style="{ background: typeColor(s.schedule_type, s.order_id) + '18', border: `1px solid ${typeColor(s.schedule_type, s.order_id)}` }">
            <div style="font-weight:600;" :style="{ color: typeColor(s.schedule_type, s.order_id) }">
              {{ s.schedule_date }}
            </div>
            <div style="font-size:11px; color:#606266;">
              <el-tag :color="typeColor(s.schedule_type, s.order_id)" style="color:#fff; border:none;" size="small">
                {{ typeLabel(s.schedule_type, s.order_id) }}
              </el-tag>
              {{ s.city || '' }} {{ s.title || '' }}
              <el-tag v-if="s.order_id" size="small" type="warning" style="margin-left:4px;">工单#{{ s.order_id }}</el-tag>
            </div>
            <el-button v-if="!isConsultant || s.consultant_id === user.consultantId" link size="small" type="danger"
              style="position:absolute; top:2px; right:2px; font-size:11px;"
              @click="deleteSchedule(s.id)">✕</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="dialog.visible" title="新增排期" width="580px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="主案老师" required>
          <el-select v-model="dialog.form.consultant_id" style="width:100%" placeholder="选择老师" :disabled="isConsultant">
            <el-option v-for="c in consultants" :key="c.id" :value="c.id" :label="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="助理老师">
          <el-select v-model="dialog.form.assistant_id" style="width:100%" clearable placeholder="可不选">
            <el-option v-for="c in consultants.filter((c: any) => c.id !== dialog.form.consultant_id)" :key="c.id" :value="c.id" :label="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="排期日期" required>
          <el-date-picker
            v-model="dialog.form.dates"
            type="dates"
            value-format="YYYY-MM-DD"
            placeholder="可多选日期"
            style="width:100%"
          />
          <div style="font-size:12px;color:#909399;margin-top:4px">支持多选，按住 Ctrl/Command 点击多个日期</div>
        </el-form-item>
        <el-form-item label="排期类型">
          <el-radio-group v-model="dialog.form.schedule_type">
            <el-radio value="available">✅ 可约</el-radio>
            <el-radio value="busy">🔴 执案/出差</el-radio>
            <el-radio value="leave">⚪ 休假</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 执案排期时显示额外字段 -->
        <template v-if="dialog.form.schedule_type === 'busy'">
          <el-divider content-position="left">📋 执案信息（自动生成工单）</el-divider>
          <el-form-item label="客户/会员">
            <el-select v-model="dialog.form.member_id" style="width:100%" filterable clearable placeholder="选择客户">
              <el-option v-for="m in members" :key="m.id" :value="m.id" :label="`${m.name} · ${m.enterprise_name || m.phone || ''}`" />
            </el-select>
          </el-form-item>
          <el-form-item label="服务项目">
            <el-select v-model="dialog.form.service_id" style="width:100%" clearable placeholder="选择服务">
              <el-option v-for="s in services" :key="s.id" :value="s.id" :label="`${s.name} · ${s.category || ''}`" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联工单">
            <el-select v-model="dialog.form.order_id" style="width:100%" clearable placeholder="不选则自动新建工单">
              <el-option v-for="o in orders.filter((o: any) => o.status !== 'completed' && o.status !== 'cancelled')" :key="o.id" :value="o.id" :label="`${o.order_no} · ${o.store_name || ''}`" />
            </el-select>
            <div style="font-size:12px;color:#e6a23c;margin-top:4px">✨ 不选工单 = 自动创建新工单，排期即触发工单流程</div>
          </el-form-item>
        </template>

        <el-form-item label="城市/地点">
          <el-input v-model="dialog.form.city" placeholder="如：武汉、南京、扬中" />
        </el-form-item>
        <el-form-item label="标题/门店">
          <el-input v-model="dialog.form.title" placeholder="如：木子家门店、一二一门店" />
        </el-form-item>
        <el-form-item label="详细备注">
          <el-input v-model="dialog.form.remark" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">
          {{ dialog.form.schedule_type === 'busy' && !dialog.form.order_id ? '保存排期 + 自动创建工单' : '保存排期' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
