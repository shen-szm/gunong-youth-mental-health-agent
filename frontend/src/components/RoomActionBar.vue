<template>
  <Transition name="room-action">
    <section
      v-if="feature"
      ref="actionBar"
      class="room-action-bar"
      aria-labelledby="room-action-title"
      @keydown.esc="$emit('close')"
    >
      <span class="room-action-symbol" aria-hidden="true">{{ feature.symbol }}</span>
      <div class="room-action-copy">
        <p>{{ feature.location }}</p>
        <h2 id="room-action-title">{{ feature.title }}</h2>
        <span>{{ feature.description }}</span>
      </div>

      <fieldset v-if="feature.id === 'daily'" class="room-action-moods">
        <legend>此刻更接近</legend>
        <button
          v-for="mood in moods"
          :key="mood"
          type="button"
          :class="{ active: selectedMood === mood }"
          :aria-pressed="selectedMood === mood"
          @click="$emit('select-mood', mood)"
        >
          {{ mood }}
        </button>
      </fieldset>

      <div class="room-action-controls">
        <button ref="primaryButton" class="room-action-primary" type="button" :disabled="feature.actionDisabled" @click="$emit('primary')">
          {{ feature.actionLabel }}
        </button>
        <button class="room-action-close" type="button" aria-label="关闭场景操作条" @click="$emit('close')">×</button>
      </div>
    </section>
  </Transition>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  feature: { type: Object, default: null },
  moods: { type: Array, default: () => [] },
  selectedMood: { type: String, default: '' },
})

defineEmits(['primary', 'close', 'select-mood'])

const actionBar = ref(null)
const primaryButton = ref(null)

watch(() => props.feature?.id, async value => {
  if (!value) return
  await nextTick()
  const target = props.feature?.actionDisabled
    ? actionBar.value?.querySelector('.room-action-moods button')
    : primaryButton.value
  target?.focus({ preventScroll: true })
})
</script>

<style scoped>
.room-action-bar {
  position: fixed;
  left: 50%;
  bottom: calc(112px + env(safe-area-inset-bottom));
  z-index: 225;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  width: min(680px, calc(100vw - 32px));
  min-height: 72px;
  padding: 12px;
  border-radius: 14px;
  color: #f7f4ed;
  background: rgba(16, 22, 28, .92);
  box-shadow: 0 6px 8px rgba(5, 8, 12, .3);
  backdrop-filter: blur(20px) saturate(1.14);
  transform: translateX(-50%);
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', system-ui, sans-serif;
}
.room-action-symbol {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  color: #1d2a25;
  background: #b8d7c7;
  font: 800 18px/1 ui-monospace, 'SFMono-Regular', Consolas, monospace;
}
.room-action-copy { min-width: 0; }
.room-action-copy p,
.room-action-copy h2,
.room-action-copy span { margin: 0; }
.room-action-copy p { color: #b8d7c7; font-size: 10px; font-weight: 700; }
.room-action-copy h2 { margin-top: 2px; font-size: 14px; line-height: 1.35; }
.room-action-copy span { display: block; margin-top: 2px; color: rgba(247, 244, 237, .76); font-size: 11px; line-height: 1.45; }
.room-action-controls { display: flex; align-items: center; gap: 7px; }
.room-action-primary,
.room-action-close,
.room-action-moods button {
  border: 0;
  border-radius: 10px;
  font: inherit;
  cursor: pointer;
}
.room-action-primary {
  min-height: 42px;
  padding: 0 16px;
  color: #18231f;
  background: #e8d49b;
  font-size: 12px;
  font-weight: 800;
}
.room-action-close {
  width: 42px;
  height: 42px;
  color: #f7f4ed;
  background: rgba(255, 255, 255, .08);
  font-size: 20px;
}
.room-action-moods {
  grid-column: 2 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  border: 0;
}
.room-action-moods legend { float: left; margin-right: 4px; color: rgba(247, 244, 237, .72); font-size: 10px; line-height: 32px; }
.room-action-moods button { min-height: 32px; padding: 0 10px; color: rgba(247, 244, 237, .82); background: rgba(255, 255, 255, .08); font-size: 11px; }
.room-action-moods button.active { color: #1d2a25; background: #b8d7c7; }
.room-action-primary:hover { background: #f0dc9f; }
.room-action-primary:disabled { color: rgba(24, 35, 31, .62); background: #b9ae8b; cursor: not-allowed; }
.room-action-close:hover,
.room-action-moods button:hover { background: rgba(255, 255, 255, .15); }
.room-action-primary:focus-visible,
.room-action-close:focus-visible,
.room-action-moods button:focus-visible { outline: 3px solid #f0d58e; outline-offset: 2px; }
.room-action-enter-active,
.room-action-leave-active { transition: opacity .18s ease, transform .18s cubic-bezier(.22, 1, .36, 1); }
.room-action-enter-from,
.room-action-leave-to { opacity: 0; transform: translate(-50%, 8px); }

@media (max-width: 640px) {
  .room-action-bar {
    grid-template-columns: 38px minmax(0, 1fr) auto;
    bottom: calc(100px + env(safe-area-inset-bottom));
    width: calc(100vw - 24px);
    min-height: 64px;
    padding: 10px;
  }
  .room-action-symbol { width: 44px; height: 44px; }
  .room-action-copy span { display: none; }
  .room-action-primary { min-height: 44px; max-width: 116px; padding-inline: 12px; }
  .room-action-close { width: 44px; height: 44px; }
  .room-action-moods button { min-height: 44px; }
  .room-action-moods { grid-column: 1 / -1; }
}

@media (prefers-reduced-motion: reduce) {
  .room-action-enter-active,
  .room-action-leave-active { transition: none; }
}
</style>
