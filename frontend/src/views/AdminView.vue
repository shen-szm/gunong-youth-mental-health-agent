<template>
  <div class="teacher-page">
    <aside class="teacher-sidebar" aria-label="教师工作台导航">
      <div class="teacher-brand">
        <span aria-hidden="true">咕</span>
        <div><strong>咕哝教师端</strong><small>校园支持数字员工 · v{{ teacherVersion }}</small><em>{{ userStore.isSuperAdmin ? '管理员教师' : '普通教师' }}</em></div>
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
          <span aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <em v-if="item.id === 'approvals' && pendingApprovalCount">{{ pendingApprovalCount }}</em>
        </button>
      </nav>
      <small class="teacher-nav-hint">左右滑动查看更多职责入口</small>
      <div class="teacher-sidebar-footer">
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

          <div class="case-layout">
            <div class="case-roster" aria-label="学生支持对象列表">
              <button v-for="student in filteredStudents" :key="student.id" :aria-pressed="caseStudent?.id === student.id" :class="['case-student', { selected: caseStudent?.id === student.id }]" @click="chooseCaseStudent(student)">
                <span class="avatar">{{ firstChar(studentName(student)) }}</span>
                <span class="case-student-main"><strong>{{ studentName(student) }}</strong><small>{{ riskText(student.risk_level) }} · {{ student.mood_count }} 条自愿记录</small></span>
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
                  <p>学生无需逐次申请或等待教师开通。文字对话仅发送去标识化结构特征，不发送聊天原文；安全分流仍由本地规则强制裁决。</p>
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
              <div class="chart-section"><h4>主动记录次数（近30天）</h4><div class="trend-chart" v-if="detail.trend?.length"><div class="trend-area"><div class="trend-grid" style="top:25%"></div><div class="trend-grid" style="top:50%"></div><div class="trend-grid" style="top:75%"></div><div v-for="d in detail.trend" :key="d.date" class="trend-col"><span class="trend-count">{{ d.count }}条</span><div class="trend-track"><div class="trend-bar" :style="{ height: Math.max(8, Number(d.count || 0) / maxTrendCount * 100) + '%', background: getMoodColor(d.dominant_label) }"></div></div><span class="trend-date">{{ String(d.date) }}</span></div></div></div><p v-else class="empty-state">近30天暂无主动记录</p></div>
              <div class="chart-section"><h4>记录标签分布</h4><div class="dist-bars" v-if="detail.distribution && Object.keys(detail.distribution).length"><div v-for="(count, label) in sortedDist" :key="label" class="dist-row"><span class="dist-emoji">{{ getEmoji(label) }}</span><span class="dist-label">{{ label }}</span><div class="dist-track"><div class="dist-fill" :style="{ width: getDistPct(count) + '%', background: getMoodColor(label) }"></div></div><span class="dist-count">{{ count }}次</span></div></div><p v-else class="empty-state">暂无分布数据</p></div>
              <div class="chart-section"><h4>💬 高频词汇</h4><div class="word-cloud-wrap" v-if="normalizedWordCloud.length"><div class="normal-word-cloud"><span v-for="(item, index) in normalizedWordCloud" :key="item.word + index" :class="['word-cloud-item', 'level-' + item.level, 'pos-' + (index % 18)]" :style="{ '--word-size': item.size + 'px', '--word-opacity': item.opacity }">{{ item.word }}</span></div></div><p v-else class="empty-state">暂无词云数据</p></div>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import axios from 'axios'
import TeacherTodayDashboard from '../components/TeacherTodayDashboard.vue'
import TeacherReviewReport from '../components/TeacherReviewReport.vue'
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
  { id: 'approvals', label: '权限审批', icon: '✓', group: '管理', adminOnly: true },
  { id: 'accounts', label: '账号职责', icon: '⌘', group: '管理', adminOnly: true },
]
const visibleNavItems = computed(() => teacherNavItems.filter(item => !item.adminOnly || userStore.isSuperAdmin))
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
  return { 开心: '😊', 平静: '😌', 焦虑: '😟', 难过: '😢', 愤怒: '😠' }[label] || '🙂'
}

function getMoodColor(label) {
  return { 开心: '#5f9f75', 平静: '#6d9f93', 焦虑: '#d3a13f', 难过: '#769fbd', 愤怒: '#c76558' }[label] || '#7b9088'
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
.teacher-page { min-height: 100vh; padding: 24px; background: #f4f7f5; color: #26332f; }
.teacher-hero { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; padding: 24px; border-radius: 20px; background: linear-gradient(135deg, #ffffff, #eaf3ef); border: 1px solid #dce8e2; }
.eyebrow { color: #4f7d70; font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.teacher-hero h2 { font-size: 30px; margin-bottom: 8px; }
.hero-copy { color: #60716b; max-width: 680px; line-height: 1.7; }
.hero-actions, .detail-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.primary-btn, .ghost-btn, .danger-btn { min-height: 36px; padding: 8px 15px; border-radius: 10px; font-size: 14px; transition: transform .18s ease, background .18s ease; }
.primary-btn { background: #4f7d70; color: white; }
.ghost-btn { background: #eef4f1; color: #36554d; }
.danger-btn { background: #f5e5e1; color: #b85c50; }
.primary-btn:hover, .ghost-btn:hover, .danger-btn:hover { transform: translateY(-1px); }
.primary-btn:disabled { opacity: .6; cursor: not-allowed; transform: none; }
.error-screen { margin-top: 20px; padding: 48px; border-radius: 18px; background: white; text-align: center; color: #b85c50; }
.overview-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 18px 0; }
.metric-card, .risk-card { padding: 18px; border-radius: 16px; background: white; border: 1px solid #e1e9e5; }
.metric-card span, .risk-card span { display: block; color: #53645e; font-size: 13px; }
.metric-card strong { display: block; margin: 8px 0 4px; font-size: 30px; }
.metric-card small { color: #70827b; }
.metric-card.warning strong { color: #c46d4c; }
.risk-bars { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
.risk-bars b, .risk-label, .status-pill { border-radius: 999px; padding: 5px 9px; font-size: 12px; }
.risk-low, .risk-label.low { background: #e7f4ec; color: #4f7d70; }
.risk-mid, .risk-label.middle, .risk-label.medium { background: #fff5d7; color: #9b7528; }
.risk-high, .risk-label.high { background: #fde8e1; color: #ba594b; }
.up { color: #4f8a65 !important; } .down { color: #bd6255 !important; }
.teacher-tabs { display: flex; gap: 8px; margin-bottom: 14px; position: sticky; top: 0; z-index: 5; padding: 8px 0; background: #f4f7f5; }
.teacher-tabs button { padding: 10px 18px; border-radius: 12px; background: #e8efeb; color: #52645e; font-weight: 600; }
.teacher-tabs button.active { background: #4f7d70; color: white; }
.panel { padding: 20px; border-radius: 18px; background: white; border: 1px solid #e1e9e5; }
.panel-title { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }
.panel-title h3 { font-size: 22px; margin-bottom: 6px; }
.panel-title p { color: #6f807a; line-height: 1.6; }
.split-layout, .lesson-layout { display: grid; grid-template-columns: minmax(320px, .9fr) minmax(360px, 1.1fr); gap: 18px; }
.warning-list, .template-list, .account-list, .student-grid { display: grid; gap: 10px; }
.warning-item, .student-card, .template-list button, .account-row { width: 100%; text-align: left; display: flex; gap: 12px; align-items: center; padding: 14px; border-radius: 14px; background: #f7faf8; border: 1px solid #e2ebe6; }
.warning-item.selected, .student-card.selected, .template-list button.selected { border-color: #4f7d70; background: #edf6f2; }
.warning-main { flex: 1; display: grid; gap: 4px; }
.warning-main small, .student-card small, .template-list small, .account-row small { color: #75857f; line-height: 1.5; }
.risk-dot { width: 10px; height: 10px; border-radius: 50%; background: #8bb7a9; }
.warning-item.high .risk-dot { background: #d46f61; } .warning-item.middle .risk-dot, .warning-item.medium .risk-dot { background: #d5a73f; }
.section-kicker { display: inline-flex; margin-bottom: 10px; padding: 4px 9px; border-radius: 999px; background: #eaf4f0; color: #4f7d70; font-size: 12px; font-weight: 800; }
.detail-card, .profile-card, .lesson-result { padding: 18px; border-radius: 16px; background: #f8fbf9; border: 1px solid #e1e9e5; }
.detail-head { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.detail-head h4, .profile-card h4, .lesson-result h4 { font-size: 18px; margin-top: 8px; }
.detail-copy, .suggestion-box p, .profile-card p { color: #5f706a; line-height: 1.8; }
.suggestion-box { margin: 14px 0; padding: 14px; border-radius: 12px; background: #eef5f1; }
.handle-box, .lesson-compose label { display: grid; gap: 8px; font-weight: 700; color: #455a53; }
textarea, input { width: 100%; border: 1px solid #d9e5df; border-radius: 12px; background: white; padding: 11px 12px; font: inherit; color: #26332f; }
textarea { min-height: 96px; resize: vertical; }
.student-grid { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.student-card { display: grid; justify-items: start; }
.avatar { width: 38px; height: 38px; border-radius: 50%; background: #5b8c7e; color: white; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; }
.profile-card { margin-top: 16px; display: grid; gap: 14px; }
.profile-metrics { display: flex; gap: 10px; flex-wrap: wrap; }
.profile-metrics span { padding: 8px 10px; border-radius: 10px; background: white; color: #60716b; }
.emotion-detail-panel { margin-top: 16px; padding: 18px; border-radius: 16px; background: #fbfdfc; border: 1px solid #e1e9e5; }
.panel-title.compact { margin-bottom: 14px; }
.detail-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }
.detail-stat { background: white; border-radius: 12px; padding: 13px 10px; text-align: center; border: 1px solid #e5ede8; }
.ds-value { font-size: 22px; font-weight: 800; color: #4f7d70; }
.ds-label { font-size: 12px; color: #75857f; margin-top: 4px; }
.emotion-sections { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.chart-section { padding: 14px; border-radius: 14px; background: white; border: 1px solid #e5ede8; }
.chart-section h4 { margin-bottom: 10px; font-size: 15px; }
.trend-chart { background: #f7faf8; border-radius: 12px; padding: 12px 8px; }
.trend-area { display: flex; align-items: flex-end; gap: 4px; position: relative; height: 130px; }
.trend-grid { position: absolute; left: 0; right: 0; height: 1px; background: #dfe8e3; }
.trend-col { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; position: relative; z-index: 1; height: 100%; }
.trend-track { flex: 1; width: 100%; display: flex; align-items: flex-end; justify-content: center; }
.trend-bar { width: 60%; max-width: 24px; min-height: 4px; border-radius: 5px 5px 0 0; }
.trend-val, .trend-date { font-size: 10px; color: #75857f; white-space: nowrap; }
.dist-bars { display: grid; gap: 8px; }
.dist-row { display: flex; align-items: center; gap: 8px; }
.dist-emoji { width: 24px; text-align: center; }
.dist-label { width: 42px; font-size: 13px; }
.dist-track { flex: 1; height: 8px; border-radius: 999px; background: #edf3f0; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 999px; }
.dist-count { width: 42px; text-align: right; color: #75857f; font-size: 12px; }
.word-cloud-wrap { min-height: 260px; padding: 18px; background: #f7faf8; border-radius: 12px; overflow: hidden; }
.normal-word-cloud { position: relative; min-height: 224px; }
.word-cloud-item { position: absolute; left: 50%; top: 50%; display: inline-block; max-width: 220px; color: #4f7d70; font-size: var(--word-size); font-weight: 800; line-height: 1.1; white-space: nowrap; opacity: var(--word-opacity); text-shadow: 0 8px 22px rgba(58, 91, 79, .08); transform: translate(-50%, -50%); }
.word-cloud-item.level-hot { color: #315d51; font-weight: 900; }
.word-cloud-item.level-mid { color: #9b7528; }
.word-cloud-item.level-soft { color: #6f8ca0; font-weight: 700; }
.word-cloud-item.pos-0 { transform: translate(-50%, -50%) scale(1.08); }
.word-cloud-item.pos-1 { transform: translate(-112%, -118%) rotate(-4deg); }
.word-cloud-item.pos-2 { transform: translate(18%, -112%) rotate(3deg); }
.word-cloud-item.pos-3 { transform: translate(-120%, 16%) rotate(2deg); }
.word-cloud-item.pos-4 { transform: translate(28%, 20%) rotate(-3deg); }
.word-cloud-item.pos-5 { transform: translate(-50%, 118%) rotate(1deg); }
.word-cloud-item.pos-6 { transform: translate(-156%, -52%) rotate(5deg); }
.word-cloud-item.pos-7 { transform: translate(72%, -48%) rotate(-5deg); }
.word-cloud-item.pos-8 { transform: translate(-158%, 78%) rotate(-2deg); }
.word-cloud-item.pos-9 { transform: translate(82%, 86%) rotate(4deg); }
.word-cloud-item.pos-10 { transform: translate(-14%, -174%) rotate(2deg); }
.word-cloud-item.pos-11 { transform: translate(-24%, 174%) rotate(-3deg); }
.word-cloud-item.pos-12 { transform: translate(-198%, -8%) scale(.92); }
.word-cloud-item.pos-13 { transform: translate(116%, -6%) scale(.92); }
.word-cloud-item.pos-14 { transform: translate(-210%, -104%) scale(.86); }
.word-cloud-item.pos-15 { transform: translate(126%, -104%) scale(.86); }
.word-cloud-item.pos-16 { transform: translate(-218%, 128%) scale(.82); }
.word-cloud-item.pos-17 { transform: translate(132%, 132%) scale(.82); }
.analysis-card { min-height: 120px; padding: 14px; border-radius: 12px; background: #f7faf8; color: #52645e; line-height: 1.8; }
.analysis-sections { display: grid; gap: 10px; }
.analysis-block { padding: 13px 14px; border-radius: 12px; background: white; border: 1px solid #e3ece7; }
.analysis-block span { display: inline-flex; margin-bottom: 5px; padding: 3px 8px; border-radius: 999px; background: #eaf4f0; color: #4f7d70; font-size: 12px; font-weight: 800; }
.analysis-block h5 { margin: 0 0 6px; font-size: 15px; color: #2f403b; }
.analysis-block ul { margin: 0; padding-left: 18px; }
.analysis-block li { margin: 4px 0; color: #52645e; line-height: 1.65; }
.analysis-block.finding span { background: #fff4d7; color: #9b7528; }
.analysis-block.advice span { background: #e9f0fa; color: #5c718f; }
.analysis-empty { color: #53645e; }
.analysis-loading { display: flex; gap: 6px; padding: 10px 0; }
.analysis-loading .dot { width: 9px; height: 9px; border-radius: 50%; background: #4f7d70; animation: bounce 1.2s infinite both; }
.analysis-loading .dot:nth-child(2) { animation-delay: .2s; }
.analysis-loading .dot:nth-child(3) { animation-delay: .4s; }
@keyframes bounce { 0%,100% { opacity:.35; transform: translateY(0); } 50% { opacity:1; transform: translateY(-4px); } }

.template-list button { display: grid; }
.lesson-compose { display: grid; gap: 14px; align-content: start; }
.lesson-result { margin-top: 16px; }
.lesson-result pre { margin-top: 10px; white-space: pre-wrap; line-height: 1.8; color: #3c4a45; font-family: inherit; }
.account-row { justify-content: space-between; }
.account-row div { flex: 1; display: grid; gap: 3px; }
.assignment-control { display: flex !important; align-items: end; gap: 8px; flex: 0 1 360px !important; }
.assignment-control label { display: grid; gap: 5px; color: #52665f; font-size: 12px; }
.assignment-control select { min-height: 38px; padding: 7px 9px; border: 2px solid #778e85; border-radius: 9px; background: #fff; color: #26332f; }
.empty-state { padding: 18px; text-align: center; color: #53645e; background: #f8fbf9; border-radius: 14px; }
.empty-state.tall { min-height: 260px; display: grid; place-items: center; }
.teacher-tabs button span { display: inline-grid; place-items: center; min-width: 20px; height: 20px; margin-left: 5px; border-radius: 999px; background: #b85c50; color: #fff; font-size: 11px; }
.case-layout { display: grid; grid-template-columns: minmax(280px, .78fr) minmax(420px, 1.22fr); gap: 18px; }
.case-roster, .approval-list, .original-list { display: grid; align-content: start; gap: 10px; }
.case-student { width: 100%; display: grid; grid-template-columns: 42px minmax(0, 1fr); gap: 10px 12px; align-items: center; padding: 14px; border: 1px solid #e0e8e4; border-radius: 14px; background: #f9fbfa; text-align: left; }
.case-student.selected { border-color: #4f7d70; background: #edf6f2; box-shadow: 0 0 0 2px rgba(79, 125, 112, .1); }
.case-student-main { display: grid; gap: 4px; }
.case-student-main small { color: #566a63; }
.access-pill { grid-column: 2; justify-self: start; padding: 4px 8px; border-radius: 999px; background: #eef2f0; color: #465b54; font-size: 11px; font-style: normal; font-weight: 700; }
.access-pill.approved, .access-pill.direct { background: #dff0e7; color: #2f674f; }
.access-pill.pending { background: #fff0ca; color: #765915; }
.access-pill.rejected { background: #f7e3df; color: #9a4d42; }
.case-stage { min-height: 420px; padding: 20px; border: 1px solid #e0e8e4; border-radius: 16px; background: #fff; }
.case-stage-head, .original-list-head, .approval-meta, .handoff-card { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; }
.case-stage-head h4, .original-list-head h4, .handoff-card h4, .approval-card h4 { margin: 4px 0 0; font-size: 18px; }
.role-badge { align-self: start; padding: 7px 10px; border-radius: 999px; background: #eef4f1; color: #36554d; font-size: 12px; font-weight: 800; }
.role-badge.admin { background: #e2ede8; color: #285c4d; }
.access-application, .approval-waiting, .authorized-case { display: grid; gap: 14px; margin-top: 18px; }
.access-application label { display: grid; gap: 7px; color: #496159; font-weight: 700; }
.access-application textarea { min-height: 112px; padding: 12px; border: 2px solid #778e85; border-radius: 10px; resize: vertical; color: #26332f; background: #fff; }
.approval-waiting, .privacy-notice { padding: 16px; border-radius: 12px; background: #fff7df; color: #654f18; }
.privacy-notice { display: grid; gap: 5px; background: #eef5f2; color: #36554d; }
.student-ai-authorization { display:grid; gap:12px; margin-top:16px; padding:16px; border:1px solid #d8e3dd; border-radius:14px; background:#f7faf8; }
.student-ai-authorization h4 { margin:4px 0 6px; }
.student-ai-authorization p,.student-ai-authorization small { margin:0; color:#5d7169; line-height:1.55; }
.authority-check { display:grid; grid-template-columns:18px minmax(0,1fr); gap:9px; align-items:start; color:#435a51; line-height:1.55; }
.authority-check input { width:18px; height:18px; margin:2px 0 0; accent-color:#5f8977; }
.authority-expiry { display:flex; align-items:center; gap:10px; color:#435a51; }
.authority-expiry select { min-height:38px; padding:0 10px; border:1px solid #ccd9d3; border-radius:9px; background:#fff; }
.agent-brief { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.case-command-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 22px 0 12px; }
.case-command-head h4 { margin: 3px 0 0; font-size: 22px; color: #203c33; }
.risk-decision { padding: 7px 11px; border-radius: 999px; font-size: 12px; font-weight: 800; color: #35594c; background: #e3f1eb; border: 1px solid #c9dfd5; }
.risk-decision.urgent { color: #8c332d; background: #fff0ed; border-color: #efc2bb; }
.risk-decision.professional { color: #714f14; background: #fff6db; border-color: #e9d390; }
.agent-pipeline { display: grid; gap: 8px; margin-bottom: 14px; }
.agent-pipeline article { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 12px 14px; border-radius: 14px; background: #f5f9f7; border: 1px solid #dfebe5; }
.agent-pipeline article > span { color: #4f6d61; font: 700 11px/1 monospace; }
.agent-pipeline article div { display: grid; gap: 3px; }
.agent-pipeline article strong { color: #27483d; font-size: 14px; }
.agent-pipeline article small { color: #4d625a; }
.agent-pipeline article em { color: #3d765f; font-style: normal; font-size: 12px; font-weight: 700; }
.desktop-case-agent-live { display:none; }
.agent-source-badge { display:none; }
.agent-handoff-ledger { display: none; }
@media (min-width:1024px) {
  .desktop-case-agent-live { display:grid; grid-template-columns:minmax(260px,.8fr) minmax(0,1.6fr); gap:18px; margin:14px 0; padding:16px; border:1px solid #dce8e2; border-radius:14px; background:linear-gradient(145deg,#f7fbf9,#fffaf2); }
  .desktop-case-agent-live h4 { margin:4px 0 6px; color:#29483d; }
  .desktop-case-agent-live p { margin:0; color:#53665f; font-size:12px; line-height:1.55; }
  .desktop-case-agent-live ol { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:6px; margin:0; padding:0; list-style:none; }
  .desktop-case-agent-live li { display:flex; gap:7px; min-width:0; padding:9px; border-radius:10px; background:#eef3f0; }
  .desktop-case-agent-live li i { display:grid; place-items:center; width:20px; height:20px; flex:0 0 auto; border-radius:6px; color:#6d7b76; background:#dde6e2; font-style:normal; }
  .desktop-case-agent-live li.complete i { color:#fff; background:#4e8069; }
  .desktop-case-agent-live li.running i { color:#523d19; background:#e4c379; }
  .desktop-case-agent-live li span,.desktop-case-agent-live li strong,.desktop-case-agent-live li small { display:block; min-width:0; }
  .desktop-case-agent-live li strong { overflow:hidden; color:#314c42; font-size:10px; text-overflow:ellipsis; white-space:nowrap; }
  .desktop-case-agent-live li small { margin-top:3px; color:#687a73; font-size:9px; line-height:1.35; }
  .case-processing-state { display:flex; align-items:center; gap:10px; padding:12px; border-radius:12px; background:#eef3f0; }
  .case-processing-state i { display:grid; place-items:center; width:28px; height:28px; border-radius:8px; color:#523d19; background:#e4c379; font-style:normal; animation:agent-wait-pulse 1.2s ease-in-out infinite; }
  .case-processing-state strong,.case-processing-state small { display:block; }
  .case-processing-state strong { color:#314c42; font-size:12px; }
  .case-processing-state small { margin-top:3px; color:#687a73; font-size:10px; }
  .case-result-badges { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px; }
  .agent-source-badge { display:inline-flex; align-items:center; padding:6px 10px; border:1px solid #d4e2dc; border-radius:999px; color:#315e51; background:#f3f8f5; font-size:11px; font-weight:800; }
  .agent-handoff-ledger { display: block; margin: 4px 0 16px; padding: 16px 0 0; border-top: 1px solid #dce6e1; }
  .agent-handoff-ledger > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
  .agent-handoff-ledger > header h4 { margin: 4px 0 0; color: #29483d; font-size: 17px; }
  .agent-handoff-ledger > header p { display: flex; align-items: baseline; gap: 5px; margin: 0; color: #5b7068; }
  .agent-handoff-ledger > header p strong { color: #285b4b; font-size: 20px; }
  .agent-handoff-ledger > header p span { font-size: 11px; }
  .agent-handoff-boundary { max-width: 76ch; margin: 8px 0 11px; color: #586c64; font-size: 12px; line-height: 1.55; }
  .agent-handoff-ledger ol { margin: 0; padding: 0; list-style: none; border-bottom: 1px solid #e1e9e5; }
  .agent-handoff-ledger li { display: grid; grid-template-columns: minmax(210px, .85fr) minmax(0, 1.3fr); gap: 8px 24px; padding: 13px 0; border-top: 1px solid #e1e9e5; }
  .agent-handoff-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 10px; }
  .agent-handoff-meta code { color: #49645a; font-size: 10px; }
  .agent-handoff-meta time { color: #677a73; font-size: 10px; }
  .agent-handoff-meta span { padding: 3px 6px; border-radius: 999px; color: #6c571c; background: #f4e8c7; font-size: 10px; font-weight: 800; }
  .agent-handoff-meta span.is-verified { color: #2f674f; background: #dff0e7; }
  .agent-handoff-meta span.is-failed { color: #8b4037; background: #f7e3df; }
  .agent-handoff-meta span.is-attention { color: #6c571c; background: #f4e8c7; }
  .agent-handoff-result strong { color: #29483d; font-size: 13px; }
  .agent-handoff-result p { margin: 4px 0 0; color: #53675f; font-size: 12px; line-height: 1.55; }
  .agent-handoff-ledger dl { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(160px, .65fr) minmax(140px, .55fr); gap: 12px; margin: 2px 0 0; }
  .agent-handoff-ledger dl > div { display: grid; gap: 2px; }
  .agent-handoff-ledger dt { color: #697a73; font-size: 10px; }
  .agent-handoff-ledger dd { margin: 0; color: #344c43; font-size: 11px; line-height: 1.45; }
  .agent-handoff-empty { margin: 10px 0 0; padding: 12px 0; border-top: 1px solid #e1e9e5; color: #60726b; font-size: 12px; }
}
@keyframes agent-wait-pulse { 50% { opacity:.55; } }
.work-product-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.assessment-brief { margin-top: 12px; padding: 16px; border: 1px solid rgba(104,82,64,.16); border-radius: 16px; background: rgba(255,250,242,.72); }
.assessment-emotion { color: #5e4b3f; font-weight: 700; }
.assessment-domain-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 8px; margin: 12px 0; }
.assessment-domain-grid article { padding: 11px; border-radius: 12px; background: rgba(255,255,255,.68); }
.assessment-domain-grid span,.assessment-domain-grid strong { display: block; }.assessment-domain-grid span { color: #7f6e61; font-size: 12px; }.assessment-domain-grid p { margin: 5px 0 0; color: #6d5d52; font-size: 12px; line-height: 1.45; }
.evidence-brief, .decision-brief, .agent-conflict, .task-board { padding: 16px; border: 1px solid #dfe9e4; border-radius: 16px; background: #fff; }
.evidence-brief h4, .decision-brief h4 { margin: 5px 0 8px; color: #27483d; font-size: 17px; }
.evidence-brief p, .decision-brief p, .agent-conflict p { color: #52675f; line-height: 1.65; }
.evidence-brief small { color: #52675f; word-break: break-all; }
.decision-brief ul { margin: 10px 0 0; padding-left: 18px; color: #4d625a; font-size: 12px; line-height: 1.75; }
.evidence-links { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
.evidence-links button { padding: 3px 6px; border: 1px solid #b7ccc3; border-radius: 7px; color: #345d50; background: #f2f8f5; font: 700 10px/1.2 monospace; cursor: pointer; }
.agent-conflict { margin-top: 12px; background: #fffaf2; border-color: #ebddc2; }
.agent-conflict div { display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: center; margin-top: 8px; }
.agent-conflict strong { color: #6a4d23; }
.agent-conflict p { margin: 0; }
.agent-conflict em { color: #5f4b25; font-size: 12px; font-style: normal; }
.agent-conflict .evidence-links { grid-column: 1 / -1; }
.task-board { margin-top: 12px; }
.task-row { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 12px 0; border-top: 1px solid #edf1ef; }
.task-row > span { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 8px; color: #4f7d70; background: #edf6f2; font-weight: 800; }
.task-row div { display: grid; gap: 3px; }
.task-row strong { color: #2d463e; }
.task-row small { color: #52675f; }
.task-row button { padding: 8px 12px; border: 1px solid #b9d1c6; border-radius: 10px; color: #426b5e; background: #f4faf7; cursor: pointer; }
.task-row button.confirmed { color: #fff; background: #4f7d70; border-color: #4f7d70; }
.agent-brief > div { padding: 13px; border: 1px solid #e0e8e4; border-radius: 12px; background: #f8faf9; }
.agent-brief span { display: block; margin-bottom: 6px; color: #53645e; font-size: 11px; }
.agent-brief strong { font-size: 13px; line-height: 1.55; }
.original-list { max-height: 430px; padding-right: 4px; overflow: auto; }
.original-list-head { position: sticky; top: 0; padding: 8px 0; background: #fff; z-index: 1; }
.original-list-head small { color: #53645e; }
.original-record { padding: 14px; border: 1px solid #e2ebe6; border-radius: 12px; background: #fafcfb; }
.original-record > div { display: flex; justify-content: space-between; gap: 12px; color: #50645d; font-size: 11px; }
.original-record p { margin: 9px 0 0; color: #2f3d38; line-height: 1.7; white-space: pre-wrap; }
.original-record p { overflow-wrap: anywhere; }
.handoff-card { padding: 16px; border-radius: 14px; background: #eaf3ef; }
.handoff-card p { margin: 7px 0 0; max-width: 660px; color: #60716b; line-height: 1.65; }
.link-btn { display: inline-flex; align-items: center; justify-content: center; text-decoration: none; white-space: nowrap; }
.case-message { padding: 10px 12px; border-radius: 10px; background: #eef4f1; color: #36554d; }
.approval-card { padding: 18px; border: 1px solid #e0e8e4; border-radius: 14px; background: #fff; }
.approval-card p { color: #52665f; line-height: 1.65; }
.approval-card small { color: #53645e; }
.approval-actions { display: flex; gap: 10px; margin-top: 14px; }
.review-note { padding: 9px 11px; border-radius: 9px; background: #f3f6f4; }
.review-confirm { display: grid; gap: 10px; margin-top: 14px; padding: 14px; border: 2px solid #789087; border-radius: 12px; background: #f8fbf9; }
.review-confirm label { display: grid; gap: 6px; color: #435850; font-weight: 700; }
.review-confirm textarea { min-height: 78px; border: 2px solid #778e85; }
.approval-error { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px; border-radius: 12px; background: #f8e7e3; color: #783c34; }
.teacher-page button:focus-visible, .teacher-page a:focus-visible, .teacher-page textarea:focus-visible, .teacher-page input:focus-visible, .original-list:focus-visible { outline: 3px solid #245f82; outline-offset: 3px; }
.teacher-page .danger-btn { color: #813b32; background: #fae8e4; }
@media (max-width: 1000px) { .case-layout { grid-template-columns: 1fr; } .agent-brief, .work-product-grid { grid-template-columns: 1fr; } .assessment-domain-grid { grid-template-columns: repeat(2,minmax(0,1fr)); } }
@media (max-width: 900px) { .teacher-page { padding: 14px; } .teacher-hero, .panel-title { flex-direction: column; } .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .split-layout, .lesson-layout, .emotion-sections { grid-template-columns: 1fr; } .teacher-tabs { overflow-x: auto; } }
@media (max-width: 620px) { .case-stage-head, .original-list-head, .handoff-card { flex-direction: column; } .role-badge { align-self: stretch; text-align: center; } }
@media (max-width: 560px) { .overview-grid, .detail-stats { grid-template-columns: 1fr; } .teacher-tabs button { white-space: nowrap; } .account-row { align-items: flex-start; } .agent-conflict div, .task-row { grid-template-columns: 1fr; } .task-row > span { display: none; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }

/* v5.1 教师工作台应用壳：稳定导航承载高密度任务，玻璃仅用于粘性工具栏。 */
.teacher-page {
  --teacher-sidebar: #18312a;
  --teacher-sidebar-2: #214038;
  --teacher-canvas: #eef2f0;
  --teacher-surface: #ffffff;
  --teacher-ink: #22342e;
  --teacher-muted: #5f716a;
  --teacher-line: #d9e2de;
  --teacher-accent: #315e51;
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  min-height: 100dvh;
  padding: 0;
  color: var(--teacher-ink);
  background: var(--teacher-canvas);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.teacher-sidebar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  height: 100dvh;
  padding: 18px 14px;
  color: #eff6f3;
  background: var(--teacher-sidebar);
}
.teacher-brand { display: flex; gap: 11px; align-items: center; padding: 4px 7px 20px; }
.teacher-brand > span { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; color: #18312a; background: #d9ca94; font: 900 16px/1 ui-monospace, Consolas, monospace; }
.teacher-brand div { min-width: 0; display: grid; gap: 2px; }
.teacher-brand strong { font-size: 14px; }
.teacher-brand small { color: rgba(239, 246, 243, .62); font-size: 10px; }
.teacher-brand em { color: #d9ca94; font-size: 9px; font-style: normal; }
.teacher-nav-hint { display: none; }
.teacher-nav { display: grid; gap: 4px; }
.teacher-nav button {
  display: grid;
  grid-template-columns: 25px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  width: 100%;
  min-height: 42px;
  padding: 8px 10px;
  border: 0;
  border-radius: 9px;
  color: rgba(239, 246, 243, .72);
  background: transparent;
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.teacher-nav button > span:first-child { display: grid; place-items: center; width: 24px; height: 24px; color: rgba(239, 246, 243, .72); font: 800 13px/1 ui-monospace, Consolas, monospace; }
.teacher-nav button:hover { color: #fff; background: rgba(255,255,255,.07); }
.teacher-nav button.active { color: #fff; background: var(--teacher-sidebar-2); }
.teacher-nav button.active > span:first-child { color: #d9ca94; }
.teacher-nav em { display: grid; place-items: center; min-width: 20px; height: 20px; padding: 0 5px; border-radius: 999px; color: #492e28; background: #e6b6aa; font-size: 10px; font-style: normal; font-weight: 900; }
.teacher-sidebar-footer { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: auto; padding-top: 14px; border-top: 1px solid rgba(255,255,255,.1); }
.teacher-sidebar-footer .role-badge { grid-column: 1 / -1; margin-bottom: 3px; color: #d9ebe4; background: rgba(255,255,255,.08); text-align: center; }
.teacher-sidebar-footer button { min-height: 36px; padding: 7px; border: 0; border-radius: 8px; color: rgba(239,246,243,.75); background: rgba(255,255,255,.06); font: inherit; font-size: 11px; cursor: pointer; }
.teacher-sidebar-footer button:hover { color: #fff; background: rgba(255,255,255,.11); }
.teacher-shell { min-width: 0; }
.teacher-topbar {
  position: sticky;
  top: 0;
  z-index: 15;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
  min-height: 76px;
  padding: 12px 24px;
  border-bottom: 1px solid rgba(207, 219, 214, .92);
  background: rgba(247, 249, 248, .9);
  backdrop-filter: blur(18px) saturate(1.08);
}
.teacher-topbar p, .teacher-topbar h1 { margin: 0; }
.teacher-topbar p { color: #64756f; font-size: 11px; }
.teacher-topbar h1 { margin-top: 3px; color: #20342e; font-size: 20px; letter-spacing: -.02em; }
.teacher-search { position: relative; width: min(340px, 42vw); }
.teacher-search input { width: 100%; min-height: 42px; padding: 9px 58px 9px 13px; border: 1px solid #cbd9d3; border-radius: 10px; color: #273a34; background: #fff; font: inherit; font-size: 13px; }
.teacher-search input::placeholder { color: #61736c; }
.teacher-search kbd { position: absolute; top: 50%; right: 9px; padding: 3px 6px; border: 1px solid #cbd7d2; border-radius: 6px; color: #5a6e67; background: #f3f6f4; font: 700 10px/1.2 ui-monospace, Consolas, monospace; transform: translateY(-50%); }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.workspace { width: min(1480px, 100%); margin: 0 auto; padding: 22px 24px 38px; }
.workspace > .panel { padding: 20px; border: 0; border-radius: 14px; background: var(--teacher-surface); box-shadow: 0 4px 8px rgba(34, 55, 48, .07); }
.panel-title { margin-bottom: 16px; }
.panel-title h3 { margin: 0 0 5px; color: #243a33; font-size: 19px; letter-spacing: -.015em; }
.panel-title p { max-width: 72ch; margin: 0; color: var(--teacher-muted); font-size: 13px; line-height: 1.55; }
.section-kicker { margin-bottom: 7px; padding: 3px 7px; border-radius: 6px; color: #3f665a; background: #edf4f1; font-size: 10px; }
.primary-btn, .ghost-btn, .danger-btn { min-height: 40px; border-radius: 9px; }
.primary-btn { background: var(--teacher-accent); }
.ghost-btn { color: #345a4f; background: #edf4f1; }
.danger-btn { color: #813b32; background: #fae8e4; }
.primary-btn:hover, .ghost-btn:hover, .danger-btn:hover { transform: none; filter: brightness(.97); }
.case-layout { grid-template-columns: minmax(250px, .7fr) minmax(460px, 1.3fr); }
.case-roster { max-height: calc(100dvh - 170px); padding-right: 4px; overflow-y: auto; }
.case-student, .warning-item, .student-card, .account-row { border-color: #dde6e2; border-radius: 11px; background: #f6f8f7; }
.case-student.selected, .warning-item.selected, .student-card.selected { border-color: #4f7d70; background: #edf4f1; box-shadow: none; }
.case-stage { border-color: #dbe4e0; border-radius: 12px; }
.agent-pipeline article { border: 0; border-radius: 10px; background: #f3f7f5; }
.evidence-brief, .decision-brief, .agent-conflict, .task-board, .approval-card { border-radius: 12px; }
.detail-card, .profile-card, .lesson-result, .emotion-detail-panel { border-radius: 12px; }
.word-cloud-wrap { min-height: 220px; }
.analysis-title { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
.analysis-title h4 { margin: 0; }
.analysis-title small, .analysis-source { color: #61736c; font-size: 10px; }
.analysis-source { margin: 0 0 10px; padding: 8px 10px; border-radius: 8px; background: #f1f5f3; line-height: 1.5; }
.trend-count { color: #536b63; font-size: 9px; }
.teacher-page button:focus-visible,
.teacher-page a:focus-visible,
.teacher-page textarea:focus-visible,
.teacher-page input:focus-visible,
.teacher-page select:focus-visible,
.original-list:focus-visible { outline: 3px solid #245f82; outline-offset: 2px; }

@media (max-width: 980px) {
  .teacher-page { grid-template-columns: 196px minmax(0, 1fr); }
  .teacher-sidebar { padding-inline: 10px; }
  .workspace { padding-inline: 18px; }
  .case-layout { grid-template-columns: 1fr; }
  .case-roster { max-height: 300px; }
}
@media (max-width: 760px) {
  .teacher-page { display: block; }
  .teacher-sidebar { position: sticky; height: auto; padding: 9px 10px; }
  .teacher-brand { padding: 0 2px 8px; }
  .teacher-brand > span { width: 32px; height: 32px; }
  .teacher-nav { display: flex; gap: 5px; overflow-x: auto; padding-bottom: 2px; }
  .teacher-nav button { flex: 0 0 auto; grid-template-columns: 20px auto auto; min-height: 44px; width: auto; white-space: nowrap; }
  .teacher-nav button > span:first-child { width: 20px; }
  .teacher-nav-hint { display: block; padding: 3px 4px 0; color: rgba(239,246,243,.58); font-size: 9px; }
  .teacher-sidebar-footer { position: absolute; top: 8px; right: 10px; display: flex; margin: 0; padding: 0; border: 0; }
  .teacher-sidebar-footer .role-badge { display: none; }
  .teacher-sidebar-footer button { min-height: 44px; padding-inline: 9px; }
  .teacher-topbar { top: 114px; min-height: auto; padding: 11px 14px; }
  .teacher-topbar p { display: none; }
  .teacher-topbar h1 { font-size: 18px; }
  .teacher-search { width: min(260px, 56vw); }
  .workspace { padding: 16px 12px 28px; }
  .workspace > .panel { padding: 15px; }
}
@media (max-width: 520px) {
  .teacher-topbar { align-items: stretch; flex-direction: column; gap: 8px; }
  .teacher-search { width: 100%; }
  .teacher-search input { min-height: 44px; }
  .panel-title { align-items: stretch; }
  .panel-title > button { width: 100%; }
  .case-stage { padding: 14px; }
  .work-product-grid, .emotion-sections, .detail-stats { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .teacher-page *, .teacher-page *::before, .teacher-page *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; }
}

/* v5.1.0-alpha.30 desktop teacher workbench refinement.
   Product UI stays familiar and dense; glass is reserved for the sticky toolbar. */
@media (min-width: 761px) {
  .teacher-page {
    --teacher-sidebar: var(--ui-forest-950, #15382f);
    --teacher-sidebar-2: #285247;
    --teacher-canvas: var(--ui-canvas, #f1f4f2);
    --teacher-surface: var(--ui-surface, #ffffff);
    --teacher-ink: var(--ui-ink, #1f332c);
    --teacher-muted: var(--ui-muted, #566a62);
    --teacher-line: var(--ui-line, #d5dfda);
    --teacher-accent: var(--ui-forest-650, #2f6758);
    grid-template-columns: 244px minmax(0, 1fr);
  }
  .teacher-sidebar {
    padding: 20px 14px 16px;
    background: var(--teacher-sidebar);
    box-shadow: inset -1px 0 rgba(255,255,255,.07);
  }
  .teacher-brand {
    gap: 12px;
    padding: 2px 8px 18px;
    margin-bottom: 6px;
  }
  .teacher-brand > span {
    width: 40px;
    height: 40px;
    color: #193a31;
    background: var(--ui-gold-300, #ead49a);
  }
  .teacher-brand strong { font-size: 15px; letter-spacing: -.01em; }
  .teacher-brand small { color: rgba(244, 250, 247, .7); }
  .teacher-brand em { color: var(--ui-gold-300, #ead49a); }
  .teacher-nav { gap: 3px; }
  .teacher-nav button {
    min-height: 44px;
    border-radius: 9px;
    color: rgba(244, 250, 247, .76);
    transition: color var(--ui-duration-fast, 180ms) ease, background-color var(--ui-duration-fast, 180ms) ease;
  }
  .teacher-nav button:hover { background: rgba(255,255,255,.075); }
  .teacher-nav button.active { background: #285247; }
  .teacher-nav button.active > span:first-child {
    border-radius: 7px;
    color: #ead49a;
    background: rgba(234, 212, 154, .1);
  }
  .teacher-sidebar button:focus-visible { outline-color: #f5dda0; }
  .teacher-sidebar-footer button { transition: color 180ms ease, background-color 180ms ease; }

  .teacher-topbar {
    min-height: 72px;
    padding: 11px 28px;
    border-color: rgba(202, 215, 209, .88);
    background: rgba(248, 250, 249, .88);
    -webkit-backdrop-filter: blur(22px) saturate(1.12);
    backdrop-filter: blur(22px) saturate(1.12);
  }
  .teacher-topbar p { color: #60726b; }
  .teacher-topbar h1 { color: #1d342c; font-size: 21px; letter-spacing: -.025em; }
  .teacher-search { width: min(380px, 42vw); }
  .teacher-search input {
    min-height: 44px;
    border-color: #c6d4ce;
    border-radius: 10px;
    background: rgba(255,255,255,.94);
  }
  .teacher-search input:hover { border-color: #9fb6ac; }
  .teacher-search input:focus { border-color: #4a7b6e; }

  .workspace { padding: 26px 28px 44px; }
  .workspace > .panel {
    padding: 24px;
    border: 1px solid var(--teacher-line);
    border-radius: 14px;
    box-shadow: none;
  }
  .panel-title { margin-bottom: 20px; }
  .panel-title h3 { color: #1f392f; font-size: 20px; letter-spacing: -.02em; }
  .panel-title p { color: var(--teacher-muted); line-height: 1.6; }
  .section-kicker {
    padding: 4px 7px;
    color: #315f52;
    background: #e9f1ed;
  }

  .primary-btn,
  .ghost-btn,
  .danger-btn {
    min-height: 40px;
    border-radius: 9px;
    transition: background-color var(--ui-duration-fast, 180ms) ease, color var(--ui-duration-fast, 180ms) ease, filter var(--ui-duration-fast, 180ms) ease;
  }
  .primary-btn { background: #2f6758; }
  .primary-btn:hover { background: #28594d; filter: none; }
  .ghost-btn { color: #315d51; background: #eaf1ee; }
  .ghost-btn:hover { background: #dfeae5; filter: none; }

  .case-student,
  .warning-item,
  .student-card,
  .account-row,
  .template-list button {
    border-radius: 10px;
    background: #f7f9f8;
    transition: border-color 180ms ease, background-color 180ms ease;
  }
  .case-student:hover,
  .warning-item:hover,
  .student-card:hover,
  .template-list button:hover { border-color: #afc2b9; background: #f2f6f4; }
  .case-student.selected,
  .warning-item.selected,
  .student-card.selected,
  .template-list button.selected { border-color: #5e897c; background: #eaf2ee; }

  .case-stage,
  .detail-card,
  .profile-card,
  .lesson-result,
  .emotion-detail-panel,
  .evidence-brief,
  .decision-brief,
  .agent-conflict,
  .task-board,
  .approval-card { border-radius: 12px; }
  .agent-pipeline article { padding: 13px 14px; background: #f2f6f4; }
  .desktop-case-agent-live {
    border-color: #d4e0da;
    background: #f7faf8;
  }
  .desktop-case-agent-live li { background: #eaf1ee; }
  .chart-section { border-radius: 12px; }
}
</style>
