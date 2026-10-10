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
</script>

<template>
  <section class="verification" aria-labelledby="verification-title">
    <header><div><h2 id="verification-title">能力验证档案</h2><p>从输入案例到报告交付，逐项核对实际 API 执行结果。</p></div><UiIcon name="benchmark" :size="26" /></header>
    <p class="verification-origin"><strong>{{ evidence.origin }}</strong>。{{ evidence.boundary }}这些记录不会计入今日工作台或学生统计。</p>
    <div class="verification-summary" aria-label="验证结果摘要"><span>案例 <strong>{{ stats.passed }} / {{ stats.total }} 通过</strong></span><span>类型 <strong>{{ categories.length - 1 }} 类</strong></span><span>断言 <strong>{{ stats.passedChecks }} / {{ stats.checks }} 通过</strong></span><span>执行时间 <strong>{{ new Date(evidence.generated_at).toLocaleString('zh-CN', { hour12: false }) }}</strong></span></div>
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
.verification{background:#fff;padding:24px;border:1px solid #d6e2dc;border-radius:12px;color:#263f36;min-width:0}.verification header{display:flex;justify-content:space-between;align-items:center;gap:20px}.verification h2{font-size:23px;margin:0}.verification header p{color:#4b6358;line-height:1.6;margin:8px 0 0}.verification-origin{padding:14px;background:#f1f6f3;line-height:1.7;font-size:13px;color:#405c4f}.verification-summary{display:flex;flex-wrap:wrap;gap:18px 28px;padding:14px 0;border-bottom:1px solid #d6e2dc;font-size:13px;color:#4b6358}.verification-summary strong{margin-left:7px;color:#263f36;font-variant-numeric:tabular-nums}.verification-filters{display:flex;align-items:center;gap:20px;padding:20px 0;font-size:13px}.verification-filters label{display:flex;align-items:center;gap:8px}.verification-filters select{min-height:38px;border:1px solid #97aea2;border-radius:6px;background:white;color:#263f36;padding:6px 10px;font:inherit}.verification-filters>span{margin-left:auto;color:#4b6358}.verification-layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:24px}.verification-list{max-height:820px;overflow:auto;align-self:start;border-right:1px solid #d6e2dc;padding-right:14px}.verification-list button{display:grid;gap:6px;width:100%;padding:12px;margin-bottom:6px;text-align:left;border:1px solid transparent;border-radius:6px;background:transparent;color:#263f36;cursor:pointer;font:inherit}.verification-list button[aria-pressed=true]{background:#e6f1eb;border-color:#97aea2}.verification-list button:hover{background:#f1f6f3}.verification-list button span,.verification-list button small{font-size:12px;color:#4b6358}.verification-list button strong{font-size:13px}.verification-case{min-width:0}.verification-case h3{margin:0;font-size:18px}.verification-input{color:#405c4f;line-height:1.7;margin:10px 0}.verification-case h4{margin:16px 0 10px;font-size:15px}.verification-checks{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:1fr 1fr;gap:0 22px}.verification-checks li{display:flex;align-items:center;gap:7px;padding:10px 0;border-bottom:1px solid #e2ebe6;font-size:12px}.verification-checks strong{margin-left:auto;color:#315f50}.verification-checks .failed{color:#95382f}.verification details{margin-top:20px;font-size:12px;line-height:1.7;color:#405c4f}.verification summary{cursor:pointer;font-weight:700;min-height:36px}.verification code{overflow-wrap:anywhere}.verification-empty{padding:40px 0;color:#4b6358}.verification :focus-visible{outline:3px solid #315f50;outline-offset:3px}
@media(max-width:1100px){.verification-layout{grid-template-columns:175px minmax(0,1fr);gap:16px}}
</style>
