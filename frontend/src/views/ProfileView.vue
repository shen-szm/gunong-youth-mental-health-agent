<template>
  <div class="profile-page">
    <!-- 顶部背景 + 头像 -->
    <div class="profile-hero">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="avatar">
          <span>{{ (userStore.nickname || '你')[0] }}</span>
        </div>
        <h3>{{ userStore.nickname || '未设置昵称' }}</h3>
        <p class="uid">ID {{ userStore.userId }}</p>
        <span v-if="userStore.isAdmin" class="admin-badge">管理员</span>
      </div>
    </div>

    <!-- 数据统计 -->
    <div class="stats-row">
      <div class="stat-item" @click="router.push('/trend')">
        <div class="stat-val">{{ stats.moodCount }}</div>
        <div class="stat-lbl">情绪记录</div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <div class="stat-val">{{ stats.chatCount }}</div>
        <div class="stat-lbl">对话次数</div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <div class="stat-val">{{ stats.days }}</div>
        <div class="stat-lbl">使用天数</div>
      </div>
    </div>

    <!-- 情绪分布 -->
    <div class="section" v-if="Object.keys(distribution).length">
      <div class="section-title">情绪分布</div>
      <div class="mood-dist">
        <div class="dist-row" v-for="(count, label) in distribution" :key="label">
          <span class="dist-emoji">{{ getEmoji(label) }}</span>
          <span class="dist-label">{{ label }}</span>
          <div class="dist-track">
            <div class="dist-fill" :style="{ width: getPercent(count)+'%' }"></div>
          </div>
          <span class="dist-pct">{{ getPercent(count) }}%</span>
        </div>
      </div>
    </div>

    <!-- 成就徽章 -->
    <div class="section">
      <div class="section-title">成就</div>
      <div class="badges">
        <div v-for="b in badges" :key="b.name" :class="['badge', { unlocked: b.unlocked }]">
          <div class="badge-icon">{{ b.icon }}</div>
          <div class="badge-name">{{ b.name }}</div>
          <div class="badge-desc">{{ b.desc }}</div>
          <div v-if="b.unlocked" class="badge-check">✓</div>
        </div>
      </div>
    </div>

    <!-- 设置 -->
    <div class="section">
      <div class="section-title">个人设置</div>
      <div class="menu-card">
        <div class="setting-row">
          <span class="setting-icon">✏️</span>
          <span class="setting-label">昵称</span>
          <input class="setting-input" v-model="nickname" placeholder="输入昵称" />
          <button class="save-btn" @click="saveNickname">保存</button>
        </div>
      </div>
    </div>

    <!-- 管理员入口 -->
    <div class="section" v-if="userStore.isAdmin">
      <div class="section-title">系统</div>
      <div class="menu-card">
        <div class="menu-row" @click="router.push('/admin')">
          <span class="setting-icon">⚙️</span>
          <span>管理后台</span>
          <span class="arrow">›</span>
        </div>
      </div>
    </div>

    <button class="logout-btn" @click="handleLogout">退出登录</button>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { updateProfile } from '../api/user'
import { getMoodStats } from '../api/mood'
import { getChatHistory } from '../api/chat'

const router = useRouter()
const userStore = useUserStore()
const nickname = ref(userStore.nickname || '')
const stats = reactive({ moodCount: 0, chatCount: 0, days: 0 })
const distribution = ref({})
const totalMoodCount = computed(() => Object.values(distribution.value).reduce((a, b) => a + b, 0))

const badges = computed(() => [
  { icon: '🌱', name: '初次倾诉', desc: '完成第一次对话', unlocked: stats.chatCount >= 1 },
  { icon: '📝', name: '记录者', desc: '记录5次情绪', unlocked: stats.moodCount >= 5 },
  { icon: '💪', name: '坚持一周', desc: '使用7天以上', unlocked: stats.days >= 7 },
  { icon: '🌟', name: '倾诉达人', desc: '20次对话', unlocked: stats.chatCount >= 20 },
  { icon: '🎯', name: '情绪大师', desc: '50次情绪记录', unlocked: stats.moodCount >= 50 },
  { icon: '💎', name: '忠实用户', desc: '使用30天以上', unlocked: stats.days >= 30 },
])

function getEmoji(label) {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😰', '难过': '😢', '愤怒': '😡' }
  return map[label] || '🙂'
}

function getPercent(count) {
  return totalMoodCount.value ? Math.round(count / totalMoodCount.value * 100) : 0
}

async function loadStats() {
  const uid = Number(userStore.userId)
  try {
    const moodRes = await getMoodStats(uid, 999)
    stats.moodCount = moodRes.data.count || 0
    distribution.value = moodRes.data.distribution || {}
    if (moodRes.data.trend) stats.days = moodRes.data.trend.length
    const chatRes = await getChatHistory(uid)
    stats.chatCount = chatRes.data?.length || 0
  } catch {}
}

async function saveNickname() {
  if (!nickname.value.trim()) { alert('昵称不能为空'); return }
  try {
    await updateProfile(Number(userStore.userId), nickname.value, '')
    userStore.login(userStore.userId, nickname.value, userStore.isAdmin)
    alert('保存成功')
  } catch { alert('保存失败') }
}

function handleLogout() {
  if (confirm('确定要退出登录吗？')) { userStore.logout(); router.push('/login') }
}

onMounted(loadStats)
</script>

<style scoped>
.profile-page {
  background: #F5F0EC; min-height: 100vh; padding-bottom: 40px;
  font-family: 'PingFang SC','Microsoft YaHei',sans-serif;
}

/* 顶部英雄区 */
.profile-hero { position: relative; padding-bottom: 28px; }
.hero-bg {
  position: absolute; inset: 0; height: 160px;
  background: linear-gradient(160deg, #A8C4B8 0%, #8EA89A 50%, #7A9A8C 100%);
  border-radius: 0 0 32px 32px;
}
.hero-content {
  position: relative; z-index: 1;
  display: flex; flex-direction: column; align-items: center;
  padding-top: 28px;
}
.avatar {
  width: 72px; height: 72px; border-radius: 50%;
  background: white; box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  display: flex; align-items: center; justify-content: center;
  font-size: 30px; font-weight: bold; color: #7A9A8C;
  margin-bottom: 10px;
}
.hero-content h3 { color: white; font-size: 18px; margin: 0; text-shadow: 0 1px 4px rgba(0,0,0,0.15); }
.uid { color: rgba(255,255,255,0.7); font-size: 12px; margin: 4px 0 0; }
.admin-badge {
  margin-top: 6px; background: rgba(255,255,255,0.25); color: white;
  font-size: 11px; padding: 2px 10px; border-radius: 10px;
}

/* 数据统计 */
.stats-row {
  background: white; margin: 0 16px 14px; border-radius: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  display: flex; align-items: center; padding: 16px 0;
}
.stat-item {
  flex: 1; text-align: center; cursor: pointer;
  transition: transform 0.2s;
}
.stat-item:hover { transform: scale(1.05); }
.stat-val { font-size: 24px; font-weight: 700; color: #5A8070; }
.stat-lbl { font-size: 11px; color: #9A948E; margin-top: 3px; }
.stat-divider { width: 1px; height: 36px; background: #F0ECE8; }

/* 通用 section */
.section { margin: 0 16px 14px; }
.section-title {
  font-size: 12px; color: #9A948E; font-weight: 500;
  letter-spacing: 1px; text-transform: uppercase;
  margin-bottom: 8px; padding-left: 4px;
}

/* 情绪分布 */
.mood-dist {
  background: white; border-radius: 16px; padding: 14px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  display: flex; flex-direction: column; gap: 10px;
}
.dist-row { display: flex; align-items: center; gap: 8px; }
.dist-emoji { font-size: 16px; width: 22px; text-align: center; }
.dist-label { width: 36px; font-size: 13px; color: #5A5450; flex-shrink: 0; }
.dist-track { flex: 1; height: 7px; background: #F0ECE8; border-radius: 4px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #8EA89A, #A8C4B8); transition: width 0.8s ease; }
.dist-pct { width: 34px; font-size: 11px; color: #9A948E; text-align: right; }

/* 成就徽章 */
.badges {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
}
.badge {
  background: white; border-radius: 14px; padding: 14px 8px 12px;
  text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  opacity: 0.35; transition: all 0.3s; position: relative;
}
.badge.unlocked { opacity: 1; box-shadow: 0 3px 12px rgba(142,168,154,0.2); }
.badge-icon { font-size: 26px; margin-bottom: 4px; }
.badge-name { font-size: 12px; font-weight: 600; color: #3A3530; }
.badge-desc { font-size: 10px; color: #9A948E; margin-top: 2px; }
.badge-check {
  position: absolute; top: 6px; right: 8px;
  font-size: 10px; color: #8EA89A; font-weight: 700;
}

/* 设置/菜单卡片 */
.menu-card {
  background: white; border-radius: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow: hidden;
}
.setting-row {
  display: flex; align-items: center; gap: 10px; padding: 14px 16px;
}
.setting-icon { font-size: 16px; }
.setting-label { font-size: 14px; color: #5A5450; flex-shrink: 0; }
.setting-input {
  flex: 1; padding: 6px 10px; border: 1.5px solid #E8E0D8;
  border-radius: 8px; font-size: 13px; outline: none;
  transition: border-color 0.2s;
}
.setting-input:focus { border-color: #8EA89A; }
.save-btn {
  padding: 6px 14px; background: #8EA89A; color: white;
  border-radius: 8px; font-size: 12px; white-space: nowrap;
  transition: background 0.2s;
}
.save-btn:hover { background: #7A9A8C; }

.menu-row {
  display: flex; align-items: center; gap: 10px; padding: 14px 16px;
  cursor: pointer; font-size: 14px; color: #5A5450;
  transition: background 0.2s;
}
.menu-row:hover { background: #F8F4F0; }
.arrow { margin-left: auto; font-size: 18px; color: #C0B8B0; }

/* 退出按钮 */
.logout-btn {
  display: block; width: calc(100% - 32px); margin: 8px 16px 0;
  padding: 13px; border-radius: 14px; text-align: center;
  font-size: 14px; color: #C06860;
  background: white; border: 1.5px solid #F0E0DE;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: all 0.2s;
}
.logout-btn:hover { background: #FFF5F3; border-color: #D4776A; }
</style>
