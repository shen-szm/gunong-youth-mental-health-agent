<template>
  <div class="teacher-page">
    <aside class="teacher-sidebar" aria-label="教师工作台导航">
      <div class="teacher-brand">
        <span aria-hidden="true">咕</span>
        <div><strong>咕哝教师端</strong><small>校园支持数字员工</small><div class="teacher-brand-meta"><em>{{ userStore.isSuperAdmin ? '管理员教师' : '普通教师' }}</em><span class="teacher-version">v{{ teacherVersion }}</span></div></div>
      </div>
      <nav ref="teacherNav" class="teacher-nav" data-guide="tabs">
        <button
          v-for="item in visibleNavItems"
          :key="item.id"
          :data-nav-id="item.id"
          type="button"
          :class="{ active: tab === item.id }"
          :aria-current="tab === item.id ? 'page' : undefined"
          @click="openTab(item.id)"
        >
          <span aria-hidden="true"><UiIcon class="teacher-nav-icon" :name="item.id" /><span class="teacher-legacy-icon">{{ item.icon }}</span></span>
          <span>{{ item.label }}</span>
          <em v-if="item.id === 'approvals' && pendingApprovalCount">{{ pendingApprovalCount }}</em>
        </button>
      </nav>
      <small class="teacher-nav-hint">左右滑动查看更多职责入口</small>
      <div class="teacher-sidebar-footer">
        <button type="button" class="teacher-user" title="更换头像" @click="showAvatarPicker = true">
          <span class="teacher-user-avatar">
            <img v-if="avatarSrc" :src="avatarSrc" alt="我的头像" />
            <template v-else>{{ (userStore.nickname || '师')[0] }}</template>
          </span>
          <span class="teacher-user-name">{{ userStore.nickname || '教师' }}</span>
        </button>
        <AvatarPickerModal
          v-if="showAvatarPicker"
          :nickname="userStore.nickname"
          @close="showAvatarPicker = false"
          @change="src => { avatarSrc = src }"
        />
        <span :class="['role-badge', userStore.isSuperAdmin ? 'admin' : 'teacher']">{{ userStore.isSuperAdmin ? '管理员教师' : '普通教师' }}</span>
        <button type="button" @click="handleBack">返回学生端</button>
        <button type="button" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <div class="teacher-shell">
      <header class="teacher-topbar">
        <div>
          <p>教师支持工作台 / {{ currentTabMeta.group }}</p>
          <h1>{{ currentTabMeta.label }}</h1>
        </div>
        <label class="teacher-search">
          <span class="sr-only">搜索学生</span>
          <input ref="teacherSearchInput" v-model="teacherQuery" type="search" placeholder="搜索当前职责范围内的学生" />
          <kbd>Ctrl/⌘ K</kbd>
        </label>
      </header>

      <div v-if="error" class="error-screen">
        <p>{{ error }}</p>
        <button class="primary-btn" @click="loadAll">重新加载</button>
      </div>

      <template v-else>
        <main class="workspace">
          <TeacherVerification v-if="tab === 'benchmark'" />
          <TeacherTodayDashboard
            v-if="tab === 'today'"
            :warnings="filteredWarnings"
            :students="filteredStudents"
            :approvals="accessRequests"
            :super-admin="userStore.isSuperAdmin"
            :refreshing="workspaceRefreshing"
            @refresh="refreshWorkspace"
            @open-tab="openTab"
            @open-item="openTodayItem"
            @open-student="openTodayStudent"
          />
        <section v-if="tab === 'cases'" class="panel case-workbench">
          <div class="panel-title">
            <div>
              <span class="section-kicker">端到端任务入口</span>
              <h3>校园心理支持工单</h3>
              <p>普通教师需先申请并获管理员教师审批；管理员教师可直接查看。每次查看原文都会留下审计记录。</p>
            </div>
            <span :class="['role-badge', userStore.isSuperAdmin ? 'admin' : 'teacher']">{{ userStore.isSuperAdmin ? '管理员教师 · 可直达' : '普通教师 · 审批后查看' }}</span>
          </div>

          <div class="case-overview" aria-label="工单权限概览">
            <div class="overview-head">
              <span>权限状态构成</span>
              <em>{{ filteredStudents.length }} 名支持对象</em>
            </div>
            <div v-if="filteredStudents.length" class="overview-bar" role="img" :aria-label="caseAccessAria">
              <span
                v-for="band in caseAccessBands"
                v-show="band.count"
                :key="band.key"
                :class="['overview-seg', 'access-' + band.key]"
                :style="{ flexGrow: band.count }"
                :title="`${band.label} ${band.count} 人 · ${band.pct}%`"
              />
            </div>
            <p v-else class="overview-empty">当前筛选下暂无支持对象。</p>
            <ul class="overview-legend">
              <li v-for="band in caseAccessBands" :key="band.key">
                <i :class="'access-' + band.key" aria-hidden="true" />
                <span>{{ band.label }}</span>
                <strong>{{ band.count }}</strong>
                <em>{{ band.pct }}%</em>
              </li>
            </ul>
          </div>

          <div class="case-layout">
            <div class="case-roster" aria-label="学生支持对象列表">
              <button v-for="student in filteredStudents" :key="student.id" :aria-pressed="caseStudent?.id === student.id" :class="['case-student', { selected: caseStudent?.id === student.id }]" @click="chooseCaseStudent(student)">
                <span class="avatar">{{ firstChar(studentName(student)) }}</span>
                <span class="case-student-main"><strong>{{ studentName(student) }}</strong><small>{{ riskText(student.risk_level) }} · {{ student.mood_count }} 条自愿记录<span v-if="student.screening"> · 筛查 {{ student.screening.band_label }} {{ student.screening.total_score }}/27</span></small></span>
                <em :class="['access-pill', student.access?.status]">{{ student.access?.label }}</em>
              </button>
              <p v-if="!filteredStudents.length" class="empty-state">当前筛选下暂无支持工单。</p>
            </div>

            <article class="case-stage" v-if="caseStudent">
              <div class="case-stage-head">
                <div><span class="section-kicker">{{ studentName(caseStudent) }}</span><h4>{{ caseStageTitle }}</h4></div>
                <span class="status-pill">{{ caseStudent.access?.label }}</span>
              </div>

              <section class="student-ai-authorization" aria-labelledby="student-ai-authorization-title">
                <div>
                  <span class="section-kicker">学生端 Agent 数据处理</span>
                  <h4 id="student-ai-authorization-title">学生端受约束模型对话全局启用</h4>
                  <p>学生无需逐次申请或等待教师开通。对话原文会发送给平台接入的 DeepSeek 模型，用于生成本轮回应和本次小结；安全分流、危机判断与风险等级仍由本地规则强制裁决。</p>
                  <small>平台运营方仍须完成适用的机构、监护与隐私治理，不由学生在聊天中重复操作。</small>
                </div>
              </section>

              <div v-if="['not_requested', 'rejected', 'expired', 'revoked'].includes(caseStudent.access?.status)" class="access-application">
                <p>请说明查看目的。批准后可在7天内查看“审批时点之前”的该学生近30天倾诉和情绪记录原文；之后新增内容需要重新申请。</p>
                <label><span>申请理由</span><textarea v-model="accessReason" placeholder="例如：近期到校困难增多，需要结合自愿记录制定一次线下关怀计划。"></textarea></label>
                <button class="primary-btn" :disabled="accessSubmitting || accessReason.trim().length < 10" @click="submitAccessRequest">{{ accessSubmitting ? '正在提交…' : '提交个案查看申请' }}</button>
              </div>

              <div v-else-if="caseStudent.access?.status === 'pending'" class="approval-waiting">
                <strong>申请已进入审批队列</strong>
                <p>审批前不展示个案摘要或原文。管理员教师处理后，刷新列表即可继续。</p>
                <button class="ghost-btn" @click="loadStudents">刷新审批状态</button>
              </div>

              <div v-else class="authorized-case">
                <div class="privacy-notice"><strong>授权范围：近30天原文</strong><span>仅用于本工单，不得传播，不得作为诊断依据。所有敏感访问均记录审计。</span></div>
                <TeacherCaseTaskPanel
                  :key="`${userStore.userId}:${caseStudent.id}:${caseStudent.access?.request_id || 0}`"
                  :account-id="Number(userStore.userId)"
                  :student-id="caseStudent.id"
                  :student-label="studentName(caseStudent)"
                  :request-id="caseStudent.access?.request_id || null"
                />
                <button class="primary-btn" :disabled="contextLoading" @click="loadCaseContext">{{ contextLoading ? '数字员工正在执行…' : (workProduct ? '重新执行工单' : '执行支持工单') }}</button>

                <section v-if="contextLoading" class="desktop-case-agent-live" role="status" aria-live="polite" aria-label="数字员工当前执行进度">
                  <div><span class="section-kicker">服务端执行状态</span><h4>正在核验权限并生成支持工单</h4><p>接口返回前不预先宣称任何 Agent 步骤已完成；完成后会展示服务端返回的可核验流水线。</p></div>
                  <div class="case-processing-state"><i aria-hidden="true">•</i><span><strong>本次工单处理中</strong><small>等待真实接口结果</small></span></div>
                </section>

                <template v-if="workProduct">
                  <div ref="caseResultHeading" class="case-command-head" tabindex="-1">
                    <div><span class="section-kicker">{{ workProduct.case_id }}</span><h4>工单协作画布</h4></div>
                    <div class="case-result-badges"><span class="agent-source-badge">{{ teacherGenerationLabel }}</span><span :class="['risk-decision', workProduct.risk]">{{ workProduct.risk === 'urgent' ? '立即处置' : workProduct.risk === 'professional' ? '需要专业支持' : workProduct.risk === 'watch' ? '持续关注' : '常规支持' }}</span></div>
                  </div>
                  <div class="agent-pipeline" aria-label="数字员工执行进度">
                    <article v-for="(step, index) in workProduct.pipeline" :key="step.name" :class="step.status">
                      <span>{{ String(index + 1).padStart(2, '0') }}</span><div><strong>{{ step.name }}</strong><small>{{ step.result }}</small></div><em>{{ pipelineStatusText(step.status) }}</em>
                    </article>
                  </div>
                  <section v-if="agentHandoff" class="agent-handoff-ledger" aria-labelledby="teacher-agent-handoff-title">
                    <header>
                      <div><span class="section-kicker">结构化 Agent 接力</span><h4 id="teacher-agent-handoff-title">最近任务与核验结果</h4></div>
                      <p aria-label="Agent 任务核验汇总"><strong>{{ agentHandoff.verified_count || 0 }}</strong><span>/ {{ agentHandoff.run_count || 0 }} 次通过核验</span></p>
                    </header>
                    <p class="agent-handoff-boundary">仅展示授权截止时间内的去标识化任务成果；结构化接力不等于心理诊断，也不表示教师已完成线下行动。</p>
                    <ol v-if="recentAgentHandoffs.length">
                      <li v-for="run in recentAgentHandoffs" :key="run.run_code">
                        <div class="agent-handoff-meta">
                          <code>{{ run.run_code }}</code>
                          <time v-if="run.completed_at" :datetime="run.completed_at">{{ formatDateTime(run.completed_at) }}</time>
                          <span :class="`is-${handoffVerificationTone(run.verification?.status || run.status)}`">{{ handoffVerificationLabel(run.verification?.status || run.status) }}</span>
                        </div>
                        <div class="agent-handoff-result">
                          <strong>{{ run.artifact?.title || run.task_contract?.objective || '结构化支持任务' }}</strong>
                          <p v-if="run.artifact?.outcome || run.task_contract?.objective">{{ run.artifact?.outcome || run.task_contract?.objective }}</p>
                        </div>
                        <dl>
                          <div v-if="run.artifact?.next_action"><dt>建议下一步</dt><dd>{{ run.artifact.next_action }}</dd></div>
                          <div v-if="run.artifact?.next_owner"><dt>下一责任人</dt><dd>{{ handoffOwnerLabel(run.artifact.next_owner) }}</dd></div>
                          <div><dt>风险分流</dt><dd>{{ handoffRiskLabel(run.risk_level) }}</dd></div>
                        </dl>
                      </li>
                    </ol>
                    <p v-else class="agent-handoff-empty">授权范围内暂无可接力的已保存 Agent 任务。</p>
                  </section>
                  <div class="work-product-grid">
                    <section class="evidence-brief"><span class="section-kicker">观察摘要</span><h4>{{ workProduct.observation.headline }}</h4><p>{{ workProduct.observation.latest_signal }}</p><div class="evidence-links"><button v-for="id in workProduct.observation.evidence_ids" :key="id" type="button" @click="scrollToEvidence(id)">{{ id }}</button></div></section>
                    <section class="decision-brief"><span class="section-kicker">安全裁决</span><h4>教师需要确认的下一步</h4><p>{{ workProduct.decision }}</p><div class="evidence-links"><button v-for="id in workProduct.decision_evidence_ids" :key="id" type="button" @click="scrollToEvidence(id)">{{ id }}</button></div><ul><li v-for="rule in workProduct.guardrails" :key="rule">{{ rule }}</li></ul></section>
                  </div>
                  <section v-if="workProduct.assessment_summary" class="assessment-brief">
                    <div class="original-list-head"><div><span class="section-kicker">学生主动自评</span><h4>近两周支持需求观察</h4></div><small>{{ formatDateTime(workProduct.assessment_summary.created_at) }}</small></div>
                    <p class="assessment-emotion">{{ workProduct.assessment_summary.emotion_summary }}</p>
                    <div class="assessment-domain-grid">
                      <article v-for="domain in workProduct.assessment_summary.domains" :key="domain.id"><span>{{ domain.label }}</span><strong>{{ domain.level }}</strong><p>{{ domain.observation }}</p></article>
                    </div>
                    <ul><li v-for="need in workProduct.assessment_summary.support_needs" :key="need">{{ need }}</li></ul>
                    <small>这是待专业人员审核的支持决策草案，不是经验证量表或医学诊断；“需要专业支持”须由校内心理教师或正规医疗机构进一步评估。</small>
                  </section>
                  <section v-if="workProduct.screening_summary" class="assessment-brief screening-brief">
                    <div class="original-list-head"><div><span class="section-kicker">标准筛查</span><h4>最近一次筛查结果</h4></div><small>{{ formatDateTime(workProduct.screening_summary.created_at) }}</small></div>
                    <div class="profile-metrics screening-metrics">
                      <span>分级 <b>{{ workProduct.screening_summary.band_label }}</b></span>
                      <span>总分 <b>{{ workProduct.screening_summary.total_score }}/27</b></span>
                      <span>第9题安全标记 <b>{{ workProduct.screening_summary.safety_active ? '待线下核实' : workProduct.screening_summary.item9_positive ? '已完成安全交接' : '无应答' }}</b></span>
                    </div>
                    <small>PHQ-9 是筛查工具，不是诊断；总分只用于支持分流，不得用于纪律处理或贴标签。教师只能看到分级、总分、填写时间和第9题安全标记，看不到每道题的答案。</small>
                  </section>
                  <section class="agent-conflict" v-if="workProduct.conflicts?.length">
                    <span class="section-kicker">明确分歧</span>
                    <div v-for="item in workProduct.conflicts" :key="item.topic"><strong>{{ item.topic }}</strong><p>{{ item.views.join(' / ') }}</p><em>裁决：{{ item.resolution }}</em><span class="evidence-links"><button v-for="id in item.evidence_ids" :key="id" type="button" @click="scrollToEvidence(id)">{{ id }}</button></span></div>
                  </section>
                  <section class="task-board">
                    <div class="original-list-head"><h4>可交付支持任务</h4><small>执行前由教师逐项确认</small></div>
                    <article v-for="(task, index) in workProduct.tasks" :key="task.title" class="task-row">
                      <span>{{ index + 1 }}</span><div><strong>{{ task.title }}</strong><small>{{ task.owner }} · {{ task.due }}</small><span class="evidence-links"><button v-for="id in task.evidence_ids" :key="id" type="button" @click="scrollToEvidence(id)">{{ id }}</button></span></div>
                      <button type="button" :disabled="taskDecisionLoading === index" :class="{ confirmed: confirmedTasks.includes(index) }" @click="toggleTask(index)">{{ taskDecisionLoading === index ? '记录中…' : confirmedTasks.includes(index) ? '已确认并审计' : '确认任务' }}</button>
                    </article>
                  </section>
                  <div class="original-list" tabindex="0" aria-label="经授权的学生证据列表，可上下滚动">
                      <div class="original-list-head"><h4>经授权的证据 · 可回溯</h4><small>{{ workProduct.records?.length || 0 }} 条 · 每次打开均已审计</small></div>
                    <article v-for="record in workProduct.records" :id="`evidence-${record.id}`" :key="record.id" class="original-record" tabindex="-1">
                      <div><span>{{ record.source }}</span><time :datetime="record.created_at">{{ formatDateTime(record.created_at) }}</time></div>
                      <p>{{ record.content }}</p>
                    </article>
                    <p v-if="!workProduct.records?.length" class="empty-state">近30天暂无可展示原文。</p>
                  </div>
                  <TeacherReviewReport
                    :report="reviewReport"
                    :loading="reviewReportLoading"
                    :decision-loading="reviewDecisionLoading"
                    @generate="generateReviewReport"
                    @decision="submitReviewDecision"
                    @download="downloadReviewReport"
                  />
                </template>
              </div>
              <p v-if="caseMessage" class="case-message" role="status">{{ caseMessage }}</p>
            </article>
            <div v-else class="empty-state tall">选择左侧学生，查看权限状态与下一步。</div>
          </div>
        </section>

        <section v-if="tab === 'approvals' && userStore.isSuperAdmin" class="panel approval-panel">
          <div class="panel-title"><div><span class="section-kicker">管理员教师</span><h3>个案查看审批</h3><p>核对申请目的和最小必要范围后决定是否开放近30天原文。</p></div><button class="ghost-btn" @click="loadAccessRequests">刷新申请</button></div>
          <div v-if="accessRequests.length" class="case-overview" aria-label="审批队列概览">
            <div class="overview-head"><span>审批队列构成</span><em>{{ accessRequests.length }} 条申请</em></div>
            <div class="overview-bar" role="img" :aria-label="approvalBandsAria">
              <span
                v-for="band in approvalBands"
                v-show="band.count"
                :key="band.key"
                :class="['overview-seg', band.key]"
                :style="{ flexGrow: band.count }"
                :title="`${band.label} ${band.count} 条`"
              />
            </div>
            <ul class="overview-legend">
              <li v-for="band in approvalBands" :key="band.key"><i :class="band.key" aria-hidden="true" /><span>{{ band.label }}</span><strong>{{ band.count }}</strong></li>
            </ul>
          </div>
          <p v-if="approvalLoading" class="empty-state" role="status">正在读取审批队列…</p>
          <p v-else-if="approvalError" class="approval-error" role="alert">{{ approvalError }} <button class="ghost-btn" @click="loadAccessRequests">重试</button></p>
          <div v-else class="approval-list">
            <article v-for="item in accessRequests" :key="item.id" class="approval-card">
              <div class="approval-meta"><span>{{ item.request_code }}</span><em :class="['access-pill', item.status]">{{ accessStatusText(item.status) }}</em></div>
              <h4>{{ cleanDisplayName(item.teacher_name) }} 申请查看 {{ cleanDisplayName(item.student_name) }}</h4>
              <p>{{ item.reason }}</p>
              <small>范围：审批时点之前近30天的倾诉和情绪记录原文；授权7天有效，新增内容不自动纳入</small>
              <div v-if="item.status === 'pending' && reviewTargetId !== item.id" class="approval-actions"><button class="primary-btn" @click="prepareReview(item, 'approved')">审核并批准</button><button class="danger-btn" @click="prepareReview(item, 'rejected')">审核并拒绝</button></div>
              <div v-else-if="item.status === 'pending'" class="review-confirm" role="group" :aria-label="pendingDecision === 'approved' ? '确认批准原文查看' : '确认拒绝原文查看'">
                <strong>{{ pendingDecision === 'approved' ? '确认开放固定原文范围' : '确认拒绝本次申请' }}</strong>
                <p v-if="pendingDecision === 'approved'">批准后，教师可在7天内查看审批时点之前的近30天原文；之后新增内容不会自动纳入。</p>
                <label><span>审批说明</span><textarea v-model="reviewNote" maxlength="300"></textarea></label>
                <div class="approval-actions"><button class="primary-btn" :disabled="reviewSubmitting || reviewNote.trim().length < 4" @click="reviewAccess(item, pendingDecision)">{{ reviewSubmitting ? '正在提交…' : '确认提交' }}</button><button class="ghost-btn" :disabled="reviewSubmitting" @click="cancelReview">取消</button></div>
              </div>
              <p v-else-if="item.review_note" class="review-note">审批备注：{{ item.review_note }}</p>
            </article>
            <p v-if="!accessRequests.length" class="empty-state">暂无申请工单。</p>
          </div>
        </section>

        <section v-if="tab === 'warnings'" class="panel warning-panel" data-guide="warning-list">
          <div class="panel-title">
            <div>
              <h3>支持提醒</h3>
              <p>按行动优先级和更新时间排序，先核实明确安全信号与尚未跟进的记录。这里是规则分流，不是诊断或概率。</p>
            </div>
            <button class="ghost-btn" @click="loadWarnings">刷新提醒</button>
          </div>

          <div class="warn-overview" aria-label="支持提醒可视化概览">
            <div class="warn-mix">
              <div class="overview-head">
                <span>风险分流</span>
                <em>{{ filteredWarnings.length }} 条待核实</em>
              </div>
              <div v-if="filteredWarnings.length" class="overview-bar" role="img" :aria-label="warningRiskAria">
                <span
                  v-for="band in warningBands"
                  v-show="band.count"
                  :key="band.key"
                  :class="['overview-seg', band.key]"
                  :style="{ flexGrow: band.count }"
                  :title="`${band.label} ${band.count} 条`"
                />
              </div>
              <p v-else class="overview-empty">当前筛选下暂无提醒。</p>
              <ul class="overview-legend">
                <li v-for="band in warningBands" :key="band.key">
                  <i :class="band.key" aria-hidden="true" />
                  <span>{{ band.label }}</span>
                  <strong>{{ band.count }}</strong>
                </li>
              </ul>
            </div>
            <div class="warn-week">
              <div class="overview-head">
                <span>近 7 天新增</span>
                <em>{{ warningWeekTotal }} 条</em>
              </div>
              <div class="overview-week-chart" role="img" :aria-label="`近 7 天每日新增提醒：${warningWeek.map(day => day.count + ' 条').join('、')}`">
                <div
                  v-for="(day, index) in warningWeek"
                  :key="day.key"
                  class="overview-week-col"
                  :class="{ today: index === 6 }"
                  :title="`${day.key} · ${day.count} 条`"
                >
                  <span class="overview-week-count">{{ day.count || '' }}</span>
                  <div class="overview-week-track">
                    <i :class="{ empty: !day.count }" :style="{ height: warningBarHeight(day.count) + '%' }" />
                  </div>
                  <span class="overview-week-day">{{ day.weekday }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="split-layout">
            <div class="warning-list">
              <button
                v-for="item in filteredWarnings"
                :key="item.id"
                :class="['warning-item', item.risk_level, { selected: selectedWarning?.id === item.id }]"
                @click="selectWarning(item)"
              >
                <span class="risk-dot"></span>
                <span class="warning-main">
                  <strong>{{ cleanDisplayName(item.student_name || item.nickname || ('学生 ' + item.student_id)) }}</strong>
                  <small>{{ item.reason || item.summary || '需要教师关注' }}</small>
                </span>
                <em>{{ riskText(item.risk_level) }}</em>
              </button>
              <p v-if="!filteredWarnings.length" class="empty-state">当前筛选下暂无支持提醒。</p>
            </div>

            <aside class="detail-card" data-guide="warning-detail"><span class="section-kicker">提醒详情</span>
              <template v-if="selectedWarning">
                <div class="detail-head">
                  <div>
                    <span class="status-pill">{{ riskText(selectedWarning.risk_level) }}</span>
                    <h4>{{ cleanDisplayName(selectedWarning.student_name || selectedWarning.nickname || '学生支持提醒') }}</h4>
                  </div>
                  <small>{{ selectedWarning.created_at?.slice?.(0, 16) || '刚刚更新' }}</small>
                </div>
                <p class="detail-copy">{{ selectedWarning.detail || selectedWarning.reason || selectedWarning.summary || '近期出现需要教师核对的主动记录，建议结合线下观察完成一次跟进。' }}</p>
                <div class="suggestion-box">
                  <strong>处理建议</strong>
                  <p>{{ selectedWarning.suggestion || '先查看近 7 天主动记录变化，再进行一次低压力的线下关怀并记录学生意愿。' }}</p>
                </div>
                <label class="handle-box">
                  <span>处理记录</span>
                  <textarea v-model="handleNote" placeholder="例如：已约学生课后沟通，持续观察三天。"></textarea>
                </label>
                <div class="detail-actions">
                  <button class="primary-btn" @click="handleWarning">标记已处理</button>
                  <button class="ghost-btn" @click="openStudentFromWarning">进入学生记录</button>
                </div>
              </template>
              <div v-else class="empty-state tall">点击左侧任意提醒，查看详情与处理建议。</div>
            </aside>
          </div>
        </section>

        <section v-if="tab === 'students' && userStore.isSuperAdmin" class="panel" data-guide="student-profile">
          <div class="panel-title">
            <div>
              <h3>学生支持记录</h3>
              <p>查看学生主动记录、标签变化与支持历史。这里只做描述性整理，不作心理测评或诊断。</p>
            </div>
            <button class="ghost-btn" @click="loadStudents">刷新学生</button>
          </div>
          <div class="student-grid">
            <button
              v-for="student in filteredStudents"
              :key="student.id"
              :class="['student-card', { selected: selectedStudent?.id === student.id }]"
              @click="selectStudent(student)"
            >
              <span class="avatar">{{ firstChar(studentName(student)) }}</span>
              <strong>{{ studentName(student) }}</strong>
              <small>{{ student.mood_count || 0 }} 条自愿记录 · {{ riskText(student.risk_level) }}</small>
              <em :class="['risk-label', student.risk_level || 'low']">{{ riskText(student.risk_level) }}</em>
            </button>
          </div>
          <article class="profile-card" v-if="selectedStudent">
            <div>
              <h4>{{ studentName(selectedStudent) }} 的关注摘要</h4>
              <p>{{ studentProfile.summary || '当前记录覆盖不足，建议结合学生意愿、近期主动记录与线下观察综合判断。' }}</p>
            </div>
            <div class="profile-metrics">
              <span>数据范围 <b>近30天主动记录</b></span>
              <span>高频词 <b>{{ profileKeywords }}</b></span>
              <span>标准筛查 <b>{{ selectedScreening ? `${selectedScreening.band_label} · ${selectedScreening.total_score}/27` : '未完成' }}</b></span>
              <span>最近活跃 <b>{{ studentProfile.last_active || selectedStudent.last_active || '--' }}</b></span>
            </div>
          </article>

          <section class="emotion-detail-panel" v-if="selectedStudent" data-guide="emotion-detail">
            <div class="panel-title compact">
              <div>
                <h3>学生记录详情</h3>
                <p>趋势、标签和文本整理仅描述已有记录，不能代表学生整体心理状态。</p>
              </div>
              <button class="ghost-btn" :disabled="analysisLoading" @click="loadAnalysis">{{ analysisLoading ? '整理中...' : '重新整理记录' }}</button>
            </div>
            <div class="detail-stats">
              <div class="detail-stat"><p class="ds-value">{{ detail.stats.total_moods ?? 0 }}</p><p class="ds-label">情绪记录</p></div>
              <div class="detail-stat"><p class="ds-value">{{ detail.stats.total_chats ?? 0 }}</p><p class="ds-label">对话次数</p></div>
              <div class="detail-stat"><p class="ds-value">{{ detail.stats.use_days ?? 0 }}</p><p class="ds-label">使用天数</p></div>
              <div class="detail-stat"><p class="ds-value">{{ dominantRecordLabel }}</p><p class="ds-label">常见记录标签</p></div>
            </div>
            <div class="emotion-sections">
              <div class="chart-section"><h4>主动记录次数（近30天）</h4><div class="trend-chart" v-if="detail.trend?.length"><div class="trend-area"><div class="trend-grid" style="top:25%"></div><div class="trend-grid" style="top:50%"></div><div class="trend-grid" style="top:75%"></div><div v-for="d in detail.trend" :key="d.date" class="trend-col" :title="`${d.date} · ${d.count} 条`"><span class="trend-count">{{ d.count }}条</span><div class="trend-track"><div class="trend-bar" :style="{ height: Math.max(8, Number(d.count || 0) / maxTrendCount * 100) + '%', background: getMoodColor(d.dominant_label) }"></div></div><span class="trend-date">{{ String(d.date).slice(5) }}</span></div></div></div><p v-else class="empty-state">近30天暂无主动记录</p></div>
              <div class="chart-section"><h4>记录标签分布</h4><div class="dist-bars" v-if="detail.distribution && Object.keys(detail.distribution).length"><div v-for="(count, label) in sortedDist" :key="label" class="dist-row"><span class="dist-emoji">{{ getEmoji(label) }}</span><span class="dist-label">{{ label }}</span><div class="dist-track"><div class="dist-fill" :style="{ width: getDistPct(count) + '%', background: getMoodColor(label) }"></div></div><span class="dist-count">{{ count }}次</span></div></div><p v-else class="empty-state">暂无分布数据</p></div>
              <div class="chart-section"><h4>高频词汇</h4><div class="word-cloud-wrap" v-if="normalizedWordCloud.length"><div class="normal-word-cloud"><span v-for="(item, index) in normalizedWordCloud" :key="item.word + index" :class="['word-cloud-item', 'level-' + item.level, 'pos-' + (index % 18)]" :style="{ '--word-size': item.size + 'px', '--word-opacity': item.opacity }">{{ item.word }}</span></div></div><p v-else class="empty-state">暂无词云数据</p></div>
              <div class="chart-section"><div class="analysis-title"><h4>{{ analysisHeading }}</h4><small v-if="analysisMeta.generatedAt">{{ analysisMeta.degraded ? '规则注册表' : analysisMeta.source }} · {{ analysisMeta.version }} · {{ formatDateTime(analysisMeta.generatedAt) }}</small></div><div class="analysis-card"><div v-if="analysisLoading" class="analysis-loading"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div><div v-else-if="analysisSections.length" class="analysis-sections"><p v-if="analysisMeta.degraded" class="analysis-source">当前为规则化记录整理，不表示外部模型已完成分析。</p><article v-for="section in analysisSections" :key="section.title" :class="['analysis-block', section.kind]"><span>{{ section.label }}</span><h5>{{ section.title }}</h5><ul><li v-for="(item, index) in section.items" :key="index">{{ item }}</li></ul></article></div><p v-else class="analysis-empty">选择学生后会整理已有记录；结果需结合线下观察确认，不作诊断。</p></div></div>
            </div>
          </section>
        </section>

        <section v-if="tab === 'lesson'"
 class="panel lesson-panel" data-guide="lesson-plan">
          <div class="panel-title">
            <div>
              <h3>AI 班会生成</h3>
              <p>把班级近期风险和关键词转成一节可执行班会，减少教师准备成本。</p>
            </div>
            <button class="ghost-btn" @click="loadTemplates">刷新模板</button>
          </div>
          <div class="lesson-layout">
            <div class="template-list">
              <button
                v-for="tpl in templates"
                :key="tpl.id || tpl.name"
                :class="{ selected: lessonForm.template === (tpl.id || tpl.name) }"
                @click="chooseTemplate(tpl)"
              >
                <strong>{{ tpl.name || tpl.title }}</strong>
                <small>{{ tpl.description || tpl.scene || '适合近期班级共性议题' }}</small>
              </button>
              <p v-if="!templates.length" class="empty-state">暂无模板，可直接填写主题生成。</p>
            </div>
            <div class="lesson-compose">
              <label>
                <span>班会主题</span>
                <input v-model="lessonForm.topic" placeholder="例如：考前减压与情绪调节" />
              </label>
              <label>
                <span>班级重点情况</span>
                <textarea v-model="lessonForm.context" placeholder="例如：本周焦虑类记录增多，宿舍人际关键词较集中。"></textarea>
              </label>
              <button class="primary-btn" :disabled="lessonLoading" @click="generateLessonPlan">
                {{ lessonLoading ? '生成中...' : '生成班会方案' }}
              </button>
            </div>
          </div>
          <article class="lesson-result" v-if="lessonPlan">
            <h4>生成结果</h4>
            <pre>{{ lessonPlan }}</pre>
          </article>
        </section>

        <section v-if="tab === 'accounts' && userStore.isSuperAdmin" class="panel">
          <div class="panel-title">
            <div>
              <h3>账号管理</h3>
              <p>保留内部兼容字段 is_admin，但界面统一表达为教师权限。</p>
            </div>
            <button class="ghost-btn" @click="loadAccounts">刷新账号</button>
          </div>
          <div v-if="accounts.length" class="case-overview" aria-label="账号角色概览">
            <div class="overview-head"><span>账号角色构成</span><em>{{ accounts.length }} 个账号</em></div>
            <div class="overview-bar" role="img" :aria-label="accountBandsAria">
              <span
                v-for="band in accountBands"
                v-show="band.count"
                :key="band.key"
                :class="['overview-seg', band.key]"
                :style="{ flexGrow: band.count }"
                :title="`${band.label} ${band.count} 个`"
              />
            </div>
            <ul class="overview-legend">
              <li v-for="band in accountBands" :key="band.key"><i :class="band.key" aria-hidden="true" /><span>{{ band.label }}</span><strong>{{ band.count }}</strong></li>
            </ul>
          </div>
          <div class="account-list">
            <div v-for="u in accounts" :key="u.id" class="account-row">
              <span class="avatar">{{ firstChar(cleanDisplayName(u.nickname || u.username)) }}</span>
              <div>
                <strong>{{ cleanDisplayName(u.nickname || u.username) }}</strong>
                <small>ID: {{ u.id }} · {{ u.role === 'admin_teacher' ? '管理员教师' : u.role === 'teacher' ? '普通教师' : '学生' }}</small>
              </div>
              <div v-if="u.role === 'teacher'" class="assignment-control">
                <label><span>职责学生</span><select v-model="assignmentStudentByTeacher[u.id]"><option value="">选择学生</option><option v-for="student in students" :key="student.id" :value="student.id">{{ studentName(student) }}</option></select></label>
                <button class="ghost-btn" :disabled="!assignmentStudentByTeacher[u.id]" @click="assignStudent(u)">分配职责</button>
              </div>
              <button v-if="u.role !== 'admin_teacher'" class="ghost-btn" @click="toggleTeacher(u)">{{ u.is_admin ? '取消教师' : '设为教师' }}</button>
              <span v-else class="role-badge admin">管理员教师</span>
            </div>
            <p v-if="!accounts.length" class="empty-state">暂无账号数据。</p>
          </div>
        </section>
      </main>
    </template>
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import axios from 'axios'
import TeacherTodayDashboard from '../components/TeacherTodayDashboard.vue'
import AvatarPickerModal from '../components/AvatarPickerModal.vue'
import { getAvatarSrc } from '../utils/avatar'
import TeacherReviewReport from '../components/TeacherReviewReport.vue'
import UiIcon from '../components/UiIcon.vue'
import { useDesktopViewport } from '../utils/useDesktopViewport'
const desktop = useDesktopViewport()
const TeacherVerification = defineAsyncComponent(() => import('../components/TeacherVerification.vue'))
const TeacherCaseTaskPanel = defineAsyncComponent(() => import('../components/TeacherCaseTaskPanel.vue'))
import pkg from '../../package.json'
import {
  getTeacherOverview,
  getTeacherStudents,
  getTeacherWarnings,
  getTeacherWarningDetail,
  handleTeacherWarning,
  getLessonTemplates,
  generateLesson,
  getStudentProfile,
  getTeacherAccounts,
  updateTeacherAccount,
  createCaseAccessRequest,
  getCaseAccessRequests,
  decideCaseAccessRequest,
  getStudentWorkProduct,
  decideStudentWorkProductTask,
  generateStudentReviewReport,
  getLatestStudentReviewReport,
  decideStudentReviewReport,
  studentReviewReportPdfUrl,
  setTeacherStudentAssignment,
  setStudentExternalAiAuthorization,
} from '../api/teacher'


const router = useRouter()
const userStore = useUserStore()
const showAvatarPicker = ref(false)
const avatarSrc = ref(getAvatarSrc())

const tab = ref('today')
const teacherVersion = pkg.version
const error = ref('')
const teacherQuery = ref('')
const teacherSearchInput = ref(null)
const teacherNav = ref(null)
const workspaceRefreshing = ref(false)
const overview = ref({})
const students = ref([])
const warningList = ref([])
const selectedWarning = ref(null)
const selectedStudent = ref(null)
const studentProfile = ref({})
const detail = ref({ stats: {}, trend: [], distribution: {}, word_cloud: [] })
const analysis = ref('')
const analysisMeta = ref({ degraded: true, source: '', version: '', generatedAt: '' })
const analysisLoading = ref(false)
const templates = ref([])
const accounts = ref([])
const handleNote = ref('')
const lessonLoading = ref(false)
const lessonPlan = ref('')
const accessRequests = ref([])
const caseStudent = ref(null)
const accessReason = ref('')
const accessSubmitting = ref(false)
const contextLoading = ref(false)
const workProduct = ref(null)
const reviewReport = ref(null)
const reviewReportLoading = ref(false)
const reviewDecisionLoading = ref(false)
const caseResultHeading = ref(null)
const confirmedTasks = ref([])
const taskDecisionLoading = ref(null)
const caseMessage = ref('')
const aiAuthorityConfirmed = ref(false)
const aiAuthorizationDays = ref(30)
const aiAuthorizationLoading = ref(false)
const approvalLoading = ref(false)
const approvalError = ref('')
const reviewTargetId = ref(null)
const pendingDecision = ref('')
const reviewNote = ref('')
const reviewSubmitting = ref(false)
const assignmentStudentByTeacher = ref({})
const lessonForm = ref({ template: '', topic: '考前减压与情绪调节', context: '' })
const teacherNavItems = [
  { id: 'today', label: '今日工作台', icon: '⌂', group: '工作' },
  { id: 'cases', label: '支持工单', icon: '▣', group: '工作' },
  { id: 'warnings', label: '支持提醒', icon: '!', group: '工作' },
  { id: 'students', label: '学生记录', icon: '◎', group: '工作', adminOnly: true },
  { id: 'lesson', label: 'AI 班会', icon: '◇', group: '工具' },
  { id: 'benchmark', label: '能力验证', icon: '✓', group: '工具' },
  { id: 'approvals', label: '权限审批', icon: '✓', group: '管理', adminOnly: true },
  { id: 'accounts', label: '账号职责', icon: '⌘', group: '管理', adminOnly: true },
]
const visibleNavItems = computed(() => teacherNavItems.filter(item => (!item.adminOnly || userStore.isSuperAdmin) && (item.id !== 'benchmark' || desktop.value)))
watch(desktop, value => { if (!value && tab.value === 'benchmark') tab.value = 'today' })
const currentTabMeta = computed(() => visibleNavItems.value.find(item => item.id === tab.value) || teacherNavItems[0])
const normalizedTeacherQuery = computed(() => teacherQuery.value.trim().toLowerCase())
const filteredStudents = computed(() => {
  if (!normalizedTeacherQuery.value) return students.value
  return students.value.filter(student => studentName(student).toLowerCase().includes(normalizedTeacherQuery.value))
})
const filteredWarnings = computed(() => {
  if (!normalizedTeacherQuery.value) return warningList.value
  return warningList.value.filter(item => cleanDisplayName(item.student_name || item.nickname || `学生 ${item.student_id}`).toLowerCase().includes(normalizedTeacherQuery.value))
})

const ACCESS_BANDS = [
  { key: 'direct', label: '直达权限', statuses: ['direct'] },
  { key: 'approved', label: '审批通过', statuses: ['approved'] },
  { key: 'pending', label: '审批中', statuses: ['pending'] },
  { key: 'closed', label: '驳回/过期', statuses: ['rejected', 'expired', 'revoked'] },
  { key: 'none', label: '未申请', statuses: ['not_requested'] },
]
const caseAccessBands = computed(() => {
  const bands = ACCESS_BANDS.map(band => ({ key: band.key, label: band.label, count: 0 }))
  filteredStudents.value.forEach(student => {
    const status = student.access?.status
    const index = ACCESS_BANDS.findIndex(band => band.statuses.includes(status))
    bands[index === -1 ? bands.length - 1 : index].count += 1
  })
  const total = Math.max(1, filteredStudents.value.length)
  return bands.map(band => ({ ...band, pct: Math.round((band.count / total) * 100) }))
})
const caseAccessAria = computed(() => `权限状态构成：${caseAccessBands.value.map(band => `${band.label} ${band.count} 人`).join('，')}`)

const warningBands = computed(() => {
  const counts = { urgent: 0, high: 0, middle: 0, low: 0 }
  filteredWarnings.value.forEach(item => {
    if (item.urgent === true || item.risk === 'urgent') counts.urgent += 1
    else if (item.risk_level === 'high' || item.risk === 'professional') counts.high += 1
    else if (['middle', 'medium'].includes(item.risk_level) || item.risk === 'watch') counts.middle += 1
    else counts.low += 1
  })
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0)
  return [
    { key: 'urgent', label: '危急', count: counts.urgent },
    { key: 'high', label: '高风险', count: counts.high },
    { key: 'middle', label: '需关注', count: counts.middle },
    { key: 'low', label: '常规', count: counts.low },
  ].map(band => ({ ...band, pct: total ? Math.round((band.count / total) * 100) : 0 }))
})
const warningRiskAria = computed(() => `风险分流：${warningBands.value.map(band => `${band.label} ${band.count} 条`).join('，')}`)
const warningWeek = computed(() => {
  const DAY = 86400000
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(start.getTime() - (6 - index) * DAY)
    return { key: `${date.getMonth() + 1}-${date.getDate()}`, weekday: '日一二三四五六'[date.getDay()], date, count: 0 }
  })
  filteredWarnings.value.forEach(item => {
    const raw = item.created_at || item.updated_at
    if (!raw) return
    const time = new Date(String(raw).replace(' ', 'T'))
    if (Number.isNaN(time.getTime())) return
    const day = days.find(entry => time >= entry.date && time < new Date(entry.date.getTime() + DAY))
    if (day) day.count += 1
  })
  return days
})
const warningWeekTotal = computed(() => warningWeek.value.reduce((sum, day) => sum + day.count, 0))
const warningWeekPeak = computed(() => Math.max(1, ...warningWeek.value.map(day => day.count)))
function warningBarHeight(count) {
  return count ? Math.max(10, Math.round((count / warningWeekPeak.value) * 100)) : 0
}

const approvalBands = computed(() => {
  const counts = { pending: 0, approved: 0, rejected: 0, other: 0 }
  accessRequests.value.forEach(item => {
    counts[counts[item.status] !== undefined ? item.status : 'other'] += 1
  })
  return [
    { key: 'approval-pending', label: '待审批', count: counts.pending },
    { key: 'approval-approved', label: '已批准', count: counts.approved },
    { key: 'approval-rejected', label: '已拒绝', count: counts.rejected },
    { key: 'approval-other', label: '已失效', count: counts.other },
  ]
})
const approvalBandsAria = computed(() => `审批队列构成：${approvalBands.value.map(band => `${band.label} ${band.count} 条`).join('，')}`)

const accountBands = computed(() => {
  const counts = { admin: 0, teacher: 0, student: 0 }
  accounts.value.forEach(account => {
    if (account.role === 'admin_teacher') counts.admin += 1
    else if (account.role === 'teacher') counts.teacher += 1
    else counts.student += 1
  })
  return [
    { key: 'account-admin', label: '管理员教师', count: counts.admin },
    { key: 'account-teacher', label: '普通教师', count: counts.teacher },
    { key: 'account-student', label: '学生账号', count: counts.student },
  ]
})
const accountBandsAria = computed(() => `账号角色构成：${accountBands.value.map(band => `${band.label} ${band.count} 个`).join('，')}`)
const pendingApprovalCount = computed(() => accessRequests.value.filter((item) => item.status === 'pending').length)
const caseStageTitle = computed(() => {
  const status = caseStudent.value?.access?.status
  if (status === 'pending') return '等待管理员教师审批'
  if (status === 'approved' || status === 'direct') return '已具备个案查看权限'
  return '提交个案查看申请'
})
const profileKeywords = computed(() => {
  const words = studentProfile.value.keywords || selectedStudent.value?.keywords || []
  if (!words.length) return '--'
  return words.slice(0, 4).map((w) => w.word || w).join('、')
})
const selectedScreening = computed(() => studentProfile.value.screening_summary || selectedStudent.value?.screening || null)
const dominantRecordLabel = computed(() => Object.keys(sortedDist.value)[0] || '--')
const maxTrendCount = computed(() => Math.max(1, ...(detail.value.trend || []).map(item => Number(item.count || 0))))
const analysisHeading = computed(() => analysisMeta.value.degraded ? '规则化记录整理' : 'Agent 记录整理')
const teacherGenerationLabel = computed(() => {
  const generation = workProduct.value?.generation || {}
  if (generation.source === 'safety_override') return '安全规则强制覆盖'
  if (generation.source === 'xunfei_constrained') return '讯飞受约束生成'
  if (generation.degraded) return '规则安全降级'
  return '本地确定性规则'
})
const agentHandoff = computed(() => workProduct.value?.agent_handoff && typeof workProduct.value.agent_handoff === 'object'
  ? workProduct.value.agent_handoff
  : null)
const recentAgentHandoffs = computed(() => Array.isArray(agentHandoff.value?.latest) ? agentHandoff.value.latest : [])

const normalizedWordCloud = computed(() => {
  const raw = Array.isArray(detail.value.word_cloud) ? detail.value.word_cloud : []
  const items = raw
    .map((item) => {
      const word = String(item.word || item.text || item.keyword || item || '').trim()
      const count = Number(item.count || item.value || item.weight || 1)
      return word ? { word, count: Number.isFinite(count) ? count : 1 } : null
    })
    .filter(Boolean)
    .sort((a, b) => b.count - a.count)
    .slice(0, 18)
  const max = Math.max(1, ...items.map((item) => item.count))
  return items.map((item, index) => ({
    ...item,
    size: Math.round(14 + (item.count / max) * 24),
    opacity: (0.68 + (item.count / max) * 0.32).toFixed(2),
    level: index < 3 ? 'hot' : index < 8 ? 'mid' : 'soft',
  }))
})

const analysisSections = computed(() => parseAnalysisSections(analysis.value))

function normalizeList(payload, keys) {
  const data = payload?.data || payload
  if (Array.isArray(data)) return data
  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key]
  }
  return []
}

function normalizeObject(payload, fallback = {}) {
  return payload?.data || payload || fallback
}

function cleanDisplayName(value) {
  return String(value || '').trim() || '未命名'
}

function studentName(student) {
  return cleanDisplayName(student?.nickname || student?.username || student?.name || `学生 ${student?.id || ''}`)
}

async function loadOverview() {
  const r = await getTeacherOverview(userStore.userId)
  overview.value = normalizeObject(r.data, {})
}

async function loadWarnings() {
  const r = await getTeacherWarnings(userStore.userId)
  warningList.value = normalizeList(r.data, ['warnings', 'items', 'list'])
  if (!selectedWarning.value && warningList.value.length) selectWarning(warningList.value[0])
}

async function loadStudents() {
  const r = await getTeacherStudents(userStore.userId)
  students.value = normalizeList(r.data, ['students', 'items', 'list'])
  if (caseStudent.value) caseStudent.value = students.value.find((item) => item.id === caseStudent.value.id) || null
  if (!caseStudent.value && students.value.length) caseStudent.value = students.value[0]
}

async function loadAccessRequests() {
  approvalLoading.value = true
  approvalError.value = ''
  try {
    const r = await getCaseAccessRequests()
    accessRequests.value = normalizeList(r.data, ['items', 'requests'])
  } catch {
    accessRequests.value = []
    approvalError.value = '审批队列读取失败，当前结果不可用。'
  } finally {
    approvalLoading.value = false
  }
}

async function loadTemplates() {
  const r = await getLessonTemplates(userStore.userId)
  templates.value = normalizeList(r.data, ['templates', 'items', 'list'])
}

async function loadAccounts() {
  try {
    const r = await getTeacherAccounts(userStore.userId)
    accounts.value = normalizeList(r.data, ['accounts', 'users', 'items'])
  } catch {
    accounts.value = []
  }
}

async function loadAll() {
  error.value = ''
  try {
    await Promise.all([loadOverview(), loadWarnings(), loadStudents(), loadTemplates(), loadAccounts(), loadAccessRequests()])
  } catch (e) {
    error.value = '教师端数据加载失败，请确认后端 /api/teacher 服务正常。'
  }
}

async function refreshWorkspace() {
  workspaceRefreshing.value = true
  try { await loadAll() } finally { workspaceRefreshing.value = false }
}

async function openTodayItem(item) {
  if (item.type === 'warning') {
    tab.value = 'warnings'
    await selectWarning(item.payload)
    return
  }
  if (item.type === 'approval') {
    tab.value = 'approvals'
    prepareReview(item.payload, 'approved')
    return
  }
  if (item.type === 'case') {
    tab.value = 'cases'
    chooseCaseStudent(item.payload)
  }
}

function openTodayStudent(student) {
  if (userStore.isSuperAdmin) {
    tab.value = 'students'
    selectStudent(student)
    return
  }
  tab.value = 'cases'
  chooseCaseStudent(student)
}

function focusTeacherSearch(event) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    teacherSearchInput.value?.focus({ preventScroll: true })
  }
}

function handoffVerificationTone(status) {
  if (['verified', 'passed', 'completed'].includes(status)) return 'verified'
  if (['failed', 'blocked', 'rejected'].includes(status)) return 'failed'
  if (['needs_attention', 'attention'].includes(status)) return 'attention'
  return 'pending'
}

function handoffVerificationLabel(status) {
  return ({ verified: '已核验', failed: '未通过', attention: '需处理', pending: '待核验' })[handoffVerificationTone(status)]
}

function handoffRiskLabel(risk) {
  return ({
    routine: '常规支持',
    watch: '建议持续留意',
    professional: '建议专业支持',
    urgent: '立即安全协助',
  })[risk] || '尚未分流'
}

function handoffOwnerLabel(owner) {
  return ({
    student: '学生自主选择',
    student_choice: '学生自主选择',
    student_with_trusted_adult: '学生与可信成年人共同决定',
    teacher: '教师确认后接力',
    counselor: '校内心理支持人员',
    school_support: '校内支持人员',
    trusted_adult_or_school_support: '可信成年人或校内支持人员',
    trusted_adult_or_emergency_support: '可信成年人或紧急支持',
  })[owner] || String(owner || '未指定').replaceAll('_', ' ')
}

function chooseCaseStudent(student) {
  caseStudent.value = student
  accessReason.value = ''
  workProduct.value = null
  reviewReport.value = null
  confirmedTasks.value = []
  caseMessage.value = ''
  aiAuthorityConfirmed.value = false
}

async function updateStudentAiAuthorization(active) {
  if (!caseStudent.value || aiAuthorizationLoading.value) return
  aiAuthorizationLoading.value = true
  caseMessage.value = ''
  try {
    await setStudentExternalAiAuthorization(caseStudent.value.id, active, active ? aiAuthorityConfirmed.value : false, aiAuthorizationDays.value)
    await loadStudents()
    caseMessage.value = active ? '学生端模型协作已启用并记录审计。' : '学生端模型协作授权已撤回，后续自动切回本地规则。'
    aiAuthorityConfirmed.value = false
  } catch (e) {
    caseMessage.value = e.response?.data?.detail || '授权状态更新失败，请重试。'
  } finally {
    aiAuthorizationLoading.value = false
  }
}

async function submitAccessRequest() {
  if (!caseStudent.value || accessReason.value.trim().length < 10) return
  accessSubmitting.value = true
  caseMessage.value = ''
  try {
    const r = await createCaseAccessRequest(caseStudent.value.id, accessReason.value.trim())
    caseMessage.value = r.data.status === 'direct' ? '管理员教师可直接查看。' : '申请已提交，等待管理员教师审批。'
    await Promise.all([loadStudents(), loadAccessRequests()])
  } catch (e) {
    caseMessage.value = e.response?.data?.detail || '申请提交失败，请稍后重试。'
  } finally {
    accessSubmitting.value = false
  }
}

async function loadCaseContext() {
  if (!caseStudent.value) return
  contextLoading.value = true
  caseMessage.value = ''
  try {
    const productResponse = await getStudentWorkProduct(caseStudent.value.id, caseStudent.value.access?.request_id)
    workProduct.value = productResponse.data
    try {
      reviewReport.value = (await getLatestStudentReviewReport(caseStudent.value.id, caseStudent.value.access?.request_id)).data
    } catch (reportError) {
      reviewReport.value = null
      if (reportError.response?.status !== 404) caseMessage.value = '支持工单已读取，但历史评审报告暂时不可用；仍可继续查看证据或重新生成报告。'
    }
    confirmedTasks.value = Array.isArray(productResponse.data.confirmed_task_indices) ? productResponse.data.confirmed_task_indices : []
    if (!caseMessage.value) caseMessage.value = `支持工单已生成：${teacherGenerationLabel.value}`
    await nextTick()
    caseResultHeading.value?.focus({ preventScroll: true })
  } catch (e) {
    workProduct.value = null
    caseMessage.value = e.response?.data?.detail || '暂时无法读取个案原文。'
  } finally {
    contextLoading.value = false
  }
}

async function generateReviewReport() {
  if (!caseStudent.value || reviewReportLoading.value) return
  reviewReportLoading.value = true
  caseMessage.value = ''
  try {
    reviewReport.value = (await generateStudentReviewReport(caseStudent.value.id, caseStudent.value.access?.request_id)).data
    caseMessage.value = '最终评审报告已生成，等待教师核对并签署。'
  } catch (e) {
    caseMessage.value = e.response?.data?.detail || '最终评审报告生成失败，请重试。'
  } finally {
    reviewReportLoading.value = false
  }
}

async function submitReviewDecision({ decision, checklistConfirmed, evidenceGapAcknowledged, note }) {
  if (!caseStudent.value || !reviewReport.value || reviewDecisionLoading.value) return
  reviewDecisionLoading.value = true
  caseMessage.value = ''
  try {
    reviewReport.value = (await decideStudentReviewReport(
      caseStudent.value.id,
      reviewReport.value.report_id,
      decision,
      checklistConfirmed,
      evidenceGapAcknowledged,
      note,
      caseStudent.value.access?.request_id,
    )).data
    caseMessage.value = decision === 'reviewed' ? '教师复核已签署并记录审计。' : '报告已退回修订并记录原因。'
  } catch (e) {
    caseMessage.value = e.response?.data?.detail || '审核状态记录失败，请重试。'
  } finally {
    reviewDecisionLoading.value = false
  }
}

function downloadReviewReport() {
  if (!caseStudent.value || !reviewReport.value) return
  window.open(studentReviewReportPdfUrl(caseStudent.value.id, reviewReport.value.report_id, caseStudent.value.access?.request_id), '_blank', 'noopener,noreferrer')
}

async function toggleTask(index) {
  if (!caseStudent.value || !workProduct.value || taskDecisionLoading.value !== null) return
  const isConfirmed = confirmedTasks.value.includes(index)
  taskDecisionLoading.value = index
  caseMessage.value = ''
  try {
    await decideStudentWorkProductTask(
      caseStudent.value.id,
      workProduct.value.case_id,
      index,
      isConfirmed ? 'revoked' : 'confirmed',
      caseStudent.value.access?.request_id,
    )
    confirmedTasks.value = isConfirmed
      ? confirmedTasks.value.filter((item) => item !== index)
      : [...confirmedTasks.value, index]
    caseMessage.value = isConfirmed ? '任务确认已撤销并记录审计。' : '教师确认已记录审计。'
  } catch (e) {
    caseMessage.value = e.response?.data?.detail || '任务确认记录失败，请重试。'
  } finally {
    taskDecisionLoading.value = null
  }
}

function scrollToEvidence(id) {
  const target = document.getElementById(`evidence-${id}`)
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  target?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' })
  target?.focus({ preventScroll: true })
}

async function reviewAccess(item, decision) {
  reviewSubmitting.value = true
  try {
    await decideCaseAccessRequest(item.id, decision, reviewNote.value.trim())
    await Promise.all([loadAccessRequests(), loadStudents()])
    cancelReview()
  } catch (e) {
    approvalError.value = e.response?.data?.detail || '审批失败，请稍后重试。'
  } finally {
    reviewSubmitting.value = false
  }
}

function prepareReview(item, decision) {
  reviewTargetId.value = item.id
  pendingDecision.value = decision
  reviewNote.value = decision === 'approved' ? '申请目的明确，同意按固定时间范围开放7天' : '申请理由或职责范围不足，暂不开放原文'
}

function cancelReview() {
  reviewTargetId.value = null
  pendingDecision.value = ''
  reviewNote.value = ''
}

function accessStatusText(status) {
  return { pending: '待审批', approved: '已批准', rejected: '已拒绝', revoked: '已撤销', direct: '管理员直达' }[status] || status
}

function formatDateTime(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '--'
}

function pipelineStatusText(status) {
  return ({ completed: '已完成', running: '进行中', blocked: '已停止', degraded: '已降级', failed: '失败' })[status] || '等待'
}

async function selectWarning(item) {
  selectedWarning.value = item
  handleNote.value = ''
  try {
    const r = await getTeacherWarningDetail(item.id, userStore.userId)
    selectedWarning.value = { ...item, ...normalizeObject(r.data, {}) }
  } catch {}
}

async function selectStudent(student) {
  selectedStudent.value = student
  analysis.value = ''
  analysisMeta.value = { degraded: true, source: '', version: '', generatedAt: '' }
  detail.value = { stats: {}, trend: [], distribution: {}, word_cloud: [] }
  try {
    const r = await getStudentProfile(student.id || student.student_id, userStore.userId)
    studentProfile.value = normalizeObject(r.data, {})
  } catch {
    studentProfile.value = {}
  }
  await loadEmotionDetail(student)
  loadAnalysis()
}

async function loadEmotionDetail(student = selectedStudent.value) {
  if (!student) return
  const studentId = student.id || student.student_id
  try {
    const r = await axios.get(`/api/admin/user-detail/${studentId}`, { params: { user_id: userStore.userId, days: 30 } })
    detail.value = r.data || { stats: {}, trend: [], distribution: {}, word_cloud: [] }
  } catch {
    detail.value = { stats: {}, trend: [], distribution: {}, word_cloud: [] }
  }
}

async function loadAnalysis() {
  if (!selectedStudent.value) return
  const studentId = selectedStudent.value.id || selectedStudent.value.student_id
  analysisLoading.value = true
  try {
    const r = await axios.get(`/api/admin/user-analysis/${studentId}`, { params: { user_id: userStore.userId } })
    analysis.value = r.data?.analysis || '暂无记录整理结果。'
    analysisMeta.value = {
      degraded: r.data?.degraded !== false,
      source: r.data?.source || 'deterministic_record_registry',
      version: r.data?.version || 'teacher-record-summary-v1',
      generatedAt: r.data?.generated_at || '',
    }
  } catch {
    analysis.value = '记录整理暂时不可用，请稍后重试。'
    analysisMeta.value = { degraded: true, source: '', version: '', generatedAt: '' }
  } finally {
    analysisLoading.value = false
  }
}


function parseAnalysisSections(text = '') {
  const cleaned = String(text || '')
    .replace(/\*\*/g, '')
    .replace(/#{1,6}\s*/g, '')
    .replace(/\r/g, '')
    .trim()
  if (!cleaned || cleaned.includes('暂无记录整理结果') || cleaned.includes('暂时不可用')) return []
  const markers = [
    { key: 'summary', label: '记录摘要', title: '已有记录呈现了什么', words: ['心理状态总结', '状态总结', '整体情绪', '记录摘要'] },
    { key: 'finding', label: '需要核对', title: '需要结合线下观察的变化', words: ['关键发现', '发现', '需要核对'] },
    { key: 'advice', label: '行动草案', title: '可由教师确认的下一步', words: ['专业建议', '建议', '行动草案'] },
  ]
  const sentences = cleaned
    .split(/(?=\d+\.|[。；;]|\n+)/)
    .map((line) => line.replace(/^[-\s\d.、]+/, '').trim())
    .filter(Boolean)
  return markers.map((marker) => {
    const picked = sentences.filter((line) => marker.words.some((word) => line.includes(word)))
    const items = (picked.length ? picked : sentences).slice(0, marker.key === 'summary' ? 2 : 3)
      .map((line) => line.replace(new RegExp(marker.words.join('|'), 'g'), '').replace(/^[:：\s]+/, '').trim())
      .filter(Boolean)
    return { kind: marker.key, label: marker.label, title: marker.title, items: items.length ? items : ['暂无足够内容，请结合学生近期记录综合判断。'] }
  })
}

async function handleWarning() {
  if (!selectedWarning.value) return
  await handleTeacherWarning(selectedWarning.value.id, userStore.userId, handleNote.value || '教师已确认并跟进')
  selectedWarning.value = { ...selectedWarning.value, status: 'handled' }
  await loadWarnings()
}

function openStudentFromWarning() {
  const sid = selectedWarning.value?.student_id
  const target = students.value.find((s) => String(s.id || s.student_id) === String(sid))
  if (!userStore.isSuperAdmin) {
    tab.value = 'cases'
    if (target) chooseCaseStudent(target)
    return
  }
  tab.value = 'students'
  if (target) selectStudent(target)
}

function chooseTemplate(tpl) {
  lessonForm.value.template = tpl.id || tpl.name || tpl.title
  lessonForm.value.topic = tpl.name || tpl.title || lessonForm.value.topic
  lessonForm.value.context = tpl.description || tpl.scene || lessonForm.value.context
}

async function generateLessonPlan() {
  lessonLoading.value = true
  lessonPlan.value = ''
  try {
    const r = await generateLesson(userStore.userId, lessonForm.value)
    const data = normalizeObject(r.data, {})
    lessonPlan.value = data.content || data.plan || data.result || JSON.stringify(data, null, 2)
  } catch {
    lessonPlan.value = '生成失败：请确认 AI 班会接口可用，或稍后重试。'
  } finally {
    lessonLoading.value = false
  }
}

async function toggleTeacher(u) {
  await updateTeacherAccount(u.id, userStore.userId, { is_admin: !u.is_admin })
  await loadAccounts()
}

async function assignStudent(teacherAccount) {
  const studentId = assignmentStudentByTeacher.value[teacherAccount.id]
  if (!studentId) return
  try {
    await setTeacherStudentAssignment(teacherAccount.id, Number(studentId), true)
    caseMessage.value = `已将学生职责分配给 ${cleanDisplayName(teacherAccount.nickname || teacherAccount.username)}`
  } catch (e) {
    error.value = e.response?.data?.detail || '职责分配失败'
  }
}

async function openTab(name) {
  if (!visibleNavItems.value.some(item => item.id === name)) return
  tab.value = name
  if (name === 'approvals' && userStore.isSuperAdmin) await loadAccessRequests()
  if (name === 'cases') await loadStudents()
}


function handleBack() {
  router.push('/')
}

function handleLogout() {
  userStore.logout()
  router.push('/teacher-login')
}

function firstChar(text = '') {
  return String(text || '?').slice(0, 1).toUpperCase()
}

const sortedDist = computed(() => {
  const d = detail.value.distribution || {}
  return Object.fromEntries(Object.entries(d).sort((a, b) => b[1] - a[1]))
})

function getDistPct(count) {
  const total = Object.values(detail.value.distribution || {}).reduce((a, b) => a + Number(b || 0), 0)
  return total ? (Number(count || 0) / total) * 100 : 0
}

function getEmoji(label) {
  return {
    愤怒: '😠', 厌恶: '🤢', 恐惧: '😨', 开心: '😊', 中性: '😐', 悲伤: '😢', 惊讶: '😲',
    平静: '😌', 焦虑: '😟', 难过: '😢',
  }[label] || '🙂'
}

function getMoodColor(label) {
  return {
    愤怒: '#CF9AA1', 厌恶: '#B8903E', 恐惧: '#A9A3B5', 开心: '#55A87C', 中性: '#6E7FA3',
    悲伤: '#6F82A6', 惊讶: '#D9B46A',
    平静: '#8FCBA6', 焦虑: '#D9B46A', 难过: '#6F82A6',
  }[label] || '#6E7FA3'
}

function riskText(level = 'low') {
  return {
    high: '建议尽快核实',
    middle: '建议持续关注',
    medium: '建议持续关注',
    low: '常规关怀',
    handled: '已完成跟进',
  }[level] || '待核实'
}

onMounted(() => {
  window.addEventListener('keydown', focusTeacherSearch)
  if (!userStore.isAdmin) {
    error.value = '请用教师账号登录'
    return
  }
  loadAll()
})
watch(tab, async (activeTab) => {
  await nextTick()
  teacherNav.value?.querySelector(`[data-nav-id="${activeTab}"]`)?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
})
onBeforeUnmount(() => window.removeEventListener('keydown', focusTeacherSearch))
</script>

<style scoped>
/* ============================================================
   教师工作台 · 版式基线
   细描边 + 小圆角 + 单一强调色 + 等宽数字，避免渐变与彩色胶囊。
   ============================================================ */
.teacher-page {
  display: grid;
  grid-template-columns: 224px minmax(0, 1fr);
  min-height: 100dvh;
  padding: 0;
  color: var(--t-ink);
  background: var(--t-canvas);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 13px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  --teacher-accent: var(--t-accent);
}
.teacher-sidebar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  height: 100dvh;
  padding: 20px 12px 14px;
  color: #F1EBDB;
  background: var(--t-sidebar);
}
.teacher-brand { display: flex; gap: 10px; align-items: center; padding: 0 8px 16px; }
.teacher-brand > span {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  border-radius: var(--t-r-sm);
  color: var(--t-sidebar);
  background: var(--t-brand);
  font-size: 15px;
  font-weight: 700;
}
.teacher-brand div { min-width: 0; display: grid; gap: 1px; }
.teacher-brand strong { font-size: 14px; font-weight: 600; letter-spacing: .01em; }
.teacher-brand small { color: rgba(244, 241, 232, .48); font-size: 11px; }
.teacher-brand em { color: var(--t-brand); font-size: 10px; font-style: normal; letter-spacing: .04em; }
.teacher-brand-meta { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; }
.teacher-version { color: rgba(244, 241, 232, .34); font: 500 10px/1.5 var(--t-mono); }
.teacher-nav { display: grid; gap: 2px; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, .08); }
.teacher-nav button {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  gap: 9px;
  align-items: center;
  width: 100%;
  min-height: 36px;
  padding: 7px 9px;
  border: 0;
  border-radius: var(--t-r-sm);
  color: rgba(244, 241, 232, .66);
  background: transparent;
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: color 160ms ease, background-color 160ms ease, transform 180ms cubic-bezier(.22, 1, .36, 1);
}
.teacher-nav button > span:first-child { display: grid; place-items: center; width: 20px; height: 20px; color: rgba(244, 241, 232, .55); transition: color 140ms ease, transform 180ms cubic-bezier(.22, 1, .36, 1); }
.teacher-legacy-icon { display: none; }
.teacher-nav button:hover { color: #fff; background: rgba(255, 255, 255, .06); transform: translateX(2px); }
.teacher-nav button:hover > span:first-child { transform: scale(1.14); }
.teacher-nav button.active { color: #fff; font-weight: 600; background: rgba(255, 255, 255, .085); box-shadow: inset 3px 0 0 var(--t-brand); transform: none; }
.teacher-nav button.active > span:first-child { color: var(--t-brand); transform: scale(1.1); }
.teacher-nav em {
  display: grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 99px;
  color: #F7E7E9;
  background: #B95C66;
  font-size: 10px;
  font-style: normal;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.teacher-nav-hint { display: none; }
.teacher-sidebar-footer { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: auto; padding-top: 14px; border-top: 1px solid rgba(255, 255, 255, .08); }
.teacher-sidebar-footer .teacher-user { grid-column: 1 / -1; display: flex; align-items: center; gap: 8px; padding: 5px 6px; text-align: left; }
.teacher-user-avatar { width: 26px; height: 26px; flex: 0 0 auto; border-radius: 6px; overflow: hidden; display: grid; place-items: center; background: rgba(255, 255, 255, .12); color: #E4DED0; font-size: 12px; }
.teacher-user-avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
.teacher-user-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11.5px; }
.teacher-sidebar-footer .role-badge,
.teacher-sidebar-footer .role-badge.admin { grid-column: 1 / -1; margin: 0 0 2px; padding: 5px 8px; border: 1px solid rgba(255, 255, 255, .08); border-radius: 3px; color: rgba(244, 241, 232, .68); background: rgba(255, 255, 255, .03); font-size: 11px; font-weight: 500; text-align: center; }
.teacher-sidebar-footer button { min-height: 30px; padding: 5px; border: 1px solid rgba(255, 255, 255, .1); border-radius: var(--t-r-sm); color: rgba(244, 241, 232, .7); background: transparent; font: inherit; font-size: 11px; cursor: pointer; }
.teacher-sidebar-footer button:hover { color: #fff; background: rgba(255, 255, 255, .07); }

.teacher-shell { min-width: 0; }
.teacher-topbar {
  position: sticky;
  top: 0;
  z-index: 15;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
  min-height: 64px;
  padding: 10px 28px;
  border-bottom: 1px solid var(--t-line);
  background: var(--t-surface);
}
.teacher-topbar p, .teacher-topbar h1 { margin: 0; }
.teacher-topbar p { color: var(--t-faint); font: 500 11px/1.4 var(--t-mono); letter-spacing: .03em; }
.teacher-topbar h1 { margin-top: 2px; color: var(--t-ink); font-size: 18px; font-weight: 600; letter-spacing: -.01em; }
.teacher-search { position: relative; width: min(320px, 40vw); }
.teacher-search input { width: 100%; min-height: 34px; padding: 6px 64px 6px 11px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 12.5px; }
.teacher-search input::placeholder { color: var(--t-faint); }
.teacher-search kbd { position: absolute; top: 50%; right: 8px; padding: 1px 5px; border: 1px solid var(--t-line); border-radius: 3px; color: var(--t-faint); background: var(--t-surface-2); font: 500 10px/1.6 var(--t-mono); transform: translateY(-50%); }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }

.workspace { width: min(1440px, 100%); margin: 0 auto; padding: 24px 28px 48px; }
.workspace > .panel { padding: 22px; border: 1px solid var(--t-line); border-radius: var(--t-r-lg); background: var(--t-surface); }
.panel-title { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }
.panel-title h3 { margin: 0 0 4px; color: var(--t-ink); font-size: 17px; font-weight: 600; letter-spacing: -.005em; }
.panel-title p { max-width: 78ch; margin: 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.65; }
.section-kicker { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 8px; color: var(--t-muted); font-size: 11px; font-weight: 600; letter-spacing: .03em; }
.section-kicker::before { content: ""; width: 14px; height: 1px; background: var(--t-line-2); }

.primary-btn, .ghost-btn, .danger-btn {
  min-height: 34px;
  padding: 6px 14px;
  border: 1px solid transparent;
  border-radius: var(--t-r-sm);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease;
}
.primary-btn { color: #fff; background: var(--t-accent); }
.primary-btn:hover:not(:disabled) { background: var(--t-accent-ink); }
.ghost-btn { color: var(--t-ink-2); background: var(--t-surface); border-color: var(--t-line-2); }
.ghost-btn:hover:not(:disabled) { border-color: #868C9B; background: var(--t-surface-2); }
.danger-btn { color: var(--t-red); background: var(--t-surface); border-color: #E9C4C8; }
.danger-btn:hover:not(:disabled) { background: var(--t-red-bg); }
.primary-btn:disabled, .ghost-btn:disabled, .danger-btn:disabled { opacity: .5; cursor: not-allowed; }

.role-badge { align-self: flex-start; padding: 2px 8px; border: 1px solid var(--t-line-2); border-radius: 3px; color: var(--t-muted); background: var(--t-surface-2); font-size: 11px; font-weight: 600; white-space: nowrap; }
.role-badge.admin { color: var(--t-accent-ink); border-color: #8FCBA6; background: var(--t-accent-soft); }
.error-screen { margin-top: 20px; padding: 44px; border: 1px solid #E9C4C8; border-radius: var(--t-r-lg); color: var(--t-red); background: var(--t-surface); text-align: center; }
.empty-state { padding: 22px 16px; border: 1px dashed var(--t-line-2); border-radius: var(--t-r); color: var(--t-muted); background: transparent; text-align: center; font-size: 12.5px; }
.empty-state.tall { display: grid; place-items: center; min-height: 240px; }
/* ---------- 支持工单 ---------- */
.case-layout { display: grid; grid-template-columns: minmax(250px, .72fr) minmax(0, 1.28fr); gap: 22px; align-items: start; }
.case-roster { display: grid; align-content: start; gap: 6px; max-height: calc(100dvh - 160px); padding-right: 4px; overflow-y: auto; }
.case-student {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  gap: 3px 10px;
  align-items: center;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--t-line);
  border-left: 2px solid transparent;
  border-radius: var(--t-r);
  color: var(--t-ink);
  background: var(--t-surface);
  text-align: left;
  cursor: pointer;
  transition: border-color 140ms ease, background-color 140ms ease;
}
.case-student:hover { border-color: var(--t-line-2); background: var(--t-surface-2); }
.case-student.selected { border-color: #A9AEB9; border-left-color: var(--t-accent); background: var(--t-accent-soft); }
.case-student-main { display: grid; gap: 2px; min-width: 0; }
.case-student-main strong { overflow: hidden; font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.case-student-main small { overflow: hidden; color: var(--t-muted); font-size: 11.5px; text-overflow: ellipsis; white-space: nowrap; }
.avatar { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: var(--t-r-sm); color: var(--t-ink-2); background: #F1EBDB; font-size: 13px; font-weight: 600; }
.access-pill { grid-column: 3; justify-self: end; align-self: center; padding: 1px 6px; border: 1px solid var(--t-line-2); border-radius: 3px; color: var(--t-muted); background: transparent; font-size: 10.5px; font-style: normal; white-space: nowrap; }
.access-pill.approved, .access-pill.direct { color: var(--t-green-ink); border-color: #C5E3D1; background: var(--t-green-bg); }
.access-pill.pending { color: var(--t-amber-ink); border-color: #EBD4A4; background: var(--t-amber-bg); }
.access-pill.rejected, .access-pill.expired, .access-pill.revoked { color: var(--t-red); border-color: #E9C4C8; background: var(--t-red-bg); }

.case-stage { min-height: 420px; padding: 22px; border: 1px solid var(--t-line); border-radius: var(--t-r-lg); background: var(--t-surface); }
.case-stage-head, .original-list-head, .approval-meta { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; }
.case-stage-head h4, .original-list-head h4, .approval-card h4 { margin: 2px 0 0; font-size: 16px; font-weight: 600; letter-spacing: -.005em; }
.status-pill { padding: 2px 8px; border: 1px solid var(--t-line-2); border-radius: 3px; color: var(--t-muted); background: var(--t-surface-2); font-size: 11px; white-space: nowrap; }
.student-ai-authorization { margin-top: 16px; padding: 12px 14px; border: 1px solid var(--t-line); border-left: 2px solid var(--t-line-2); border-radius: var(--t-r); background: var(--t-surface-2); }
.student-ai-authorization h4 { margin: 3px 0 5px; font-size: 14px; font-weight: 600; }
.student-ai-authorization p, .student-ai-authorization small { margin: 0; color: var(--t-muted); font-size: 12px; line-height: 1.65; }
.student-ai-authorization small { display: block; margin-top: 4px; color: var(--t-faint); }
.access-application, .approval-waiting, .authorized-case { display: grid; gap: 14px; margin-top: 18px; }
.authorized-case > .primary-btn { justify-self: start; min-width: 168px; }
.access-application p { margin: 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.65; }
.access-application label { display: grid; gap: 6px; color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.access-application textarea { min-height: 104px; padding: 10px 12px; border: 1px solid var(--t-line-2); border-radius: var(--t-r); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 13px; resize: vertical; }
.approval-waiting { padding: 12px 14px; border: 1px solid #EBD4A4; border-radius: var(--t-r); color: var(--t-amber-ink); background: var(--t-amber-bg); }
.approval-waiting strong { font-size: 13px; }
.approval-waiting p { margin: 3px 0 0; font-size: 12.5px; line-height: 1.6; }
.privacy-notice { display: grid; gap: 2px; padding: 10px 12px; border-left: 2px solid var(--t-accent); color: var(--t-accent-ink); background: var(--t-accent-soft); font-size: 12px; }
.privacy-notice span { color: var(--t-muted); }

.case-command-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 24px 0 10px; }
.case-command-head h4 { margin: 2px 0 0; font-size: 18px; font-weight: 600; letter-spacing: -.01em; }
.case-result-badges { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.risk-decision { padding: 2px 8px; border: 1px solid #8FCBA6; border-radius: 3px; color: var(--t-accent-ink); background: var(--t-accent-soft); font-size: 11px; font-weight: 600; white-space: nowrap; }
.risk-decision.urgent { color: var(--t-red); border-color: #E9C4C8; background: var(--t-red-bg); }
.risk-decision.professional { color: var(--t-amber-ink); border-color: #EBD4A4; background: var(--t-amber-bg); }
.risk-decision.watch { color: var(--t-amber-ink); border-color: #EBD4A4; background: var(--t-amber-bg); }
.agent-source-badge { display: inline-flex; align-items: center; padding: 2px 8px; border: 1px solid var(--t-line-2); border-radius: 3px; color: var(--t-muted); font-size: 11px; font-weight: 600; }
.agent-pipeline { display: grid; margin-bottom: 16px; border-top: 1px solid var(--t-line); }
.agent-pipeline article { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; gap: 12px; align-items: baseline; padding: 10px 2px; border-bottom: 1px solid var(--t-line); background: none; }
.agent-pipeline article > span { color: var(--t-faint); font: 500 11px/1.4 var(--t-mono); }
.agent-pipeline article div { display: grid; gap: 2px; }
.agent-pipeline article strong { color: var(--t-ink); font-size: 13px; font-weight: 600; }
.agent-pipeline article small { color: var(--t-muted); font-size: 11.5px; }
.agent-pipeline article em { color: var(--t-muted); font-size: 11px; font-style: normal; white-space: nowrap; }
.agent-pipeline article.is-complete em, .agent-pipeline article.completed em { color: var(--t-green-ink); }
.agent-pipeline article.is-blocked em, .agent-pipeline article.blocked em, .agent-pipeline article.failed em { color: var(--t-red); }
.agent-pipeline article.is-attention em, .agent-pipeline article.attention em, .agent-pipeline article.running em { color: var(--t-amber-ink); }

.desktop-case-agent-live { display: none; }
.case-processing-state { display: flex; align-items: center; gap: 10px; margin: 14px 0; padding: 12px 14px; border: 1px solid var(--t-line); border-radius: var(--t-r); background: var(--t-surface-2); }
.case-processing-state i { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 3px; color: var(--t-amber-ink); background: var(--t-amber-bg); font-style: normal; }
.case-processing-state strong, .case-processing-state small { display: block; }
.case-processing-state strong { font-size: 12.5px; }
.case-processing-state small { color: var(--t-muted); font-size: 11px; }

.agent-handoff-ledger { display: none; }
.work-product-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; margin-top: 6px; border-top: 1px solid var(--t-line); }
.evidence-brief, .decision-brief { padding: 16px 20px 14px 0; border: 0; border-radius: 0; background: none; }
.decision-brief { padding-right: 0; padding-left: 20px; border-left: 1px solid var(--t-line); }
.evidence-brief h4, .decision-brief h4 { margin: 4px 0 7px; color: var(--t-ink); font-size: 15px; font-weight: 600; line-height: 1.5; }
.evidence-brief p, .decision-brief p, .agent-conflict p { margin: 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.7; }
.evidence-brief small { color: var(--t-faint); word-break: break-all; }
.decision-brief ul { margin: 10px 0 0; padding-left: 16px; color: var(--t-muted); font-size: 12px; line-height: 1.75; }
.evidence-links { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.evidence-links button { padding: 1px 5px; border: 1px solid var(--t-line-2); border-radius: 3px; color: var(--t-accent); background: var(--t-surface); font: 500 10px/1.6 var(--t-mono); cursor: pointer; }
.evidence-links button:hover { border-color: var(--t-accent); background: var(--t-accent-soft); }

.assessment-brief { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--t-line); }
.assessment-brief > .original-list-head { margin-bottom: 10px; }
.assessment-emotion { margin: 0 0 10px; color: var(--t-ink-2); font-size: 13px; font-weight: 600; }
.assessment-domain-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 0 0 10px; }
.assessment-domain-grid article { padding: 10px 12px; border: 1px solid var(--t-line); border-radius: var(--t-r); background: var(--t-surface-2); }
.assessment-domain-grid span, .assessment-domain-grid strong { display: block; }
.assessment-domain-grid span { color: var(--t-muted); font-size: 11px; }
.assessment-domain-grid strong { margin-top: 2px; color: var(--t-ink); font-size: 13px; font-weight: 600; }
.assessment-domain-grid p { margin: 4px 0 0; color: var(--t-muted); font-size: 11.5px; line-height: 1.55; }
.assessment-brief ul { margin: 8px 0; padding-left: 16px; color: var(--t-muted); font-size: 12.5px; line-height: 1.7; }
.assessment-brief > small { color: var(--t-faint); font-size: 11px; line-height: 1.6; }
.profile-metrics { display: flex; flex-wrap: wrap; gap: 6px; }
.profile-metrics span { padding: 4px 9px; border: 1px solid var(--t-line); border-radius: 3px; color: var(--t-muted); background: var(--t-surface); font-size: 11.5px; }
.profile-metrics b { color: var(--t-ink); font-weight: 600; }
.screening-brief { margin-top: 4px; }
.screening-metrics { margin: 8px 0 6px; }

.agent-conflict { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--t-line); }
.agent-conflict div { display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: baseline; padding: 8px 0; border-bottom: 1px solid var(--t-line); }
.agent-conflict strong { font-size: 12.5px; font-weight: 600; }
.agent-conflict em { color: var(--t-muted); font-size: 11.5px; font-style: normal; }
.agent-conflict .evidence-links { grid-column: 1 / -1; margin-top: 0; }
.task-board { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--t-line); }
.task-row { display: grid; grid-template-columns: 22px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 10px 0; border-top: 1px solid var(--t-line); }
.task-row:first-of-type { border-top: 0; }
.task-row > span { color: var(--t-faint); font: 500 11px/1.4 var(--t-mono); }
.task-row div { display: grid; gap: 2px; }
.task-row strong { color: var(--t-ink); font-size: 12.5px; font-weight: 600; }
.task-row small { color: var(--t-muted); font-size: 11.5px; }
.task-row button { min-height: 30px; padding: 4px 10px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink-2); background: var(--t-surface); font: inherit; font-size: 12px; cursor: pointer; }
.task-row button:hover:not(:disabled) { border-color: var(--t-accent); color: var(--t-accent); }
.task-row button.confirmed { color: var(--t-green-ink); border-color: #C5E3D1; background: var(--t-green-bg); }
.original-list { max-height: 430px; padding-right: 4px; overflow: auto; }
.original-list-head { position: sticky; top: 0; z-index: 1; padding: 10px 0; border-bottom: 1px solid var(--t-line); background: var(--t-surface); }
.original-list-head small { color: var(--t-faint); font-size: 11px; }
.original-record { padding: 10px 14px; border-left: 2px solid var(--t-line-2); background: var(--t-surface-2); }
.original-record > div { display: flex; justify-content: space-between; gap: 12px; color: var(--t-faint); font-size: 11px; }
.original-record p { margin: 6px 0 0; color: var(--t-ink-2); font-size: 12.5px; line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; }
.case-message { margin: 0; padding: 9px 12px; border-left: 2px solid var(--t-accent); color: var(--t-accent-ink); background: var(--t-accent-soft); font-size: 12.5px; }

/* ---------- 审批 ---------- */
.approval-list { display: grid; gap: 10px; }
.approval-list > .empty-state { margin: 0; }
.approval-card { padding: 16px 18px; border: 1px solid var(--t-line); border-radius: var(--t-r); background: var(--t-surface); }
.approval-meta { align-items: center; margin-bottom: 6px; }
.approval-meta > span { color: var(--t-faint); font: 500 11px/1.4 var(--t-mono); }
.approval-card h4 { margin: 0 0 4px; font-size: 14px; font-weight: 600; }
.approval-card p { margin: 0 0 6px; color: var(--t-muted); font-size: 12.5px; line-height: 1.65; }
.approval-card small { display: block; color: var(--t-faint); font-size: 11.5px; line-height: 1.6; }
.approval-actions { display: flex; gap: 8px; margin-top: 12px; }
.review-note { margin: 8px 0 0; color: var(--t-muted); font-size: 12px; }
.review-confirm { display: grid; gap: 10px; margin-top: 12px; padding: 14px; border: 1px solid var(--t-line-2); border-radius: var(--t-r); background: var(--t-surface-2); }
.review-confirm strong { font-size: 13px; }
.review-confirm p { margin: 0; color: var(--t-muted); font-size: 12px; line-height: 1.6; }
.review-confirm label { display: grid; gap: 5px; color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.review-confirm textarea { min-height: 72px; padding: 8px 10px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); font: inherit; font-size: 12.5px; resize: vertical; }
.approval-error { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 0; padding: 10px 12px; border-left: 2px solid var(--t-red); color: var(--t-red); background: var(--t-red-bg); font-size: 12.5px; }
/* ---------- 支持提醒 ---------- */
/* 概览图：权限构成 / 风险分流 / 近 7 天新增 */
.case-overview,
.warn-overview { margin-bottom: 16px; padding: 14px 16px; border: 1px solid var(--t-line); border-radius: var(--t-r); background: var(--t-surface); }
.warn-overview { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, .9fr); gap: 20px; }
.warn-week { padding-inline-start: 20px; border-inline-start: 1px solid var(--t-line); }
.overview-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.overview-head > span { color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.overview-head em { color: var(--t-faint); font: 500 10.5px/1.4 var(--t-mono); font-style: normal; }
.overview-bar { display: flex; height: 8px; margin-top: 12px; border-radius: 2px; overflow: hidden; background: var(--t-surface-2); }
.overview-seg { display: block; min-width: 2px; transform-origin: left; animation: overview-grow 520ms cubic-bezier(.22, 1, .36, 1) both; }
@keyframes overview-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.overview-seg.urgent,
.overview-legend i.urgent { background: #B95C66; }
.overview-seg.high,
.overview-legend i.high { background: #CF9AA1; }
.overview-seg.middle,
.overview-legend i.middle { background: #D9B46A; }
.overview-seg.low,
.overview-legend i.low { background: #A9AEB9; }
.overview-seg.access-direct,
.overview-legend i.access-direct { background: var(--t-accent); }
.overview-seg.access-approved,
.overview-legend i.access-approved { background: #8FCBA6; }
.overview-seg.access-pending,
.overview-legend i.access-pending { background: #E8C783; }
.overview-seg.access-closed,
.overview-legend i.access-closed { background: #B95C66; }
.overview-seg.access-none,
.overview-legend i.access-none { background: #D5CDBC; }
.overview-seg.approval-pending,
.overview-legend i.approval-pending { background: #E8C783; }
.overview-seg.approval-approved,
.overview-legend i.approval-approved { background: #8FCBA6; }
.overview-seg.approval-rejected,
.overview-legend i.approval-rejected { background: #B95C66; }
.overview-seg.approval-other,
.overview-legend i.approval-other { background: #A9AEB9; }
.overview-seg.account-admin,
.overview-legend i.account-admin { background: var(--t-accent); }
.overview-seg.account-teacher,
.overview-legend i.account-teacher { background: #8FCBA6; }
.overview-seg.account-student,
.overview-legend i.account-student { background: #D5CDBC; }
.overview-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 10px 0 0; padding: 0; list-style: none; }
.overview-legend li { display: flex; align-items: center; gap: 6px; color: var(--t-muted); font-size: 11px; }
.overview-legend i { flex: 0 0 auto; width: 6px; height: 6px; border-radius: 1px; }
.overview-legend strong { color: var(--t-ink); font: 600 11.5px/1.4 var(--t-mono); }
.overview-legend em { color: var(--t-faint); font: 500 10px/1.4 var(--t-mono); font-style: normal; }
.overview-empty { margin: 12px 0 0; color: var(--t-muted); font-size: 11.5px; }
.overview-week-chart { display: flex; align-items: flex-end; gap: 6px; height: 58px; margin-top: 10px; }
.overview-week-col { display: flex; flex-direction: column; justify-content: flex-end; flex: 1; height: 100%; min-width: 0; text-align: center; }
.overview-week-count { height: 11px; color: var(--t-faint); font: 500 9px/1.2 var(--t-mono); opacity: .75; }
.overview-week-track { display: flex; align-items: flex-end; height: 34px; border-bottom: 1px solid var(--t-line-2); }
.overview-week-track i { display: block; width: 62%; max-width: 18px; margin: 0 auto; border-radius: 2px 2px 0 0; background: var(--t-accent); opacity: .75; }
.overview-week-track i.empty { background: none; }
.overview-week-day { margin-top: 4px; color: var(--t-faint); font-size: 9.5px; }
.overview-week-col.today .overview-week-day { color: var(--t-ink-2); font-weight: 600; }

.split-layout, .lesson-layout { display: grid; grid-template-columns: minmax(280px, .85fr) minmax(0, 1.15fr); gap: 24px; align-items: start; }
.warning-list { display: grid; gap: 0; border-top: 1px solid var(--t-line); }
.warning-item {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 11px 6px;
  border: 0;
  border-bottom: 1px solid var(--t-line);
  color: var(--t-ink);
  background: none;
  text-align: left;
  cursor: pointer;
}
.warning-item:hover { background: var(--t-surface-2); }
.warning-item.selected { background: var(--t-accent-soft); box-shadow: inset 2px 0 var(--t-accent); }
.risk-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--t-faint); }
.warning-item.high .risk-dot { background: var(--t-red); }
.warning-item.middle .risk-dot, .warning-item.medium .risk-dot { background: #D9B46A; }
.warning-main { display: grid; gap: 2px; min-width: 0; }
.warning-main strong { overflow: hidden; font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.warning-main small { overflow: hidden; color: var(--t-muted); font-size: 11.5px; line-height: 1.5; text-overflow: ellipsis; white-space: nowrap; }
.warning-item em { color: var(--t-muted); font-size: 11px; font-style: normal; white-space: nowrap; }
.detail-card { padding: 18px 20px; border: 1px solid var(--t-line); border-radius: var(--t-r-lg); background: var(--t-surface); }
.detail-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 10px; }
.detail-head h4 { margin: 6px 0 0; font-size: 16px; font-weight: 600; }
.detail-head small { color: var(--t-faint); font: 500 11px var(--t-mono); white-space: nowrap; }
.detail-copy { margin: 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.75; }
.suggestion-box { margin: 14px 0; padding: 10px 12px; border-left: 2px solid var(--t-line-2); background: var(--t-surface-2); }
.suggestion-box strong { display: block; margin-bottom: 3px; font-size: 12px; }
.suggestion-box p { margin: 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.7; }
.handle-box { display: grid; gap: 6px; color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.handle-box textarea { min-height: 86px; padding: 10px 12px; border: 1px solid var(--t-line-2); border-radius: var(--t-r); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 12.5px; resize: vertical; }
.detail-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }

/* ---------- 学生记录 ---------- */
.student-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(196px, 1fr)); gap: 8px; }
.student-card {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) auto;
  gap: 2px 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--t-line);
  border-radius: var(--t-r);
  color: var(--t-ink);
  background: var(--t-surface);
  text-align: left;
  cursor: pointer;
  transition: border-color 140ms ease, background-color 140ms ease;
}
.student-card .avatar { grid-row: 1 / 3; }
.student-card strong { overflow: hidden; font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.student-card small { overflow: hidden; color: var(--t-muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.student-card:hover { border-color: var(--t-line-2); background: var(--t-surface-2); }
.student-card.selected { border-color: #A9AEB9; background: var(--t-accent-soft); }
.risk-label { grid-row: 1 / 3; grid-column: 3; padding: 1px 6px; border: 1px solid var(--t-line-2); border-radius: 3px; color: var(--t-muted); font-size: 10.5px; font-style: normal; }
.risk-label.low { color: var(--t-green-ink); border-color: #C5E3D1; background: var(--t-green-bg); }
.risk-label.middle, .risk-label.medium { color: var(--t-amber-ink); border-color: #EBD4A4; background: var(--t-amber-bg); }
.risk-label.high { color: var(--t-red); border-color: #E9C4C8; background: var(--t-red-bg); }
.profile-card { display: grid; gap: 10px; margin-top: 14px; padding: 16px 18px; border: 1px solid var(--t-line); border-radius: var(--t-r-lg); background: var(--t-surface); }
.profile-card h4 { margin: 0 0 4px; font-size: 15px; font-weight: 600; }
.profile-card p { margin: 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.7; }
.emotion-detail-panel { margin-top: 16px; padding: 18px 0 0; border-top: 1px solid var(--t-line); }
.panel-title.compact { margin-bottom: 12px; }
.detail-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 16px; border-block: 1px solid var(--t-line); }
.detail-stat { padding: 12px 14px; border-inline-end: 1px solid var(--t-line); }
.detail-stat:last-child { border-inline-end: 0; }
.ds-value { margin: 0; color: var(--t-ink); font-size: 21px; font-weight: 600; letter-spacing: -.02em; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.ds-label { margin: 2px 0 0; color: var(--t-muted); font-size: 11.5px; }
.emotion-sections { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.chart-section { padding: 14px 16px; border: 1px solid var(--t-line); border-radius: var(--t-r); background: var(--t-surface); }
.chart-section h4 { margin: 0 0 10px; color: var(--t-ink); font-size: 13px; font-weight: 600; }
.trend-chart { padding: 10px 4px 2px; }
.trend-area { position: relative; display: flex; align-items: flex-end; gap: 3px; height: 128px; }
.trend-grid { position: absolute; left: 0; right: 0; height: 0; border-top: 1px dashed var(--t-line); }
.trend-col { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; height: 100%; min-width: 0; flex: 1; border-radius: 2px; transition: background-color 140ms ease; }
.trend-col:hover { background: rgba(85, 168, 124, .06); }
.trend-col:hover .trend-count { color: var(--t-ink-2); }
.trend-count { color: var(--t-faint); font-size: 9px; font-variant-numeric: tabular-nums; }
.trend-track { display: flex; align-items: flex-end; justify-content: center; width: 100%; flex: 1; }
.trend-bar { width: 62%; max-width: 20px; min-height: 3px; border-radius: 2px 2px 0 0; }
.trend-date { color: var(--t-faint); font-size: 9px; white-space: nowrap; }
.dist-bars { display: grid; gap: 7px; }
.dist-row { display: flex; align-items: center; gap: 8px; }
.dist-emoji { width: 18px; text-align: center; font-size: 12px; filter: grayscale(1); opacity: .72; }
.dist-label { width: 40px; color: var(--t-ink-2); font-size: 12px; }
.dist-track { flex: 1; height: 6px; border-radius: 2px; background: var(--t-surface-2); overflow: hidden; }
.dist-fill { height: 100%; border-radius: 2px; }
.dist-count { width: 40px; color: var(--t-faint); font-size: 11px; text-align: right; font-variant-numeric: tabular-nums; }
.word-cloud-wrap { min-height: 220px; padding: 16px; border: 1px solid var(--t-line); border-radius: var(--t-r); background: var(--t-surface); overflow: hidden; }
.normal-word-cloud { position: relative; min-height: 188px; }
.word-cloud-item { position: absolute; left: 50%; top: 50%; display: inline-block; max-width: 220px; color: var(--t-ink-2); font-size: var(--word-size); font-weight: 600; line-height: 1.15; white-space: nowrap; opacity: var(--word-opacity); transform: translate(-50%, -50%); }
.word-cloud-item.level-hot { color: var(--t-accent-ink); font-weight: 700; }
.word-cloud-item.level-mid { color: #B8903E; }
.word-cloud-item.level-soft { color: var(--t-muted); font-weight: 500; }
.word-cloud-item.pos-0 { transform: translate(-50%, -50%) scale(1.06); }
.word-cloud-item.pos-1 { transform: translate(-112%, -118%) rotate(-3deg); }
.word-cloud-item.pos-2 { transform: translate(18%, -112%) rotate(2deg); }
.word-cloud-item.pos-3 { transform: translate(-120%, 16%) rotate(1deg); }
.word-cloud-item.pos-4 { transform: translate(28%, 20%) rotate(-2deg); }
.word-cloud-item.pos-5 { transform: translate(-50%, 118%); }
.word-cloud-item.pos-6 { transform: translate(-156%, -52%) rotate(2deg); }
.word-cloud-item.pos-7 { transform: translate(72%, -48%) rotate(-2deg); }
.word-cloud-item.pos-8 { transform: translate(-158%, 78%) rotate(-1deg); }
.word-cloud-item.pos-9 { transform: translate(82%, 86%) rotate(2deg); }
.word-cloud-item.pos-10 { transform: translate(-14%, -174%); }
.word-cloud-item.pos-11 { transform: translate(-24%, 174%); }
.word-cloud-item.pos-12 { transform: translate(-198%, -8%) scale(.92); }
.word-cloud-item.pos-13 { transform: translate(116%, -6%) scale(.92); }
.word-cloud-item.pos-14 { transform: translate(-210%, -104%) scale(.86); }
.word-cloud-item.pos-15 { transform: translate(126%, -104%) scale(.86); }
.word-cloud-item.pos-16 { transform: translate(-218%, 128%) scale(.82); }
.word-cloud-item.pos-17 { transform: translate(132%, 132%) scale(.82); }
.analysis-title { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
.analysis-title h4 { margin: 0; }
.analysis-title small, .analysis-source { color: var(--t-faint); font-size: 10.5px; }
.analysis-card { min-height: 110px; padding: 12px 14px; border: 1px solid var(--t-line); border-radius: var(--t-r); color: var(--t-muted); font-size: 12.5px; line-height: 1.75; }
.analysis-sections { display: grid; gap: 12px; }
.analysis-block { padding: 0 0 12px; border-bottom: 1px solid var(--t-line); }
.analysis-block:last-child { padding-bottom: 0; border-bottom: 0; }
.analysis-block > span { display: inline-block; margin-bottom: 4px; color: var(--t-faint); font-size: 10.5px; font-weight: 600; letter-spacing: .04em; }
.analysis-block h5 { margin: 0 0 4px; color: var(--t-ink); font-size: 13px; font-weight: 600; }
.analysis-block ul { margin: 0; padding-left: 16px; }
.analysis-block li { margin: 2px 0; color: var(--t-muted); line-height: 1.7; }
.analysis-block.finding > span { color: var(--t-amber-ink); }
.analysis-block.advice > span { color: var(--t-blue); }
.analysis-empty { margin: 0; color: var(--t-muted); }
.analysis-source { margin: 0 0 8px; }
.analysis-loading { display: flex; gap: 5px; padding: 8px 0; }
.analysis-loading .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--t-line-2); animation: bounce 1.2s infinite both; }
.analysis-loading .dot:nth-child(2) { animation-delay: .2s; }
.analysis-loading .dot:nth-child(3) { animation-delay: .4s; }
@keyframes bounce { 0%, 100% { opacity: .35; transform: translateY(0); } 50% { opacity: 1; transform: translateY(-3px); } }

/* ---------- 班会 ---------- */
.template-list { display: grid; gap: 0; border-top: 1px solid var(--t-line); align-content: start; }
.template-list button { display: grid; gap: 2px; width: 100%; padding: 11px 8px; border: 0; border-bottom: 1px solid var(--t-line); color: var(--t-ink); background: none; text-align: left; cursor: pointer; }
.template-list button:hover { background: var(--t-surface-2); }
.template-list button.selected { background: var(--t-accent-soft); box-shadow: inset 2px 0 var(--t-accent); }
.template-list strong { font-size: 13px; font-weight: 600; }
.template-list small { color: var(--t-muted); font-size: 11.5px; line-height: 1.55; }
.lesson-compose { display: grid; gap: 14px; align-content: start; }
.lesson-compose label { display: grid; gap: 6px; color: var(--t-ink-2); font-size: 12px; font-weight: 600; }
.lesson-compose input, .lesson-compose textarea { width: 100%; padding: 9px 11px; border: 1px solid var(--t-line-2); border-radius: var(--t-r); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 13px; }
.lesson-compose textarea { min-height: 96px; resize: vertical; }
.lesson-result { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--t-line); }
.lesson-result h4 { margin: 0 0 8px; font-size: 14px; font-weight: 600; }
.lesson-result pre { margin: 0; color: var(--t-ink-2); font-family: inherit; font-size: 12.5px; line-height: 1.8; white-space: pre-wrap; }

/* ---------- 账号 ---------- */
.account-list { display: grid; gap: 0; border-top: 1px solid var(--t-line); }
.account-row { display: flex; gap: 12px; align-items: center; width: 100%; padding: 11px 4px; border-bottom: 1px solid var(--t-line); }
.account-row > div { display: grid; gap: 1px; flex: 1; min-width: 0; }
.account-row strong { font-size: 13px; font-weight: 600; }
.account-row small { color: var(--t-muted); font-size: 11px; }
.assignment-control { display: flex; align-items: flex-end; gap: 8px; flex: 0 1 300px; }
.assignment-control label { display: grid; gap: 4px; color: var(--t-muted); font-size: 11px; }
.assignment-control select { min-height: 32px; padding: 4px 8px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 12px; }

/* ---------- 大屏细节 ---------- */
@media (min-width: 1024px) {
  .teacher-shell:has(.has-acceptance) .teacher-topbar { position: static; }
  .desktop-case-agent-live { display: grid; grid-template-columns: minmax(240px, .8fr) minmax(0, 1.6fr); gap: 18px; margin: 14px 0; padding: 14px 16px; border: 1px solid var(--t-line); border-left: 2px solid var(--t-line-2); border-radius: var(--t-r); background: var(--t-surface-2); }
  .desktop-case-agent-live h4 { margin: 2px 0 5px; font-size: 14px; font-weight: 600; }
  .desktop-case-agent-live p { margin: 0; color: var(--t-muted); font-size: 11.5px; line-height: 1.6; }
  .desktop-case-agent-live ol { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 6px; margin: 0; padding: 0; list-style: none; }
  .desktop-case-agent-live li { display: flex; gap: 6px; min-width: 0; padding: 8px; border: 1px solid var(--t-line); border-radius: var(--t-r-sm); background: var(--t-surface); }
  .desktop-case-agent-live li i { display: grid; place-items: center; flex: 0 0 auto; width: 18px; height: 18px; border-radius: 2px; color: var(--t-faint); background: var(--t-surface-2); font-size: 10px; font-style: normal; }
  .desktop-case-agent-live li.complete i { color: #fff; background: var(--t-green); }
  .desktop-case-agent-live li.running i { color: var(--t-amber-ink); background: var(--t-amber-bg); }
  .desktop-case-agent-live li span, .desktop-case-agent-live li strong, .desktop-case-agent-live li small { display: block; min-width: 0; }
  .desktop-case-agent-live li strong { overflow: hidden; color: var(--t-ink-2); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
  .desktop-case-agent-live li small { margin-top: 2px; color: var(--t-faint); font-size: 9px; line-height: 1.35; }
  .agent-handoff-ledger { display: block; margin: 6px 0 18px; padding-top: 16px; border-top: 1px solid var(--t-line); }
  .agent-handoff-ledger > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
  .agent-handoff-ledger > header h4 { margin: 2px 0 0; font-size: 15px; font-weight: 600; }
  .agent-handoff-ledger > header p { display: flex; align-items: baseline; gap: 5px; margin: 0; color: var(--t-muted); font-size: 11.5px; }
  .agent-handoff-ledger > header p strong { color: var(--t-ink); font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .agent-handoff-boundary { max-width: 76ch; margin: 6px 0 10px; color: var(--t-faint); font-size: 11.5px; line-height: 1.6; }
  .agent-handoff-ledger ol { margin: 0; padding: 0; list-style: none; }
  .agent-handoff-ledger li { display: grid; grid-template-columns: minmax(200px, .85fr) minmax(0, 1.3fr); gap: 6px 24px; padding: 11px 0; border-top: 1px solid var(--t-line); }
  .agent-handoff-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; }
  .agent-handoff-meta code { color: var(--t-faint); font-size: 10px; }
  .agent-handoff-meta time { color: var(--t-faint); font-size: 10px; font-variant-numeric: tabular-nums; }
  .agent-handoff-meta span { padding: 1px 6px; border: 1px solid var(--t-line-2); border-radius: 3px; color: var(--t-muted); font-size: 10px; font-weight: 600; }
  .agent-handoff-meta span.is-verified { color: var(--t-green-ink); border-color: #C5E3D1; background: var(--t-green-bg); }
  .agent-handoff-meta span.is-failed { color: var(--t-red); border-color: #E9C4C8; background: var(--t-red-bg); }
  .agent-handoff-meta span.is-attention { color: var(--t-amber-ink); border-color: #EBD4A4; background: var(--t-amber-bg); }
  .agent-handoff-result strong { font-size: 12.5px; font-weight: 600; }
  .agent-handoff-result p { margin: 2px 0 0; color: var(--t-muted); font-size: 11.5px; line-height: 1.6; }
  .agent-handoff-ledger dl { display: grid; grid-column: 1 / -1; grid-template-columns: minmax(0, 1.5fr) minmax(150px, .65fr) minmax(130px, .55fr); gap: 12px; margin: 2px 0 0; }
  .agent-handoff-ledger dl > div { display: grid; gap: 1px; }
  .agent-handoff-ledger dt { color: var(--t-faint); font-size: 10px; }
  .agent-handoff-ledger dd { margin: 0; color: var(--t-ink-2); font-size: 11px; line-height: 1.45; }
  .agent-handoff-empty { margin: 10px 0 0; padding-top: 10px; border-top: 1px solid var(--t-line); color: var(--t-muted); font-size: 11.5px; }
  .case-layout:has(.task-report-review) { grid-template-columns: minmax(0, 1fr); }
  .case-layout:has(.task-report-review) > .case-roster { display: flex; gap: 8px; max-height: none; padding: 0 0 8px; overflow-x: auto; }
  .case-layout:has(.task-report-review) > .case-roster .case-student { flex: 0 0 240px; min-width: 0; }
}

.teacher-page button:focus-visible,
.teacher-page a:focus-visible,
.teacher-page textarea:focus-visible,
.teacher-page input:focus-visible,
.teacher-page select:focus-visible,
.original-list:focus-visible { outline: 2px solid var(--t-accent); outline-offset: 2px; }
.teacher-page input:hover:not(:disabled), .teacher-page textarea:hover:not(:disabled), .teacher-page select:hover:not(:disabled) { border-color: #A9AEB9; }

@media (max-width: 1100px) {
  .assessment-domain-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 980px) {
  .teacher-page { grid-template-columns: 188px minmax(0, 1fr); }
  .teacher-sidebar { padding-inline: 10px; }
  .workspace { padding-inline: 18px; }
  .case-layout, .split-layout, .lesson-layout { grid-template-columns: 1fr; }
  .warn-overview { grid-template-columns: 1fr; gap: 14px; }
  .warn-week { padding: 12px 0 0; border-inline-start: 0; border-top: 1px solid var(--t-line); }
  .case-roster { max-height: 300px; }
  .work-product-grid { grid-template-columns: 1fr; }
  .decision-brief { padding-left: 0; border-left: 0; border-top: 1px solid var(--t-line); }
  .evidence-sections { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .teacher-page { display: block; }
  .teacher-sidebar { position: sticky; height: auto; padding: 10px 10px 8px; }
  .teacher-brand { padding: 0 2px 8px; }
  .teacher-brand > span { width: 28px; height: 28px; font-size: 13px; }
  .teacher-brand small, .teacher-brand-meta { display: none; }
  .teacher-nav { display: flex; gap: 4px; padding-top: 8px; overflow-x: auto; }
  .teacher-nav button { flex: 0 0 auto; grid-template-columns: 18px auto auto; width: auto; min-height: 40px; padding: 6px 10px; white-space: nowrap; }
  .teacher-nav button > span:first-child { width: 18px; }
  .teacher-nav button.active { box-shadow: none; border-bottom: 2px solid var(--t-brand); border-radius: 3px 3px 0 0; }
  .teacher-sidebar-footer { position: absolute; top: 8px; right: 10px; display: flex; margin: 0; padding: 0; border: 0; }
  .teacher-sidebar-footer .teacher-user { padding: 4px; }
  .teacher-user-name { display: none; }
  .teacher-sidebar-footer .role-badge { display: none; }
  .teacher-sidebar-footer button { min-height: 36px; padding-inline: 8px; }
  .teacher-topbar { top: 96px; min-height: auto; padding: 10px 14px; }
  .teacher-topbar p { display: none; }
  .teacher-topbar h1 { font-size: 17px; }
  .teacher-search { width: min(240px, 52vw); }
  .workspace { padding: 14px 12px 28px; }
  .workspace > .panel { padding: 14px; }
}
@media (max-width: 560px) {
  .teacher-topbar { align-items: stretch; flex-direction: column; gap: 8px; }
  .teacher-search { width: 100%; }
  .teacher-search input { min-height: 40px; }
  .panel-title { flex-direction: column; align-items: stretch; }
  .panel-title > button { width: 100%; }
  .case-stage { padding: 14px; }
  .emotion-sections, .detail-stats { grid-template-columns: 1fr; }
  .detail-stat { border-inline-end: 0; border-bottom: 1px solid var(--t-line); }
  .detail-stat:last-child { border-bottom: 0; }
  .assessment-domain-grid { grid-template-columns: 1fr; }
  .case-stage-head, .original-list-head, .approval-meta { flex-direction: column; }
  .role-badge { align-self: stretch; text-align: center; }
  .account-row { align-items: flex-start; flex-wrap: wrap; }
  .assignment-control { flex: 1 1 100%; }
  .agent-conflict div, .task-row { grid-template-columns: 1fr; }
  .task-row > span { display: none; }
}
</style>
