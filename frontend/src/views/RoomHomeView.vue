<template>
  <div class="room" :class="timeOfDay">

    <!-- ══ 欢迎遮罩：点击任意处进入 ══ -->
    <Transition name="splash-fade">
      <div v-if="showSplash" class="splash" @click="enterApp">
        <div class="splash-logo">咕哝</div>
        <div class="splash-sub">轻触，开始今天的倾诉</div>
        <div class="splash-hint">点击任意位置进入</div>
      </div>
    </Transition>

    <!-- AI 生成背景图 -->
    <div class="bg-wrap">
      <img class="room-bg" :src="bgImage" alt="温馨房间" />
    </div>

    <!-- 顶部信息栏 -->
    <div class="top-bar">
      <div class="clock">{{ currentTime }}</div>
      <div class="greeting-text">{{ greeting }}，{{ userStore.nickname || '朋友' }}</div>
      <div class="greeting-sub">今天过得怎么样？</div>
    </div>

    <!-- 窗外天气浮层 -->
    <div class="weather-float" @click="refreshWeather">
      <span>{{ weatherEmoji }}</span>
      <span>{{ temperature }}°C</span>
    </div>

    <!-- 音乐切换按钮 -->
    <button class="music-btn" @click="toggleMusic" :title="musicOn ? '关闭音乐' : '开启音乐'">
      <svg v-if="musicOn" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        <path d="M9 3v12.26A3 3 0 107.5 18c0-.17.02-.34.04-.5H7.5a.5.5 0 01-.5-.5V7H17v7.26A3 3 0 1015.5 17c0-.17.02-.34.04-.5H15.5a.5.5 0 01-.5-.5V3H9z"/>
      </svg>
      <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
        <path d="M9 3v12.26A3 3 0 107.5 18H7.5V7H17v5M3 3l18 18"/>
      </svg>
    </button>

    <!-- 交互热区 — 电脑（倾诉） -->
    <div class="hot-zone zone-monitor" @click="goToChat">
      <div class="hover-tip">💬 倾诉</div>
    </div>

    <!-- 交互热区 — 床（情绪回顾） -->
    <div class="hot-zone zone-bed" @click="goToTrend">
      <div class="bed-label">回顾近期的情绪</div>
    </div>

    <!-- 交互热区 — 窗户（出去看看） -->
    <div class="hot-zone zone-window" @click="showTransportPanel = true">
      <div class="window-label">出去看看</div>
    </div>

    <!-- 底部导航 -->
    <nav class="bottom-nav">
      <button class="bnav-item bnav-home active" @click="goToChat">
        <div class="icon-wrap">
          <!-- 像素风显示器图标 (16x16 网格) -->
          <svg class="icon-outline" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="square" shape-rendering="crispEdges">
            <!-- 显示器外框 -->
            <rect x="2" y="1" width="12" height="9" fill="none"/>
            <!-- 底座 -->
            <rect x="6.5" y="11" width="3" height="1" fill="currentColor"/>
            <rect x="7" y="10" width="2" height="1" fill="currentColor"/>
            <!-- 底座底部 -->
            <rect x="5" y="12" width="6" height="1" fill="currentColor"/>
          </svg>
          <svg class="icon-fill" viewBox="0 0 16 16" fill="currentColor" shape-rendering="crispEdges">
            <!-- 显示器外框 -->
            <rect x="2" y="1" width="12" height="9"/>
            <!-- 屏幕内部 -->
            <rect x="3.5" y="2.5" width="9" height="6" fill="none" stroke="currentColor" stroke-width="0.8"/>
            <!-- 底座 -->
            <rect x="6.5" y="11" width="3" height="1"/>
            <rect x="7" y="10" width="2" height="1"/>
            <rect x="5" y="12" width="6" height="1"/>
          </svg>
        </div>
        <span class="bnav-label">倾诉</span>
      </button>
      <button class="bnav-item bnav-me" @click="goProfile">
        <div class="icon-wrap">
          <!-- 像素风人物图标 (16x16 网格) -->
          <svg class="icon-outline" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="square" shape-rendering="crispEdges">
            <!-- 头部 -->
            <rect x="6" y="1" width="4" height="4"/>
            <!-- 身体 -->
            <rect x="4" y="6" width="8" height="1"/>
            <rect x="5" y="7" width="6" height="1"/>
            <rect x="5" y="8" width="6" height="1"/>
            <rect x="6" y="9" width="4" height="1"/>
            <!-- 腿 -->
            <rect x="6" y="10" width="1" height="2"/>
            <rect x="9" y="10" width="1" height="2"/>
          </svg>
          <svg class="icon-fill" viewBox="0 0 16 16" fill="currentColor" shape-rendering="crispEdges">
            <!-- 头部 -->
            <rect x="6" y="1" width="4" height="4"/>
            <!-- 身体 -->
            <rect x="4" y="6" width="8" height="1"/>
            <rect x="5" y="7" width="6" height="1"/>
            <rect x="5" y="8" width="6" height="1"/>
            <rect x="6" y="9" width="4" height="1"/>
            <!-- 腿 -->
            <rect x="6" y="10" width="1" height="2"/>
            <rect x="9" y="10" width="1" height="2"/>
          </svg>
        </div>
        <span class="bnav-label">我的</span>
      </button>
    </nav>

    <!-- ══ 个人中心面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showProfilePanel" class="profile-overlay" @click="showProfilePanel = false">
        <div class="profile-panel" @click.stop>
          <!-- 关闭按钮 -->
          <div class="panel-close" @click="showProfilePanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </div>

          <!-- 头像区 -->
          <div class="panel-hero">
            <div class="panel-avatar">{{ (userStore.nickname || '你')[0] }}</div>
            <div class="panel-name">{{ userStore.nickname || '未设置昵称' }}</div>
            <div class="panel-uid">ID {{ userStore.userId }}</div>
            <span v-if="userStore.isAdmin" class="panel-badge">管理员</span>
            <!-- 状态 -->
            <button class="status-tag" @click.stop="showStatusPicker = true">
              <span v-if="userStatus">{{ userStatus.emoji }} {{ userStatus.text }}</span>
              <span v-else>+ 状态</span>
            </button>
          </div>

          <!-- 数据统计 -->
          <div class="panel-stats">
            <div class="pstat-item" @click="goToTrend(); showProfilePanel = false">
              <div class="pstat-val">{{ stats.moodCount }}</div>
              <div class="pstat-lbl">情绪记录</div>
            </div>
            <div class="pstat-divider"></div>
            <div class="pstat-item">
              <div class="pstat-val">{{ stats.chatCount }}</div>
              <div class="pstat-lbl">对话次数</div>
            </div>
            <div class="pstat-divider"></div>
            <div class="pstat-item">
              <div class="pstat-val">{{ stats.days }}</div>
              <div class="pstat-lbl">使用天数</div>
            </div>
          </div>

          <!-- 情绪分布 -->
          <div class="panel-section" v-if="Object.keys(distribution).length">
            <div class="panel-sec-title">情绪分布</div>
            <div class="panel-dist">
              <div class="pdist-row" v-for="(count, label) in distribution" :key="label">
                <span class="pdist-emoji">{{ getEmoji(label) }}</span>
                <span class="pdist-label">{{ label }}</span>
                <div class="pdist-track"><div class="pdist-fill" :style="{ width: getPercent(count)+'%' }"></div></div>
                <span class="pdist-pct">{{ getPercent(count) }}%</span>
              </div>
            </div>
          </div>

          <!-- 情绪日历 -->
          <div class="panel-section">
            <div class="panel-sec-title">情绪日历</div>
            <div class="mood-calendar">
              <!-- 月份 -->
              <div v-for="month in moodCalendar" :key="month.month" class="cal-month">
                <div class="cal-month-label">{{ month.month }}</div>
                <div class="cal-grid">
                  <div v-for="day in month.days" :key="day.date" :class="['cal-day', { 'has-mood': day.mood }]">
                    <span class="cal-date">{{ day.day }}</span>
                    <span v-if="day.mood" class="cal-mood">{{ day.mood }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 成就 -->
          <div class="panel-section">
            <div class="panel-sec-title">成就</div>
            <div class="panel-badges">
              <div v-for="b in badges" :key="b.name" :class="['pbadge', { unlocked: b.unlocked }]">
                <div class="pbadge-icon">{{ b.icon }}</div>
                <div class="pbadge-name">{{ b.name }}</div>
                <div class="pbadge-desc">{{ b.desc }}</div>
                <div v-if="b.unlocked" class="pbadge-check">✓</div>
              </div>
            </div>
          </div>

          <!-- 设置 -->
          <div class="panel-section">
            <div class="panel-sec-title">个人设置</div>
            <div class="panel-menu">
              <div class="panel-setting-row">
                <span>✏️ 昵称</span>
                <input v-model="nickname" placeholder="输入昵称" />
                <button @click="saveNickname">保存</button>
              </div>
            </div>
          </div>

          <!-- 管理员 -->
          <div class="panel-section" v-if="userStore.isAdmin">
            <div class="panel-sec-title">系统</div>
            <div class="panel-menu">
              <div class="panel-menu-row" @click="router.push('/admin'); showProfilePanel = false">
                ⚙️ 管理后台 <span class="arrow">›</span>
              </div>
            </div>
          </div>

          <!-- 退出 -->
          <button class="panel-logout" @click="handleLogout">退出登录</button>
        </div>
      </div>
    </Transition>

    <!-- ══ 状态选择器 ══ -->
    <Transition name="panel-slide">
      <div v-if="showStatusPicker" class="profile-overlay" @click="showStatusPicker = false">
        <div class="profile-panel status-picker" @click.stop>
          <div class="panel-close" @click="showStatusPicker = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </div>
          <div class="trend-header">
            <h2>设个状态</h2>
            <p>随时表达你当下的心情</p>
          </div>

          <!-- 自定义 -->
          <div class="status-custom">
            <input v-model="statusInput" placeholder="说点什么..." @keyup.enter="setCustomStatus" />
            <button class="quick-btn" @click="setCustomStatus" :disabled="!statusInput.trim()">
              <span>💬</span> 就这样
            </button>
          </div>

          <!-- 预设状态 -->
          <div class="status-grid">
            <button v-for="s in presetStatuses" :key="s.text" class="status-item" @click="setStatus(s)">
              <span class="status-emoji">{{ s.emoji }}</span>
              <span class="status-text">{{ s.text }}</span>
            </button>
          </div>

          <button v-if="userStatus" class="panel-logout" @click="clearStatus" style="margin-top:10px">
            结束状态
          </button>
        </div>
      </div>
    </Transition>

    <!-- ══ 出去看看 — 交通工具选择 ══ -->
    <Transition name="panel-slide">
      <div v-if="showTransportPanel" class="profile-overlay" @click="showTransportPanel = false">
        <div class="profile-panel transport-panel" @click.stop>
          <div class="panel-close" @click="showTransportPanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </div>
          <div class="trend-header">
            <h2>🚪 出去看看</h2>
            <p>请选择你的交通工具</p>
          </div>
          <div class="transport-list">
            <button class="transport-item" @click="openCityPanel('subway')">
              <span class="transport-icon">🚇</span>
              <span class="transport-name">地铁</span>
              <span class="transport-arrow">›</span>
            </button>
            <button class="transport-item" @click="openCityPanel('bus')">
              <span class="transport-icon">🚌</span>
              <span class="transport-name">巴士</span>
              <span class="transport-arrow">›</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ══ 出去看看 — 城市选择 ══ -->
    <Transition name="panel-slide">
      <div v-if="showCityPanel" class="profile-overlay" @click="showCityPanel = false">
        <div class="profile-panel city-panel" @click.stop>
          <div class="panel-close" @click="showCityPanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </div>
          <div class="trend-header">
            <h2>{{ selectedTransportIcon }} 请选择前往的城市</h2>
            <p>当前选择：{{ selectedTransportName }}</p>
          </div>
          <div class="city-list">
            <button v-for="city in availableCities" :key="city.name" class="city-item" @click="selectCity(city)">
              <span class="city-emoji">{{ city.emoji }}</span>
              <div class="city-info">
                <span class="city-name">{{ city.name }}</span>
                <span class="city-desc">{{ city.desc }}</span>
              </div>
            </button>
          </div>
          <button class="back-btn" @click="showCityPanel = false; showTransportPanel = true">← 返回选择交通工具</button>
        </div>
      </div>
    </Transition>

    <!-- ══ 情绪回顾面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showTrendPanel" class="profile-overlay" @click="showTrendPanel = false">
        <div class="profile-panel trend-panel" @click.stop>
          <!-- 关闭按钮 -->
          <div class="panel-close" @click="showTrendPanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </div>

          <!-- 标题 -->
          <div class="trend-header">
            <h2>情绪回顾</h2>
            <p>了解你的情绪变化</p>
          </div>

          <!-- 时间标签 -->
          <div class="tab-bar">
            <button v-for="t in trendTabs" :key="t.key" :class="{active: trendActiveTab===t.key}" @click="trendActiveTab=t.key">
              {{ t.label }}
            </button>
          </div>

          <!-- 空状态 -->
          <div class="empty-state" v-if="!trendStats.trend?.length && !Object.keys(trendStats.distribution||{}).length">
            <div class="empty-icon">🌿</div>
            <p>还没有情绪记录</p>
            <p class="empty-hint">去倾诉一下，这里会自动记录你的情绪变化</p>
            <button class="go-chat-btn" @click="showTrendPanel = false; goToChat()">去倾诉 →</button>
          </div>

          <!-- 统计卡片 -->
          <div class="stats-row" v-else>
            <div class="stat-card main-stat">
              <div class="score-wrap">
                <svg class="score-ring" viewBox="0 0 80 80">
                  <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="6"/>
                  <circle cx="40" cy="40" r="34" fill="none" :stroke="trendScoreColor" stroke-width="6"
                    stroke-linecap="round" stroke-dasharray="213.6"
                    :stroke-dashoffset="213.6 - 213.6 * ((trendStats.avg_score || 0) / 10)"
                    transform="rotate(-90 40 40)" style="transition:stroke-dashoffset 1s ease"/>
                </svg>
                <div class="main-score" :style="{color: trendScoreColor}">{{ trendStats.avg_score || '--' }}</div>
              </div>
              <div class="main-label">平均情绪分</div>
              <div class="main-hint" :style="{color: trendScoreColor}">{{ trendScoreHint }}</div>
            </div>
            <div class="side-stats">
              <div class="stat-card side-card">
                <div class="side-val">{{ trendStats.count || 0 }}</div>
                <div class="side-label">记录次数</div>
              </div>
              <div class="stat-card side-card">
                <div class="side-emoji">{{ topMoodEmoji }}</div>
                <div class="side-label">主要情绪</div>
              </div>
            </div>
          </div>

          <!-- 折线图 -->
          <div class="card chart-card" v-if="trendStats.trend?.length">
            <div class="card-title">📈 情绪走势</div>
            <div class="line-chart-wrap">
              <svg class="line-chart" viewBox="0 0 300 100" preserveAspectRatio="none">
                <line v-for="y in [20,50,80]" :key="y" x1="0" :y1="y" x2="300" :y2="y" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
                <defs>
                  <linearGradient id="trendLineGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" :stop-color="trendScoreColor" stop-opacity="0.25"/>
                    <stop offset="100%" :stop-color="trendScoreColor" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <polygon v-if="polyPoints" :points="polyPoints + ` ${lastX},95 ${firstX},95`" :fill="'url(#trendLineGrad)'"/>
                <polyline v-if="linePoints" :points="linePoints" fill="none" :stroke="trendScoreColor" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
                <circle v-for="(p, i) in chartPoints" :key="i" :cx="p.x" :cy="p.y" r="3.5" fill="white" :stroke="trendScoreColor" stroke-width="2"/>
              </svg>
              <div class="x-labels">
                <span v-for="(d, i) in xLabels" :key="i">{{ d }}</span>
              </div>
            </div>
          </div>

          <!-- 情绪分布 -->
          <div class="card" v-if="trendStats.distribution && Object.keys(trendStats.distribution).length">
            <div class="card-title">🎯 情绪分布</div>
            <div class="dist-list">
              <div v-for="(count, label) in sortedDist" :key="label" class="dist-row">
                <span class="dist-emoji">{{ getMoodEmoji(label) }}</span>
                <span class="dist-label">{{ label }}</span>
                <div class="dist-track">
                  <div class="dist-fill" :style="{width: getDistWidth(count)+'%', background: getMoodColor(label)}"></div>
                </div>
                <span class="dist-pct">{{ getDistWidth(count) }}%</span>
              </div>
            </div>
          </div>

          <!-- 情绪日历（仅"全部"时显示） -->
          <div class="card" v-if="trendActiveTab === 999 && moodCalendar.length">
            <div class="card-title">📅 情绪日历</div>
            <div class="mood-calendar">
              <div v-for="month in moodCalendar" :key="month.month" class="cal-month">
                <div class="cal-month-label">{{ month.month }}</div>
                <div class="cal-grid">
                  <div v-for="day in month.days" :key="day.date" :class="['cal-day', { 'has-mood': day.mood }]">
                    <span class="cal-date">{{ day.day }}</span>
                    <span v-if="day.mood" class="cal-mood">{{ day.mood }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- AI 洞察 -->
          <div class="card insight-card" v-if="trendStats.trend?.length">
            <div class="card-title">🤖 AI情绪洞察</div>
            <div class="insight-content">
              <div v-if="trendInsightLoading" class="insight-loading">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
              <p v-else class="insight-text">{{ trendInsight }}</p>
            </div>
            <button class="refresh-btn" @click="loadTrendInsight" :disabled="trendInsightLoading">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="margin-right:4px"><path d="M17.65 6.35A7.96 7.96 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
              重新分析
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ══ 聊天面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showChatPanel" class="profile-overlay" @click="showChatPanel = false">
        <div class="profile-panel chat-panel" @click.stop>
          <!-- 关闭按钮 -->
          <div class="panel-close" @click="showChatPanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </div>

          <!-- 顶部 -->
          <div class="chat-header">
            <div class="header-center">
              <img src="/images/logo.jpg" class="ai-avatar ai-logo" alt="咕哝" />
              <div>
                <div class="ai-name">咕哝</div>
                <div class="ai-status">
                  <span class="status-dot" :class="{thinking: chatLoading}"></span>
                  {{ chatLoading ? '正在思考...' : '在线，随时倾听' }}
                </div>
              </div>
            </div>
          </div>

          <!-- 消息列表 -->
          <div class="chat-messages" ref="msgBox">
            <div class="welcome-wrap" v-if="chatMessages.length === 0">
              <img src="/images/logo.jpg" class="welcome-avatar ai-logo" alt="咕哝" />
              <div class="welcome-bubble">
                <p>嘿，你来了 👋</p>
                <p>今天怎么样？有什么想聊的，我都在这里。</p>
              </div>
            </div>

            <div v-for="(m, i) in chatMessages" :key="i" :class="['msg-row', m.role]">
              <img v-if="m.role === 'assistant'" src="/images/logo.jpg" class="msg-avatar ai-logo" alt="咕哝" />
              <div class="bubble-wrap">
                <div v-if="m.emotion" class="emotion-tag">
                  <span>{{ getEmotionEmoji(m.emotion) }}</span>
                  <span>{{ m.emotion }}</span>
                </div>
                <div class="bubble">
                  <span>{{ m.content }}</span>
                </div>
                <button v-if="m.role === 'assistant'" class="tts-btn" @click="playTTS(m.content)" :class="{playing: ttsPlaying === i}">
                  <svg v-if="ttsPlaying !== i" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.8-1-3.3-2.5-4v8c1.5-.7 2.5-2.2 2.5-4z"/></svg>
                  <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                </button>
              </div>
            </div>

            <div v-if="chatLoading" class="msg-row assistant">
              <img src="/images/logo.jpg" class="msg-avatar ai-logo" alt="咕哝" />
              <div class="bubble-wrap">
                <div class="bubble typing-bubble">
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </div>
              </div>
            </div>
          </div>

          <!-- 快捷按钮 -->
          <div class="quick-wrap">
            <div class="quick-scroll">
              <button v-for="e in emotions" :key="e.text" class="quick-btn" @click="sendChatMsg(e.text)">
                <span>{{ e.emoji }}</span> {{ e.text }}
              </button>
            </div>
          </div>

          <!-- 输入栏 -->
          <div class="input-bar">
            <button class="voice-btn" :class="{ recording }" @click="toggleVoice" :disabled="chatLoading" :title="recording ? '停止录音' : '语音输入'">
              <svg v-if="!recording" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 14c1.7 0 3-1.3 3-3V5c0-1.7-1.3-3-3-3S9 3.3 9 5v6c0 1.7 1.3 3 3 3zm5.3-3c0 3-2.5 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.4 2.7 6.2 6 6.7V21h2v-3.3c3.3-.5 6-3.3 6-6.7h-1.7z"/></svg>
              <span v-else class="rec-wave"></span>
            </button>
            <div class="input-wrap">
              <input v-model="chatInput" placeholder="说说你的感受..." @keyup.enter="sendChatMsg()" :disabled="chatLoading" ref="inputEl"/>
            </div>
            <button class="send-btn" @click="sendChatMsg()" :disabled="chatLoading || !chatInput.trim()">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
            </button>
          </div>

          <!-- 录音提示 -->
          <transition name="hint-fade">
            <div v-if="recording" class="recording-hint">
              <span class="rec-dot"></span> 正在录音，再次点击停止
            </div>
          </transition>
        </div>
      </div>
    </Transition>

    <!-- 隐藏音频元素 -->
    <audio ref="audioEl" src="/audio/bgm.mp3" loop preload="auto" />
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { updateProfile } from '../api/user'
import { getMoodStats, getMoodInsight } from '../api/mood'
import { getChatHistory, sendMessage } from '../api/chat'

const router = useRouter()
const userStore = useUserStore()

// ═══ 个人中心面板 ═══
const showProfilePanel = ref(false)
const showChatPanel = ref(false)
const showStatusPicker = ref(false)
const nickname = ref(userStore.nickname || '')
const stats = reactive({ moodCount: 0, chatCount: 0, days: 0 })

// ═══ 出去看看 — 交通工具 & 城市 ═══
const showTransportPanel = ref(false)
const showCityPanel = ref(false)
const selectedTransport = ref('')
const selectedTransportIcon = computed(() => selectedTransport.value === 'subway' ? '🚇' : '🚌')
const selectedTransportName = computed(() => selectedTransport.value === 'subway' ? '地铁' : '巴士')

const cityData = {
  subway: [
    { name: '洛阳', emoji: '🏯', desc: '千年古都，牡丹花城' },
    { name: '西安', emoji: '🏯', desc: '十三朝古都，长安风韵' },
  ],
  bus: []
}

const availableCities = computed(() => cityData[selectedTransport.value] || [])

function openCityPanel(type) {
  selectedTransport.value = type
  showTransportPanel.value = false
  showCityPanel.value = true
}

function selectCity(city) {
  alert(`你选择了${selectedTransportName.value}前往${city.name} ${city.emoji}`)
  showCityPanel.value = false
}

// ═══ 微信状态 ═══
const userStatus = ref(JSON.parse(localStorage.getItem('shengyu_user_status') || 'null'))
const statusInput = ref('')

const presetStatuses = [
  { emoji: '😊', text: '美滋滋' },
  { emoji: '😩', text: '裂开' },
  { emoji: '✨', text: '求锦鲤' },
  { emoji: '☀️', text: '等天晴' },
  { emoji: '😴', text: '疲惫' },
  { emoji: '😶', text: '发呆' },
  { emoji: '🏃', text: '冲' },
  { emoji: '😢', text: 'emo' },
  { emoji: '💭', text: '胡思乱想' },
  { emoji: '🔥', text: '元气满满' },
  { emoji: '🤖', text: 'bot' },
  { emoji: '🧱', text: '搬砖' },
  { emoji: '📚', text: '沉迷学习' },
  { emoji: '⏰', text: '忙' },
  { emoji: '🐟', text: '摸鱼' },
  { emoji: '✈️', text: '出差' },
  { emoji: '🏠', text: '飞奔回家' },
  { emoji: '🌙', text: '勿扰模式' },
  { emoji: '🌊', text: '浪' },
  { emoji: '📍', text: '打卡' },
  { emoji: '🏃', text: '运动' },
  { emoji: '☕', text: '喝咖啡' },
  { emoji: '🧋', text: '喝奶茶' },
  { emoji: '🍚', text: '干饭' },
  { emoji: '👶', text: '带娃' },
  { emoji: '🦸', text: '拯救世界' },
  { emoji: '🤳', text: '自拍' },
]

function addStatusHistory(emoji, text) {
  const now = new Date()
  const dateStr = now.toISOString().slice(0, 10)
  const history = JSON.parse(localStorage.getItem('shengyu_status_history') || '[]')
  // 同一天覆盖，新增日期追加
  const idx = history.findIndex(h => h.date === dateStr)
  if (idx >= 0) { history[idx] = { date: dateStr, emoji, text } }
  else { history.push({ date: dateStr, emoji, text }) }
  localStorage.setItem('shengyu_status_history', JSON.stringify(history))
  buildStatusCalendar()
}

function setStatus(item) {
  userStatus.value = { emoji: item.emoji, text: item.text }
  localStorage.setItem('shengyu_user_status', JSON.stringify(userStatus.value))
  addStatusHistory(item.emoji, item.text)
  showStatusPicker.value = false
}
function setCustomStatus() {
  const text = statusInput.value.trim()
  if (!text) return
  userStatus.value = { emoji: '💬', text }
  localStorage.setItem('shengyu_user_status', JSON.stringify(userStatus.value))
  addStatusHistory('💬', text)
  statusInput.value = ''
  showStatusPicker.value = false
}
function clearStatus() {
  userStatus.value = null
  localStorage.removeItem('shengyu_user_status')
  showStatusPicker.value = false
}
const distribution = ref({})
const totalMoodCount = computed(() => Object.values(distribution.value).reduce((a, b) => a + b, 0))

// ═══ 情绪回顾面板 ═══
const showTrendPanel = ref(false)
const trendActiveTab = ref(7)
const trendTabs = [{ key: 7, label: '近7天' }, { key: 30, label: '近30天' }, { key: 999, label: '全部' }]
const trendStats = ref({})
const trendInsight = ref('正在分析你的情绪数据...')
const trendInsightLoading = ref(false)

const trendScoreColor = computed(() => {
  const s = trendStats.value.avg_score || 5
  if (s >= 7) return '#6DB58B'
  if (s >= 5) return '#7FB3A6'
  if (s >= 3) return '#E8C468'
  return '#D4776A'
})
const trendScoreHint = computed(() => {
  const s = trendStats.value.avg_score || 0
  if (s >= 8) return '状态很好 ☺'
  if (s >= 6) return '整体不错'
  if (s >= 4) return '需要关注'
  if (s > 0) return '建议多倾诉'
  return '--'
})
const topMood = computed(() => {
  const dist = trendStats.value.distribution || {}
  if (!Object.keys(dist).length) return '--'
  return Object.entries(dist).sort((a, b) => b[1] - a[1])[0][0]
})
const topMoodEmoji = computed(() => {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😰', '难过': '😢', '愤怒': '😡' }
  return map[topMood.value] || '--'
})
const sortedDist = computed(() => {
  const dist = trendStats.value.distribution || {}
  return Object.fromEntries(Object.entries(dist).sort((a, b) => b[1] - a[1]))
})

// 折线图计算
const chartPoints = computed(() => {
  const trend = trendStats.value.trend || []
  if (!trend.length) return []
  const n = trend.length
  return trend.map((d, i) => ({
    x: n === 1 ? 150 : 15 + (i / (n - 1)) * 270,
    y: 95 - (d.avg / 10) * 80
  }))
})
const linePoints = computed(() => chartPoints.value.map(p => `${p.x},${p.y}`).join(' '))
const polyPoints = computed(() => linePoints.value)
const firstX = computed(() => chartPoints.value[0]?.x)
const lastX = computed(() => chartPoints.value[chartPoints.value.length - 1]?.x)
const xLabels = computed(() => {
  const trend = trendStats.value.trend || []
  if (!trend.length) return []
  if (trend.length <= 5) return trend.map(d => d.date.slice(5))
  const step = Math.ceil(trend.length / 5)
  return trend.filter((_, i) => i % step === 0 || i === trend.length - 1).map(d => d.date.slice(5))
})

function getMoodEmoji(label) {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😰', '难过': '😢', '愤怒': '😡' }
  return map[label] || '🙂'
}
function getMoodColor(label) {
  const c = { '开心': '#6DB58B', '平静': '#7FB3A6', '焦虑': '#E8C468', '难过': '#8EAFC4', '愤怒': '#D4776A' }
  return c[label] || '#C8BEB4'
}
function getDistWidth(count) {
  const total = Object.values(trendStats.value.distribution || {}).reduce((a, b) => a + b, 0)
  return total ? Math.round(count / total * 100) : 0
}

async function loadTrendData() {
  try {
    const r = await getMoodStats(Number(userStore.userId), trendActiveTab.value)
    trendStats.value = r.data
  } catch {}
}
async function loadTrendInsight() {
  trendInsightLoading.value = true; trendInsight.value = ''
  try {
    const r = await getMoodInsight(Number(userStore.userId))
    trendInsight.value = r.data.insight
  } catch { trendInsight.value = '分析失败，请稍后重试~' }
  trendInsightLoading.value = false
}
function openTrendPanel() {
  showTrendPanel.value = true
  loadTrendData(); loadTrendInsight()
}
watch(trendActiveTab, loadTrendData)
watch(showChatPanel, (v) => { if (v) nextTick(() => scrollChatBottom()) })

const badges = computed(() => [
  { icon: '🌱', name: '初次倾诉', desc: '完成第一次对话', unlocked: stats.chatCount >= 1 },
  { icon: '📝', name: '记录者', desc: '记录5次情绪', unlocked: stats.moodCount >= 5 },
  { icon: '💪', name: '坚持一周', desc: '使用7天以上', unlocked: stats.days >= 7 },
  { icon: '🌟', name: '倾诉达人', desc: '20次对话', unlocked: stats.chatCount >= 20 },
  { icon: '🎯', name: '情绪大师', desc: '50次情绪记录', unlocked: stats.moodCount >= 50 },
  { icon: '💎', name: '忠实用户', desc: '使用30天以上', unlocked: stats.days >= 30 },
])

/* 情绪日历（从状态历史生成） */
const moodCalendar = ref([])

function buildStatusCalendar() {
  const history = JSON.parse(localStorage.getItem('shengyu_status_history') || '[]')
  // 把当前状态也加入今天（如果历史里没有今天的话）
  const today = new Date().toISOString().slice(0, 10)
  if (userStatus.value && !history.find(h => h.date === today)) {
    history.unshift({ date: today, emoji: userStatus.value.emoji, text: userStatus.value.text })
  }
  if (!history.length) { moodCalendar.value = []; return }
  // 按日期排序（最新在前）
  const sorted = [...history].sort((a, b) => b.date.localeCompare(a.date))
  // 按年月分组
  const groups = {}
  for (const h of sorted) {
    const [y, m] = h.date.split('-')
    const key = `${y}-${m}`
    if (!groups[key]) groups[key] = { year: y, month: Number(m), days: {} }
    groups[key].days[Number(h.date.split('-')[2])] = h.emoji
  }
  // 每个月生成1号到最后一条记录的日期
  const result = []
  for (const key of Object.keys(groups).sort().reverse()) {
    const g = groups[key]
    const lastDay = Math.max(...Object.keys(g.days).map(Number))
    const monthLabel = g.month + '月'
    const days = []
    for (let d = lastDay; d >= 1; d--) {
      const dateStr = `${g.year}-${String(g.month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      days.push({ day: d, date: dateStr, mood: g.days[d] || null })
    }
    result.push({ month: monthLabel, days })
  }
  moodCalendar.value = result
}

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
  if (confirm('确定要退出登录吗？')) { userStore.logout(); showProfilePanel.value = false }
}

function openProfile() {
  showProfilePanel.value = true
  nickname.value = userStore.nickname || ''
  loadStats()
}

// ─── 欢迎遮罩 & BGM ───
const showSplash = ref(true)
const audioEl = ref(null)
const musicOn = ref(true)

function enterApp() {
  showSplash.value = false
  // 用户触发点击，绕过浏览器自动播放限制
  if (audioEl.value) {
    audioEl.value.loop = true
    audioEl.value.volume = 0
    audioEl.value.play().then(() => {
      // 渐入音量
      let vol = 0
      const fade = setInterval(() => {
        vol = Math.min(vol + 0.04, 0.45)
        audioEl.value.volume = vol
        if (vol >= 0.45) clearInterval(fade)
      }, 80)
    }).catch(() => {})
  }
}

function toggleMusic() {
  if (!audioEl.value) return
  if (musicOn.value) {
    // 渐出后暂停
    let vol = audioEl.value.volume
    const fade = setInterval(() => {
      vol = Math.max(vol - 0.05, 0)
      audioEl.value.volume = vol
      if (vol <= 0) { clearInterval(fade); audioEl.value.pause() }
    }, 50)
  } else {
    // 恢复播放并渐入
    audioEl.value.loop = true
    audioEl.value.play().then(() => {
      let vol = 0
      const fade = setInterval(() => {
        vol = Math.min(vol + 0.04, 0.45)
        audioEl.value.volume = vol
        if (vol >= 0.45) clearInterval(fade)
      }, 80)
    }).catch(() => {})
  }
  musicOn.value = !musicOn.value
}

// ─── 调试模式 ───
const debugTime = ref('auto')
const debugWeather = ref('auto')

// ─── 时间 ───
const currentHour = ref(new Date().getHours())
const currentTime = ref('')
let timer = null

function tick() {
  const now = new Date()
  if (debugTime.value === 'auto') currentHour.value = now.getHours()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const timeOfDay = computed(() => {
  const h = currentHour.value
  if (h >= 6 && h < 17) return 'day'
  if (h >= 17 && h < 20) return 'evening'
  return 'night'
})

// ─── 屏幕尺寸检测 ───
const isDesktop = ref(window.innerWidth >= 768)
function onResize() { isDesktop.value = window.innerWidth >= 768 }

// ─── 昼夜背景图 ───
const bgImage = computed(() => {
  if (isDesktop.value) {
    if (timeOfDay.value === 'day') return '/images/电脑端-白天.jpg'
    if (timeOfDay.value === 'evening') return '/images/电脑端-傍晚.jpg'
    return '/images/电脑端-夜晚.jpg'
  }
  if (timeOfDay.value === 'day') return '/images/手机版-白天.jpg'
  if (timeOfDay.value === 'evening') return '/images/手机版-傍晚.jpg'
  return '/images/手机版-夜晚.jpg'
})

const greeting = computed(() => {
  const h = currentHour.value
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

// ─── 天气 ───
const weatherCode = ref(0)
const temperature = ref('--')
const weatherEmoji = ref('☀️')

function emojiFor(code) {
  if (code === 0) return '☀️'
  if (code <= 3) return '⛅'
  if (code <= 48) return '🌫️'
  if (code <= 67) return '🌧️'
  if (code <= 77) return '❄️'
  if (code <= 82) return '🌧️'
  if (code <= 86) return '❄️'
  return '⛈️'
}

async function fetchWeather(lat, lon) {
  try {
    const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,weather_code&timezone=auto`)
    const d = await r.json()
    weatherCode.value = d.current.weather_code
    temperature.value = Math.round(d.current.temperature_2m)
    weatherEmoji.value = emojiFor(d.current.weather_code)
  } catch { temperature.value = '--'; weatherEmoji.value = '☀️' }
}

function refreshWeather() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      p => fetchWeather(p.coords.latitude, p.coords.longitude),
      () => fetchWeather(23.13, 113.26)
    )
  } else {
    fetchWeather(23.13, 113.26)
  }
}

// ─── 导航 ───
function goToChat()  { openChatPanel() }
function goToTrend() { openTrendPanel() }
function goProfile() { openProfile() }

// ═══ 聊天面板 ═══
const chatInput = ref('')
const chatMessages = ref([])
const chatLoading = ref(false)
const recording = ref(false)
const msgBox = ref(null)
const inputEl = ref(null)
const ttsPlaying = ref(-1)

const emotions = [
  { emoji: '😰', text: '今天有点焦虑' },
  { emoji: '😊', text: '我感到很开心' },
  { emoji: '😩', text: '最近压力很大' },
  { emoji: '😢', text: '有点难过' },
  { emoji: '😤', text: '我想吐槽一下' },
  { emoji: '😴', text: '感觉很疲惫' },
]

function getEmotionEmoji(emotion) {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😰', '难过': '😢', '愤怒': '😡', '疲惫': '😴' }
  return map[emotion] || '🙂'
}

async function sendChatMsg(text) {
  const msg = text || chatInput.value.trim()
  if (!msg || chatLoading.value) return
  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: msg })
  await nextTick()
  scrollChatBottom()
  chatLoading.value = true
  try {
    const res = await sendMessage(Number(userStore.userId), msg)
    await nextTick()
    if (res.data?.reply) {
      chatMessages.value.push({ role: 'assistant', content: res.data.reply, emotion: res.data.emotion })
    } else {
      chatMessages.value.push({ role: 'assistant', content: '抱歉，我暂时无法回复，请稍后再试...' })
    }
  } catch (err) {
    console.error('发送失败:', err)
    chatMessages.value.push({ role: 'assistant', content: '网络异常，请检查连接后重试...' })
  }
  chatLoading.value = false
  await nextTick()
  scrollChatBottom()
}

function scrollChatBottom() {
  nextTick(() => { if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight })
}

// 语音输入
let mediaRecorder = null, audioContext = null, audioChunks = [], mediaStream = null

async function toggleVoice() {
  recording.value ? stopRecording() : await startRecording()
}

async function startRecording() {
  try {
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

function stopRecording() {
  recording.value = false
  if (audioContext) { audioContext.close().catch(() => {}); audioContext = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (!audioChunks.length) return
  const totalLength = audioChunks.reduce((a, b) => a + b.byteLength, 0)
  const merged = new Int16Array(totalLength / 2)
  let offset = 0
  for (const chunk of audioChunks) { merged.set(new Int16Array(chunk), offset); offset += chunk.byteLength / 2 }
  const wavBuffer = encodeWav(merged.buffer, 16000)
  chatLoading.value = true
  fetch('/api/chat/asr', { method: 'POST', body: new Blob([wavBuffer], { type: 'audio/wav' }), headers: { 'Content-Type': 'audio/wav' } })
    .then(r => r.json())
    .then(data => { if (data.text) sendChatMsg(data.text); else chatMessages.value.push({ role: 'assistant', content: '没有听清，请再说一次~' }) })
    .catch(() => chatMessages.value.push({ role: 'assistant', content: '语音识别失败，请重试...' }))
    .finally(() => { chatLoading.value = false })
  audioChunks = []
}

function playTTS(text) {
  if (!text) return
  fetch('/api/chat/tts?text=' + encodeURIComponent(text))
    .then(r => { if (!r.ok) throw new Error(); return r.blob() })
    .then(blob => {
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.play().catch(() => alert('语音播放失败'))
      audio.onended = () => { URL.revokeObjectURL(url); ttsPlaying.value = -1 }
    })
    .catch(() => alert('语音合成失败'))
}

async function openChatPanel() {
  showChatPanel.value = true
  chatInput.value = ''
  try {
    const res = await getChatHistory(Number(userStore.userId))
    if (res.data?.length) chatMessages.value = res.data
    scrollChatBottom()
  } catch {}
}

onMounted(() => { tick(); timer = setInterval(tick, 30000); refreshWeather(); window.addEventListener('resize', onResize); buildStatusCalendar() })
onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (audioEl.value) audioEl.value.pause()
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
/* ═══════════ 全局 ═══════════ */
.room {
  width: 100%; height: 100vh; position: relative; overflow: hidden;
  font-family: 'PingFang SC','Microsoft YaHei','Noto Sans SC',sans-serif;
}

/* ═══════════ 欢迎遮罩 ═══════════ */
.splash {
  position: fixed; inset: 0; z-index: 999;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px;
  background: rgba(18, 20, 28, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  cursor: pointer;
  user-select: none;
}
.splash-logo {
  font-size: 52px; font-weight: 700; letter-spacing: 8px;
  color: #F0EAE0;
  text-shadow: 0 2px 20px rgba(255,220,160,0.25);
}
.splash-sub {
  font-size: 15px; color: rgba(220,215,210,0.7); letter-spacing: 2px;
}
.splash-hint {
  margin-top: 40px;
  font-size: 12px; color: rgba(200,200,200,0.35); letter-spacing: 1.5px;
  animation: hint-blink 2s ease-in-out infinite;
}
@keyframes hint-blink {
  0%,100% { opacity: 0.35; }
  50%     { opacity: 0.75; }
}
/* 遮罩消失动画 */
.splash-fade-leave-active { transition: opacity 0.8s ease, filter 0.8s ease; }
.splash-fade-leave-from   { opacity: 1; filter: blur(0); }
.splash-fade-leave-to     { opacity: 0; filter: blur(8px); }

/* ═══════════ 背景图 ═══════════ */
.bg-wrap { position: absolute; inset: 0; z-index: 0; }
.room-bg { width: 100%; height: 100%; object-fit: cover; object-position: center; }

/* ═══════════ 顶部信息栏 ═══════════ */
.top-bar {
  position: absolute; top: 16px; left: 0; right: 0;
  display: flex; flex-direction: column; align-items: center;
  text-align: center; gap: 2px; z-index: 30; pointer-events: none;
}
.clock {
  font-size: 14px; font-weight: 500; opacity: 0.85;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 1px 6px rgba(0,0,0,0.3); margin-bottom: 2px;
}
.greeting-text {
  font-size: 18px; font-weight: 600; letter-spacing: 0.5px;
  text-shadow: 0 1px 8px rgba(0,0,0,0.3);
}
.greeting-sub {
  font-size: 12px; margin-top: 2px; opacity: 0.75;
  text-shadow: 0 1px 6px rgba(0,0,0,0.2);
}

/* ═══════════ 天气浮层 ═══════════ */
.weather-float {
  position: absolute; top: 18%; left: 8%; z-index: 20;
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; padding: 4px 12px; border-radius: 12px;
  backdrop-filter: blur(10px);
  cursor: pointer; transition: transform 0.2s;
}
.weather-float:hover { transform: scale(1.05); }

/* ═══════════ 音乐按钮 ═══════════ */
.music-btn {
  position: fixed; bottom: 64px; right: 18px; z-index: 200;
  width: 34px; height: 34px; border-radius: 50%;
  background: rgba(255,255,255,0.12);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: rgba(255,255,255,0.6);
  transition: color 0.2s, background 0.2s, transform 0.2s;
}
.music-btn:hover {
  color: rgba(255,255,255,0.95);
  background: rgba(255,255,255,0.2);
  transform: scale(1.08);
}
.music-btn:active { transform: scale(0.9); }
.night .music-btn { color: rgba(160,185,210,0.6); }
.night .music-btn:hover { color: rgba(200,220,240,0.95); }

/* ═══════════ 交互热区 ═══════════ */
.hot-zone {
  position: absolute; z-index: 10;
  cursor: pointer; border-radius: 8px; transition: background 0.3s;
}
.hot-zone:hover { background: rgba(255,255,255,0.06); }


/* 窗户悬浮文字 */
.window-label {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%) rotate(15deg) scale(1);
  font-size: 24px; font-weight: 900;
  color: #FFFFFF;
  text-shadow: 2px 2px 0 rgba(0,0,0,0.7);
  white-space: nowrap;
  pointer-events: none;
  letter-spacing: 6px;
  opacity: 1;
  font-family: 'Press Start 2P', 'Courier New', monospace;
  -webkit-font-smoothing: none;
  -moz-osx-font-smoothing: unset;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.zone-window:hover .window-label {
  transform: translate(-50%, -50%) rotate(15deg) scale(1.15);
}

.zone-monitor { top: 42%; left: 38%; width: 30%; height: 6%; }
.zone-bed     { bottom: 20%; left: 5%; width: 26%; height: 20%; transform: rotate(-38deg); }
.zone-window  { top: 14%; left: 12%; width: 30%; height: 33%; transform: rotate(-15deg); }

.hover-tip {
  position: absolute; bottom: -8px; left: 50%;
  font-size: 12px; padding: 4px 14px; border-radius: 12px;
  white-space: nowrap; opacity: 0;
  pointer-events: none; backdrop-filter: blur(6px);
  transform: translateX(-50%) translateY(4px);
  transition: opacity 0.25s, transform 0.25s;
}
.hot-zone:hover .hover-tip { opacity: 1; transform: translateX(-50%) translateY(0); }
.night .hover-tip   { background: rgba(0,0,0,0.5); color: #E0D4C8; }
.day .hover-tip,
.evening .hover-tip { background: rgba(255,255,255,0.75); color: #5A5450; }

/* 床上悬浮文字标签 */
.bed-label {
  position: absolute;
  top: 40%; left: 50%;
  transform: translate(-50%, -50%) rotate(38deg);
  font-size: 13px; font-weight: 500;
  color: rgba(255,255,255,0.92);
  text-shadow: 0 1px 6px rgba(0,0,0,0.35);
  white-space: nowrap;
  pointer-events: none;
  letter-spacing: 1px;
  opacity: 0;
  transition: opacity 0.3s;
}
.hot-zone:hover .bed-label { opacity: 1; }

/* ═══════════ 出去看看面板 ═══════════ */
.transport-panel, .city-panel { padding-top: 14px; }
.transport-list { display: flex; flex-direction: column; gap: 10px; padding: 0 4px; }
.transport-item {
  display: flex; align-items: center; gap: 14px;
  padding: 18px 16px; border-radius: 16px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  cursor: pointer; transition: all 0.2s;
  color: #E8E2D8; font-size: 15px;
}
.transport-item:hover { background: rgba(255,255,255,0.12); transform: translateY(-1px); }
.transport-item:active { transform: scale(0.98); }
.transport-icon { font-size: 28px; }
.transport-name { flex: 1; text-align: left; font-weight: 500; }
.transport-arrow { font-size: 20px; color: rgba(200,200,200,0.3); }

.city-list { display: flex; flex-direction: column; gap: 10px; padding: 0 4px; }
.city-item {
  display: flex; align-items: center; gap: 14px;
  padding: 16px; border-radius: 16px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  cursor: pointer; transition: all 0.2s;
  color: #E8E2D8;
}
.city-item:hover { background: rgba(255,255,255,0.12); transform: translateY(-1px); }
.city-item:active { transform: scale(0.98); }
.city-emoji { font-size: 30px; }
.city-info { display: flex; flex-direction: column; gap: 2px; }
.city-name { font-size: 15px; font-weight: 600; color: #FFF; }
.city-desc { font-size: 12px; color: rgba(200,200,200,0.5); }

.back-btn {
  width: 100%; margin-top: 14px; padding: 13px; border-radius: 14px;
  text-align: center; font-size: 14px;
  color: #8A847E; background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  cursor: pointer; transition: all 0.2s;
}
.back-btn:hover { background: rgba(255,255,255,0.1); }
.bottom-nav {
  position: fixed; bottom: 0; left: 0; right: 0;
  height: 52px;
  display: flex; align-items: flex-end; justify-content: center;
  gap: 56px; padding-bottom: 8px;
  z-index: 100; background: transparent;
}
.bnav-item {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: none; border: none; cursor: pointer;
  color: inherit; -webkit-tap-highlight-color: transparent;
  position: relative; padding: 2px;
}
.bnav-item .icon-wrap {
  width: 38px; height: 38px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(4px);
  border: 1.5px solid rgba(255,255,255,0.12);
  transition: all 0.2s;
}
.bnav-item:hover .icon-wrap {
  background: rgba(255,255,255,0.18);
  transform: scale(1.08);
}
.bnav-item:active .icon-wrap { transform: scale(0.92); }
.bnav-item.active .icon-wrap {
  background: rgba(255,255,255,0.22);
  border-color: rgba(255,255,255,0.25);
  animation: tab-bounce 0.35s cubic-bezier(0.25,0.46,0.45,0.94);
}
.bnav-item svg { width: 22px; height: 22px; image-rendering: pixelated; shape-rendering: crispEdges; }
.bnav-item .icon-outline { display: block; }
.bnav-item .icon-fill    { display: none; }
.bnav-item.active .icon-outline { display: none; }
.bnav-item.active .icon-fill    { display: block; }
.bnav-item .bnav-label {
  font-size: 10px; margin-top: 2px;
  opacity: 0.65; letter-spacing: 0.5px;
  transition: opacity 0.2s;
}
.bnav-item:hover .bnav-label { opacity: 0.9; }
.bnav-item.active .bnav-label { opacity: 1; font-weight: 500; }
@keyframes tab-bounce {
  0%   { transform: scale(1); }
  40%  { transform: scale(1.15); }
  100% { transform: scale(1); }
}

/* 白天 */
.day .bnav-item           { color: rgba(80,90,100,0.6); }
.day .bnav-item:hover     { color: rgba(50,60,70,0.9); }
.day .bnav-item.active    { color: rgba(45,80,60,0.95); }
.day .bnav-item .icon-wrap{ background: rgba(255,255,255,0.35); border-color: rgba(255,255,255,0.45); }
/* 傍晚 */
.evening .bnav-item       { color: rgba(120,100,80,0.65); }
.evening .bnav-item:hover { color: rgba(90,70,45,0.9); }
.evening .bnav-item.active{ color: rgba(140,95,55,0.95); }
.evening .bnav-item .icon-wrap{ background: rgba(255,255,255,0.3); border-color: rgba(255,255,255,0.4); }
/* 夜晚 */
.night .bnav-item         { color: rgba(200,210,220,0.5); }
.night .bnav-item:hover   { color: rgba(230,240,250,0.9); }
.night .bnav-item.active  { color: rgba(190,220,250,0.95); }
.night .bnav-item .icon-wrap{ background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.15); }

/* ═══════════ 个人中心面板 ═══════════ */
/* 背景遮罩 */
.profile-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.35);
  backdrop-filter: blur(6px);
  display: flex; align-items: flex-end; justify-content: center;
}
/* 面板主体 */
.profile-panel {
  width: 100%; max-height: 85vh; position: relative;
  background: rgba(30,30,35,0.88);
  backdrop-filter: blur(24px);
  border-radius: 24px 24px 0 0;
  padding: 20px 20px 28px;
  overflow-y: auto;
  color: #E8E2D8;
  font-family: 'PingFang SC','Microsoft YaHei',sans-serif;
}
.profile-panel::-webkit-scrollbar { width: 0; }

/* 关闭按钮 */
.panel-close {
  position: absolute; top: 14px; right: 18px;
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.08); color: rgba(200,200,200,0.6);
  cursor: pointer; transition: all 0.2s;
}
.panel-close:hover { background: rgba(255,255,255,0.15); color: white; }

/* 头像区 */
.panel-hero {
  display: flex; flex-direction: column; align-items: center;
  padding: 8px 0 16px;
}
.panel-avatar {
  width: 68px; height: 68px; border-radius: 50%;
  background: rgba(255,255,255,0.1); border: 2px solid rgba(255,255,255,0.12);
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: 700; color: #C8B8A8;
  margin-bottom: 10px;
}
.panel-name { font-size: 18px; font-weight: 600; color: #FFF; }
.panel-uid { font-size: 12px; color: rgba(200,200,200,0.5); margin-top: 2px; }
.panel-badge {
  margin-top: 6px; font-size: 11px; color: #C8B8A8;
  background: rgba(255,255,255,0.1); padding: 2px 10px; border-radius: 10px;
}

/* 微信状态 */
.status-tag {
  margin-top: 8px; padding: 3px 14px; border-radius: 12px;
  background: rgba(255,255,255,0.08); color: #B0A89E;
  font-size: 12px; border: 1px solid rgba(255,255,255,0.1);
  cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 4px;
}
.status-tag:hover { background: rgba(255,255,255,0.14); }

/* 状态选择器 */
.status-picker { padding-top: 14px; }
.status-custom {
  display: flex; gap: 8px; padding: 4px 0 12px; align-items: center;
}
.status-custom input {
  flex: 1; padding: 8px 14px; border-radius: 14px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
  color: #E8E2D8; font-size: 13px; outline: none;
}
.status-custom input::placeholder { color: #7A756E; }
.status-custom .quick-btn {
  flex-shrink: 0; padding: 6px 14px; border-radius: 14px;
  background: #8EA89A; color: white; font-size: 12px;
  border: none; cursor: pointer; transition: background 0.2s;
}
.status-custom .quick-btn:hover:not(:disabled) { background: #7A9A8C; }
.status-custom .quick-btn:disabled { background: #5A6A62; cursor: not-allowed; }
.status-grid {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;
  padding: 0 0 12px;
}
.status-item {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 8px 4px; border-radius: 12px;
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06);
  cursor: pointer; transition: all 0.2s; gap: 4px;
}
.status-item:hover { background: rgba(255,255,255,0.1); transform: translateY(-1px); }
.status-emoji { font-size: 22px; line-height: 1; }
.status-text { font-size: 11px; color: #C8C0B6; text-align: center; white-space: nowrap; }

/* 数据统计 */
.panel-stats {
  display: flex; align-items: center; justify-content: center;
  gap: 0; padding: 14px 0; margin-bottom: 6px;
  border-radius: 16px;
  background: rgba(255,255,255,0.06);
}
.pstat-item { flex: 1; text-align: center; cursor: pointer; }
.pstat-val { font-size: 22px; font-weight: 700; color: #C8B8A8; }
.pstat-lbl { font-size: 11px; color: rgba(200,200,200,0.5); margin-top: 3px; }
.pstat-divider { width: 1px; height: 32px; background: rgba(255,255,255,0.08); }

/* Section */
.panel-section { margin-bottom: 14px; }
.panel-sec-title {
  font-size: 11px; color: rgba(200,200,200,0.4); font-weight: 500;
  letter-spacing: 1px; text-transform: uppercase;
  margin-bottom: 8px; padding-left: 2px;
}

/* 情绪分布 */
.panel-dist {
  background: rgba(255,255,255,0.05); border-radius: 14px; padding: 12px;
  display: flex; flex-direction: column; gap: 8px;
}
.pdist-row { display: flex; align-items: center; gap: 8px; }
.pdist-emoji { font-size: 16px; width: 22px; text-align: center; }
.pdist-label { width: 36px; font-size: 13px; color: #D0C8C0; flex-shrink: 0; }
.pdist-track { flex: 1; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; }
.pdist-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #8EA89A, #A8C4B8); transition: width 0.8s ease; }
.pdist-pct { width: 34px; font-size: 11px; color: rgba(200,200,200,0.5); text-align: right; }

/* 成就 */
.panel-badges {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
}
.pbadge {
  background: rgba(255,255,255,0.05); border-radius: 12px; padding: 12px 6px 10px;
  text-align: center; opacity: 0.3; transition: all 0.3s; position: relative;
}
.pbadge.unlocked { opacity: 1; background: rgba(255,255,255,0.09); }
.pbadge-icon { font-size: 24px; margin-bottom: 3px; }
.pbadge-name { font-size: 11px; font-weight: 600; color: #E8E2D8; }
.pbadge-desc { font-size: 9px; color: rgba(200,200,200,0.4); margin-top: 1px; }
.pbadge-check { position: absolute; top: 4px; right: 6px; font-size: 10px; color: #8EA89A; font-weight: 700; }

/* ═══════════ 情绪日历 ═══════════ */
.mood-calendar { display: flex; flex-direction: column; gap: 16px; }
.cal-month { }
.cal-month-label { font-size: 18px; font-weight: 600; color: #E8E2D8; margin-bottom: 10px; letter-spacing: 1px; }
.cal-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}
.cal-day {
  display: flex; flex-direction: column; align-items: center;
  padding: 4px 2px;
  border-radius: 10px;
  transition: background 0.2s;
}
.cal-day:hover { background: rgba(255,255,255,0.05); }
.cal-day .cal-date {
  font-size: 11px; color: #7A756E; line-height: 1.3;
}
.cal-day.has-mood .cal-date {
  color: #E8E2D8; font-weight: 600;
}
.cal-day .cal-mood {
  font-size: 18px; line-height: 1.3;
  margin-top: 2px;
  display: block;
  width: 26px; height: 26px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.08);
  border-radius: 50%;
}

/* 菜单卡片 */
.panel-menu {
  background: rgba(255,255,255,0.05); border-radius: 14px; overflow: hidden;
}
.panel-setting-row {
  display: flex; align-items: center; gap: 8px; padding: 12px 14px;
}
.panel-setting-row span { font-size: 14px; color: #D0C8C0; white-space: nowrap; }
.panel-setting-row input {
  flex: 1; padding: 6px 10px; border: 1.5px solid rgba(255,255,255,0.1);
  border-radius: 8px; font-size: 13px; background: rgba(0,0,0,0.2);
  color: #E8E2D8; outline: none;
}
.panel-setting-row input:focus { border-color: #8EA89A; }
.panel-setting-row button {
  padding: 6px 14px; background: rgba(142,168,154,0.7); color: white;
  border-radius: 8px; font-size: 12px; white-space: nowrap; border: none; cursor: pointer;
}
.panel-menu-row {
  display: flex; align-items: center; gap: 10px; padding: 14px 14px;
  cursor: pointer; font-size: 14px; color: #D0C8C0;
  transition: background 0.2s;
}
.panel-menu-row:hover { background: rgba(255,255,255,0.06); }
.panel-menu-row .arrow { margin-left: auto; font-size: 18px; color: rgba(200,200,200,0.3); }

/* 退出 */
.panel-logout {
  width: 100%; padding: 13px; border-radius: 14px; text-align: center;
  font-size: 14px; color: #C06860;
  background: rgba(192,104,96,0.08); border: 1.5px solid rgba(192,104,96,0.15);
  margin-top: 4px; cursor: pointer; transition: all 0.2s; border: none;
}
.panel-logout:hover { background: rgba(192,104,96,0.15); }

/* 面板滑入动画 */
.panel-slide-enter-active, .panel-slide-leave-active { transition: opacity 0.3s; }
.panel-slide-enter-from, .panel-slide-leave-to { opacity: 0; }
.panel-slide-enter-active .profile-panel,
.panel-slide-leave-active .profile-panel { transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94); }
.panel-slide-enter-from .profile-panel { transform: translateY(100%); }
.panel-slide-leave-to .profile-panel { transform: translateY(100%); }

/* ═══════════ 情绪回顾面板 ═══════════ */
.trend-panel { padding-top: 14px; }
.trend-header { text-align: center; padding: 4px 0 10px; }
.trend-header h2 { margin: 0; font-size: 17px; color: #E8E2D8; }
.trend-header p { margin: 0; font-size: 11px; color: #8A847E; }

/* 时间标签 */
.trend-panel .tab-bar {
  display: flex; gap: 8px; padding: 0 0 10px;
}
.trend-panel .tab-bar button {
  padding: 5px 16px; border-radius: 14px;
  background: rgba(255,255,255,0.08); color: #9A948E; font-size: 12px;
  border: 1px solid rgba(255,255,255,0.08); transition: all 0.2s;
}
.trend-panel .tab-bar button.active { background: #8EA89A; color: white; border-color: #8EA89A; }

/* 统计卡片 */
.trend-panel .stats-row { display: flex; gap: 8px; margin-bottom: 10px; }
.trend-panel .stat-card {
  background: rgba(255,255,255,0.06); border-radius: 16px;
  backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.06);
}
.trend-panel .main-stat {
  flex: 1; padding: 16px 8px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 110px;
}
.trend-panel .score-wrap { position: relative; width: 70px; height: 70px; margin-bottom: 8px; }
.trend-panel .score-ring { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0.5; }
.trend-panel .main-score {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 700; letter-spacing: -1px; color: #B8DCC2;
}
.trend-panel .main-label { font-size: 11px; color: #7A756E; margin-top: 2px; }
.trend-panel .main-hint { font-size: 12px; margin-top: 2px; font-weight: 600; letter-spacing: 0.5px; color: #C4BEA8; }
.trend-panel .side-stats { display: flex; flex-direction: column; gap: 8px; flex: 0 0 82px; }
.trend-panel .side-card { padding: 10px 6px; text-align: center; flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; }
.trend-panel .side-val { font-size: 22px; font-weight: 700; color: #B8DCC2; line-height: 1.1; }
.trend-panel .side-emoji { font-size: 26px; margin-bottom: 2px; }
.trend-panel .side-label { font-size: 10px; color: #7A756E; margin-top: 3px; }

/* 通用卡片 */
.trend-panel .card {
  background: rgba(255,255,255,0.06); border-radius: 16px;
  backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 10px; padding: 14px;
}
.trend-panel .card-title { font-size: 13px; font-weight: 600; color: #E8E2D8; margin-bottom: 12px; }

/* 折线图 */
.trend-panel .line-chart-wrap { position: relative; }
.trend-panel .line-chart { width: 100%; height: 90px; }
.trend-panel .x-labels {
  display: flex; justify-content: space-between;
  font-size: 10px; color: #8A847E; margin-top: 3px; padding: 0 8px;
}

/* 情绪分布 */
.trend-panel .dist-list { display: flex; flex-direction: column; gap: 8px; }
.trend-panel .dist-row { display: flex; align-items: center; gap: 8px; }
.trend-panel .dist-emoji { font-size: 16px; width: 22px; text-align: center; }
.trend-panel .dist-label { width: 36px; font-size: 12px; color: #C8C0B6; flex-shrink: 0; }
.trend-panel .dist-track { flex: 1; height: 7px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; }
.trend-panel .dist-fill { height: 100%; border-radius: 4px; transition: width 0.8s ease; }
.trend-panel .dist-pct { width: 34px; font-size: 11px; color: #8A847E; text-align: right; }

/* AI 洞察 */
.trend-panel .insight-content { min-height: 40px; }
.trend-panel .insight-loading { display: flex; gap: 5px; padding: 6px 0; }
.trend-panel .insight-loading .dot {
  width: 8px; height: 8px; border-radius: 50%; background: #8EA89A;
  animation: bounce 1.2s infinite both;
}
.trend-panel .insight-loading .dot:nth-child(2) { animation-delay: 0.2s; }
.trend-panel .insight-loading .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0);opacity:0.4} 40%{transform:translateY(-5px);opacity:1} }
.trend-panel .insight-text { font-size: 13px; line-height: 1.7; color: #B8B0A6; margin: 0; }
.trend-panel .refresh-btn {
  margin-top: 8px; padding: 5px 12px; border-radius: 10px;
  background: rgba(255,255,255,0.08); color: #8A847E; font-size: 11px;
  display: inline-flex; align-items: center; border: none; cursor: pointer;
  transition: background 0.2s;
}
.trend-panel .refresh-btn:hover:not(:disabled) { background: rgba(255,255,255,0.14); }
.trend-panel .refresh-btn:disabled { opacity: 0.4; }

/* 空状态 */
.trend-panel .empty-state { text-align: center; padding: 32px 16px; }
.trend-panel .empty-icon { font-size: 40px; margin-bottom: 10px; }
.trend-panel .empty-state p { font-size: 14px; color: #B8B0A6; margin: 0; }
.trend-panel .empty-hint { font-size: 12px; color: #8A847E; margin-top: 6px !important; }
.trend-panel .go-chat-btn {
  margin-top: 16px; padding: 8px 24px;
  background: #8EA89A; color: white; border-radius: 18px; font-size: 13px;
  border: none; cursor: pointer; transition: background 0.2s;
}
.trend-panel .go-chat-btn:hover { background: #7A9A8C; }

/* ══════════ 聊天面板 AI logo ══════════ */
.ai-logo {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.welcome-avatar .ai-logo {
  width: 40px;
  height: 40px;
}

.msg-avatar .ai-logo {
  width: 28px;
  height: 28px;
}

/* ═══════════ 主题文字色 ═══════════ */
.day .greeting-text,.day .greeting-sub,.day .clock { color: #FFF; }
.day .weather-float { background: rgba(255,255,255,0.25); color: #FFF; }
.evening .greeting-text,.evening .greeting-sub,.evening .clock { color: #FFF; }
.evening .weather-float { background: rgba(255,255,255,0.2); color: #FFF; }
.night .greeting-text,.night .greeting-sub,.night .clock { color: #F0E8E0; }
.night .weather-float { background: rgba(0,0,0,0.35); color: #C8D4E0; }

/* ═══════════ 响应式 — 电脑端（≥768px）══════════ */
@media (min-width: 768px) {
  /* 全屏布局 */
  .room { max-width: 100%; }
  .bg-wrap { inset: 0; }
  .room-bg { object-fit: cover; object-position: center; }

  /* 电脑端热区适配（16:9 横屏图） */
  .zone-monitor { top: 40%; left: 42%; width: 10%; height: 14%; }
  .zone-bed     { top: 60%; left: 20%; width: 20%; height: 38%; transform: rotate(-44deg); }

  /* 床上文字适配 */
  .bed-label {
    transform: translate(-50%, -50%) rotate(44deg);
    font-size: 16px;
  }

  /* 顶部信息栏放大 */
  .top-bar { top: 24px; }
  .clock        { font-size: 16px; }
  .greeting-text{ font-size: 22px; }
  .greeting-sub { font-size: 14px; }

  /* 天气浮层 */
  .weather-float { top: 12%; left: 4%; font-size: 14px; padding: 6px 16px; }

  /* 音乐按钮 */
  .music-btn { bottom: 70px; right: 30px; width: 38px; height: 38px; }

  /* 底部导航居中 */
  .bottom-nav { max-width: 100%; left: 0; transform: none; }
  /* 电脑端面板居中 */
  .profile-overlay { align-items: center; }
  .profile-panel {
    width: 480px; max-height: 80vh;
    border-radius: 24px;
    padding: 24px 28px 32px;
  }
  /* 情绪回顾面板电脑端 */
  .trend-panel .stats-row { padding: 0; }
  .trend-panel .side-stats { flex: 0 0 100px; }
  .trend-panel .card { margin-bottom: 12px; }

  /* 聊天面板电脑端 */
  .chat-panel .chat-messages { padding: 24px 24px 16px; }
  .chat-panel .bubble-wrap { max-width: 60%; }
  .chat-panel .welcome-bubble { max-width: 60%; }
  .chat-panel .quick-scroll { padding: 0 24px; }
  .chat-panel .input-bar { padding: 12px 24px; }

  /* 状态选择器电脑端 */
  .status-grid { grid-template-columns: repeat(6, 1fr); gap: 10px; }
  .status-item { padding: 10px 6px; }
}

/* ═══════════ 聊天面板 ═══════════ */
.chat-panel { display: flex; flex-direction: column; padding: 0 !important; overflow: hidden !important; }

/* 顶部 */
.chat-panel .chat-header {
  display: flex; align-items: center; justify-content: center;
  padding: 12px 16px; padding-top: max(12px, env(safe-area-inset-top));
  background: rgba(25,25,30,0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;
}
.chat-panel .header-center { display: flex; align-items: center; gap: 10px; }
.chat-panel .ai-avatar { font-size: 28px; }
.chat-panel .ai-name { font-size: 15px; font-weight: 600; color: #E8E2D8; }
.chat-panel .ai-status {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #8A847E; margin-top: 1px;
}
.chat-panel .status-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #82C4A0;
  transition: background 0.3s;
}
.chat-panel .status-dot.thinking { background: #E8C468; animation: pulse-dot 1s infinite; }
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* 消息区域 */
.chat-panel .chat-messages {
  flex: 1; overflow-y: auto; padding: 20px 16px 12px;
  scroll-behavior: smooth; background: transparent;
}
.chat-panel .chat-messages::-webkit-scrollbar { width: 0; }

/* 欢迎消息 */
.chat-panel .welcome-wrap { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 20px; }
.chat-panel .welcome-avatar { font-size: 26px; margin-top: 2px; }
.chat-panel .welcome-bubble {
  background: rgba(255,255,255,0.08);
  border-radius: 4px 16px 16px 16px;
  padding: 12px 16px; max-width: 75%;
  border: 1px solid rgba(255,255,255,0.06);
}
.chat-panel .welcome-bubble p { margin: 0; font-size: 14px; line-height: 1.6; color: #E0D8CE; }
.chat-panel .welcome-bubble p + p { margin-top: 6px; }

/* 消息行 */
.chat-panel .msg-row { display: flex; align-items: flex-end; gap: 8px; margin-bottom: 16px; }
.chat-panel .msg-row.user { flex-direction: row-reverse; }
.chat-panel .msg-avatar { font-size: 24px; flex-shrink: 0; margin-bottom: 4px; }

.chat-panel .bubble-wrap { display: flex; flex-direction: column; max-width: 72%; }
.chat-panel .msg-row.user .bubble-wrap { align-items: flex-end; }
.chat-panel .msg-row.assistant .bubble-wrap { align-items: flex-start; }

/* 情绪标签 */
.chat-panel .emotion-tag {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; padding: 3px 10px; border-radius: 10px;
  background: rgba(255,255,255,0.1); color: #B8B0A6;
  margin-bottom: 4px;
}

/* 气泡 */
.chat-panel .bubble {
  padding: 11px 15px; border-radius: 16px;
  font-size: 14px; line-height: 1.65; word-break: break-all;
}
.chat-panel .msg-row.user .bubble {
  background: #8EA89A; color: white;
  border-bottom-right-radius: 4px;
}
.chat-panel .msg-row.assistant .bubble {
  background: rgba(255,255,255,0.08); color: #E0D8CE;
  border-bottom-left-radius: 4px;
  border: 1px solid rgba(255,255,255,0.06);
}

/* TTS 按钮 */
.chat-panel .tts-btn {
  margin-top: 4px; align-self: flex-start;
  padding: 3px 8px; border-radius: 8px;
  background: rgba(255,255,255,0.06); color: #8A847E;
  font-size: 12px; display: flex; align-items: center; gap: 3px;
  transition: all 0.2s; border: none; cursor: pointer;
}
.chat-panel .tts-btn:hover, .chat-panel .tts-btn.playing { background: rgba(255,255,255,0.14); color: #C8C0B6; }

/* 加载气泡 */
.chat-panel .typing-bubble { display: flex; gap: 5px; padding: 14px 18px; }
.chat-panel .typing-bubble .dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #8A847E; animation: bounce 1.2s infinite both;
}
.chat-panel .typing-bubble .dot:nth-child(2) { animation-delay: 0.15s; }
.chat-panel .typing-bubble .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-6px)} }

/* 快捷按钮 */
.chat-panel .quick-wrap {
  flex-shrink: 0; padding: 8px 0 6px;
  border-top: 1px solid rgba(255,255,255,0.06);
  background: rgba(25,25,30,0.7);
}
.chat-panel .quick-scroll {
  display: flex; gap: 6px; padding: 0 16px; overflow-x: auto;
}
.chat-panel .quick-scroll::-webkit-scrollbar { display: none; }
.chat-panel .quick-btn {
  white-space: nowrap; flex-shrink: 0;
  padding: 6px 12px; border-radius: 14px;
  background: rgba(255,255,255,0.08); color: #B8B0A6; font-size: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  transition: all 0.2s; display: flex; align-items: center; gap: 4px;
  cursor: pointer;
}
.chat-panel .quick-btn:hover { background: rgba(255,255,255,0.14); border-color: rgba(255,255,255,0.14); }

/* 输入栏 */
.chat-panel .input-bar {
  flex-shrink: 0; display: flex; align-items: center; gap: 8px;
  padding: 10px 16px; padding-bottom: max(10px, env(safe-area-inset-bottom));
  background: rgba(25,25,30,0.9);
  border-top: 1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
}
.chat-panel .input-wrap {
  flex: 1; background: rgba(255,255,255,0.08); border-radius: 22px;
  border: 1.5px solid rgba(255,255,255,0.1);
  transition: border-color 0.2s;
  overflow: hidden;
}
.chat-panel .input-wrap:focus-within { border-color: rgba(142,168,154,0.5); }
.chat-panel .input-wrap input {
  width: 100%; padding: 10px 16px;
  font-size: 14px; background: transparent; color: #E8E2D8;
  outline: none; border: none;
}
.chat-panel .input-wrap input::placeholder { color: #6A645E; }

.chat-panel .voice-btn {
  width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.08); color: #8EA89A;
  border: 1.5px solid rgba(255,255,255,0.1); transition: all 0.2s;
  cursor: pointer;
}
.chat-panel .voice-btn:hover { background: rgba(255,255,255,0.14); }
.chat-panel .voice-btn.recording {
  background: rgba(212,119,106,0.15); color: #D4776A; border-color: #D4776A;
  animation: pulse-rec 1s infinite;
}
.chat-panel .rec-wave {
  display: block; width: 18px; height: 18px;
  border: 2.5px solid #D4776A; border-radius: 50%;
  animation: wave 1s infinite;
}
@keyframes wave { 0%{transform:scale(0.8);opacity:1} 100%{transform:scale(1.4);opacity:0} }
@keyframes pulse-rec { 0%,100%{transform:scale(1)} 50%{transform:scale(1.05)} }

.chat-panel .send-btn {
  width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: #8EA89A; color: white; transition: all 0.2s;
  border: none; cursor: pointer;
}
.chat-panel .send-btn:hover:not(:disabled) { background: #7A9A8C; transform: scale(1.05); }
.chat-panel .send-btn:disabled { background: #5A7064; }

/* 录音提示 */
.chat-panel .recording-hint {
  position: absolute; bottom: 90px; left: 50%; transform: translateX(-50%);
  background: rgba(50,45,42,0.85); color: white; padding: 8px 20px;
  border-radius: 20px; font-size: 13px; display: flex; align-items: center; gap: 8px;
  backdrop-filter: blur(8px); z-index: 10;
  pointer-events: none;
}
.chat-panel .rec-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #D4776A;
  animation: blink-dot 1s infinite;
}
@keyframes blink-dot { 0%,100%{opacity:1} 50%{opacity:0.3} }
.hint-fade-enter-active, .hint-fade-leave-active { transition: opacity 0.3s; }
.hint-fade-enter-from, .hint-fade-leave-to { opacity: 0; }
</style>
