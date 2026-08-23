<template>
  <section class="student-agent-shell" :class="{ 'is-open': open }" aria-label="咕哝智能体工作状态">
    <button
      ref="toggleButton"
      class="student-agent-toggle"
      type="button"
      :aria-label="open ? '收起咕哝智能体进度' : '展开咕哝智能体进度'"
      :aria-expanded="open"
      aria-controls="student-agent-rail"
      @click="$emit('toggle')"
    >
      <span class="agent-toggle-mark" :class="`is-${state.status}`" aria-hidden="true"></span>
      <span class="agent-toggle-copy">
        <strong>Agent</strong>
        <small>{{ compactStatus }}</small>
      </span>
    </button>

    <Transition name="agent-rail">
      <aside
        v-if="open"
        id="student-agent-rail"
        class="student-agent-rail"
        aria-labelledby="student-agent-title"
        @keydown.esc="$emit('close')"
      >
        <header class="agent-rail-header">
          <div>
            <p>倾诉协作进度</p>
            <h2 id="student-agent-title">咕哝正在做什么</h2>
          </div>
          <button ref="closeButton" class="agent-rail-close" type="button" aria-label="收起智能体进度" @click="$emit('close')">×</button>
        </header>

        <p class="agent-rail-event" role="status" aria-live="polite">
          <span :class="`is-${state.status}`" aria-hidden="true"></span>
          {{ state.lastEvent }}
        </p>

        <ol class="agent-step-list">
          <li v-for="step in steps" :key="step.id" :class="`is-${step.status}`">
            <span class="agent-step-icon" aria-hidden="true">{{ statusIcon(step.status) }}</span>
            <div>
              <strong>{{ step.label }}</strong>
              <small>{{ step.summary }}</small>
            </div>
            <em>{{ statusLabel(step.status) }}</em>
          </li>
        </ol>

        <footer class="agent-rail-footer">
          <span>已处理 {{ state.messageCount }} 条学生表达</span>
          <span>{{ riskLabel }}</span>
        </footer>
        <p class="agent-boundary">只展示可核验的工作步骤与结果摘要，不展示模型私有思维过程；情绪整理不等于心理诊断。</p>
      </aside>
    </Transition>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  state: {
    type: Object,
    required: true,
  },
  steps: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['toggle', 'close'])
const toggleButton = ref(null)
const closeButton = ref(null)

const compactStatus = computed(() => {
  const labels = {
    standby: '等待倾听',
    running: '正在协作',
    ready: '本轮完成',
    urgent: '安全流程优先',
    error: '等待重试',
  }
  return labels[props.state.status] || '等待倾听'
})

const riskLabel = computed(() => {
  const labels = {
    unassessed: '尚未分流',
    routine: '日常支持',
    watch: '建议持续留意',
    professional: '建议专业支持',
    urgent: '立即安全协助',
  }
  return labels[props.state.riskLevel] || labels.unassessed
})

function statusIcon(status) {
  return ({ completed: '✓', running: '•', attention: '!', blocked: '—', waiting: '·', error: '×' })[status] || '·'
}

function statusLabel(status) {
  return ({ completed: '完成', running: '进行中', attention: '需确认', blocked: '已停止', waiting: '等待', error: '需重试' })[status] || '等待'
}

watch(() => props.open, async (value, previous) => {
  await nextTick()
  if (value) closeButton.value?.focus({ preventScroll: true })
  else if (previous) toggleButton.value?.focus({ preventScroll: true })
})
</script>

<style scoped>
.student-agent-shell {
  --agent-ink: #f7f4ed;
  --agent-muted: rgba(247, 244, 237, .72);
  --agent-accent: #b9d9c9;
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 230;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: var(--agent-ink);
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', system-ui, sans-serif;
  pointer-events: none;
}
.student-agent-toggle,
.student-agent-rail { pointer-events: auto; }
.student-agent-toggle {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 104px;
  min-height: 46px;
  padding: 7px 10px;
  border: 0;
  border-radius: 12px;
  color: var(--agent-ink);
  background: rgba(17, 23, 29, .88);
  box-shadow: 0 5px 8px rgba(5, 8, 12, .24);
  backdrop-filter: blur(16px) saturate(1.18);
  cursor: pointer;
  text-align: left;
}
.agent-toggle-mark {
  width: 10px;
  height: 10px;
  flex: 0 0 auto;
  border-radius: 3px;
  background: #93a09a;
}
.agent-toggle-mark.is-running { background: #d9bd79; animation: agent-pulse 1.2s ease-in-out infinite; }
.agent-toggle-mark.is-ready { background: #91c8aa; }
.agent-toggle-mark.is-urgent, .agent-toggle-mark.is-error { background: #e49b84; }
.student-agent-toggle strong,
.student-agent-toggle small { display: block; }
.student-agent-toggle strong { font-size: 12px; line-height: 1.25; }
.student-agent-toggle small { margin-top: 2px; color: var(--agent-muted); font-size: 10px; }
.agent-toggle-copy { min-width: 0; }
.student-agent-rail {
  width: min(330px, calc(100vw - 40px));
  max-height: calc(100vh - 190px);
  overflow-y: auto;
  padding: 17px;
  border-radius: 14px;
  background: rgba(17, 23, 29, .94);
  box-shadow: 0 6px 8px rgba(5, 8, 12, .28);
  backdrop-filter: blur(22px) saturate(1.2);
}
.agent-rail-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.agent-rail-header p { margin: 0 0 3px; color: var(--agent-accent); font-size: 11px; font-weight: 700; }
.agent-rail-header h2 { margin: 0; font-size: 17px; line-height: 1.35; }
.agent-rail-close {
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 10px;
  color: var(--agent-ink);
  background: rgba(255, 255, 255, .08);
  font-size: 20px;
  cursor: pointer;
}
.agent-rail-event {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 15px 0 12px;
  padding: 10px 11px;
  border-radius: 10px;
  color: rgba(247, 244, 237, .9);
  background: rgba(255, 255, 255, .065);
  font-size: 12px;
  line-height: 1.5;
}
.agent-rail-event span { width: 8px; height: 8px; flex: 0 0 auto; border-radius: 2px; background: #93a09a; }
.agent-rail-event span.is-running { background: #d9bd79; }
.agent-rail-event span.is-ready { background: #91c8aa; }
.agent-rail-event span.is-urgent, .agent-rail-event span.is-error { background: #e49b84; }
.agent-step-list { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
.agent-step-list li {
  display: grid;
  grid-template-columns: 25px minmax(0, 1fr) auto;
  gap: 9px;
  align-items: start;
  padding: 9px 4px;
  border-bottom: 1px solid rgba(255, 255, 255, .07);
}
.agent-step-list li:last-child { border-bottom: 0; }
.agent-step-icon {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  color: rgba(247, 244, 237, .72);
  background: rgba(255, 255, 255, .075);
  font-size: 12px;
  font-weight: 800;
}
.agent-step-list li.is-completed .agent-step-icon { color: #17231e; background: #a9d4be; }
.agent-step-list li.is-running .agent-step-icon { color: #2f2412; background: #e6ca87; animation: agent-pulse 1.2s ease-in-out infinite; }
.agent-step-list li.is-attention .agent-step-icon,
.agent-step-list li.is-error .agent-step-icon { color: #32170f; background: #efad96; }
.agent-step-list li.is-blocked { opacity: .6; }
.agent-step-list strong,
.agent-step-list small { display: block; }
.agent-step-list strong { font-size: 12px; line-height: 1.4; }
.agent-step-list small { margin-top: 2px; color: var(--agent-muted); font-size: 12px; line-height: 1.45; }
.agent-step-list em { color: var(--agent-muted); font-size: 10px; font-style: normal; white-space: nowrap; }
.agent-rail-footer { display: flex; justify-content: space-between; gap: 10px; margin-top: 13px; color: var(--agent-accent); font-size: 10px; }
.agent-boundary { margin: 10px 0 0; color: rgba(247, 244, 237, .7); font-size: 12px; line-height: 1.55; }
.student-agent-toggle:focus-visible,
.student-agent-rail button:focus-visible { outline: 3px solid #f0d58e; outline-offset: 3px; }
.agent-rail-enter-active,
.agent-rail-leave-active { transition: opacity .2s ease, transform .2s cubic-bezier(.22, 1, .36, 1); }
.agent-rail-enter-from,
.agent-rail-leave-to { opacity: 0; transform: translateX(12px); }
@keyframes agent-pulse { 50% { opacity: .58; } }

@media (min-width: 900px) {
  .student-agent-shell.is-open .student-agent-toggle { width: 46px; justify-content: center; }
  .student-agent-shell.is-open .agent-toggle-copy { display: none; }
}

@media (max-width: 899px) {
  .student-agent-shell {
    top: 12px;
    right: 12px;
    bottom: auto;
    align-items: flex-end;
    flex-direction: column;
  }
  .student-agent-toggle { width: 92px; min-height: 44px; }
  .student-agent-rail {
    width: min(360px, calc(100vw - 24px));
    max-height: min(66vh, 560px);
  }
  .agent-rail-enter-from,
  .agent-rail-leave-to { opacity: 0; transform: translateY(12px); }
}

@media (prefers-reduced-motion: reduce) {
  .agent-rail-enter-active,
  .agent-rail-leave-active { transition: none; }
  .agent-toggle-mark.is-running,
  .agent-step-list li.is-running .agent-step-icon { animation: none; }
}
</style>
