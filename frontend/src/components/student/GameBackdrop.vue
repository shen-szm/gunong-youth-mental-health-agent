<template>
  <div class="game-backdrop" :class="[`is-${part}`, `variant-${variant}`]" aria-hidden="true">
    <img class="gb-scene" :src="scene" alt="" />
    <div class="gb-wash"></div>
    <div class="gb-sun"></div>
    <div class="gb-glow"></div>
    <div v-if="part !== 'day'" class="gb-fireflies">
      <i v-for="n in 12" :key="n" :style="fireflyStyle(n)"></i>
    </div>
    <div class="gb-vignette"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import homeDay from '../../assets/island/home-day.png'
import homeDusk from '../../assets/island/home-dusk.png'
import homeNight from '../../assets/island/home-night.png'

const props = defineProps({
  part: { type: String, default: 'day' },
  variant: { type: String, default: 'page' },
})

const scene = computed(() => {
  if (props.part === 'evening') return homeDusk
  if (props.part === 'night') return homeNight
  return homeDay
})

function fireflyStyle(n) {
  const left = (n * 37 + 11) % 100
  const top = 24 + ((n * 53) % 62)
  const size = 2 + (n % 3)
  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${(n * 1.7) % 6}s`,
    animationDuration: `${4 + (n % 4)}s`,
  }
}
</script>

<style scoped>
.game-backdrop {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.gb-scene {
  position: absolute;
  left: 50%;
  bottom: -6vh;
  width: max(120vw, 900px);
  transform: translateX(-50%);
  opacity: 0.38;
  filter: saturate(0.92);
  mask-image: linear-gradient(to top, #000 0%, rgba(0, 0, 0, 0.72) 32%, transparent 78%);
  -webkit-mask-image: linear-gradient(to top, #000 0%, rgba(0, 0, 0, 0.72) 32%, transparent 78%);
  transition: opacity 600ms ease;
}

.is-evening .gb-scene { opacity: 0.42; filter: saturate(0.86) brightness(0.86); }
.is-night .gb-scene { opacity: 0.46; filter: saturate(0.72) brightness(0.62); }

.gb-wash {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(120% 80% at 50% 0%, rgba(255, 250, 240, 0.55), transparent 60%),
    linear-gradient(180deg, #f5ecdc 0%, rgba(245, 236, 220, 0.86) 46%, rgba(245, 236, 220, 0.28) 100%);
  transition: background 600ms ease;
}
.is-evening .gb-wash {
  background:
    radial-gradient(120% 80% at 50% 0%, rgba(255, 196, 128, 0.14), transparent 58%),
    linear-gradient(180deg, #3a2c24 0%, rgba(58, 44, 36, 0.86) 48%, rgba(44, 33, 27, 0.4) 100%);
}
.is-night .gb-wash {
  background:
    radial-gradient(120% 80% at 50% 0%, rgba(227, 194, 125, 0.08), transparent 58%),
    linear-gradient(180deg, #241c17 0%, rgba(36, 28, 23, 0.88) 48%, rgba(26, 20, 16, 0.5) 100%);
}

.gb-sun {
  position: absolute;
  top: 6vh;
  right: 12vw;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 226, 168, 0.7), rgba(255, 226, 168, 0));
  filter: blur(2px);
  transition: background 600ms ease, opacity 600ms ease;
}
.is-evening .gb-sun {
  top: 26vh;
  right: 16vw;
  background: radial-gradient(circle, rgba(255, 183, 120, 0.5), rgba(255, 183, 120, 0));
}
.is-night .gb-sun {
  top: 8vh;
  right: 18vw;
  width: 84px;
  height: 84px;
  background: radial-gradient(circle, rgba(241, 230, 210, 0.32), rgba(241, 230, 210, 0));
}

.gb-glow {
  position: absolute;
  left: 50%;
  bottom: -12vh;
  width: 80vw;
  height: 34vh;
  transform: translateX(-50%);
  background: radial-gradient(ellipse at center, rgba(255, 214, 150, 0.22), transparent 70%);
  transition: background 600ms ease;
}
.is-night .gb-glow {
  background: radial-gradient(ellipse at center, rgba(227, 194, 125, 0.12), transparent 70%);
}

.gb-fireflies {
  position: absolute;
  inset: 0;
}
.gb-fireflies i {
  position: absolute;
  border-radius: 50%;
  background: #f6d68f;
  box-shadow: 0 0 8px 2px rgba(246, 214, 143, 0.55);
  opacity: 0;
  animation: gb-drift 5s ease-in-out infinite;
}

.gb-vignette {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 62%, rgba(56, 38, 24, 0.16) 100%);
}
.is-night .gb-vignette {
  background: linear-gradient(180deg, transparent 60%, rgba(0, 0, 0, 0.3) 100%);
}

.variant-chat .gb-scene { opacity: 0.28; }
.variant-chat.is-evening .gb-scene { opacity: 0.32; }
.variant-chat.is-night .gb-scene { opacity: 0.36; }

@keyframes gb-drift {
  0%, 100% { opacity: 0; transform: translate3d(0, 6px, 0); }
  40% { opacity: 0.9; transform: translate3d(6px, -8px, 0); }
  70% { opacity: 0.35; transform: translate3d(-4px, -14px, 0); }
}

@media (prefers-reduced-motion: reduce) {
  .gb-fireflies i { animation: none !important; opacity: 0.5; }
  .gb-scene, .gb-wash, .gb-sun, .gb-glow { transition: none !important; }
}
</style>
