<template>
  <div class="promo-page">
    <h2 style="margin-bottom:16px">晋级管理</h2>
    <el-tabs v-model="tab">
      <!-- Tab 1: 晋级进度 -->
      <el-tab-pane label="晋级进度" name="progress">
        <div style="margin-bottom:12px;display:flex;align-items:center;gap:12px">
          <el-date-picker v-model="progressYear" type="year" value-format="YYYY" format="YYYY年" size="small" style="width:120px" @change="loadProgress" />
          <el-select v-model="branchFilter" placeholder="全部分公司" clearable size="small" style="width:200px" @change="loadProgress">
            <el-option v-for="b in branches" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
          <el-button type="primary" size="small" @click="loadProgress" :loading="loadingProgress">刷新</el-button>
        </div>
        <el-table :data="filteredProgressList" v-loading="loadingProgress" stripe border size="small">
          <el-table-column prop="name" label="老师" width="90" />
          <el-table-column label="分公司" width="120">
            <template #default="{ row }">
              {{ (branches.find(b => b.id === row.branch_id) || {}).name || '—' }}
            </template>
          </el-table-column>
          <el-table-column prop="level_name" label="当前级别" width="100" />
          <el-table-column prop="next_level_name" label="下一级" width="100" />
          <el-table-column label="年度销售" width="160">
            <template #default="{ row }">
              <template v-if="row.progress">
                <div style="display:flex;align-items:center;gap:4px">
                  <el-tag :type="row.progress.sales.met ? 'success' : 'danger'" size="small" round>
                    ¥{{ fmtW(row.progress.sales.actual) }}万
                  </el-tag>
                  <span style="color:#909399;font-size:12px">/ {{ fmtW(row.progress.sales.target) }}万</span>
                  <el-tooltip v-if="row.progress.sales.override !== null && row.progress.sales.override !== undefined" content="手动修正值" placement="top">
                    <el-icon style="color:#e6a23c;font-size:14px"><EditPen /></el-icon>
                  </el-tooltip>
                </div>
                <el-progress :percentage="pct(row.progress.sales)" :stroke-width="4" :show-text="false"
                  :color="row.progress.sales.met ? '#67c23a' : '#409eff'" style="margin-top:4px" />
              </template>
              <span v-else style="color:#999">—</span>
            </template>
          </el-table-column>
          <el-table-column label="执案天数" width="140">
            <template #default="{ row }">
              <template v-if="row.progress">
                <div style="display:flex;align-items:center;gap:4px">
                  <el-tag :type="row.progress.work_days.met ? 'success' : 'danger'" size="small" round>
                    {{ row.progress.work_days.actual }}天
                  </el-tag>
                  <span style="color:#909399;font-size:12px">/ {{ row.progress.work_days.target }}天</span>
                  <el-tooltip v-if="row.progress.work_days.override !== null && row.progress.work_days.override !== undefined" content="手动修正值" placement="top">
                    <el-icon style="color:#e6a23c;font-size:14px"><EditPen /></el-icon>
                  </el-tooltip>
                </div>
                <el-progress :percentage="pct(row.progress.work_days)" :stroke-width="4" :show-text="false"
                  :color="row.progress.work_days.met ? '#67c23a' : '#409eff'" style="margin-top:4px" />
              </template>
              <span v-else style="color:#999">—</span>
            </template>
          </el-table-column>
          <el-table-column label="带队人数" min-width="180">
            <template #default="{ row }">
              <template v-if="row.progress && row.progress.mentees">
                <!-- OR模式 -->
                <template v-if="row.progress.mentees.mode === 'or' && row.progress.mentees.all_options">
                  <div v-for="(opt, oi) in row.progress.mentees.all_options" :key="oi"
                    style="display:flex;align-items:center;gap:6px;flex-wrap:wrap"
                    :style="{ marginBottom: oi < row.progress.mentees.all_options.length - 1 ? '4px' : '0',
                      paddingBottom: oi < row.progress.mentees.all_options.length - 1 ? '4px' : '0',
                      borderBottom: oi < row.progress.mentees.all_options.length - 1 ? '1px dashed #dcdfe6' : 'none' }">
                    <span style="font-size:11px;color:#909399;min-width:14px">{{ opt.met ? '✅' : '▸' }}</span>
                    <span v-for="(d, i) in opt.details" :key="i" style="display:inline-flex;align-items:center;gap:2px">
                      <el-tag :type="d.met ? 'success' : 'danger'" size="small" effect="plain" style="font-size:12px;padding:0 6px">
                        {{ levelShort(d.level) }}:{{ d.actual }}/{{ d.min }}
                      </el-tag>
                    </span>
                  </div>
                </template>
                <!-- AND模式 -->
                <template v-else-if="row.progress.mentees.details && row.progress.mentees.details.length">
                  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
                    <span style="font-size:11px;color:#909399;min-width:14px">{{ row.progress.mentees.met ? '✅' : '▸' }}</span>
                    <span v-for="(d, i) in row.progress.mentees.details" :key="i">
                      <el-tag :type="d.met ? 'success' : 'danger'" size="small" effect="plain" style="font-size:12px;padding:0 6px">
                        {{ levelShort(d.level) }}:{{ d.actual }}/{{ d.min }}
                      </el-tag>
                    </span>
                  </div>
                </template>
                <span v-else style="color:#999">—</span>
              </template>
              <span v-else style="color:#999">—</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="!row.next_level" type="warning" size="small">最高级</el-tag>
              <el-tag v-else-if="row.all_met" type="success" size="small">可申请</el-tag>
              <el-tag v-else-if="row.application && row.application.status === 'voting'" type="primary" size="small">投票中</el-tag>
              <el-tag v-else-if="row.application && row.application.status === 'approved'" type="success" size="small">已通过</el-tag>
              <el-tag v-else type="info" size="small">进行中</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button size="small" plain @click="openOverrideDialog(row)" :icon="Edit">编辑</el-button>
              <template v-if="row.next_level">
                <el-button v-if="!row.need_partner_vote && row.next_level"
                  type="warning" size="small" plain
                  @click="directPromote(row)">直接晋级</el-button>
                <el-button v-else-if="row.all_met && (!row.application || row.application.status === 'rejected')"
                  type="primary" size="small" plain
                  @click="applyPromotion(row)">发起晋级</el-button>
                <span v-else-if="row.application && row.application.status === 'voting'" style="color:#409eff;font-size:12px">等待投票</span>
                <span v-else-if="row.application && row.application.status === 'approved'" style="color:#67c23a;font-size:12px">✅ 已晋级</span>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: 晋级申请 / 投票 -->
      <el-tab-pane label="晋级申请" name="applications">
        <div style="margin-bottom:12px;display:flex;align-items:center;gap:12px">
          <el-date-picker v-model="appYear" type="year" value-format="YYYY" format="YYYY年" size="small" style="width:120px" @change="loadApplications" />
          <el-select v-model="appStatus" placeholder="全部状态" clearable size="small" style="width:120px" @change="loadApplications">
            <el-option label="待投票" value="voting" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
          <el-button type="primary" size="small" @click="loadApplications" :loading="loadingApps">刷新</el-button>
        </div>
        <el-table :data="appList" v-loading="loadingApps" stripe border size="small">
          <el-table-column prop="consultant_name" label="老师" width="90" />
          <el-table-column label="晋级" width="200">
            <template #default="{ row }">
              {{ levelMap[row.current_level] || row.current_level }} → {{ levelMap[row.target_level] || row.target_level }}
            </template>
          </el-table-column>
          <el-table-column label="年度销售" width="110" align="right">
            <template #default="{ row }">¥{{ fmtW(row.sales_actual) }}万</template>
          </el-table-column>
          <el-table-column label="执案天数" width="90" align="center">
            <template #default="{ row }">{{ row.work_days_actual }}天</template>
          </el-table-column>
          <el-table-column label="带队人数" width="90" align="center">
            <template #default="{ row }">{{ row.mentees_actual }}人</template>
          </el-table-column>
          <el-table-column label="投票" width="120" align="center">
            <template #default="{ row }">
              <span style="color:#67c23a;font-weight:600">{{ row.approve_count }}</span>
              <span style="color:#909399"> / {{ row.vote_count }}票</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button size="small" plain @click="openVoteDialog(row)">投票详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 3: 晋级标准 -->
      <el-tab-pane label="晋级标准" name="rules">
        <el-table :data="rules" v-loading="loadingRules" stripe border size="small">
          <el-table-column prop="level_name" label="职级" width="110" />
          <el-table-column label="销售指标" width="120" align="right">
            <template #default="{ row }">
              {{ row.sales_target > 0 ? fmtW(row.sales_target) + '万' : '—' }}
            </template>
          </el-table-column>
          <el-table-column label="执案天数" width="100" align="center">
            <template #default="{ row }">{{ row.min_work_days > 0 ? '≥' + row.min_work_days + '天' : '—' }}</template>
          </el-table-column>
          <el-table-column label="带队要求" min-width="180">
            <template #default="{ row }">{{ row.mentee_desc || '—' }}</template>
          </el-table-column>
          <el-table-column label="核心要求" min-width="180">
            <template #default="{ row }">{{ row.core_requirement || '—' }}</template>
          </el-table-column>
          <el-table-column label="合伙人投票" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.need_partner_vote" type="warning" size="small">需要</el-tag>
              <span v-else style="color:#999">—</span>
            </template>
          </el-table-column>
          <el-table-column label="通过率" width="80" align="center">
            <template #default="{ row }">
              {{ row.need_partner_vote ? (row.vote_pass_rate * 100) + '%' : '—' }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 编辑修正值弹窗 -->
    <el-dialog v-model="overrideDialog.show" :title="'编辑晋级数据 - ' + (overrideDialog.row?.name || '')" width="520px" destroy-on-close>
      <el-form label-width="100px" size="default">
        <el-form-item label="年度销售">
          <div style="display:flex;align-items:center;gap:8px;width:100%">
            <el-input-number v-model="overrideForm.sales" :precision="0" :step="10000" :min="0" style="flex:1" placeholder="留空=自动计算" />
            <span style="color:#909399;font-size:12px;white-space:nowrap">元</span>
          </div>
          <div style="font-size:12px;color:#909399;margin-top:4px" v-if="overrideDialog.row?.progress">
            系统自动值：¥{{ fmtW(overrideDialog.row.progress.sales.auto) }}万
          </div>
        </el-form-item>
        <el-form-item label="执案天数">
          <div style="display:flex;align-items:center;gap:8px;width:100%">
            <el-input-number v-model="overrideForm.work_days" :precision="0" :step="1" :min="0" style="flex:1" placeholder="留空=自动计算" />
            <span style="color:#909399;font-size:12px;white-space:nowrap">天</span>
          </div>
          <div style="font-size:12px;color:#909399;margin-top:4px" v-if="overrideDialog.row?.progress">
            系统自动值：{{ overrideDialog.row.progress.work_days.auto }}天
          </div>
        </el-form-item>
        <el-form-item label="带队人数">
          <div style="display:flex;align-items:center;gap:8px;width:100%">
            <el-input-number v-model="overrideForm.mentees" :precision="0" :step="1" :min="0" style="flex:1" placeholder="留空=自动计算" />
            <span style="color:#909399;font-size:12px;white-space:nowrap">人</span>
          </div>
          <div style="font-size:12px;color:#909399;margin-top:4px" v-if="overrideDialog.row?.progress">
            系统自动值：{{ overrideDialog.row.progress.mentees.auto }}人
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="overrideForm.remark" placeholder="修正原因（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="overrideDialog.row?.has_override" type="danger" plain @click="clearOverride" style="float:left">恢复自动</el-button>
        <el-button @click="overrideDialog.show = false">取消</el-button>
        <el-button type="primary" @click="saveOverride" :loading="overrideDialog.saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 投票弹窗 -->
    <el-dialog v-model="voteDialog.show" :title="'投票详情 - ' + (voteDialog.app?.consultant_name || '')" width="600px">
      <div v-if="voteDialog.app" style="margin-bottom:16px">
        <p><strong>晋级：</strong>{{ levelMap[voteDialog.app.current_level] }} → {{ levelMap[voteDialog.app.target_level] }}</p>
        <p><strong>合伙人总数：</strong>{{ voteDialog.totalPartners }}人 | <strong>已投：</strong>{{ voteDialog.votedCount }}人 | <strong>通过：</strong>{{ voteDialog.approveCount }}人</p>
        <el-progress :percentage="voteDialog.totalPartners > 0 ? Math.round(voteDialog.approveCount / voteDialog.totalPartners * 100) : 0"
          :color="voteDialog.approveCount / (voteDialog.totalPartners || 1) >= 0.8 ? '#67c23a' : '#409eff'" style="margin-top:8px" />
      </div>
      <el-table :data="voteDialog.votes" stripe border size="small" v-loading="voteDialog.loading">
        <el-table-column prop="voter_name" label="投票人" width="100" />
        <el-table-column label="投票" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.vote === 'approve' ? 'success' : 'danger'" size="small">
              {{ row.vote === 'approve' ? '满意' : '不满意' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="评定意见" min-width="200" />
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ row.voted_at?.slice(0, 16).replace('T', ' ') }}</template>
        </el-table-column>
      </el-table>
      <!-- 投票操作（仅voting状态）-->
      <div v-if="voteDialog.app?.status === 'voting'" style="margin-top:16px;padding-top:16px;border-top:1px solid #ebeef5">
        <h4 style="margin-bottom:8px">投票（选择合伙人）</h4>
        <el-form :inline="true" size="small">
          <el-form-item label="投票人">
            <el-select v-model="voteForm.voter_id" placeholder="选择合伙人" filterable style="width:160px">
              <el-option v-for="p in partners" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="意见">
            <el-input v-model="voteForm.comment" placeholder="评定意见（可选）" style="width:200px" />
          </el-form-item>
          <el-form-item>
            <el-button type="success" @click="submitVote('approve')">满意</el-button>
            <el-button type="danger" @click="submitVote('reject')">不满意</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, EditPen } from '@element-plus/icons-vue'
import http from '@/utils/http'

const tab = ref('progress')
const levelMap = {
  probation: '考核期 P', trainee: '培训期 T', pm: '项目经理 PM', pd: '项目总监 PD',
  junior_partner: '初级合伙人 JP', partner: '中级合伙人 MP',
  senior_partner: '高级合伙人 SP', founding_partner: '创始合伙人 FP',
}

const fmtW = (v) => v ? (Number(v) / 10000).toFixed(1) : '0'
const pct = (p) => p.target > 0 ? Math.min(100, Math.round(p.actual / p.target * 100)) : 100

const LEVEL_SHORT = {
  probation: 'P', trainee: 'T', pm: 'PM', pd: 'PD',
  junior_partner: 'JP', partner: 'MP', senior_partner: 'SP', founding_partner: 'FP', any: '总'
}
const levelShort = (lv) => LEVEL_SHORT[lv] || lv

// ── 分公司筛选 ──
const branches = ref([])
const branchFilter = ref(null)

async function loadBranches() {
  try {
    const res = await http.get('/admin/branches')
    branches.value = Array.isArray(res) ? res : (res && res.data) || []
  } catch {}
}

const filteredProgressList = computed(() => {
  if (!branchFilter.value) return progressList.value
  return progressList.value.filter(r => r.branch_id === branchFilter.value)
})

// ── 晋级进度 ──
const progressYear = ref(String(new Date().getFullYear()))
const progressList = ref([])
const loadingProgress = ref(false)

async function loadProgress() {
  loadingProgress.value = true
  try {
    const res = await http.get('/admin/promotion/progress', { params: { year: progressYear.value } })
    progressList.value = Array.isArray(res) ? res : (res && res.data) || []
  } finally { loadingProgress.value = false }
}

// ── 晋级申请 ──
const appYear = ref(String(new Date().getFullYear()))
const appStatus = ref('')
const appList = ref([])
const loadingApps = ref(false)

async function loadApplications() {
  loadingApps.value = true
  try {
    const params = { year: appYear.value }
    if (appStatus.value) params.status = appStatus.value
    const res = await http.get('/admin/promotion/applications', { params })
    appList.value = Array.isArray(res) ? res : (res && res.data) || []
  } finally { loadingApps.value = false }
}

// ── 晋级规则 ──
const rules = ref([])
const loadingRules = ref(false)
async function loadRules() {
  loadingRules.value = true
  try {
    const res = await http.get('/admin/promotion/rules')
    rules.value = Array.isArray(res) ? res : (res && res.data) || []
  } finally { loadingRules.value = false }
}

// ── 合伙人列表 ──
const partners = ref([])
async function loadPartners() {
  try {
    const res = await http.get('/admin/consultants')
    const all = Array.isArray(res) ? res : (res && res.data) || []
    partners.value = all.filter(c => ['junior_partner', 'partner', 'senior_partner', 'founding_partner'].includes(c.level))
  } catch {}
}

// ── 编辑修正值 ──
const overrideDialog = ref({ show: false, row: null, saving: false })
const overrideForm = ref({ sales: null, work_days: null, mentees: null, remark: '' })

function openOverrideDialog(row) {
  overrideDialog.value = { show: true, row, saving: false }
  // 预填：优先用现有修正值，没有则用自动值
  if (row.progress) {
    overrideForm.value = {
      sales: row.progress.sales.override !== null && row.progress.sales.override !== undefined
        ? row.progress.sales.override : row.progress.sales.auto,
      work_days: row.progress.work_days.override !== null && row.progress.work_days.override !== undefined
        ? row.progress.work_days.override : row.progress.work_days.auto,
      mentees: row.progress.mentees.override !== null && row.progress.mentees.override !== undefined
        ? row.progress.mentees.override : row.progress.mentees.auto,
      remark: row.override_remark || '',
    }
  } else {
    overrideForm.value = { sales: 0, work_days: 0, mentees: 0, remark: '' }
  }
}

async function saveOverride() {
  const row = overrideDialog.value.row
  if (!row) return
  overrideDialog.value.saving = true
  try {
    await http.put(`/admin/promotion/overrides/${row.consultant_id}`, {
      year: Number(progressYear.value),
      sales_override: overrideForm.value.sales,
      work_days_override: overrideForm.value.work_days,
      mentees_override: overrideForm.value.mentees,
      remark: overrideForm.value.remark,
    })
    ElMessage.success(`${row.name} 晋级数据已更新`)
    overrideDialog.value.show = false
    loadProgress()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    overrideDialog.value.saving = false
  }
}

async function clearOverride() {
  const row = overrideDialog.value.row
  if (!row) return
  await ElMessageBox.confirm(
    `确定清除 ${row.name} 的手动修正值？将恢复为系统自动计算。`,
    '恢复自动', { type: 'warning' }
  )
  try {
    await http.delete(`/admin/promotion/overrides/${row.consultant_id}`, { params: { year: Number(progressYear.value) } })
    ElMessage.success('已恢复自动计算')
    overrideDialog.value.show = false
    loadProgress()
  } catch {
    ElMessage.error('操作失败')
  }
}

// ── 发起晋级 ──
async function applyPromotion(row) {
  await ElMessageBox.confirm(
    `确定为 ${row.name} 发起晋级申请？\n${row.level_name} → ${row.next_level_name}\n将进入合伙人投票环节`,
    '发起晋级', { type: 'info' }
  )
  await http.post('/admin/promotion/apply', {
    consultant_id: row.consultant_id, target_level: row.next_level, year: Number(progressYear.value)
  })
  ElMessage.success('晋级申请已提交，等待合伙人投票')
  loadProgress()
  loadApplications()
}

// ── 直接晋级（考核期/培训期）──
async function directPromote(row) {
  await ElMessageBox.confirm(
    `确定将 ${row.name} 直接晋级为 ${row.next_level_name}？`, '直接晋级', { type: 'warning' }
  )
  await http.post('/admin/promotion/direct-promote', {
    consultant_id: row.consultant_id, target_level: row.next_level
  })
  ElMessage.success(`${row.name} 已晋级为 ${row.next_level_name}`)
  loadProgress()
}

// ── 投票弹窗 ──
const voteDialog = ref({ show: false, app: null, votes: [], totalPartners: 0, votedCount: 0, approveCount: 0, loading: false })
const voteForm = ref({ voter_id: null, comment: '' })

async function openVoteDialog(app) {
  voteDialog.value = { show: true, app, votes: [], totalPartners: 0, votedCount: 0, approveCount: 0, loading: true }
  voteForm.value = { voter_id: null, comment: '' }
  try {
    const res = await http.get(`/admin/promotion/applications/${app.id}/votes`)
    const d = (res && res.data) ? res.data : (res || {})
    voteDialog.value.votes = d.votes || []
    voteDialog.value.totalPartners = d.total_partners || 0
    voteDialog.value.votedCount = d.voted_count || 0
    voteDialog.value.approveCount = d.approve_count || 0
  } finally { voteDialog.value.loading = false }
}

async function submitVote(vote) {
  if (!voteForm.value.voter_id) return ElMessage.warning('请选择投票人')
  const app = voteDialog.value.app
  await http.post(`/admin/promotion/applications/${app.id}/vote`, {
    voter_id: voteForm.value.voter_id, vote, comment: voteForm.value.comment
  })
  ElMessage.success('投票成功')
  openVoteDialog(app)
  loadApplications()
  loadProgress()
}

const statusType = (s) => ({ voting: 'primary', approved: 'success', rejected: 'danger', pending: 'info' }[s] || 'info')
const statusLabel = (s) => ({ voting: '投票中', approved: '已通过', rejected: '已驳回', pending: '待处理' }[s] || s)

onMounted(() => { loadProgress(); loadRules(); loadPartners(); loadApplications(); loadBranches() })
</script>

<style scoped>
.promo-page { padding: 0; }
</style>
