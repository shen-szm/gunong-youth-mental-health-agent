<template>
  <div class="sc-page game-page" :data-part="part">
    <GameBackdrop :part="part" variant="chat" />
    <header class="sc-head">
      <div class="sc-head-inner">
        <router-link class="sc-back" to="/" aria-label="返回首页">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
        </router-link>
        <router-link class="sc-pet" to="/" aria-label="咕团在首页等你，点击返回" title="回首页看看咕团">
          <img :src="petAvatar" alt="咕团" />
        </router-link>
        <div class="sc-head-copy">
          <strong id="sc-chat-title">咕哝倾诉空间</strong>
          <small><span class="sc-dot" :class="{ thinking: chatLoading }"></span>{{ chatLoading ? '正在思考...' : '在线，随时倾听' }}</small>
        </div>
        <button
          v-if="!chatUrgentLocked && hasUserMessage"
          class="sc-end"
          type="button"
          :disabled="chatLoading"
          @click="requestConversationEnd"
        >结束本次倾诉</button>
      </div>
    </header>

    <div class="sc-msgs" ref="msgBox">
      <div class="sc-msgs-inner" :class="{ 'is-empty': chatMessages.length === 0 }">
        <div v-if="guideCompleteNotice" class="sc-guide-notice" role="status">
          第一段倾诉已经完成，引导也收好啦。
          <router-link to="/">回首页看看咕团</router-link>
        </div>
        <div class="sc-welcome" v-if="chatMessages.length === 0">
          <img :src="guguanAvatar" class="sc-welcome-avatar" alt="咕团" />
          <div class="sc-welcome-bubble">
            <p>先不用把话组织好。</p>
            <small>一件小事、一段说不清的感受，或者今天的好消息，都可以从这里开始。</small>
          </div>
        </div>
        <div v-if="!chatMessages.length" class="sc-starters" aria-label="选择倾诉开场">
          <button v-for="starter in conversationStarters" :key="starter.title" type="button" :title="starter.text" @click="prepareConversation(starter.text)"><strong>{{ starter.title }}</strong><span>{{ starter.text }}</span></button>
        </div>

        <StudentScreeningCard
          v-if="!chatMessages.length && (!chatUrgentLocked || screeningUrgentActive)"
          ref="screeningCard"
          :paused="chatUrgentLocked"
          @urgent="handleScreeningUrgent"
          @updated="handleScreeningUpdated"
        />

        <div v-for="(m, i) in chatMessages" :key="i" :class="['sc-row', m.role]">
          <img v-if="m.role === 'assistant'" :src="guguanAvatar" class="sc-msg-avatar" alt="咕团" />
          <div class="sc-bwrap">
            <div v-if="m.role === 'user' && m.emotion" class="sc-etag" :title="m.emotion_basis?.length ? `依据：${m.emotion_basis.join('；')}` : '基于本轮表达的非诊断性情绪线索'">
              <span>{{ getEmotionEmoji(m.emotion) }}</span>
              <span>{{ m.emotion }}{{ m.emotion_intensity && m.emotion_intensity !== '不确定' ? ` · ${m.emotion_intensity}` : '' }}</span>
            </div>
            <div class="sc-bubble">
              <span>{{ m.content }}</span>
            </div>
            <button v-if="m.role === 'assistant'" class="sc-tts" type="button" @click="toggleTTS(m.content, i)" :class="{ playing: ttsPlaying === i }" :aria-label="ttsPlaying === i ? '停止朗读' : '朗读这条回复'">
              <svg v-if="ttsPlaying !== i" viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.8-1-3.3-2.5-4v8c1.5-.7 2.5-2.2 2.5-4z"/></svg>
              <svg v-else viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            </button>
          </div>
        </div>

        <div v-if="chatLoading" class="sc-row assistant">
          <img :src="guguanAvatar" class="sc-msg-avatar" alt="咕团" />
          <div class="sc-bwrap">
            <div class="sc-bubble sc-typing">
              <span class="sc-tdot"></span><span class="sc-tdot"></span><span class="sc-tdot"></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!chatUrgentLocked" class="sc-consentbar">
      <div class="sc-consent" :class="{ 'is-open': policyExpanded }" role="note">
        <button
          type="button"
          class="sc-consent-toggle"
          :aria-expanded="policyExpanded"
          aria-controls="sc-consent-detail"
          @click="policyExpanded = !policyExpanded"
        >
          <strong>{{ consentTitle }}</strong>
          <span>{{ policyExpanded ? '收起' : '数据说明' }}</span>
          <svg :class="{ open: policyExpanded }" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m6 9 6 6 6-6"/></svg>
        </button>
        <small v-if="policyExpanded" id="sc-consent-detail">{{ consentDetail }}</small>
      </div>
    </div>

    <section
      v-if="chatUrgentLocked"
      ref="chatUrgentSupport"
      class="sc-urgent"
      role="alert"
      aria-live="assertive"
      aria-labelledby="sc-urgent-title"
      tabindex="-1"
    >
      <strong id="sc-urgent-title">先保持真人支持，不要独处</strong>
      <p>请先去到可信成年人身边并远离危险物。若已采取行动或正处在迫切危险中，立即拨打 110 或 120；也可拨打 12356。咕哝是 AI 支持工具，不能替代真人危机干预。</p>
      <div class="sc-calls" aria-label="紧急求助电话">
        <a href="tel:12356">拨打 12356</a>
        <a href="tel:110">拨打 110</a>
        <a href="tel:120">拨打 120</a>
      </div>
      <label><input v-model="safetyCurrentSafe" type="checkbox"> 我现在在安全地点，身边没有危险物</label>
      <label><input v-model="safetyContactedAdult" type="checkbox"> 我已经联系并和一位可信成年人待在一起</label>
      <small v-if="!safetyCurrentSafe || !safetyContactedAdult" class="sc-resolve-hint">
        请先勾选以上两项，确认你已在安全地点并已联系可信成年人。
      </small>
      <button
        class="sc-resolve"
        type="button"
        :disabled="!safetyCurrentSafe || !safetyContactedAdult || safetyResolving"
        @click="resolveUrgentChat"
      >{{ safetyResolving ? '正在确认…' : '确认已完成安全交接，开始新话题' }}</button>
      <p v-if="safetyResolveError" class="sc-safety-error" role="status">{{ safetyResolveError }}</p>
    </section>

    <section v-if="showEndConfirmation && !chatUrgentLocked" class="sc-endconfirm" role="status" aria-live="polite">
      <div>
        <strong>要结束本次倾诉并生成小结吗？</strong>
        <span>会整理整段对话；这不是诊断或量表结果。</span>
      </div>
      <div class="sc-endconfirm-actions">
        <button type="button" @click="cancelConversationEnd">继续聊</button>
        <button class="sc-endconfirm-primary" type="button" @click="completeConversation">生成小结</button>
      </div>
    </section>

    <section
      v-if="showProfessionalNotice"
      class="sc-screening-ack"
      role="note"
      aria-live="polite"
      aria-labelledby="sc-screening-ack-title"
    >
      <div class="sc-screening-ack-copy">
        <strong id="sc-screening-ack-title">筛查结果正在影响聊天</strong>
        <p>你最近一次状态筛查的总分偏高，这不是诊断。在你确认已联系可信成年人之前，咕哝会先给出安全建议。</p>
        <small>如果还没有联系，请先找家长、老师或学校心理老师；有即时危险请拨打 110 或 120。确认后会恢复普通对话，筛查结果仍保留，可随时删除。</small>
      </div>
      <button
        ref="screeningAckButton"
        type="button"
        :disabled="screeningAcking"
        @click="acknowledgeProfessionalScreening"
      >{{ screeningAcking ? '正在记录…' : '我已知晓并已联系可信成年人' }}</button>
      <p v-if="screeningAckError" class="sc-screening-ack-error" role="status">{{ screeningAckError }}</p>
    </section>
    <p v-else-if="screeningAckDone" class="sc-screening-ackdone" role="status">
      已记录你的确认，接下来会恢复正常对话。筛查结果仍保留。
    </p>

    <div v-if="!chatUrgentLocked && chatMessages.length" class="sc-quickwrap">
      <div
        class="sc-quick"
        ref="quickScroll"
        @wheel="onQuickWheel"
        @mousedown="onQuickMouseDown"
        @mousemove="onQuickMouseMove"
        @mouseup="onQuickMouseUp"
        @mouseleave="onQuickMouseUp"
      >
        <button v-for="e in conversationFollowups" :key="e.text" class="sc-chip" @click="prepareConversation(e.text)">
          <span>{{ e.emoji }}</span> {{ e.text }}
        </button>
      </div>
    </div>

    <div v-if="!chatUrgentLocked" class="sc-inputbar">
      <button class="sc-voice" :class="{ recording }" @click="toggleVoice" :disabled="chatLoading || !voiceInputEnabled" :title="voiceInputEnabled ? (recording ? '停止录音' : '语音输入') : '语音输入需独立授权后启用'">
        <svg v-if="!recording" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 14c1.7 0 3-1.3 3-3V5c0-1.7-1.3-3-3-3S9 3.3 9 5v6c0 1.7 1.3 3 3 3zm5.3-3c0 3-2.5 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.4 2.7 6.2 6 6.7V21h2v-3.3c3.3-.5 6-3.3 6-6.7h-1.7z"/></svg>
        <span v-else class="sc-rec-wave" aria-hidden="true"></span>
      </button>
      <div class="sc-iinput">
        <input v-model="chatInput" :placeholder="chatInputPlaceholder" @keydown.enter="onInputEnter" :disabled="chatLoading" ref="inputEl" aria-label="输入想说的话" />
      </div>
      <button class="sc-send" @click="sendChatMsg()" :disabled="chatLoading || !chatInput.trim()" aria-label="发送">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
      </button>
    </div>

    <p v-if="recording" class="sc-rechint" role="status"><span class="sc-rec-dot" aria-hidden="true"></span> 正在录音，再次点击停止</p>

    <button
      v-if="summaryStatus !== 'idle'"
      ref="summaryOrbButton"
      class="sc-orb"
      :class="[`is-${summaryStatus}`, { 'has-unread': summaryUnread }]"
      type="button"
      :disabled="summaryStatus === 'processing'"
      :aria-label="summaryOrbLabel"
      :aria-expanded="showSupportDrawer"
      @click="openSummaryDrawer"
    >
      <span class="sc-orb-pixel" aria-hidden="true"><img :src="guguanAvatar" alt="" /></span>
      <span class="sc-orb-copy">
        <strong>{{ summaryStatus === 'processing' ? '正在整理' : summaryStatus === 'error' ? '整理失败' : '倾诉小结' }}</strong>
        <small>{{ summaryStatus === 'ready' ? `${conversationSummary?.dominant_emotion || '情绪'} · ${conversationSummary?.intensity || ''}` : summaryStatus === 'error' ? '点此重试' : '请稍候' }}</small>
      </span>
      <span v-if="summaryUnread" class="sc-orb-dot" aria-hidden="true"></span>
    </button>
    <p class="sc-live" aria-live="polite" aria-atomic="true">{{ summaryStatus === 'ready' && summaryUnread ? '本次倾诉小结已经整理完成' : '' }}</p>

    <Transition name="sc-fade">
      <div v-if="showSupportDrawer" class="sc-drawer-mask" @click.self="closeSupportDrawer">
        <aside ref="drawerEl" class="sc-drawer" role="dialog" aria-modal="true" aria-labelledby="sc-drawer-title" tabindex="-1">
          <button class="sc-drawer-close" type="button" aria-label="关闭倾诉小结" @click="closeSupportDrawer">×</button>

          <template v-if="supportDrawerMode === 'plan' && summaryStatus === 'ready' && conversationSummary">
            <p class="sc-eyebrow">本次倾诉小结</p>
            <h2 id="sc-drawer-title" ref="supportModeHeading" tabindex="-1">我听到的是</h2>
            <div class="sc-emo-state">
              <span class="sc-emo-icon" aria-hidden="true">{{ getEmotionEmoji(conversationSummary.dominant_emotion) }}</span>
              <div><small>主要情绪</small><strong>{{ conversationSummary.dominant_emotion }} · {{ conversationSummary.intensity }}</strong></div>
            </div>
            <p class="sc-summary">{{ conversationSummary.summary }}</p>

            <section class="sc-section" aria-labelledby="sc-evidence-title">
              <h3 id="sc-evidence-title">我为什么这样理解</h3>
              <ul><li v-for="signal in conversationSummary.signals" :key="signal.message_id">{{ signal.observation }}</li></ul>
            </section>

            <section class="sc-need">
              <span>你现在可能更需要</span>
              <strong>{{ conversationSummary.support_need }}</strong>
            </section>

            <section v-if="conversationSummary.risk_level === 'professional'" class="sc-pro" role="note">
              <strong>建议尽快接入真人专业支持</strong>
              <p>这些影响已经不适合只靠自己扛着。今天请告诉一位可信成年人，并请对方协助联系学校心理老师、12356或正规医疗机构。</p>
            </section>

            <section class="sc-section" aria-live="polite">
              <h3>倾诉后的下一步</h3>
              <ol class="sc-next"><li v-for="(action, index) in conversationSummary.next_steps" :key="action" :class="{ primary: index === 0 }">{{ action }}</li></ol>
              <small v-if="supportFeedback" class="sc-feedback">{{ supportFeedback }}</small>
            </section>

            <p class="sc-boundary">{{ conversationSummary.boundary }}</p>
            <div class="sc-drawer-controls">
              <button class="sc-primary" type="button" @click="continueAfterSummary">继续倾诉</button>
              <button type="button" @click="startNewConversation">开始新话题</button>
            </div>
            <button class="sc-help-link" type="button" @click="supportDrawerMode = 'help'">我想找人帮忙</button>
            <button class="sc-del-link" type="button" @click="removeConversationSummary">删除本次小结</button>
          </template>

          <template v-else-if="supportDrawerMode === 'plan'">
            <p class="sc-eyebrow">倾诉后的下一步</p>
            <h2 id="sc-drawer-title" ref="supportModeHeading" tabindex="-1">这次没有整理完成</h2>
            <p class="sc-summary">聊天内容还在。你可以继续倾诉，或重新尝试生成小结。</p>
            <button class="sc-primary sc-submit" type="button" @click="completeConversation">重新整理</button>
            <button class="sc-help-link" type="button" @click="continueAfterSummary">继续倾诉</button>
          </template>

          <template v-else-if="supportDrawerMode === 'help'">
            <p class="sc-eyebrow">把支持接到真人</p>
            <h2 id="sc-drawer-title" ref="supportModeHeading" tabindex="-1">你希望谁先来帮忙？</h2>
            <p class="sc-summary">只说你愿意说的。你可以先选一位可信成年人，再决定是否把刚才的摘要给对方看。</p>
            <div class="sc-person-grid">
              <button v-for="person in ['班主任或老师', '家长或监护人', '其他可信成年人']" :key="person" type="button" :aria-pressed="selectedSupportPerson === person" :class="{ active: selectedSupportPerson === person }" @click="selectedSupportPerson = person">{{ person }}</button>
            </div>
            <label class="sc-share-toggle"><input v-model="shareSupportSummary" type="checkbox" /> 把上面的摘要写进求助卡</label>
            <p class="sc-send-boundary">系统不会自动通知任何人。确认后会生成一张求助卡，由你决定何时当面给对方看。</p>
            <button class="sc-primary sc-submit" type="button" :disabled="!selectedSupportPerson" @click="confirmHelpRequest">生成求助卡</button>
            <button class="sc-help-link" type="button" @click="supportDrawerMode = 'plan'">返回上一步</button>
          </template>

          <template v-else>
            <p class="sc-eyebrow">可以当面展示的求助卡</p>
            <h2 id="sc-drawer-title" ref="supportModeHeading" tabindex="-1">我想请你先听我说</h2>
            <section class="sc-card-preview">
              <span>给 {{ currentHelpCard.person }}</span>
              <p v-if="currentHelpCard.summary">{{ currentHelpCard.summary }}</p>
              <p v-else>我最近遇到了一件自己不太能处理的事，希望你先听我说，再和我一起想下一步。</p>
              <strong>你现在不用马上解决，请先陪我把话说完。</strong>
            </section>
            <p class="sc-send-boundary">这张卡不会自动发送。你可以把当前屏幕当面给对方看。</p>
            <button class="sc-primary sc-submit" type="button" @click="closeSupportDrawer">完成并关闭</button>
            <button class="sc-help-link" type="button" @click="supportDrawerMode = 'help'">返回修改</button>
          </template>
        </aside>
      </div>
    </Transition>
  </div>
</template>

<script setup>
// 从 RoomHomeView.vue（alpha.37）移植的学生聊天实现：
// 会话生命周期、危机锁、结束确认、小结与求助卡抽屉与旧实现保持一致，
// 仅剥离房间专属元素（Agent 轨迹、首启引导、天气/音乐），换用极简皮肤。
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { activateDialog } from '../utils/dialogFocus'
import { useTimeOfDay } from '../utils/timeOfDay'
import { petImageForStatus, readPetCompanion } from '../utils/petCompanion'
import StudentScreeningCard from '../components/StudentScreeningCard.vue'
import GameBackdrop from '../components/student/GameBackdrop.vue'
import { acknowledgeScreening, getLatestScreening } from '../api/screening'
import {
  completeChatSession,
  deleteChatSummary,
  getChatHistory,
  getLatestChatSummary,
  resolveChatSafety,
  sendMessage,
  startChatSession,
} from '../api/chat'

const route = useRoute()
const userStore = useUserStore()

const part = useTimeOfDay()
const petState = computed(() => readPetCompanion(userStore.userId))
const petAvatar = computed(() => {
  const status = part.value === 'night' && petState.value.status !== 'happy' ? 'sleeping' : petState.value.status
  return petImageForStatus(status)
})
// 聊天头像不跟随“夜里睡觉”的门口宠物状态，保持在线陪伴的表情。
const guguanAvatar = computed(() => petImageForStatus(petState.value.status))
const FIRST_RUN_GUIDE_KEY = 'shengyu_first_run_guide_completed_version'
const FIRST_RUN_GUIDE_VERSION = '4.3.0'
const guidePending = ref(false)
const guideCompleteNotice = ref(false)

function safeSessionGet(key) {
  try { return sessionStorage.getItem(key) } catch { return null }
}

function completePendingGuide(message, reply) {
  if (!guidePending.value) return
  guidePending.value = false
  guideCompleteNotice.value = true
  const emotion = reply?.emotion || '被认真听见'
  const summary = message
    ? `你刚刚说的是：“${message.slice(0, 18)}${message.length > 18 ? '…' : ''}”。这份心情已经被好好接住。`
    : '你已经完成了第一次小倾诉，这份心情已经被好好接住。'
  try {
    const uid = userStore.userId || 'guest'
    localStorage.setItem(`${FIRST_RUN_GUIDE_KEY}:${uid}`, FIRST_RUN_GUIDE_VERSION)
    localStorage.setItem(`shengyu_first_run_mood_card:${uid}`, JSON.stringify({
      emoji: emotion.includes('开') ? '🌤️' : emotion.includes('难') ? '🌧️' : '🌱',
      title: '今日心情卡',
      copy: summary,
      emotion,
      summary,
      suggestion: '去树洞看看，也许会遇到相似的回声。',
    }))
    sessionStorage.removeItem('gy_guide_pending_chat')
  } catch {}
  setTimeout(() => { guideCompleteNotice.value = false }, 8000)
}

const conversationStarters = [
  { title: '先听我说', text: '我想先说说，暂时不用给建议。' },
  { title: '一起理清楚', text: '最近有件事反复占着我的心思，我想一起理一理。' },
  { title: '留住好消息', text: '今天有一个让我开心的小瞬间，想和你分享。' },
]
const conversationFollowups = [
  { emoji: '💬', text: '先听我说，暂时不用给建议。' },
  { emoji: '📝', text: '我想一起整理一下这件事。' },
  { emoji: '🌱', text: '我想试一个很小的步骤。' },
  { emoji: '☕', text: '我想先停一会儿，不用追问。' },
]
const chatInput = ref('')
const chatInputPlaceholder = '说说你的感受...'
const externalAiConsent = ref(false)
const companionEngine = ref(null)
const consentTitle = computed(() => {
  if (!externalAiConsent.value) return '当前使用本地安全回应'
  return companionEngine.value === 'legacy_xunfei' ? '讯飞策略协作已启用' : 'DeepSeek 小满对话已启用'
})
const consentDetail = computed(() => {
  if (!externalAiConsent.value) return '模型服务暂不可用，系统会继续提供本地安全回应。'
  if (companionEngine.value === 'legacy_xunfei') {
    return '无需单独申请即可对话；文字倾诉只在本地提取情绪、主题、功能影响等去标识化结构线索，由模型选择回应策略、后端生成安全话术。聊天原文、姓名、学校、联系方式、精确地址和原始录音不会发送给外部模型，危机判断始终由本地安全规则优先处理。'
  }
  return '无需单独申请即可对话；对话原文会发送给平台接入的 DeepSeek 模型，用于生成本轮回应和本次小结。姓名、学校、联系方式、精确地址和原始录音不会发送。危机判断与风险等级始终由本地安全规则优先处理。'
})
const policyExpanded = ref(false)
const voiceInputEnabled = ref(false)
const chatMessages = ref([])
const chatLoading = ref(false)
const recording = ref(false)
const msgBox = ref(null)
const inputEl = ref(null)
const ttsPlaying = ref(-1)
const chatSessionId = ref('')
const screeningCard = ref(null)
const chatUrgentSupport = ref(null)
const chatUrgentLocked = ref(false)
const screeningUrgentActive = ref(false)
const screeningState = ref(null)
const screeningAckButton = ref(null)
const screeningAcking = ref(false)
const screeningAckError = ref('')
const screeningAckDone = ref(false)
const safetyCurrentSafe = ref(false)
const safetyContactedAdult = ref(false)
const safetyResolving = ref(false)
const safetyResolveError = ref('')
const summarySessionId = ref('')
const showEndConfirmation = ref(false)
const summaryStatus = ref('idle')
const summaryUnread = ref(false)
const conversationSummary = ref(null)
const showSupportDrawer = ref(false)
const drawerEl = ref(null)
const supportModeHeading = ref(null)
const summaryOrbButton = ref(null)
let releaseDrawerDialog = null
const supportDrawerMode = ref('plan')
const supportDraft = ref({ summary: '', actions: [] })
const supportFeedback = ref('')
const selectedSupportPerson = ref('')
const shareSupportSummary = ref(false)
const currentHelpCard = ref({ person: '', summary: '' })

const hasUserMessage = computed(() => chatMessages.value.some(item => item.role === 'user'))
const showProfessionalNotice = computed(() => (
  !chatUrgentLocked.value
  && screeningState.value?.risk_level === 'professional'
  && !screeningState.value?.acknowledged
))
const summaryOrbLabel = computed(() => {
  if (summaryStatus.value === 'processing') return '正在整理本次倾诉'
  if (summaryStatus.value === 'error') return '倾诉小结整理失败，打开后可以重试'
  return `打开本次倾诉小结，主要情绪${conversationSummary.value?.dominant_emotion || ''}${conversationSummary.value?.intensity || ''}`
})

function focusWithoutScroll(target) {
  target?.focus?.({ preventScroll: true })
}

const CHAT_KEYBOARD_EXCLUDE = 'button, a, input, select, textarea, summary, label, [role="button"], [role="link"], [contenteditable="true"]'

function canAutoFocusChat() {
  return !!window.matchMedia
    && window.matchMedia('(hover: hover) and (pointer: fine)').matches
    && window.matchMedia('(min-width: 768px)').matches
}

function isTextEntryTarget(target) {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  if (target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return true
  if (target.tagName === 'INPUT') {
    return !['checkbox', 'radio', 'button', 'submit', 'reset'].includes(target.type)
  }
  return false
}

// 页面上直接打字时把焦点交给聊天输入框；按钮/链接上的空格仍保留原生激活。
function handleGlobalChatKeydown(event) {
  if (event.defaultPrevented) return
  if (chatUrgentLocked.value || chatLoading.value || showSupportDrawer.value || recording.value) return
  if (event.ctrlKey || event.metaKey || event.altKey) return
  const target = event.target
  if (isTextEntryTarget(target)) return
  if (target instanceof Element && target.closest('[role="dialog"], [aria-modal="true"]')) return
  const editingKey = event.isComposing || event.key === 'Process'
    || event.key === 'Unidentified' || event.key === 'Dead' || event.keyCode === 229
  if (!editingKey && event.key.length !== 1) return
  if (!editingKey && event.key === ' '
    && target instanceof Element && target.closest(CHAT_KEYBOARD_EXCLUDE)) return
  const input = inputEl.value
  if (!input || input.disabled) return
  input.focus({ preventScroll: true })
}

function restoreChatFocusAfterReply() {
  if (!canAutoFocusChat()) return
  if (chatUrgentLocked.value || showSupportDrawer.value || recording.value) return
  const active = document.activeElement
  const passive = !active || active === document.body || active === document.documentElement
    || active.classList?.contains('sc-send')
    || !!active.closest?.('.sc-quick')
  if (passive) focusWithoutScroll(inputEl.value)
}

function getEmotionEmoji(emotion) {
  const map = {
    '愤怒': '😠', '厌恶': '🤢', '恐惧': '😨', '开心': '😊', '中性': '😐', '悲伤': '😢', '惊讶': '😲',
    '平静': '😌', '焦虑': '😟', '难过': '😢', '疲惫': '😴',
    '孤独': '🌙', '委屈': '💧', '害怕': '🫧', '复杂': '🌀', '不确定': '…',
  }
  return map[emotion] || '🙂'
}

function prepareConversation(text) {
  chatInput.value = text
  nextTick(() => inputEl.value?.focus())
}

function onInputEnter(event) {
  // 中文输入法选词时的回车只用于确认候选，不发送消息。
  if (event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  sendChatMsg()
}

function scrollChatBottom() {
  nextTick(() => { if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight })
}

// ─── 快捷按钮横向拖拽 ───
const quickScroll = ref(null)
let isDragging = false
let dragStartX = 0
let dragScrollLeft = 0
function onQuickWheel(e) {
  if (!quickScroll.value) return
  if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
    quickScroll.value.scrollLeft += e.deltaY
    e.preventDefault()
  }
}
function onQuickMouseDown(e) {
  if (!quickScroll.value) return
  isDragging = true
  dragStartX = e.pageX - quickScroll.value.offsetLeft
  dragScrollLeft = quickScroll.value.scrollLeft
  quickScroll.value.style.cursor = 'grabbing'
}
function onQuickMouseMove(e) {
  if (!isDragging || !quickScroll.value) return
  e.preventDefault()
  const x = e.pageX - quickScroll.value.offsetLeft
  quickScroll.value.scrollLeft = dragScrollLeft - (x - dragStartX) * 1.2
}
function onQuickMouseUp() {
  isDragging = false
  if (quickScroll.value) quickScroll.value.style.cursor = 'grab'
}

// ─── 会话与消息 ───
async function sendChatMsg(text) {
  const msg = text || chatInput.value.trim()
  if (!msg || chatLoading.value || chatUrgentLocked.value) return
  chatInput.value = ''
  showEndConfirmation.value = false
  screeningAckDone.value = false
  chatMessages.value.push({ role: 'user', content: msg })
  const userMessageIndex = chatMessages.value.length - 1
  await nextTick()
  scrollChatBottom()
  chatLoading.value = true
  try {
    await userStore.ensureStudentSession(true)
    const session = await startChatSession(false)
    externalAiConsent.value = !!session.data.external_ai_enabled
    companionEngine.value = session.data.companion_engine || null
    voiceInputEnabled.value = !!session.data.voice_input_enabled
    applyChatSessionStatus(session.data?.status)
    chatSessionId.value = session.data.session_id
    const requestKey = globalThis.crypto?.randomUUID?.() || `${Date.now()}_${Math.random().toString(36).slice(2)}`
    let res
    try {
      res = await sendMessage(Number(userStore.userId), msg, 'text', chatSessionId.value, requestKey)
    } catch (err) {
      if (err.response?.status !== 409 || !String(err.response.data?.detail || '').includes('隐私说明已更新')) throw err
      const fresh = await startChatSession(true)
      chatSessionId.value = fresh.data.session_id
      externalAiConsent.value = !!fresh.data.external_ai_enabled
      companionEngine.value = fresh.data.companion_engine || null
      voiceInputEnabled.value = !!fresh.data.voice_input_enabled
      res = await sendMessage(Number(userStore.userId), msg, 'text', chatSessionId.value, requestKey)
    }
    await nextTick()
    if (res.data?.reply) {
      chatMessages.value[userMessageIndex] = {
        ...chatMessages.value[userMessageIndex], emotion: res.data.emotion,
        emotion_intensity: res.data.emotion_intensity, emotion_basis: res.data.emotion_basis,
        analysis_source: res.data.analysis_source,
      }
      chatMessages.value.push({ role: 'assistant', content: res.data.reply })
      chatSessionId.value = res.data.session_id || chatSessionId.value
      completePendingGuide(msg, res.data)
      showEndConfirmation.value = res.data.conversation_signal === 'end_candidate'
      if (res.data?.risk_level === 'professional' && !screeningState.value?.acknowledged) {
        loadScreeningNotice()
      }
      if (res.data.conversation_signal === 'urgent') {
        chatUrgentLocked.value = true
        safetyCurrentSafe.value = false
        safetyContactedAdult.value = false
        nextTick(() => focusWithoutScroll(chatUrgentSupport.value))
      }
    } else {
      chatMessages.value.push({ role: 'assistant', content: '抱歉，我暂时无法回复，请稍后再试...' })
    }
  } catch (err) {
    console.error('发送失败:', err)
    chatMessages.value.push({ role: 'assistant', content: '这次连接没有完成，你刚才的话还在。请再试一次。' })
  }
  chatLoading.value = false
  await nextTick()
  scrollChatBottom()
  restoreChatFocusAfterReply()
}

function requestConversationEnd() {
  if (chatUrgentLocked.value || !hasUserMessage.value || chatLoading.value) return
  showEndConfirmation.value = true
  nextTick(() => scrollChatBottom())
}

function cancelConversationEnd() {
  showEndConfirmation.value = false
  nextTick(() => focusWithoutScroll(inputEl.value))
}

function applyChatSessionStatus(status) {
  chatUrgentLocked.value = status === 'urgent'
  if (!chatUrgentLocked.value) screeningUrgentActive.value = false
  safetyCurrentSafe.value = false
  safetyContactedAdult.value = false
  safetyResolveError.value = ''
  if (!chatUrgentLocked.value) return
  showEndConfirmation.value = false
  nextTick(() => focusWithoutScroll(chatUrgentSupport.value))
}

function handleScreeningUrgent(payload) {
  if (payload?.session_id) chatSessionId.value = payload.session_id
  screeningUrgentActive.value = true
  applyChatSessionStatus('urgent')
}

function handleScreeningUpdated(latest) {
  screeningState.value = latest || null
}

async function loadScreeningNotice() {
  try {
    const res = await getLatestScreening()
    screeningState.value = res.data?.screening || null
  } catch {}
}

async function acknowledgeProfessionalScreening() {
  if (screeningAcking.value || !showProfessionalNotice.value) return
  screeningAcking.value = true
  screeningAckError.value = ''
  try {
    const res = await acknowledgeScreening(true)
    screeningState.value = res.data || null
    screeningAckDone.value = true
    await nextTick()
    focusWithoutScroll(inputEl.value)
  } catch (err) {
    screeningAckError.value = err?.response?.data?.detail || '暂时无法记录，请稍后再试，或先和可信成年人待在一起。'
  } finally {
    screeningAcking.value = false
  }
}

async function resolveUrgentChat() {
  if (!chatSessionId.value || !safetyCurrentSafe.value || !safetyContactedAdult.value || safetyResolving.value) return
  safetyResolving.value = true
  safetyResolveError.value = ''
  try {
    await resolveChatSafety(chatSessionId.value, true, true)
    const session = await startChatSession(true)
    chatSessionId.value = session.data.session_id
    stopTTS()
    chatMessages.value = []
    chatInput.value = ''
    applyChatSessionStatus(session.data?.status)
    await nextTick()
    await screeningCard.value?.refresh()
    await loadScreeningNotice()
    screeningAckDone.value = false
    await nextTick()
    if (showProfessionalNotice.value) focusWithoutScroll(screeningAckButton.value)
    else focusWithoutScroll(inputEl.value)
  } catch (err) {
    safetyResolveError.value = err?.response?.data?.detail || '暂时无法开始新话题，请继续和可信成年人待在一起。'
  } finally {
    safetyResolving.value = false
  }
}

// ─── 结束倾诉与小结 ───
function applySummaryResponse(data, unread = true) {
  if (data?.status !== 'ready' || !data.summary) return false
  summarySessionId.value = data.session_id
  conversationSummary.value = data.summary
  supportDraft.value = {
    summary: data.summary.summary,
    actions: Array.isArray(data.summary.next_steps) ? data.summary.next_steps : [],
  }
  supportFeedback.value = ''
  supportDrawerMode.value = 'plan'
  summaryStatus.value = 'ready'
  summaryUnread.value = unread
  return true
}

async function completeConversation() {
  if (!chatSessionId.value || summaryStatus.value === 'processing') return
  showEndConfirmation.value = false
  showSupportDrawer.value = false
  summaryStatus.value = 'processing'
  summaryUnread.value = false
  try {
    const res = await completeChatSession(chatSessionId.value)
    if (res.data?.status === 'urgent') {
      summaryStatus.value = 'idle'
      chatUrgentLocked.value = true
      safetyCurrentSafe.value = false
      safetyContactedAdult.value = false
      nextTick(() => focusWithoutScroll(chatUrgentSupport.value))
      return
    }
    if (!applySummaryResponse(res.data, true)) throw new Error('invalid summary response')
  } catch (err) {
    console.error('小结生成失败:', err)
    summaryStatus.value = 'error'
  }
}

function openSummaryDrawer() {
  if (summaryStatus.value === 'processing') return
  supportDrawerMode.value = 'plan'
  summaryUnread.value = false
  showSupportDrawer.value = true
}

function closeSupportDrawer() {
  showSupportDrawer.value = false
  supportFeedback.value = ''
  nextTick(() => {
    if (summaryStatus.value !== 'idle' && summaryOrbButton.value) focusWithoutScroll(summaryOrbButton.value)
    else focusWithoutScroll(inputEl.value)
  })
}

watch(showSupportDrawer, async open => {
  if (open) {
    await nextTick()
    releaseDrawerDialog = activateDialog(drawerEl.value, {
      onClose: closeSupportDrawer,
      initialFocus: () => supportModeHeading.value || drawerEl.value,
    })
  } else {
    releaseDrawerDialog?.()
    releaseDrawerDialog = null
  }
})

async function beginFreshConversation() {
  const res = await startChatSession(true)
  chatSessionId.value = res.data.session_id
  applyChatSessionStatus(res.data?.status)
  if (chatUrgentLocked.value) {
    showSupportDrawer.value = false
    return
  }
  stopTTS()
  chatMessages.value = []
  chatInput.value = ''
  showEndConfirmation.value = false
  showSupportDrawer.value = false
  await nextTick()
  focusWithoutScroll(inputEl.value)
}

async function continueAfterSummary() {
  try {
    if (!chatMessages.value.length && summarySessionId.value) {
      const history = await getChatHistory(Number(userStore.userId), summarySessionId.value)
      chatMessages.value = Array.isArray(history.data) ? history.data : []
    }
    const res = await startChatSession(true, summarySessionId.value || null)
    chatSessionId.value = res.data.session_id
    applyChatSessionStatus(res.data?.status)
    if (chatUrgentLocked.value) {
      showSupportDrawer.value = false
      return
    }
    chatInput.value = ''
    showEndConfirmation.value = false
    showSupportDrawer.value = false
    await nextTick()
    scrollChatBottom()
    focusWithoutScroll(inputEl.value)
  } catch {
    showSupportDrawer.value = false
  }
}

async function startNewConversation() {
  try { await beginFreshConversation() } catch { showSupportDrawer.value = false }
}

async function removeConversationSummary() {
  if (!summarySessionId.value || !window.confirm('删除后将无法再次查看这份小结。聊天原文不会因此删除，确认删除吗？')) return
  try {
    await deleteChatSummary(summarySessionId.value)
    showSupportDrawer.value = false
    summaryStatus.value = 'idle'
    summaryUnread.value = false
    conversationSummary.value = null
    summarySessionId.value = ''
    await nextTick()
    focusWithoutScroll(inputEl.value)
  } catch (err) {
    console.error('删除小结失败:', err)
    supportFeedback.value = '暂时无法删除，请稍后再试。'
  }
}

// ─── 求助卡 ───
function confirmHelpRequest() {
  if (!selectedSupportPerson.value) return
  const requestCard = {
    person: selectedSupportPerson.value,
    summary: shareSupportSummary.value ? supportDraft.value.summary : '',
    createdAt: new Date().toISOString(),
    status: 'ready_to_share',
  }
  const key = `shengyu_student_help_cards_${userStore.userId}`
  const previous = readSessionList(key)
  sessionStorage.setItem(key, JSON.stringify([requestCard, ...previous].slice(0, 6)))
  currentHelpCard.value = requestCard
  supportFeedback.value = `求助卡已生成，但不会自动发送。请在安全、方便的时候当面给${selectedSupportPerson.value}看；遇到紧急危险请立即拨打110、120或12356。`
  supportDrawerMode.value = 'card'
}

function readSessionList(key) {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

// ─── 语音输入 ───
let audioContext = null
let audioChunks = []
let mediaStream = null

function toggleVoice() {
  recording.value ? stopRecording() : startRecording()
}

async function startRecording() {
  try {
    const session = await startChatSession(false)
    chatSessionId.value = session.data.session_id
    externalAiConsent.value = !!session.data.external_ai_enabled
    companionEngine.value = session.data.companion_engine || null
    voiceInputEnabled.value = !!session.data.voice_input_enabled
    if (!voiceInputEnabled.value) {
      alert('语音输入需要独立授权，当前请使用文字输入')
      return
    }
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true } })
    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 })
    const source = audioContext.createMediaStreamSource(mediaStream)
    const processor = audioContext.createScriptProcessor(4096, 1, 1)
    audioChunks = []
    processor.onaudioprocess = (e) => {
      const f = e.inputBuffer.getChannelData(0)
      const int16 = new Int16Array(f.length)
      for (let i = 0; i < f.length; i++) { const s = Math.max(-1, Math.min(1, f[i])); int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF }
      audioChunks.push(int16.buffer)
    }
    source.connect(processor); processor.connect(audioContext.destination)
    recording.value = true
  } catch { alert('无法启动录音，请确保浏览器有麦克风权限') }
}

function encodeWav(pcmData, sampleRate = 16000) {
  const buffer = new ArrayBuffer(44 + pcmData.byteLength)
  const view = new DataView(buffer)
  const writeString = (offset, str) => { for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i)) }
  writeString(0, 'RIFF')
  view.setUint32(4, 36 + pcmData.byteLength, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, pcmData.byteLength, true)
  new Uint8Array(buffer, 44).set(new Uint8Array(pcmData))
  return buffer
}

async function stopRecording() {
  recording.value = false
  if (audioContext) { audioContext.close().catch(() => {}); audioContext = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (!audioChunks.length) return
  const totalLength = audioChunks.reduce((a, b) => a + b.byteLength, 0)
  const merged = new Int16Array(totalLength / 2)
  let offset = 0
  for (const chunk of audioChunks) { merged.set(new Int16Array(chunk), offset); offset += chunk.byteLength / 2 }
  const wavBuffer = encodeWav(merged.buffer, 16000)
  audioChunks = []
  chatLoading.value = true
  try {
    const asrUrl = `/api/chat/asr?session_id=${encodeURIComponent(chatSessionId.value || '')}`
    const res = await fetch(asrUrl, { method: 'POST', body: new Blob([wavBuffer], { type: 'audio/wav' }), headers: { 'Content-Type': 'audio/wav' } })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      chatMessages.value.push({ role: 'assistant', content: data?.detail || '语音识别失败，请重试...' })
    } else if (data.text) {
      // 转写成功后先释放 ASR 的 loading，再交给正常发送流程；否则 sendChatMsg 会被自身守卫吞掉。
      chatLoading.value = false
      await sendChatMsg(data.text)
    } else {
      chatMessages.value.push({ role: 'assistant', content: '没有听清，请再说一次~' })
    }
  } catch {
    chatMessages.value.push({ role: 'assistant', content: '语音识别失败，请重试...' })
  } finally {
    chatLoading.value = false
    await nextTick()
    scrollChatBottom()
  }
}

let ttsAudio = null
let ttsObjectUrl = ''
let ttsRequestId = 0

function releaseTTS() {
  if (ttsAudio) {
    ttsAudio.onended = null
    ttsAudio.pause()
    ttsAudio.src = ''
    ttsAudio = null
  }
  if (ttsObjectUrl) {
    URL.revokeObjectURL(ttsObjectUrl)
    ttsObjectUrl = ''
  }
  ttsPlaying.value = -1
}

function stopTTS() {
  ttsRequestId += 1
  releaseTTS()
}

async function toggleTTS(text, index) {
  if (!text) return
  if (ttsPlaying.value === index) {
    stopTTS()
    return
  }
  const requestId = ++ttsRequestId
  releaseTTS()
  ttsPlaying.value = index
  try {
    const session = await startChatSession(false)
    if (requestId !== ttsRequestId) return
    chatSessionId.value = session.data.session_id
    externalAiConsent.value = !!session.data.external_ai_enabled
    companionEngine.value = session.data.companion_engine || null
    voiceInputEnabled.value = !!session.data.voice_input_enabled
    if (!externalAiConsent.value) {
      releaseTTS()
      alert('教师端尚未启用语音模型协作')
      return
    }
    const res = await fetch('/api/chat/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, session_id: chatSessionId.value || null }),
    })
    if (requestId !== ttsRequestId) return
    if (!res.ok) throw new Error('tts request failed')
    const blob = await res.blob()
    if (requestId !== ttsRequestId) return
    ttsObjectUrl = URL.createObjectURL(blob)
    const audio = new Audio(ttsObjectUrl)
    ttsAudio = audio
    audio.onended = () => { if (requestId === ttsRequestId) releaseTTS() }
    try {
      await audio.play()
    } catch {
      if (requestId === ttsRequestId) {
        releaseTTS()
        alert('语音播放失败')
      }
    }
  } catch {
    if (requestId !== ttsRequestId) return
    releaseTTS()
    alert('语音合成失败')
  }
}

async function loadLatestConversationSummary() {
  try {
    const res = await getLatestChatSummary()
    applySummaryResponse(res.data, false)
  } catch {}
}

onMounted(async () => {
  window.addEventListener('keydown', handleGlobalChatKeydown)
  guidePending.value = safeSessionGet('gy_guide_pending_chat') === '1'
  try {
    await userStore.ensureStudentSession()
    const session = await startChatSession(false)
    chatSessionId.value = session.data.session_id
    externalAiConsent.value = !!session.data.external_ai_enabled
    companionEngine.value = session.data.companion_engine || null
    voiceInputEnabled.value = !!session.data.voice_input_enabled
    applyChatSessionStatus(session.data?.status)
    const res = await getChatHistory(Number(userStore.userId), chatSessionId.value)
    chatMessages.value = Array.isArray(res.data) ? res.data : []
  } catch {}
  await loadScreeningNotice()
  if (route.query.handoff === 'failed') {
    applyChatSessionStatus('urgent')
    safetyResolveError.value = '安全交接暂时未连接，请继续和可信成年人待在一起，并优先拨打 12356；危险迫近时拨打 110 或 120。'
  }
  await loadLatestConversationSummary()
  await nextTick()
  if (chatMessages.value.length) scrollChatBottom()
  else if (msgBox.value) msgBox.value.scrollTop = 0
  if (!chatUrgentLocked.value && canAutoFocusChat()) focusWithoutScroll(inputEl.value)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalChatKeydown)
  if (audioContext) { audioContext.close().catch(() => {}); audioContext = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  recording.value = false
  stopTTS()
  releaseDrawerDialog?.()
  releaseDrawerDialog = null
})
</script>

<style scoped>
.sc-page {
  position: relative;
  height: calc(100dvh - 70px);
  width: 100%;
  display: flex;
  flex-direction: column;
  background: var(--m-bg);
  color: var(--m-ink);
}
@media (min-width: 768px) {
  /* 桌面端底栏改为悬浮 dock，给输入栏留出 8px 间隙 */
  .sc-page { height: calc(100dvh - 78px); }
}

/* 流光氛围：两团柔光缓慢漂移（z0，内容层升到 z1 之上） */
.sc-page::before,
.sc-page::after {
  content: '';
  position: fixed;
  inset: -10%;
  z-index: 0;
  pointer-events: none;
}
.sc-page::before {
  background: radial-gradient(38vmax 38vmax at 14% 12%, var(--m-glow-mint), transparent 68%);
  animation: m-drift-a var(--m-drift-dur) ease-in-out infinite;
}
.sc-page::after {
  background: radial-gradient(34vmax 34vmax at 86% 88%, var(--m-glow-gold), transparent 70%);
  animation: m-drift-b var(--m-drift-dur) ease-in-out infinite;
  animation-delay: -13s;
}
.sc-head,
.sc-msgs,
.sc-consentbar,
.sc-quickwrap,
.sc-inputbar,
.sc-urgent,
.sc-endconfirm {
  position: relative;
  z-index: 1;
}
.sc-rechint { z-index: 2; }
.sc-orb { z-index: 3; }

/* ─── 顶栏 ─── */
.sc-head {
  background: var(--m-surface);
  border-bottom: 1px solid var(--m-line);
}
.sc-head-inner {
  width: min(760px, 100%);
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
}
.sc-back {
  width: 34px;
  height: 34px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: var(--m-ink-2);
  text-decoration: none;
  transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease);
}
.sc-back:hover { background: var(--m-bg); }
.sc-back:active { transform: scale(.92); }
.sc-logo { width: 36px; height: 36px; border-radius: 10px; object-fit: cover; flex: none; }
.sc-head-copy { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.sc-head-copy strong { font-size: 15px; }
.sc-head-copy small { font-size: 12px; color: var(--m-ink-3); display: inline-flex; align-items: center; }
.sc-dot { width: 7px; height: 7px; border-radius: 50%; background: #6DB58B; margin-right: 5px; display: inline-block; }
.sc-dot.thinking { background: var(--warning); animation: sc-pulse 1.2s ease-in-out infinite; }
@keyframes sc-pulse { 0%, 100% { opacity: .4; } 50% { opacity: 1; } }
.sc-end {
  flex: none;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid var(--m-line);
  background: var(--m-surface);
  color: var(--m-ink-2);
  font-size: 12.5px;
  white-space: nowrap;
  transition: border-color var(--m-dur-fast) var(--m-ease),
              color var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.sc-end:hover { border-color: var(--m-accent); color: var(--m-accent-strong); }
.sc-end:not(:disabled):active { transform: scale(.96); }
.sc-end:disabled { opacity: .45; cursor: not-allowed; }

/* ─── 消息区 ─── */
.sc-msgs {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.sc-msgs-inner {
  width: min(760px, 100%);
  margin: 0 auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px 6px;
}
.sc-msgs-inner.is-empty { justify-content: safe center; }

.sc-welcome { display: flex; gap: 10px; align-items: flex-start; animation: m-rise var(--m-enter-dur) var(--m-ease) backwards; }
.sc-welcome-avatar { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; flex: none; }
.sc-welcome-bubble {
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  border-radius: 4px 16px 16px 16px;
  padding: 11px 13px;
  font-size: 13.5px;
  line-height: 1.7;
}
.sc-welcome-bubble small { display: block; margin-top: 3px; font-size: 12px; color: var(--m-ink-2); }
.sc-welcome-bubble p + p { margin-top: 8px; }

.sc-starters { display: flex; flex-wrap: wrap; gap: 8px; animation: m-rise var(--m-enter-dur) var(--m-ease) 60ms backwards; }
.sc-starters button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  border-radius: var(--m-radius-md);
  border: 1px solid var(--m-line);
  background: var(--m-surface);
  transition: border-color var(--m-dur-fast) var(--m-ease),
              background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.sc-starters button:hover { border-color: var(--m-accent); background: var(--m-accent-soft); transform: translateY(-1px); }
.sc-starters button:active { transform: scale(.99); }
.sc-starters button strong { font-size: 13px; color: var(--m-ink); }
.sc-starters button span { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

.sc-consentbar {
  width: min(760px, 100%);
  margin: 0 auto;
  padding: 2px 14px 0;
}
.sc-consent {
  font-size: 11px;
  line-height: 1.7;
  color: var(--m-ink-2);
  background: var(--m-accent-soft);
  border-radius: var(--m-radius-md);
  padding: 6px 10px;
}
.sc-consent strong { display: block; font-size: 11px; color: var(--m-accent-strong); }
.sc-consent small { display: block; margin-top: 4px; }
.sc-consent-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 0;
  background: transparent;
  font: inherit;
  color: inherit;
  text-align: left;
}
.sc-consent-toggle strong { flex: 1; margin: 0; }
.sc-consent-toggle span { flex: none; font-size: 11px; font-weight: 600; color: var(--m-accent-strong); }
.sc-consent-toggle svg { flex: none; color: var(--m-ink-2); transition: transform var(--m-dur-fast) var(--m-ease); }
.sc-consent-toggle svg.open { transform: rotate(180deg); }

.sc-row { display: flex; gap: 8px; align-items: flex-end; animation: m-rise-sm var(--m-dur-slow) var(--m-ease) backwards; }
.sc-row.user { justify-content: flex-end; }
.sc-msg-avatar { width: 30px; height: 30px; border-radius: 50%; object-fit: cover; flex: none; }
.sc-bwrap { display: flex; flex-direction: column; gap: 4px; max-width: 78%; }
.sc-row.user .sc-bwrap { align-items: flex-end; }
.sc-bubble {
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  color: var(--m-ink);
}
.sc-row.assistant .sc-bubble { border-radius: 4px 16px 16px 16px; }
.sc-row.user .sc-bubble { background: var(--m-accent); border-color: transparent; color: #fff; border-radius: 16px 16px 4px 16px; }
.sc-etag {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  font-size: 11px;
  color: var(--m-accent-strong);
  background: var(--m-accent-soft);
  padding: 3px 9px;
  border-radius: 999px;
  animation: m-pop var(--m-dur-slow) var(--m-ease) backwards;
}
.sc-tts {
  align-self: flex-start;
  display: inline-flex;
  padding: 2px 4px;
  background: transparent;
  color: var(--m-ink-3);
}
.sc-tts.playing { color: var(--m-accent); }

.sc-typing { display: inline-flex; gap: 5px; align-items: center; padding: 14px 16px; }
.sc-tdot { width: 6px; height: 6px; border-radius: 50%; background: var(--m-ink-3); animation: sc-blink 1.2s infinite; }
.sc-tdot:nth-child(2) { animation-delay: .2s; }
.sc-tdot:nth-child(3) { animation-delay: .4s; }
@keyframes sc-blink { 0%, 80%, 100% { opacity: .25; } 40% { opacity: 1; } }

/* ─── 危机锁 ─── */
.sc-urgent {
  width: calc(100% - 32px);
  max-width: 728px;
  margin: 0 auto 10px;
  padding: 14px 16px;
  border-radius: var(--m-radius-md);
  background: #FDEEEA;
  border: 1px solid #EFC9C0;
  color: #7A3A32;
  display: grid;
  gap: 9px;
  font-size: 13px;
  line-height: 1.7;
  animation: m-rise-sm 360ms var(--m-ease) backwards;
}
.sc-urgent strong { font-size: 14.5px; }
.sc-calls { display: flex; gap: 8px; flex-wrap: wrap; }
.sc-calls a {
  padding: 9px 14px;
  border-radius: 999px;
  background: var(--m-danger);
  color: #fff;
  font-weight: 600;
  font-size: 13px;
  text-decoration: none;
  transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease);
}
.sc-calls a:hover { background: #A95851; }
.sc-calls a:active { transform: scale(.96); }
.sc-urgent label { display: flex; gap: 8px; align-items: flex-start; font-size: 12.5px; }
.sc-resolve {
  width: 100%;
  padding: 11px 0;
  border-radius: var(--m-radius-md);
  background: var(--m-danger);
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease);
}
.sc-resolve:not(:disabled):active { transform: scale(.97); }
.sc-resolve:disabled { opacity: .5; cursor: not-allowed; }
.sc-safety-error { font-size: 12px; color: #B4534A; }

/* ─── 结束确认 ─── */
.sc-endconfirm {
  width: calc(100% - 32px);
  max-width: 728px;
  margin: 0 auto 10px;
  padding: 12px 14px;
  border-radius: var(--m-radius-md);
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  display: grid;
  gap: 10px;
  animation: m-rise-sm 360ms var(--m-ease) backwards;
}
.sc-endconfirm strong { display: block; font-size: 14px; }
.sc-endconfirm span { display: block; font-size: 12.5px; color: var(--m-ink-2); margin-top: 2px; }
.sc-endconfirm-actions { display: flex; gap: 8px; justify-content: flex-end; }
.sc-endconfirm-actions button {
  padding: 9px 14px;
  border-radius: var(--m-radius-md);
  background: var(--m-bg);
  color: var(--m-ink-2);
  font-size: 13px;
  transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease);
}
.sc-endconfirm-actions button:active { transform: scale(.97); }
.sc-endconfirm-actions .sc-endconfirm-primary { background: var(--m-accent); color: #fff; font-weight: 600; }

/* ─── 快捷 chips / 输入 ─── */
.sc-quickwrap { padding: 6px 12px 4px; }
.sc-quick {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  padding-right: 28px;
  scrollbar-width: none;
  cursor: grab;
  mask-image: linear-gradient(to right, #000 calc(100% - 36px), transparent 100%);
  -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 36px), transparent 100%);
}
.sc-quick::-webkit-scrollbar { display: none; }
.sc-chip {
  flex: none;
  padding: 8px 14px;
  border-radius: 999px;
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  color: var(--m-ink-2);
  font-size: 13px;
  white-space: nowrap;
  transition: border-color var(--m-dur-fast) var(--m-ease),
              color var(--m-dur-fast) var(--m-ease),
              background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.sc-chip:hover { border-color: var(--m-accent); color: var(--m-accent-strong); background: var(--m-accent-soft); }
.sc-chip:active { transform: scale(.96); }

.sc-inputbar {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 12px calc(10px + env(safe-area-inset-bottom));
}
.sc-voice {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: 50%;
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  color: var(--m-ink-2);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--m-dur-fast) var(--m-ease),
              background var(--m-dur-fast) var(--m-ease),
              color var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.sc-voice.recording { background: var(--m-accent-soft); color: var(--m-accent-strong); }
.sc-voice:not(:disabled):hover { border-color: var(--m-accent); }
.sc-voice:not(:disabled):active { transform: scale(.94); }
.sc-voice:disabled { opacity: .45; cursor: not-allowed; }
.sc-rec-wave { width: 14px; height: 14px; border-radius: 4px; background: var(--m-danger); animation: sc-pulse 1s ease-in-out infinite; }
.sc-iinput {
  flex: 1;
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  border-radius: 999px;
  padding: 0 16px;
  transition: border-color var(--m-dur-fast) var(--m-ease), box-shadow var(--m-dur-fast) var(--m-ease);
}
.sc-iinput:focus-within { border-color: var(--m-accent); box-shadow: 0 0 0 3px var(--m-ring); }
.sc-iinput input {
  width: 100%;
  padding: 11px 0;
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  font-size: 14.5px;
  color: var(--m-ink);
}
.sc-send {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: 50%;
  background: var(--m-accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease),
              box-shadow var(--m-dur-fast) var(--m-ease);
}
.sc-send:not(:disabled):hover { background: var(--m-accent-strong); transform: translateY(-1px); box-shadow: 0 6px 16px rgba(91, 140, 126, .35); }
.sc-send:not(:disabled):active { transform: translateY(0) scale(.93); }
.sc-send:disabled { opacity: .45; cursor: not-allowed; }

.sc-rechint {
  position: absolute;
  bottom: 92px;
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(34, 48, 43, .86);
  color: #fff;
  font-size: 12px;
}
.sc-rec-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--m-danger); animation: sc-pulse 1s ease-in-out infinite; }

/* ─── 小结 orb ─── */
.sc-orb {
  position: absolute;
  right: 14px;
  bottom: 90px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px 8px 8px;
  border-radius: 999px;
  background: var(--m-surface);
  border: 1px solid var(--m-line);
  box-shadow: var(--m-shadow);
  animation: m-rise-sm var(--m-dur-slow) var(--m-ease) backwards;
  transition: transform var(--m-dur-fast) var(--m-ease), box-shadow var(--m-dur-fast) var(--m-ease);
}
.sc-orb:not(:disabled):hover { transform: translateY(-2px); box-shadow: var(--m-shadow-hover); }
.sc-orb:not(:disabled):active { transform: translateY(0) scale(.97); }
.sc-orb:disabled { cursor: wait; }
.sc-orb-pixel img { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; display: block; }
.sc-orb-copy { display: flex; flex-direction: column; align-items: flex-start; gap: 1px; }
.sc-orb-copy strong { font-size: 12.5px; color: var(--m-ink); }
.sc-orb-copy small { font-size: 11px; color: var(--m-ink-3); }
.sc-orb.is-error .sc-orb-copy strong { color: var(--m-danger); }
.sc-orb-dot {
  position: absolute;
  top: 6px;
  right: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--m-accent);
}
.sc-live { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

/* ─── 小结 / 求助卡抽屉 ─── */
.sc-drawer-mask {
  position: fixed;
  inset: 0;
  z-index: 240;
  background: rgba(28, 38, 34, .38);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
@media (min-width: 640px) {
  .sc-drawer-mask { align-items: center; justify-content: flex-end; padding: 24px; }
}
.sc-drawer {
  position: relative;
  width: 100%;
  max-width: 460px;
  max-height: 86dvh;
  overflow: auto;
  background: var(--m-surface);
  border-radius: var(--m-radius-lg) var(--m-radius-lg) 0 0;
  padding: 20px 18px calc(20px + env(safe-area-inset-bottom));
}
@media (min-width: 640px) {
  .sc-drawer { border-radius: var(--m-radius-lg); padding-bottom: 20px; max-height: calc(100dvh - 48px); }
}
.sc-drawer-close {
  position: absolute;
  top: 12px;
  right: 14px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--m-bg);
  color: var(--m-ink-2);
  font-size: 18px;
  line-height: 1;
  transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease);
}
.sc-drawer-close:hover { background: var(--m-line); }
.sc-drawer-close:active { transform: scale(.92); }
.sc-eyebrow { margin: 0; font-size: 12px; color: var(--m-ink-3); letter-spacing: 1px; }
.sc-drawer h2 { margin: 4px 0 14px; font-size: 18px; color: var(--m-ink); }

.sc-emo-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: var(--m-radius-md);
  background: var(--m-bg);
}
.sc-emo-icon { font-size: 26px; }
.sc-emo-state small { display: block; font-size: 11.5px; color: var(--m-ink-3); }
.sc-emo-state strong { font-size: 14px; color: var(--m-ink); }

.sc-summary { margin: 12px 0 16px; font-size: 14px; line-height: 1.8; color: var(--m-ink); }
.sc-section { margin: 0 0 16px; }
.sc-section h3 { margin: 0 0 8px; font-size: 13.5px; color: var(--m-accent-strong); }
.sc-section ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; }
.sc-section li { font-size: 13px; line-height: 1.7; color: var(--m-ink-2); }
.sc-next li.primary { color: var(--m-ink); font-weight: 600; }
.sc-feedback { display: block; margin-top: 8px; font-size: 12px; color: var(--m-accent-strong); }

.sc-need {
  display: grid;
  gap: 3px;
  padding: 12px 14px;
  border-radius: var(--m-radius-md);
  background: var(--m-accent-soft);
  margin-bottom: 16px;
}
.sc-need span { font-size: 12px; color: var(--m-ink-2); }
.sc-need strong { font-size: 14.5px; color: var(--m-accent-strong); }

.sc-pro {
  padding: 12px 14px;
  border-radius: var(--m-radius-md);
  background: #FDEEEA;
  border: 1px solid #EFC9C0;
  color: #7A3A32;
  margin-bottom: 16px;
}
.sc-pro strong { font-size: 13.5px; }
.sc-pro p { margin: 6px 0 0; font-size: 12.5px; line-height: 1.7; }

.sc-boundary { margin: 0 0 14px; font-size: 11.5px; line-height: 1.7; color: var(--m-ink-3); }
.sc-drawer-controls { display: flex; gap: 10px; margin-bottom: 10px; }
.sc-drawer-controls button {
  flex: 1;
  padding: 11px 0;
  border-radius: var(--m-radius-md);
  background: var(--m-bg);
  color: var(--m-ink-2);
  font-size: 14px;
  transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease);
}
.sc-drawer-controls button:not(:disabled):active { transform: scale(.97); }
.sc-drawer-controls .sc-primary { background: var(--m-accent); color: #fff; font-weight: 600; }
.sc-primary:disabled { opacity: .45; cursor: not-allowed; }
.sc-submit { width: 100%; padding: 12px 0; border-radius: var(--m-radius-md); color: #fff; font-size: 14.5px; font-weight: 600; margin-bottom: 10px; transition: background var(--m-dur-fast) var(--m-ease), transform var(--m-dur-fast) var(--m-ease); }
.sc-submit:not(:disabled):active { transform: scale(.97); }
.sc-submit.sc-primary { background: var(--m-accent); }
.sc-help-link {
  display: block;
  width: 100%;
  padding: 10px 0;
  background: transparent;
  color: var(--m-accent-strong);
  font-size: 13.5px;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.sc-del-link {
  display: block;
  width: 100%;
  padding: 6px 0 0;
  background: transparent;
  color: var(--m-ink-3);
  font-size: 12px;
}

.sc-person-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-bottom: 12px; }
@media (min-width: 420px) { .sc-person-grid { grid-template-columns: 1fr 1fr; } }
.sc-person-grid button {
  padding: 11px 8px;
  border-radius: var(--m-radius-md);
  border: 1.5px solid var(--m-line);
  background: var(--m-surface);
  color: var(--m-ink-2);
  font-size: 13.5px;
  transition: border-color var(--m-dur-fast) var(--m-ease),
              background var(--m-dur-fast) var(--m-ease),
              transform var(--m-dur-fast) var(--m-ease);
}
.sc-person-grid button:not(.active):hover { border-color: var(--m-accent); }
.sc-person-grid button:active { transform: scale(.98); }
.sc-person-grid button.active { border-color: var(--m-accent); background: var(--m-accent-soft); color: var(--m-accent-strong); font-weight: 600; }
.sc-share-toggle { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--m-ink-2); margin-bottom: 10px; }
.sc-send-boundary { font-size: 12px; line-height: 1.7; color: var(--m-ink-3); margin: 0 0 14px; }

.sc-card-preview {
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: var(--m-radius-md);
  border: 1.5px dashed var(--m-accent);
  background: var(--m-accent-soft);
  margin-bottom: 14px;
}
.sc-card-preview span { font-size: 12px; color: var(--m-ink-2); }
.sc-card-preview p { margin: 0; font-size: 14px; line-height: 1.8; color: var(--m-ink); }
.sc-card-preview strong { font-size: 13.5px; color: var(--m-accent-strong); }

.sc-fade-enter-active, .sc-fade-leave-active { transition: opacity 240ms ease; }
.sc-fade-enter-from, .sc-fade-leave-to { opacity: 0; }
.sc-fade-enter-active .sc-drawer { animation: m-panel-rise 240ms var(--m-ease) backwards; }

/* ─── 电脑端：顶栏通栏 + 内容 760 居中，小结 orb 贴内容列右缘 ─── */
@media (min-width: 768px) {
  .sc-quickwrap { width: min(760px, 100%); margin: 0 auto; }
  .sc-inputbar { width: min(760px, 100%); margin: 0 auto; }
  .sc-orb { right: calc((100% - 760px) / 2 + 14px); }
}

/* ─── 游戏化皮肤：场景由 GameBackdrop 承担，聊天浮在房间世界里 ─── */
.sc-page {
  background: transparent;
  color: var(--game-ink);
}
.sc-page::before,
.sc-page::after { display: none; }

.sc-pet {
  width: 36px;
  height: 36px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid var(--game-line);
  background: var(--game-gold-soft);
  overflow: hidden;
  transition: transform var(--m-dur-fast) var(--m-ease), background var(--m-dur-fast) var(--m-ease);
}
.sc-pet img { width: 32px; height: 32px; object-fit: contain; }
.sc-pet:hover { transform: translateY(-1px) scale(1.03); background: var(--game-surface); }
.sc-pet:active { transform: scale(.94); }

.sc-head { background: var(--game-surface); border-bottom-color: var(--game-line); }
.sc-head-copy strong { color: var(--game-ink); }
.sc-head-copy small { color: var(--game-ink-3); }
.sc-back { color: var(--game-ink-2); }
.sc-back:hover { background: var(--game-surface-soft); }
.sc-end { background: var(--game-surface-soft); border-color: var(--game-line); color: var(--game-ink-2); }
.sc-end:hover { border-color: var(--game-accent); color: var(--game-ink); }

.sc-welcome-bubble,
.sc-starters button,
.sc-bubble,
.sc-endconfirm {
  background: var(--game-surface);
  border-color: var(--game-line);
  color: var(--game-ink);
  box-shadow: var(--game-shadow-soft);
}
.sc-starters button strong { color: var(--game-ink); }
.sc-starters button span { color: var(--game-ink-2); }
.sc-starters button:hover { background: var(--game-accent-soft); border-color: var(--game-accent); }
.sc-consent { background: var(--game-accent-soft); color: var(--game-ink-2); }
.sc-consent strong { color: var(--game-wood); }
.sc-row.user .sc-bubble {
  background: var(--game-accent);
  border-color: transparent;
  color: var(--game-on-accent);
  box-shadow: 0 6px 16px rgba(40, 30, 20, .16);
}
.sc-etag { background: var(--game-gold-soft); color: var(--game-wood); }

.sc-chip {
  background: var(--game-surface);
  border-color: var(--game-line);
  color: var(--game-ink-2);
}
.sc-chip:hover {
  background: var(--game-accent-soft);
  border-color: var(--game-accent);
  color: var(--game-ink);
}
.sc-voice,
.sc-iinput {
  background: var(--game-surface);
  border-color: var(--game-line);
}
.sc-voice { color: var(--game-ink-2); }
.sc-voice.recording { background: var(--game-gold-soft); color: var(--game-wood); }
.sc-iinput input { color: var(--game-ink); }
.sc-iinput input::placeholder { color: var(--game-ink-3); }
.sc-iinput:focus-within { border-color: var(--game-accent); box-shadow: 0 0 0 3px var(--game-accent-soft); }
.sc-send { background: var(--game-accent); color: var(--game-on-accent); }
.sc-send:not(:disabled):hover { background: var(--game-accent); filter: brightness(1.08); }
.sc-endconfirm-actions button { background: var(--game-surface-soft); color: var(--game-ink-2); }
.sc-endconfirm-actions .sc-endconfirm-primary { background: var(--game-accent); color: var(--game-on-accent); }

.sc-guide-notice {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  padding: 11px 14px;
  border-radius: 14px;
  border: 1px solid var(--game-line);
  background: var(--game-gold-soft);
  color: var(--game-ink-2);
  font-size: 12.5px;
  line-height: 1.6;
  animation: m-rise var(--m-enter-dur) var(--m-ease) backwards;
}
.sc-guide-notice a {
  color: var(--game-wood);
  font-weight: 600;
  text-decoration: none;
  border-bottom: 1px dashed currentColor;
}

/* 夜晚 / 傍晚的危机卡保持高对比，不做深色化处理。 */

/* 像素皮肤 3.0 · 倾诉页 */
.sc-head { border-bottom: 2px solid var(--px-line); }
.sc-back,
.sc-end,
.sc-pet {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  background: var(--game-surface-soft);
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end),
              background 160ms steps(2, end), border-color 160ms steps(2, end);
}
.sc-back:hover,
.sc-end:hover,
.sc-pet:hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); }
.sc-back:active,
.sc-end:active,
.sc-pet:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.sc-head-copy strong { font-family: var(--px-font); font-size: 16px; letter-spacing: .02em; }
.sc-welcome-bubble,
.sc-bubble,
.sc-endconfirm,
.sc-consent,
.sc-guide-notice {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: none;
}
.sc-consent { padding: 6px 10px; }
.sc-msg-avatar,
.sc-welcome-avatar {
  width: 34px;
  height: 34px;
  padding: 1px;
  border: 2px solid var(--px-line);
  border-radius: 4px;
  background: var(--game-gold-soft);
  object-fit: contain;
  image-rendering: pixelated;
}
.sc-orb {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
}
.sc-orb:not(:disabled):hover { box-shadow: 4px 4px 0 var(--px-shadow); }
.sc-orb-pixel img {
  width: 36px;
  height: 36px;
  padding: 1px;
  border: 2px solid var(--px-line);
  border-radius: 4px;
  background: var(--game-gold-soft);
  object-fit: contain;
  image-rendering: pixelated;
}
.sc-orb-copy strong { font-family: var(--px-font); font-size: 13px; }
.sc-row.assistant .sc-bubble,
.sc-row.user .sc-bubble { border-radius: 4px; }
.sc-row.user .sc-bubble { border-color: var(--px-line); box-shadow: none; }
.sc-starters button {
  border: 2px solid var(--px-line);
  border-radius: 4px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end),
              background 160ms steps(2, end), border-color 160ms steps(2, end);
}
.sc-starters button:hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); }
.sc-starters button:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.sc-starters button strong { font-family: var(--px-font); font-size: 14px; letter-spacing: .01em; }
.sc-chip { border-width: 2px; border-radius: 4px; }
.sc-iinput,
.sc-voice {
  border-width: 2px;
  border-radius: 4px;
}
.sc-send {
  border: 2px solid var(--px-gold);
  border-radius: 4px;
  background: var(--px-gold);
  color: var(--game-on-accent);
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end), filter 160ms steps(2, end);
}
.sc-send:not(:disabled):hover { background: var(--px-gold); transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); filter: none; }
.sc-send:not(:disabled):active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.sc-endconfirm-actions button { border: 2px solid var(--px-line); border-radius: 4px; }
.sc-drawer {
  border: 2px solid var(--px-line);
  box-shadow: -4px 4px 0 var(--px-shadow);
}
.sc-drawer-close { border-radius: 4px; }
.sc-person-grid button { border-width: 2px; border-radius: 4px; }
.sc-screening-ack {
  width: calc(100% - 32px);
  max-width: 728px;
  margin: 0 auto 10px;
  padding: 12px 14px;
  display: grid;
  gap: 8px;
  border: 2px solid var(--px-line);
  border-radius: 6px;
  background: var(--m-surface);
  color: var(--m-ink);
  box-shadow: 4px 4px 0 var(--px-shadow);
}
.sc-screening-ack-copy { display: grid; gap: 4px; }
.sc-screening-ack strong { font-family: var(--px-font); font-size: 14px; }
.sc-screening-ack p { font-size: 12.5px; line-height: 1.65; color: var(--m-ink-2); }
.sc-screening-ack small { font-size: 11px; line-height: 1.6; color: var(--m-ink-3); }
.sc-screening-ack button {
  justify-self: start;
  max-width: 100%;
  padding: 9px 14px;
  border: 2px solid var(--px-gold);
  border-radius: 4px;
  background: var(--px-gold);
  color: var(--game-on-accent);
  font-family: var(--px-font);
  font-size: 12.5px;
  box-shadow: 3px 3px 0 var(--px-shadow);
  transition: transform 160ms steps(2, end), box-shadow 160ms steps(2, end);
}
.sc-screening-ack button:not(:disabled):hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 var(--px-shadow); }
.sc-screening-ack button:not(:disabled):active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--px-shadow); }
.sc-screening-ack button:disabled { opacity: .55; cursor: not-allowed; }
.sc-screening-ack .sc-screening-ack-error { color: #B4534A; }
.sc-screening-ackdone {
  width: calc(100% - 32px);
  max-width: 728px;
  margin: 0 auto 10px;
  padding: 8px 12px;
  border: 2px solid var(--px-line);
  border-radius: 4px;
  background: var(--m-surface);
  color: var(--m-ink-2);
  font-size: 12px;
  line-height: 1.6;
}
.sc-resolve-hint { font-size: 12px; color: #8A4A42; }
.sc-back:focus-visible,
.sc-end:focus-visible,
.sc-pet:focus-visible,
.sc-starters button:focus-visible,
.sc-chip:focus-visible,
.sc-send:focus-visible,
.sc-voice:focus-visible,
.sc-orb:focus-visible,
.sc-drawer-close:focus-visible,
.sc-endconfirm-actions button:focus-visible,
.sc-screening-ack button:focus-visible,
.sc-drawer-controls button:focus-visible,
.sc-submit:focus-visible,
.sc-person-grid button:focus-visible {
  outline: 3px dashed var(--px-gold);
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
</style>
