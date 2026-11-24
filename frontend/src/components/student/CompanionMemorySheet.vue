<template>
  <div class="cms-overlay" @click.self="$emit('close')">
    <section
      ref="cardEl"
      class="cms-card"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cms-title"
      tabindex="-1"
    >
      <header class="cms-head">
        <div>
          <h2 id="cms-title">小满记得的事</h2>
          <p>这些是你在聊天里主动说起、小满悄悄记下的小事。</p>
        </div>
        <button class="cms-close" type="button" aria-label="关闭" @click="$emit('close')">×</button>
      </header>

      <p v-if="!loading && !enabled" class="cms-off" role="status">
        小满的记忆现在没有启用；已有的记录仍然可以在这里删除。
      </p>

      <p v-if="loading" class="cms-loading" role="status">正在看看小满记住了什么…</p>
      <p v-else-if="error" class="cms-error" role="status">{{ error }}</p>
      <template v-else>
        <p v-if="!items.length" class="cms-empty">
          小满还没记住什么。等你说到喜欢的事、最近在忙什么，它会悄悄记下来。
        </p>
        <ul v-else class="cms-list">
          <li v-for="item in items" :key="item.memory_code" :class="{ 'is-inactive': !item.active }">
            <span class="cms-cat">{{ item.category }}</span>
            <span class="cms-text">{{ item.content }}</span>
            <span v-if="!item.active" class="cms-paused">当前不使用</span>
            <button
              type="button"
              class="cms-forget"
              :disabled="deleting === item.memory_code"
              @click="forget(item)"
            >{{ deleting === item.memory_code ? '正在忘记…' : '忘记' }}</button>
          </li>
        </ul>
      </template>

      <p v-if="status && !error" class="cms-status" role="status">{{ status }}</p>

      <footer class="cms-foot">
        <p>只保存在你的账号里，最多保留 180 天；姓名、学校、联系方式和危机内容不会被记住。</p>
        <button
          v-if="items.length"
          type="button"
          class="cms-forget-all"
          :disabled="clearing"
          @click="forgetAll"
        >{{ clearing ? '正在清空…' : '全部忘记' }}</button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { activateDialog } from '../../utils/dialogFocus'
import {
  clearCompanionMemories,
  deleteCompanionMemory,
  getCompanionMemories,
} from '../../api/chat'

const emit = defineEmits(['close'])

const cardEl = ref(null)
let releaseDialog = null
const loading = ref(true)
const enabled = ref(false)
const items = ref([])
const error = ref('')
const status = ref('')
const deleting = ref('')
const clearing = ref(false)

onMounted(async () => {
  releaseDialog = activateDialog(cardEl.value, { onClose: () => emit('close') })
  await load()
})

onBeforeUnmount(() => {
  releaseDialog?.()
  releaseDialog = null
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await getCompanionMemories()
    enabled.value = Boolean(data?.enabled)
    items.value = Array.isArray(data?.items) ? data.items : []
  } catch {
    error.value = '暂时看不到这些记录，请稍后再试。'
  } finally {
    loading.value = false
  }
}

async function forget(item) {
  if (deleting.value) return
  deleting.value = item.memory_code
  error.value = ''
  status.value = ''
  try {
    await deleteCompanionMemory(item.memory_code)
    items.value = items.value.filter(row => row.memory_code !== item.memory_code)
    status.value = '这件小事已经忘掉了。'
  } catch {
    error.value = '这次没有删掉，请稍后再试。'
  } finally {
    deleting.value = ''
  }
}

async function forgetAll() {
  if (clearing.value || !items.value.length) return
  if (!window.confirm('小满会忘记这里列出的全部小事，聊天记录不会受影响。确定吗？')) return
  clearing.value = true
  error.value = ''
  status.value = ''
  try {
    await clearCompanionMemories()
    items.value = []
    status.value = '小满已经把这些事都忘掉了。'
  } catch {
    error.value = '这次没有清空，请稍后再试。'
  } finally {
    clearing.value = false
  }
}
</script>

<style scoped>
.cms-overlay {
  position: fixed;
  inset: 0;
  z-index: 340;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 0;
  background: rgba(28, 38, 34, .42);
  animation: cms-fade 180ms ease backwards;
}

.cms-card {
  width: 100%;
  max-width: 460px;
  max-height: min(78vh, 620px);
  display: flex;
  flex-direction: column;
  padding: 20px 20px calc(16px + env(safe-area-inset-bottom));
  color: var(--game-ink, #3b3228);
  background: var(--game-surface-solid, #fffaf0);
  border: 2px solid var(--px-line, rgba(90, 62, 38, .28));
  border-radius: 6px 6px 0 0;
  box-shadow: 4px 4px 0 var(--px-shadow, rgba(74, 52, 32, .22));
  animation: cms-rise 240ms ease backwards;
}

@media (min-width: 640px) {
  .cms-overlay { align-items: center; padding: 20px; }
  .cms-card { border-radius: 6px; padding-bottom: 20px; }
}

.cms-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.cms-head h2 {
  margin: 0;
  font-family: var(--px-font, inherit);
  font-size: 18px;
  color: var(--game-ink, #3b3228);
}

.cms-head p {
  margin: 5px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--game-ink-2, #6b5c4e);
}

.cms-close {
  flex: none;
  width: 34px;
  height: 34px;
  border: 2px solid var(--px-line, rgba(90, 62, 38, .28));
  border-radius: 4px;
  background: transparent;
  color: var(--game-ink-2, #6b5c4e);
  font-size: 20px;
  line-height: 1;
}

.cms-close:hover { border-color: var(--px-gold, #b07a45); }
.cms-close:active { transform: translate(2px, 2px); }

.cms-off,
.cms-loading,
.cms-error,
.cms-empty {
  margin: 16px 0 0;
  padding: 12px 14px;
  border: 2px dashed var(--px-line, rgba(90, 62, 38, .28));
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--game-ink-2, #6b5c4e);
}

.cms-error { color: var(--game-danger, #b4534a); }
.cms-empty { border-style: solid; }

.cms-list {
  margin: 16px 0 0;
  padding: 0;
  list-style: none;
  overflow-y: auto;
  display: grid;
  gap: 8px;
}

.cms-list li {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 9px;
  padding: 10px 11px;
  border: 2px solid var(--px-line, rgba(90, 62, 38, .28));
  border-radius: 4px;
  background: var(--game-surface-soft, rgba(255, 247, 234, .66));
}

.cms-list li.is-inactive { opacity: .62; }

.cms-cat {
  padding: 2px 6px;
  border: 1px solid var(--px-line, rgba(90, 62, 38, .28));
  border-radius: 3px;
  font-size: 11px;
  color: var(--game-ink-3, #8a7a6a);
  white-space: nowrap;
}

.cms-text {
  min-width: 0;
  font-size: 13.5px;
  line-height: 1.45;
  color: var(--game-ink, #3b3228);
  overflow-wrap: anywhere;
}

.cms-paused {
  grid-column: 2;
  font-size: 11px;
  color: var(--game-ink-3, #8a7a6a);
}

.cms-forget {
  padding: 5px 9px;
  border: 2px solid var(--px-line, rgba(90, 62, 38, .28));
  border-radius: 4px;
  background: transparent;
  color: var(--game-ink-2, #6b5c4e);
  font-size: 12px;
  white-space: nowrap;
}

.cms-forget:hover { border-color: var(--game-danger, #b4534a); color: var(--game-danger, #b4534a); }
.cms-forget:disabled { opacity: .55; }

.cms-status {
  margin: 12px 0 0;
  font-size: 12.5px;
  color: var(--game-accent-strong, #3c6653);
}

.cms-foot {
  margin-top: auto;
  padding-top: 14px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
}

.cms-foot p {
  margin: 0;
  font-size: 11px;
  line-height: 1.55;
  color: var(--game-ink-3, #8a7a6a);
}

.cms-forget-all {
  flex: none;
  padding: 7px 11px;
  border: 2px solid var(--px-line, rgba(90, 62, 38, .28));
  border-radius: 4px;
  background: transparent;
  color: var(--game-danger, #b4534a);
  font-size: 12px;
  white-space: nowrap;
}

.cms-forget-all:hover { border-color: var(--game-danger, #b4534a); }
.cms-forget-all:disabled { opacity: .55; }

.cms-close:focus-visible,
.cms-forget:focus-visible,
.cms-forget-all:focus-visible {
  outline: 3px dashed var(--px-gold, #b07a45);
  outline-offset: 2px;
}

@keyframes cms-fade {
  from { opacity: 0; }
}

@keyframes cms-rise {
  from { opacity: 0; transform: translateY(14px); }
}

@media (prefers-reduced-motion: reduce) {
  .cms-overlay,
  .cms-card { animation: none; }
}
</style>
