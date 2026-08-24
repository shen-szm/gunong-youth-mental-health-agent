<template>
  <div class="treehole-page" :class="{ 'inline-mode': inline }">
    <div class="treehole-header" v-if="!inline">
      <button class="back-btn" @click="router.back()">←</button>
      <h1>💌 虚拟树洞</h1>
    </div>
    <div class="inline-title" v-if="inline">
      <h2>💌 虚拟树洞</h2>
    </div>

    <div class="treehole-intro">
      <p>🌿 这里用于分享去标识化的感受</p>
      <p>请不要填写姓名、学校、联系方式或精确地址</p>
      <!-- 每日一句温暖 -->
      <div class="daily-warmth" v-if="dailyQuote">
        <span class="dw-icon">💡</span>
        <span class="dw-text">{{ dailyQuote }}</span>
      </div>
      <div class="stats" v-if="stats">
        已有 {{ stats.total_posts }} 位朋友倾诉 · {{ stats.total_resonance }} 次共鸣
      </div>
    </div>

    <!-- AI陪伴入口 + 漂流瓶 -->
    <div class="entry-row">
      <div class="companion-entry half" @click="showCompanions = true">
        <div class="ce-left">
          <span class="ce-emoji">🤗</span>
          <div>
            <div class="ce-title">AI 陪伴聊天</div>
            <div class="ce-desc">选一个角色陪你聊</div>
          </div>
        </div>
        <span class="ce-arrow">→</span>
      </div>
      <div class="companion-entry half bottle" @click="openDriftBottle">
        <div class="ce-left">
          <span class="ce-emoji">🫙</span>
          <div>
            <div class="ce-title">心情漂流瓶</div>
            <div class="ce-desc">捞一个陌生人的心情</div>
          </div>
        </div>
        <span class="ce-arrow">→</span>
      </div>
    </div>

    <!-- 漂流瓶弹窗 -->
    <Transition name="fade">
      <div v-if="showDriftBottle" class="companion-modal" @click.self="showDriftBottle = false">
        <div class="companion-panel drift-panel">
          <div class="cp-header">
            <h3>🫙 捞到一个漂流瓶</h3>
            <button class="cp-close" @click="showDriftBottle = false">✕</button>
          </div>
          <div class="drift-content">
            <div class="drift-mood">{{ getMoodEmoji(driftMood) }} {{ driftMood }}</div>
            <p class="drift-text">{{ driftContent }}</p>
            <div class="drift-hint">—— 来自一位陌生人的心情</div>
          </div>
          <button class="drift-again" @click="openDriftBottle">再捞一个</button>
        </div>
      </div>
    </Transition>

    <!-- AI陪伴选择弹窗 -->
    <Transition name="fade">
      <div v-if="showCompanions" class="companion-modal" @click.self="showCompanions = false">
        <div class="companion-panel">
          <div class="cp-header">
            <h3>选择陪伴角色</h3>
            <button class="cp-close" @click="showCompanions = false">✕</button>
          </div>
          <div class="cp-list">
            <div v-for="c in companions" :key="c.id" class="cp-item" @click="startCompanion(c)">
              <div class="cpi-avatar">{{ c.avatar }}</div>
              <div class="cpi-info">
                <div class="cpi-name">{{ c.name }}</div>
                <div class="cpi-desc">{{ c.desc }}</div>
              </div>
              <span class="cpi-go">→</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 陪伴对话界面 -->
    <Transition name="fade">
      <div v-if="companionActive" class="companion-chat">
        <div class="cc-header">
          <button @click="companionActive = false">← 返回树洞</button>
          <span>{{ companionName }}</span>
        </div>
        <div class="cc-messages" ref="chatMessages">
          <div v-for="(msg, i) in companionMsgs" :key="i" class="cc-msg" :class="msg.role">
            <div class="ccm-bubble">{{ msg.content }}</div>
          </div>
          <div v-if="companionTyping" class="cc-msg assistant">
            <div class="ccm-bubble typing">正在输入...</div>
          </div>
        </div>
        <div class="cc-input">
          <input v-model="companionInput" placeholder="说点什么..." @keyup.enter="sendCompanionMsg" />
          <button @click="sendCompanionMsg" :disabled="!companionInput.trim() || companionTyping">发送</button>
        </div>
      </div>
    </Transition>

    <!-- 发布区域 -->
    <div class="post-area" v-if="!companionActive">
      <div class="mood-selector">
        <button v-for="m in moodOptions" :key="m.label" class="mood-btn" :class="{ active: selectedMood === m.label }" @click="selectedMood = m.label">
          {{ m.emoji }} {{ m.label }}
        </button>
      </div>
      <div class="input-row">
        <input v-model="newContent" placeholder="说一说你现在的感受..." @keyup.enter="createPost" />
        <button class="post-btn" @click="createPost" :disabled="!newContent.trim()">发布</button>
      </div>
    </div>

    <!-- 信息流 -->
    <div class="feed" v-if="!companionActive">
      <div v-for="post in posts" :key="post.id" class="treehole-card">
        <div class="thc-mood">{{ getMoodEmoji(post.mood_card) }}</div>
        <div class="thc-body">
          <p class="thc-content">{{ post.content }}</p>
          <div class="thc-footer">
            <span class="thc-time">{{ formatTime(post.created_at) }}</span>
            <div class="thc-actions">
              <button v-if="post.is_local" class="thc-delete" @click="deletePost(post.id)">
                🗑️ 删除
              </button>
              <button class="thc-resonance" @click="addResonance(post.id)">
                🤝 我也一样 ({{ post.resonance_count }})
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="!posts.length" class="empty-hint">还没有人发言，做第一个吧~</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { treeholeApi } from '../api/treehole'
import { sendMessage } from '../api/chat'
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || ''
const router = useRouter()
const userStore = useUserStore()

const props = defineProps({ inline: { type: Boolean, default: false } })
const emit = defineEmits(['close'])

const posts = ref([])
const newContent = ref('')
const selectedMood = ref('')
const stats = ref(null)

// 每日温暖语录
const WARM_QUOTES = [
  '你今天的努力，是幸运的伏笔。',
  '不必着急赶路，偶尔停下来看看天空也很好。',
  '世界很大，你的心事有人愿意听。',
  '今天的你，已经比昨天更勇敢了。',
  '累了就休息，不是放弃，是为了走得更远。',
  '你值得被温柔以待，尤其是被自己。',
  '没有白走的路，每一步都算数。',
  '允许自己不开心，也是爱自己的一种方式。',
  '你比你想象的更强大。',
  '慢慢来，谁还没有一个努力的过程。',
  '星星发亮是为了让每个人找到自己的星星。',
  '今天的不开心就止于此吧，明天依旧光芒万丈。',
]
const dailyQuote = ref('')

// 漂流瓶
const showDriftBottle = ref(false)
const driftContent = ref('')
const driftMood = ref('')

// AI陪伴
const showCompanions = ref(false)
const companions = ref([])
const companionActive = ref(false)
const companionName = ref('')
const companionId = ref('')
const companionMsgs = ref([])
const companionInput = ref('')
const companionTyping = ref(false)
const chatMessages = ref(null)

const moodOptions = [
  { emoji: '😰', label: '蕉绿了' },
  { emoji: '😢', label: 'emo了' },
  { emoji: '😡', label: '蚌埠住了' },
  { emoji: '😴', label: '电量不足' },
  { emoji: '🤔', label: '整个人不好' },
  { emoji: '😌', label: '还好吧' },
  { emoji: '🥳', label: '开心到飞起' },
  { emoji: '✨', label: '被治愈了' },
  { emoji: '💪', label: '支棱起来了' },
]

function getMoodEmoji(label) {
  const m = moodOptions.find(o => o.label === label)
  return m ? m.emoji : '💚'
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return Math.floor(diff / 86400000) + '天前'
}

const TH_STORAGE_KEY = 'shengyu_treehole_posts'
const TH_RESONATED_KEY = 'shengyu_treehole_resonated'

function loadLocalPosts() {
  try {
    const saved = localStorage.getItem(TH_STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch {}
  return []
}
function saveLocalPosts(list) {
  localStorage.setItem(TH_STORAGE_KEY, JSON.stringify(list))
}
function getResonatedSet() {
  try {
    return new Set(JSON.parse(localStorage.getItem(TH_RESONATED_KEY) || '[]'))
  } catch { return new Set() }
}
function addResonatedId(id) {
  const set = getResonatedSet()
  set.add(id)
  localStorage.setItem(TH_RESONATED_KEY, JSON.stringify([...set]))
}

async function createPost() {
  const content = newContent.value.trim()
  if (!content) return
  const mood = selectedMood.value || '还好吧'

  const post = {
    id: Date.now(),
    content,
    mood_card: mood,
    created_at: new Date().toISOString(),
    resonance_count: 0,
    is_local: true,
  }

  // 优先走 API
  try {
    const res = await treeholeApi.createPost(Number(userStore.userId), mood, content)
    newContent.value = ''
    selectedMood.value = ''
    loadFeed()
    if (res.data?.warm_reply) {
      alert('💌 来自树洞的温暖：\n\n' + res.data.warm_reply)
    }
  } catch (e) {
    // API 失败则保存到本地
    const local = loadLocalPosts()
    local.unshift(post)
    saveLocalPosts(local)
    posts.value = local
    newContent.value = ''
    selectedMood.value = ''
  }
}

function deletePost(postId) {
  if (!confirm('确定要删除这条倾诉吗？')) return
  const local = loadLocalPosts()
  const filtered = local.filter(p => p.id !== postId)
  saveLocalPosts(filtered)
  posts.value = posts.value.filter(p => p.id !== postId)
}

async function addResonance(postId) {
  const resonated = getResonatedSet()
  if (resonated.has(postId)) {
    alert('你已经共鸣过这条啦 💚')
    return
  }

  try {
    const res = await treeholeApi.addResonance(postId, Number(userStore.userId))
    if (res.data?.success) {
      const post = posts.value.find(p => p.id === postId)
      if (post) post.resonance_count = res.data.resonance_count
      addResonatedId(postId)
    }
  } catch (e) {
    // 本地模式：直接+1
    const post = posts.value.find(p => p.id === postId)
    if (post) {
      post.resonance_count = (post.resonance_count || 0) + 1
      addResonatedId(postId)
      // 同步保存到 localStorage
      const local = loadLocalPosts()
      const lp = local.find(p => p.id === postId)
      if (lp) lp.resonance_count = post.resonance_count
      saveLocalPosts(local)
    }
  }
}

async function loadFeed() {
  try {
    const res = await treeholeApi.getFeed(Number(userStore.userId))
    const apiPosts = res.data?.posts || []
    // 合并本地和 API 数据（本地优先，因为可能包含离线发布的内容）
    const local = loadLocalPosts()
    const merged = [...local]
    for (const p of apiPosts) {
      if (!merged.find(m => m.id === p.id)) merged.push(p)
    }
    merged.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    posts.value = merged
    saveLocalPosts(merged)
  } catch (e) {
    console.error('加载失败', e)
    posts.value = loadLocalPosts()
  }
}

async function loadStats() {
  try {
    const res = await axios.get(`${API}/api/treehole/stats`)
    stats.value = res.data
  } catch (e) { /* ignore */ }
}

// ═══════ AI 陪伴角色配置 ═══════
const COMPANION_PROFILES = {
  xiaoqing: {
    id: 'xiaoqing',
    avatar: '🌸',
    name: '温柔倾听模式（AI）',
    shortName: '倾听 AI',
    desc: '这是温柔倾听 AI 模式，不是真人或心理医生。它帮助你描述感受、整理当下需要，不提供现实照护或绝对承诺。',
    greeting: '你好，我是温柔倾听 AI 模式，不是真人或心理医生。你可以从此刻最想说的一件事开始；请不要发送姓名、学校、电话等身份信息。',
    replies: {
      default: [
        '慢慢说，AI 倾听模式会帮助你整理。',
        '不管发生什么，你都不是一个人哦。',
        '有时候情绪就像天气，阴天总会过去的。',
        '听起来这并不容易，我们可以先看清当下最需要什么。',
        '来，深呼吸，让心慢慢静下来。',
      ],
      sad: [
        '我注意到你提到了难过。可以说说发生了什么吗？',
        '流泪并不等于软弱。如果愿意，可以用一两个词描述此刻的感受。',
        '每个人的心里都有一片柔软的草地，偶尔被踩痛了也没关系，阳光还是会照进来的。',
        '难过时可以先短暂休息，并考虑联系一位你信任的成年人。',
        '你知道吗？你现在经历的难过，未来都会变成你温柔的力量。',
      ],
      happy: [
        '听到你开心真好。如果愿意，可以把这件小事记下来，留作以后回看。',
        '如果愿意，可以记下这件开心的小事。',
        '听到这件事让你高兴，真好。',
        '可以想想是什么让这一刻变得特别。',
        '真好呀，愿你的每一天都有这样的小确幸。',
      ],
      anxious: [
        '焦虑就像心里住了一只乱飞的小鸟，我们先试着让它慢慢安静下来，好吗？',
        '压力太大时，允许自己停下来短暂休息。',
        '可以先做三次缓慢呼吸；如果不舒服就停止。',
        '你已经在努力了，这本身就值得骄傲。剩下的，交给时间吧。',
        '焦虑的时候，试着把注意力放在当下——你能听到的声音、能闻到的味道。',
      ],
      tired: [
        '累了可以先休息，并留意疲惫是否持续影响生活。',
        '身体在提醒你要爱自己了。今晚早点休息，明天又是新的一天。',
        '偶尔什么都不想做也没关系，躺平也是一种充电方式呢。',
        '你不需要一直表现得坚强，也可以向可信成年人求助。',
        '如果持续睡不好，请告诉可信成年人并考虑专业支持。',
      ],
      love: [
        '如果愿意，可以说说这段关系带给你的感受。',
        '喜欢一个人的感觉，就像春天第一朵花开，既害羞又美好。不管结果如何，这份心意本身就很珍贵。',
        '关系中的感受值得被看见，同时也要留意彼此尊重和边界。',
        '暗恋也好，明恋也罢，这都是青春里最温柔的篇章。',
        '如果喜欢一个人让你变得更好，那他就是对的人。',
      ],
      hello: [
        '你好，今天过得怎么样？',
        '你好，想从哪件事开始说起？',
        '欢迎使用温柔倾听 AI 模式。',
        '你好，可以按自己的节奏表达。',
      ],
    }
  },
  aze: {
    id: 'aze',
    avatar: '☀️',
    name: '行动陪伴模式（AI）',
    shortName: '行动 AI',
    desc: '这是行动陪伴 AI 模式，不是真人或心理医生。它帮助你把困扰拆成低负担的小步骤，不代替现实支持。',
    greeting: '你好，我是行动陪伴 AI 模式，不是真人或心理医生。你可以说说眼前最想处理的一件小事，我们一起拆成一个可执行步骤。',
    replies: {
      default: [
        '我们可以先找一个现在能做的小步骤。',
        '可以先缓慢呼吸，再描述具体情况。',
        '先稳住节奏，不必一次解决所有事情。',
        '可以继续说，AI 会帮你整理重点。',
        '如果事情超出你能独自处理的范围，请联系可信成年人。',
      ],
      sad: [
        '遇到低谷并不少见，但你的具体感受仍值得认真对待。',
        '想哭也可以；等你准备好时，我们再看看下一步。',
        '如果难受持续或加重，请联系可信成年人，不要独自承担。',
        '难受时可以先照顾喝水、进食和休息等基本需要。',
        '可以允许情绪存在，再决定一个很小的下一步。',
      ],
      happy: [
        '这份进展来之不易，可以为自己做一个小小庆祝。',
        '看到你有进展，真好。',
        '可以记录是什么帮助了你，以后或许还能复用。',
        '高兴可以有很多表达方式，选择让你舒服的就好。',
        '这份进展值得被记录下来。',
      ],
      anxious: [
        '可以把担心分成“现在能做的”和“暂时无法控制的”。',
        '压力大时可以选择适量活动，但不必期待一次就解决全部困扰。',
        '别想太多，很多时候事情没你想的那么糟。先把眼前的事做好，其他的交给时间。',
        '焦虑不等于想太多；可以先识别触发它的具体情境。',
        '可以描述最担心的部分，我们再找一个小步骤。',
      ],
      tired: [
        '累了可以先休息，再选择一个低负担的恢复方式。',
        '可以先照顾睡眠、进食和休息等基本需要。',
        '如果最近经常熬夜，可以尝试把睡前时间提前一点。',
        '别硬撑；如果疲惫明显影响生活，请告诉可信成年人。',
        '疲惫不一定代表失败，可以先照顾基本需要。',
      ],
      love: [
        '如果愿意，可以说说这段关系让你困惑的地方。',
        '表达感受前可以先考虑安全、边界和自己能承受的结果。',
        '关系中真诚很重要，彼此同意、尊重和边界也同样重要。',
        '是否表达由你决定，不需要因为 AI 建议而冒险。',
        '健康的关系通常包含相互尊重，也允许双方保留自己的生活。',
      ],
      hello: [
        '嘿！在呢在呢，今天怎么样？',
        '你好，有什么想聊的吗？',
        '欢迎使用行动陪伴 AI 模式。',
        '你好，可以从最想处理的一件事开始。',
      ],
    }
  },
  gunong: {
    id: 'gunong',
    avatar: '🌿',
    name: '咕哝 AI',
    shortName: '咕哝',
    desc: '你是AI情绪支持工具「咕哝」，不是心理医生或真人。你会温和倾听、帮助用户描述感受，并提供低风险的日常调节建议；不诊断、不治疗。',
    greeting: '你好，我是咕哝AI情绪支持工具。你可以在这里整理感受；我不是心理医生，也不能承诺绝对保密。若你可能伤害自己或无法保证安全，请马上联系可信成年人并拨打12356、110或120。今天想从哪件事说起？',
    replies: {
      default: [
        '谢谢你愿意和我分享。能多说一点吗？',
        '我听到了，这对你来说一定不容易。',
        '你的感受是真实的，也是值得被认真对待的。',
        '我想更深入地理解你。你能具体描述一下吗？',
        '无论你想聊什么，我都在这里陪着你。',
      ],
      sad: [
        '我注意到你现在的情绪比较低落。心理学上有一种方法叫"情绪命名"——试着用更具体的词描述你的感受，比如"失落"、"孤独"或"无助"。这能帮助你更好地理解自己。你愿意试试吗？',
        '悲伤是一种信号，它在告诉我们某些需求没有被满足。你能告诉我，最近有什么事情让你感到特别难过吗？',
        '当痛苦来临时，允许自己感受它是一种自我关怀。同时，你也可以尝试"5-4-3-2-1" grounding 技巧：说出周围5样能看到的东西、4样能听到的、3样能触摸到的、2样能闻到的、1样能尝到的。这能帮你回到当下。',
        '如果你愿意，可以用几个词写下此刻的感受；写不出来也没关系。',
        '你现在不需要马上好起来。允许自己慢慢来， healing 是一个过程，不是一个开关。',
      ],
      happy: [
        '很高兴听到你的好消息！积极情绪的记录对心理健康非常有益。你能具体说说是什么让你感到开心吗？这样我们可以一起"储存"这份快乐。',
        '这种正向体验是一个很好的资源。在心理学中，我们称这为"积极情绪存款"。当未来遇到困难时，你可以回想这一刻来给自己力量。',
        '真好！积极情绪不仅能让你当下感到愉悦，还能拓展你的思维视野。趁现在感觉好，要不要考虑做一件你一直想做但还没开始的事？',
        '你现在的快乐状态是一个很好的"锚点"。建议你记录下此刻的感受和原因，未来情绪低落时可以回来看看。',
        '如果感觉合适，你也可以把这件开心的小事分享给信任的人。',
      ],
      anxious: [
        '焦虑通常源于对未来的不确定感。一个有效的应对方法是"担忧时间"（Worry Time）技巧：每天设定15分钟专门用来担忧，其他时间当焦虑出现时，告诉自己"我会留到担忧时间再想"。这能帮助你重获掌控感。',
        '你现在的焦虑是可以理解的。让我们做一个简单的呼吸练习：吸气4秒，屏息4秒，呼气6秒。重复3次。你愿意和我一起试试吗？',
        '当脑中反复出现“我应该做得更好”时，可以试着换成“我希望做好，也允许自己一步一步来”。',
        '可以把担心分成“现在能做的”和“暂时不能控制的”，先选择一个很小、可完成的动作。',
        '焦虑时，我们的身体往往处于"战斗或逃跑"模式。试着把手放在胸口，对自己说："我现在是安全的，我足够好，我值得被善待。"',
      ],
      tired: [
        '长期疲劳可能是身心透支的信号。建议你先做一个简单的"能量审计"：列出过去一周消耗你能量的事情，和给你能量的事情。然后试着减少一件耗能的事，增加一件充能的事。',
        '睡眠问题常常和心理压力有关。你可以试试"渐进式肌肉放松法"：从脚趾开始，先紧绷肌肉5秒，然后放松10秒，逐步向上移动到全身。',
        '疲劳是身体在发出休息的信号。自我关怀不是奢侈品，而是必需品。今晚能不能给自己一个小小的"关机仪式"，比如泡个热水澡或听一段轻音乐？',
        '当你感到"什么都不想做"时，试着把"应该做"换成"选择做"。哪怕只选择做一件极小的事，比如喝一杯水，也是在照顾自己的信号。',
        '身心疲惫时可以短暂休息；如果疲惫持续或明显影响生活，请告诉可信成年人并寻求专业帮助。',
      ],
      love: [
        '感情中的困惑是很常见的。我想请你做一个"价值观澄清"练习：写出你在亲密关系中最看重的3个品质。这能帮助你更清楚地了解自己的需求。',
        '喜欢一个人时的忐忑不安，其实是大脑中的多巴胺系统在运作。这种感受虽然让人焦虑，但也是人类最美好体验的一部分。你现在的感受是什么？',
        '在关系中，尊重彼此边界和保持自己的生活都很重要。你觉得这段关系让你感到安全和被尊重吗？',
        '恋爱中的情绪波动是正常的。试着区分"事实"和"感受"：对方没回消息是事实，"ta不爱我了"是你的解读。事实本身往往没有那么可怕。',
        '无论这段感情的结果如何，你都在学习如何爱与被爱。这种能力会伴随你一生，是最宝贵的心理财富之一。',
      ],
      hello: [
        '你好，我是咕哝。今天你想探讨什么话题？',
        '你好，我是 AI 情绪支持工具。请不要发送可识别身份的信息；如果你无法保证当下安全，请立即联系可信成年人并拨打12356、110或120。',
        '欢迎。能告诉我，是什么让你今天来到这里吗？',
        '你好，感谢你的信任。我们可以从任何你想聊的话题开始。',
      ],
    }
  }
}

// 正能量漂流瓶池
const POSITIVE_BOTTLES = [
  { mood: '开心到飞起', content: '今天帮一位老人过马路，她笑着对我说"好孩子"，那一刻觉得世界真美好。' },
  { mood: '被治愈了', content: '下班路上看到一只橘猫在晒太阳，它眯着眼睛的样子太治愈了，忍不住停下来看了好久。' },
  { mood: '支棱起来了', content: '终于跑完了人生第一个5公里！虽然很累，但冲过终点的那一刻，我觉得自己能征服全世界。' },
  { mood: '还好吧', content: '今天没有什么特别的事发生，但喝到了一杯很香的咖啡，平静也是一种幸福吧。' },
  { mood: '开心到飞起', content: '收到了暗恋对象的消息，虽然只有几个字，但我盯着屏幕笑了整整五分钟。' },
  { mood: '被治愈了', content: '雨后的天空出现了一道彩虹，路边的小朋友指着天空大喊"妈妈你看！"，真好啊。' },
  { mood: '支棱起来了', content: '复习了三周，今天考试终于过了！所有的努力都没有白费，继续加油！' },
  { mood: '还好吧', content: '独自一人在公园的长椅上坐了一下午，看着人来人往，觉得孤独也是一种自由。' },
  { mood: '开心到飞起', content: '第一次做蛋糕，虽然卖相一般，但家人说很好吃，那一刻觉得好幸福。' },
  { mood: '被治愈了', content: '晚上回家的路上，路灯把影子拉得很长，耳机里放着喜欢的歌，突然觉得一切都刚刚好。' },
  { mood: '支棱起来了', content: '今天被老板表扬了！虽然只是一件小事，但那种被认可的感觉真的太棒了！' },
  { mood: '还好吧', content: '读完了搁置很久的一本书，合上书的那一刻，内心出奇地平静。' },
  { mood: '开心到飞起', content: '和好久不见的朋友见了一面，我们聊了很多，好像时间从来没有把我们分开过。' },
  { mood: '被治愈了', content: '今天给自己买了一束花，插在书桌上的瓶子里，整个房间都变得温柔了。' },
  { mood: '支棱起来了', content: '坚持打卡健身第30天！从一开始的气喘吁吁到现在能轻松完成，原来我也可以做到。' },
  { mood: '开心到飞起', content: '路过面包店刚好买到刚出炉的菠萝包，咬一口外酥里嫩，今天的快乐是碳水给的！' },
  { mood: '被治愈了', content: '家里的小狗在我难过的时候把脑袋靠在我腿上，原来它什么都知道。' },
  { mood: '还好吧', content: '周末睡到自然醒，拉开窗帘阳光正好，没有什么比这一刻更舒服了。' },
  { mood: '支棱起来了', content: '鼓起勇气拒绝了不想去的聚会，第一次把自己的感受放在第一位，感觉棒极了。' },
  { mood: '被治愈了', content: '在图书馆坐了一整天，虽然累但很充实。回家的路上买了最爱的奶茶，奖励自己。' },
]

const DEFAULT_COMPANIONS = Object.values(COMPANION_PROFILES).map(p => ({
  id: p.id, avatar: p.avatar, name: p.name, desc: p.desc
}))

async function loadCompanions() {
  try {
    const res = await axios.get(`${API}/api/companion/list`)
    companions.value = res.data?.companions || []
  } catch (e) {
    companions.value = DEFAULT_COMPANIONS
  }
}

async function startCompanion(c) {
  showCompanions.value = false
  companionId.value = c.id
  companionName.value = c.name
  companionMsgs.value = []
  companionActive.value = true

  const profile = COMPANION_PROFILES[c.id]
  const greeting = profile?.greeting || `你好呀！我是${c.name}，有什么想和我聊的吗？`

  try {
    const res = await axios.post(`${API}/api/companion/start`, null, {
      params: { user_id: Number(userStore.userId), character_id: c.id }
    })
    if (res.data?.greeting) {
      companionMsgs.value.push({ role: 'assistant', content: res.data.greeting })
    } else {
      companionMsgs.value.push({ role: 'assistant', content: greeting })
    }
  } catch (e) {
    companionMsgs.value.push({ role: 'assistant', content: greeting })
  }
}

async function sendCompanionMsg() {
  if (!companionInput.value.trim() || companionTyping.value) return

  const content = companionInput.value
  companionMsgs.value.push({ role: 'user', content })
  companionInput.value = ''
  companionTyping.value = true

  await nextTick()
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }

  try {
    const res = await sendMessage(Number(userStore.userId), content)
    companionMsgs.value.push({ role: 'assistant', content: res.data?.reply || '安全支持服务暂时没有返回内容，请稍后重试。' })
  } catch (e) {
    companionMsgs.value.push({ role: 'assistant', content: '暂时无法连接安全支持服务。若你可能伤害自己或他人，或无法保证当下安全，请立即联系身边可信成年人，并拨打12356、110或120；否则请稍后重试。' })
  }

  companionTyping.value = false
  await nextTick()
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }
}

onMounted(() => {
  loadFeed()
  loadStats()
  loadCompanions()
  // 根据日期选择每日语录（每天一样）
  const dayIndex = new Date().getDate() % WARM_QUOTES.length
  dailyQuote.value = WARM_QUOTES[dayIndex]
})

// 漂流瓶：从正能量池随机捞取
function openDriftBottle() {
  const pool = POSITIVE_BOTTLES.length > 0 ? POSITIVE_BOTTLES : posts.value
  if (!pool.length) {
    alert('树洞还是空的，来做第一个倾诉的人吧~')
    return
  }
  const randomItem = pool[Math.floor(Math.random() * pool.length)]
  driftContent.value = randomItem.content
  driftMood.value = randomItem.mood || '被治愈了'
  showDriftBottle.value = true
}
</script>

<style scoped>
.treehole-page {
  min-height: 100vh;
  background: #F5F0EC;
  padding-bottom: 80px;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.treehole-header {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; padding-top: max(16px, env(safe-area-inset-top));
  background: white; border-bottom: 1px solid #eee;
}
.treehole-header h1 { font-size: 18px; font-weight: 600; color: #3D6B5E; margin: 0; }
.back-btn { background: none; border: none; font-size: 20px; color: #5B8C7E; cursor: pointer; }

.treehole-intro { padding: 20px; text-align: center; }
.treehole-intro p { margin: 4px 0; font-size: 13px; color: #7A8B7E; }
.stats { font-size: 11px; color: #aaa; margin-top: 8px; }

/* 每日温暖 */
.daily-warmth {
  display: flex; align-items: center; justify-content: center;
  gap: 6px; margin-top: 10px; padding: 8px 14px;
  background: rgba(91,140,126,0.08); border-radius: 20px;
  max-width: 90%; margin-left: auto; margin-right: auto;
}
.dw-icon { font-size: 14px; }
.dw-text { font-size: 12px; color: #5B8C7E; font-style: italic; }

/* 入口行 */
.entry-row { display: flex; gap: 10px; margin: 0 16px 16px; }
.companion-entry {
  padding: 14px 16px; background: white;
  border-radius: 16px; display: flex; align-items: center;
  justify-content: space-between; cursor: pointer;
  transition: all 0.2s; border: 1px solid #e8e0d8;
  box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}
.companion-entry.half { flex: 1; margin: 0; }
.companion-entry.bottle { background: linear-gradient(135deg, #fff, #f8f4f0); }
.companion-entry:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.ce-left { display: flex; align-items: center; gap: 12px; }
.ce-emoji { font-size: 28px; }
.ce-title { font-size: 14px; font-weight: 600; color: #3D6B5E; }
.ce-desc { font-size: 12px; color: #888; margin-top: 2px; }
.ce-arrow { font-size: 18px; color: #5B8C7E; }

/* 陪伴选择弹窗 */
.companion-modal {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: flex-end; justify-content: center; z-index: 100;
}
.companion-panel {
  background: white; border-radius: 20px 20px 0 0; width: 100%; max-width: 480px;
  padding: 20px; max-height: 70vh;
}
.cp-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.cp-header h3 { font-size: 16px; color: #3D6B5E; margin: 0; }
.cp-close { background: none; border: none; font-size: 18px; color: #999; cursor: pointer; }
.cp-item {
  display: flex; align-items: center; gap: 14px; padding: 14px;
  border-radius: 12px; cursor: pointer; transition: all 0.2s;
}
.cp-item:hover { background: #f5f0ec; }
.cpi-avatar { width: 48px; height: 48px; border-radius: 50%; background: #E8D5B7; display: flex; align-items: center; justify-content: center; font-size: 24px; }
.cpi-info { flex: 1; }
.cpi-name { font-size: 15px; font-weight: 600; color: #333; }
.cpi-desc { font-size: 12px; color: #888; margin-top: 4px; }
.cpi-go { color: #5B8C7E; font-size: 16px; }

/* 漂流瓶弹窗 */
.drift-panel { text-align: center; }
.drift-content { padding: 20px 10px; }
.drift-mood { font-size: 13px; color: #5B8C7E; margin-bottom: 12px; }
.drift-text { font-size: 16px; color: #333; line-height: 1.8; font-style: italic; margin: 0 0 16px; }
.drift-hint { font-size: 11px; color: #bbb; }
.drift-again {
  width: 100%; padding: 12px; border-radius: 12px; border: none;
  background: #5B8C7E; color: white; font-size: 14px; cursor: pointer;
  margin-top: 8px;
}

/* 陪伴对话界面 */
.companion-chat {
  position: fixed; inset: 0; background: #F5F0EC; z-index: 90;
  display: flex; flex-direction: column;
}
.cc-header {
  padding: 16px 20px; padding-top: max(16px, env(safe-area-inset-top));
  background: white; border-bottom: 1px solid #eee;
  display: flex; align-items: center; gap: 16px;
}
.cc-header button { background: none; border: none; font-size: 14px; color: #5B8C7E; cursor: pointer; }
.cc-header span { font-size: 16px; font-weight: 600; color: #3D6B5E; }

.cc-messages { flex: 1; overflow-y: auto; padding: 16px; }
.cc-msg { margin-bottom: 12px; display: flex; }
.cc-msg.user { justify-content: flex-end; }
.cc-msg.assistant { justify-content: flex-start; }
.ccm-bubble {
  max-width: 75%; padding: 12px 16px; border-radius: 16px;
  font-size: 14px; line-height: 1.6;
}
.cc-msg.user .ccm-bubble { background: #5B8C7E; color: white; border-bottom-right-radius: 4px; }
.cc-msg.assistant .ccm-bubble { background: white; color: #333; border-bottom-left-radius: 4px; }
.ccm-bubble.typing { color: #999; font-style: italic; }

.cc-input {
  padding: 12px 16px; background: white; border-top: 1px solid #eee;
  display: flex; gap: 8px;
}
.cc-input input {
  flex: 1; padding: 10px 14px; border-radius: 20px;
  border: 1px solid #e0e0e0; font-size: 14px; outline: none;
}
.cc-input input:focus { border-color: #5B8C7E; }
.cc-input button {
  padding: 10px 18px; border-radius: 20px; border: none;
  background: #5B8C7E; color: white; font-size: 14px; cursor: pointer;
}
.cc-input button:disabled { background: #ccc; }

/* 发布区域 */
.post-area { margin: 0 16px 16px; padding: 14px 16px; background: white; border-radius: 16px; }
.mood-selector { display: flex; gap: 8px; margin-bottom: 12px; overflow-x: auto; padding-bottom: 6px; -webkit-overflow-scrolling: touch; }
/* 自定义滚动条 - 滑块效果 */
.mood-selector::-webkit-scrollbar { height: 4px; }
.mood-selector::-webkit-scrollbar-track { background: rgba(0,0,0,0.05); border-radius: 2px; }
.mood-selector::-webkit-scrollbar-thumb { background: #5B8C7E; border-radius: 2px; }
.mood-selector::-webkit-scrollbar-thumb:hover { background: #4a7a6e; }
.mood-btn {
  padding: 8px 14px; border-radius: 20px; border: 1px solid #e8e8e8;
  background: #f8f8f8; font-size: 13px; cursor: pointer; transition: all 0.2s;
  white-space: nowrap; flex-shrink: 0; user-select: none; -webkit-user-select: none;
}
.mood-btn.active { background: #5B8C7E; color: white; border-color: #5B8C7E; }

.input-row { display: flex; gap: 8px; }
.input-row input {
  flex: 1; padding: 10px 14px; border-radius: 20px;
  border: 1px solid #e0e0e0; font-size: 14px; outline: none;
}
.input-row input:focus { border-color: #5B8C7E; }
.post-btn {
  padding: 10px 18px; border-radius: 20px; border: none;
  background: #5B8C7E; color: white; font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
}
.post-btn:disabled { background: #ccc; }
.post-btn:hover:not(:disabled) { background: #4a7a6e; }

.feed { padding: 0 16px; }
.treehole-card {
  display: flex; gap: 12px; padding: 16px;
  background: white; border-radius: 16px; margin-bottom: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: all 0.2s;
}
.treehole-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.thc-mood { font-size: 28px; flex-shrink: 0; }
.thc-body { flex: 1; }
.thc-content { font-size: 14px; color: #333; line-height: 1.6; margin: 0 0 10px; }
.thc-footer { display: flex; justify-content: space-between; align-items: center; }
.thc-time { font-size: 11px; color: #bbb; }
.thc-footer { display: flex; justify-content: space-between; align-items: center; }
.thc-actions { display: flex; align-items: center; gap: 6px; }
.thc-resonance {
  background: none; border: none; font-size: 12px; color: #5B8C7E;
  cursor: pointer; padding: 4px 10px; border-radius: 12px; transition: all 0.2s;
}
.thc-resonance:hover { background: rgba(91,140,126,0.1); }
.thc-delete {
  background: none; border: none; font-size: 12px; color: #D4766A;
  cursor: pointer; padding: 4px 10px; border-radius: 12px; transition: all 0.2s;
}
.thc-delete:hover { background: rgba(212,118,106,0.1); }
.empty-hint { text-align: center; padding: 40px; font-size: 13px; color: #999; }

/* 过渡动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* inline 弹窗模式 - 适配深色背景 */
.treehole-page.inline-mode { background: transparent; padding: 0; min-height: auto; }
.treehole-page.inline-mode .treehole-intro p { color: rgba(232,226,216,0.6); }
.treehole-page.inline-mode .daily-warmth { background: rgba(127,179,166,0.1); }
.treehole-page.inline-mode .dw-text { color: #7FB3A6; }
.treehole-page.inline-mode .stats { color: rgba(232,226,216,0.4); }
.treehole-page.inline-mode .companion-entry { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.08); }
.treehole-page.inline-mode .companion-entry.bottle { background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03)); }
.treehole-page.inline-mode .ce-title { color: #7FB3A6; }
.treehole-page.inline-mode .ce-desc { color: rgba(232,226,216,0.5); }
.treehole-page.inline-mode .post-area { background: rgba(255,255,255,0.06); }
.treehole-page.inline-mode .mood-btn { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); color: rgba(232,226,216,0.7); }
.treehole-page.inline-mode .mood-btn.active { background: #5B8C7E; color: white; border-color: #5B8C7E; }
/* inline 深色滚动条 */
.treehole-page.inline-mode .mood-selector::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
.treehole-page.inline-mode .mood-selector::-webkit-scrollbar-thumb { background: #7FB3A6; }
.treehole-page.inline-mode .mood-selector::-webkit-scrollbar-thumb:hover { background: #5B8C7E; }
.treehole-page.inline-mode .input-row input { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); color: #E8E2D8; }
.treehole-page.inline-mode .input-row input::placeholder { color: rgba(232,226,216,0.35); }
.treehole-page.inline-mode .treehole-card { background: rgba(255,255,255,0.06); }
.treehole-page.inline-mode .thc-content { color: rgba(232,226,216,0.85); }
.treehole-page.inline-mode .thc-time { color: rgba(232,226,216,0.35); }
.treehole-page.inline-mode .thc-resonance { color: #7FB3A6; }
.treehole-page.inline-mode .thc-delete { color: #D4968A; }
.treehole-page.inline-mode .empty-hint { color: rgba(232,226,216,0.35); }

/* inline 弹窗深色适配 */
.treehole-page.inline-mode .companion-modal { background: rgba(0,0,0,0.5); }
.treehole-page.inline-mode .companion-panel {
  background: rgba(35,35,42,0.98);
  border: 1px solid rgba(255,255,255,0.06);
}
.treehole-page.inline-mode .cp-header h3 { color: #E8E2D8; }
.treehole-page.inline-mode .cp-close { color: rgba(232,226,216,0.5); }
.treehole-page.inline-mode .cp-item:hover { background: rgba(255,255,255,0.06); }
.treehole-page.inline-mode .cpi-name { color: #E8E2D8; }
.treehole-page.inline-mode .cpi-desc { color: rgba(232,226,216,0.45); }
.treehole-page.inline-mode .cpi-go { color: #7FB3A6; }
.treehole-page.inline-mode .drift-mood { color: #7FB3A6; }
.treehole-page.inline-mode .drift-text { color: #E8E2D8; }
.treehole-page.inline-mode .drift-hint { color: rgba(232,226,216,0.35); }

/* inline 陪伴对话深色适配 */
.treehole-page.inline-mode .companion-chat { background: rgba(20,20,25,0.98); }
.treehole-page.inline-mode .cc-header { background: rgba(35,35,42,0.98); border-color: rgba(255,255,255,0.06); }
.treehole-page.inline-mode .cc-header button { color: #7FB3A6; }
.treehole-page.inline-mode .cc-header span { color: #E8E2D8; }
.treehole-page.inline-mode .ccm-bubble { background: rgba(255,255,255,0.08); color: #E8E2D8; }
.treehole-page.inline-mode .cc-msg.user .ccm-bubble { background: #5B8C7E; }
.treehole-page.inline-mode .cc-input { background: rgba(35,35,42,0.98); border-color: rgba(255,255,255,0.06); }
.treehole-page.inline-mode .cc-input input { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.1); color: #E8E2D8; }
.treehole-page.inline-mode .cc-input input::placeholder { color: rgba(232,226,216,0.35); }

.inline-title { text-align: center; margin-bottom: 16px; }
.inline-title h2 { margin: 0; font-size: 18px; color: #E8E2D8; }
</style>
