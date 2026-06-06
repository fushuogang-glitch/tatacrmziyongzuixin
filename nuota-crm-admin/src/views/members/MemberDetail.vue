<script setup lang="ts">
import { onMounted, ref, reactive, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import { useUserStore } from '../../store/user';
import MemberRechargeBlock from './MemberRechargeBlock.vue';
import MemberDeepAnalysisBlock from './MemberDeepAnalysisBlock.vue';

const route = useRoute();
const router = useRouter();
const user = useUserStore();
const isAdmin = computed(() => user.role !== 'consultant');
const id = Number(route.params.id);
const member = ref<any>(null);
const payments = ref<any[]>([]);
const followups = ref<any[]>([]);
const loading = ref(false);
const fuLoading = ref(false);
const savingHistory = ref(false);
const savingDailyProfile = ref(false);
const historyForm = reactive({ course: 0, service: 0, referral: 0 });
const dailyProfile = reactive<any>({
  birth_date: '',
  birth_time: '',
  bazi_text: '',
  auspicious_keyword: '',
  color_personality: '',
  mbti: '',
  bazi_analysis: '',
  teacher_notes: '',
  monthly_fortune: '',
});

const STATUS_OPTS = [
  { value: 'intention', label: '意向客户', type: 'info' },
  { value: 'following', label: '跟进中', type: 'warning' },
  { value: 'closed', label: '已成交', type: 'success' },
  { value: 'lost', label: '已流失', type: 'danger' },
  { value: 'silent', label: '沉默客户', type: '' },
];

const TYPE_OPTS = [
  { value: 'note', label: '📝 备注' },
  { value: 'call', label: '📞 电话' },
  { value: 'visit', label: '🤝 拜访' },
  { value: 'wechat', label: '💬 微信' },
];

const fuForm = reactive({
  content: '',
  status: 'following',
  follow_type: 'note',
  next_follow_date: '',
});

function statusTag(s: string) {
  return STATUS_OPTS.find(o => o.value === s)?.type || '';
}
function statusLabel(s: string) {
  return STATUS_OPTS.find(o => o.value === s)?.label || s;
}
function typeLabel(t: string) {
  return TYPE_OPTS.find(o => o.value === t)?.label || t;
}

async function load() {
  loading.value = true;
  try {
    member.value = await API.memberDetail(id);
    historyForm.course = member.value.history_course_count || 0;
    historyForm.service = member.value.history_service_count || 0;
    historyForm.referral = member.value.history_referral_count || 0;
    payments.value = (await API.paymentList(id) as any) || [];
    await loadDailyProfile();
  } finally {
    loading.value = false;
  }
}

async function loadDailyProfile() {
  const p: any = await API.dailyThoughtProfile(id);
  Object.assign(dailyProfile, p || {});
}

async function loadFollowups() {
  fuLoading.value = true;
  try {
    followups.value = (await API.followupList(id) as any) || [];
  } finally {
    fuLoading.value = false;
  }
}

async function addFollowup() {
  if (!fuForm.content.trim()) {
    ElMessage.warning('请填写跟进内容');
    return;
  }
  try {
    await API.followupAdd(id, {
      content: fuForm.content,
      status: fuForm.status,
      follow_type: fuForm.follow_type,
      next_follow_date: fuForm.next_follow_date || null,
    });
    ElMessage.success('跟进记录已保存');
    fuForm.content = '';
    fuForm.next_follow_date = '';
    await loadFollowups();
  } catch {
    ElMessage.error('保存失败');
  }
}

async function deleteFollowup(fid: number) {
  try {
    await ElMessageBox.confirm('确认删除这条跟进记录？', '提示', { type: 'warning' });
    await (API as any).followupDelete(fid);
    ElMessage.success('已删除');
    await loadFollowups();
  } catch {}
}

async function saveHistory() {
  savingHistory.value = true;
  try {
    await API.memberUpdate(id, {
      history_course_count: historyForm.course,
      history_service_count: historyForm.service,
      history_referral_count: historyForm.referral,
    });
    ElMessage.success('历史次数已保存，等级已重算');
    await load();
  } catch {
    ElMessage.error('保存失败');
  } finally {
    savingHistory.value = false;
  }
}

async function saveDailyProfile() {
  savingDailyProfile.value = true;
  try {
    const p: any = await API.dailyThoughtProfileSave(id, {
      birth_date: dailyProfile.birth_date || null,
      birth_time: dailyProfile.birth_time || null,
      bazi_text: dailyProfile.bazi_text || null,
      auspicious_keyword: dailyProfile.auspicious_keyword || null,
      color_personality: dailyProfile.color_personality || null,
      mbti: dailyProfile.mbti || null,
      bazi_analysis: dailyProfile.bazi_analysis || null,
      teacher_notes: dailyProfile.teacher_notes || null,
    });
    Object.assign(dailyProfile, p || {});
    ElMessage.success('每日一念画像已保存');
  } catch {
    ElMessage.error('保存失败');
  } finally {
    savingDailyProfile.value = false;
  }
}

async function deleteMember() {
  try {
    await ElMessageBox.confirm(
      `确认删除客户「${member.value?.name}」？\n此操作不可撤销，将同时删除其缴费记录、跟进记录等关联数据。`,
      '❗ 删除客户',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'error' }
    );
    await API.memberDelete(id);
    ElMessage.success('客户已删除');
    router.push('/members');
  } catch {}
}

function fmt(v: any) {
  if (!v) return '-';
  return String(v).replace('T', ' ').slice(0, 16);
}

function memberTypeName(t: string) {
  const map: any = { trial: '体验会员', annual: '年费会员', vip: 'VIP' };
  return map[t] || t;
}
function memberTierName(t: string) {
  const map: any = { kindergarten: '七杀星·南斗度厄星君', primary: '天相星·南斗司禄星君', junior: '天同星·南斗益算星君', senior: '天机星·南斗上生星君', college: '天梁星·南斗延寿星君', bachelor: '天府星·南斗司命星君', master: '太阴元君·月宫', doctor: '太阳帝君·日宫', postdoc: '紫微大帝·中天北极' };
  return map[t] || t || '-';
}
function statusName(s: string) {
  const map: any = { active: '正常', expired: '已到期', frozen: '已冻结' };
  return map[s] || s;
}
function payTypeName(t: string) {
  const map: any = { trial: '体验费', annual: '年费' };
  return map[t] || t;
}
function payStatusName(s: string) {
  const map: any = { pending: '待付款', paid: '已付款', refunded: '已退款' };
  return map[s] || s;
}

onMounted(() => {
  load();
  loadFollowups();
});
</script>

<template>
  <div v-loading="loading" style="max-width: 960px; margin: 0 auto;">
    <el-page-header @back="router.back()" style="margin-bottom: 16px;">
      <template #content>
        <span style="font-weight: 600;">学员详情</span>
        <el-tag v-if="member" :type="member.status === 'active' ? 'success' : 'danger'"
          style="margin-left: 10px;" size="small">
          {{ statusName(member?.status) }}
        </el-tag>
      </template>
    </el-page-header>

    <!-- 基本信息 -->
    <el-card v-if="member" style="margin-bottom: 16px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">基本信息</span>
          <el-button v-if="isAdmin" type="danger" size="small" @click="deleteMember">🗑 删除客户</el-button>
        </div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="学员编号">{{ member.member_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ member.name }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ member.phone }}</el-descriptions-item>
        <el-descriptions-item label="性别">
          <el-tag :type="member.gender === 'male' ? '' : 'danger'" size="small">
            {{ member.gender === 'male' ? '♂ 先生' : '♀ 女士' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="生日">{{ member.birthday || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="企业名称">{{ member.enterprise_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="城市">{{ member.city || '-' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ {'boss':'👑 老板','partner':'🤝 合伙人','store_manager':'🏪 店长','operations_gm':'📊 运营总经理','manager':'👔 经理'}[member.role] || member.role || '-' }}</el-descriptions-item>
        <el-descriptions-item label="会员类型">{{ memberTypeName(member.member_type) }}</el-descriptions-item>
        <el-descriptions-item label="会员等级">{{ memberTierName(member.member_tier) }}</el-descriptions-item>
        <el-descriptions-item label="年消费">¥{{ member.annual_spending || 0 }}</el-descriptions-item>
        <el-descriptions-item label="入学日期">{{ member.enroll_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="到期日期">{{ member.expire_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="推荐码">{{ member.referral_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="人脸认证">
          <el-tag :type="member.face_bound ? 'success' : 'info'" size="small">
            {{ member.face_bound ? '已认证' : '未认证' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="协议签署">
          <el-tag :type="member.agreement_signed ? 'success' : 'info'" size="small">
            {{ member.agreement_signed ? '已签署' : '未签署' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ fmt(member.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="副负责人">
          <span v-if="member.co_manager_name">{{ member.co_manager_name }}（{{ member.co_manager_phone || '-' }}）</span>
          <span v-else style="color:#c0c4cc">未设置</span>
        </el-descriptions-item>
        <el-descriptions-item label="门店数量">{{ member.store_count || '-' }}</el-descriptions-item>
        <el-descriptions-item label="门店性质">{{ member.store_type || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 历史次数调整（影响会员等级） - 仅管理员可见 -->
    <el-card v-if="member && isAdmin" style="margin-bottom: 16px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">📊 服务统计 & 历史次数调整</span>
          <el-tag type="warning" size="small">修改后等级自动重算</el-tag>
        </div>
      </template>
      <div class="history-grid">
        <div class="history-item">
          <div class="history-label">📚 课程次数</div>
          <div class="history-row">
            <span class="history-sys">系统: {{ member.tier_info?.stats?.course_count - (member.history_course_count||0) || 0 }}</span>
            <span class="history-plus">+</span>
            <span class="history-manual">历史:</span>
            <el-input-number v-model="historyForm.course" :min="0" :max="999" size="small" style="width:120px;" />
          </div>
          <div class="history-total">合计: <b>{{ (member.tier_info?.stats?.course_count - (member.history_course_count||0) || 0) + historyForm.course }}</b> 次</div>
        </div>
        <div class="history-item">
          <div class="history-label">🔧 专案服务次数</div>
          <div class="history-row">
            <span class="history-sys">系统: {{ member.tier_info?.stats?.service_count - (member.history_service_count||0) || 0 }}</span>
            <span class="history-plus">+</span>
            <span class="history-manual">历史:</span>
            <el-input-number v-model="historyForm.service" :min="0" :max="999" size="small" style="width:120px;" />
          </div>
          <div class="history-total">合计: <b>{{ (member.tier_info?.stats?.service_count - (member.history_service_count||0) || 0) + historyForm.service }}</b> 次</div>
        </div>
        <div class="history-item">
          <div class="history-label">🤝 推荐人数</div>
          <div class="history-row">
            <span class="history-sys">系统: {{ member.tier_info?.stats?.referral_count - (member.history_referral_count||0) || 0 }}</span>
            <span class="history-plus">+</span>
            <span class="history-manual">历史:</span>
            <el-input-number v-model="historyForm.referral" :min="0" :max="999" size="small" style="width:120px;" />
          </div>
          <div class="history-total">合计: <b>{{ (member.tier_info?.stats?.referral_count - (member.history_referral_count||0) || 0) + historyForm.referral }}</b> 次</div>
        </div>
      </div>
      <div style="text-align:right;margin-top:12px;">
        <el-button type="primary" @click="saveHistory" :loading="savingHistory">保存并重算等级</el-button>
      </div>
    </el-card>

    <!-- 缴费记录 -->
    <el-card style="margin-bottom: 16px;">
      <template #header><span style="font-weight:600;">缴费记录</span></template>
      <el-table :data="payments" stripe size="small">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">
            <span style="color: #67c23a; font-weight: 600;">¥{{ row.amount }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">{{ payTypeName(row.pay_type) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.pay_status === 'paid' ? 'success' : row.pay_status === 'refunded' ? 'danger' : 'warning'" size="small">
              {{ payStatusName(row.pay_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="支付时间" width="160">
          <template #default="{ row }">{{ fmt(row.pay_time) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" />
      </el-table>
    </el-card>

    <!-- 储值 -->
    <MemberRechargeBlock :member-id="id" style="margin-bottom: 16px;" />

    <!-- 八字命理测算 / 每日一念画像 -->
    <el-card v-if="member" style="margin-bottom: 16px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">☯ 八字命理测算</span>
          <el-tag type="warning" size="small">老师后台录入 / 月度提醒客户</el-tag>
        </div>
      </template>
      <el-form label-width="110px">
        <div class="daily-profile-grid">
          <el-form-item label="出生日期">
            <el-date-picker v-model="dailyProfile.birth_date" type="date" value-format="YYYY-MM-DD" placeholder="用户填写或老师补录" style="width:100%;" />
          </el-form-item>
          <el-form-item label="出生时辰">
            <el-input v-model="dailyProfile.birth_time" placeholder="如：子时 / 23:30" />
          </el-form-item>
          <el-form-item label="吉祥词">
            <el-input v-model="dailyProfile.auspicious_keyword" placeholder="可选：固定展示给客户的词" />
          </el-form-item>
          <el-form-item label="颜色性格">
            <el-input v-model="dailyProfile.color_personality" placeholder="如：金色行动型 / 蓝色理性型" />
          </el-form-item>
          <el-form-item label="MBTI">
            <el-input v-model="dailyProfile.mbti" placeholder="如：ENTJ / INFJ" />
          </el-form-item>
        </div>
        <el-form-item label="生辰八字">
          <el-input v-model="dailyProfile.bazi_text" placeholder="如：甲子 乙丑 丙寅 丁卯" />
        </el-form-item>
        <el-form-item label="命理测算">
          <el-input
            v-model="dailyProfile.bazi_analysis"
            type="textarea"
            :rows="5"
            placeholder="输入你的专业八字命理测算内容：格局、五行喜忌、当月宜忌、经营提醒、沟通建议等"
          />
        </el-form-item>
        <el-form-item label="老师备注">
          <el-input v-model="dailyProfile.teacher_notes" type="textarea" :rows="3" placeholder="老师对客户性格、沟通方式、服务注意事项的补充" />
        </el-form-item>
        <el-form-item label="本月运势">
          <el-input v-model="dailyProfile.monthly_fortune" type="textarea" :rows="4" readonly />
        </el-form-item>
        <div style="text-align:right;">
          <el-button type="primary" @click="saveDailyProfile" :loading="savingDailyProfile">保存测算并生成本月运势</el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 🔮 会员深度分析 -->
    <MemberDeepAnalysisBlock :member-id="id" />

    <!-- 客户跟进记录 -->
    <el-card v-loading="fuLoading">
      <template #header>
        <span style="font-weight:600;">客户跟进记录</span>
        <span style="float:right; color:#909399; font-size:13px;">共 {{ followups.length }} 条</span>
      </template>

      <!-- 新增跟进表单 -->
      <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
        <div style="display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap;">
          <el-select v-model="fuForm.status" placeholder="跟进状态" size="small" style="width: 130px;">
            <el-option v-for="o in STATUS_OPTS" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
          <el-select v-model="fuForm.follow_type" placeholder="跟进方式" size="small" style="width: 120px;">
            <el-option v-for="o in TYPE_OPTS" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
          <el-date-picker v-model="fuForm.next_follow_date" type="datetime" placeholder="下次跟进时间（可选）"
            size="small" style="width: 200px;" value-format="YYYY-MM-DD HH:mm:ss" />
        </div>
        <el-input v-model="fuForm.content" type="textarea" :rows="3"
          placeholder="记录本次跟进内容、客户反馈、下步计划..." />
        <div style="text-align: right; margin-top: 8px;">
          <el-button type="primary" size="small" @click="addFollowup">保存跟进记录</el-button>
        </div>
      </div>

      <!-- 跟进时间线 -->
      <el-empty v-if="followups.length === 0" description="暂无跟进记录" :image-size="60" />
      <el-timeline v-else>
        <el-timeline-item v-for="f in followups" :key="f.id"
          :timestamp="f.created_at" placement="top">
          <el-card shadow="never" style="border: 1px solid #ebeef5;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div style="flex: 1;">
                <div style="margin-bottom: 8px; display: flex; gap: 6px; flex-wrap: wrap;">
                  <el-tag :type="statusTag(f.status)" size="small">{{ statusLabel(f.status) }}</el-tag>
                  <el-tag type="info" size="small">{{ typeLabel(f.follow_type) }}</el-tag>
                  <span style="font-size: 12px; color: #909399;">{{ f.admin_name }}</span>
                </div>
                <div style="color: #303133; line-height: 1.6;">{{ f.content }}</div>
                <div v-if="f.next_follow_date" style="margin-top: 6px; font-size: 12px; color: #e6a23c;">
                  📅 下次跟进：{{ f.next_follow_date }}
                </div>
              </div>
              <el-button link type="danger" size="small" @click="deleteFollowup(f.id)"
                style="margin-left: 10px; flex-shrink: 0;">删除</el-button>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<style scoped>
.history-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.history-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 14px;
}
.history-label {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 8px;
}
.history-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  flex-wrap: wrap;
}
.history-sys { color: #909399; }
.history-plus { color: #e6a23c; font-weight: 600; }
.history-manual { color: #606266; }
.history-total {
  margin-top: 8px;
  font-size: 13px;
  color: #409eff;
}
.daily-profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 12px;
}
@media (max-width: 768px) {
  .daily-profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
