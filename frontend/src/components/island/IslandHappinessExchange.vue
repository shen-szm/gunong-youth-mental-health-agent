<template>
  <section class="happiness-game" aria-labelledby="island-happiness-title">
    <header class="activity-copy">
      <div>
        <small>幸福交换树 · 卡牌交换</small>
        <h3 id="island-happiness-title">留下一件小事，换回一束微光</h3>
        <p>写下一件真实发生、让你觉得还不错的小事。内容保存在当前浏览器的此账号空间，逐条满 30 天后清理。</p>
      </div>
      <dl><div><dt>交换次数</dt><dd>{{ happiness.exchanges }}</dd></div><div><dt>幸福册</dt><dd>{{ happiness.notes.length }}</dd></div></dl>
    </header>

    <div class="exchange-layout">
      <form class="exchange-form" @submit.prevent="exchange">
        <label for="island-happiness-note">一件令你幸福的小事</label>
        <textarea
          id="island-happiness-note"
          v-model="input"
          :disabled="urgent"
          maxlength="80"
          rows="4"
          placeholder="例如：放学路上看见一只晒太阳的小猫。"
        ></textarea>
        <div class="privacy-copy">
          <span>{{ input.length }}/80</span>
          <small>请勿填写姓名、学校、电话或地址；共享设备上的其他使用者可能看到。</small>
        </div>
        <button type="submit" :disabled="urgent || !input.trim()">放进树洞并交换</button>
      </form>

      <div class="card-stage" aria-label="幸福灵感卡组">
        <Swiper
          v-if="happiness.exchanges"
          :modules="swiperModules"
          effect="cards"
          :grab-cursor="true"
          :keyboard="{ enabled: true }"
          :a11y="{ enabled: true, prevSlideMessage: '上一张幸福卡', nextSlideMessage: '下一张幸福卡' }"
          :initial-slide="happiness.cardIndex"
          @slide-change="rememberCard"
        >
          <SwiperSlide v-for="(card, index) in HAPPINESS_CARDS" :key="card">
            <article class="happiness-card">
              <small>咕哝预写的幸福灵感卡</small>
              <p>{{ card }}</p>
              <span>第 {{ index + 1 }} 束微光</span>
            </article>
          </SwiperSlide>
        </Swiper>
        <div v-else class="empty-card">
          <span aria-hidden="true">光</span>
          <strong>树上还留着一张卡</strong>
          <small>完成一次交换后，可以左右滑动查看卡组。</small>
        </div>
        <p class="system-card-note">卡片由系统预写，不是其他学生的实时分享。</p>
      </div>
    </div>

    <section v-if="urgent" ref="urgentPanel" class="happiness-safety" role="alert" aria-live="assertive" tabindex="-1">
      <h4>先确认你现在的安全</h4>
      <p>这些话可能表示你现在无法保证安全。请先不要独处，马上去到一位可信成年人身边；刚才的文字不会存入幸福册。</p>
      <div><a href="tel:12356">拨打 12356</a><a href="tel:110">拨打 110</a><a href="tel:120">拨打 120</a><button type="button" @click="$emit('open-chat')">打开倾诉求助</button></div>
      <small>如果家人可能是伤害来源，请联系可信老师、其他安全成年人或报警。AI 不能替代真人危机干预。</small>
    </section>

    <section v-if="happiness.notes.length" class="happiness-book" aria-labelledby="happiness-book-title">
      <header><div><small>当前设备的此账号空间</small><h4 id="happiness-book-title">我的幸福册</h4></div><button type="button" @click="clearAll">清空此设备记录</button></header>
      <ul>
        <li v-for="(note, index) in happiness.notes" :key="`${note.createdAt}-${index}`"><span>{{ note.text }}</span><button type="button" :aria-label="`删除幸福小事：${note.text}`" @click="remove(index)">删除</button></li>
      </ul>
    </section>
    <p v-if="storageError" class="storage-warning" role="alert">浏览器未能写入本次变化；请勿把当前页面内容视为已保存或已从设备清除。</p>
    <p class="activity-status" role="status" aria-live="polite">{{ message }}</p>
  </section>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { A11y, EffectCards, Keyboard } from 'swiper/modules'
import { Swiper, SwiperSlide } from 'swiper/vue'
import 'swiper/css'
import 'swiper/css/effect-cards'
import { isOfflineCompanionUrgent } from '../../utils/companionSafety.js'
import { HAPPINESS_CARDS } from '../../game/island/islandActivityState.js'

const props = defineProps({ happiness: { type: Object, required: true }, storageError: { type: Boolean, default: false } })
const emit = defineEmits(['update:happiness', 'played', 'open-chat'])
const swiperModules = [A11y, EffectCards, Keyboard]
const input = ref('')
const urgent = ref(false)
const urgentPanel = ref(null)
const message = ref('写下一件小事后，幸福树会为你换一张卡。')

function exchange() {
  if (urgent.value) return
  const note = input.value.trim().replace(/\s+/g, ' ').slice(0, 80)
  if (!note) return
  if (isOfflineCompanionUrgent(note)) {
    input.value = ''
    urgent.value = true
    message.value = '普通交换已停止。请优先联系可信成年人和真人安全支持。'
    emit('played', { activity: 'exchange', action: 'safety' })
    nextTick(() => urgentPanel.value?.focus({ preventScroll: true }))
    return
  }
  urgent.value = false
  const notes = [...props.happiness.notes, { text: note, createdAt: Date.now() }].slice(-12)
  const exchanges = props.happiness.exchanges + 1
  emit('update:happiness', { ...props.happiness, notes, exchanges, cardIndex: (exchanges - 1) % HAPPINESS_CARDS.length })
  input.value = ''
  message.value = '这件小事已加入本页幸福册，也换来了一张心岛幸福卡；设备保存状态会在下方提示。'
  emit('played', { activity: 'exchange', action: 'exchange' })
}

function rememberCard(swiper) {
  emit('update:happiness', { ...props.happiness, cardIndex: swiper.activeIndex })
}
function remove(index) {
  const notes = props.happiness.notes.filter((_, noteIndex) => noteIndex !== index)
  emit('update:happiness', { ...props.happiness, notes })
  message.value = props.storageError ? '浏览器未能写入删除结果，请勿把它视为已从设备清除。' : '已从你的幸福册删除。'
}
function clearAll() {
  emit('update:happiness', { ...props.happiness, notes: [] })
  message.value = props.storageError ? '浏览器未能写入清空结果，请勿把它视为已从设备清除。' : '幸福册已清空。'
}
</script>

<style scoped>
.happiness-game { display: grid; gap: 16px; color: #fff4df; }
.activity-copy { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.activity-copy small { color: #ffd083; font-size: 12px; font-weight: 800; letter-spacing: .06em; }
.activity-copy h3 { margin: 4px 0 0; font-size: 24px; line-height: 1.2; }
.activity-copy p { max-width: 62ch; margin: 7px 0 0; color: #f5d9bd; font-size: 14px; line-height: 1.55; }
.activity-copy dl { display: flex; gap: 8px; margin: 0; }
.activity-copy dl div { min-width: 88px; padding: 9px 12px; border: 1px solid rgba(255,224,187,.2); border-radius: 12px; background: #743f31; }
.activity-copy dt { color: #f0c7a6; font-size: 11px; }.activity-copy dd { margin: 3px 0 0; font-size: 18px; font-weight: 800; font-variant-numeric: tabular-nums; }
.exchange-layout { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(280px, .9fr); gap: 24px; align-items: stretch; }
.exchange-form { display: grid; align-content: start; gap: 10px; padding: 18px; border: 1px solid #bd7351; border-radius: 18px; background: #724235; }
.exchange-form label { font-size: 13px; font-weight: 900; }
.exchange-form textarea { box-sizing: border-box; width: 100%; min-height: 126px; resize: vertical; padding: 13px; border: 1px solid #d3936d; border-radius: 13px; color: #4a2b22; background: #fff0d5; font: inherit; font-size: 15px; line-height: 1.6; }
.privacy-copy { display: flex; justify-content: space-between; gap: 12px; color: #f2ccb0; font-size: 11px; line-height: 1.45; }.privacy-copy small { max-width: 56ch; }
.exchange-form > button { min-height: 48px; border: 0; border-radius: 12px; color: #4a2b22; background: #ffd083; font: inherit; font-weight: 900; cursor: pointer; }.exchange-form > button:disabled { opacity: .48; cursor: not-allowed; }
.card-stage { display: grid; min-width: 0; align-content: center; justify-items: center; padding: 12px 28px; border: 1px solid #bd7351; border-radius: 18px; background: #5e3d38; overflow: hidden; }
.card-stage :deep(.swiper) { width: min(100%, 330px); min-width: 0; height: 190px; margin: 0; place-self: center; overflow: visible; }
.card-stage :deep(.swiper-slide) { border-radius: 18px; }
.happiness-card, .empty-card { box-sizing: border-box; display: grid; width: 100%; height: 100%; align-content: center; justify-items: start; padding: 24px; border: 1px solid #fff0bf; border-radius: 18px; color: #4a2b22; background: #ffdca0; box-shadow: 0 14px 26px rgba(45,23,27,.3); }
.happiness-card small { font-size: 10px; font-weight: 900; letter-spacing: .05em; }.happiness-card p { margin: 14px 0; font-size: 18px; font-weight: 800; line-height: 1.55; }.happiness-card span { font-size: 11px; opacity: .72; }
.empty-card { justify-items: center; text-align: center; color: #f9ddc1; background: #784b3f; }.empty-card > span { display: grid; width: 48px; height: 48px; place-items: center; border: 1px solid #ffd083; border-radius: 14px; color: #ffd083; font-weight: 900; }.empty-card strong { margin-top: 12px; }.empty-card small { margin-top: 5px; color: #edc8aa; }
.system-card-note { margin: 13px 0 0; color: #e8bfa3; font-size: 10px; text-align: center; }
.happiness-safety { padding: 16px; border: 2px solid #e49078; border-radius: 16px; color: #fff6eb; background: #793d36; }.happiness-safety h4 { margin: 0; font-size: 16px; }.happiness-safety p { margin: 7px 0; font-size: 13px; line-height: 1.55; }.happiness-safety > div { display: flex; flex-wrap: wrap; gap: 8px; }.happiness-safety a, .happiness-safety button { display: grid; min-height: 44px; padding: 0 13px; place-items: center; border: 0; border-radius: 11px; color: #4a2b22; background: #ffe0a9; font: inherit; font-weight: 900; text-decoration: none; }.happiness-safety > small { display: block; margin-top: 8px; color: #f1c9b2; font-size: 11px; line-height: 1.5; }
.happiness-book { padding-top: 14px; border-top: 1px solid rgba(255,224,187,.18); }.happiness-book header { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; }.happiness-book header small { color: #eab998; font-size: 10px; }.happiness-book h4 { margin: 2px 0 0; font-size: 16px; }.happiness-book header button, .happiness-book li button { min-height: 38px; border: 0; color: #f1c6aa; background: transparent; cursor: pointer; }.happiness-book ul { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; margin: 10px 0 0; padding: 0; list-style: none; }.happiness-book li { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 9px 11px; border-radius: 11px; background: #6e4339; }.happiness-book li span { font-size: 12px; line-height: 1.45; }
.activity-status { min-height: 20px; margin: 0; color: #f5d9bd; font-size: 13px; }
.storage-warning { margin: 0; padding: 10px 12px; border: 1px solid #e7a087; border-radius: 11px; color: #fff0e5; background: #743b35; font-size: 12px; line-height: 1.5; }
button:focus-visible, a:focus-visible, textarea:focus-visible { outline: 3px solid #fff0a8; outline-offset: 3px; }
@media (max-width: 900px) { .activity-copy dl { display: none; } .exchange-layout { grid-template-columns: 1fr; } .happiness-book ul { grid-template-columns: 1fr; } }
</style>
