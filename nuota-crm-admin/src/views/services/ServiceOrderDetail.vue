<template>
  <div class="page" v-loading="loading">
    <el-button text @click="$router.back()" style="margin-bottom: 12px">← 返回工单列表</el-button>

    <!-- 流程步骤条（8步） -->
    <el-card class="card">
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step v-for="s in steps" :key="s.status" :title="s.label"
          :description="s.done ? '✓' : s.current ? '当前' : ''" />
      </el-steps>
    </el-card>

    <!-- 工单基本信息 -->
    <el-card class="card">
      <div class="head">
        <div>
          <el-tag :type="statusType(wf.order?.status)" size="large">{{ wf.order?.workflow_stage || wf.order?.status }}</el-tag>
          <span class="order-no">{{ wf.order?.order_no }}</span>
        </div>
        <div class="actions">
          <el-button type="default" @click="showEditInfo">✏️ 编辑信息</el-button>
          <el-button v-if="can.can_confirm" type="primary" @click="showConfirm">确认工单</el-button>
          <el-button v-if="can.can_accept" type="primary" @click="showAccept">接受工单</el-button>
          <el-button v-if="can.can_prepare" type="warning" @click="showPrepare">提交执案准备</el-button>
          <el-button v-if="can.can_start" type="primary" @click="showStart">到店开始执案</el-button>
          <el-button v-if="can.can_log" type="primary" @click="showDayLog">填写每日日志</el-button>
          <el-button v-if="can.can_report" type="success" @click="showReport">提交执案报告</el-button>
          <el-button v-if="can.can_followup" type="warning" @click="showFollowup">填写跟进会议</el-button>
          <el-button v-if="can.can_complete" type="success" @click="doComplete">整体执案结束</el-button>
          <el-button v-if="can.can_cancel" type="danger" plain @click="doCancel">取消工单</el-button>
        </div>
      </div>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="服务项目">{{ wf.service?.name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="服务类别">{{ wf.service?.category || '—' }}</el-descriptions-item>
        <el-descriptions-item label="会员">{{ wf.member?.name || '—' }}（{{ wf.member?.enterprise_name || '' }}）</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ wf.member?.phone || '—' }}</el-descriptions-item>
        <el-descriptions-item label="主案老师">{{ wf.consultant?.name || '待分配' }}</el-descriptions-item>
        <el-descriptions-item label="助理老师">{{ wf.assistant?.name || '无' }}</el-descriptions-item>
        <el-descriptions-item label="主案专业">{{ wf.consultant?.specialty || '—' }}</el-descriptions-item>
        <el-descriptions-item label="预约日期">{{ wf.order?.appoint_date || '—' }}</el-descriptions-item>
        <el-descriptions-item label="预约时段">{{ wf.order?.appoint_time || '—' }}</el-descriptions-item>
        <el-descriptions-item label="服务门店">{{ wf.order?.store_name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="第几期下店">第 {{ wf.order?.visit_number || 1 }} 期</el-descriptions-item>
        <el-descriptions-item label="执案天数">{{ wf.schedule_days || wf.service?.duration_days || '待排期' }} 天<span v-if="wf.schedule_start" style="color:#999;margin-left:8px">{{ wf.schedule_start }} ~ {{ wf.schedule_end }}</span></el-descriptions-item>
        <el-descriptions-item label="进度">
          <el-progress :percentage="wf.order?.workflow_progress || 0" :stroke-width="12" />
        </el-descriptions-item>
        <el-descriptions-item label="跟进次数">{{ wf.followup_count || 0 }} / 3</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ wf.order?.remark || '无' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 执案日志时间线 -->
    <el-card class="card">
      <template #header>
        <div class="card-head">
          <span>执案日志（{{ wf.logs?.length || 0 }} 条）</span>
        </div>
      </template>

      <el-timeline v-if="wf.logs?.length">
        <el-timeline-item
          v-for="l in wf.logs" :key="l.id"
          :timestamp="l.created_at"
          :color="logColor(l.log_type)"
          placement="top"
        >
          <div class="log-item">
            <div class="log-header">
              <el-tag size="small" :type="logTagType(l.log_type)">{{ l.stage }}</el-tag>
              <span v-if="l.day_number" class="day-badge">{{ l.log_type === 'followup' ? `回访#${l.day_number}` : `Day${l.day_number}` }}</span>
            </div>
            <div class="log-content">
              <template v-if="parseChecklist(l.content)">
                <!-- 渲染非Checklist部分的文本（准备摘要、订票信息） -->
                <div v-for="(line, li) in extractTextLines(l.content)" :key="li" style="margin-bottom:4px">{{ line }}</div>
                <div class="checklist-display">
                  <div v-for="(group, gi) in groupChecklist(parseChecklist(l.content))" :key="gi" class="checklist-gate">
                    <div class="gate-label">🔒 第{{ group.gate }}关：{{ group.gate_name }}</div>
                    <div v-for="(ci, idx) in group.items" :key="idx" class="checklist-item" :class="{ done: ci.done }">
                      <span class="check-icon">{{ ci.done ? '✅' : '⬜' }}</span>
                      <span>{{ ci.item }}</span>
                    </div>
                  </div>
                </div>
              </template>
              <template v-else>{{ l.content }}</template>
            </div>
            <div v-if="l.findings" class="log-sub"><strong>{{ l.log_type === 'followup' ? '新问题：' : '发现问题：' }}</strong>{{ l.findings }}</div>
            <div v-if="l.decisions" class="log-sub"><strong>{{ l.log_type === 'followup' ? '数据回顾：' : '达成共识：' }}</strong>{{ l.decisions }}</div>
            <div v-if="l.next_actions" class="log-sub"><strong>{{ l.log_type === 'followup' ? '跟进行动项：' : '下一步：' }}</strong>{{ l.next_actions }}</div>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无日志" />
    </el-card>

    <!-- 满意度评价 -->
    <el-card v-if="wf.order?.rating" class="card">
      <template #header><span>满意度评价</span></template>
      <div class="rating-row">
        <span class="stars">{{ '★'.repeat(wf.order.rating) }}{{ '☆'.repeat(5 - wf.order.rating) }}</span>
        <span class="rating-num">{{ wf.order.rating }}/5</span>
      </div>
      <div class="comment">{{ wf.order.rating_comment || '无评论' }}</div>
    </el-card>

    <!-- ===== 弹窗 ===== -->

    <!-- 编辑工单信息（任何阶段可用，不影响流程） -->
    <el-dialog v-model="editDlg.vis" title="编辑工单信息" width="620px">
      <el-form :model="editDlg.form" label-width="100px">
        <el-form-item label="服务项目">
          <el-select v-model="editDlg.form.service_id" style="width:100%" clearable placeholder="选择服务项目">
            <el-option v-for="s in serviceList" :key="s.id" :value="s.id" :label="`${s.name}（${s.category}）`" />
          </el-select>
        </el-form-item>
        <el-form-item label="会员">
          <el-select v-model="editDlg.form.member_id" style="width:100%" clearable filterable placeholder="搜索会员">
            <el-option v-for="m in memberList" :key="m.id" :value="m.id" :label="`${m.name}（${m.enterprise_name || m.phone || ''}）`" />
          </el-select>
        </el-form-item>
        <el-form-item label="主案老师">
          <el-select v-model="editDlg.form.consultant_id" style="width:100%" clearable>
            <el-option v-for="c in consultants" :key="c.id" :value="c.id" :label="c.name + (c.specialty ? ` · ${c.specialty}` : '')" />
          </el-select>
        </el-form-item>
        <el-form-item label="助理老师">
          <el-select v-model="editDlg.form.assistant_id" style="width:100%" clearable placeholder="可不选">
            <el-option v-for="c in consultants.filter((c: any) => c.id !== editDlg.form.consultant_id)" :key="c.id" :value="c.id" :label="c.name + (c.specialty ? ` · ${c.specialty}` : '')" />
          </el-select>
        </el-form-item>
        <el-form-item label="预约日期">
          <el-date-picker v-model="editDlg.form.appoint_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="预约时段">
          <el-input v-model="editDlg.form.appoint_time" placeholder="如 09:00-18:00" />
        </el-form-item>
        <el-form-item label="服务门店">
          <el-input v-model="editDlg.form.store_name" placeholder="如 武汉 木子美学" />
        </el-form-item>
        <el-form-item label="门店地址">
          <el-input v-model="editDlg.form.store_address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="第几期下店">
          <el-input-number v-model="editDlg.form.visit_number" :min="1" :max="99" controls-position="right" style="width:160px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editDlg.form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDlg.vis = false">取消</el-button>
        <el-button type="primary" @click="doEditInfo">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- 确认工单 -->
    <el-dialog v-model="confirmDlg.vis" title="确认工单 · 分配老师" width="520px">
      <el-form :model="confirmDlg.form" label-width="90px">
        <el-form-item label="主案老师" required>
          <el-select v-model="confirmDlg.form.consultant_id" style="width:100%">
            <el-option v-for="c in consultants" :key="c.id" :value="c.id" :label="c.name + (c.specialty ? ` · ${c.specialty}` : '')" />
          </el-select>
        </el-form-item>
        <el-form-item label="助理老师">
          <el-select v-model="confirmDlg.form.assistant_id" style="width:100%" clearable placeholder="可不选">
            <el-option v-for="c in consultants.filter((c: any) => c.id !== confirmDlg.form.consultant_id)" :key="c.id" :value="c.id" :label="c.name + (c.specialty ? ` · ${c.specialty}` : '')" />
          </el-select>
        </el-form-item>
        <el-form-item label="确认日期">
          <el-date-picker v-model="confirmDlg.form.appoint_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="时段">
          <el-input v-model="confirmDlg.form.appoint_time" placeholder="如 09:00-18:00" />
        </el-form-item>
        <el-form-item label="门店名称">
          <el-input v-model="confirmDlg.form.store_name" />
        </el-form-item>
        <el-form-item label="门店地址">
          <el-input v-model="confirmDlg.form.store_address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="confirmDlg.form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="confirmDlg.vis = false">取消</el-button>
        <el-button type="primary" @click="doConfirm">确认并通知老师</el-button>
      </template>
    </el-dialog>

    <!-- 接受工单 -->
    <el-dialog v-model="acceptDlg.vis" title="接受工单" width="420px">
      <el-form :model="acceptDlg.form" label-width="80px">
        <el-form-item label="接单备注">
          <el-input v-model="acceptDlg.form.accept_note" type="textarea" :rows="3" placeholder="如：已与客户电话确认、需要提前准备XXX" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="acceptDlg.vis = false">取消</el-button>
        <el-button type="primary" @click="doAccept">确认接单</el-button>
      </template>
    </el-dialog>

    <!-- 执案准备（五关Checklist + 订票信息） -->
    <el-dialog v-model="prepareDlg.vis" title="📋 塔塔执案前Checklist（助理版）" width="680px" top="5vh">
      <el-form :model="prepareDlg.form" label-width="90px">
        <el-form-item label="准备摘要" required>
          <el-input v-model="prepareDlg.form.prepare_summary" type="textarea" :rows="2" placeholder="概述本次执案准备情况" />
        </el-form-item>

        <el-form-item label="订票信息">
          <el-input v-model="prepareDlg.form.travel_info" type="textarea" :rows="3"
            placeholder="🚄 高铁/航班信息、酒店预订信息&#10;如：5月20日 G1234 武汉→扬中 08:00-12:00&#10;酒店：扬中XX酒店 2晚" />
        </el-form-item>

        <el-divider content-position="left">🔒 五关Checklist（出发前48小时填写）</el-divider>

        <div v-for="gate in uniqueGates" :key="gate" class="gate-section">
          <div class="gate-title">第{{ gate }}关：{{ gateNames[gate] }}</div>
          <div v-for="(item, idx) in prepareChecklist.filter(c => c.gate === gate)" :key="idx" class="checklist-row">
            <el-checkbox v-model="item.done">{{ item.item }}</el-checkbox>
          </div>
        </div>

        <el-divider />
        <div class="checklist-add">
          <el-input v-model="newCheckItem" placeholder="自定义添加准备项" size="small" @keyup.enter="addCheckItem">
            <template #append><el-button @click="addCheckItem">+ 添加</el-button></template>
          </el-input>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="prepareDlg.vis = false">取消</el-button>
        <el-button type="warning" @click="doPrepare">提交执案准备</el-button>
      </template>
    </el-dialog>

    <!-- 开始执案 -->
    <el-dialog v-model="startDlg.vis" title="到店开始执案" width="520px">
      <el-form :model="startDlg.form" label-width="100px">
        <el-form-item label="实际到店日期">
          <el-date-picker v-model="startDlg.form.actual_start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="参与人员">
          <el-input v-model="startDlg.form.participants" placeholder="如：老板+3名顾问+2名美容师" />
        </el-form-item>
        <el-form-item label="研讨会议程">
          <el-input v-model="startDlg.form.agenda" type="textarea" :rows="4" placeholder="Day1: 现状诊断研讨&#10;Day2: 系统框架共建&#10;Day3: 启动会（视情况）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="startDlg.vis = false">取消</el-button>
        <el-button type="primary" @click="doStart">确认到店·开始执案</el-button>
      </template>
    </el-dialog>

    <!-- 每日执案日志 -->
    <el-dialog v-model="dayLogDlg.vis" title="填写每日执案日志" width="680px" top="5vh">
      <el-form :model="dayLogDlg.form" label-width="90px">
        <el-form-item label="第几天" required>
          <el-input-number v-model="dayLogDlg.form.day_number" :min="1" :max="30" controls-position="right" style="width:160px" />
          <span style="margin-left:12px;color:#999;font-size:13px">第 {{ dayLogDlg.form.day_number }} 天</span>
        </el-form-item>
        <el-form-item label="研讨阶段">
          <el-select v-model="dayLogDlg.form.stage" style="width:100%" filterable allow-create placeholder="选择或输入">
            <el-option value="现状诊断" label="现状诊断 · 差额分析" />
            <el-option value="框架共建" label="系统框架共建 · 品项/SOP/客户分级" />
            <el-option value="启动会" label="启动会 · 全员宣布" />
            <el-option value="品项搭建" label="品项搭建 · CABD框架" />
            <el-option value="营销设计" label="营销大促设计" />
            <el-option value="团队培训" label="团队培训 · 场景演练" />
            <el-option value="其他" label="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="执案内容" required>
          <el-input v-model="dayLogDlg.form.content" type="textarea" :rows="4" placeholder="今天做了什么、研讨了哪些内容" />
        </el-form-item>
        <el-form-item label="发现问题">
          <el-input v-model="dayLogDlg.form.findings" type="textarea" :rows="2" placeholder="门店存在的核心问题" />
        </el-form-item>
        <el-form-item label="达成共识">
          <el-input v-model="dayLogDlg.form.decisions" type="textarea" :rows="2" placeholder="和门店一起得出的结论/决策" />
        </el-form-item>
        <el-form-item label="明日计划">
          <el-input v-model="dayLogDlg.form.next_actions" type="textarea" :rows="2" placeholder="明天要做的事" />
        </el-form-item>

        <!-- 第3-5关 Checklist 勾选 -->
        <el-divider content-position="left">✅ 执案现场 Checklist（完成即勾）</el-divider>
        <div v-for="group in dayLogGates" :key="group.gate" class="gate-section">
          <div class="gate-title">第{{ group.gate }}关：{{ group.gate_name }}</div>
          <div v-for="(item, idx) in group.items" :key="idx" class="checklist-row">
            <el-checkbox v-model="item.done">{{ item.item }}</el-checkbox>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dayLogDlg.vis = false">取消</el-button>
        <el-button type="primary" @click="doDayLog">保存日志</el-button>
      </template>
    </el-dialog>

    <!-- 提交执案报告（含文件） -->
    <el-dialog v-model="reportDlg.vis" title="提交执案报告" width="660px" top="5vh">
      <el-form :model="reportDlg.form" label-width="110px">
        <el-form-item label="执案总结" required>
          <el-input v-model="reportDlg.form.summary" type="textarea" :rows="4" placeholder="本次执案的核心成果概述" />
        </el-form-item>
        <el-form-item label="核心问题">
          <el-input v-model="reportDlg.form.problems_found" type="textarea" :rows="3" placeholder="门店存在的主要问题" />
        </el-form-item>
        <el-form-item label="搭建方案">
          <el-input v-model="reportDlg.form.solutions_built" type="textarea" :rows="3" placeholder="为门店搭建的系统/框架/SOP" />
        </el-form-item>
        <el-form-item label="跟进计划">
          <el-input v-model="reportDlg.form.follow_up_plan" type="textarea" :rows="2" placeholder="后续2-3次跟进回访的计划" />
        </el-form-item>
        <el-form-item label="建议下次">
          <el-input v-model="reportDlg.form.next_visit_suggestion" placeholder="如：建议1个月后回访复盘" />
        </el-form-item>

        <el-divider content-position="left">📄 文件上传</el-divider>

        <el-form-item label="会议记录文件">
          <el-input v-model="reportDlg.form.meeting_records" type="textarea" :rows="2"
            placeholder="会议记录文件URL（多个用换行分隔）&#10;后续接入文件上传组件" />
        </el-form-item>
        <el-form-item label="客户方案文件">
          <el-input v-model="reportDlg.form.deliverables" type="textarea" :rows="2"
            placeholder="交付给客户的方案文件URL（多个用换行分隔）&#10;如：品项框架.xlsx、SOP手册.pdf" />
        </el-form-item>
        <el-form-item label="其他附件">
          <el-input v-model="reportDlg.form.attachments" type="textarea" :rows="2" placeholder="其他附件URL" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportDlg.vis = false">取消</el-button>
        <el-button type="success" @click="doReport">提交报告 · 进入跟进阶段</el-button>
      </template>
    </el-dialog>

    <!-- 执案后跟进会议 -->
    <el-dialog v-model="followupDlg.vis" title="📋 执案后跟进会议记录" width="620px" top="5vh">
      <el-form :model="followupDlg.form" label-width="110px">
        <el-form-item label="第几次跟进" required>
          <el-radio-group v-model="followupDlg.form.meeting_number">
            <el-radio-button :value="1">第1次</el-radio-button>
            <el-radio-button :value="2">第2次</el-radio-button>
            <el-radio-button :value="3">第3次</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="会议日期">
          <el-date-picker v-model="followupDlg.form.meeting_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="会议类型">
          <el-radio-group v-model="followupDlg.form.meeting_type">
            <el-radio-button value="online">线上会议</el-radio-button>
            <el-radio-button value="onsite">线下回访</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="会议内容" required>
          <el-input v-model="followupDlg.form.content" type="textarea" :rows="4"
            placeholder="本次跟进会议讨论了什么？执案效果如何？" />
        </el-form-item>
        <el-form-item label="执案数据回顾">
          <el-input v-model="followupDlg.form.data_review" type="textarea" :rows="3"
            placeholder="📊 执案后数据变化：&#10;如：客单价提升15%，新客到店率+20%，品项渗透率变化等" />
        </el-form-item>
        <el-form-item label="新发现问题">
          <el-input v-model="followupDlg.form.issues" type="textarea" :rows="2"
            placeholder="跟进中发现的新问题" />
        </el-form-item>
        <el-form-item label="跟进行动项">
          <el-input v-model="followupDlg.form.actions" type="textarea" :rows="2"
            placeholder="下一步需要执行的动作" />
        </el-form-item>
        <el-form-item label="会议记录文件">
          <el-input v-model="followupDlg.form.meeting_record_file"
            placeholder="会议记录文件URL（后续接入上传组件）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="followupDlg.vis = false">取消</el-button>
        <el-button type="warning" @click="doFollowup">保存跟进记录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';

const route = useRoute();
const id = Number(route.params.id);
const loading = ref(false);
const wf = ref<any>({});
const steps = ref<any[]>([]);
const can = ref<any>({});
const consultants = ref<any[]>([]);

const currentStep = computed(() => steps.value.findIndex((s: any) => s.current));

async function load() {
  loading.value = true;
  try {
    const r: any = await API.serviceOrderWorkflow(id);
    const d = r?.data || r;
    wf.value = d;
    steps.value = d.steps || [];
    can.value = d.can_advance || {};
    // 如果后端返回了checklist模板，合并到本地
    if (d.checklist_template?.length && !checklistLoaded.value) {
      prepareChecklist.value = d.checklist_template.map((c: any) => ({ ...c }));
      checklistLoaded.value = true;
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || '加载失败');
  } finally {
    loading.value = false;
  }
}

async function loadConsultants() {
  try {
    const r: any = await API.get('/admin/consultants');
    consultants.value = r?.data || r || [];
  } catch (_) {}
}

// ----- Edit Info (不改流程，只改基本信息) -----
const editDlg = reactive({ vis: false, form: { service_id: null as number | null, member_id: null as number | null, consultant_id: null as number | null, assistant_id: null as number | null, appoint_date: '', appoint_time: '', store_name: '', store_address: '', visit_number: 1, remark: '' } });
const serviceList = ref<any[]>([]);
const memberList = ref<any[]>([]);

async function loadServices() {
  try {
    const r: any = await API.serviceList();
    serviceList.value = r?.data || r || [];
  } catch (_) {}
}
async function loadMembers() {
  try {
    const r: any = await API.memberList({ page: 1, size: 100 });
    const d = r?.data || r;
    memberList.value = d?.items || (Array.isArray(d) ? d : []);
  } catch (_) {}
}
function showEditInfo() {
  const o = wf.value.order || {};
  editDlg.form = {
    service_id: o.service_id || null,
    member_id: o.member_id || null,
    consultant_id: o.consultant_id || null,
    assistant_id: o.assistant_id || null,
    appoint_date: o.appoint_date || '',
    appoint_time: o.appoint_time || '',
    store_name: o.store_name || '',
    store_address: o.store_address || '',
    visit_number: o.visit_number || 1,
    remark: o.remark || '',
  };
  loadConsultants();
  loadServices();
  loadMembers();
  editDlg.vis = true;
}
async function doEditInfo() {
  try {
    // el-select clearable 清空后值可能是 '' 或 undefined，需转为 null 让后端识别
    const payload = { ...editDlg.form };
    if (!payload.assistant_id) payload.assistant_id = null;
    if (!payload.member_id) payload.member_id = null;
    if (!payload.service_id) payload.service_id = null;
    if (!payload.consultant_id) payload.consultant_id = null;
    await API.serviceOrderUpdate(id, payload);
    ElMessage.success('工单信息已更新');
    editDlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '更新失败'); }
}

// ----- Confirm -----
const confirmDlg = reactive({ vis: false, form: { consultant_id: 0, assistant_id: null as number | null, appoint_date: '', appoint_time: '', store_name: '', store_address: '', remark: '' } });
function showConfirm() {
  const o = wf.value.order || {} as any;
  const m = wf.value.member || {} as any;
  confirmDlg.form = {
    consultant_id: wf.value.consultant?.id || 0,
    assistant_id: wf.value.assistant?.id || null,
    appoint_date: o.appoint_date || '',
    appoint_time: o.appoint_time || '10:00-19:00',
    store_name: o.store_name || m.enterprise_name || '',
    store_address: o.store_address || m.city || '',
    remark: o.remark || '',
  };
  loadConsultants();
  confirmDlg.vis = true;
}
async function doConfirm() {
  if (!confirmDlg.form.consultant_id) return ElMessage.warning('请选择老师');
  try {
    await API.serviceOrderConfirm(id, confirmDlg.form);
    ElMessage.success('工单已确认，已通知老师');
    confirmDlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}

// ----- Accept -----
const acceptDlg = reactive({ vis: false, form: { accept_note: '' } });
function showAccept() { acceptDlg.form.accept_note = ''; acceptDlg.vis = true; }
async function doAccept() {
  try {
    await API.serviceOrderAccept(id, acceptDlg.form);
    ElMessage.success('已接单，已通知销售老师');
    acceptDlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}

// ----- Prepare (五关Checklist + 订票信息) -----
const prepareDlg = reactive({ vis: false, form: { prepare_summary: '', travel_info: '' } });
const checklistLoaded = ref(false);
const prepareChecklist = ref<{gate: number; gate_name: string; item: string; done: boolean}[]>([
  // 五关Checklist预设
  { gate: 1, gate_name: "对接确认（出发前3天）", item: "已联系带队老师，确认到达时间和地点", done: false },
  { gate: 1, gate_name: "对接确认（出发前3天）", item: "已明确本次执案自己的具体职责（逐条列出）", done: false },
  { gate: 1, gate_name: "对接确认（出发前3天）", item: "已知道本次执案的核心目标是什么", done: false },
  { gate: 1, gate_name: "对接确认（出发前3天）", item: "已了解客户基本情况（门店规模/老板姓名/上次执案遗留问题）", done: false },
  { gate: 2, gate_name: "材料准备（出发前1天）", item: "会议记录模板已准备好（不是到了再找）", done: false },
  { gate: 2, gate_name: "材料准备（出发前1天）", item: "执案日程表已收到并读完", done: false },
  { gate: 2, gate_name: "材料准备（出发前1天）", item: "团队行程已同步（谁几点到/住哪个酒店/怎么集合）", done: false },
  { gate: 2, gate_name: "材料准备（出发前1天）", item: "自己的住宿已确认", done: false },
  { gate: 3, gate_name: "现场规范（执案当天）", item: "到店第一件事：找带队老师报到，确认今天任务分工", done: false },
  { gate: 3, gate_name: "现场规范（执案当天）", item: "会议记录当场记，当天整理完发带队老师审核", done: false },
  { gate: 3, gate_name: "现场规范（执案当天）", item: "文案/输出物当天完成，不过夜", done: false },
  { gate: 3, gate_name: "现场规范（执案当天）", item: "有不懂的当场问，不猜，不扛", done: false },
  { gate: 4, gate_name: "团队协作（全程）", item: "有集体动作（敬酒/发言/表态）前先跟团队沟通，不单独行动", done: false },
  { gate: 4, gate_name: "团队协作（全程）", item: "团队所有人行程变化第一时间同步群里", done: false },
  { gate: 4, gate_name: "团队协作（全程）", item: "客户面前展示统一形象，有分歧私下解决", done: false },
  { gate: 5, gate_name: "收尾（执案结束当天）", item: "会议记录已发带队老师", done: false },
  { gate: 5, gate_name: "收尾（执案结束当天）", item: "执案总结已完成（不少于300字，当天发）", done: false },
  { gate: 5, gate_name: "收尾（执案结束当天）", item: "下次执案待解决问题已记录", done: false },
  { gate: 5, gate_name: "收尾（执案结束当天）", item: "已向带队老师确认下次执案时间", done: false },
]);

const uniqueGates = computed(() => [...new Set(prepareChecklist.value.map(c => c.gate))].sort());
const gateNames: Record<number, string> = {
  1: '对接确认（出发前3天）',
  2: '材料准备（出发前1天）',
  3: '现场规范（执案当天）',
  4: '团队协作（全程）',
  5: '收尾（执案结束当天）',
};

const newCheckItem = ref('');
function addCheckItem() {
  if (newCheckItem.value.trim()) {
    prepareChecklist.value.push({ gate: 6, gate_name: '自定义', item: newCheckItem.value.trim(), done: false });
    newCheckItem.value = '';
  }
}
function showPrepare() {
  prepareDlg.form = { prepare_summary: '', travel_info: '' };
  // 重置checklist
  prepareChecklist.value.forEach(c => c.done = false);
  prepareDlg.vis = true;
}
async function doPrepare() {
  if (!prepareDlg.form.prepare_summary) return ElMessage.warning('请填写准备摘要');
  try {
    await API.serviceOrderPrepare(id, {
      ...prepareDlg.form,
      checklist: JSON.stringify(prepareChecklist.value),
    });
    ElMessage.success('执案准备已提交');
    prepareDlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}

// ----- Start -----
const startDlg = reactive({ vis: false, form: { actual_start_date: '', participants: '', agenda: '' } });
function showStart() {
  startDlg.form = { actual_start_date: new Date().toISOString().split('T')[0], participants: '', agenda: 'Day1: 现状诊断研讨\nDay2: 系统框架共建研讨\nDay3: 启动会（视情况）' };
  startDlg.vis = true;
}
async function doStart() {
  try {
    await API.serviceOrderStart(id, startDlg.form);
    ElMessage.success('执案已开始，排期已自动创建');
    startDlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}

// ----- Day Log -----
const dayLogDlg = reactive({ vis: false, form: { day_number: 1, stage: '现状诊断', content: '', findings: '', decisions: '', next_actions: '' } });

// 第3-5关 Checklist（执案现场勾选）
const dayLogChecklist = ref<{gate: number; gate_name: string; item: string; done: boolean}[]>([]);
const dayLogGates = computed(() => {
  const map = new Map<number, { gate: number; gate_name: string; items: any[] }>();
  for (const it of dayLogChecklist.value) {
    if (!map.has(it.gate)) map.set(it.gate, { gate: it.gate, gate_name: it.gate_name, items: [] });
    map.get(it.gate)!.items.push(it);
  }
  return Array.from(map.values()).sort((a, b) => a.gate - b.gate);
});

function initDayLogChecklist() {
  // 取第3-5关，优先用后端模板，fallback到本地
  const template = (wf.value.checklist_template || []).filter((c: any) => c.gate >= 3);
  const finalTemplate = template.length ? template : prepareChecklist.value.filter(c => c.gate >= 3);
  // 找历史日志中已勾选的checklist
  const doneSets = new Set<string>();
  for (const log of (wf.value.logs || [])) {
    if (log.log_type === 'daily') {
      const parsed = parseChecklist(log.content);
      if (parsed) {
        for (const c of parsed) {
          if (c.done) doneSets.add(`${c.gate}-${c.item}`);
        }
      }
    }
  }
  dayLogChecklist.value = finalTemplate.map((c: any) => ({
    ...c,
    done: doneSets.has(`${c.gate}-${c.item}`),
  }));
}

function showDayLog() {
  const existingDays = (wf.value.logs || []).filter((l: any) => l.log_type === 'daily').map((l: any) => l.day_number);
  const nextDay = existingDays.length ? Math.max(...existingDays) + 1 : 1;
  dayLogDlg.form = { day_number: Math.min(nextDay, 3), stage: nextDay === 1 ? '现状诊断' : nextDay === 2 ? '框架共建' : '启动会', content: '', findings: '', decisions: '', next_actions: '' };
  initDayLogChecklist();
  dayLogDlg.vis = true;
}
async function doDayLog() {
  if (!dayLogDlg.form.content) return ElMessage.warning('请填写执案内容');
  // 把Checklist状态附加到内容后面
  const checkedItems = dayLogChecklist.value.filter(c => c.done || c.gate >= 3);
  const payload: any = { ...dayLogDlg.form };
  if (checkedItems.length) {
    payload.content = payload.content + '\n\n📋 执案现场 Checklist：' + JSON.stringify(checkedItems);
  }
  try {
    await API.serviceOrderDayLog(id, payload);
    ElMessage.success(`Day${dayLogDlg.form.day_number} 日志已保存`);
    dayLogDlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}

// ----- Report (含文件) -----
const reportDlg = reactive({ vis: false, form: { summary: '', problems_found: '', solutions_built: '', follow_up_plan: '', next_visit_suggestion: '', meeting_records: '', deliverables: '', attachments: '' } });
function showReport() {
  reportDlg.form = { summary: '', problems_found: '', solutions_built: '', follow_up_plan: '', next_visit_suggestion: '', meeting_records: '', deliverables: '', attachments: '' };
  reportDlg.vis = true;
}
async function doReport() {
  if (!reportDlg.form.summary) return ElMessage.warning('请填写执案总结');
  try {
    await API.serviceOrderReport(id, reportDlg.form);
    ElMessage.success('执案报告已提交，进入跟进阶段');
    reportDlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}

// ----- Followup -----
const followupDlg = reactive({ vis: false, form: { meeting_number: 1, meeting_date: '', meeting_type: 'online', content: '', data_review: '', issues: '', actions: '', meeting_record_file: '' } });
function showFollowup() {
  const existingFollowups = (wf.value.logs || []).filter((l: any) => l.log_type === 'followup').length;
  followupDlg.form = {
    meeting_number: existingFollowups + 1,
    meeting_date: new Date().toISOString().split('T')[0],
    meeting_type: 'online',
    content: '', data_review: '', issues: '', actions: '', meeting_record_file: '',
  };
  followupDlg.vis = true;
}
async function doFollowup() {
  if (!followupDlg.form.content) return ElMessage.warning('请填写会议内容');
  try {
    await API.serviceOrderFollowup(id, followupDlg.form);
    ElMessage.success(`第${followupDlg.form.meeting_number}次跟进已记录`);
    followupDlg.vis = false;
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}

// ----- Complete / Cancel -----
async function doComplete() {
  await ElMessageBox.confirm('确认整体执案结束？套餐次数将自动扣减，并通知会员评价。', '整体执案结束');
  try {
    await API.serviceOrderComplete(id);
    ElMessage.success('整体执案结束');
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}
async function doCancel() {
  await ElMessageBox.confirm('确认取消该工单？', '取消工单', { type: 'warning' });
  try {
    await API.serviceOrderCancel(id);
    ElMessage.success('工单已取消');
    load();
  } catch (e: any) { ElMessage.error(e?.msg || e?.detail || '操作失败'); }
}

// ----- Utils -----
// ---- Checklist 解析与分组 ----
function parseChecklist(content: string): any[] | null {
  if (!content) return null;
  const match = content.match(/\[\s*\{.*?"gate".*?\}\s*\]/s);
  if (!match) return null;
  try {
    const arr = JSON.parse(match[0]);
    if (Array.isArray(arr) && arr.length && arr[0].gate !== undefined) return arr;
  } catch (_) {}
  return null;
}
function groupChecklist(items: any[]): { gate: number; gate_name: string; items: any[] }[] {
  const map = new Map<number, { gate: number; gate_name: string; items: any[] }>();
  for (const it of items) {
    if (!map.has(it.gate)) map.set(it.gate, { gate: it.gate, gate_name: it.gate_name, items: [] });
    map.get(it.gate)!.items.push(it);
  }
  return Array.from(map.values()).sort((a, b) => a.gate - b.gate);
}
function extractTextLines(content: string): string[] {
  // 提取Checklist JSON之前的文本行（准备摘要、订票信息）
  const jsonStart = content.indexOf('[{');
  const textPart = jsonStart > 0 ? content.substring(0, jsonStart) : content;
  return textPart.split('\n').map(l => l.replace(/^\ud83d\udccb\s*五关Checklist：\s*$/, '').trim()).filter(l => l.length > 0);
}

function statusType(s: string): any {
  return ({ pending: 'warning', confirmed: 'primary', accepted: '', preparing: 'warning',
    in_progress: '', reporting: 'success', follow_up: 'warning', completed: 'success', cancelled: 'info' } as any)[s] || '';
}
function logColor(t: string) {
  return ({ system: '#909399', daily: '#c9a96e', report: '#67c23a', prepare: '#e6a23c', followup: '#409eff' } as any)[t] || '#409eff';
}
function logTagType(t: string): any {
  return ({ system: 'info', daily: 'warning', report: 'success', prepare: '', followup: 'primary' } as any)[t] || '';
}

onMounted(() => { load(); loadConsultants(); });
</script>

<style scoped>
.page { padding: 20px; max-width: 1000px; }
.card { margin-bottom: 16px; }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.order-no { margin-left: 12px; color: #999; font-family: monospace; font-size: 14px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.card-head { display: flex; justify-content: space-between; align-items: center; }

.log-item { padding: 4px 0; }
.log-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.day-badge { background: #c9a96e; color: #fff; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; }
.log-content { color: #333; line-height: 1.6; white-space: pre-wrap; }
.log-sub { color: #666; font-size: 13px; margin-top: 4px; line-height: 1.5; }

.rating-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.stars { color: #c9a96e; font-size: 24px; letter-spacing: 4px; }
.rating-num { color: #999; }
.comment { color: #333; }

/* 五关Checklist样式 */
.gate-section { margin-bottom: 16px; }
.gate-title { font-weight: 600; color: #333; margin-bottom: 8px; padding: 6px 12px; background: #f5f7fa; border-radius: 4px; border-left: 3px solid #c9a96e; }
.checklist-row { margin-bottom: 4px; padding-left: 12px; }
.checklist-add { margin-top: 8px; }

/* 日志中Checklist渲染 */
.checklist-display { margin-top: 4px; }
.checklist-gate { margin-bottom: 12px; }
.gate-label { font-weight: 600; font-size: 13px; color: #333; padding: 4px 10px; background: #f5f7fa; border-radius: 4px; border-left: 3px solid #c9a96e; margin-bottom: 6px; }
.checklist-item { display: flex; align-items: flex-start; gap: 6px; padding: 3px 0 3px 12px; font-size: 13px; color: #555; line-height: 1.5; }
.checklist-item.done { color: #999; }
.check-icon { flex-shrink: 0; }
</style>
