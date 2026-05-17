<template>
  <div class="page" v-loading="loading">
    <el-button text @click="$router.back()" style="margin-bottom:12px">← 返回课程列表</el-button>

    <!-- 课程信息卡 -->
    <el-card class="card">
      <template #header>
        <div class="card-head">
          <span>📚 {{ course.title }}</span>
          <el-tag :type="statusType(course.status)">{{ statusLabel(course.status) }}</el-tag>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="品牌">{{ course.brand }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ course.category || '-' }}</el-descriptions-item>
        <el-descriptions-item label="讲师">{{ course.instructor || '-' }}</el-descriptions-item>
        <el-descriptions-item label="地点">{{ course.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="日期">{{ course.start_date }} ~ {{ course.end_date }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ course.start_time }} ~ {{ course.end_time }}</el-descriptions-item>
        <el-descriptions-item label="价格">¥{{ course.price }}</el-descriptions-item>
        <el-descriptions-item label="名额">{{ course.enrolled_count || 0 }} / {{ course.max_students }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="course.description" style="margin-top:12px; color:#666;">{{ course.description }}</div>
    </el-card>

    <!-- 报名学员列表 -->
    <el-card class="card">
      <template #header>
        <div class="card-head">
          <span>👥 报名学员（{{ enrollments.length }}人）</span>
        </div>
      </template>
      <el-table :data="enrollments" border stripe size="small">
        <el-table-column prop="attendee_name" label="姓名" width="100" />
        <el-table-column prop="attendee_phone" label="手机" width="130" />
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="enrollStatusType(row.status)" size="small">{{ enrollStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="100" align="right">
          <template #default="{ row }">¥{{ row.payment_amount }}</template>
        </el-table-column>
        <el-table-column label="跟进" width="60" align="center">
          <template #default="{ row }">{{ row.followup_count || 0 }}次</template>
        </el-table-column>
        <el-table-column label="评价" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.rating" style="color:#c9a96e; font-weight:600;">★{{ row.rating }}</span>
            <span v-else style="color:#ccc;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" align="center">
          <template #default="{ row }">
            <el-button v-if="row.status === 'enrolled'" link type="primary" @click="doContact(row)">📞 确认联系</el-button>
            <el-button v-if="row.status === 'contacted'" link type="primary" @click="doNotify(row)">📨 发参会通知</el-button>
            <el-button v-if="row.status === 'notified'" link type="success" @click="doCheckin(row)">✅ 签到扣费</el-button>
            <el-button v-if="['checked_in','follow_up'].includes(row.status)" link type="warning" @click="openFollowup(row)">📋 跟进</el-button>
            <el-button v-if="row.status === 'follow_up' && row.followup_count >= 1" link type="success" @click="doComplete(row)">🏁 结束</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 课程操作 -->
    <el-card class="card">
      <template #header><span>⚙️ 课程操作</span></template>
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        <el-button v-if="course.status === 'published' || course.status === 'ongoing'" type="danger" @click="endCourse">🔚 结束课程</el-button>
        <el-button type="primary" @click="reviewDlg.vis = true">🎥 发布/编辑课程回顾</el-button>
      </div>
    </el-card>

    <!-- 课程回顾展示 -->
    <el-card v-if="course.review_text || course.video_channel_url" class="card">
      <template #header><span>🎥 课程回顾</span></template>
      <div v-if="course.review_text" style="margin-bottom:12px; color:#333; line-height:1.8;">{{ course.review_text }}</div>
      <div v-if="course.highlights" style="margin-bottom:12px;">
        <el-tag v-for="h in course.highlights.split(',')" :key="h" size="small" style="margin-right:6px;">{{ h.trim() }}</el-tag>
      </div>
      <div v-if="course.video_channel_url">
        <el-link :href="course.video_channel_url" target="_blank" type="primary">📹 视频号回顾链接</el-link>
      </div>
    </el-card>

    <!-- 顾问联系弹窗 -->
    <el-dialog v-model="contactDlg.vis" title="📞 顾问联系确认" width="480px">
      <p>确认已电话联系学员 <b>{{ contactDlg.name }}</b>，并发送参会准备资料：</p>
      <el-input v-model="contactDlg.note" type="textarea" :rows="3" placeholder="沟通备注（选填）" style="margin-top:12px" />
      <template #footer>
        <el-button @click="contactDlg.vis = false">取消</el-button>
        <el-button type="primary" @click="submitContact">确认已联系</el-button>
      </template>
    </el-dialog>

    <!-- 跟进弹窗 -->
    <el-dialog v-model="followupDlg.vis" title="📋 售后跟进" width="480px">
      <p>学员：<b>{{ followupDlg.name }}</b>（第{{ followupDlg.number }}次跟进）</p>
      <el-input v-model="followupDlg.content" type="textarea" :rows="3" placeholder="跟进内容..." style="margin-top:12px" />
      <el-input v-model="followupDlg.next_action" placeholder="下次计划（选填）" style="margin-top:12px" />
      <template #footer>
        <el-button @click="followupDlg.vis = false">取消</el-button>
        <el-button type="primary" @click="submitFollowup">提交跟进</el-button>
      </template>
    </el-dialog>

    <!-- 课程回顾弹窗 -->
    <el-dialog v-model="reviewDlg.vis" title="🎥 发布课程回顾" width="580px">
      <el-form :model="reviewDlg.form" label-width="120px">
        <el-form-item label="课程回顾文字">
          <el-input v-model="reviewDlg.form.review_text" type="textarea" :rows="4" placeholder="课程亮点、学员反馈、核心收获..." />
        </el-form-item>
        <el-form-item label="视频号链接">
          <el-input v-model="reviewDlg.form.video_channel_url" placeholder="粘贴视频号链接" />
        </el-form-item>
        <el-form-item label="课程亮点标签">
          <el-input v-model="reviewDlg.form.highlights" placeholder="用英文逗号分隔，如：营销体系,客户分级,品项搭建" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDlg.vis = false">取消</el-button>
        <el-button type="primary" @click="submitReview">发布回顾</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const route = useRoute();
const id = Number(route.params.id);
const loading = ref(false);
const course = ref<any>({});
const enrollments = ref<any[]>([]);


function statusType(s: string) {
  return ({ draft: 'info', published: 'success', ongoing: 'warning', ended: '' } as any)[s] || '';
}
function statusLabel(s: string) {
  return ({ draft: '草稿', published: '已发布', ongoing: '进行中', ended: '已结束' } as any)[s] || s;
}
function enrollStatusType(s: string) {
  return ({ enrolled: 'warning', contacted: 'primary', notified: '', checked_in: 'success', follow_up: 'warning', completed: 'success', cancelled: 'info' } as any)[s] || '';
}
function enrollStatusLabel(s: string) {
  return ({ enrolled: '已报名', contacted: '已联系', notified: '已通知', checked_in: '已签到', follow_up: '跟进中', completed: '已完成', cancelled: '已取消' } as any)[s] || s;
}

// ── 顾问联系 ──
const contactDlg = reactive({ vis: false, id: 0, name: '', note: '' });
function doContact(row: any) {
  contactDlg.id = row.id;
  contactDlg.name = row.attendee_name;
  contactDlg.note = '';
  contactDlg.vis = true;
}
async function submitContact() {
  await API.courseEnrollContact(contactDlg.id, { contact_note: contactDlg.note });
  ElMessage.success('已确认联系');
  contactDlg.vis = false;
  load();
}

// ── 发参会通知 ──
async function doNotify(row: any) {
  await ElMessageBox.confirm(`确认向 ${row.attendee_name} 发送参会通知（订票/交通/住宿信息）？`, '发送参会通知');
  await API.courseEnrollNotify(row.id);
  ElMessage.success('参会通知已发送');
  load();
}

// ── 签到扣费 ──
async function doCheckin(row: any) {
  await ElMessageBox.confirm(`确认 ${row.attendee_name} 签到？学费将自动扣除`, '签到扣费');
  await API.courseEnrollCheckin(row.id, 'manual');
  ElMessage.success('签到成功，学费已扣除');
  load();
}

// ── 跟进 ──
const followupDlg = reactive({ vis: false, id: 0, name: '', number: 1, content: '', next_action: '' });
function openFollowup(row: any) {
  followupDlg.id = row.id;
  followupDlg.name = row.attendee_name;
  followupDlg.number = (row.followup_count || 0) + 1;
  followupDlg.content = '';
  followupDlg.next_action = '';
  followupDlg.vis = true;
}
async function submitFollowup() {
  await API.courseEnrollFollowup(followupDlg.id, { content: followupDlg.content, next_action: followupDlg.next_action });
  ElMessage.success(`第${followupDlg.number}次跟进已记录`);
  followupDlg.vis = false;
  load();
}

// ── 结束 ──
async function doComplete(row: any) {
  await ElMessageBox.confirm(`确认 ${row.attendee_name} 课程流程结束？`, '课程结束');
  await API.courseEnrollComplete(row.id);
  ElMessage.success('课程已结束');
  load();
}

// ── 结束课程 ──
async function endCourse() {
  await ElMessageBox.confirm('确认结束课程？课程将归入“往期课程”', '结束课程');
  await API.courseEnd(id);
  ElMessage.success('课程已结束，已归入往期');
  load();
}

// ── 课程回顾 ──
const reviewDlg = reactive({
  vis: false,
  form: { review_text: '', video_channel_url: '', highlights: '' }
});
async function submitReview() {
  await API.courseReview(id, reviewDlg.form);
  ElMessage.success('课程回顾已发布');
  reviewDlg.vis = false;
  load();
}

// 加载时填充回顾表单
async function load() {
  loading.value = true;
  try {
    const r1: any = await API.courseDetail(id);
    course.value = r1?.data || r1 || {};
    // 填充回顾表单
    reviewDlg.form.review_text = course.value.review_text || '';
    reviewDlg.form.video_channel_url = course.value.video_channel_url || '';
    reviewDlg.form.highlights = course.value.highlights || '';
    const r2: any = await API.courseEnrollments({ course_id: id });
    enrollments.value = r2?.data || r2 || [];
  } finally { loading.value = false; }
}

onMounted(load);
</script>

<style scoped>
.page { padding: 20px; }
.card { margin-bottom: 16px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
</style>
