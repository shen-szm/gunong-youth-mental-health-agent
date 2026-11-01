<template>
  <div class="home">
    <header class="header">
      <div>
        <h2>{{ greeting }}，{{ userStore.nickname || '朋友' }}</h2>
        <p class="date">{{ today }}</p>
      </div>
      <div class="avatar" @click="router.push('/profile')">{{ (userStore.nickname||'你')[0] }}</div>
    </header>

    <div class="emotion-card" :style="{background: emotionColor}" @click="showMoodPicker = true">
      <p class="emotion-label">今日情绪</p>
      <p class="emotion-value">{{ todayEmotion.label }}</p>
      <p class="emotion-hint">点击记录今日心情</p>
    </div>

    <!-- 情绪选择弹窗 -->
    <div v-if="showMoodPicker" class="modal-overlay" @click.self="showMoodPicker = false">
      <div class="modal">
        <h3>记录今日情绪</h3>
        <div class="mood-options">
          <div v-for="m in moodOptions" :key="m.label" class="mood-option"
               :style="{borderColor: selectedMood === m.label ? m.color : '#eee', background: selectedMood === m.label ? m.color + '15' : '#fff'}"
               @click="selectedMood = m.label">
            <span class="mood-emoji">{{ m.emoji }}</span>
            <span class="mood-name">{{ m.label }}</span>
          </div>
        </div>
        <textarea v-model="moodNote" class="mood-input" placeholder="写点什么吧（可选）..." rows="3"></textarea>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showMoodPicker = false">取消</button>
          <button class="btn-confirm" @click="saveMood" :disabled="!selectedMood">保存</button>
        </div>
      </div>
    </div>

    <div class="quick-actions">
      <div class="action" @click="router.push('/chat')">
        <span class="action-icon">💬</span>
        <span>开始倾诉</span>
      </div>
      <div class="action" @click="router.push('/trend')">
        <span class="action-icon">📊</span>
        <span>情绪趋势</span>
      </div>
    </div>

    <div class="section">
      <h3>✨ AI洞察</h3>
      <p class="insight">{{ insight }}</p>
    </div>

    <div class="section">
      <h3>🕐 最近心情</h3>
      <div v-if="recentMoods.length === 0" class="empty">还没有记录，去倾诉吧~</div>
      <div v-for="m in recentMoods" :key="m.id" class="mood-item">
        <span class="mood-dot" :style="{background: getMoodColor(m.label)}"></span>
        <span class="mood-label">{{ m.label }}</span>
        <span class="mood-content">{{ m.content || '无记录' }}</span>
        <span class="mood-time">{{ m.time || m.date }}</span>
      </div>
    </div>

    <footer class="beian-footer">
      <a href="https://beian.mps.gov.cn/#/query/webSearch?code=44011202003950" target="_blank" rel="noopener noreferrer" class="beian-link">
        <img src="/images/beian-icon.png" alt="公安备案" class="beian-icon" />
        <span>粤公网安备44011202003950号</span>
      </a>
      <span class="beian-divider">|</span>
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
        class="icp-link"
        aria-label="前往工信部备案管理系统查询粤ICP备2026048986号-2"
      >粤ICP备2026048986号-2</a>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "../stores/user";
import { getMoodInsight, recordMood, getMoodList, getTodayMood } from "../api/mood";

const router = useRouter();
const userStore = useUserStore();

const insight = ref("正在读取你的情绪数据...");
const recentMoods = ref([]);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 6) return "夜深了";
  if (h < 12) return "早上好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
});
const today = new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "short" });

const todayEmotion = ref({ label: "点击记录", score: 5 });
const showMoodPicker = ref(false);
const selectedMood = ref("");
const moodNote = ref("");
const savingMood = ref(false);

const moodOptions = [
  { emoji: "😠", label: "愤怒", score: 3, color: "#D4766A" },
  { emoji: "🤢", label: "厌恶", score: 2, color: "#A98A5C" },
  { emoji: "😨", label: "恐惧", score: 2, color: "#8B7BA6" },
  { emoji: "😊", label: "开心", score: 9, color: "#6DB58B" },
  { emoji: "😐", label: "中性", score: 6, color: "#A8A29A" },
  { emoji: "😢", label: "悲伤", score: 3, color: "#8EAFC4" },
  { emoji: "😲", label: "惊讶", score: 6, color: "#E8C468" },
];

async function saveMood() {
  if (!selectedMood.value) return;
  savingMood.value = true;
  try {
    const opt = moodOptions.find(m => m.label === selectedMood.value);
    await recordMood({
      user_id: userStore.userId,
      label: selectedMood.value,
      score: opt.score,
      content: moodNote.value,
    });
    todayEmotion.value = { label: selectedMood.value, score: opt.score };
    showMoodPicker.value = false;
    selectedMood.value = "";
    moodNote.value = "";
    // 刷新最近心情
    try {
      const r2 = await getMoodList(userStore.userId, 7);
      recentMoods.value = r2.data.slice(0, 5);
    } catch {}
  } catch (e) {
    alert("保存失败：" + (e.response?.data?.detail || e.message));
  } finally {
    savingMood.value = false;
  }
}
const emotionColor = computed(() => {
  const colors = {
    "愤怒":"#E8BEB8", "厌恶":"#DDD2BE", "恐惧":"#D8D0E4", "开心":"#B5E0C8",
    "中性":"#DCD9D2", "悲伤":"#B8C8D8", "惊讶":"#F0E0A8",
    "平静":"#C8E0D8", "焦虑":"#F0E0A8", "难过":"#B8C8D8",
  };
  return colors[todayEmotion.value.label] || "#C8E0D8";
});

function getMoodColor(label) {
  const colors = {
    "愤怒":"#D4766A", "厌恶":"#A98A5C", "恐惧":"#8B7BA6", "开心":"#6DB58B",
    "中性":"#A8A29A", "悲伤":"#8EAFC4", "惊讶":"#E8C468",
    "平静":"#7FB3A6", "焦虑":"#E8C468", "难过":"#8EAFC4",
  };
  return colors[label] || "#aaa";
}

onMounted(async () => {
  try {
    const r1 = await getMoodInsight(userStore.userId);
    insight.value = r1.data.insight;
  } catch {}
  try {
    const r2 = await getMoodList(userStore.userId, 7);
    recentMoods.value = r2.data.slice(0, 5);
  } catch {}
});
</script>

<style scoped>
.home { padding: 16px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { font-size: 20px; }
.date { font-size: 13px; color: var(--text-secondary); }
.avatar {
  width: 40px; height: 40px; border-radius: 50%;
  background: var(--primary); color: white;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; cursor: pointer;
  box-shadow: 0 2px 8px rgba(91,140,126,0.25);
}
.emotion-card {
  border-radius: 16px; padding: 24px; color: white;
  margin-bottom: 20px; transition: background 0.3s;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.emotion-label { font-size: 13px; opacity: 0.85; }
.emotion-value { font-size: 32px; font-weight: bold; margin: 8px 0; }
.emotion-hint { font-size: 12px; opacity: 0.75; }
.quick-actions { display: flex; gap: 12px; margin-bottom: 24px; }
.action {
  flex:1; background: var(--card); border-radius: 12px;
  padding: 16px; text-align: center; font-size: 14px;
  cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: transform 0.2s;
}
.action:hover { transform: translateY(-2px); }
.action-icon { font-size: 28px; display: block; margin-bottom: 8px; }
.section { margin-bottom: 24px; }
.section h3 { font-size: 16px; margin-bottom: 12px; }
.insight {
  background: var(--card); border-radius: 12px;
  padding: 16px; font-size: 14px; line-height: 1.6;
  color: var(--text-secondary);
  border-left: 3px solid var(--primary-light);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.mood-item {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 0; border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.mood-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink:0; }
.mood-content { flex:1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary); }
.mood-time { font-size: 12px; color: #bbb; flex-shrink:0; }
.empty { color: #bbb; font-size: 14px; text-align: center; padding: 20px 0; }

/* 情绪选择弹窗 */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.35); z-index: 100;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(2px);
}
.modal {
  background: #fff; border-radius: 20px; padding: 24px;
  width: 320px; max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
}
.modal h3 { font-size: 18px; margin-bottom: 16px; text-align: center; color: var(--text); }
.mood-options { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px; }
.mood-option {
  text-align: center; padding: 12px 4px;
  border: 2px solid var(--border); border-radius: 12px; cursor: pointer;
  transition: all 0.2s; background: #fff;
}
.mood-option:hover { transform: scale(1.05); }
.mood-emoji { font-size: 24px; display: block; }
.mood-name { font-size: 12px; display: block; margin-top: 4px; color: var(--text-secondary); }
.mood-input {
  width: 100%; border: 1px solid var(--border); border-radius: 10px;
  padding: 12px; font-size: 14px; resize: none;
  box-sizing: border-box; margin-bottom: 16px;
}
.mood-input:focus { outline: none; border-color: var(--primary); }
.modal-actions { display: flex; gap: 12px; }
.modal-actions button {
  flex: 1; padding: 10px; border: none; border-radius: 10px;
  font-size: 14px; cursor: pointer;
}
.btn-cancel { background: var(--hover); color: var(--text-secondary); }
.btn-confirm { background: var(--primary); color: #fff; transition: background 0.2s; }
.btn-confirm:hover { background: var(--primary-dark); }
.btn-confirm:disabled { opacity: 0.5; cursor: not-allowed; }

/* 备案号 */
.beian-footer {
  text-align: center;
  padding: 20px 0 12px;
  margin-top: 8px;
  display: flex; align-items: center; justify-content: center; gap: 10px;
}
.beian-footer a {
  font-size: 12px;
  color: var(--text-secondary);
  text-decoration: none;
  opacity: 0.6;
  transition: opacity 0.2s;
}
.beian-footer a:hover {
  opacity: 1;
  color: var(--primary);
}
.beian-footer a:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
  opacity: 1;
}
.icp-link { font-weight: 600; }
.beian-link {
  display: inline-flex; align-items: center; gap: 4px;
}
.beian-icon {
  width: 16px; height: 16px; display: inline-block;
}
.beian-divider {
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.3;
}

/* 响应式 */
@media (min-width: 768px) {
  .home { padding: 24px; }
  .emotion-value { font-size: 38px; }
  .quick-actions { gap: 16px; }
  .action { padding: 20px; }
}
@media (max-width: 360px) {
  .emotion-card { padding: 18px; }
  .emotion-value { font-size: 26px; }
  .mood-options { gap: 4px; }
  .mood-emoji { font-size: 20px; }
}
</style>
