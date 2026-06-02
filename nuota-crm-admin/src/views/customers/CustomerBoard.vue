<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Search, Refresh, OfficeBuilding, Location, User, Shop, Tickets,
  Plus, Lock, Unlock, Bell, Phone, Edit,
} from '@element-plus/icons-vue';
import { API } from '../../api';
import { useUserStore } from '../../store/user';

const router = useRouter();
const userStore = useUserStore();
const isAdmin = computed(() => userStore.role !== 'consultant');

const loading = ref(false);
const rows = ref<any[]>([]);
const grouped = ref<any[]>([]);
const total = ref(0);

const stats = ref<any>({ total_customers: 0, total_cities: 0, total_stores: 0, active_customers: 0 });
const filters = ref<any>({ cities: [], districts: [], store_types: [], consultants: [] });
const pendingCount = ref(0);

const view = ref<'consultant' | 'city' | 'none'>('consultant');

const query = reactive({
  q: '', city: '', district: '', store_type: '', consultant_id: '' as any,
});

const STORE_TYPES = ['生美', '双美', '医美', '连锁', '单店'];

function typeTag(t: string) {
  const map: Record<string, string> = {
    '直营': 'success', '加盟': 'warning', '单店': 'info',
    '连锁': 'primary', '生美': 'success', '双美': 'warning', '医美': 'danger',
  };
  return map[t] || 'info';
}

async function loadAux() {
  try { filters.value = (await API.customerFilters()) || filters.value; } catch {}
  try { stats.value = (await API.customerStats()) || stats.value; } catch {}
  try {
    const p: any = await API.phoneGrantPending();
    pendingCount.value = (p?.items || []).length;
  } catch {}
}

async function load() {
  loading.value = true;
  try {
    const params: any = { group_by: view.value };
    if (query.q) params.q = query.q;
    if (query.city) params.city = query.city;
    if (query.district) params.district = query.district;
    if (query.store_type) params.store_type = query.store_type;
    if (query.consultant_id) params.consultant_id = query.consultant_id;
    const d: any = await API.customerList(params);
    rows.value = d.items || [];
    grouped.value = d.grouped || [];
    total.value = d.total || 0;
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.message || '加载失败');
  } finally { loading.value = false; }
}

function doSearch() { load(); }
function reset() {
  query.q = ''; query.city = ''; query.district = '';
  query.store_type = ''; query.consultant_id = '';
  load();
}
function openDetail(id: number) { router.push(`/members/${id}`); }
function switchView(v: any) { view.value = v; load(); }

/* ── 电话申请 ── */
async function applyPhone(c: any) {
  try {
    const { value } = await ElMessageBox.prompt('请填写查看该客户电话的原因（如：下店执案需联系）', '申请查看电话', {
      confirmButtonText: '提交申请', cancelButtonText: '取消', inputType: 'textarea',
    });
    const r: any = await API.phoneGrantApply({ member_id: c.id, reason: value || '' });
    ElMessage.success(r?.msg || '申请已提交');
  } catch {}
}

/* ── 新增/编辑 ── */
const dlgVisible = ref(false);
const editing = ref(false);
const form = reactive<any>({
  id: null, name: '', phone: '', enterprise_name: '', address: '',
  city: '', district: '', store_type: '', store_count: 1,
  cooperation: '', consultant_id: '' as any, member_type: 'trial', status: 'active',
});
function resetForm() {
  Object.assign(form, {
    id: null, name: '', phone: '', enterprise_name: '', address: '',
    city: '', district: '', store_type: '', store_count: 1,
    cooperation: '', consultant_id: '', member_type: 'trial', status: 'active',
  });
}
function openCreate() { resetForm(); editing.value = false; dlgVisible.value = true; }
function openEdit(c: any) {
  resetForm();
  Object.assign(form, {
    id: c.id, name: c.name, phone: c.phone_masked ? '' : c.phone,
    enterprise_name: c.enterprise_name, address: c.address, city: c.city,
    district: c.district, store_type: c.store_type, store_count: c.store_count,
    cooperation: c.cooperation, consultant_id: c.consultant_id || '',
    member_type: c.member_type || 'trial', status: c.status || 'active',
  });
  editing.value = true; dlgVisible.value = true;
}
async function submitForm() {
  if (!form.name) return ElMessage.warning('请填写客户姓名');
  const body: any = { ...form };
  if (!body.consultant_id) delete body.consultant_id;
  try {
    if (editing.value && form.id) {
      if (!body.phone) delete body.phone; // 编辑时电话被打码则不覆盖
      await API.customerUpdate(form.id, body);
      ElMessage.success('已保存');
    } else {
      if (!body.phone) return ElMessage.warning('请填写电话');
      await API.customerCreate(body);
      ElMessage.success('客户已创建');
    }
    dlgVisible.value = false;
    loadAux(); load();
  } catch (e: any) {
    ElMessage.error(e?.detail || e?.message || '保存失败');
  }
}

/* ── 审批中心 ── */
const grantVisible = ref(false);
const grantRows = ref<any[]>([]);
async function openGrants() {
  grantVisible.value = true;
  try { grantRows.value = ((await API.phoneGrantPending()) as any)?.items || []; }
  catch { grantRows.value = []; }
}
async function reviewGrant(g: any, approve: boolean) {
  try {
    await API.phoneGrantReview({ grant_id: g.id, approve });
    ElMessage.success(approve ? '已授权（7天有效）' : '已拒绝');
    grantRows.value = grantRows.value.filter((x) => x.id !== g.id);
    pendingCount.value = grantRows.value.length;
    load();
  } catch (e: any) { ElMessage.error(e?.detail || '操作失败'); }
}

onMounted(() => { loadAux(); load(); });
</script>

<template>
  <div class="cb">
    <!-- 顶部汇总 -->
    <div class="stat-row">
      <div class="stat-card s1"><el-icon class="ic"><User /></el-icon><div><div class="num">{{ stats.total_customers }}</div><div class="lbl">客户总数</div></div></div>
      <div class="stat-card s2"><el-icon class="ic"><Location /></el-icon><div><div class="num">{{ stats.total_cities }}</div><div class="lbl">覆盖城市</div></div></div>
      <div class="stat-card s3"><el-icon class="ic"><Shop /></el-icon><div><div class="num">{{ stats.total_stores }}</div><div class="lbl">门店总数</div></div></div>
      <div class="stat-card s4"><el-icon class="ic"><Tickets /></el-icon><div><div class="num">{{ stats.active_customers }}</div><div class="lbl">活跃客户</div></div></div>
    </div>

    <!-- 工具条 -->
    <div class="toolbar">
      <div class="seg">
        <button :class="{ on: view==='consultant' }" @click="switchView('consultant')">按销售归属</button>
        <button :class="{ on: view==='city' }" @click="switchView('city')">按地区</button>
        <button :class="{ on: view==='none' }" @click="switchView('none')">全部客户</button>
      </div>
      <div class="grow"></div>
      <el-badge :value="pendingCount" :hidden="pendingCount===0" class="bell-badge">
        <el-button :icon="Bell" round @click="openGrants">电话授权审批</el-button>
      </el-badge>
      <el-button v-if="isAdmin" type="primary" :icon="Plus" round @click="openCreate">新增客户</el-button>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <el-input v-model="query.q" placeholder="搜索 客户/门店/电话/地址" clearable style="width:220px" :prefix-icon="Search" @keyup.enter="doSearch" @clear="doSearch" />
      <el-select v-model="query.city" placeholder="城市" clearable style="width:120px" @change="doSearch"><el-option v-for="c in filters.cities" :key="c" :label="c" :value="c" /></el-select>
      <el-select v-model="query.district" placeholder="区域" clearable style="width:120px" @change="doSearch"><el-option v-for="d in filters.districts" :key="d" :label="d" :value="d" /></el-select>
      <el-select v-model="query.store_type" placeholder="门店性质" clearable style="width:120px" @change="doSearch"><el-option v-for="t in filters.store_types" :key="t" :label="t" :value="t" /></el-select>
      <el-select v-model="query.consultant_id" placeholder="销售归属" clearable style="width:130px" @change="doSearch"><el-option v-for="c in filters.consultants" :key="c.id" :label="c.name" :value="c.id" /></el-select>
      <el-button :icon="Search" type="primary" plain @click="doSearch">查询</el-button>
      <el-button :icon="Refresh" @click="reset">重置</el-button>
      <div class="count">共 {{ total }} 个客户</div>
    </div>

    <div v-loading="loading">
      <!-- 分组视图 -->
      <template v-if="view !== 'none' && grouped.length">
        <div v-for="g in grouped" :key="g.group" class="group-block">
          <div class="group-head">
            <span class="g-dot"></span>
            <span class="g-name">{{ g.group }}</span>
            <span class="g-cnt">{{ g.count }}</span>
          </div>
          <div class="card-grid">
            <div v-for="c in g.items" :key="c.id" class="cust-card" @click="openDetail(c.id)">
              <div class="card-head">
                <div class="store-name"><el-icon><OfficeBuilding /></el-icon><span>{{ c.enterprise_name || c.name }}</span></div>
                <el-tag :type="typeTag(c.store_type)" size="small" effect="light" round>{{ c.store_type || '未分类' }}</el-tag>
              </div>
              <div class="card-body">
                <div class="row">
                  <span class="k">客户</span>
                  <span class="v">{{ c.name }}</span>
                </div>
                <div class="row">
                  <span class="k">电话</span>
                  <span class="v phone">
                    <el-icon><Phone /></el-icon>{{ c.phone }}
                    <el-tag v-if="c.phone_masked" size="small" type="info" effect="plain" class="lock-tag" @click.stop="applyPhone(c)">
                      <el-icon><Lock /></el-icon> 申请查看
                    </el-tag>
                    <el-icon v-else class="ok-ic"><Unlock /></el-icon>
                  </span>
                </div>
                <div class="row"><span class="k">地址</span><span class="v">{{ [c.city, c.district].filter(Boolean).join(' ') }} {{ c.address }}</span></div>
                <div class="row"><span class="k">合作内容</span><span class="v coop">{{ c.cooperation || '—' }}</span></div>
              </div>
              <div class="card-foot">
                <div class="metric"><span class="m-num">{{ c.service_count }}</span><span class="m-lbl">服务次数</span></div>
                <div class="metric"><span class="m-num">{{ c.store_count }}</span><span class="m-lbl">门店数</span></div>
                <div class="sales"><el-icon><User /></el-icon><span>{{ c.consultant_name || '未分配' }}</span></div>
                <el-icon v-if="isAdmin" class="edit-ic" @click.stop="openEdit(c)"><Edit /></el-icon>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 全部视图 -->
      <div v-else class="card-grid">
        <div v-for="c in rows" :key="c.id" class="cust-card" @click="openDetail(c.id)">
          <div class="card-head">
            <div class="store-name"><el-icon><OfficeBuilding /></el-icon><span>{{ c.enterprise_name || c.name }}</span></div>
            <el-tag :type="typeTag(c.store_type)" size="small" effect="light" round>{{ c.store_type || '未分类' }}</el-tag>
          </div>
          <div class="card-body">
            <div class="row"><span class="k">客户</span><span class="v">{{ c.name }}</span></div>
            <div class="row">
              <span class="k">电话</span>
              <span class="v phone">
                <el-icon><Phone /></el-icon>{{ c.phone }}
                <el-tag v-if="c.phone_masked" size="small" type="info" effect="plain" class="lock-tag" @click.stop="applyPhone(c)"><el-icon><Lock /></el-icon> 申请查看</el-tag>
                <el-icon v-else class="ok-ic"><Unlock /></el-icon>
              </span>
            </div>
            <div class="row"><span class="k">地址</span><span class="v">{{ [c.city, c.district].filter(Boolean).join(' ') }} {{ c.address }}</span></div>
            <div class="row"><span class="k">合作内容</span><span class="v coop">{{ c.cooperation || '—' }}</span></div>
          </div>
          <div class="card-foot">
            <div class="metric"><span class="m-num">{{ c.service_count }}</span><span class="m-lbl">服务次数</span></div>
            <div class="metric"><span class="m-num">{{ c.store_count }}</span><span class="m-lbl">门店数</span></div>
            <div class="sales"><el-icon><User /></el-icon><span>{{ c.consultant_name || '未分配' }}</span></div>
            <el-icon v-if="isAdmin" class="edit-ic" @click.stop="openEdit(c)"><Edit /></el-icon>
          </div>
        </div>
        <el-empty v-if="!loading && rows.length === 0" description="暂无客户数据" style="grid-column:1/-1" />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dlgVisible" :title="editing ? '编辑客户' : '新增客户'" width="560px" class="cust-dlg">
      <el-form :model="form" label-width="84px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="客户姓名" required><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="电话"><el-input v-model="form.phone" :placeholder="editing ? '留空则不修改' : '必填'" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="门店名称"><el-input v-model="form.enterprise_name" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="城市"><el-input v-model="form.city" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="区域"><el-input v-model="form.district" placeholder="区/县" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="门店数"><el-input-number v-model="form.store_count" :min="0" :max="999" controls-position="right" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="详细地址"><el-input v-model="form.address" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="门店性质"><el-select v-model="form.store_type" placeholder="选择" clearable style="width:100%"><el-option v-for="t in STORE_TYPES" :key="t" :label="t" :value="t" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="销售归属"><el-select v-model="form.consultant_id" placeholder="选择老师" clearable style="width:100%"><el-option v-for="c in filters.consultants" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="合作内容"><el-input v-model="form.cooperation" type="textarea" :rows="3" placeholder="如：年费咨询·9神器·下店执案12次" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgVisible=false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 授权审批 -->
    <el-dialog v-model="grantVisible" title="电话授权审批" width="640px">
      <el-table :data="grantRows" size="small" empty-text="暂无待审批申请">
        <el-table-column label="申请老师" prop="applicant_name" width="100" />
        <el-table-column label="客户/门店" min-width="160">
          <template #default="{ row }">{{ row.member_name }}<span v-if="row.enterprise_name" style="color:#9ca3af"> · {{ row.enterprise_name }}</span></template>
        </el-table-column>
        <el-table-column label="原因" prop="reason" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="reviewGrant(row, true)">授权7天</el-button>
            <el-button size="small" type="danger" plain @click="reviewGrant(row, false)">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
.cb { padding: 4px 2px; --np: #7c3aed; }

/* 汇总卡 */
.stat-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 16px; }
.stat-card { display: flex; align-items: center; gap: 14px; padding: 18px 20px; border-radius: 14px; color: #fff; box-shadow: 0 6px 18px rgba(0,0,0,.06); }
.stat-card .ic { font-size: 30px; opacity: .92; }
.stat-card .num { font-size: 26px; font-weight: 700; line-height: 1.1; }
.stat-card .lbl { font-size: 13px; opacity: .9; margin-top: 2px; }
.s1 { background: linear-gradient(135deg,#7c3aed,#a855f7); }
.s2 { background: linear-gradient(135deg,#6366f1,#818cf8); }
.s3 { background: linear-gradient(135deg,#0ea5e9,#38bdf8); }
.s4 { background: linear-gradient(135deg,#8b5cf6,#c084fc); }

/* 工具条 */
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.toolbar .grow { flex: 1; }
.seg { display: inline-flex; background: #f5f3ff; border-radius: 10px; padding: 4px; }
.seg button { border: 0; background: transparent; padding: 7px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; color: #6b7280; transition: all .2s; }
.seg button.on { background: #fff; color: var(--np); font-weight: 600; box-shadow: 0 2px 8px rgba(124,58,237,.18); }

.filter-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 18px; }
.filter-bar .count { margin-left: auto; color: #9ca3af; font-size: 13px; }

/* 分组 */
.group-block { margin-bottom: 22px; }
.group-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.group-head .g-dot { width: 8px; height: 18px; border-radius: 4px; background: linear-gradient(180deg,#a855f7,#7c3aed); }
.group-head .g-name { font-size: 15px; font-weight: 700; color: #1f2937; }
.group-head .g-cnt { background: #f5f3ff; color: var(--np); font-size: 12px; padding: 1px 9px; border-radius: 10px; font-weight: 600; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px,1fr)); gap: 14px; min-height: 80px; }

.cust-card { position: relative; background: #fff; border: 1px solid #f0eefb; border-radius: 14px; padding: 16px 18px; cursor: pointer; transition: all .22s; display: flex; flex-direction: column; }
.cust-card::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; border-radius:14px 0 0 14px; background: linear-gradient(180deg,#a855f7,#7c3aed); opacity: 0; transition: opacity .22s; }
.cust-card:hover { box-shadow: 0 10px 30px rgba(124,58,237,.16); border-color: #ddd6fe; transform: translateY(-3px); }
.cust-card:hover::before { opacity: 1; }

.card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 12px; }
.store-name { display: flex; align-items: center; gap: 6px; font-size: 16px; font-weight: 700; color: #1f2937; }
.store-name .el-icon { color: var(--np); }

.card-body { flex: 1; }
.card-body .row { display: flex; font-size: 13px; line-height: 2; }
.card-body .k { width: 62px; flex-shrink: 0; color: #b0b3bb; }
.card-body .v { color: #374151; flex: 1; }
.card-body .v.coop { color: #6d28d9; }
.card-body .v.phone { display: inline-flex; align-items: center; gap: 5px; }
.card-body .v.phone .el-icon { color: #9ca3af; }
.lock-tag { cursor: pointer; margin-left: 4px; }
.lock-tag :deep(.el-icon) { vertical-align: -1px; }
.ok-ic { color: #10b981; }

.card-foot { display: flex; align-items: center; gap: 16px; margin-top: 12px; padding-top: 12px; border-top: 1px dashed #f0eefb; }
.metric { display: flex; flex-direction: column; align-items: center; }
.metric .m-num { font-size: 18px; font-weight: 700; color: var(--np); }
.metric .m-lbl { font-size: 11px; color: #b0b3bb; }
.sales { margin-left: auto; display: flex; align-items: center; gap: 4px; font-size: 12px; color: #6b7280; background: #f5f3ff; padding: 4px 10px; border-radius: 20px; }
.sales .el-icon { color: var(--np); }
.edit-ic { color: #c4b5fd; cursor: pointer; padding: 4px; }
.edit-ic:hover { color: var(--np); }
</style>
