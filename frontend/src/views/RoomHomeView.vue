<template>
  <div class="room" :class="timeOfDay">

    <!-- ══ 欢迎遮罩：点击任意处进入 ══ -->
    <Transition name="splash-fade">
      <div v-if="showSplash" class="splash" @click="enterApp">
        <div class="splash-logo">
          <span>咕哝</span>
          <span class="splash-version">V3.2</span>
        </div>
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
    <!-- 复访引导：每日仪式 + 首次使用提示 -->
    <div class="engagement-stack" v-if="!showSplash">
      <section class="daily-ritual-card">
        <div class="ritual-kicker">今日咕哝</div>
        <div class="ritual-title">{{ dailyRitual.title }}</div>
        <p class="ritual-copy">{{ dailyRitual.copy }}</p>
        <button class="ritual-action" @click="openDailyRitualAction">
          {{ dailyRitual.actionText }}
        </button>
      </section>

      <section class="first-run-guide" v-if="showFirstRunGuide">
        <button class="guide-close" @click="dismissFirstRunGuide" aria-label="关闭新手引导">×</button>
        <div class="guide-title">第一次来这里，可以这样开始</div>
        <ol class="guide-steps">
          <li>点电脑，说一句今天的感受</li>
          <li>看报告，了解最近的情绪变化</li>
          <li>进树洞，看看有没有人和你一样</li>
        </ol>
        <button class="guide-primary" @click="goToChat()">先说一句 →</button>
      </section>
    </div>
    <!-- 全局音乐开关 -->
    <button class="global-music-btn" @click="toggleMusic" :title="musicOn ? '关闭背景音乐' : '开启背景音乐'">
      <span v-if="musicOn">🔊</span>
      <span v-else>🔇</span>
    </button>

    <!-- 窗外天气浮层 -->
    <div class="weather-float" @click="refreshWeather">
      <span>{{ weatherEmoji }}</span>
      <span>{{ temperature }}°C</span>
    </div>

    <!-- 音乐推荐按钮 -->
    <!-- 已改为热区形式，见下方 zone-speaker -->

    <!-- 音乐切换按钮（隐藏，功能移至面板内） -->

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

    <!-- 交互热区 — 音响1（音乐推荐） -->
    <div class="hot-zone zone-speaker zone-speaker-left" @click="openMusicPanel">
      <div class="speaker-notes">
        <span class="note n1">🎵</span>
        <span class="note n2">🎶</span>
        <span class="note n3">♪</span>
        <span class="note n4">🎵</span>
        <span class="note n5">♫</span>
      </div>
    </div>

    <!-- 交互热区 — 音响2（音乐推荐） -->
    <div class="hot-zone zone-speaker zone-speaker-right" @click="openMusicPanel">
      <div class="speaker-notes">
        <span class="note n1">🎶</span>
        <span class="note n2">♫</span>
        <span class="note n3">🎵</span>
        <span class="note n4">♪</span>
        <span class="note n5">🎶</span>
      </div>
    </div>

    <!-- 小工具热区 — 桌面物品（治愈+娱乐） -->
    <div class="mini-tools-bar">
      <div class="mini-tool-item" @click="openMiniApp('air')">
        <span class="mini-tool-emoji">❄️</span>
        <span class="mini-tool-name">小空调</span>
      </div>
      <div class="mini-tool-item" @click="openMiniApp('itv')">
        <span class="mini-tool-emoji">📺</span>
        <span class="mini-tool-name">小电视</span>
      </div>
    </div>

    <!-- 底部导航 -->
    <nav class="bottom-nav">
      <button class="bnav-item" @click="goToChat">
        <div class="icon-wrap">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <span class="bnav-label">倾诉</span>
      </button>
      <button class="bnav-item" @click="showHealingPanel = true">
        <div class="icon-wrap">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
        </div>
        <span class="bnav-label">治愈</span>
      </button>
      <button class="bnav-item" @click="showTreeHolePanel = true">
        <div class="icon-wrap">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
            <line x1="9" y1="9" x2="9.01" y2="9"/>
            <line x1="15" y1="9" x2="15.01" y2="9"/>
          </svg>
        </div>
        <span class="bnav-label">树洞</span>
      </button>
      <button class="bnav-item" @click="showReportPanel = true">
        <div class="icon-wrap">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
        </div>
        <span class="bnav-label">报告</span>
      </button>
      <button class="bnav-item" @click="goProfile">
        <div class="icon-wrap">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
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
            <span v-if="userStore.isAdmin" class="panel-badge">教师</span>
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
              <div
                class="pdist-row" v-for="(count, label) in distribution" :key="label"
                :class="{ 'is-top': topMoodLabels.includes(label) }"
                @mouseenter="showTooltip(label)" @mouseleave="hideTooltip"
              >
                <span class="pdist-emoji">{{ getEmoji(label) }}</span>
                <span class="pdist-label">{{ label }}</span>
                <div class="pdist-track">
                  <div class="pdist-fill" :style="{ width: getPercent(count)+'%', background: getMoodColor(label) }"></div>
                </div>
                <span class="pdist-pct">{{ getPercent(count) }}%</span>
                <!-- 自定义tooltip -->
                <Transition name="tip-fade">
                  <div class="pdist-tooltip" v-if="hoveredMood === label">
                    {{ moodJudgeNote[label] }}
                    <div class="pdist-tooltip-arrow"></div>
                  </div>
                </Transition>
              </div>
              <!-- 占比最大时的安慰建议 -->
              <div class="pdist-comfort" v-for="(msg, i) in topMoodComforts" :key="i">{{ msg }}</div>
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

          <!-- 账号管理 -->
          <div class="panel-section">
            <div class="panel-sec-title">账号管理</div>
            <div class="panel-menu">
              <div class="panel-setting-row">
                <span>🔑 修改密码</span>
                <button @click="showPwdModal = true">修改</button>
              </div>
            </div>
          </div>

          <!-- 管理员 -->
          <div class="panel-section" v-if="userStore.isAdmin">
            <div class="panel-sec-title">系统</div>
            <div class="panel-menu">
              <div class="panel-menu-row" @click="router.push('/admin'); showProfilePanel = false">
                ⚙️ 教师端 <span class="arrow">›</span>
              </div>
            </div>
          </div>

          <!-- 退出 -->
          <button class="panel-logout" @click="handleLogout">退出登录</button>
        </div>
      </div>
    </Transition>

    <!-- ══ 修改密码弹窗 ══ -->
    <div class="pwd-modal-overlay" v-if="showPwdModal" @click.self="showPwdModal = false">
      <div class="pwd-modal-card">
        <h4>修改密码</h4>
        <input v-model="oldPwd" type="password" placeholder="请输入旧密码" />
        <input v-model="newPwd1" type="password" placeholder="请输入新密码（至少6位）" />
        <input v-model="newPwd2" type="password" placeholder="请再次输入新密码" />
        <div class="pwd-modal-btns">
          <button class="pwd-modal-cancel" @click="showPwdModal = false">取消</button>
          <button class="pwd-modal-confirm" @click="handleChangePwd">确认修改</button>
        </div>
        <p v-if="pwdMsg" :class="['pwd-modal-msg', pwdOk ? 'success' : 'error']">{{ pwdMsg }}</p>
      </div>
    </div>

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

    <!-- ══ 西安地铁转场动画 ══ -->
    <Transition name="transition-fade">
      <div v-if="showXianTransition" class="metro-transition" :class="`phase-${xianPhase}`">
        <div class="metro-bg">
          <img src="/images/xian-metro.jpg" alt="西安地铁" />
          <div class="metro-window metro-window-left"></div>
          <div class="metro-window metro-window-right"></div>
        </div>
        <div class="speed-lines">
          <div class="sl-line" v-for="n in 12" :key="n" :style="{ animationDelay: `${n * 0.15}s`, top: `${8 + (n * 7) % 84}%` }"></div>
        </div>
        <div class="metro-loading">
          <div class="ml-train">🚇</div>
          <p class="ml-text">正在前往西安</p>
          <div class="ml-track">
            <div class="ml-progress"></div>
          </div>
        </div>
        <div class="metro-blur-overlay"></div>
        <div class="metro-white-overlay"></div>
      </div>
    </Transition>

    <!-- ══ 西安城市探索 - 全屏热区 + 弹窗交互 ══ -->
    <Transition name="xian-fade">
      <div v-if="showXianPanel" class="xian-fullscreen">
        <!-- 全屏西安场景图 -->
        <div class="xian-bg-wrap">
          <img src="/images/xian.png" alt="西安古城" class="xian-bg-img" />
          <div class="xian-bg-vignette"></div>
        </div>

        <!-- 顶部导航栏 -->
        <div class="xian-top-bar">
          <button class="xian-back-btn" @click="closeXianPanel(); showCityPanel = true">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            <span class="back-home-text">回家</span>
          </button>
          <span class="xian-top-label">西安 · 皮影制作</span>
          <div class="xian-top-spacer"></div>
        </div>

        <!-- 单个交互热区（弹窗未打开时显示） -->
        <div v-if="!showPuppetPopup" class="xian-hotspot" @click="startPuppetMaking">
          <div class="hs-outer-ring"></div>
          <div class="hs-inner">
            <span class="hs-emoji">🎭</span>
          </div>
          <span class="hs-label">探索皮影制作</span>
          <p class="hs-sub">点击此处开始</p>
        </div>

        <!-- 视频播放热区 -->
        <div v-if="!showPuppetPopup && !showVideoPlayer" class="xian-hotspot xian-video-hotspot" @click="openVideoPlayer">
          <div class="hs-outer-ring"></div>
          <div class="hs-inner">
            <span class="hs-emoji">🎬</span>
          </div>
          <span class="hs-label">观看皮影戏</span>
          <p class="hs-sub">点击播放视频</p>
        </div>

        <!-- 皮影制作弹窗 -->
        <Transition name="popup-scale">
          <div v-if="showPuppetPopup" class="puppet-popup-overlay">
            <div class="puppet-popup">
              <!-- 弹窗头部：步骤圆点 + 关闭按钮 -->
              <div class="pp-header">
                <div class="pp-step-dots">
                  <span
                    v-for="s in 7"
                    :key="s"
                    class="pp-dot"
                    :class="{ active: shadowPuppetStep >= s, current: shadowPuppetStep === s }"
                  ></span>
                </div>
                <button class="pp-close" @click="closePuppetPopup">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>

              <!-- 步骤内容 (1-7) -->
              <div v-if="shadowPuppetStep >= 1 && shadowPuppetStep <= 7" class="pp-body">
                <div class="pp-visual" :class="currentStepData?.animClass">
                  <span class="pp-emoji">{{ currentStepData?.emoji }}</span>
                </div>
                <div class="pp-num">步骤 {{ currentStepData?.id }} / 7</div>
                <h3 class="pp-step-title">{{ currentStepData?.title }}</h3>
                <p class="pp-desc">{{ currentStepData?.desc }}</p>
                <p class="pp-detail">{{ currentStepData?.detail }}</p>
              </div>

              <!-- 完成内容 -->
              <div v-if="shadowPuppetStep === 8" class="pp-body pp-done-body">
                <div class="xsc-puppet-wrap">
                  <svg viewBox="0 0 120 200" class="xsc-puppet-svg">
                    <circle cx="60" cy="35" r="18" fill="none" stroke="#C4A35A" stroke-width="2"/>
                    <ellipse cx="60" cy="38" rx="12" ry="8" fill="rgba(196,163,90,0.15)" stroke="rgba(196,163,90,0.3)" stroke-width="1"/>
                    <path d="M42 28 Q50 12 60 10 Q70 12 78 28" fill="none" stroke="#D4B76A" stroke-width="1.5"/>
                    <path d="M45 26 L60 6 L75 26" fill="none" stroke="#C4A35A" stroke-width="1" stroke-dasharray="3,3"/>
                    <circle cx="54" cy="33" r="2.5" fill="#C4A35A" opacity="0.6"/>
                    <circle cx="66" cy="33" r="2.5" fill="#C4A35A" opacity="0.6"/>
                    <rect x="42" y="55" width="36" height="55" rx="8" fill="none" stroke="#C4A35A" stroke-width="2"/>
                    <path d="M46 60 Q60 68 74 60" fill="none" stroke="#D4B76A" stroke-width="1" stroke-dasharray="2,4"/>
                    <path d="M48 80 Q60 86 72 80" fill="none" stroke="rgba(196,163,90,0.35)" stroke-width="0.8" stroke-dasharray="1,5"/>
                    <line x1="46" y1="90" x2="74" y2="90" stroke="rgba(196,163,90,0.2)" stroke-width="0.5"/>
                    <line x1="48" y1="95" x2="72" y2="95" stroke="rgba(196,163,90,0.2)" stroke-width="0.5"/>
                    <path d="M42 62 Q28 60 22 45" fill="none" stroke="#C4A35A" stroke-width="2" stroke-linecap="round"/>
                    <circle cx="22" cy="45" r="4" fill="none" stroke="#D4B76A" stroke-width="1"/>
                    <path d="M78 62 Q92 60 98 45" fill="none" stroke="#C4A35A" stroke-width="2" stroke-linecap="round"/>
                    <circle cx="98" cy="45" r="4" fill="none" stroke="#D4B76A" stroke-width="1"/>
                    <path d="M48 110 L42 165" fill="none" stroke="#C4A35A" stroke-width="2" stroke-linecap="round"/>
                    <path d="M72 110 L78 165" fill="none" stroke="#C4A35A" stroke-width="2" stroke-linecap="round"/>
                    <line x1="60" y1="10" x2="60" y2="-8" stroke="#8A847E" stroke-width="1.5" stroke-linecap="round"/>
                    <circle cx="60" cy="-10" r="3" fill="#8A847E"/>
                    <line x1="22" y1="45" x2="18" y2="38" stroke="#8A847E" stroke-width="1" stroke-linecap="round"/>
                    <circle cx="18" cy="37" r="2" fill="#8A847E"/>
                    <line x1="98" y1="45" x2="102" y2="38" stroke="#8A847E" stroke-width="1" stroke-linecap="round"/>
                    <circle cx="102" cy="37" r="2" fill="#8A847E"/>
                  </svg>
                </div>
                <h3 class="pp-step-title">恭喜！皮影制作完成</h3>
                <p class="pp-detail">你完成了一盏传统陕西皮影的制作，这是中华民族千年智慧的结晶。</p>
              </div>

              <!-- 底部操作（步骤中） -->
              <div class="pp-footer" v-if="shadowPuppetStep >= 1 && shadowPuppetStep <= 7">
                <div class="pp-progress-bar">
                  <div class="pp-track">
                    <div class="pp-fill" :style="{ width: (shadowPuppetStep / 7 * 100) + '%' }"></div>
                  </div>
                </div>
                <div class="pp-btns">
                  <button v-if="shadowPuppetStep > 1" class="pp-btn-prev" @click="prevStep">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
                    <span>上一步</span>
                  </button>
                  <button class="pp-btn" @click="nextStep">
                    <span>{{ shadowPuppetStep < 7 ? '下一步' : '完成制作' }}</span>
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  </button>
                </div>
              </div>

              <!-- 底部操作（完成时） -->
              <div class="pp-footer" v-if="shadowPuppetStep === 8">
                <div class="pp-actions">
                  <button class="pp-btn-ghost" @click="resetPuppet">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
                    <span>重新制作</span>
                  </button>
                  <button class="pp-btn-main" @click="closePuppetPopup">完成</button>
                </div>
              </div>
            </div>
          </div>
        </Transition>

        <!-- 视频播放弹窗 -->
        <Transition name="popup-scale">
          <div v-if="showVideoPlayer" class="video-player-overlay" @click.self="closeVideoPlayer">
            <div class="video-player-card">
              <div class="vp-header">
                <span class="vp-title">皮影戏 · 光影之美</span>
                <button class="vp-close" @click="closeVideoPlayer">✕</button>
              </div>
              <div class="vp-body">
                <video
                  ref="videoRef"
                  class="vp-video"
                  :src="videoSrc"
                  controls
                  autoplay
                  playsinline
                  webkit-playsinline
                  @ended="onVideoEnded"
                ></video>
              </div>
            </div>
          </div>
        </Transition>

      </div>
    </Transition>

    <!-- ══ 洛阳地铁转场动画 ══ -->
    <Transition name="transition-fade">
      <div v-if="showLuoyangTransition" class="metro-transition" :class="`phase-${luoyangPhase}`">
        <!-- 地铁车厢背景 -->
        <div class="metro-bg">
          <img src="/images/luoyang-metro.jpg" alt="洛阳地铁" />
          <!-- 两侧窗外运动模糊 -->
          <div class="metro-window metro-window-left"></div>
          <div class="metro-window metro-window-right"></div>
        </div>

        <!-- 速度线（运动感） -->
        <div class="speed-lines">
          <div class="sl-line" v-for="n in 12" :key="n" :style="{ animationDelay: `${n * 0.15}s`, top: `${8 + (n * 7) % 84}%` }"></div>
        </div>

        <!-- 加载文字 -->
        <div class="metro-loading">
          <div class="ml-train">🚇</div>
          <p class="ml-text">正在前往洛阳</p>
          <div class="ml-track">
            <div class="ml-progress"></div>
          </div>
        </div>

        <!-- 整体模糊遮罩 -->
        <div class="metro-blur-overlay"></div>

        <!-- 白屏过渡 -->
        <div class="metro-white-overlay"></div>
      </div>
    </Transition>

    <!-- ══ 洛阳城市探索 - 全屏热区 + 弹窗交互 ══ -->
    <Transition name="xian-fade">
      <div v-if="showLuoyangPanel" class="xian-fullscreen luoyang-fullscreen">
        <!-- 全屏洛阳场景图 -->
        <div class="xian-bg-wrap">
          <img src="/images/luoyang.png" alt="洛阳古城" class="xian-bg-img" />
          <div class="xian-bg-vignette"></div>
        </div>

        <!-- 顶部返回栏 -->
        <div class="xian-top-bar">
          <button class="xian-back-btn" @click="closeLuoyangPanel(); showCityPanel = true">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M15 18l-6-6 6-6"/></svg>
            <span class="back-home-text">回家</span>
          </button>
          <span class="xian-top-label">洛阳 · 非遗拓印</span>
          <div class="xian-top-spacer"></div>
        </div>

        <!-- 拓印制作热区 -->
        <div v-if="!showRubbingPopup && !showLuoyangVideoPlayer" class="xian-hotspot" @click="startRubbing">
          <div class="hs-outer-ring"></div>
          <div class="hs-inner">
            <span class="hs-emoji">🖌️</span>
          </div>
          <span class="hs-label">体验非遗拓印</span>
          <p class="hs-sub">点击此处开始</p>
        </div>

        <!-- 视频播放热区 -->
        <div v-if="!showRubbingPopup && !showLuoyangVideoPlayer" class="xian-hotspot luoyang-video-hotspot" @click="openLuoyangVideoPlayer">
          <div class="hs-outer-ring"></div>
          <div class="hs-inner">
            <span class="hs-emoji">🎬</span>
          </div>
          <span class="hs-label">观看拓印技艺</span>
          <p class="hs-sub">点击播放视频</p>
        </div>

        <!-- 拓印制作弹窗 -->
        <Transition name="popup-scale">
          <div v-if="showRubbingPopup" class="puppet-popup-overlay" @click.self="closeRubbingPopup">
            <div class="puppet-popup">
              <!-- 弹窗头部：步骤圆点 + 关闭按钮 -->
              <div class="pp-header">
                <div class="pp-step-dots">
                  <span
                    v-for="s in 6"
                    :key="s"
                    class="pp-dot"
                    :class="{ active: rubbingStep >= s, current: rubbingStep === s }"
                  ></span>
                </div>
                <button class="pp-close" @click="closeRubbingPopup">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>

              <!-- 步骤内容 (1-6) -->
              <div v-if="rubbingStep >= 1 && rubbingStep <= 6" class="pp-body">
                <div class="pp-visual">
                  <span class="pp-emoji">{{ rubbingSteps[rubbingStep - 1].emoji }}</span>
                </div>
                <div class="pp-num">步骤 {{ rubbingSteps[rubbingStep - 1].id }} / 6</div>
                <h3 class="pp-step-title">{{ rubbingSteps[rubbingStep - 1].title }}</h3>
                <p class="pp-desc">{{ rubbingSteps[rubbingStep - 1].desc }}</p>
                <p class="pp-detail">{{ rubbingSteps[rubbingStep - 1].detail }}</p>
              </div>

              <!-- 完成内容 -->
              <div v-if="rubbingStep === 7" class="pp-body pp-done-body">
                <div class="xsc-puppet-wrap">
                  <svg viewBox="0 0 200 260" class="xsc-puppet-svg" style="width:120px;height:156px;">
                    <rect x="30" y="20" width="140" height="200" rx="4" fill="none" stroke="#C4A35A" stroke-width="2"/>
                    <line x1="30" y1="60" x2="170" y2="60" stroke="#C4A35A" stroke-width="1.5"/>
                    <line x1="30" y1="100" x2="170" y2="100" stroke="#C4A35A" stroke-width="1.5"/>
                    <line x1="30" y1="140" x2="170" y2="140" stroke="#C4A35A" stroke-width="1.5"/>
                    <line x1="30" y1="180" x2="170" y2="180" stroke="#C4A35A" stroke-width="1.5"/>
                    <text x="100" y="45" text-anchor="middle" fill="#C4A35A" font-size="14" font-family="serif">洛阳碑刻</text>
                    <text x="100" y="85" text-anchor="middle" fill="#C4A35A" font-size="10" font-family="serif">千年文脉</text>
                    <text x="100" y="125" text-anchor="middle" fill="#C4A35A" font-size="10" font-family="serif">一纸传薪</text>
                    <text x="100" y="165" text-anchor="middle" fill="#C4A35A" font-size="10" font-family="serif">非遗瑰宝</text>
                    <text x="100" y="205" text-anchor="middle" fill="#C4A35A" font-size="10" font-family="serif">匠心传承</text>
                  </svg>
                </div>
                <h3 class="pp-step-title">恭喜！拓印完成</h3>
                <p class="pp-detail">你完成了非遗拓印的全部 6 个步骤，感受了千年碑刻的传续技艺。</p>
              </div>

              <!-- 底部操作（步骤中） -->
              <div class="pp-footer" v-if="rubbingStep >= 1 && rubbingStep <= 6">
                <div class="pp-progress-bar">
                  <div class="pp-track">
                    <div class="pp-fill" :style="{ width: (rubbingStep / 6 * 100) + '%' }"></div>
                  </div>
                </div>
                <div class="pp-btns">
                  <button v-if="rubbingStep > 1" class="pp-btn-prev" @click="prevRubbingStep">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
                    <span>上一步</span>
                  </button>
                  <button class="pp-btn" @click="nextRubbingStep">
                    <span>{{ rubbingStep === 6 ? '完成制作' : '下一步' }}</span>
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  </button>
                </div>
              </div>

              <!-- 底部操作（完成时） -->
              <div class="pp-footer" v-if="rubbingStep === 7">
                <div class="pp-btns">
                  <button class="pp-btn" @click="resetRubbing">重新体验</button>
                  <button class="pp-btn-prev" @click="closeRubbingPopup">完成</button>
                </div>
              </div>

            </div>
          </div>
        </Transition>

        <!-- 视频播放弹窗 -->
        <Transition name="popup-scale">
          <div v-if="showLuoyangVideoPlayer" class="video-player-overlay" @click.self="closeLuoyangVideoPlayer">
            <div class="video-player-card">
              <div class="vp-header">
                <span class="vp-title">非遗拓印 · 匠心传承</span>
                <button class="vp-close" @click="closeLuoyangVideoPlayer">✕</button>
              </div>
              <div class="vp-body">
                <video
                  ref="luoyangVideoRef"
                  class="vp-video"
                  :src="luoyangVideoSrc"
                  controls
                  autoplay
                  playsinline
                  webkit-playsinline
                  @ended="onLuoyangVideoEnded"
                ></video>
              </div>
            </div>
          </div>
        </Transition>

      </div>
    </Transition>

    <!-- ══ 音乐推荐面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showMusicPanel" class="profile-overlay" @click="showMusicPanel = false">
        <div class="profile-panel music-panel" @click.stop>
          <div class="panel-close" @click="showMusicPanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </div>

          <!-- 标题 -->
          <div class="trend-header">
            <div style="display:flex;align-items:center;justify-content:space-between;width:100%">
              <h2>🎵 今日音乐推荐</h2>
              <button class="music-toggle-btn" @click="toggleMusic" :title="musicOn ? '关闭背景音乐' : '开启背景音乐'">
                <svg v-if="musicOn" viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M9 3v12.26A3 3 0 107.5 18c0-.17.02-.34.04-.5H7.5a.5.5 0 01-.5-.5V7H17v7.26A3 3 0 1015.5 17c0-.17.02-.34.04-.5H15.5a.5.5 0 01-.5-.5V3H9z"/></svg>
                <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M9 3v12.26A3 3 0 107.5 18H7.5V7H17v5M3 3l18 18"/></svg>
                {{ musicOn ? '关音乐' : '开音乐' }}
              </button>
            </div>
            <p v-if="primaryEmotion">
              你今天的<span class="emotion-badge">{{ getEmoji(primaryEmotion) }} {{ primaryEmotion }}</span>占了{{ primaryEmotionPct }}%，为你定制了以下歌单
            </p>
            <p v-else>还没有情绪记录，先来倾诉一下吧 💬</p>
          </div>

          <!-- 算法说明卡片 -->
          <div class="algo-card" v-if="primaryEmotion">
            <div class="algo-title">📊 推荐算法</div>
            <div class="algo-factors">
              <div class="algo-factor">
                <div class="factor-bar-wrap">
                  <div class="factor-bar" style="width:50%"></div>
                </div>
                <div class="factor-meta">
                  <span class="factor-label">情绪匹配度</span>
                  <span class="factor-w">50%</span>
                </div>
              </div>
              <div class="algo-factor">
                <div class="factor-bar-wrap">
                  <div class="factor-bar" style="width:20%"></div>
                </div>
                <div class="factor-meta">
                  <span class="factor-label">情绪倾向</span>
                  <span class="factor-w">20%</span>
                </div>
              </div>
              <div class="algo-factor">
                <div class="factor-bar-wrap">
                  <div class="factor-bar" style="width:15%; background:#7FB3A6;"></div>
                </div>
                <div class="factor-meta">
                  <span class="factor-label">{{ timeFactorLabel }}</span>
                  <span class="factor-w">15%</span>
                </div>
              </div>
              <div class="algo-factor">
                <div class="factor-bar-wrap">
                  <div class="factor-bar" style="width:15%; background:#E8C468;"></div>
                </div>
                <div class="factor-meta">
                  <span class="factor-label">{{ weatherFactorLabel }}</span>
                  <span class="factor-w">15%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 隐藏音频元素：通过后端代理播放网易云音频 -->
          <audio ref="musicAudioEl" class="am-hidden-audio" preload="none" controls></audio>

          <!-- 推荐歌单卡片列表 -->
          <div class="music-list" v-if="musicRecs.length">
            <div
              v-for="(rec, i) in musicRecs" :key="i"
              class="music-card"
              :class="{ 'is-top': i === 0, 'is-expanded': expandedCard === i }"
            >
              <!-- 卡片头部：点击展开/折叠 -->
              <div class="mc-header" @click="toggleCard(i)">
                  <div class="mc-rank">
                  <span v-if="i === 0" class="rank-crown">🏆</span>
                  <span v-else class="rank-num">{{ i + 1 }}</span>
                </div>
                <div class="mc-style-info">
                  <div class="mc-style-name">
                    <span class="mc-emoji">{{ rec.emoji }}</span>
                    {{ rec.style }}
                  </div>
                  <div class="mc-reason">{{ rec.reason }}</div>
                </div>
                <div class="mc-score-wrap">
                  <span class="mc-score-num" :style="{ color: rec.scoreColor }">{{ rec.totalScore }}</span>
                  <span class="mc-score-label">分</span>
                </div>
                <div class="mc-arrow" :class="{ 'is-open': expandedCard === i }">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>
                </div>
              </div>

              <!-- 展开区域：歌曲列表 -->
              <Transition name="mc-expand">
                <div v-if="expandedCard === i" class="mc-body">
                  <!-- Apple Music 风格迷你播放卡片 -->
                  <div
                    v-for="(song, si) in rec.songs" :key="si"
                    class="am-song-card"
                    :class="{ 'is-active': activeSongId === song.songId }"
                    @click="toggleSongPlay(song)"
                  >
                    <!-- 封面 -->
                    <div class="am-cover-wrap">
                      <img
                        class="am-cover"
                        :src="song.cover"
                        :alt="song.name"
                        loading="lazy"
                        @error="onCoverError"
                        referrerpolicy="no-referrer"
                      />
                      <!-- 播放状态遮罩 -->
                      <div class="am-cover-overlay" v-if="activeSongId === song.songId">
                        <div class="am-eq-bars">
                          <span v-for="n in 4" :key="n" class="am-eq-bar"></span>
                        </div>
                      </div>
                    </div>
                    <!-- 歌曲信息 -->
                    <div class="am-song-info">
                      <div class="am-song-name">{{ song.name }}</div>
                      <div class="am-song-artist">{{ song.artist }}</div>
                    </div>
                    <!-- 操作按钮 -->
                    <div class="am-actions">
                      <button class="am-play-btn" @click.stop="toggleSongPlay(song)" :title="activeSongId === song.songId ? '暂停' : '播放'">
                        <svg v-if="activeSongId === song.songId" viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
                        <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
                      </button>
                      <a
                        class="am-link-btn"
                        :href="neteaseSongUrl(song.songId)"
                        target="_blank"
                        rel="noopener noreferrer"
                        @click.stop
                        title="在网易云查看详情"
                      >
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/></svg>
                      </a>
                    </div>
                  </div>
                </div>
              </Transition>
              <!-- 来源标注 -->
              <div class="mc-source" v-if="musicRecs.length">来源：网易云音乐</div>
            </div>
          </div>

          <!-- 空状态 -->
          <div class="empty-state" v-else-if="!primaryEmotion">
            <div class="empty-icon">🎶</div>
            <p>分享你的心情，获取专属音乐推荐</p>
          </div>
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
            <div
              class="quick-scroll"
              ref="quickScroll"
              @wheel="onQuickWheel"
              @mousedown="onQuickMouseDown"
              @mousemove="onQuickMouseMove"
              @mouseup="onQuickMouseUp"
              @mouseleave="onQuickMouseUp"
            >
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

    <!-- ══ 治愈面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showHealingPanel" class="profile-overlay" @click="showHealingPanel = false">
        <div class="profile-panel healing-panel" @click.stop>
          <div class="panel-close" @click="showHealingPanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </div>
          <HealingView :inline="true" @close="showHealingPanel = false" />
        </div>
      </div>
    </Transition>

    <!-- ══ 树洞面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showTreeHolePanel" class="profile-overlay" @click="showTreeHolePanel = false">
        <div class="profile-panel treehole-panel" @click.stop>
          <div class="panel-close" @click="showTreeHolePanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </div>
          <TreeHoleView :inline="true" @close="showTreeHolePanel = false" />
        </div>
      </div>
    </Transition>

    <!-- ══ 报告面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showReportPanel" class="profile-overlay" @click="showReportPanel = false">
        <div class="profile-panel report-panel" @click.stop>
          <div class="panel-close" @click="showReportPanel = false">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </div>
          <div class="trend-header">
            <h2>📊 情绪报告</h2>
            <p>了解你的心理健康状态</p>
          </div>

          <!-- 生成报告入口 -->
          <div v-if="!reportData && !reportLoading && chatMessages.length > 0" class="report-intro">
            <div class="report-intro-quote">
              <span class="rq-mark">"</span>
              <p>每一段心情都值得被记录</p>
              <span class="rq-mark">"</span>
            </div>
            <div class="report-intro-highlights">
              <div class="rhi-item">
                <span class="rhi-num">{{ stats.days || 1 }}</span>
                <span class="rhi-label">天同行</span>
              </div>
              <div class="rhi-divider"></div>
              <div class="rhi-item">
                <span class="rhi-num">{{ stats.chatCount }}</span>
                <span class="rhi-label">次对话</span>
              </div>
              <div class="rhi-divider"></div>
              <div class="rhi-item">
                <span class="rhi-num">{{ stats.moodCount }}</span>
                <span class="rhi-label">条记录</span>
              </div>
            </div>
            <div class="report-intro-text">
              咕哝已经默默陪伴你一段时间了，<br>为你准备了一份专属心情日记，来看看这段时间的心路历程吧。
            </div>
            <button class="report-intro-btn" @click="generateReport" :disabled="reportLoading">
              {{ reportLoading ? '生成中...' : '生成我的心情报告' }}
            </button>
          </div>

          <!-- 报告加载 -->
          <div v-if="reportLoading" class="report-loading">
            <div class="rl-dots">
              <span></span><span></span><span></span>
            </div>
            <p class="rl-text">正在分析情绪数据...</p>
          </div>

          <!-- 报告内容 -->
          <div v-if="reportData" class="report-content">
            <div class="report-section">
              <h3>🎯 情绪总览</h3>
              <p class="report-summary">{{ reportData.summary }}</p>
            </div>
            <div class="report-section" v-if="reportData.suggestions?.length">
              <h3>💡 建议与关怀</h3>
              <ul class="report-suggestions">
                <li v-for="(s, i) in reportData.suggestions" :key="i">{{ s }}</li>
              </ul>
            </div>
            <div class="report-section" v-if="reportData.positive_affirmation">
              <h3>🌈 每日寄语</h3>
              <p class="report-affirmation">「{{ reportData.positive_affirmation }}」</p>
            </div>
            <button class="report-back-btn" @click="reportData = null">
              <span>←</span> 返回重新生成
            </button>
          </div>

          <!-- 空状态 -->
          <div v-if="!reportData && !reportLoading && chatMessages.length === 0" class="report-empty">
            <div class="report-empty-art">
              <div class="re-seed">🌱</div>
              <div class="re-soil"></div>
            </div>
            <div class="report-empty-title">心路才刚刚开始</div>
            <div class="report-empty-text">
              每一次倾诉都是一颗种子，<br>
              等它们慢慢发芽，就会开出属于你的心情花园。
            </div>
            <button class="report-empty-btn" @click="showReportPanel = false; goToChat()">
              去种下第一颗心情种子 →
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ══ 小工具 iframe 全屏弹窗 ══ -->
    <Transition name="panel-slide">
      <div v-if="showMiniApp" class="mini-app-overlay" @click.self="closeMiniApp">
        <div class="mini-app-container">
          <div class="mini-app-header">
            <button class="mini-app-back" @click="closeMiniApp">← 回家</button>
            <span class="mini-app-title">{{ miniAppTitle }}</span>
            <div class="mini-app-spacer"></div>
          </div>
          <div class="mini-app-body">
            <iframe :src="miniAppUrl" class="mini-app-iframe" frameborder="0" allowfullscreen allow="autoplay; clipboard-write; encrypted-media; microphone; camera; midi; geolocation; gyroscope; accelerometer; magnetometer; speaker-selection"></iframe>
            <div v-if="miniAppHideBottom" class="mini-app-bottom-mask"></div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 隐藏音频元素2 -->
    <audio ref="audioEl" src="/audio/bgm.mp3" preload="auto" />

    <!-- 备案信息 -->
    <footer class="beian-footer">
      <a href="https://beian.mps.gov.cn/#/query/webSearch?code=44011202003950" target="_blank" rel="noopener noreferrer" class="beian-link">
        <img src="/images/beian-icon.png" alt="公安备案" class="beian-icon" />
        <span>粤公网安备44011202003950号</span>
      </a>
      <span class="beian-divider">|</span>
      <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">粤ICP备2026048986号-2</a>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { updateProfile, changePassword } from '../api/user'
import { getMoodStats, getMoodInsight } from '../api/mood'
import { getChatHistory, sendMessage } from '../api/chat'
import HealingView from './HealingView.vue'
import TreeHoleView from './TreeHoleView.vue'

const router = useRouter()
const userStore = useUserStore()

// ═══ 个人中心面板 ═══
const showProfilePanel = ref(false)
const showChatPanel = ref(false)
const showHealingPanel = ref(false)
const showTreeHolePanel = ref(false)
const showReportPanel = ref(false)
const showStatusPicker = ref(false)

// ═══ 复访引导：每日仪式 + 首次使用提示 ═══
const FIRST_RUN_GUIDE_KEY = 'shengyu_first_run_guide_dismissed'
const DAILY_RITUAL_SEEN_KEY = 'shengyu_daily_ritual_seen'
const showFirstRunGuide = ref(localStorage.getItem(FIRST_RUN_GUIDE_KEY) !== '1')
const dailyRitualSeed = new Date().toISOString().slice(0, 10)
const dailyRituals = [
  {
    title: '先不用变好，先把今天说出来',
    copy: '给自己三分钟，只描述感受，不评价自己。',
    actionText: '开始倾诉',
    action: 'chat',
  },
  {
    title: '看看有没有人也这样想',
    copy: '有些心情被别人说出来以后，会轻一点。',
    actionText: '去树洞看看',
    action: 'treehole',
  },
  {
    title: '今天只做一个很小的照顾',
    copy: '喝水、伸展、听一首歌，都算认真对待自己。',
    actionText: '打开治愈角',
    action: 'healing',
  },
]
const dailyRitual = computed(() => {
  const sum = [...dailyRitualSeed].reduce((total, char) => total + char.charCodeAt(0), 0)
  return dailyRituals[sum % dailyRituals.length]
})
function markDailyRitualSeen() {
  localStorage.setItem('shengyu_daily_ritual_seen', dailyRitualSeed)
}
function openDailyRitualAction() {
  markDailyRitualSeen()
  if (dailyRitual.value.action === 'treehole') {
    showTreeHolePanel.value = true
    return
  }
  if (dailyRitual.value.action === 'healing') {
    showHealingPanel.value = true
    return
  }
  goToChat()
}
function dismissFirstRunGuide() {
  showFirstRunGuide.value = false
  localStorage.setItem(FIRST_RUN_GUIDE_KEY, '1')
}
const nickname = ref(userStore.nickname || '')
const stats = reactive({ moodCount: 0, chatCount: 0, days: 0 })

// ═══ 小工具（iframe弹窗） ═══
const showMiniApp = ref(false)
const miniAppUrl = ref('')
const miniAppTitle = ref('')
const miniAppKey = ref('')
const miniAppMap = {
  air: { url: 'https://giao.me/air', title: '❄️ 小空调' },
  itv: { url: 'https://giao.me/itv', title: '📺 小电视' },
}
function openMiniApp(key) {
  const app = miniAppMap[key]
  if (!app) return
  miniAppKey.value = key
  miniAppUrl.value = app.url
  miniAppTitle.value = app.title
  showMiniApp.value = true
  // 暂停背景音乐，让小组件声音独立播放
  if (audioEl.value && musicOn.value) {
    audioEl.value.pause()
  }
}
function closeMiniApp() {
  showMiniApp.value = false
  miniAppUrl.value = ''
  miniAppKey.value = ''
  // 恢复背景音乐
  if (audioEl.value && musicOn.value) {
    audioEl.value.play().catch(() => {})
  }
}
// 小空调和小电视需要隐藏底部外部链接
const miniAppHideBottom = computed(() => ['air', 'itv'].includes(miniAppKey.value))


// ═══ 修改密码 ═══
const showPwdModal = ref(false)
const oldPwd = ref('')
const newPwd1 = ref('')
const newPwd2 = ref('')
const pwdMsg = ref('')
const pwdOk = ref(false)

async function handleChangePwd() {
  pwdMsg.value = ''
  if (!oldPwd.value) { pwdMsg.value = '请输入旧密码'; return }
  if (!newPwd1.value.trim()) { pwdMsg.value = '请输入新密码'; return }
  if (newPwd1.value !== newPwd2.value) { pwdMsg.value = '两次输入的新密码不一致'; return }
  if (newPwd1.value.length < 6) { pwdMsg.value = '新密码至少6位'; return }
  try {
    await changePassword(Number(userStore.userId), oldPwd.value, newPwd1.value, newPwd2.value)
    pwdOk.value = true
    pwdMsg.value = '密码修改成功！'
    oldPwd.value = ''; newPwd1.value = ''; newPwd2.value = ''
    setTimeout(() => { showPwdModal.value = false; pwdMsg.value = ''; pwdOk.value = false }, 1500)
  } catch (e) {
    pwdOk.value = false
    pwdMsg.value = e.response?.data?.detail || '修改失败'
  }
}

// ═══ 报告 ═══
const reportData = ref(null)
const reportLoading = ref(false)

async function generateReport() {
  reportLoading.value = true
  try {
    // 使用已有的情绪数据生成报告
    const res = await getMoodStats({ period: 30 })
    const distribution = res.distribution || {}
    const avgScore = res.avg_score || 0
    const count = res.count || 0

    const topMood = Object.entries(distribution).sort((a, b) => b[1] - a[1])[0]
    const topMoodLabel = topMood ? topMood[0] : '平静'
    const topMoodPct = topMood ? Math.round(topMood[1] / count * 100) : 0

    const suggestions = []
    if (avgScore < 4) {
      suggestions.push('建议多进行户外活动，适当运动有助于改善情绪')
      suggestions.push('可以尝试与亲近的人聊聊最近的感受')
    } else if (avgScore < 7) {
      suggestions.push('保持当前的生活节奏，注意劳逸结合')
      suggestions.push('每天给自己留一点独处放松的时间')
    } else {
      suggestions.push('你目前的状态很不错，继续保持积极的心态')
    }
    if (topMoodLabel === '焦虑' || topMoodLabel === '紧张') {
      suggestions.push('试试治愈空间的呼吸练习，对缓解焦虑很有效')
    }
    if (topMoodLabel === '悲伤' || topMoodLabel === '低落') {
      suggestions.push('可以去树洞倾诉，有人会与你共鸣')
    }

    const affirmations = [
      '你已经做得很好了，不必对自己太苛刻',
      '每一天都是新的开始，你值得被温柔以待',
      '感到疲惫也没关系，休息也是前进的一种方式',
      '你的存在本身就有意义',
      '慢慢来，比较快'
    ]

    reportData.value = {
      summary: `近30天共记录 ${count} 次情绪，平均情绪分 ${avgScore.toFixed(1)}。主要情绪为「${topMoodLabel}」占比 ${topMoodPct}%。${avgScore >= 7 ? '整体状态良好，继续保持！' : avgScore >= 4 ? '情绪起伏属于正常范围，关注自我关怀。' : '近期情绪偏低落，建议多关照自己。'}`,
      suggestions,
      positive_affirmation: affirmations[Math.floor(Math.random() * affirmations.length)]
    }
  } catch (e) {
    console.error('生成报告失败:', e)
    reportData.value = {
      summary: '暂无足够的情绪数据来生成报告，请先多倾诉几次吧。',
      suggestions: ['去和咕哝聊聊天，记录你的情绪'],
      positive_affirmation: '每一步都算数，你正在路上。'
    }
  }
  reportLoading.value = false
}

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
  if (city.name === '西安') {
    startXianTransition()
  } else if (city.name === '洛阳') {
    startLuoyangTransition()
  } else {
    alert(`你选择了${selectedTransportName.value}前往${city.name} ${city.emoji}`)
    showCityPanel.value = false
  }
}

// ═══ 西安城市探索 & 皮影制作 ═══
const showXianPanel = ref(false)
const showXianTransition = ref(false)
const xianPhase = ref(0)

// 地铁转场音乐
const metroAudioEl = ref(null)

// 西安城市音乐播放列表
const xianPlaylist = [
  '/audio/xian-song1.mp3',
  '/audio/xian-song2.mp3',
  '/audio/xian-song3.mp3',
]
const xianMusicEl = ref(null)
const xianMusicIndex = ref(0)

function playXianCityMusic() {
  if (!xianMusicEl.value) {
    xianMusicEl.value = new Audio()
    xianMusicEl.value.volume = 0.5
    xianMusicEl.value.addEventListener('ended', () => {
      xianMusicIndex.value = (xianMusicIndex.value + 1) % xianPlaylist.length
      xianMusicEl.value.src = xianPlaylist[xianMusicIndex.value]
      xianMusicEl.value.play().catch(() => {})
    })
  }
  xianMusicIndex.value = 0
  xianMusicEl.value.src = xianPlaylist[0]
  xianMusicEl.value.play().catch(() => {})
}

function stopXianCityMusic() {
  if (xianMusicEl.value) {
    xianMusicEl.value.pause()
    xianMusicEl.value.currentTime = 0
  }
}

function playMetroAudio(src) {
  // 暂停背景音乐
  if (audioEl.value && musicOn.value) {
    audioEl.value.pause()
  }
  // 创建并播放地铁音乐
  if (!metroAudioEl.value) {
    metroAudioEl.value = new Audio()
  }
  metroAudioEl.value.src = src
  metroAudioEl.value.loop = false
  metroAudioEl.value.volume = 0.6
  metroAudioEl.value.play().catch(() => {})
}

function stopMetroAudio() {
  if (metroAudioEl.value) {
    metroAudioEl.value.pause()
    metroAudioEl.value.currentTime = 0
  }
}

function startXianTransition() {
  showCityPanel.value = false
  showXianTransition.value = true
  xianPhase.value = 0

  // 播放西安地铁音乐
  playMetroAudio('/audio/xian-metro.mp3')

  setTimeout(() => { xianPhase.value = 1 }, 1500)
  setTimeout(() => { xianPhase.value = 2 }, 3200)
  setTimeout(() => { xianPhase.value = 3 }, 4800)
  setTimeout(() => {
    showXianTransition.value = false
    showXianPanel.value = true
    xianPhase.value = 0
    // 转场结束，停止地铁音乐，开始播放西安城市音乐
    stopMetroAudio()
    playXianCityMusic()
  }, 6200)
}

const showPuppetPopup = ref(false)
const shadowPuppetStep = ref(0) // 0=未开始, 1-7=步骤, 8=完成

// 视频播放
const showVideoPlayer = ref(false)
const videoRef = ref(null)
const videoSrc = ref('/videos/puppet-show.mp4')

const shadowPuppetSteps = [
  {
    id: 1,
    title: '制皮',
    emoji: '🐂',
    desc: '选用上等牛皮，经过浸泡、刮毛、去脂，制成薄如纸、韧如丝的皮影原料。',
    detail: '牛皮需在水中浸泡三天三夜，再用特制刀具反复刮削，直至厚度均匀透光。',
    animClass: 'anim-leather'
  },
  {
    id: 2,
    title: '画稿',
    emoji: '🖌️',
    desc: '将人物造型描绘在牛皮上，线条流畅，神态生动。',
    detail: '画师需精通戏曲人物造型，一笔一画勾勒出角色的忠奸善恶。',
    animClass: 'anim-draw'
  },
  {
    id: 3,
    title: '雕刻',
    emoji: '🔪',
    desc: '以刻刀代笔，在牛皮上镂刻出精细的纹样与轮廓。',
    detail: '陕西皮影采用"推皮触刀"技法，刀锋不动而推皮行走，线条细如发丝。',
    animClass: 'anim-carve'
  },
  {
    id: 4,
    title: '上色',
    emoji: '🎨',
    desc: '用传统矿物颜料为皮影着色，红绿黄黑，对比鲜明。',
    detail: '皮影着色讲究"红忠紫孝、黑正粉老、水白奸邪"的色彩语言。',
    animClass: 'anim-paint'
  },
  {
    id: 5,
    title: '脱水',
    emoji: '☀️',
    desc: '将上好色的皮影平铺晾干，使色彩牢固附着。',
    detail: '需在阴凉通风处自然晾干，不可暴晒，否则容易开裂变形。',
    animClass: 'anim-dry'
  },
  {
    id: 6,
    title: '组装',
    emoji: '🔗',
    desc: '将头、身、四肢用线连接，使皮影关节灵活可动。',
    detail: '关节连接处需精准打孔，用丝线或铁丝串联，保证舞动时协调自然。',
    animClass: 'anim-assemble'
  },
  {
    id: 7,
    title: '装杆',
    emoji: '🎭',
    desc: '在皮影的关键部位装上操纵杆，便于表演者操控。',
    detail: '主杆装在脖颈，手杆分装两臂，三杆配合可演绎千军万马。',
    animClass: 'anim-rod'
  }
]

const currentStepData = computed(() => {
  if (shadowPuppetStep.value >= 1 && shadowPuppetStep.value <= 7) {
    return shadowPuppetSteps[shadowPuppetStep.value - 1]
  }
  return null
})

function openXianPanel() {
  showCityPanel.value = false
  showXianPanel.value = true
  showPuppetPopup.value = false
  shadowPuppetStep.value = 0
}

function closeXianPanel() {
  showXianPanel.value = false
  showPuppetPopup.value = false
  shadowPuppetStep.value = 0
  // 停止西安城市音乐，恢复背景音乐
  stopXianCityMusic()
  if (audioEl.value && musicOn.value) {
    audioEl.value.play().catch(() => {})
  }
}

function startPuppetMaking() {
  showPuppetPopup.value = true
  shadowPuppetStep.value = 1
}

function closePuppetPopup() {
  showPuppetPopup.value = false
  shadowPuppetStep.value = 0
}

// ═══ 视频播放 ═══
function openVideoPlayer() {
  showVideoPlayer.value = true
  // 暂停背景音乐
  if (audioEl.value && musicOn.value) {
    audioEl.value.pause()
  }
  // 暂停西安城市音乐
  if (xianMusicEl.value) {
    xianMusicEl.value.pause()
  }
}
function closeVideoPlayer() {
  showVideoPlayer.value = false
  if (videoRef.value) {
    videoRef.value.pause()
    videoRef.value.currentTime = 0
  }
  // 如果在西安面板内，恢复城市音乐而非BGM
  if (showXianPanel.value && xianMusicEl.value) {
    xianMusicEl.value.play().catch(() => {})
  } else if (audioEl.value && musicOn.value) {
    audioEl.value.play().catch(() => {})
  }
}
function onVideoEnded() {
  // 视频播放结束，恢复音乐
  if (showXianPanel.value && xianMusicEl.value) {
    xianMusicEl.value.play().catch(() => {})
  } else if (audioEl.value && musicOn.value) {
    audioEl.value.play().catch(() => {})
  }
}

// ═══ 洛阳城市探索 & 非遗拓印 ═══
const showLuoyangPanel = ref(false)
const showLuoyangTransition = ref(false)
const luoyangPhase = ref(0) // 0=初始 1=运动感 2=模糊 3=白屏 4=显示洛阳

const showRubbingPopup = ref(false)
const rubbingStep = ref(0) // 0=未开始, 1-6=步骤, 7=完成

const rubbingSteps = [
  { id: 1, title: '清理器物', emoji: '🧹', desc: '用软毛刷轻轻清理碑刻表面的灰尘和杂物，确保碑面干净平整。', detail: '清碑是拓印的第一步，需耐心细致，为后续上纸打好基础。' },
  { id: 2, title: '上纸润纸', emoji: '📜', desc: '将宣纸轻轻覆盖在碑刻表面，用喷壶均匀喷洒清水。', detail: '纸张充分湿润后与碑面紧密贴合，是拓印成败的关键一步。' },
  { id: 3, title: '敲打入凹', emoji: '🔨', desc: '用棕刷从中心向四周轻轻敲打，使纸张嵌入碑文的凹槽中。', detail: '刷纸需力道均匀，确保字迹凹凸分明，为扑墨做好准备。' },
  { id: 4, title: '自然晾干', emoji: '💨', desc: '等待纸张自然晾干至半干状态，纸张与碑面贴合紧密。', detail: '不可急用热源烘干，自然晾干才能保证纸张张力和墨色均匀。' },
  { id: 5, title: '扑墨拓印', emoji: '🖌️', desc: '用拓包蘸取适量墨汁，在纸上轻轻拍打，使字迹清晰显现。', detail: '打墨讲究"淡施轻扑"，层层叠加，墨色浓淡相宜方为上品。' },
  { id: 6, title: '揭取拓片', emoji: '🖼️', desc: '待墨汁干透后，从一角轻轻揭起拓片。', detail: '一张完整的碑刻拓印作品便完成了，千年文脉一纸传薪。' },
]

// 洛阳视频播放
const showLuoyangVideoPlayer = ref(false)
const luoyangVideoRef = ref(null)
const luoyangVideoSrc = ref('/videos/luoyang-rubbing.mp4')

// 洛阳城市音乐播放列表
const luoyangPlaylist = [
  '/audio/luoyang-song1.mp3',
  '/audio/luoyang-song2.mp3',
  '/audio/luoyang-song3.mp3',
]
const luoyangMusicEl = ref(null)
const luoyangMusicIndex = ref(0)

function playLuoyangCityMusic() {
  if (!luoyangMusicEl.value) {
    luoyangMusicEl.value = new Audio()
    luoyangMusicEl.value.volume = 0.5
    luoyangMusicEl.value.addEventListener('ended', () => {
      luoyangMusicIndex.value = (luoyangMusicIndex.value + 1) % luoyangPlaylist.length
      luoyangMusicEl.value.src = luoyangPlaylist[luoyangMusicIndex.value]
      luoyangMusicEl.value.play().catch(() => {})
    })
  }
  luoyangMusicIndex.value = 0
  luoyangMusicEl.value.src = luoyangPlaylist[0]
  luoyangMusicEl.value.play().catch(() => {})
}

function stopLuoyangCityMusic() {
  if (luoyangMusicEl.value) {
    luoyangMusicEl.value.pause()
    luoyangMusicEl.value.currentTime = 0
  }
}

function startLuoyangTransition() {
  showCityPanel.value = false
  showLuoyangTransition.value = true
  luoyangPhase.value = 0

  // 播放洛阳地铁音乐
  playMetroAudio('/audio/luoyang-metro.mp3')

  // 转场时间线
  setTimeout(() => { luoyangPhase.value = 1 }, 1500)   // 启动运动感
  setTimeout(() => { luoyangPhase.value = 2 }, 3200)   // 开始模糊
  setTimeout(() => { luoyangPhase.value = 3 }, 4800)   // 白屏
  setTimeout(() => {
    showLuoyangTransition.value = false
    showLuoyangPanel.value = true
    luoyangPhase.value = 0
    // 转场结束，停止地铁音乐，播放洛阳城市音乐
    stopMetroAudio()
    playLuoyangCityMusic()
  }, 6200)                                              // 显示洛阳
}

function openLuoyangPanel() {
  showCityPanel.value = false
  showLuoyangPanel.value = true
}
function closeLuoyangPanel() {
  showLuoyangPanel.value = false
  closeLuoyangVideoPlayer()
  closeRubbingPopup()
  // 停止洛阳城市音乐，恢复背景音乐
  stopLuoyangCityMusic()
  if (audioEl.value && musicOn.value) {
    audioEl.value.play().catch(() => {})
  }
}
function startRubbing() {
  showRubbingPopup.value = true
  rubbingStep.value = 1
}
function closeRubbingPopup() {
  showRubbingPopup.value = false
  rubbingStep.value = 0
}
function prevRubbingStep() {
  if (rubbingStep.value > 1) rubbingStep.value--
}
function nextRubbingStep() {
  if (rubbingStep.value < 6) {
    rubbingStep.value++
  } else {
    rubbingStep.value = 7
  }
}
function resetRubbing() {
  rubbingStep.value = 1
}

function openLuoyangVideoPlayer() {
  showLuoyangVideoPlayer.value = true
  // 暂停背景音乐
  if (audioEl.value && musicOn.value) {
    audioEl.value.pause()
  }
  // 暂停洛阳城市音乐
  if (luoyangMusicEl.value) {
    luoyangMusicEl.value.pause()
  }
}
function closeLuoyangVideoPlayer() {
  showLuoyangVideoPlayer.value = false
  if (luoyangVideoRef.value) {
    luoyangVideoRef.value.pause()
    luoyangVideoRef.value.currentTime = 0
  }
  // 如果在洛阳面板内，恢复城市音乐而非BGM
  if (showLuoyangPanel.value && luoyangMusicEl.value) {
    luoyangMusicEl.value.play().catch(() => {})
  } else if (audioEl.value && musicOn.value) {
    audioEl.value.play().catch(() => {})
  }
}
function onLuoyangVideoEnded() {
  if (showLuoyangPanel.value && luoyangMusicEl.value) {
    luoyangMusicEl.value.play().catch(() => {})
  } else if (audioEl.value && musicOn.value) {
    audioEl.value.play().catch(() => {})
  }
}

function resetPuppet() {
  shadowPuppetStep.value = 1
}

function prevStep() {
  if (shadowPuppetStep.value > 1) {
    shadowPuppetStep.value--
  }
}

function nextStep() {
  if (shadowPuppetStep.value < 7) {
    shadowPuppetStep.value++
  } else {
    shadowPuppetStep.value = 8
  }
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

// 情绪分布 — 评判说明
const moodJudgeNote = {
  '开心': '通过对话中的积极关键词、感叹词、愉悦语气和正面事件描述综合判定',
  '平静': '由中性平稳的叙述节奏、日常话题和低情绪波动表达判定',
  '焦虑': '依据不安词汇、反复确认、急促表达和对未来的担忧信号识别',
  '难过': '从低能量措辞、悲伤表达、回避性话题和自我否定倾向判断',
  '愤怒': '基于激烈用语、否定句式、不满情绪和对事件的强烈反应分析',
}
// 占比最大时的安慰/建议
const moodComfort = {
  '开心': '太棒了！保持这份好心情，你值得每一刻的快乐 🌟',
  '平静': '内心宁静是一种力量。慢慢来，一切都在变好的路上 🌿',
  '焦虑': '焦虑是大脑在提醒你重视某事，不是你的敌人。试着深呼吸，你已经做得很好了 💛',
  '难过': '难过没关系，它是你柔软内心的证明。如果愿意，我一直在这里倾听 🤍',
  '愤怒': '愤怒是边界被触碰的信号。允许自己生气，但别让情绪控制你。找个出口释放它吧 💪',
}
const topMoodLabels = computed(() => {
  const dist = distribution.value
  if (!Object.keys(dist).length) return []
  const entries = Object.entries(dist)
  const maxVal = Math.max(...entries.map(e => e[1]))
  if (maxVal <= 0) return []
  // 只取一个占比最高的情绪作为主导情绪（即使有并列也只取第一个）
  const topEntry = entries.find(e => e[1] === maxVal)
  return topEntry ? [topEntry[0]] : []
})
const topMoodComforts = computed(() => {
  return topMoodLabels.value.map(l => moodComfort[l]).filter(Boolean)
})
const hoveredMood = ref(null)
function showTooltip(label) { hoveredMood.value = label }
function hideTooltip() { hoveredMood.value = null }

// ═══ 音乐推荐 ═══
const showMusicPanel = ref(false)
const expandedCard = ref(-1) // -1 = 全部折叠，0-4 = 展开第N张卡片
const activeSongId = ref(null) // 当前播放中的歌曲 songId
const musicAudioEl = ref(null) // <audio> 元素引用

function toggleCard(idx) {
  expandedCard.value = expandedCard.value === idx ? -1 : idx
}

function toggleSongPlay(song) {
  if (activeSongId.value === song.songId) {
    // 暂停当前
    activeSongId.value = null
    if (musicAudioEl.value) {
      musicAudioEl.value.pause()
      musicAudioEl.value.src = ''
    }
  } else {
    // 播放新歌：先尝试用后端 /api/music/play 代理播放
    activeSongId.value = song.songId
    if (musicAudioEl.value) {
      // 监听播放失败，失败后跳转网易云网页
      const onError = () => {
        musicAudioEl.value.removeEventListener('error', onError)
        // 播放失败，跳转网易云网页
        window.open(`https://music.163.com/song?id=${song.songId}`, '_blank')
        activeSongId.value = null
      }
      musicAudioEl.value.addEventListener('error', onError)
      musicAudioEl.value.src = playAudioUrl(song.songId)
      musicAudioEl.value.play().catch(() => {
        // autoplay 被拦，用户手动点播放按钮时不会再进这里
      })
    }
  }
}

function openMusicPanel() {
  showMusicPanel.value = true
  expandedCard.value = -1
  activeSongId.value = null
  if (musicAudioEl.value) {
    musicAudioEl.value.pause()
    musicAudioEl.value.src = ''
  }
}

// 后端代理音频 URL（绕过网易云 Referer 限制）
function playAudioUrl(songId) {
  return `${import.meta.env.VITE_API_BASE || ''}/api/music/play?song_id=${songId}`
}

// 构建网易云歌曲详情页 URL
function neteaseSongUrl(songId) {
  return `https://music.163.com/song?id=${songId}`
}

// 封面图片加载失败时，替换为占位符
function onCoverError(e) {
  const target = e.target
  if (target && target.tagName === 'IMG') {
    target.style.display = 'none'
    const parent = target.parentElement
    if (!parent.querySelector('.mc-cover-placeholder')) {
      const div = document.createElement('div')
      div.className = 'mc-cover-placeholder'
      div.textContent = '🎵'
      parent.insertBefore(div, target)
    }
  }
}

// 主导情绪 & 占比
const primaryEmotion = computed(() => {
  return topMoodLabels.value[0] || null
})
const primaryEmotionPct = computed(() => {
  const p = primaryEmotion.value
  if (!p || !distribution.value[p]) return 0
  return Math.round(distribution.value[p] / totalMoodCount.value * 100)
})

// ─── 音乐风格库：每种风格对 5 种情绪的亲和力评分 (0-10)，并附带代表性歌曲 ───
const musicStyles = [
  {
    style: '欢快流行', emoji: '🎉', color: '#E8C468',
    searchKeyword: '欢快 流行 华语',
    reason: '适合开心时放大愉悦感',
    affinity: { '开心': 10, '平静': 4, '焦虑': 1, '难过': 0, '愤怒': 2 },
    timeAffinity: { day: 9, evening: 6, night: 3 },
    weatherAffinity: { sun: 9, cloud: 7, rain: 3, snow: 3, fog: 4 },
    // 代表性歌曲：歌名、歌手、网易云songId（用于iframe播放器）
    songs: [
      { name: '晴天', artist: '周杰伦', songId: 186016, cover: 'https://p1.music.126.net/ZGffiDQZrGj5s_hnR1CNbg==/109951165566379710.jpg' },
      { name: '告白气球', artist: '周杰伦', songId: 569213183, cover: 'https://p1.music.126.net/e4hVwChbCGUZ37Wrd9B6yQ==/109951163919066717.jpg' },
      { name: '小幸运', artist: '田馥甄', songId: 2917134, cover: 'https://p1.music.126.net/TQxwpNMQWiih1b19b4KKGw==/1681153278877522.jpg' },
    ]
  },
  {
    style: '治愈轻音乐', emoji: '🎹', color: '#7FB3A6',
    searchKeyword: '治愈 轻音乐 纯音乐',
    reason: '安抚焦虑，带来内心平静',
    affinity: { '开心': 5, '平静': 8, '焦虑': 10, '难过': 9, '愤怒': 4 },
    timeAffinity: { day: 6, evening: 9, night: 10 },
    weatherAffinity: { sun: 6, cloud: 8, rain: 10, snow: 9, fog: 9 },
    songs: [
      { name: '城南花已开', artist: '三亩地', songId: 1359357042, cover: 'https://p1.music.126.net/i-7ktILRPImJ0NwiH8DABg==/109951162885959979.jpg' },
      { name: '夜的钢琴曲五', artist: '石进', songId: 67295, cover: 'https://p1.music.126.net/zdjtruSEpZNwmlwWcohpsg==/109951163167564492.jpg' },
      { name: '所念皆星河', artist: 'CMJ', songId: 1444918783, cover: 'https://p1.music.126.net/3VeuCpgZlZDD1Gxb-KBJqg==/109951164953114721.jpg' },
    ]
  },
  {
    style: '温暖民谣', emoji: '🎸', color: '#C9A86C',
    searchKeyword: '温暖 民谣 治愈',
    reason: '像朋友在耳边讲故事',
    affinity: { '开心': 6, '平静': 9, '焦虑': 7, '难过': 8, '愤怒': 3 },
    timeAffinity: { day: 7, evening: 9, night: 7 },
    weatherAffinity: { sun: 7, cloud: 9, rain: 8, snow: 7, fog: 8 },
    songs: [
      { name: '成都', artist: '赵雷', songId: 436514312, cover: 'https://p1.music.126.net/34YW1QtKxJ_3YnX9ZzKhzw==/2946691234868155.jpg' },
      { name: '理想三旬', artist: '赵雷', songId: 483671599, cover: 'https://p1.music.126.net/ZZAQGWl9mR7g5xCyWWH3Pw==/19149094509535913.jpg' },
      { name: '给他', artist: '赵雷', songId: 436514315, cover: 'https://p1.music.126.net/7EYBYjQeiq98Qf4guhhmVA==/109951168738695464.jpg' },
    ]
  },
  {
    style: '节奏电子', emoji: '🎧', color: '#D4776A',
    searchKeyword: '电子 节奏 House 中文',
    reason: '用节拍点燃能量',
    affinity: { '开心': 9, '平静': 3, '焦虑': 2, '难过': 1, '愤怒': 6 },
    timeAffinity: { day: 9, evening: 7, night: 2 },
    weatherAffinity: { sun: 10, cloud: 7, rain: 3, snow: 2, fog: 3 },
    songs: [
      { name: '你要跳舞吗', artist: '新裤子', songId: 1356068210, cover: 'https://p1.music.126.net/C6Vro2l0BH59Wka9gOaC6w==/109951171180358170.jpg' },
      { name: '生活因你而火热', artist: '新裤子', songId: 1356068220, cover: 'https://p1.music.126.net/0lflIySgfNfAq5zBaasoDg==/109951165787458877.jpg' },
      { name: '没有理想的人不伤心', artist: '新裤子', songId: 29787149, cover: 'https://p1.music.126.net/UsI2lB7qV2fhvBIjY0DCjQ==/109951172945816490.jpg' },
    ]
  },
  {
    style: '舒缓R&B', emoji: '🎷', color: '#8B7BA6',
    searchKeyword: 'R&B 舒缓 中文',
    reason: '柔和的律动让你放松下来',
    affinity: { '开心': 7, '平静': 8, '焦虑': 6, '难过': 5, '愤怒': 3 },
    timeAffinity: { day: 6, evening: 10, night: 8 },
    weatherAffinity: { sun: 7, cloud: 8, rain: 9, snow: 6, fog: 7 },
    songs: [
      { name: '关键词', artist: '林俊杰', songId: 37115780, cover: 'https://p1.music.126.net/xZAbLHvJbuotr2E-Z8w5DA==/109951165971294045.jpg' },
      { name: '修炼爱情', artist: '林俊杰', songId: 25706282, cover: 'https://p1.music.126.net/625-tE8OzdM-rWO37PgqlQ==/109951168111472442.jpg' },
      { name: '不为谁而作的歌', artist: '林俊杰', songId: 436514197, cover: 'https://p1.music.126.net/D7-9kByFrvbgiuEnC0dDfA==/109951165970794886.jpg' },
    ]
  },
  {
    style: '释放摇滚', emoji: '🎸', color: '#C94A4A',
    searchKeyword: '摇滚 释放 中文摇滚',
    reason: '让积压的情绪随鼓点释放',
    affinity: { '开心': 5, '平静': 1, '焦虑': 3, '难过': 2, '愤怒': 10 },
    timeAffinity: { day: 8, evening: 5, night: 1 },
    weatherAffinity: { sun: 8, cloud: 6, rain: 5, snow: 3, fog: 4 },
    songs: [
      { name: '山海', artist: '草东没有派对', songId: 1358695895, cover: 'https://p1.music.126.net/C6Vro2l0BH59Wka9gOaC6w==/109951171180358170.jpg' },
      { name: '丑', artist: '草东没有派对', songId: 5276217, cover: 'https://p1.music.126.net/I-nsxE9zdpuin9g_mckpXg==/86861418611919.jpg' },
      { name: '大风吹', artist: '刘柏辛', songId: 1496091321, cover: 'https://p1.music.126.net/C6Vro2l0BH59Wka9gOaC6w==/109951171180358170.jpg' },
    ]
  },
  {
    style: '自然白噪音', emoji: '🌿', color: '#6DB58B',
    searchKeyword: '自然 白噪音 雨声',
    reason: '回归自然的频率，抚平焦躁',
    affinity: { '开心': 3, '平静': 10, '焦虑': 8, '难过': 6, '愤怒': 4 },
    timeAffinity: { day: 7, evening: 8, night: 10 },
    weatherAffinity: { sun: 5, cloud: 8, rain: 10, snow: 8, fog: 9 },
    songs: [
      { name: '雨声白噪音', artist: '自然之声', songId: 1465849737, cover: 'https://p1.music.126.net/C6Vro2l0BH59Wka9gOaC6w==/109951171180358170.jpg' },
      { name: '森林鸟鸣', artist: '自然之声', songId: 1465849758, cover: 'https://p2.music.126.net/C6Vro2l0BH59Wka9gOaC6w==/109951171180358170.jpg' },
      { name: '海浪声', artist: '自然之声', songId: 1444918786, cover: 'https://p1.music.126.net/jsBhqms-CD7T_DYCxnIQjA==/109951166460341641.jpg' },
    ]
  },
  {
    style: '经典爵士', emoji: '🎺', color: '#C9A050',
    searchKeyword: '爵士 经典 咖啡',
    reason: '在优雅旋律中品味独处时光',
    affinity: { '开心': 6, '平静': 9, '焦虑': 5, '难过': 6, '愤怒': 2 },
    timeAffinity: { day: 6, evening: 9, night: 8 },
    weatherAffinity: { sun: 6, cloud: 8, rain: 9, snow: 8, fog: 7 },
    songs: [
      { name: 'Fly Me to the Moon', artist: 'Frank Sinatra', songId: 4168622, cover: 'https://p2.music.126.net/bJRtgoTCe0YspTrkdYo0Tw==/676199651127457.jpg' },
      { name: 'What a Wonderful World', artist: 'Louis Armstrong', songId: 26383868, cover: 'https://p1.music.126.net/N3qjM1qskbd7Dx_Dynvt1w==/109951169912228684.jpg' },
      { name: 'L-O-V-E', artist: 'Nat King Cole', songId: 18402858, cover: 'https://p1.music.126.net/bTFrV7URxgZ0o-isyGD7xQ==/109951170244545780.jpg' },
    ]
  },
  {
    style: '能量说唱', emoji: '🎤', color: '#D4776A',
    searchKeyword: '说唱 正能量 中文说唱',
    reason: '用有力的词句为自己打气',
    affinity: { '开心': 8, '平静': 2, '焦虑': 4, '难过': 2, '愤怒': 7 },
    timeAffinity: { day: 9, evening: 5, night: 1 },
    weatherAffinity: { sun: 9, cloud: 6, rain: 3, snow: 2, fog: 3 },
    songs: [
      { name: '野狼Disco', artist: '宝石Gem', songId: 1359094256, cover: 'https://p2.music.126.net/RsYEUlA8agDF8zaer4CGPg==/697090372021875.jpg' },
      { name: '我tm年轻人', artist: 'Bridge', songId: 1444918784, cover: 'https://p1.music.126.net/zpHpJYRJLlAUJaXO9kWQgA==/109951169037909968.jpg' },
      { name: '经济舱', artist: '满舒克', songId: 1298137594, cover: 'https://p2.music.126.net/Asu2_uqMi8hu_Ro8cbKOTA==/109951169642450108.jpg' },
    ]
  },
  {
    style: '怀旧金曲', emoji: '📻', color: '#A0846C',
    searchKeyword: '经典老歌 怀旧 华语金曲',
    reason: '熟悉的旋律是最好的陪伴',
    affinity: { '开心': 7, '平静': 7, '焦虑': 5, '难过': 9, '愤怒': 2 },
    timeAffinity: { day: 6, evening: 8, night: 7 },
    weatherAffinity: { sun: 6, cloud: 8, rain: 9, snow: 8, fog: 7 },
    songs: [
      { name: '后来', artist: '刘若英', songId: 254128, cover: 'https://p2.music.126.net/N_dKBZBGibWNhrjDTEgxXg==/109951168163382132.jpg' },
      { name: '红豆', artist: '王菲', songId: 254033, cover: 'https://p2.music.126.net/YDfgFWb0Hom_z1rmyhB5ng==/115448720932051.jpg' },
      { name: '情非得已', artist: '庾澄庆', songId: 254492, cover: 'https://p2.music.126.net/nSCOYgdN2yo1e-NdQWa4CQ==/18511377767232313.jpg' },
    ]
  },
]

// ─── 天气分类 ───
const weatherCategory = computed(() => {
  const code = weatherCode.value
  if (code === 0) return 'sun'
  if (code <= 3) return 'cloud'
  if (code <= 48) return 'fog'
  if (code <= 67) return 'rain'
  if (code <= 86) return 'snow'
  return 'rain'
})

// ─── 时段与天气标签 ───
const timeFactorLabel = computed(() => {
  const t = timeOfDay.value
  if (t === 'day') return '☀️ 白天活力'
  if (t === 'evening') return '🌅 傍晚放松'
  return '🌙 夜间舒缓'
})
const weatherFactorLabel = computed(() => {
  const w = weatherCategory.value
  if (w === 'sun') return '☀️ 晴天偏明快'
  if (w === 'cloud') return '⛅ 多云偏温暖'
  if (w === 'rain') return '🌧️ 雨天偏治愈'
  if (w === 'snow') return '❄️ 雪天偏温暖'
  return '🌫️ 雾天偏沉静'
})

// ─── 情绪倾向：正值=积极主导，负值=消极主导 ───
const emotionTendency = computed(() => {
  const dist = distribution.value
  if (!Object.keys(dist).length) return 0
  const total = totalMoodCount.value
  const pos = (dist['开心'] || 0) + (dist['平静'] || 0) * 0.5
  const neg = (dist['焦虑'] || 0) + (dist['难过'] || 0) + (dist['愤怒'] || 0)
  if (total === 0) return 0
  return Math.round(((pos - neg) / total) * 100)
})

// ─── 核心推荐算法 ───
const musicRecs = computed(() => {
  const dist = distribution.value
  if (!Object.keys(dist).length || !primaryEmotion.value) return []

  const total = totalMoodCount.value
  const pct = {}
  for (const [label, count] of Object.entries(dist)) {
    pct[label] = count / total
  }

  const primary = primaryEmotion.value
  const time = timeOfDay.value
  const weather = weatherCategory.value
  const tendency = emotionTendency.value

  const scored = musicStyles.map(s => {
    const primaryMatch = s.affinity[primary] || 0
    const emotionScore = (primaryMatch / 10) * 50

    const posAffinity = Math.max(s.affinity['开心'] || 0, s.affinity['平静'] || 0)
    const negAffinity = Math.max(s.affinity['焦虑'] || 0, s.affinity['难过'] || 0, s.affinity['愤怒'] || 0)
    let tendencyBonus = 0
    if (tendency > 0) {
      tendencyBonus = (posAffinity / 10) * (tendency / 100) * 20
    } else {
      tendencyBonus = (negAffinity / 10) * (Math.abs(tendency) / 100) * 20
  }

    const timeScore = ((s.timeAffinity[time] || 5) / 10) * 15
    const weatherScore = ((s.weatherAffinity[weather] || 5) / 10) * 15

    const totalScore = Math.round(emotionScore + tendencyBonus + timeScore + weatherScore)

    let scoreColor
    if (totalScore >= 75) scoreColor = '#D4776A'
    else if (totalScore >= 60) scoreColor = '#E8C468'
    else if (totalScore >= 40) scoreColor = '#7FB3A6'
    else scoreColor = '#8B8B8B'

    return {
      style: s.style,
      emoji: s.emoji,
      color: s.color,
      reason: s.reason,
      songs: s.songs || [],
      totalScore,
      scoreColor,
      _emotionScore: Math.round(emotionScore),
      _tendencyBonus: Math.round(tendencyBonus),
      _timeScore: Math.round(timeScore),
      _weatherScore: Math.round(weatherScore),
    }
  })

  return scored.sort((a, b) => b.totalScore - a.totalScore).slice(0, 5)
})

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

async function handleLogout() {
  if (!confirm('确定要退出登录吗？')) return
  const wasTeacher = userStore.isAdmin
  userStore.logout()
  showProfilePanel.value = false
  if (wasTeacher) {
    router.push('/teacher-login')
    return
  }
  try {
    await userStore.ensureDemoSession()
  } catch {
    router.push('/teacher-login')
  }
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

// BGM播放列表
const bgmPlaylist = [
  '/audio/bgm.mp3',
  '/audio/bgm-song2.mp3',
  '/audio/bgm-song3.mp3',
]
const bgmIndex = ref(0)

function initBgmPlaylist() {
  if (!audioEl.value) return
  audioEl.value.addEventListener('ended', () => {
    bgmIndex.value = (bgmIndex.value + 1) % bgmPlaylist.length
    audioEl.value.src = bgmPlaylist[bgmIndex.value]
    if (musicOn.value) {
      audioEl.value.play().catch(() => {})
    }
  })
}

function enterApp() {
  showSplash.value = false
  // 用户触发点击，绕过浏览器自动播放限制
  if (audioEl.value) {
    bgmIndex.value = 0
    audioEl.value.src = bgmPlaylist[0]
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
    initBgmPlaylist()
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
  { emoji: '😊', text: '今天有好事发生' },
  { emoji: '🌟', text: '我想分享快乐' },
  { emoji: '💪', text: '给自己打个气' },
  { emoji: '🌈', text: '来点正能量' },
  { emoji: '✨', text: '感恩小确幸' },
  { emoji: '🎯', text: '聊聊小目标' },
  { emoji: '🍀', text: '今天运气不错' },
  { emoji: '☀️', text: '晒晒太阳充充电' },
  { emoji: '🌸', text: '被美好治愈了' },
  { emoji: '🎉', text: '值得庆祝的事' },
  { emoji: '🤗', text: '想找人抱抱' },
  { emoji: '📝', text: '记录一下心情' },
  { emoji: '🎵', text: '想听歌放松下' },
  { emoji: '🌙', text: '夜猫子还没睡' },
]

const quickScroll = ref(null)
let isDragging = false
let dragStartX = 0
let dragScrollLeft = 0

function onQuickWheel(e) {
  if (!quickScroll.value) return
  // 垂直滚轮转为水平滚动
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
  const walk = (x - dragStartX) * 1.2
  quickScroll.value.scrollLeft = dragScrollLeft - walk
}

function onQuickMouseUp() {
  isDragging = false
  if (quickScroll.value) quickScroll.value.style.cursor = 'grab'
}

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
  loadStats()
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

onMounted(() => { tick(); timer = setInterval(tick, 30000); refreshWeather(); window.addEventListener('resize', onResize); buildStatusCalendar(); loadStats() })
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


/* ═══════════ 复访引导：每日仪式 + 首次提示 ═══════════ */
.engagement-stack {
  position: absolute;
  top: 112px;
  left: 22px;
  z-index: 32;
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: min(300px, calc(100vw - 44px));
  pointer-events: none;
}
.daily-ritual-card,
.first-run-guide {
  pointer-events: auto;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(18, 24, 32, 0.58);
  color: #fff;
  box-shadow: 0 10px 26px rgba(0,0,0,0.24);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.daily-ritual-card {
  padding: 14px 15px 15px;
}
.ritual-kicker {
  font-size: 12px;
  color: rgba(255,255,255,0.68);
  margin-bottom: 5px;
}
.ritual-title {
  font-size: 16px;
  line-height: 1.35;
  font-weight: 700;
  text-wrap: pretty;
}
.ritual-copy {
  margin: 7px 0 12px;
  color: rgba(255,255,255,0.78);
  font-size: 13px;
  line-height: 1.55;
}
.ritual-action,
.guide-primary {
  border: none;
  border-radius: 999px;
  padding: 8px 13px;
  background: rgba(255, 230, 178, 0.92);
  color: #2f2114;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease;
}
.ritual-action:hover,
.guide-primary:hover {
  transform: translateY(-1px);
  background: #fff0c6;
}
.first-run-guide {
  position: relative;
  padding: 14px 15px 15px;
}
.guide-close {
  position: absolute;
  top: 8px;
  right: 10px;
  border: none;
  background: transparent;
  color: rgba(255,255,255,0.58);
  font-size: 18px;
  cursor: pointer;
}
.guide-title {
  padding-right: 24px;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.4;
}
.guide-steps {
  margin: 10px 0 12px;
  padding-left: 18px;
  color: rgba(255,255,255,0.78);
  font-size: 12px;
  line-height: 1.7;
}
@media (max-width: 520px) {
  .engagement-stack {
    top: 96px;
    left: 12px;
    right: 12px;
    width: auto;
  }
  .first-run-guide {
    display: none;
  }
  .daily-ritual-card {
    padding: 12px 13px;
  }
  .ritual-title {
    font-size: 15px;
  }
  .ritual-copy {
    font-size: 12px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .ritual-action,
  .guide-primary {
    transition: none;
  }
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
  display: flex; align-items: center; justify-content: center; gap: 12px;
}
.splash-version {
  font-size: 14px; font-weight: 700;
  padding: 4px 12px; border-radius: 10px;
  background: linear-gradient(135deg, #8B5CF6, #6366F1);
  color: white; letter-spacing: 1px;
  box-shadow: 0 2px 12px rgba(139, 92, 246, 0.35);
  flex-shrink: 0;
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

/* 全局音乐开关 */
.global-music-btn {
  position: absolute; top: 12px; right: 12px; z-index: 35;
  width: 36px; height: 36px; border-radius: 50%;
  background: rgba(0,0,0,0.25); border: none;
  backdrop-filter: blur(6px); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; transition: all 0.2s;
}
.global-music-btn:hover { background: rgba(0,0,0,0.4); transform: scale(1.1); }

/* ═══════════ 天气浮层 ═══════════ */
.weather-float {
  position: absolute; top: 18%; left: 8%; z-index: 20;
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; padding: 4px 12px; border-radius: 12px;
  backdrop-filter: blur(10px);
  cursor: pointer; transition: transform 0.2s;
}
.weather-float:hover { transform: scale(1.05); }

/* ═══════════ 音乐按钮（已移至热区） ═══════════ */
.music-toggle-btn {
  display: flex; align-items: center; gap: 4px;
  background: rgba(255,255,255,0.08); border: none;
  color: rgba(232,226,216,0.6); border-radius: 10px;
  padding: 4px 10px; font-size: 11px; cursor: pointer;
  transition: all 0.2s;
}
.music-toggle-btn:hover { background: rgba(255,255,255,0.15); color: #E8E2D8; }

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
.zone-bed     { bottom: 20%; left: 8%; width: 26%; height: 20%; transform: rotate(-38deg); }
.zone-window  { top: 14%; left: 12%; width: 30%; height: 33%; transform: rotate(-15deg); }
.zone-speaker { width: 3%; height: 10%; border-radius: 30%; }
.zone-speaker-left { top: 45%; left: 38.6%; }
.zone-speaker-right { top: 44%; right: 45%; }
.zone-speaker .hover-tip { font-size: 10px; opacity: 0; transition: opacity 0.3s; white-space: nowrap; }
.zone-speaker:hover .hover-tip { opacity: 1; }

/* ── 音响热区 — 音符飘浮动画 ── */
.zone-speaker { overflow: visible; }
.zone-speaker .speaker-notes { display: none; }
.zone-speaker:hover .speaker-notes { display: block; }
.zone-speaker .speaker-notes .note {
  position: absolute; pointer-events: none;
  font-size: 16px; opacity: 0; filter: drop-shadow(0 0 6px rgba(255,215,0,0.7));
  animation: note-float-up 1.4s ease-out infinite;
}
.zone-speaker .speaker-notes .note.n1 { animation-delay: 0s;   left: -16px; top: 60%; }
.zone-speaker .speaker-notes .note.n2 { animation-delay: 0.25s; left: 14px;  top: 50%; }
.zone-speaker .speaker-notes .note.n3 { animation-delay: 0.5s;  left: -8px;  top: 40%; }
.zone-speaker .speaker-notes .note.n4 { animation-delay: 0.75s; left: 16px;  top: 30%; }
.zone-speaker .speaker-notes .note.n5 { animation-delay: 1.0s;  left: 0px;   top: 20%; }

@keyframes note-float-up {
  0%   { opacity: 0; transform: translateY(0) scale(0.6) rotate(0deg); }
  15%  { opacity: 1; }
  70%  { opacity: 0.7; }
  100% { opacity: 0; transform: translateY(-36px) scale(1.4) rotate(15deg); }
}

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
  display: flex; align-items: center; justify-content: center;
  gap: 10px; padding: 0 0 16px; z-index: 100;
  background: transparent; pointer-events: none;
}
.bottom-nav::before {
  content: ''; position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);
  width: 350px; height: 60px; border-radius: 30px;
  background: rgba(0,0,0,0.25);
  backdrop-filter: blur(24px) saturate(1.4);
  -webkit-backdrop-filter: blur(24px) saturate(1.4);
  border: 1px solid rgba(255,255,255,0.2);
  box-shadow: 0 8px 32px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.1);
}
.bnav-item {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 3px;
  background: none; border: none; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  position: relative; z-index: 1;
  width: 58px; height: 50px; border-radius: 14px;
  color: rgba(255,255,255,0.7); transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
  pointer-events: auto;
}
.bnav-item .icon-wrap {
  width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  background: transparent; border: none;
  transition: all 0.25s;
}
.bnav-item:hover {
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transform: scale(1.05);
}
.bnav-item:active { transform: scale(0.93); }
.bnav-item.active {
  color: #FFFFFF;
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 0 16px rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255,0.12);
}
.bnav-item.active .icon-wrap { background: transparent; border: none; animation: none; }
.bnav-item svg { width: 24px; height: 24px; }
.bnav-item .bnav-label {
  font-size: 13px; font-weight: 600;
  opacity: 1; letter-spacing: 0.5px;
  transition: opacity 0.2s;
  text-shadow: 0 1px 3px rgba(0,0,0,0.18);
}
.bnav-item.active .bnav-label { opacity: 1; font-weight: 600; }
@keyframes tab-bounce {
  0%   { transform: scale(1); }
  40%  { transform: scale(1.1); }
  100% { transform: scale(1); }
}

/* 白天 */
.day .bottom-nav::before { background: rgba(255,255,255,0.55); backdrop-filter: blur(24px) saturate(1.6); -webkit-backdrop-filter: blur(24px) saturate(1.6); border-color: rgba(255,255,255,0.5); box-shadow: 0 8px 32px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.7); }
.day .bnav-item           { color: rgba(30,35,40,0.90); }
.day .bnav-item:hover     { color: rgba(10,15,20,1.0); background: rgba(255,255,255,0.2); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.day .bnav-item.active    { color: rgba(10,15,20,1.0); background: rgba(255,255,255,0.35); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); box-shadow: 0 0 16px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.5); }
/* 傍晚 */
.evening .bottom-nav::before { background: rgba(40,30,20,0.3); backdrop-filter: blur(24px) saturate(1.3); -webkit-backdrop-filter: blur(24px) saturate(1.3); border-color: rgba(255,255,255,0.15); box-shadow: 0 8px 32px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.08); }
.evening .bnav-item       { color: rgba(255,255,255,0.7); }
.evening .bnav-item:hover { color: rgba(255,255,255,0.85); background: rgba(255,255,255,0.08); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.evening .bnav-item.active{ color: #FFFFFF; background: rgba(255,255,255,0.15); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); box-shadow: 0 0 16px rgba(255,255,255,0.04), inset 0 1px 0 rgba(255,255,255,0.1); }
/* 夜晚 */
.night .bottom-nav::before { background: rgba(0,0,0,0.25); backdrop-filter: blur(24px) saturate(1.4); -webkit-backdrop-filter: blur(24px) saturate(1.4); border-color: rgba(255,255,255,0.2); box-shadow: 0 8px 32px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.1); }
.night .bnav-item         { color: rgba(255,255,255,0.7); }
.night .bnav-item:hover   { color: rgba(255,255,255,0.9); background: rgba(255,255,255,0.08); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.night .bnav-item.active  { color: #FFFFFF; background: rgba(255,255,255,0.15); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); box-shadow: 0 0 16px rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255,0.12); }

/* ═══════════ 治愈面板 ═══════════ */
.healing-panel { padding-top: 14px; max-height: 82vh; overflow-y: auto; }

/* ═══════════ 树洞面板 ═══════════ */
.treehole-panel { padding-top: 14px; max-height: 82vh; overflow-y: auto; }

/* ═══════════ 报告面板 ═══════════ */
.report-panel { padding-top: 14px; max-height: 82vh; overflow-y: auto; }
.inline-gen-btn {
  display: block; width: 100%; padding: 14px;
  background: linear-gradient(135deg, rgba(127,179,166,0.3), rgba(212,119,106,0.3));
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 14px; color: #E8E2D8;
  font-size: 15px; font-weight: 600; cursor: pointer;
  margin-bottom: 16px; transition: all 0.2s;
}
.inline-gen-btn:hover { transform: scale(1.02); box-shadow: 0 4px 20px rgba(127,179,166,0.15); }
.inline-gen-btn:disabled { opacity: 0.5; cursor: wait; }
.report-content { display: flex; flex-direction: column; gap: 16px; }
.report-section {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 14px 16px;
}
.report-section h3 { font-size: 14px; color: #E8E2D8; margin-bottom: 8px; }
.report-summary { font-size: 13px; color: rgba(232,226,216,0.7); line-height: 1.7; }
.report-suggestions {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: 8px;
}
.report-suggestions li {
  font-size: 13px; color: rgba(232,226,216,0.7);
  padding-left: 16px; position: relative; line-height: 1.6;
}
.report-suggestions li::before {
  content: '•'; position: absolute; left: 0; color: #7FB3A6;
}
.report-affirmation {
  font-size: 14px; color: #E8C468; font-style: italic;
  text-align: center; line-height: 1.8;
}
.report-back-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%; padding: 12px; border-radius: 12px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
  color: rgba(232,226,216,0.6); font-size: 14px; cursor: pointer;
  transition: all 0.2s; margin-top: 8px;
}
.report-back-btn:hover { background: rgba(255,255,255,0.1); color: #E8E2D8; }

/* 报告生成入口 — 温馨引导 */
.report-intro {
  padding: 8px 16px 24px;
  text-align: center;
}
.report-intro-quote {
  margin-bottom: 20px;
}
.report-intro-quote p {
  display: inline;
  font-size: 15px; color: rgba(232,226,216,0.5);
  font-style: italic; line-height: 1.6;
}
.rq-mark {
  font-size: 22px; color: rgba(127,179,166,0.35);
  vertical-align: middle; margin: 0 6px;
}
.report-intro-highlights {
  display: flex; align-items: center; justify-content: center;
  gap: 0; margin-bottom: 20px;
}
.rhi-item {
  display: flex; flex-direction: column; align-items: center;
  padding: 0 18px;
}
.rhi-num {
  font-size: 28px; font-weight: 700; color: #E8E2D8;
  line-height: 1.2;
}
.rhi-label {
  font-size: 11px; color: rgba(232,226,216,0.35);
  margin-top: 2px; letter-spacing: 1px;
}
.rhi-divider {
  width: 1px; height: 32px; background: rgba(255,255,255,0.06);
}
.report-intro-text {
  font-size: 13px; color: rgba(232,226,216,0.5);
  line-height: 1.8; margin-bottom: 24px;
}
.report-intro-btn {
  width: 100%; max-width: 260px; padding: 12px;
  background: #7FB3A6; border: none; border-radius: 12px;
  color: #1A1A1E; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
}
.report-intro-btn:hover {
  background: #8EC4B6; transform: scale(1.02);
}
.report-intro-btn:disabled { opacity: 0.5; cursor: wait; }

/* 报告空状态 */
.report-empty {
  display: flex; flex-direction: column; align-items: center;
  text-align: center; padding: 24px 16px 32px;
}
.report-empty-art {
  position: relative; margin-bottom: 20px;
}
.re-seed {
  font-size: 48px; display: block;
  animation: seedFloat 3s ease-in-out infinite;
}
.re-soil {
  width: 40px; height: 4px;
  background: rgba(127,179,166,0.2);
  border-radius: 2px; margin: 4px auto 0;
}
@keyframes seedFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.report-empty-title {
  font-size: 17px; font-weight: 600; color: #E8E2D8;
  margin-bottom: 10px;
}
.report-empty-text {
  font-size: 13px; color: rgba(232,226,216,0.4);
  line-height: 1.8; margin-bottom: 24px;
}
.report-empty-btn {
  width: 100%; max-width: 240px; padding: 12px;
  background: transparent; border: 1px solid rgba(127,179,166,0.35);
  border-radius: 12px; color: #7FB3A6;
  font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
}
.report-empty-btn:hover {
  background: rgba(127,179,166,0.08);
  border-color: rgba(127,179,166,0.55);
}

/* 报告加载 */
.report-loading {
  display: flex; flex-direction: column; align-items: center;
  padding: 48px 16px;
}
.rl-dots {
  display: flex; gap: 6px; margin-bottom: 16px;
}
.rl-dots span {
  width: 6px; height: 6px;
  background: rgba(127,179,166,0.4);
  border-radius: 1px;
  animation: rlPulse 1.2s infinite both;
}
.rl-dots span:nth-child(2) { animation-delay: 0.2s; }
.rl-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes rlPulse {
  0%,80%,100% { opacity: 0.3; transform: scale(1); }
  40% { opacity: 1; transform: scale(1.2); }
}
.rl-text {
  font-size: 12px; color: rgba(232,226,216,0.4);
  font-family: 'Courier New', monospace;
  letter-spacing: 1px;
}

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
.pdist-row { display: flex; align-items: center; gap: 8px; transition: background 0.2s; border-radius: 8px; padding: 3px 4px; position: relative; }
.pdist-row:hover { background: rgba(255,255,255,0.05); }
.pdist-row.is-top { background: rgba(255,255,255,0.07); }
.pdist-emoji { font-size: 16px; width: 22px; text-align: center; }
.pdist-label { width: 36px; font-size: 13px; color: #D0C8C0; flex-shrink: 0; }
.pdist-row.is-top .pdist-label { color: #F0EAE0; font-weight: 600; }
.pdist-track { flex: 1; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; }
.pdist-fill { height: 100%; border-radius: 3px; transition: width 0.8s ease; }
.pdist-pct { width: 34px; font-size: 11px; color: rgba(200,200,200,0.5); text-align: right; }
.pdist-row.is-top .pdist-pct { color: rgba(220,220,220,0.8); font-weight: 600; }
/* 自定义tooltip */
.pdist-tooltip {
  position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%);
  margin-bottom: 8px; padding: 8px 14px;
  background: rgba(30,28,26,0.95); color: rgba(230,220,210,0.92);
  border: 1px solid rgba(255,255,255,0.15); border-radius: 10px;
  font-size: 11px; line-height: 1.5; white-space: nowrap;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  z-index: 300; pointer-events: none;
}
.pdist-tooltip-arrow {
  position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
  width: 0; height: 0;
  border-left: 6px solid transparent; border-right: 6px solid transparent;
  border-top: 6px solid rgba(30,28,26,0.95);
}
.tip-fade-enter-active, .tip-fade-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.tip-fade-enter-from, .tip-fade-leave-to { opacity: 0; transform: translateX(-50%) translateY(4px); }
.pdist-comfort {
  margin-top: 6px; padding: 10px 12px;
  background: rgba(255,255,255,0.06); border-radius: 10px;
  border-left: 3px solid rgba(255,255,255,0.2);
  font-size: 12px; color: rgba(220,210,200,0.85); line-height: 1.6;
  animation: fadeInUp 0.4s ease;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

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

/* ═══════════ 音乐推荐按钮 ═══════════ */
.music-recommend-btn {
  position: absolute; top: 12%; right: 4%; z-index: 100;
  width: 40px; height: 40px; border-radius: 50%;
  background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.12);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.25s ease;
}
.music-recommend-btn:hover {
  background: rgba(255,255,255,0.25); color: #FFF;
  transform: scale(1.1); box-shadow: 0 4px 20px rgba(212,119,106,0.25);
}
.night .music-recommend-btn {
  background: rgba(0,0,0,0.35); color: rgba(180,200,220,0.6);
  border-color: rgba(255,255,255,0.06);
}
.night .music-recommend-btn:hover { color: rgba(220,235,250,0.9); box-shadow: 0 4px 20px rgba(160,180,220,0.2); }

/* ═══════════ 音乐推荐面板 ═══════════ */
.music-panel {
  padding-top: 14px; max-height: 82vh; overflow-y: auto;
  position: relative;
}
.music-panel .trend-header .emotion-badge {
  display: inline-block; padding: 1px 8px; border-radius: 10px;
  background: rgba(212,119,106,0.2); color: #E8C468;
  font-weight: 500;
}

/* 算法卡片 */
.algo-card {
  margin: 10px 0 14px; padding: 16px 18px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
}
.algo-title {
  font-size: 13px; font-weight: 600; color: #E8E2D8;
  margin-bottom: 12px; letter-spacing: 0.5px;
}
.algo-factors {
  display: flex; flex-direction: column; gap: 10px;
}
.algo-factor {
  display: flex; flex-direction: column; gap: 4px;
}
.factor-bar-wrap {
  width: 100%; height: 8px; background: rgba(255,255,255,0.06);
  border-radius: 4px; position: relative; overflow: hidden;
}
.factor-bar {
  position: absolute; left: 0; top: 0; bottom: 0;
  background: #D4776A; border-radius: 4px;
  transition: width 0.6s ease;
}
.factor-meta {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 2px;
}
.factor-label {
  font-size: 12px; color: #B8B0A6; font-weight: 500;
}
.factor-w {
  font-size: 12px; color: #E8C468; font-weight: 700;
}

/* 推荐歌单卡片 */
.music-list {
  display: flex; flex-direction: column; gap: 8px;
  padding: 0 0 16px;
}
.music-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.25s ease;
}
.music-card:hover {
  background: rgba(255,255,255,0.07);
  border-color: rgba(255,255,255,0.1);
}
.music-card.is-top {
  background: rgba(212,119,106,0.08);
  border-color: rgba(212,119,106,0.18);
}
.music-card.is-expanded {
  background: rgba(255,255,255,0.06);
}

/* 卡片头部 */
.mc-header {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 14px; cursor: pointer;
  transition: background 0.2s;
}
.mc-header:hover { background: rgba(255,255,255,0.04); }
.mc-rank {
  width: 32px; height: 32px; display: flex;
  align-items: center; justify-content: center;
  flex-shrink: 0; border-radius: 50%;
  background: rgba(255,255,255,0.06);
}
.is-top .mc-rank { background: rgba(212,119,106,0.15); }
.rank-crown { font-size: 16px; line-height: 1; }
.rank-num {
  font-size: 13px; font-weight: 700; color: #B8B0A6; line-height: 1;
}
.is-top .rank-num { color: #D4776A; }
.mc-style-info { flex: 1; min-width: 0; }
.mc-style-name {
  font-size: 14px; font-weight: 600; color: #E8E2D8;
  margin-bottom: 2px; display: flex; align-items: center; gap: 4px;
}
.mc-emoji { font-size: 16px; }
.mc-reason {
  font-size: 11px; color: #7A756E; line-height: 1.3;
}
.mc-score-wrap {
  display: flex; flex-direction: column; align-items: center;
  flex-shrink: 0; margin-right: 4px;
}
.mc-score-num {
  font-size: 18px; font-weight: 700; line-height: 1;
}
.mc-score-label {
  font-size: 10px; color: #6A645E;
}
.mc-arrow {
  width: 20px; height: 20px; display: flex; align-items: center;
  justify-content: center; color: #6A645E;
  transition: transform 0.25s ease; flex-shrink: 0;
}
.mc-arrow.is-open { transform: rotate(180deg); }

/* 展开内容 */
.mc-expand-enter-active, .mc-expand-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}
.mc-expand-enter-from, .mc-expand-leave-to {
  max-height: 0; opacity: 0;
}
.mc-expand-enter-to, .mc-expand-leave-from {
  max-height: 500px; opacity: 1;
}
.mc-body {
  padding: 4px 14px 14px;
  display: flex; flex-direction: column; gap: 10px;
}

/* ═══════════ Apple Music 风格歌曲卡片 ═══════════ */
.am-song-card {
  display: flex; flex-wrap: wrap; align-items: center; gap: 12px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
  position: relative;
  overflow: hidden;
}
.am-song-card:hover {
  background: rgba(255,255,255,0.07);
  border-color: rgba(255,255,255,0.1);
  transform: translateY(-1px);
}
.am-song-card.is-active {
  background: rgba(142,168,154,0.08);
  border-color: rgba(142,168,154,0.25);
  box-shadow: 0 0 20px rgba(142,168,154,0.08);
}

/* 封面 */
.am-cover-wrap {
  width: 52px; height: 52px; flex-shrink: 0;
  border-radius: 12px; overflow: hidden;
  position: relative;
  background: rgba(255,255,255,0.06);
}
.am-cover {
  width: 100%; height: 100%; object-fit: cover;
  display: block;
}
.am-cover-overlay {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.55);
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(2px);
}
/* EQ 动画条 */
.am-eq-bars {
  display: flex; align-items: flex-end; gap: 3px; height: 20px;
}
.am-eq-bar {
  width: 3px; border-radius: 2px;
  background: #8EA89A;
  animation: eq-dance 0.9s ease-in-out infinite;
}
.am-eq-bar:nth-child(1) { height: 10px; animation-delay: 0s; }
.am-eq-bar:nth-child(2) { height: 18px; animation-delay: 0.2s; }
.am-eq-bar:nth-child(3) { height: 13px; animation-delay: 0.4s; }
.am-eq-bar:nth-child(4) { height: 16px; animation-delay: 0.15s; }
@keyframes eq-dance {
  0%,100% { transform: scaleY(0.6); opacity: 0.6; }
  50% { transform: scaleY(1); opacity: 1; }
}

/* 封面占位符 */
.mc-cover-placeholder {
  width: 52px; height: 52px; border-radius: 12px;
  background: rgba(255,255,255,0.06);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; flex-shrink: 0; color: rgba(255,255,255,0.15);
}

/* 歌曲信息 */
.am-song-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 3px;
}
.am-song-name {
  font-size: 14px; font-weight: 600; color: #EAE4DC;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  letter-spacing: 0.3px;
}
.am-song-artist {
  font-size: 12px; color: #8A847E;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* 操作按钮组 */
.am-actions {
  display: flex; align-items: center; gap: 8px; flex-shrink: 0;
}

/* 播放按钮 */
.am-play-btn {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(142,168,154,0.2); color: #8EA89A;
  border: 1.5px solid rgba(142,168,154,0.3);
  cursor: pointer; transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
  flex-shrink: 0;
}
.am-play-btn:hover {
  background: rgba(142,168,154,0.35); color: #A3C4B0;
  border-color: rgba(142,168,154,0.5);
  transform: scale(1.06);
  box-shadow: 0 0 14px rgba(142,168,154,0.2);
}
.am-play-btn:active { transform: scale(0.96); }
.am-song-card.is-active .am-play-btn {
  background: rgba(142,168,154,0.35); color: #B8DCC2;
  border-color: rgba(142,168,154,0.5);
}

/* 外链按钮 */
.am-link-btn {
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #6A645E; transition: all 0.2s; flex-shrink: 0;
  text-decoration: none;
}
.am-link-btn:hover { color: #B8B0A6; background: rgba(255,255,255,0.08); }

/* 隐藏音频元素（仅用于播放，不可见） */
.am-hidden-audio {
  position: absolute; width: 0; height: 0;
  opacity: 0; pointer-events: none;
}

/* 来源标注 */
.mc-source {
  text-align: center; padding: 10px 0 4px;
  font-size: 10px; color: #4A4540;
  letter-spacing: 0.5px;
}

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
  .music-recommend-btn { top: 14%; right: 6%; width: 44px; height: 44px; }
  .music-panel { max-height: 78vh; }

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
  position: relative;
}
.chat-panel .quick-wrap::after {
  content: '';
  position: absolute; right: 0; top: 0; bottom: 0;
  width: 32px;
  background: linear-gradient(to right, transparent, rgba(25,25,30,0.9));
  pointer-events: none;
}
.chat-panel .quick-scroll {
  display: flex; gap: 8px; padding: 2px 16px 6px; overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  cursor: grab;
}
.chat-panel .quick-scroll:active { cursor: grabbing; }
.chat-panel .quick-scroll::-webkit-scrollbar { display: none; }
.chat-panel .quick-btn {
  white-space: nowrap; flex-shrink: 0;
  padding: 8px 16px; border-radius: 20px;
  background: rgba(255,255,255,0.08); color: #B8B0A6; font-size: 13px;
  border: 1px solid rgba(255,255,255,0.1);
  transition: all 0.2s; display: flex; align-items: center; gap: 6px;
  cursor: pointer; user-select: none; -webkit-user-select: none;
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
  width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.55);
  border: 1px solid rgba(255,255,255,0.08); transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
  cursor: pointer;
}
.chat-panel .voice-btn:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.85); border-color: rgba(255,255,255,0.15); }
.chat-panel .voice-btn.recording {
  background: rgba(255,255,255,0.1); color: #FFFFFF; border-color: rgba(255,255,255,0.3);
  animation: pulse-rec 1s infinite; box-shadow: 0 0 16px rgba(255,255,255,0.15);
}
.chat-panel .rec-wave {
  display: block; width: 18px; height: 18px;
  border: 2.5px solid #D4776A; border-radius: 50%;
  animation: wave 1s infinite;
}
@keyframes wave { 0%{transform:scale(0.8);opacity:1} 100%{transform:scale(1.4);opacity:0} }
@keyframes pulse-rec { 0%,100%{transform:scale(1)} 50%{transform:scale(1.05)} }

.chat-panel .send-btn {
  width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.85);
  border: 1px solid rgba(255,255,255,0.12); transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
  cursor: pointer;
}
.chat-panel .send-btn:hover:not(:disabled) { background: rgba(255,255,255,0.2); color: #FFFFFF; border-color: rgba(255,255,255,0.25); transform: scale(1.04); }
.chat-panel .send-btn:disabled { background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.2); border-color: transparent; }

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

/* ═══════════ 备案信息 ═══════════ */
.beian-footer {
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(18, 24, 32, 0.72);
  border: 1px solid rgba(255,255,255,0.22);
  box-shadow: 0 8px 24px rgba(0,0,0,0.28);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.65);
}
.beian-footer a {
  font-size: 13px;
  color: #fff;
  font-weight: 700;
  text-decoration: none;
  transition: color 0.2s, opacity 0.2s;
  letter-spacing: 0.4px;
  line-height: 1;
}
.beian-footer a:hover {
  color: #fff;
  opacity: 0.86;
}
.beian-link {
  display: inline-flex; align-items: center; gap: 5px;
}
.beian-icon {
  width: 16px; height: 16px; display: inline-block;
}
.beian-divider {
  font-size: 12px;
  color: rgba(255,255,255,0.72);
  font-weight: 700;
}

@media (max-width: 520px) {
  .beian-footer {
    bottom: max(10px, env(safe-area-inset-bottom));
    max-width: calc(100vw - 24px);
    flex-wrap: wrap;
    gap: 5px 8px;
    padding: 7px 10px;
  }
  .beian-footer a {
    font-size: 11px;
    letter-spacing: 0.2px;
  }
  .beian-divider {
    font-size: 11px;
  }
}

/* ══════════ 西安全屏 + 弹窗交互 ══════════ */

/* 全屏容器 & 渐入动画 */
.xian-fade-enter-active { transition: opacity 0.4s ease; }
.xian-fade-leave-active { transition: opacity 0.3s ease; }
.xian-fade-enter-from,
.xian-fade-leave-to { opacity: 0; }

.xian-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: #0a0a0a;
}

/* 全屏背景图 */
.xian-bg-wrap {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.xian-bg-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}
.xian-bg-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.45) 100%);
  pointer-events: none;
}

/* 顶部导航 */
.xian-top-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top));
  background: linear-gradient(to bottom, rgba(0,0,0,0.55), transparent);
}
/* .xian-back-btn moved to bottom with back-home-text */
.xian-top-label {
  flex: 1;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #FFF;
  text-shadow: 0 1px 6px rgba(0,0,0,0.5);
  letter-spacing: 2px;
}
.xian-top-spacer { width: 36px; }

/* ── 单个交互热区 ── */
.xian-hotspot {
  position: absolute;
  top: 84%; left: 32%;
  transform: translate(-50%, -50%);
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

/* 脉冲外环（始终动画吸引注意） */
.hs-outer-ring {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 80px; height: 80px;
  border-radius: 50%;
  border: 2.5px solid rgba(196,163,90,0.35);
  animation: hs-ring-pulse 2.5s ease-out infinite;
}
@keyframes hs-ring-pulse {
  0%   { transform: translate(-50%, -50%) scale(0.7); opacity: 0.9; }
  50%  { transform: translate(-50%, -50%) scale(1.0); opacity: 0.6; }
  100% { transform: translate(-50%, -50%) scale(1.8); opacity: 0; }
}

.hs-inner {
  position: relative;
  z-index: 1;
  width: 72px; height: 72px;
  border-radius: 50%;
  background: rgba(20,20,20,0.8);
  backdrop-filter: blur(8px);
  border: 2px solid rgba(196,163,90,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 28px rgba(196,163,90,0.3);
  animation: hs-glow 2s ease-in-out infinite;
  transition: transform 0.3s, box-shadow 0.3s;
}
@keyframes hs-glow {
  0%, 100% { box-shadow: 0 0 20px rgba(196,163,90,0.3); }
  50%      { box-shadow: 0 0 40px rgba(196,163,90,0.55); }
}
.xian-hotspot:hover .hs-inner {
  transform: scale(1.08);
  box-shadow: 0 0 40px rgba(196,163,90,0.5);
}
.xian-hotspot:active .hs-inner { transform: scale(0.95); }

.hs-emoji {
  font-size: 32px;
  animation: hs-bounce 1.5s ease-in-out infinite;
}
@keyframes hs-bounce {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-4px); }
}

.hs-label {
  margin-top: 16px;
  font-size: 15px; font-weight: 600; color: #FFF;
  text-shadow: 0 1px 8px rgba(0,0,0,0.6);
  letter-spacing: 1px;
}
.hs-sub {
  margin-top: 4px;
  font-size: 12px; color: rgba(255,255,255,0.55);
}

/* 视频热区位置（与皮影热区分开） */
.xian-video-hotspot {
  top: 40%; left: 70%;
}

/* ── 皮影制作弹窗 ── */
.puppet-popup-overlay {
  position: absolute;
  inset: 0; z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  background: rgba(0,0,0,0.45);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

/* 弹窗弹出动画 */
.popup-scale-enter-active { transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1); }
.popup-scale-leave-active { transition: all 0.2s ease; }
.popup-scale-enter-from { opacity: 0; transform: scale(0.85); }
.popup-scale-leave-to   { opacity: 0; transform: scale(0.9); }

.puppet-popup {
  width: 100%;
  max-width: 380px;
  max-height: 85vh;
  background: rgba(22,22,24,0.95);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 28px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,0.5);
}

/* 弹窗头部：步骤圆点 + 关闭按钮 */
.pp-header {
  display: flex;
  align-items: center;
  padding: 18px 20px 12px;
}
.pp-step-dots {
  display: flex; gap: 6px; flex: 1;
}
.pp-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  transition: all 0.35s;
}
.pp-dot.active {
  background: #C4A35A;
}
.pp-dot.current {
  background: #D4B76A;
  box-shadow: 0 0 8px rgba(212,183,106,0.5);
  transform: scale(1.3);
}
.pp-close {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
  border: none; color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.pp-close:hover { background: rgba(255,255,255,0.16); color: #FFF; }

/* 弹窗内容区 */
.pp-body {
  padding: 8px 24px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  overflow-y: auto;
  flex: 1;
}

.pp-visual {
  width: 80px; height: 80px;
  border-radius: 50%;
  background: rgba(255,255,255,0.06);
  border: 1.5px solid rgba(255,255,255,0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  flex-shrink: 0;
}
.pp-emoji {
  font-size: 38px;
  animation: pp-pop 0.5s cubic-bezier(0.34,1.56,0.64,1);
}
@keyframes pp-pop {
  0% { transform: scale(0.3); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

/* 步骤emoji动画 */
.anim-leather .pp-emoji { animation: a-wobble 2s ease-in-out infinite; }
@keyframes a-wobble { 0%,100%{transform:rotate(-3deg)} 50%{transform:rotate(3deg)} }
.anim-draw .pp-emoji { animation: a-bright 2s ease-in-out infinite; }
@keyframes a-bright { 0%,100%{filter:brightness(1)} 50%{filter:brightness(1.3)} }
.anim-carve .pp-emoji { animation: a-shake 0.3s ease-in-out infinite; }
@keyframes a-shake { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-2px)} 75%{transform:translateX(2px)} }
.anim-paint .pp-emoji { animation: a-hue 3s ease-in-out infinite; }
@keyframes a-hue { 0%,100%{filter:hue-rotate(0)} 50%{filter:hue-rotate(30deg)} }
.anim-dry .pp-emoji { animation: a-fade 2s ease-in-out infinite; }
@keyframes a-fade { 0%,100%{opacity:0.7} 50%{opacity:1} }
.anim-assemble .pp-emoji { animation: a-bump 1.5s ease-in-out infinite; }
@keyframes a-bump { 0%,100%{transform:scale(1)} 50%{transform:scale(1.1)} }
.anim-rod .pp-emoji { animation: a-sway 2s ease-in-out infinite; }
@keyframes a-sway { 0%,100%{transform:rotate(-5deg)} 50%{transform:rotate(5deg)} }

.pp-num {
  font-size: 11px; color: #C4A35A; font-weight: 600;
  letter-spacing: 1px; margin-bottom: 6px;
}
.pp-step-title {
  font-size: 20px; font-weight: 700; color: #E8E2D8;
  margin: 0 0 8px;
}
.pp-desc {
  font-size: 13px; line-height: 1.6; color: #B8B0A6;
  margin: 0 0 6px;
}
.pp-detail {
  font-size: 12px; line-height: 1.5; color: #8A847E;
  margin: 0;
}

/* 完成内容 */
.pp-done-body {
  padding-bottom: 12px;
}

/* 弹窗底部 */
.pp-footer {
  padding: 16px 24px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

/* 进度条 */
.pp-progress-bar {
  width: 100%;
}
.pp-progress-bar .pp-track {
  width: 100%; height: 3px;
  background: rgba(255,255,255,0.1);
  border-radius: 2px; overflow: hidden;
}
.pp-progress-bar .pp-fill {
  height: 100%;
  background: linear-gradient(90deg, #C4A35A, #D4B76A);
  border-radius: 2px;
  transition: width 0.5s cubic-bezier(0.4,0,0.2,1);
}

/* 按钮组 */
.pp-btns {
  display: flex; gap: 12px; align-items: center;
}

/* 主按钮 */
.pp-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 12px 36px; border-radius: 22px;
  background: linear-gradient(135deg, #C4A35A, #D4B76A);
  color: #1a1a1a; font-size: 15px; font-weight: 600;
  border: none; cursor: pointer;
  transition: all 0.25s;
  box-shadow: 0 4px 20px rgba(196,163,90,0.25);
}
.pp-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 28px rgba(196,163,90,0.35); }
.pp-btn:active { transform: scale(0.97); }

/* 上一步按钮 */
.pp-btn-prev {
  display: flex; align-items: center; gap: 6px;
  padding: 12px 24px; border-radius: 22px;
  background: rgba(255,255,255,0.08); color: #C8C0B6;
  font-size: 14px; border: 1px solid rgba(255,255,255,0.1);
  cursor: pointer; transition: all 0.2s;
}
.pp-btn-prev:hover { background: rgba(255,255,255,0.14); color: #FFF; }
.pp-btn-prev:active { transform: scale(0.97); }

/* 完成操作按钮 */
.pp-actions {
  display: flex; gap: 10px;
}
.pp-btn-ghost {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 20px; border-radius: 18px;
  background: rgba(255,255,255,0.08); color: #C8C0B6;
  font-size: 13px; border: 1px solid rgba(255,255,255,0.1);
  cursor: pointer; transition: all 0.2s;
}
.pp-btn-ghost:hover { background: rgba(255,255,255,0.14); }
.pp-btn-main {
  padding: 10px 24px; border-radius: 18px;
  background: rgba(196,163,90,0.18); color: #D4B76A;
  font-size: 13px; border: 1.5px solid rgba(196,163,90,0.35);
  cursor: pointer; transition: all 0.2s;
}
.pp-btn-main:hover { background: rgba(196,163,90,0.28); }

/* ── 皮影SVG（弹窗内完成视图） ── */
.xsc-puppet-wrap {
  width: 100px; height: 160px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 12px;
  animation: puppet-pop 0.6s cubic-bezier(0.34,1.56,0.64,1);
  flex-shrink: 0;
}
@keyframes puppet-pop {
  0% { transform: scale(0); opacity: 0; }
  60% { transform: scale(1.15); }
  100% { transform: scale(1); opacity: 1; }
}
.xsc-puppet-svg {
  width: 100%; height: 100%;
  filter: drop-shadow(0 0 12px rgba(196,163,90,0.3));
  animation: puppet-float 3s ease-in-out infinite;
}
@keyframes puppet-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.xsc-puppet-svg path,
.xsc-puppet-svg circle,
.xsc-puppet-svg rect,
.xsc-puppet-svg ellipse,
.xsc-puppet-svg line {
  stroke-dasharray: 200;
  stroke-dashoffset: 200;
  animation: svg-draw 2s ease-out forwards;
}
@keyframes svg-draw { to { stroke-dashoffset: 0; } }

/* ── 视频播放弹窗 ── */
.video-player-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
}
.video-player-card {
  width: 100%;
  max-width: 640px;
  background: rgba(30,30,30,0.92);
  backdrop-filter: blur(16px);
  border-radius: 16px;
  border: 1px solid rgba(196,163,90,0.3);
  overflow: hidden;
  box-shadow: 0 16px 64px rgba(0,0,0,0.5);
  animation: popup-scale-in 0.35s cubic-bezier(0.34,1.56,0.64,1);
}
@keyframes popup-scale-in {
  0%   { transform: scale(0.85); opacity: 0; }
  100% { transform: scale(1);    opacity: 1; }
}
.vp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: rgba(255,255,255,0.04);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.vp-title {
  font-size: 15px;
  font-weight: 600;
  color: #C8C0B6;
  letter-spacing: 1px;
}
.vp-close {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
  border: none;
  color: #C8C0B6;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.vp-close:hover { background: rgba(255,255,255,0.16); }
.vp-body { padding: 0; }
.vp-video { width: 100%; display: block; background: #000; }

/* ── 洛阳特定样式 ── */
.luoyang-video-hotspot {
  top: 40%; left: 70%;
}
.pp-rubbing-result {
  margin: 16px 0;
  padding: 16px;
  background: rgba(255,255,255,0.04);
  border-radius: 12px;
  border: 1px solid rgba(196,163,90,0.15);
}

/* 移动端适配 */
@media (max-width: 480px) {
  .puppet-popup { max-width: 340px; border-radius: 24px; }
  .pp-body { padding: 6px 20px 16px; }
  .pp-visual { width: 68px; height: 68px; }
  .pp-emoji { font-size: 32px; }
  .pp-step-title { font-size: 18px; }
  .video-player-card { border-radius: 12px; }
  .vp-header { padding: 10px 14px; }
  .vp-title { font-size: 13px; }
}

/* ═══════════ 修改密码弹窗 ═══════════ */
.pwd-modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.55);
  display: flex; align-items: center; justify-content: center;
  z-index: 200;
}
.pwd-modal-card {
  background: #1E1E24; border-radius: 20px; padding: 28px 24px 20px;
  width: 300px; box-shadow: 0 12px 40px rgba(0,0,0,0.35);
}
.pwd-modal-card h4 { margin: 0 0 18px; font-size: 18px; color: #E8E2D8; text-align: center; }
.pwd-modal-card input {
  width: 100%; padding: 10px 14px; border: 1.5px solid rgba(255,255,255,0.08);
  border-radius: 10px; font-size: 14px; outline: none; margin-bottom: 12px;
  box-sizing: border-box; background: rgba(255,255,255,0.03); color: #E8E2D8;
  transition: border-color 0.2s;
}
.pwd-modal-card input::placeholder { color: rgba(232,226,216,0.3); }
.pwd-modal-card input:focus { border-color: #7FB3A6; }
.pwd-modal-btns { display: flex; gap: 10px; margin-top: 4px; }
.pwd-modal-cancel {
  flex: 1; padding: 10px; border-radius: 10px; font-size: 14px;
  background: rgba(255,255,255,0.06); color: #D0C8C0; text-align: center;
  border: none; cursor: pointer; transition: background 0.2s;
}
.pwd-modal-cancel:hover { background: rgba(255,255,255,0.1); }
.pwd-modal-confirm {
  flex: 1; padding: 10px; border-radius: 10px; font-size: 14px;
  background: #7FB3A6; color: #1A1A1E; text-align: center;
  border: none; cursor: pointer; font-weight: 600;
  transition: background 0.2s;
}
.pwd-modal-confirm:hover { background: #8EC4B6; }
.pwd-modal-msg { text-align: center; margin: 12px 0 0; font-size: 13px; }
.pwd-modal-msg.success { color: #7FB3A6; }
.pwd-modal-msg.error { color: #D4776A; }

/* ═══════════ 洛阳地铁转场动画 ═══════════ */
.metro-transition {
  position: fixed; inset: 0; z-index: 300;
  overflow: hidden;
}

/* 背景图片 */
.metro-bg {
  position: absolute; inset: 0;
  transition: filter 1.2s ease, transform 1.2s ease;
}
.metro-bg img {
  width: 100%; height: 100%; object-fit: cover;
}

/* 两侧窗外模糊 — 模拟运动感 */
.metro-window {
  position: absolute; top: 0; bottom: 0; width: 22%;
  opacity: 0; transition: opacity 0.8s ease;
  background: linear-gradient(to right, rgba(255,255,255,0), rgba(255,255,255,0));
}
.metro-window-left { left: 0; }
.metro-window-right { right: 0; }

/* Phase 1~3: 运动感启动，窗外模糊 */
.phase-1 .metro-window,
.phase-2 .metro-window,
.phase-3 .metro-window {
  opacity: 1;
}
.phase-1 .metro-window-left,
.phase-2 .metro-window-left,
.phase-3 .metro-window-left {
  animation: window-blur-left 1.2s ease-in-out infinite;
  background: linear-gradient(to right, rgba(200,220,255,0.08), rgba(255,255,255,0));
}
.phase-1 .metro-window-right,
.phase-2 .metro-window-right,
.phase-3 .metro-window-right {
  animation: window-blur-right 1.2s ease-in-out infinite;
  background: linear-gradient(to left, rgba(200,220,255,0.08), rgba(255,255,255,0));
}
@keyframes window-blur-left {
  0%, 100% { backdrop-filter: blur(2px) brightness(1); transform: translateX(0); }
  50% { backdrop-filter: blur(8px) brightness(0.92); transform: translateX(-3px); }
}
@keyframes window-blur-right {
  0%, 100% { backdrop-filter: blur(2px) brightness(1); transform: translateX(0); }
  50% { backdrop-filter: blur(8px) brightness(0.92); transform: translateX(3px); }
}

/* 速度线 */
.speed-lines {
  position: absolute; inset: 0; pointer-events: none;
  opacity: 0; transition: opacity 0.5s ease;
}
.phase-1 .speed-lines,
.phase-2 .speed-lines,
.phase-3 .speed-lines {
  opacity: 1;
}
.sl-line {
  position: absolute; left: -30%; width: 30%; height: 1.5px;
  background: rgba(255,255,255,0.18);
  border-radius: 1px;
  animation: speed-line 0.5s linear infinite;
}
@keyframes speed-line {
  0% { transform: translateX(0) scaleX(0.5); opacity: 0; }
  15% { opacity: 1; }
  100% { transform: translateX(450%) scaleX(1.5); opacity: 0; }
}

/* 加载文字 */
.metro-loading {
  position: absolute; bottom: 14%; left: 50%; transform: translateX(-50%);
  display: flex; flex-direction: column; align-items: center;
  gap: 10px; opacity: 1; transition: opacity 0.5s ease;
}
.phase-2 .metro-loading,
.phase-3 .metro-loading {
  opacity: 0;
}
.ml-train { font-size: 38px; animation: train-bounce 0.9s ease-in-out infinite; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.3)); }
@keyframes train-bounce {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-5px) scale(1.05); }
}
.ml-text { font-size: 15px; color: rgba(255,255,255,0.9); font-weight: 500; letter-spacing: 3px; text-shadow: 0 1px 6px rgba(0,0,0,0.4); }
.ml-track {
  width: 140px; height: 3px; background: rgba(255,255,255,0.12); border-radius: 2px; overflow: hidden;
}
.ml-progress {
  width: 0%; height: 100%; background: #7FB3A6; border-radius: 2px;
  animation: track-progress 3.5s ease-in-out forwards;
}
@keyframes track-progress {
  0% { width: 0%; }
  100% { width: 100%; }
}

/* 整体模糊遮罩 */
.metro-blur-overlay {
  position: absolute; inset: 0;
  backdrop-filter: blur(0px); opacity: 0;
  transition: backdrop-filter 1.2s ease, opacity 0.8s ease;
  background: rgba(0,0,0,0);
}
.phase-2 .metro-blur-overlay {
  backdrop-filter: blur(10px); opacity: 1;
  background: rgba(0,0,0,0.25);
}
.phase-3 .metro-blur-overlay {
  backdrop-filter: blur(24px); opacity: 1;
  background: rgba(0,0,0,0.55);
}

/* 白屏遮罩 */
.metro-white-overlay {
  position: absolute; inset: 0; background: #fff;
  opacity: 0; transition: opacity 0.8s ease;
}
.phase-3 .metro-white-overlay {
  opacity: 1;
}

/* transition 进入/离开 */
.transition-fade-enter-active { transition: opacity 0.3s ease; }
.transition-fade-leave-active { transition: opacity 0.6s ease; }
.transition-fade-enter-from, .transition-fade-leave-to { opacity: 0; }

/* ═══════════ 小工具条 ═══════════ */
.mini-tools-bar {
  position: absolute;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 18px;
  z-index: 12;
}
.mini-tool-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: transform 0.2s, opacity 0.2s;
  opacity: 0.85;
}
.mini-tool-item:hover {
  transform: translateY(-4px) scale(1.1);
  opacity: 1;
}
.mini-tool-emoji {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  border: 1px solid rgba(255,255,255,0.25);
  transition: background 0.2s;
}
.mini-tool-item:hover .mini-tool-emoji {
  background: rgba(255, 255, 255, 0.32);
}
.mini-tool-name {
  font-size: 14px;
  color: #fff;
  font-weight: 600;
  text-shadow: 0 1px 6px rgba(0,0,0,0.6), 0 0 12px rgba(0,0,0,0.4);
  white-space: nowrap;
}

/* ═══════════ 小工具 iframe 弹窗 ═══════════ */
.mini-app-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}
.mini-app-container {
  width: 94vw;
  max-width: 520px;
  height: 85vh;
  border-radius: 20px;
  overflow: hidden;
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 40px rgba(0,0,0,0.4);
}
.mini-app-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #1a1a2e, #2a2a4e);
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.mini-app-back {
  background: rgba(255,255,255,0.12);
  border: none;
  color: #FFF;
  font-size: 14px;
  padding: 6px 14px;
  border-radius: 20px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.mini-app-back:hover { background: rgba(255,255,255,0.22); }
.mini-app-title {
  flex: 1;
  text-align: center;
  color: #FFF;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
}
.mini-app-spacer { width: 70px; }
.mini-app-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}
.mini-app-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #fff;
}
/* 底部遮罩：仅在小空调/小电视时隐藏外部链接文字 */
.mini-app-bottom-mask {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 80px;
  background: rgba(255,255,255,1);
  pointer-events: none;
  z-index: 2;
}
/* ═══════════ 返回按钮加"回家"文字 ═══════════ */
.xian-back-btn {
  width: auto;
  min-width: 36px;
  height: 36px;
  padding: 0 12px;
  border-radius: 18px;
  background: rgba(255,255,255,0.12);
  backdrop-filter: blur(8px);
  border: none;
  color: #FFF;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 13px;
}
.xian-back-btn:hover { background: rgba(255,255,255,0.22); }
.back-home-text {
  font-size: 13px;
  color: #FFF;
  text-shadow: 0 1px 4px rgba(0,0,0,0.4);
}
</style>
