<template>
  <div class="teacher-page">
    <header class="teacher-hero">
      <div>
        <p class="eyebrow">教师端工作台</p>
        <h2>教师端</h2>
        <p class="hero-copy">从班级情绪态势出发，快速发现预警、完成处理，并生成可落地的班会方案。</p>
      </div>
      <div class="hero-actions">
        <button class="ghost-btn" @click="restartGuide">重新引导</button>
        <button class="ghost-btn" @click="handleBack">返回学生端</button>
        <button class="danger-btn" @click="handleLogout">退出</button>
      </div>
    </header>

    <div v-if="error" class="error-screen">
      <p>{{ error }}</p>
      <button class="primary-btn" @click="loadAll">重新加载</button>
    </div>

    <template v-else>
      <section class="guide-card" v-if="showGuide" data-guide="guide-card">
        <div class="guide-progress">
          <span>新手引导 {{ guideIndex + 1 }} / {{ guideSteps.length }}</span>
          <div class="progress-track"><i :style="{ width: guideProgress + '%' }"></i></div>
        </div>
        <h3>{{ currentGuide.title }}</h3>
        <p>{{ currentGuide.description }}</p>
        <div class="guide-actions">
          <button class="primary-btn" @click="runGuideAction">{{ currentGuide.action }}</button>
          <button class="ghost-btn" @click="skipGuide">跳过</button>
        </div>
      </section>

      <section class="overview-grid" data-guide="overview">
        <article class="metric-card strong">
          <span>班级学生</span>
          <strong>{{ overview.total_students ?? '--' }}</strong>
          <small>今日活跃 {{ overview.today_active ?? 0 }} 人</small>
        </article>
        <article class="metric-card warning">
          <span>待处理预警</span>
          <strong>{{ overview.pending_warnings ?? warningList.length }}</strong>
          <small>优先处理高风险学生</small>
        </article>
        <article class="metric-card">
          <span>本周平均情绪</span>
          <strong>{{ formatScore(overview.week_avg_score) }}</strong>
          <small :class="trendClass">{{ formatChange(overview.week_change) }}</small>
        </article>
        <article class="risk-card">
          <span>风险分布</span>
          <div class="risk-bars">
            <b class="risk-low">低 {{ riskCounts.low || 0 }}</b>
            <b class="risk-mid">中 {{ riskCounts.middle || 0 }}</b>
            <b class="risk-high">高 {{ riskCounts.high || 0 }}</b>
          </div>
        </article>
      </section>

      <nav class="teacher-tabs" data-guide="tabs">
        <button :class="{ active: tab === 'warnings' }" @click="openTab('warnings')">情绪预警</button>
        <button :class="{ active: tab === 'students' }" @click="openTab('students')">学生画像</button>
        <button :class="{ active: tab === 'lesson' }" @click="openTab('lesson')">AI 班会</button>
        <button :class="{ active: tab === 'accounts' }" @click="openTab('accounts')">账号管理</button>
      </nav>

      <main class="workspace">
        <section v-if="tab === 'warnings'" class="panel warning-panel" data-guide="warning-list">
          <div class="panel-title">
            <div>
              <h3>情绪预警</h3>
              <p>按风险等级和更新时间排序，建议先处理高风险与未处理记录。</p>
            </div>
            <button class="ghost-btn" @click="loadWarnings">刷新预警</button>
          </div>

          <div class="split-layout">
            <div class="warning-list">
              <button
                v-for="item in warningList"
                :key="item.id"
                :class="['warning-item', item.risk_level, { selected: selectedWarning?.id === item.id }]"
                @click="selectWarning(item)"
              >
                <span class="risk-dot"></span>
                <span class="warning-main">
                  <strong>{{ item.student_name || item.nickname || ('学生 ' + item.student_id) }}</strong>
                  <small>{{ item.reason || item.summary || '需要教师关注' }}</small>
                </span>
                <em>{{ riskText(item.risk_level) }}</em>
              </button>
              <p v-if="!warningList.length" class="empty-state">暂无预警。系统检测到风险后会显示在这里。</p>
            </div>

            <aside class="detail-card" data-guide="warning-detail">
              <template v-if="selectedWarning">
                <div class="detail-head">
                  <div>
                    <span class="status-pill">{{ riskText(selectedWarning.risk_level) }}</span>
                    <h4>{{ selectedWarning.student_name || selectedWarning.nickname || '学生预警' }}</h4>
                  </div>
                  <small>{{ selectedWarning.created_at?.slice?.(0, 16) || '刚刚更新' }}</small>
                </div>
                <p class="detail-copy">{{ selectedWarning.detail || selectedWarning.reason || selectedWarning.summary || '该学生近期情绪波动明显，建议尽快查看画像并完成一次跟进。' }}</p>
                <div class="suggestion-box">
                  <strong>处理建议</strong>
                  <p>{{ selectedWarning.suggestion || '先查看近 7 天情绪趋势，再进行一次线下关怀或班主任沟通记录。' }}</p>
                </div>
                <label class="handle-box">
                  <span>处理记录</span>
                  <textarea v-model="handleNote" placeholder="例如：已约学生课后沟通，持续观察三天。"></textarea>
                </label>
                <div class="detail-actions">
                  <button class="primary-btn" @click="handleWarning">标记已处理</button>
                  <button class="ghost-btn" @click="openStudentFromWarning">查看学生画像</button>
                </div>
              </template>
              <div v-else class="empty-state tall">点击左侧任意预警，查看详情与处理建议。</div>
            </aside>
          </div>
        </section>

        <section v-if="tab === 'students'" class="panel" data-guide="student-profile">
          <div class="panel-title">
            <div>
              <h3>学生画像</h3>
              <p>集中查看学生情绪、活跃度与近期关键词，用于判断是否需要干预。</p>
            </div>
            <button class="ghost-btn" @click="loadStudents">刷新学生</button>
          </div>
          <div class="student-grid">
            <button
              v-for="student in students"
              :key="student.id"
              :class="['student-card', { selected: selectedStudent?.id === student.id }]"
              @click="selectStudent(student)"
            >
              <span class="avatar">{{ firstChar(student.nickname || student.username || student.name) }}</span>
              <strong>{{ student.nickname || student.username || student.name }}</strong>
              <small>情绪 {{ formatScore(student.avg_mood_score || student.avg_score) }} · 记录 {{ student.mood_count || 0 }} 次</small>
              <em :class="['risk-label', student.risk_level || 'low']">{{ riskText(student.risk_level) }}</em>
            </button>
          </div>
          <article class="profile-card" v-if="selectedStudent">
            <div>
              <h4>{{ selectedStudent.nickname || selectedStudent.username || selectedStudent.name }} 的关注摘要</h4>
              <p>{{ studentProfile.summary || '该学生暂无完整画像，建议结合近期倾诉、心情记录与线下观察综合判断。' }}</p>
            </div>
            <div class="profile-metrics">
              <span>平均情绪 <b>{{ formatScore(studentProfile.avg_score || selectedStudent.avg_mood_score) }}</b></span>
              <span>高频词 <b>{{ profileKeywords }}</b></span>
              <span>最近活跃 <b>{{ studentProfile.last_active || selectedStudent.last_active || '--' }}</b></span>
            </div>
          </article>
        </section>

        <section v-if="tab === 'lesson'" class="panel lesson-panel" data-guide="lesson-plan">
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

        <section v-if="tab === 'accounts'" class="panel">
          <div class="panel-title">
            <div>
              <h3>账号管理</h3>
              <p>保留内部兼容字段 is_admin，但界面统一表达为教师权限。</p>
            </div>
            <button class="ghost-btn" @click="loadAccounts">刷新账号</button>
          </div>
          <div class="account-list">
            <div v-for="u in accounts" :key="u.id" class="account-row">
              <span class="avatar">{{ firstChar(u.nickname || u.username) }}</span>
              <div>
                <strong>{{ u.nickname || u.username }}</strong>
                <small>ID: {{ u.id }} · {{ u.is_admin ? '教师' : '普通用户' }}</small>
              </div>
              <button class="ghost-btn" @click="toggleTeacher(u)">{{ u.is_admin ? '取消教师' : '设为教师' }}</button>
            </div>
            <p v-if="!accounts.length" class="empty-state">暂无账号数据。</p>
          </div>
        </section>
      </main>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
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
} from '../api/teacher'

const GUIDE_KEY = 'shengyu_teacher_guide_v4_4_0'

const router = useRouter()
const userStore = useUserStore()

const tab = ref('warnings')
const error = ref('')
const overview = ref({})
const students = ref([])
const warningList = ref([])
const selectedWarning = ref(null)
const selectedStudent = ref(null)
const studentProfile = ref({})
const templates = ref([])
const accounts = ref([])
const handleNote = ref('')
const lessonLoading = ref(false)
const lessonPlan = ref('')
const lessonForm = ref({ template: '', topic: '考前减压与情绪调节', context: '' })
const showGuide = ref(localStorage.getItem(GUIDE_KEY) !== 'done')
const guideIndex = ref(0)

const guideSteps = [
  { tab: 'warnings', title: '第一步：先看待处理预警', description: '教师端的核心不是翻数据，而是先定位今天最需要被关注的学生。', action: '查看情绪预警' },
  { tab: 'warnings', title: '第二步：打开一个预警详情', description: '点击预警后可以看到风险原因、建议动作和处理记录入口。', action: '打开首条预警' },
  { tab: 'students', title: '第三步：查看学生画像', description: '画像用于判断风险是否持续，避免只凭单条记录做判断。', action: '查看学生画像' },
  { tab: 'lesson', title: '第四步：生成班会方案', description: '当风险呈现班级共性时，用 AI 班会把问题转成可执行的课堂活动。', action: '进入班会生成' },
]

const currentGuide = computed(() => guideSteps[guideIndex.value])
const guideProgress = computed(() => Math.round(((guideIndex.value + 1) / guideSteps.length) * 100))
const riskCounts = computed(() => overview.value.risk_counts || {})
const trendClass = computed(() => Number(overview.value.week_change || 0) >= 0 ? 'up' : 'down')
const profileKeywords = computed(() => {
  const words = studentProfile.value.keywords || selectedStudent.value?.keywords || []
  if (!words.length) return '--'
  return words.slice(0, 4).map((w) => w.word || w).join('、')
})

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
  if (!selectedStudent.value && students.value.length) selectStudent(students.value[0])
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
    await Promise.all([loadOverview(), loadWarnings(), loadStudents(), loadTemplates(), loadAccounts()])
  } catch (e) {
    error.value = '教师端数据加载失败，请确认后端 /api/teacher 服务正常。'
  }
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
  try {
    const r = await getStudentProfile(student.id || student.student_id, userStore.userId)
    studentProfile.value = normalizeObject(r.data, {})
  } catch {
    studentProfile.value = {}
  }
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

function openTab(name) {
  tab.value = name
}

function runGuideAction() {
  const step = currentGuide.value
  tab.value = step.tab
  if (guideIndex.value === 1 && warningList.value.length) selectWarning(warningList.value[0])
  if (guideIndex.value === 2 && students.value.length) selectStudent(students.value[0])
  if (guideIndex.value < guideSteps.length - 1) {
    guideIndex.value += 1
  } else {
    completeGuide()
  }
}

function completeGuide() {
  localStorage.setItem(GUIDE_KEY, 'done')
  showGuide.value = false
}

function skipGuide() {
  completeGuide()
}

function restartGuide() {
  localStorage.removeItem(GUIDE_KEY)
  guideIndex.value = 0
  showGuide.value = true
  tab.value = 'warnings'
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

function formatScore(score) {
  if (score === undefined || score === null || score === '') return '--'
  return Number(score).toFixed(1)
}

function formatChange(value) {
  const n = Number(value || 0)
  if (!n) return '与上周持平'
  return (n > 0 ? '较上周 +' : '较上周 ') + n.toFixed(1)
}

function riskText(level = 'low') {
  return { high: '高风险', middle: '中风险', medium: '中风险', low: '低风险', handled: '已处理' }[level] || '待关注'
}

onMounted(() => {
  if (!userStore.isAdmin) {
    error.value = '请用教师账号登录'
    return
  }
  loadAll()
})
</script>

<style scoped>
.teacher-page { min-height: 100vh; padding: 24px; background: #f4f7f5; color: #26332f; }
.teacher-hero { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; padding: 24px; border-radius: 20px; background: linear-gradient(135deg, #ffffff, #eaf3ef); border: 1px solid #dce8e2; }
.eyebrow { color: #4f7d70; font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.teacher-hero h2 { font-size: 30px; margin-bottom: 8px; }
.hero-copy { color: #60716b; max-width: 680px; line-height: 1.7; }
.hero-actions, .guide-actions, .detail-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.primary-btn, .ghost-btn, .danger-btn { min-height: 36px; padding: 8px 15px; border-radius: 10px; font-size: 14px; transition: transform .18s ease, background .18s ease; }
.primary-btn { background: #4f7d70; color: white; }
.ghost-btn { background: #eef4f1; color: #36554d; }
.danger-btn { background: #f5e5e1; color: #b85c50; }
.primary-btn:hover, .ghost-btn:hover, .danger-btn:hover { transform: translateY(-1px); }
.primary-btn:disabled { opacity: .6; cursor: not-allowed; transform: none; }
.error-screen { margin-top: 20px; padding: 48px; border-radius: 18px; background: white; text-align: center; color: #b85c50; }
.guide-card { margin-top: 18px; padding: 18px 20px; border-radius: 18px; background: #18231f; color: white; display: grid; gap: 10px; }
.guide-card p { color: rgba(255,255,255,.78); line-height: 1.7; }
.guide-progress { display: flex; align-items: center; gap: 12px; font-size: 13px; color: rgba(255,255,255,.72); }
.progress-track { flex: 1; height: 6px; border-radius: 999px; background: rgba(255,255,255,.16); overflow: hidden; }
.progress-track i { display: block; height: 100%; background: #8bc8b5; }
.overview-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 18px 0; }
.metric-card, .risk-card { padding: 18px; border-radius: 16px; background: white; border: 1px solid #e1e9e5; }
.metric-card span, .risk-card span { display: block; color: #71817b; font-size: 13px; }
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
.template-list button { display: grid; }
.lesson-compose { display: grid; gap: 14px; align-content: start; }
.lesson-result { margin-top: 16px; }
.lesson-result pre { margin-top: 10px; white-space: pre-wrap; line-height: 1.8; color: #3c4a45; font-family: inherit; }
.account-row { justify-content: space-between; }
.account-row div { flex: 1; display: grid; gap: 3px; }
.empty-state { padding: 18px; text-align: center; color: #81908b; background: #f8fbf9; border-radius: 14px; }
.empty-state.tall { min-height: 260px; display: grid; place-items: center; }
@media (max-width: 900px) { .teacher-page { padding: 14px; } .teacher-hero, .panel-title { flex-direction: column; } .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .split-layout, .lesson-layout { grid-template-columns: 1fr; } .teacher-tabs { overflow-x: auto; } }
@media (max-width: 560px) { .overview-grid { grid-template-columns: 1fr; } .teacher-tabs button { white-space: nowrap; } .account-row { align-items: flex-start; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
