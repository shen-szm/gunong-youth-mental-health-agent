<script setup>
import { computed, ref, watch } from 'vue'
import evidence from '../data/teacher-verification.json'
import TeacherAgentExecution from './TeacherAgentExecution.vue'
import UiIcon from './UiIcon.vue'

const category = ref('全部类型')
const outcome = ref('全部结果')
const selectedId = ref(evidence.cases[0]?.id)
const categories = ['全部类型', ...new Set(evidence.cases.map(item => item.category))]
const visibleCases = computed(() => evidence.cases.filter(item => (category.value === '全部类型' || item.category === category.value) && (outcome.value === '全部结果' || item.passed === (outcome.value === '全部通过'))))
const active = computed(() => visibleCases.value.find(item => item.id === selectedId.value) || visibleCases.value[0])
watch([category, outcome], () => { selectedId.value = visibleCases.value[0]?.id })
const stats = computed(() => ({ total: evidence.cases.length, passed: evidence.cases.filter(item => item.passed).length, checks: evidence.cases.reduce((n, item) => n + Object.keys(item.checks).length, 0), passedChecks: evidence.cases.reduce((n, item) => n + Object.values(item.checks).filter(Boolean).length, 0) }))
const passRate = computed(() => (stats.value.checks ? Math.round((stats.value.passedChecks / stats.value.checks) * 100) : 0))
</script>

<template>
  <section class="verification" aria-labelledby="verification-title">
    <header><div><h2 id="verification-title">能力验证档案</h2><p>从输入案例到报告交付，逐项核对实际 API 执行结果。</p></div><UiIcon name="benchmark" :size="26" /></header>
    <p class="verification-origin"><strong>{{ evidence.origin }}</strong>。{{ evidence.boundary }}这些记录不会计入今日工作台或学生统计。</p>
    <div class="verification-summary" aria-label="验证结果摘要"><span>案例 <strong>{{ stats.passed }} / {{ stats.total }} 通过</strong></span><span>类型 <strong>{{ categories.length - 1 }} 类</strong></span><span>断言 <strong>{{ stats.passedChecks }} / {{ stats.checks }} 通过</strong></span><span>执行时间 <strong>{{ new Date(evidence.generated_at).toLocaleString('zh-CN', { hour12: false }) }}</strong></span></div>
    <div class="verification-meter-row">
      <span class="verification-meter-label">断言通过率</span>
      <div class="verification-meter" role="img" :aria-label="`断言通过率 ${passRate}%`"><span :style="{ width: passRate + '%' }" /></div>
      <strong class="verification-meter-value">{{ passRate }}%</strong>
    </div>
    <div class="verification-filters"><label>案例类型<select v-model="category"><option v-for="item in categories" :key="item">{{ item }}</option></select></label><label>验证结果<select v-model="outcome"><option>全部结果</option><option>全部通过</option><option>存在失败</option></select></label><span>当前 {{ visibleCases.length }} 个案例</span></div>
    <div v-if="active" class="verification-layout">
      <nav aria-label="验证案例" class="verification-list"><button v-for="item in visibleCases" :key="item.id" type="button" :aria-pressed="active.id === item.id" @click="selectedId = item.id"><span>{{ item.id }}</span><strong>{{ item.title }}</strong><small>{{ item.passed ? '通过' : '存在失败' }} · {{ item.report.overall_decision?.risk_label }}</small></button></nav>
      <article class="verification-case">
        <h3>{{ active.title }}</h3><p class="verification-input">输入：{{ active.input }}</p>
        <TeacherAgentExecution :key="active.id" :report="active.report" />
        <h4>本例验收记录</h4><ul class="verification-checks"><li v-for="(passed, name) in active.checks" :key="name"><UiIcon :name="passed ? 'check' : 'close'" /><span>{{ name }}</span><strong :class="{ failed: !passed }">{{ passed ? '通过' : '失败' }}</strong></li></ul>
        <details><summary>查看报告结论与复现信息</summary><p>{{ active.report.executive_summary }}</p><p>报告编号：{{ active.report.report_id }}</p><p>运行方式：{{ active.report.generation?.source }}；报告状态：{{ active.report.status }}</p><p>案例定义 SHA-256：<code>{{ evidence.scenario_sha256 }}</code></p><p>报告引擎 SHA-256：<code>{{ evidence.engine_sha256 }}</code></p><p>复现命令（仓库根目录）：<code>backend/venv/Scripts/python.exe backend/scripts/verify_teacher_cases.py</code></p></details>
      </article>
    </div>
    <p v-else class="verification-empty">当前筛选没有案例。请选择其他类型或查看全部结果。</p>
  </section>
</template>

<style scoped>
.verification { min-width: 0; padding: 22px; border: 1px solid var(--t-line); border-radius: var(--t-r-lg); background: var(--t-surface); color: var(--t-ink); font-size: 13px; }
.verification header { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
.verification header > svg { color: var(--t-line-2); }
.verification h2 { margin: 0; font-size: 19px; font-weight: 600; letter-spacing: -.01em; }
.verification header p { margin: 4px 0 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.6; }
.verification-origin { margin: 14px 0 0; padding: 10px 12px; border-left: 2px solid var(--t-line-2); color: var(--t-muted); background: var(--t-surface-2); font-size: 12px; line-height: 1.7; }
.verification-origin strong { color: var(--t-ink-2); font-weight: 600; }
.verification-summary { display: flex; flex-wrap: wrap; gap: 8px 30px; padding: 12px 0; border-bottom: 1px solid var(--t-line); color: var(--t-muted); font-size: 12px; }
.verification-summary strong { margin-left: 5px; color: var(--t-ink); font-weight: 600; font-variant-numeric: tabular-nums; }
.verification-meter-row { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--t-line); }
.verification-meter-label { flex: 0 0 auto; color: var(--t-muted); font-size: 11.5px; }
.verification-meter { flex: 1; height: 6px; border-radius: 2px; overflow: hidden; background: var(--t-surface-2); }
.verification-meter span { display: block; height: 100%; border-radius: 2px; background: var(--t-accent); transition: width 480ms cubic-bezier(.22, 1, .36, 1); }
.verification-meter-value { flex: 0 0 auto; color: var(--t-ink); font: 600 13px/1 var(--t-mono); font-variant-numeric: tabular-nums; }
.verification-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 20px; padding: 12px 0; font-size: 12px; }
.verification-filters label { display: flex; align-items: center; gap: 7px; color: var(--t-muted); }
.verification-filters select { min-height: 30px; padding: 3px 8px; border: 1px solid var(--t-line-2); border-radius: var(--t-r-sm); color: var(--t-ink); background: var(--t-surface); font: inherit; font-size: 12px; }
.verification-filters > span { margin-left: auto; color: var(--t-faint); }
.verification-layout { display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 26px; }
.verification-list { align-self: start; max-height: 780px; padding-right: 12px; overflow: auto; border-right: 1px solid var(--t-line); }
.verification-list button { display: grid; gap: 1px; width: 100%; margin-bottom: 2px; padding: 9px 10px; border: 0; border-left: 2px solid transparent; border-radius: 0 var(--t-r-sm) var(--t-r-sm) 0; color: var(--t-ink); background: none; text-align: left; cursor: pointer; font: inherit; }
.verification-list button[aria-pressed=true] { border-left-color: var(--t-accent); background: var(--t-accent-soft); }
.verification-list button:hover { background: var(--t-surface-2); }
.verification-list button span { color: var(--t-faint); font: 500 10px var(--t-mono); }
.verification-list button strong { font-size: 12.5px; font-weight: 600; line-height: 1.4; }
.verification-list button small { color: var(--t-muted); font-size: 10.5px; }
.verification-case { min-width: 0; }
.verification-case h3 { margin: 0; font-size: 16px; font-weight: 600; letter-spacing: -.005em; }
.verification-input { margin: 6px 0 0; color: var(--t-muted); font-size: 12.5px; line-height: 1.7; }
.verification-case h4 { margin: 16px 0 6px; font-size: 13px; font-weight: 600; }
.verification-checks { display: grid; grid-template-columns: 1fr 1fr; gap: 0 24px; margin: 0; padding: 0; list-style: none; }
.verification-checks li { display: flex; align-items: center; gap: 7px; padding: 7px 0; border-bottom: 1px solid var(--t-line); color: var(--t-ink-2); font-size: 11.5px; }
.verification-checks li > svg { color: var(--t-green-ink); }
.verification-checks strong { margin-left: auto; color: var(--t-green-ink); font-size: 11px; font-weight: 600; }
.verification-checks .failed { color: var(--t-red); }
.verification-checks li:has(.failed) > svg { color: var(--t-red); }
.verification details { margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--t-line); color: var(--t-muted); font-size: 11.5px; line-height: 1.7; }
.verification summary { min-height: 30px; color: var(--t-ink-2); font-weight: 600; cursor: pointer; }
.verification code { color: var(--t-faint); overflow-wrap: anywhere; }
.verification-empty { margin: 0; padding: 40px 0; color: var(--t-muted); text-align: center; }
.verification :focus-visible { outline: 2px solid var(--t-accent); outline-offset: 2px; }
@media (max-width: 1100px) { .verification-layout { grid-template-columns: 165px minmax(0, 1fr); gap: 18px; } }
@media (max-width: 760px) {
  .verification { padding: 16px; }
  .verification-layout { grid-template-columns: 1fr; }
  .verification-list { display: flex; gap: 6px; max-height: none; padding: 0 0 6px; border-right: 0; border-bottom: 1px solid var(--t-line); overflow-x: auto; }
  .verification-list button { flex: 0 0 190px; }
  .verification-checks { grid-template-columns: 1fr; }
}
</style>
