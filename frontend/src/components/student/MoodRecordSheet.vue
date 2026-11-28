<template>
  <div class="mrs-overlay" @click.self="$emit('close')">
    <section
      ref="cardEl"
      class="mrs-card"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mrs-title"
      tabindex="-1"
    >
      <header class="mrs-head">
        <h2 id="mrs-title">记录此刻的心情</h2>
        <p>选一个最接近的就好，没有对错。</p>
      </header>

      <div class="mrs-moods" role="group" aria-label="选择心情">
        <button
          v-for="mood in MOODS"
          :key="mood.label"
          type="button"
          :class="{ active: selected === mood.label }"
          :aria-pressed="selected === mood.label"
          @click="selected = mood.label"
        >
          <span aria-hidden="true">{{ mood.emoji }}</span>{{ mood.label }}
        </button>
      </div>

      <label class="mrs-note">
        <span>想补一句话吗（可不写）</span>
        <textarea v-model="note" maxlength="80" rows="2" placeholder="例如：今天最明显的一刻是……"></textarea>
      </label>

      <p v-if="error" class="mrs-error" role="status">{{ error }}</p>

      <div class="mrs-actions">
        <button type="button" class="mrs-cancel" @click="$emit('close')">先不记</button>
        <button type="button" class="mrs-save" :disabled="!selected || saving" @click="save">
          {{ saving ? '正在记录…' : '记下来' }}
        </button>
      </div>
      <p class="mrs-boundary">记录只用于你自己的情绪回顾，不是心理测评。</p>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useUserStore } from '../../stores/user'
import { recordMood } from '../../api/mood'
import { activateDialog } from '../../utils/dialogFocus'

const emit = defineEmits(['close', 'saved'])
const userStore = useUserStore()

const cardEl = ref(null)
let releaseDialog = null

onMounted(() => {
  releaseDialog = activateDialog(cardEl.value, { onClose: () => emit('close') })
})

onBeforeUnmount(() => {
  releaseDialog?.()
  releaseDialog = null
})

const MOODS = [
  { label: '愤怒', emoji: '😠', score: 3 },
  { label: '厌恶', emoji: '🤢', score: 2 },
  { label: '恐惧', emoji: '😨', score: 2 },
  { label: '开心', emoji: '😊', score: 9 },
  { label: '中性', emoji: '😐', score: 6 },
  { label: '悲伤', emoji: '😢', score: 3 },
  { label: '惊讶', emoji: '😲', score: 6 },
]

const selected = ref('')
const note = ref('')
const saving = ref(false)
const error = ref('')

async function save() {
  if (!selected.value || saving.value) return
  const mood = MOODS.find(item => item.label === selected.value)
  saving.value = true
  error.value = ''
  try {
    await userStore.ensureStudentSession(true)
    await recordMood({
      user_id: Number(userStore.userId),
      label: mood.label,
      score: mood.score,
      content: note.value.trim(),
    })
    emit('saved', { label: mood.label, score: mood.score })
    emit('close')
  } catch {
    error.value = '这次没有记上，请稍后再试。'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.mrs-overlay {
  position: fixed;
  inset: 0;
  z-index: 220;
  background: rgba(28, 38, 34, .38);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  animation: m-fadein var(--m-dur) var(--m-ease-soft) backwards;
}
@media (min-width: 640px) {
  .mrs-overlay { align-items: center; }
}

.mrs-card {
  width: 100%;
  max-width: 430px;
  background: var(--m-surface);
  border-radius: var(--m-radius-lg) var(--m-radius-lg) 0 0;
  padding: 22px 20px calc(18px + env(safe-area-inset-bottom));
  box-shadow: var(--m-shadow);
  animation: m-panel-rise 340ms var(--m-ease) backwards;
}
@media (min-width: 640px) {
  .mrs-card { border-radius: var(--m-radius-lg); padding-bottom: 20px; }
}

.mrs-head h2 {
  margin: 0;
  font-size: 17px;
  color: var(--m-ink);
}
.mrs-head p {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: var(--m-ink-2);
}

.mrs-moods {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 16px 0;
}
.mrs-moods button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 2px;
  border-radius: var(--m-radius-md);
  background: var(--m-bg);
  border: 1.5px solid transparent;
  font-size: 12px;
  color: var(--m-ink-2);
  transition: border-color var(--m-dur-fast) var(--m-ease),
              background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
  animation: m-pop 360ms var(--m-ease) backwards;
}
.mrs-moods button:nth-child(1) { animation-delay: 40ms; }
.mrs-moods button:nth-child(2) { animation-delay: 80ms; }
.mrs-moods button:nth-child(3) { animation-delay: 120ms; }
.mrs-moods button:nth-child(4) { animation-delay: 160ms; }
.mrs-moods button:nth-child(5) { animation-delay: 200ms; }
.mrs-moods button:nth-child(6) { animation-delay: 240ms; }
.mrs-moods button:nth-child(7) { animation-delay: 280ms; }
.mrs-moods button:hover { border-color: #CFE3DA; }
.mrs-moods button:active { transform: scale(.94); }
.mrs-moods button span { font-size: 22px; }
.mrs-moods button.active {
  border-color: var(--m-accent);
  background: var(--m-accent-soft);
  color: var(--m-accent-strong);
  font-weight: 600;
}

.mrs-note { display: block; }
.mrs-note span {
  display: block;
  font-size: 12.5px;
  color: var(--m-ink-2);
  margin-bottom: 6px;
}
.mrs-note textarea {
  width: 100%;
  border: 1.5px solid var(--m-line);
  border-radius: var(--m-radius-md);
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  color: var(--m-ink);
  background: var(--m-surface);
  resize: none;
  outline: none;
  transition: border-color var(--m-dur-fast) var(--m-ease), box-shadow var(--m-dur-fast) var(--m-ease);
}
.mrs-note textarea:focus { border-color: var(--m-accent); box-shadow: 0 0 0 3px var(--m-ring); }

.mrs-error {
  margin: 10px 0 0;
  font-size: 12.5px;
  color: var(--m-danger);
}

.mrs-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}
.mrs-actions button {
  flex: 1;
  padding: 11px 0;
  border-radius: var(--m-radius-md);
  font-size: 14.5px;
  transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease);
}
.mrs-actions button:active { transform: scale(.97); }
.mrs-cancel {
  background: var(--m-bg);
  color: var(--m-ink-2);
}
.mrs-cancel:hover { background: var(--m-line); }
.mrs-save {
  background: var(--m-accent);
  color: #fff;
  font-weight: 600;
}
.mrs-save:not(:disabled):hover { background: var(--m-accent-strong); }
.mrs-save:disabled { opacity: .45; cursor: not-allowed; }

.mrs-boundary {
  margin: 12px 0 0;
  text-align: center;
  font-size: 11px;
  color: var(--m-ink-3);
}

/* 像素皮肤 3.0 · 心情记录浮层 */
.mrs-card {
  border: 2px solid var(--px-line, var(--m-line));
  border-radius: 6px;
  box-shadow: 4px 4px 0 var(--px-shadow, var(--m-shadow));
}
.mrs-head h2 { font-family: var(--px-font); font-size: 17px; }
.mrs-moods button {
  border: 2px solid var(--px-line, var(--m-line));
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow, var(--m-shadow));
  transition: border-color 160ms steps(2, end), background 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.mrs-moods button:hover {
  border-color: var(--px-gold, var(--m-accent));
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 var(--px-shadow, var(--m-shadow));
}
.mrs-moods button:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--px-shadow, var(--m-shadow));
}
.mrs-moods button.active {
  border-color: var(--px-gold, var(--m-accent));
  box-shadow: 2px 2px 0 var(--px-shadow, var(--m-shadow));
}
.mrs-note textarea {
  border: 2px solid var(--px-line, var(--m-line));
  border-radius: 4px;
}
.mrs-note textarea:focus {
  border-color: var(--px-gold, var(--m-accent));
  box-shadow: none;
  outline: 2px dashed var(--px-gold, var(--m-accent));
  outline-offset: 3px;
}
.mrs-actions button {
  border: 2px solid var(--px-line, var(--m-line));
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow, var(--m-shadow));
  font-family: var(--px-font);
  transition: border-color 160ms steps(2, end), background 160ms steps(2, end), transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.mrs-actions button:hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow, var(--m-shadow)); }
.mrs-actions button:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow, var(--m-shadow)); }
.mrs-save {
  border-color: var(--px-gold, var(--m-accent));
  background: var(--px-gold, var(--m-accent));
  color: #221a12;
  font-family: var(--px-font);
}
.mrs-save:not(:disabled):hover { border-color: var(--px-gold, var(--m-accent-strong)); background: var(--px-gold, var(--m-accent-strong)); }
.mrs-cancel { background: transparent; }
.mrs-actions button:focus-visible { outline: 3px dashed var(--px-gold, var(--m-accent)); outline-offset: 3px; }

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
</style>
