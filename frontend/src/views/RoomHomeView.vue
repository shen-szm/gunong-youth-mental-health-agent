<template>
  <div ref="roomRoot" class="room" :class="timeOfDay" @click="handleRoomPetMove">

    <!-- ══ 欢迎遮罩：点击任意处进入 ══ -->
    <Transition name="splash-fade">
      <div v-if="showSplash" class="splash" @click="enterApp">
        <div class="splash-logo">
          <span>咕哝</span>
          <span class="splash-version">V{{ splashVersion }}</span>
        </div>
        <div class="splash-sub">轻触，开始今天的倾诉</div>
        <div class="splash-hint">点击任意位置进入</div>
      </div>
    </Transition>

    <!-- AI 生成背景图 -->
    <div class="bg-wrap">
      <img class="room-bg" :src="bgImage" alt="温馨房间" />
    </div>

    <!-- 顶部状态条：只保留今日上下文，不再堆叠独立卡片。 -->
    <header v-if="!showSplash" class="room-status-bar">
      <div class="room-status-greeting">
        <time>{{ currentTime }}</time>
        <strong>{{ greeting }}，{{ displayNickname }}</strong>
      </div>
      <button type="button" class="room-status-checkin" :aria-pressed="selectedRoomFeatureId === 'daily'" @click.stop="selectRoomFeature('daily', $event)">
        <span aria-hidden="true">{{ dailyReturnTask.emoji }}</span>
        <span>
          <small>今日状态</small>
          <strong>{{ dailyStatusLabel }}</strong>
        </span>
      </button>
      <button type="button" class="room-status-utility" :aria-label="`刷新天气，当前${temperature}度`" @click.stop="refreshWeather">
        <span aria-hidden="true">{{ weatherEmoji }}</span>
        <span>{{ temperature }}°</span>
      </button>
      <button type="button" class="room-status-utility" :aria-label="musicOn ? '关闭背景音乐' : '开启背景音乐'" @click.stop="toggleMusic">
        <span aria-hidden="true">{{ musicOn ? 'Ⅱ' : '▷' }}</span>
        <span>声音</span>
      </button>
    </header>
    <StudentAgentRail
      v-if="!showSplash && !showLeisurePanel"
      :open="showAgentRail"
      :state="studentAgentState"
      :steps="studentAgentSteps"
      @toggle="toggleAgentRail"
      @close="showAgentRail = false"
    />
    <aside v-if="!showSplash && showFirstRunGuide" class="room-onboarding-cue" aria-live="polite">
      <span class="room-onboarding-step">{{ guideStage === 'mood-card' ? '完成' : guideStage === 'confession' ? '2/2' : '1/2' }}</span>
      <div>
        <strong>{{ guideStage === 'mood-card' ? '第一次倾诉已经被接住' : guideStage === 'confession' ? '把最想说的一句话告诉咕哝' : '先从房间里的电脑开始' }}</strong>
        <small>{{ guideStage === 'mood-card' ? firstRunMoodCard.summary : guideStage === 'confession' ? '倾诉窗口已经准备好。' : '电脑会打开一个安静的倾诉空间。' }}</small>
      </div>
      <button type="button" @click="guideStage === 'mood-card' ? openTreeHoleFromMoodCard() : focusGuideTarget()">
        {{ guideStage === 'mood-card' ? '去树洞看看' : '带我开始' }}
      </button>
      <button v-if="guideStage !== 'mood-card'" type="button" class="room-onboarding-skip" aria-label="跳过首次引导" @click="skipFirstRunGuide">×</button>
    </aside>
    <button
      v-if="!showSplash"
      type="button"
      :class="['room-roaming-pet', { moving: petIsMoving }]"
      :style="{ left: `${roomPetPosition.x}px`, top: `${roomPetPosition.y}px` }"
      :aria-pressed="selectedRoomFeatureId === 'pet'"
      @click.stop="selectRoomFeature('pet', $event)"
    >
      <img :src="selectedPetFrame" :alt="selectedPetVisual.name" />
      <span>{{ petIsMoving ? petRoamingBubble : petCompanionMessage }}</span>
    </button>
    <div v-if="showPetCompanionPanel" class="pet-panel-overlay" @click.self="closeWorkspacePanel('pet')">
      <section class="pet-panel-card pet-playground-card" data-workspace="pet" @keydown.esc="closeWorkspacePanel('pet')">
        <button type="button" class="pet-panel-close" aria-label="关闭宠物互动" @click="closeWorkspacePanel('pet')">×</button>
        <div class="pet-panel-head">
          <div class="pet-panel-avatar" :class="`is-${petMoodStatus}`">
            <img class="pet-panel-frame" :src="selectedPetFrame" :alt="selectedPetVisual.name" />
          </div>
          <div>
            <span class="pet-panel-kicker">宠物互动</span>
            <h3>{{ petAffinityLabel }}</h3>
            <p>{{ petCompanionMessage }}</p>
          </div>
        </div>
        <div class="pet-panel-meta">
          <span>亲密度 {{ petCompanionState.affinity }}</span>
          <span>随时回来都可以</span>
        </div>
        <div class="pet-playground-stage">
          <div class="pet-stage-hint">点击房间任意位置，它会跑过去陪你</div>
          <img class="pet-stage-frame" :src="selectedPetFrame" :alt="selectedPetVisual.name" />
          <div class="pet-stage-bubble">{{ petCompanionMessage }}</div>
        </div>
        <div class="pet-panel-actions">
          <button type="button" @click.stop="petPetting">摸摸它</button>
          <button type="button" @click.stop="feedPetSnack">喂点心</button>
          <button type="button" class="is-primary" @click.stop="talkWithPet">和它说句话</button>
          <button type="button" @click.stop="closeWorkspacePanel('pet')">回到房间</button>
        </div>
        <div class="pet-visual-picker">
          <div class="pet-section-title">
            <span>宠物形象</span>
            <small>选择陪你待机的小伙伴</small>
          </div>
          <div class="pet-visual-list">
            <button
              v-for="visual in PET_VISUALS"
              :key="visual.key"
              type="button"
              :class="['pet-visual-option', { active: selectedPetVisualKey === visual.key }]"
              @click.stop="selectPetVisual(visual.key)"
            >
              <img :src="visual.frames[0]" :alt="visual.name" />
              <strong>{{ visual.name }}</strong>
            </button>
          </div>
        </div>
        <div class="pet-companion-restored">
          <div class="pet-section-title">
            <span>原陪伴角色</span>
            <small>选择一个小伙伴开始聊天</small>
          </div>
          <div class="pet-companion-list">
            <button
              v-for="companion in petCompanions"
              :key="companion.id"
              type="button"
              :class="['pet-companion-option', { active: activePetCompanionId === companion.id }]"
              @click.stop="startPetCompanion(companion)"
            >
              <img :src="companion.image || selectedPetFrame" :alt="companion.name" />
              <span class="pet-companion-emoji">{{ companion.avatar }}</span>
              <strong>{{ companion.name }}</strong>
              <em>{{ companion.desc }}</em>
            </button>
          </div>
          <div class="pet-companion-chat" v-if="petCompanionActive">
            <div class="pet-chat-head">
              <img :src="activePetImage" :alt="activePetCompanion.name" />
              <div>
                <strong>{{ activePetCompanion.name }}</strong>
                <span>正在陪你聊天</span>
              </div>
            </div>
            <div ref="petChatMessages" class="pet-chat-messages">
              <div v-for="(msg, index) in petCompanionMsgs" :key="index" :class="['pet-chat-msg', msg.role]">
                {{ msg.content }}
              </div>
              <div v-if="petCompanionTyping" class="pet-chat-msg assistant">正在想怎么回应你...</div>
            </div>
            <div class="pet-chat-input-row">
              <input v-model="petCompanionInput" placeholder="和它说点什么..." @keyup.enter="sendPetCompanionMsg" />
              <button type="button" @click.stop="sendPetCompanionMsg" :disabled="!petCompanionInput.trim() || petCompanionTyping">发送</button>
            </div>
          </div>
        </div>
      </section>
    </div>
    <!-- 交互热区 — 电脑（倾诉） -->
    <button type="button" :class="['hot-zone zone-monitor', { 'is-guide-target': showFirstRunGuide && guideStage === 'computer', 'is-selected': selectedRoomFeatureId === 'chat' }]" :aria-pressed="selectedRoomFeatureId === 'chat'" aria-label="电脑：打开倾诉空间" @click.stop="selectRoomFeature('chat', $event)">
      <span class="hover-tip">电脑 · 倾诉</span>
      <div v-if="showFirstRunGuide && guideStage === 'computer'" class="guide-target-badge">点这里：倾诉</div>
    </button>

    <!-- 交互热区 — 床（情绪回顾） -->
    <button type="button" :class="['hot-zone zone-bed', { 'is-selected': selectedRoomFeatureId === 'trend' }]" :aria-pressed="selectedRoomFeatureId === 'trend'" aria-label="床头：回顾近期情绪" @click.stop="selectRoomFeature('trend', $event)">
      <span class="bed-label">床头 · 情绪回顾</span>
    </button>

    <!-- 交互热区 — 窗户（悬浮提示） -->
    <button type="button" :class="['hot-zone zone-window', { 'is-selected': selectedRoomFeatureId === 'window' }]" :aria-pressed="selectedRoomFeatureId === 'window'" aria-label="窗户：看看窗外" @click.stop="selectRoomFeature('window', $event)">
      <span class="window-label">窗边 · 看看窗外</span>
    </button>

    <!-- 心岛入口：延续房间像素场景，真正的游戏引擎仅在进入后加载。 -->
    <button
      v-if="!showSplash"
      type="button"
      class="heart-island-door"
      aria-label="进入心岛探索"
      @click.stop="openWorkspacePanel('leisure', $event.currentTarget)"
    >
      <span class="heart-island-door-glow" aria-hidden="true"></span>
      <span class="heart-island-door-copy"><strong>心岛</strong><small>走进去探索</small></span>
    </button>

    <!-- 交互热区 — 音响1（音乐推荐） -->
    <button type="button" :class="['hot-zone zone-speaker zone-speaker-left', { 'is-selected': selectedRoomFeatureId === 'music' }]" :aria-pressed="selectedRoomFeatureId === 'music'" aria-label="音响：打开音乐推荐" @click.stop="selectRoomFeature('music', $event)">
      <span class="hover-tip">音响 · 音乐</span>
      <div class="speaker-notes">
        <span class="note n1">🎵</span>
        <span class="note n2">🎶</span>
        <span class="note n3">♪</span>
        <span class="note n4">🎵</span>
        <span class="note n5">♫</span>
      </div>
    </button>

    <!-- 交互热区 — 音响2（音乐推荐） -->
    <button type="button" :class="['hot-zone zone-speaker zone-speaker-right', { 'is-selected': selectedRoomFeatureId === 'music' }]" :aria-pressed="selectedRoomFeatureId === 'music'" aria-label="音响：打开音乐推荐" @click.stop="selectRoomFeature('music', $event)">
      <span class="hover-tip">音响 · 音乐</span>
      <div class="speaker-notes">
        <span class="note n1">🎶</span>
        <span class="note n2">♫</span>
        <span class="note n3">🎵</span>
        <span class="note n4">♪</span>
        <span class="note n5">🎶</span>
      </div>
    </button>

    <RoomActionBar
      :feature="selectedRoomFeature"
      :moods="dailyCheckInOptions"
      :selected-mood="dailyReturnState.mood"
      @primary="runSelectedRoomFeature"
      @select-mood="selectDailyMood"
      @close="clearRoomFeature"
    />


    <nav class="bottom-nav">
      <button ref="chatNavButton" class="bnav-item" @click="goToChat">
        <div class="icon-wrap">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <span class="bnav-label">倾诉</span>
      </button>
      <button class="bnav-item" @click="openWorkspacePanel('pet', $event.currentTarget)">
        <div class="icon-wrap">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 11c-2.5-2.5-5-1.2-5 1.3 0 2.7 3.1 5.2 9 8.2 5.9-3 9-5.5 9-8.2 0-2.5-2.5-3.8-5-1.3"/>
            <path d="M8.5 7.5 7 4M15.5 7.5 17 4M9 13h.01M15 13h.01"/>
          </svg>
        </div>
        <span class="bnav-label">咕团</span>
      </button>
      <button ref="islandNavButton" class="bnav-item" @click="openWorkspacePanel('leisure', $event.currentTarget)">
        <div class="icon-wrap">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3 5 7v10l7 4 7-4V7z"/>
            <path d="m5 7 7 4 7-4M12 11v10"/>
          </svg>
        </div>
        <span class="bnav-label">探索</span>
      </button>
      <button ref="profileNavButton" class="bnav-item" @click="goProfile">
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
      <div v-if="showProfilePanel" class="profile-overlay" @click.self="closeWorkspacePanel('profile')">
        <div class="profile-panel" data-workspace="profile" role="dialog" aria-modal="true" aria-label="个人空间" @click.stop @keydown.esc="closeWorkspacePanel('profile')">
          <!-- 关闭按钮 -->
          <button type="button" class="panel-close" aria-label="关闭个人空间" @click="closeWorkspacePanel('profile')">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>

          <!-- 头像区 -->
          <div class="panel-hero">
            <div class="panel-avatar">{{ displayNickname[0] }}</div>
            <div class="panel-name">{{ displayNickname }}</div>
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
            <div class="panel-sec-title">更多空间</div>
            <div class="profile-space-grid">
              <button type="button" @click="handleGuideTreeholeTarget">树洞回声<small>看看相似的心情</small></button>
              <button type="button" @click="openWorkspacePanel('report', $event.currentTarget)">情绪报告<small>回顾自己的记录</small></button>
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
      <div v-if="showTransportPanel" class="profile-overlay" @click.self="closeWorkspacePanel('transport')">
        <div class="profile-panel transport-panel" data-workspace="transport" @click.stop @keydown.esc="closeWorkspacePanel('transport')">
          <button type="button" class="panel-close" aria-label="关闭出发方式" @click="closeWorkspacePanel('transport')">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
          <div class="trend-header">
            <h2>🚪 选择出发方式</h2>
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
      <div v-if="showMusicPanel" class="profile-overlay" @click.self="closeWorkspacePanel('music')">
        <div class="profile-panel music-panel" data-workspace="music" @click.stop @keydown.esc="closeWorkspacePanel('music')">
          <button type="button" class="panel-close" aria-label="关闭音乐推荐" @click="closeWorkspacePanel('music')">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </button>

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
      <div v-if="showTrendPanel" class="profile-overlay" @click.self="closeWorkspacePanel('trend')">
        <div class="profile-panel trend-panel" data-workspace="trend" @click.stop @keydown.esc="closeWorkspacePanel('trend')">
          <!-- 关闭按钮 -->
          <button type="button" class="panel-close" aria-label="关闭情绪回顾" @click="closeWorkspacePanel('trend')">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>

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
              <div class="main-score">{{ trendStats.count || 0 }}</div>
              <div class="main-label">自愿记录</div>
              <div class="main-hint">描述性整理，不是心理测评</div>
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
            <div class="card-title">记录标签变化</div>
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
            <div class="card-title">记录标签分布</div>
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
            <div class="card-title">Agent 记录整理</div>
            <div class="insight-content">
              <div v-if="trendInsightLoading" class="insight-loading">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
              <p v-else class="insight-text">{{ trendInsight }}</p>
            </div>
            <button class="refresh-btn" @click="loadTrendInsight" :disabled="trendInsightLoading">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="margin-right:4px"><path d="M17.65 6.35A7.96 7.96 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
              重新整理
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ══ 聊天面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showChatPanel" class="profile-overlay" @click.self="closeWorkspacePanel('chat')">
        <div class="profile-panel chat-panel" data-workspace="chat" @click.stop @keydown.esc="closeWorkspacePanel('chat')">
          <!-- 关闭按钮 -->
          <button class="panel-close" type="button" aria-label="关闭倾诉面板" @click="closeWorkspacePanel('chat')">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>

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
            <button
              class="chat-end-button"
              type="button"
              :disabled="chatLoading || !chatMessages.some(item => item.role === 'user')"
              @click="requestConversationEnd"
            >结束本次倾诉</button>
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

          <section v-if="showEndConfirmation" class="chat-end-confirm" role="status" aria-live="polite">
            <div>
              <strong>要结束本次倾诉并生成小结吗？</strong>
              <span>会整理整段对话；这不是诊断或量表结果。</span>
            </div>
            <div class="chat-end-actions">
              <button type="button" @click="cancelConversationEnd">继续聊</button>
              <button class="chat-end-primary" type="button" @click="completeConversation">生成小结</button>
            </div>
          </section>

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
              <input v-model="chatInput" :placeholder="chatInputPlaceholder" @keyup.enter="sendChatMsg()" :disabled="chatLoading" ref="inputEl"/>
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

    <!-- 倾诉结束后才出现：像素房间中的液态玻璃小结入口 -->
    <Transition name="summary-orb">
      <button
        v-if="summaryStatus !== 'idle' && !showLeisurePanel"
        ref="summaryOrbButton"
        class="student-summary-orb"
        :class="[`is-${summaryStatus}`, { 'has-unread': summaryUnread }]"
        type="button"
        :disabled="summaryStatus === 'processing'"
        :aria-label="summaryOrbLabel"
        :aria-expanded="showSupportDrawer"
        @click="openSummaryDrawer"
      >
        <span class="summary-orb-pixel" aria-hidden="true">
          <img src="/images/logo.jpg" alt="" />
        </span>
        <span class="summary-orb-copy">
          <strong>{{ summaryStatus === 'processing' ? '正在整理' : summaryStatus === 'error' ? '整理失败' : '倾诉小结' }}</strong>
          <small>{{ summaryStatus === 'ready' ? `${conversationSummary?.dominant_emotion || '情绪'} · ${conversationSummary?.intensity || ''}` : summaryStatus === 'error' ? '点此重试' : '请稍候' }}</small>
        </span>
        <span v-if="summaryUnread" class="summary-unread-dot" aria-hidden="true"></span>
      </button>
    </Transition>
    <p class="summary-live-region" aria-live="polite" aria-atomic="true">{{ summaryStatus === 'ready' && summaryUnread ? '本次倾诉小结已经整理完成' : '' }}</p>

    <!-- 倾诉后的可关闭行动抽屉：保留原房间，只在一次对话完成后出现 -->
    <Transition name="support-drawer">
      <aside v-if="showSupportDrawer" class="student-support-drawer" role="dialog" aria-modal="false" aria-labelledby="support-drawer-title" @click.stop @keydown.esc="closeSupportDrawer">
        <button ref="supportCloseButton" class="support-close" type="button" aria-label="关闭倾诉小结" @click="closeSupportDrawer">×</button>

        <template v-if="supportDrawerMode === 'plan' && summaryStatus === 'ready' && conversationSummary">
          <p class="support-eyebrow">本次倾诉小结</p>
          <h2 id="support-drawer-title" ref="supportModeHeading" tabindex="-1">我听到的是——</h2>
          <div class="support-emotion-state" :data-level="conversationSummary.intensity">
            <span class="support-emotion-icon" aria-hidden="true">{{ getEmotionEmoji(conversationSummary.dominant_emotion) }}</span>
            <div><small>主要情绪</small><strong>{{ conversationSummary.dominant_emotion }} · {{ conversationSummary.intensity }}</strong></div>
          </div>
          <p class="support-summary">{{ conversationSummary.summary }}</p>

          <section class="support-evidence" aria-labelledby="support-evidence-title">
            <h3 id="support-evidence-title">我为什么这样理解</h3>
            <ul><li v-for="signal in conversationSummary.signals" :key="signal.message_id">{{ signal.observation }}</li></ul>
          </section>

          <section class="support-need-block">
            <span>你现在可能更需要</span>
            <strong>{{ conversationSummary.support_need }}</strong>
          </section>

          <section v-if="conversationSummary.risk_level === 'professional'" class="support-professional-note" role="note">
            <strong>建议尽快接入真人专业支持</strong>
            <p>这些影响已经不适合只靠自己扛着。今天请告诉一位可信成年人，并请对方协助联系学校心理老师、12356或正规医疗机构。</p>
          </section>

          <section class="support-next-step" aria-live="polite">
            <span>倾诉后的下一步</span>
            <ol><li v-for="(action, index) in conversationSummary.next_steps" :key="action" :class="{ primary: index === 0 }">{{ action }}</li></ol>
            <small v-if="supportFeedback">{{ supportFeedback }}</small>
          </section>

          <p class="support-boundary">{{ conversationSummary.boundary }}</p>
          <div class="support-summary-controls">
            <button class="support-primary" type="button" @click="continueAfterSummary">继续倾诉</button>
            <button type="button" @click="startNewConversation">开始新话题</button>
          </div>
          <button class="support-help-link" type="button" @click="supportDrawerMode = 'help'">我想找人帮忙</button>
          <button class="support-delete-link" type="button" @click="removeConversationSummary">删除本次小结</button>
        </template>

        <template v-else-if="supportDrawerMode === 'plan'">
          <p class="support-eyebrow">倾诉后的下一步</p>
          <h2 id="support-drawer-title" ref="supportModeHeading" tabindex="-1">这次没有整理完成</h2>
          <p class="support-summary">聊天内容还在。你可以继续倾诉，或重新尝试生成小结。</p>
          <button class="support-primary support-submit-help" type="button" @click="completeConversation">重新整理</button>
          <button class="support-help-link" type="button" @click="continueAfterSummary">继续倾诉</button>
        </template>

        <template v-else-if="supportDrawerMode === 'help'">
          <p class="support-eyebrow">把支持接到真人</p>
          <h2 id="support-drawer-title" ref="supportModeHeading" tabindex="-1">你希望谁先来帮忙？</h2>
          <p class="support-summary">只说你愿意说的。你可以先选一位可信成年人，再决定是否把刚才的摘要给对方看。</p>
          <div class="support-person-grid">
            <button v-for="person in ['班主任或老师', '家长或监护人', '其他可信成年人']" :key="person" type="button" :aria-pressed="selectedSupportPerson === person" :class="{ active: selectedSupportPerson === person }" @click="selectedSupportPerson = person">{{ person }}</button>
          </div>
          <label class="support-share-toggle"><input v-model="shareSupportSummary" type="checkbox" /> 把上面的摘要写进求助卡</label>
          <p class="support-send-boundary">系统不会自动通知任何人。确认后会生成一张求助卡，由你决定何时当面给对方看。</p>
          <button class="support-primary support-submit-help" type="button" :disabled="!selectedSupportPerson" @click="confirmHelpRequest">生成求助卡</button>
          <button class="support-help-link" type="button" @click="supportDrawerMode = 'plan'">返回上一步</button>
        </template>

        <template v-else>
          <p class="support-eyebrow">可以当面展示的求助卡</p>
          <h2 id="support-drawer-title" ref="supportModeHeading" tabindex="-1">我想请你先听我说</h2>
          <section class="support-card-preview">
            <span>给 {{ currentHelpCard.person }}</span>
            <p v-if="currentHelpCard.summary">{{ currentHelpCard.summary }}</p>
            <p v-else>我最近遇到了一件自己不太能处理的事，希望你先听我说，再和我一起想下一步。</p>
            <strong>你现在不用马上解决，请先陪我把话说完。</strong>
          </section>
          <p class="support-send-boundary">这张卡不会自动发送。你可以把当前屏幕当面给对方看。</p>
          <button class="support-primary support-submit-help" type="button" @click="closeSupportDrawer">完成并关闭</button>
          <button class="support-help-link" type="button" @click="supportDrawerMode = 'help'">返回修改</button>
        </template>
      </aside>
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

    <!-- ══ 休闲角：游戏与 Agent 进度共用一个工作区 ══ -->
    <Transition name="panel-slide">
      <div v-if="showLeisurePanel" class="profile-overlay leisure-overlay" @click.self="closeWorkspacePanel('leisure')">
        <StudentIslandWorkspace
          v-if="useIslandWorkspace"
          :storage-scope="userStore.userId || ''"
          @close="closeWorkspacePanel('leisure')"
          @fallback="handleIslandFallback"
        />
        <StudentLeisureHub
          v-else
          data-workspace="leisure"
          :storage-scope="userStore.userId || ''"
          @close="closeWorkspacePanel('leisure')"
          @open-healing="openWorkspacePanel('healing')"
        />
      </div>
    </Transition>

    <!-- ══ 树洞面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showTreeHolePanel" class="profile-overlay" @click.self="closeWorkspacePanel('treehole')">
        <div class="profile-panel treehole-panel" data-workspace="treehole" role="dialog" aria-modal="true" aria-label="树洞回声" @click.stop @keydown.esc="closeWorkspacePanel('treehole')">
          <button type="button" class="panel-close" aria-label="关闭树洞" @click="closeWorkspacePanel('treehole')">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
          <TreeHoleView :inline="true" @close="closeWorkspacePanel('treehole')" />
        </div>
      </div>
    </Transition>

    <!-- ══ 报告面板 ══ -->
    <Transition name="panel-slide">
      <div v-if="showReportPanel" class="profile-overlay" @click.self="closeWorkspacePanel('report')">
        <div class="profile-panel report-panel" data-workspace="report" role="dialog" aria-modal="true" aria-label="情绪记录回顾" @click.stop @keydown.esc="closeWorkspacePanel('report')">
          <button type="button" class="panel-close" aria-label="关闭情绪记录回顾" @click="closeWorkspacePanel('report')">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
          <div class="trend-header">
            <h2>📊 情绪报告</h2>
            <p>回顾近期记录与变化，不替代专业评估</p>
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
            <button class="report-empty-btn" @click="closeWorkspacePanel('report'); goToChat()">
              去种下第一颗心情种子 →
            </button>
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
import { ref, computed, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { updateProfile, changePassword } from '../api/user'
import { getMoodStats, getMoodInsight } from '../api/mood'
import {
  completeChatSession,
  deleteChatSummary,
  getChatHistory,
  getLatestChatSummary,
  sendMessage,
  startChatSession,
} from '../api/chat'
import HealingView from './HealingView.vue'
import TreeHoleView from './TreeHoleView.vue'
import StudentAgentRail from '../components/StudentAgentRail.vue'
import RoomActionBar from '../components/RoomActionBar.vue'
import StudentLeisureHub from '../components/StudentLeisureHub.vue'
import StudentIslandWorkspace from '../components/island/StudentIslandWorkspace.vue'

const router = useRouter()
const userStore = useUserStore()
const splashVersion = (import.meta.env.VITE_APP_VERSION || __APP_PACKAGE_VERSION__ || 'local').split('+')[0]
const displayNickname = computed(() => (userStore.nickname || '朋友').replace(/^(?:合成|演示)+|演示$/g, '').trim() || '朋友')

// ═══ 个人中心面板 ═══
const showProfilePanel = ref(false)
const showChatPanel = ref(false)
const showSupportDrawer = ref(false)
const supportCloseButton = ref(null)
const supportModeHeading = ref(null)
const chatNavButton = ref(null)
const islandNavButton = ref(null)
const profileNavButton = ref(null)
const summaryOrbButton = ref(null)
const chatSessionId = ref('')
const summarySessionId = ref('')
const showEndConfirmation = ref(false)
const summaryStatus = ref('idle')
const summaryUnread = ref(false)
const conversationSummary = ref(null)
const showAgentRail = ref(false)
const selectedRoomFeatureId = ref('')
let roomFeatureTrigger = null
let workspaceTrigger = null
let activeWorkspaceKey = ''
const studentAgentState = reactive({
  status: 'standby',
  phase: 'waiting',
  riskLevel: 'unassessed',
  signal: 'continue',
  emotion: '',
  verifiedSteps: [],
  messageCount: 0,
  lastEvent: '等待你开始表达；普通聊天不弹出进度，安全信号会优先提示',
})
const studentAgentSteps = computed(() => {
  const phase = studentAgentState.phase
  const urgent = studentAgentState.status === 'urgent'
  const summaryError = studentAgentState.status === 'error' && phase === 'summary'
  const chatError = phase === 'chat_error'
  const verified = new Set(studentAgentState.verifiedSteps.map(step => step.id))
  const workflowStep = id => studentAgentState.verifiedSteps.find(step => step.id === id)
  const steps = [
    { id: 'understand', label: '理解本轮表达', summary: workflowStep('observation')?.summary || '等待后端核对本轮表达', status: chatError ? 'error' : verified.has('observation') ? 'completed' : phase === 'chat' ? 'running' : 'waiting' },
    { id: 'safety', label: '安全优先分流', summary: workflowStep('safety')?.summary || '检查危机、伤害与需要成人介入的线索', status: urgent ? 'attention' : verified.has('safety') ? 'completed' : 'waiting' },
    { id: 'emotion', label: '本轮情绪线索', summary: workflowStep('emotion')?.summary || '由后端返回本轮可确认的情绪标签', status: urgent ? 'blocked' : verified.has('emotion') ? 'completed' : 'waiting' },
    { id: 'next_step', label: '支持回应编排', summary: phase === 'end_candidate' ? '本轮回应已完成，等待你确认是否生成完整小结' : workflowStep('response')?.summary || '等待安全检查后生成支持回应', status: urgent ? 'blocked' : phase === 'end_candidate' ? 'attention' : verified.has('response') ? 'completed' : 'waiting' },
    { id: 'summary', label: '倾诉后小结', summary: summaryError ? '上次整理未完成，可以安全重试' : '结束后整合完整会话并进行输出审查', status: urgent ? 'blocked' : summaryError ? 'error' : phase === 'summary' ? 'running' : phase === 'complete' ? 'completed' : 'waiting' },
  ]
  return steps
})
function toggleAgentRail() {
  const next = !showAgentRail.value
  if (next) {
    closeRoomWorkspaces('agent')
    clearRoomFeature()
  }
  showAgentRail.value = next
}
const summaryOrbLabel = computed(() => {
  if (summaryStatus.value === 'processing') return '正在整理本次倾诉'
  if (summaryStatus.value === 'error') return '倾诉小结整理失败，打开后可以重试'
  return `打开本次倾诉小结，主要情绪${conversationSummary.value?.dominant_emotion || ''}${conversationSummary.value?.intensity || ''}`
})
const supportDrawerMode = ref('plan')
const editingSupportSummary = ref(false)
const selectedSupportNeed = ref('做一个小行动')
const supportNeeds = ['先被听见', '理清这件事', '做一个小行动']
const supportDraft = ref({ summary: '', actions: [] })
const supportActionIndex = ref(0)
const supportFeedback = ref('')
const selectedSupportPerson = ref('')
const shareSupportSummary = ref(false)
const currentHelpCard = ref({ person: '', summary: '' })
const currentSupportAction = computed(() => {
  if (selectedSupportNeed.value === '先被听见') return '先不用行动，把最想被理解的一句话继续说完'
  if (selectedSupportNeed.value === '理清这件事') return supportDraft.value.actions?.[1] || '把最困扰你的部分写成一句话'
  return supportDraft.value.actions?.[supportActionIndex.value] || '先停一下，照顾好此刻的自己'
})
function focusWithoutScroll(target) {
  target?.focus?.({ preventScroll: true })
}
watch(supportDrawerMode, async () => {
  if (!showSupportDrawer.value) return
  await nextTick()
  focusWithoutScroll(supportModeHeading.value)
})
const showHealingPanel = ref(false)
const showLeisurePanel = ref(false)
const islandFallbackRequested = ref(false)
const studentIslandEnabled = import.meta.env.VITE_STUDENT_ISLAND_ALPHA5 !== '0'
const useIslandWorkspace = computed(() => studentIslandEnabled && !islandFallbackRequested.value)
const showTreeHolePanel = ref(false)
const showReportPanel = ref(false)
const showStatusPicker = ref(false)

function closeRoomWorkspaces(except = '') {
  const panels = roomWorkspacePanels()
  Object.entries(panels).forEach(([key, panel]) => {
    if (key !== except) panel.value = false
  })
  if (except !== 'agent') showAgentRail.value = false
}

function roomWorkspacePanels() {
  return {
    profile: showProfilePanel,
    chat: showChatPanel,
    support: showSupportDrawer,
    healing: showHealingPanel,
    leisure: showLeisurePanel,
    treehole: showTreeHolePanel,
    report: showReportPanel,
    pet: showPetCompanionPanel,
    transport: showTransportPanel,
    music: showMusicPanel,
    trend: showTrendPanel,
  }
}

function openWorkspacePanel(key, trigger = roomFeatureTrigger || document.activeElement) {
  if (key === 'leisure') islandFallbackRequested.value = false
  closeRoomWorkspaces(key)
  selectedRoomFeatureId.value = ''
  const panel = roomWorkspacePanels()[key]
  if (!panel) return
  workspaceTrigger = trigger?.focus ? trigger : workspaceTrigger
  activeWorkspaceKey = key
  panel.value = true
  nextTick(() => {
    const focusTarget = document.querySelector(`[data-workspace="${key}"] .panel-close, [data-workspace="${key}"] .pet-panel-close`)
    focusWithoutScroll(focusTarget)
  })
}

async function handleIslandFallback() {
  islandFallbackRequested.value = true
  await nextTick()
  focusWithoutScroll(document.querySelector('.leisure-hub .leisure-close'))
}

function closeWorkspacePanel(key) {
  const panel = roomWorkspacePanels()[key]
  if (panel) panel.value = false
  if (activeWorkspaceKey !== key) return
  activeWorkspaceKey = ''
  nextTick(() => {
    const fallback = key === 'leisure' ? islandNavButton.value : ['profile', 'treehole', 'report'].includes(key) ? profileNavButton.value : chatNavButton.value
    focusWithoutScroll(workspaceTrigger?.isConnected ? workspaceTrigger : fallback)
  })
}

// ═══ 复访引导：每日仪式 + 首次教学 ═══
const FIRST_RUN_GUIDE_KEY = 'shengyu_first_run_guide_completed_version'
const FIRST_RUN_GUIDE_VERSION = '4.3.0'
const FIRST_RUN_MOOD_CARD_KEY = 'shengyu_first_run_mood_card'
const DAILY_RETURN_STATE_KEY = 'shengyu_daily_return_state'
const PET_COMPANION_STATE_KEY = 'shengyu_pet_companion_v4_5_0'
const PET_VISUAL_KEY = 'shengyu_pet_visual_v4_5_4'
const ROOM_PET_POSITION_KEY = 'shengyu_room_pet_position_v4_5_5'
const COMPANIONSHIP_STREAK_KEY = 'shengyu_companionship_streak'
const LAST_ACTIVE_DATE_KEY = 'shengyu_last_active_date'
const todayKey = new Date().toISOString().slice(0, 10)
const showFirstRunGuide = ref(localStorage.getItem(FIRST_RUN_GUIDE_KEY) !== FIRST_RUN_GUIDE_VERSION)
const guideStage = ref('computer')
const firstRunMoodCard = ref(loadFirstRunMoodCard())
const isFirstRunChatPending = computed(() => showFirstRunGuide.value && guideStage.value === 'confession')
const dailyCheckInOptions = ['很累', '有点烦', '还可以', '轻松', '开心']
const dailyReturnTasks = [
  {
    emoji: '🌿',
    copy: '先不用变好，只要把此刻的感受说清楚一点点。',
    actionText: '去倾诉一分钟',
    action: 'chat',
  },
  {
    emoji: '🌙',
    copy: '看看树洞里有没有相似的心情，让自己知道并不孤单。',
    actionText: '去树洞看看',
    action: 'treehole',
  },
  {
    emoji: '✨',
    copy: '给身体一个很小的照顾：喝水、伸展，或听一首轻一点的歌。',
    actionText: '打开治愈角',
    action: 'healing',
  },
]
const dailyReturnTask = computed(() => {
  const sum = [...todayKey].reduce((total, char) => total + char.charCodeAt(0), 0)
  return dailyReturnTasks[sum % dailyReturnTasks.length]
})
const dailyReturnState = reactive(loadDailyReturnState())
const companionshipStreak = ref(loadCompanionshipStreak())
const petMoodMessages = {
  tired: ['今天有点累的话，先靠着我坐一会儿。', '不用马上恢复精神，我会慢慢陪你。'],
  annoyed: ['烦的时候不用讲清楚全部，先说一句也可以。', '我在这里，先把最吵的那件事放下来。'],
  okay: ['今天能回来看看自己，就已经很好了。', '我们先安静待一分钟。'],
  happy: ['你今天轻一点了，我也跟着开心。', '这份轻松值得被记住。'],
  sleepy: ['夜深了，我陪你把声音放轻一点。', '今天先不用逞强，早点休息也很好。'],
}
const petCompanionState = reactive(loadPetCompanionState())
const showPetCompanionPanel = ref(false)
const PET_VISUALS = [
  { key: 'snorlax', name: '卡比兽', frames: Array.from({ length: 8 }, (_, index) => `/pets/snorlax/frame-${String(index + 1).padStart(2, '0')}.png`) },
  { key: 'bubu', name: '布布', frames: Array.from({ length: 8 }, (_, index) => `/pets/bubu/frame-${String(index + 1).padStart(2, '0')}.png`) },
  { key: 'kabi', name: '卡比', frames: Array.from({ length: 8 }, (_, index) => `/pets/kabi/frame-${String(index + 1).padStart(2, '0')}.png`) },
]
const selectedPetVisualKey = ref(loadPetVisualKey())
const petAnimationFrame = ref(0)
let petAnimationTimer = null
const selectedPetVisual = computed(() => PET_VISUALS.find(visual => visual.key === selectedPetVisualKey.value) || PET_VISUALS[0])
const selectedPetFrame = computed(() => selectedPetVisual.value.frames[petAnimationFrame.value % selectedPetVisual.value.frames.length])

const roomRoot = ref(null)
const roomPetPosition = reactive(loadRoomPetPosition())
const petIsMoving = ref(false)
let petMoveTimer = null
const petRoamingBubble = computed(() => petIsMoving.value ? '我来了' : '点房间，我会过去')

function loadRoomPetPosition() {
  try {
    const saved = JSON.parse(localStorage.getItem(ROOM_PET_POSITION_KEY) || 'null')
    if (saved && Number.isFinite(Number(saved.x)) && Number.isFinite(Number(saved.y))) {
      return safeRoomPetPosition(Number(saved.x), Number(saved.y))
    }
  } catch {}
  return safeRoomPetPosition(window.innerWidth * .72, window.innerHeight * .76)
}
function safeRoomPetPosition(x, y) {
  const minX = Math.max(92, window.innerWidth * .38)
  const maxX = Math.max(minX, window.innerWidth - 58)
  const minY = Math.max(220, window.innerHeight * .58)
  const maxY = Math.max(minY, window.innerHeight - 96)
  return {
    x: Math.min(Math.max(x, minX), maxX),
    y: Math.min(Math.max(y, minY), maxY),
  }
}
function saveRoomPetPosition() {
  localStorage.setItem(ROOM_PET_POSITION_KEY, JSON.stringify({ x: roomPetPosition.x, y: roomPetPosition.y }))
}
function openPetPlayground() {
  openWorkspacePanel('pet')
}
function handleRoomPetMove(event) {
  if (showSplash.value || showPetCompanionPanel.value) return
  const target = event.target
  if (target?.closest?.('button, a, input, textarea, select, .hot-zone, .bottom-nav, .room-status-bar, .room-onboarding-cue, .room-action-bar, .transport-panel, .profile-panel, .chat-panel, .report-panel, .healing-panel, .treehole-panel')) return
  const next = safeRoomPetPosition(event.clientX, event.clientY)
  roomPetPosition.x = next.x
  roomPetPosition.y = next.y
  saveRoomPetPosition()
  petIsMoving.value = true
  if (petMoveTimer) clearTimeout(petMoveTimer)
  petMoveTimer = setTimeout(() => { petIsMoving.value = false }, 720)
}
function loadPetVisualKey() {
  const saved = localStorage.getItem(PET_VISUAL_KEY)
  return PET_VISUALS.some(visual => visual.key === saved) ? saved : 'snorlax'
}
function selectPetVisual(key) {
  if (!PET_VISUALS.some(visual => visual.key === key)) return
  selectedPetVisualKey.value = key
  petAnimationFrame.value = 0
  localStorage.setItem(PET_VISUAL_KEY, key)
  setPetStatus('happy', `${selectedPetVisual.value.name}靠近了一点，准备继续陪你。`)
}
function startPetAnimation() {
  if (petAnimationTimer) clearInterval(petAnimationTimer)
  petAnimationTimer = setInterval(() => {
    petAnimationFrame.value = (petAnimationFrame.value + 1) % selectedPetVisual.value.frames.length
  }, 180)
}

const PET_COMPANION_PROFILES = {
  xiaoqing: {
    id: 'xiaoqing', avatar: '🌸', image: '/pets/snorlax/frame-01.png', name: '温柔学姐「小晴」', shortName: '小晴', desc: '轻柔、耐心，适合想被认真接住的时候。',
    greeting: '我在这里。你可以慢慢说，今天最让你卡住的那件事是什么？',
    replies: {
      default: ['慢慢说，我会认真听完。', '你现在的感受是真实的，也值得被好好对待。', '不用急着变好，先把心里的声音放下来。'],
      sad: ['听起来你真的撑了很久。先深呼吸一下，我们一点点把它说清楚。', '难过不是软弱，它是在提醒你有些需求需要被看见。'],
      anxious: ['焦虑来的时候，先把它拆成一件具体的小事。现在最担心的是什么？', '我们先回到当下：喝口水、放慢呼吸，然后只处理眼前一步。'],
      tired: ['累了就先靠一会儿，不需要马上证明自己。', '你的身体在提醒你要休息，这不是退步。'],
      happy: ['真好，这份开心值得被记住。能告诉我它从哪里来的吗？'],
      hello: ['你好呀，我在。今天想从哪一句开始说？'],
    },
  },
  aze: {
    id: 'aze', avatar: '☀️', image: '/pets/snorlax/frame-01.png', name: '邻家哥哥「阿泽」', shortName: '阿泽', desc: '直接、行动感强，适合需要一点推动和陪跑的时候。',
    greeting: '来了？坐。先别一个人扛，说说现在最难处理的是哪一块。',
    replies: {
      default: ['我听着，先把情况讲清楚。', '稳住，我们先找一个能做的小动作。', '别急着全解决，先解决最靠近你的那一步。'],
      sad: ['难受就先说出来，别憋着。说完我们再想办法。', '低谷不是终点，只是现在这段路比较暗。'],
      anxious: ['担心可以理解。我们把最坏情况、发生概率、你能做什么列出来。', '压力大时先别硬扛，先做一件能立刻完成的小事。'],
      tired: ['累就先停。能量不够的时候，休息本身就是任务。'],
      happy: ['可以啊，这状态就对了。把这个小胜利记下来。'],
      hello: ['在。今天遇到什么事了？'],
    },
  },
  gunong: {
    id: 'gunong', avatar: '🌿', image: '/pets/snorlax/frame-01.png', name: '咕哝', shortName: '咕哝', desc: '更像你的专属情绪小伙伴，陪你倾诉、复盘、恢复一点力量。',
    greeting: '我一直在这里。你不用组织得很完整，先说一句现在最真实的感受就可以。',
    replies: {
      default: ['我听见了。能再多说一点吗？', '这件事对你来说应该不轻松，我们先把它放在桌面上看一看。', '我会陪你说完，不急着给答案。'],
      sad: ['现在不需要马上好起来。先允许自己难过一会儿。', '如果这份难过有名字，它更像委屈、失落，还是无助？'],
      anxious: ['先把注意力拉回现在：你能看到的三样东西是什么？', '焦虑常常把未来放大。我们先确认眼前真正需要处理的一步。'],
      tired: ['今天先降低要求。能好好休息，也是照顾自己的一部分。'],
      happy: ['这份轻松很珍贵。要不要把它记录成今天的一个小亮点？'],
      hello: ['你好，我在。今天想聊聊什么？'],
    },
  },
}
const petCompanions = ref(Object.values(PET_COMPANION_PROFILES).map(({ id, avatar, image, name, desc }) => ({ id, avatar, image, name, desc })))
const activePetCompanionId = ref('gunong')
const petCompanionActive = ref(false)
const petCompanionMsgs = ref([])
const petCompanionInput = ref('')
const petCompanionTyping = ref(false)
const petChatMessages = ref(null)
const activePetCompanion = computed(() => PET_COMPANION_PROFILES[activePetCompanionId.value] || PET_COMPANION_PROFILES.gunong)
const activePetImage = computed(() => selectedPetFrame.value)

function pickPetReply(characterId, userContent) {
  const profile = PET_COMPANION_PROFILES[characterId] || PET_COMPANION_PROFILES.gunong
  const text = String(userContent || '').toLowerCase()
  let category = 'default'
  if (/你好|hi|hello|在吗|在嘛/.test(text)) category = 'hello'
  else if (/开心|高兴|快乐|兴奋|不错|太好了|舒服/.test(text)) category = 'happy'
  else if (/难过|伤心|哭|痛苦|emo|悲伤|失落|抑郁|绝望/.test(text)) category = 'sad'
  else if (/焦虑|紧张|害怕|担心|压力|慌|恐惧|不安/.test(text)) category = 'anxious'
  else if (/累|疲惫|困|睡不着|失眠|没劲/.test(text)) category = 'tired'
  const pool = profile.replies[category] || profile.replies.default
  return pool[Math.floor(Math.random() * pool.length)]
}

async function loadPetCompanions() {
  try {
    const res = await axios.get(`${API}/api/companion/list`)
    if (Array.isArray(res.data?.companions) && res.data.companions.length) {
      petCompanions.value = res.data.companions.map(c => ({ ...c, image: PET_COMPANION_PROFILES[c.id]?.image || selectedPetFrame.value }))
    }
  } catch (e) {
    petCompanions.value = Object.values(PET_COMPANION_PROFILES).map(({ id, avatar, image, name, desc }) => ({ id, avatar, image, name, desc }))
  }
}

async function startPetCompanion(companion = activePetCompanion.value) {
  const id = companion.id || 'gunong'
  activePetCompanionId.value = id
  petCompanionActive.value = true
  petCompanionMsgs.value = []
  bumpPetAffinityOnce('talkDate')
  setPetStatus(petMoodStatus.value, '它坐近了一点，准备认真听你说。')
  const fallbackGreeting = PET_COMPANION_PROFILES[id]?.greeting || '我在这里，想说什么都可以。'
  try {
    const res = await axios.post(`${API}/api/companion/start`, null, { params: { user_id: Number(userStore.userId) || 1, character_id: id } })
    petCompanionMsgs.value.push({ role: 'assistant', content: res.data?.greeting || fallbackGreeting })
  } catch (e) {
    petCompanionMsgs.value.push({ role: 'assistant', content: fallbackGreeting })
  }
  await nextTick()
  if (petChatMessages.value) petChatMessages.value.scrollTop = petChatMessages.value.scrollHeight
}

async function sendPetCompanionMsg() {
  const content = petCompanionInput.value.trim()
  if (!content || petCompanionTyping.value) return
  petCompanionMsgs.value.push({ role: 'user', content })
  petCompanionInput.value = ''
  petCompanionTyping.value = true
  await nextTick()
  if (petChatMessages.value) petChatMessages.value.scrollTop = petChatMessages.value.scrollHeight
  await new Promise(resolve => setTimeout(resolve, 420))
  try {
    const res = await axios.post(`${API}/api/companion/chat`, { user_id: Number(userStore.userId) || 1, character_id: activePetCompanionId.value, content })
    petCompanionMsgs.value.push({ role: 'assistant', content: res.data?.reply || pickPetReply(activePetCompanionId.value, content) })
  } catch (e) {
    petCompanionMsgs.value.push({ role: 'assistant', content: pickPetReply(activePetCompanionId.value, content) })
  } finally {
    petCompanionTyping.value = false
    await nextTick()
    if (petChatMessages.value) petChatMessages.value.scrollTop = petChatMessages.value.scrollHeight
  }
}function loadDailyReturnState() {
  try {
    const saved = JSON.parse(localStorage.getItem(DAILY_RETURN_STATE_KEY) || 'null')
    if (saved?.date === todayKey) {
      return {
        date: todayKey,
        mood: dailyCheckInOptions.includes(saved.mood) ? saved.mood : '',
        completedTask: Boolean(saved.completedTask),
      }
    }
  } catch {}
  return { date: todayKey, mood: '', completedTask: false }
}
function saveDailyReturnState() {
  localStorage.setItem(DAILY_RETURN_STATE_KEY, JSON.stringify({
    date: dailyReturnState.date,
    mood: dailyReturnState.mood,
    completedTask: dailyReturnState.completedTask,
  }))
}

function loadPetCompanionState() {
  try {
    const saved = JSON.parse(localStorage.getItem(PET_COMPANION_STATE_KEY) || 'null')
    if (saved && typeof saved === 'object') {
      return {
        affinity: Number.isFinite(Number(saved.affinity)) ? Number(saved.affinity) : 1,
        lastInteractionDate: saved.lastInteractionDate || '',
        pettedDate: saved.pettedDate || '',
        fedDate: saved.fedDate || '',
        talkDate: saved.talkDate || '',
        taskDate: saved.taskDate || '',
        mood: saved.mood || '',
        status: saved.status || 'okay',
        message: saved.message || '我在这里，想靠近时就来坐坐。',
      }
    }
  } catch {}
  return { affinity: 1, lastInteractionDate: '', pettedDate: '', fedDate: '', talkDate: '', taskDate: '', mood: '', status: 'okay', message: '我在这里，想靠近时就来坐坐。' }
}
function savePetCompanionState() {
  localStorage.setItem(PET_COMPANION_STATE_KEY, JSON.stringify({ ...petCompanionState }))
}
const petMoodStatus = computed(() => {
  if (timeOfDay.value === 'night' && !['很累', '有点烦'].includes(petCompanionState.mood)) return 'sleepy'
  return petCompanionState.status || 'okay'
})
const petAffinityLabel = computed(() => {
  if (petCompanionState.affinity >= 8) return '你们已经很熟悉了'
  if (petCompanionState.affinity >= 4) return '你们正在慢慢熟悉'
  return '它还在慢慢认识你'
})
const petCompanionMessage = computed(() => petCompanionState.message || pickPetMessage(petMoodStatus.value))
const dailyStatusLabel = computed(() => {
  if (dailyReturnState.date === todayKey && dailyReturnState.mood) return dailyReturnState.mood
  return '留下一句话'
})
const roomFeatures = computed(() => ({
  chat: {
    id: 'chat',
    symbol: '▣',
    location: '电脑',
    title: '说说现在的感受',
    description: '正常聊天不会被分析面板打断，结束后由你决定是否生成小结。',
    actionLabel: '开始倾诉',
  },
  trend: {
    id: 'trend',
    symbol: '⌁',
    location: '床头',
    title: '回顾近期的情绪',
    description: '查看近期记录和变化，只呈现已有数据与明确边界。',
    actionLabel: '打开回顾',
  },
  window: {
    id: 'window',
    symbol: '◇',
    location: '窗边',
    title: '换个地方透透气',
    description: '离开房间片刻，看看城市和远方的风景。',
    actionLabel: '看看窗外',
  },
  music: {
    id: 'music',
    symbol: '♫',
    location: '音响',
    title: '听一点适合此刻的声音',
    description: '根据当前时间与已记录状态整理音乐建议。',
    actionLabel: '打开音乐',
  },
  pet: {
    id: 'pet',
    symbol: '·',
    location: selectedPetVisual.value.name,
    title: petAffinityLabel.value,
    description: petCompanionMessage.value,
    actionLabel: '和它待一会',
  },
  daily: {
    id: 'daily',
    symbol: '✦',
    location: '今日状态',
    title: '今天也给自己留一分钟',
    description: dailyReturnTask.value.copy,
    actionLabel: dailyReturnState.mood ? dailyReturnTask.value.actionText : '先选择上方状态',
    actionDisabled: !dailyReturnState.mood,
  },
}))
const selectedRoomFeature = computed(() => roomFeatures.value[selectedRoomFeatureId.value] || null)

function selectRoomFeature(id, event) {
  if (!roomFeatures.value[id]) return
  closeRoomWorkspaces()
  roomFeatureTrigger = event?.currentTarget || roomFeatureTrigger
  selectedRoomFeatureId.value = id
}

function clearRoomFeature(restoreFocus = true) {
  selectedRoomFeatureId.value = ''
  if (restoreFocus) nextTick(() => focusWithoutScroll(roomFeatureTrigger))
}

function runSelectedRoomFeature() {
  const id = selectedRoomFeatureId.value
  if (id === 'daily') {
    if (!dailyReturnState.mood) return
    clearRoomFeature(false)
    completeDailyTask()
    return
  }
  clearRoomFeature(false)
  if (id === 'chat') { handleGuideChatTarget(); return }
  if (id === 'trend') { goToTrend(); return }
  if (id === 'window') { openWorkspacePanel('transport'); return }
  if (id === 'music') { openMusicPanel(); return }
  if (id === 'pet') openPetPlayground()
}

function pickPetMessage(status) {
  const list = petMoodMessages[status] || petMoodMessages.okay
  const seed = todayKey.split('').reduce((sum, ch) => sum + ch.charCodeAt(0), 0) + petCompanionState.affinity
  return list[seed % list.length]
}
function bumpPetAffinityOnce(field, amount = 1) {
  if (petCompanionState[field] !== todayKey) {
    petCompanionState.affinity += amount
    petCompanionState[field] = todayKey
  }
  petCompanionState.lastInteractionDate = todayKey
}
function setPetStatus(status, message) {
  petCompanionState.status = status
  petCompanionState.message = message || pickPetMessage(status)
  petCompanionState.lastInteractionDate = todayKey
  savePetCompanionState()
}
function petPetting() {
  bumpPetAffinityOnce('pettedDate')
  setPetStatus('happy', '它蹭了蹭你，好像认真收到了这份靠近。')
}
function feedPetSnack() {
  bumpPetAffinityOnce('fedDate')
  setPetStatus('happy', '小点心已经收下了，它看起来安心了一点。')
}
async function talkWithPet() {
  showPetCompanionPanel.value = true
  await startPetCompanion(activePetCompanion.value)
}
function updatePetFromMood(option) {
  petCompanionState.mood = option
  if (option === '很累') setPetStatus('tired')
  else if (option === '有点烦') setPetStatus('annoyed')
  else if (option === '轻松' || option === '开心') setPetStatus('happy')
  else setPetStatus('okay')
}

function loadCompanionshipStreak() {
  const saved = Number.parseInt(localStorage.getItem(COMPANIONSHIP_STREAK_KEY) || '0', 10)
  return Number.isFinite(saved) && saved > 0 ? saved : 1
}
function updateCompanionshipStreak() {
  const saved = Number.parseInt(localStorage.getItem(COMPANIONSHIP_STREAK_KEY) || '0', 10)
  const lastActiveDate = localStorage.getItem(LAST_ACTIVE_DATE_KEY)
  if (lastActiveDate === todayKey) return Number.isFinite(saved) && saved > 0 ? saved : 1
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  const nextStreak = lastActiveDate === yesterday && Number.isFinite(saved) && saved > 0 ? saved + 1 : 1
  localStorage.setItem(COMPANIONSHIP_STREAK_KEY, String(nextStreak))
  localStorage.setItem(LAST_ACTIVE_DATE_KEY, todayKey)
  return nextStreak
}
function selectDailyMood(option) {
  dailyReturnState.mood = option
  dailyReturnState.date = todayKey
  saveDailyReturnState()
  updatePetFromMood(option)
  companionshipStreak.value = updateCompanionshipStreak()
}
function completeDailyTask() {
  dailyReturnState.completedTask = true
  dailyReturnState.date = todayKey
  saveDailyReturnState()
  bumpPetAffinityOnce('taskDate')
  setPetStatus('happy', '谢谢你留下这一刻。我会安静陪着你，不需要每天打卡。')
  companionshipStreak.value = updateCompanionshipStreak()
  if (dailyReturnTask.value.action === 'treehole') {
    openWorkspacePanel('treehole')
    return
  }
  if (dailyReturnTask.value.action === 'healing') {
    openWorkspacePanel('healing')
    return
  }
  goToChat()
}
function loadFirstRunMoodCard() {
  try {
    const saved = JSON.parse(localStorage.getItem(FIRST_RUN_MOOD_CARD_KEY) || 'null')
    if (saved?.summary && saved?.suggestion) return saved
    if (saved?.title || saved?.copy) {
      return buildFirstRunMoodCard(saved.copy || saved.title || '', saved)
    }
  } catch {}
  return buildFirstRunMoodCard()
}
function buildFirstRunMoodCard(message = '', reply = {}) {
  const emotion = reply?.emotion || '被认真听见'
  const summary = message ? `你刚刚说的是：“${message.slice(0, 18)}${message.length > 18 ? '…' : ''}”。这份心情已经被好好接住。` : '你已经完成了第一次小倾诉，这份心情已经被好好接住。'
  return {
    emoji: emotion.includes('开') ? '🌤️' : emotion.includes('难') ? '🌧️' : '🌱',
    title: '今日心情卡',
    copy: summary,
    emotion,
    summary,
    suggestion: '去树洞看看，也许会遇到相似的回声。',
  }
}
function completeFirstRunAfterChat(message, reply) {
  if (!showFirstRunGuide.value || guideStage.value !== 'confession' || !reply?.reply) return
  firstRunMoodCard.value = buildFirstRunMoodCard(message, reply)
  localStorage.setItem(FIRST_RUN_MOOD_CARD_KEY, JSON.stringify(firstRunMoodCard.value))
  localStorage.setItem(FIRST_RUN_GUIDE_KEY, FIRST_RUN_GUIDE_VERSION)
  guideStage.value = 'mood-card'
}
function focusGuideTarget() {
  const selector = guideStage.value === 'confession' ? '.chat-panel .input-wrap input' : '.zone-monitor'
  const target = document.querySelector(selector)
  target?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
  if (guideStage.value === 'confession') focusWithoutScroll(inputEl.value)
  else selectRoomFeature('chat')
}
function handleGuideChatTarget() {
  goToChat()
  if (showFirstRunGuide.value && guideStage.value === 'computer') {
    guideStage.value = 'confession'
    nextTick(() => focusWithoutScroll(inputEl.value))
  }
}
function openTreeHoleFromMoodCard() {
  showFirstRunGuide.value = false
  openWorkspacePanel('treehole')
}
function handleGuideTreeholeTarget() {
  openWorkspacePanel('treehole')
  if (showFirstRunGuide.value && guideStage.value === 'mood-card') {
    showFirstRunGuide.value = false
  }
}
function skipFirstRunGuide() {
  showFirstRunGuide.value = false
  localStorage.setItem(FIRST_RUN_GUIDE_KEY, FIRST_RUN_GUIDE_VERSION)
}
const nickname = ref(userStore.nickname || '')
const stats = reactive({ moodCount: 0, chatCount: 0, days: 0 })

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
    const count = res.count || 0

    const topMood = Object.entries(distribution).sort((a, b) => b[1] - a[1])[0]
    const topMoodLabel = topMood ? topMood[0] : '暂无'
    const topMoodCount = topMood ? topMood[1] : 0

    const suggestions = ['从最近一条记录开始，补充当时发生了什么和你希望获得的支持']
    if (topMoodLabel === '焦虑' || topMoodLabel === '紧张') {
      suggestions.push('如果你愿意，可以试试治愈空间的短时呼吸练习，留意它是否适合此刻的你')
    }
    if (topMoodLabel === '悲伤' || topMoodLabel === '低落') {
      suggestions.push('可以继续倾诉，或告诉一位你信任的人现在更希望被怎样陪伴')
    }

    const affirmations = [
      '你已经做得很好了，不必对自己太苛刻',
      '每一天都是新的开始，你值得被温柔以待',
      '感到疲惫也没关系，休息也是前进的一种方式',
      '你的存在本身就有意义',
      '慢慢来，比较快'
    ]

    reportData.value = {
      summary: count
        ? `近30天保存了 ${count} 次学生主动记录，出现较多的自报或系统归纳标签是「${topMoodLabel}」（${topMoodCount} 次）。这只是对已有记录的描述性整理，不是心理测评，也不能代表整体心理状态。`
        : '近30天暂时没有可整理的主动记录。这不代表任何心理状态，也不是心理测评结果。',
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
  openWorkspacePanel('music')
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

const trendScoreColor = computed(() => '#9fc9b6')
const topMood = computed(() => {
  const dist = trendStats.value.distribution || {}
  if (!Object.keys(dist).length) return '--'
  return Object.entries(dist).sort((a, b) => b[1] - a[1])[0][0]
})
const topMoodEmoji = computed(() => {
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😟', '难过': '😢', '愤怒': '😡' }
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
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😟', '难过': '😢', '愤怒': '😡' }
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
  openWorkspacePanel('trend')
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
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😟', '难过': '😢', '愤怒': '😡' }
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
  await userStore.logout()
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
  openWorkspacePanel('profile')
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
  if (timeOfDay.value === 'day') return '/images/白天.png'
  return '/images/夜晚.png'
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
const chatInputPlaceholder = computed(() => isFirstRunChatPending.value ? '把今天最想说的一句话丢给我' : '说说你的感受...')
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
  const map = { '开心': '😊', '平静': '😌', '焦虑': '😟', '难过': '😢', '愤怒': '😡', '疲惫': '😴' }
  return map[emotion] || '🙂'
}

async function sendChatMsg(text) {
  const msg = text || chatInput.value.trim()
  if (!msg || chatLoading.value) return
  chatInput.value = ''
  showEndConfirmation.value = false
  chatMessages.value.push({ role: 'user', content: msg })
  studentAgentState.status = 'running'
  studentAgentState.phase = 'chat'
  studentAgentState.verifiedSteps = []
  studentAgentState.messageCount = chatMessages.value.filter(item => item.role === 'user').length
  studentAgentState.lastEvent = '正在理解这条表达并检查是否需要优先安全协助'
  await nextTick()
  scrollChatBottom()
  chatLoading.value = true
  try {
    if (!chatSessionId.value) {
      const session = await startChatSession(false)
      chatSessionId.value = session.data.session_id
    }
    const res = await sendMessage(Number(userStore.userId), msg, 'text', chatSessionId.value)
    await nextTick()
    if (res.data?.reply) {
      chatMessages.value.push({ role: 'assistant', content: res.data.reply, emotion: res.data.emotion })
      chatSessionId.value = res.data.session_id || chatSessionId.value
      completeFirstRunAfterChat(msg, res.data)
      showEndConfirmation.value = res.data.conversation_signal === 'end_candidate'
      studentAgentState.signal = res.data.conversation_signal || 'continue'
      studentAgentState.emotion = res.data.emotion || ''
      studentAgentState.riskLevel = res.data.risk_level || 'routine'
      studentAgentState.verifiedSteps = Array.isArray(res.data.workflow) ? res.data.workflow : []
      if (studentAgentState.signal === 'urgent') {
        studentAgentState.status = 'urgent'
        studentAgentState.phase = 'urgent'
        studentAgentState.riskLevel = 'urgent'
        studentAgentState.lastEvent = '普通分析已停止，当前优先显示安全协助路径'
        showAgentRail.value = false
      } else {
        studentAgentState.status = 'ready'
        studentAgentState.phase = showEndConfirmation.value ? 'end_candidate' : 'responded'
        studentAgentState.lastEvent = showEndConfirmation.value
          ? '已完成本轮理解，正在等你决定继续聊还是生成小结'
          : '本轮理解与安全检查已完成，可以继续倾诉'
      }
    } else {
      chatMessages.value.push({ role: 'assistant', content: '抱歉，我暂时无法回复，请稍后再试...' })
      studentAgentState.status = 'error'
      studentAgentState.phase = 'chat_error'
      studentAgentState.lastEvent = '本轮没有获得有效结果，聊天内容已保留，可以稍后重试'
    }
  } catch (err) {
    console.error('发送失败:', err)
    chatMessages.value.push({ role: 'assistant', content: '网络异常，请检查连接后重试...' })
    studentAgentState.status = 'error'
    studentAgentState.phase = 'chat_error'
    studentAgentState.lastEvent = '本轮协作未完成，聊天内容已保留，可以稍后重试'
  }
  chatLoading.value = false
  loadStats()
  await nextTick()
  scrollChatBottom()
}

function requestConversationEnd() {
  if (!chatMessages.value.some(item => item.role === 'user') || chatLoading.value) return
  showEndConfirmation.value = true
  studentAgentState.phase = 'end_candidate'
  studentAgentState.lastEvent = '等待你确认是否结束；未确认前不会生成分析小结'
  nextTick(() => scrollChatBottom())
}

function cancelConversationEnd() {
  showEndConfirmation.value = false
  studentAgentState.phase = 'responded'
  studentAgentState.lastEvent = '已继续倾诉，本次会话仍保持打开'
  nextTick(() => focusWithoutScroll(inputEl.value))
}

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
  showChatPanel.value = false
  showSupportDrawer.value = false
  summaryStatus.value = 'processing'
  studentAgentState.status = 'running'
  studentAgentState.phase = 'summary'
  studentAgentState.lastEvent = '正在整合完整会话、生成下一步并复核输出安全性'
  showAgentRail.value = true
  summaryUnread.value = false
  try {
    const res = await completeChatSession(chatSessionId.value)
    if (res.data?.status === 'urgent') {
      summaryStatus.value = 'idle'
      showAgentRail.value = false
      showChatPanel.value = true
      studentAgentState.status = 'urgent'
      studentAgentState.phase = 'urgent'
      studentAgentState.riskLevel = 'urgent'
      studentAgentState.lastEvent = '小结生成已停止，当前优先执行安全协助流程'
      return
    }
    if (!applySummaryResponse(res.data, true)) throw new Error('invalid summary response')
    studentAgentState.status = 'ready'
    studentAgentState.phase = 'complete'
    studentAgentState.riskLevel = res.data.summary?.risk_level || 'routine'
    studentAgentState.emotion = res.data.summary?.dominant_emotion || studentAgentState.emotion
    studentAgentState.messageCount = res.data.metadata?.message_count || studentAgentState.messageCount
    studentAgentState.verifiedSteps = [
      { id: 'observation', status: 'completed', summary: '已整合完整会话中的事件与表达' },
      { id: 'safety', status: 'completed', summary: '已完成整段会话安全复核' },
      { id: 'emotion', status: 'completed', summary: '已完成完整会话情绪线索归纳' },
      { id: 'response', status: 'completed', summary: '已生成并复核支持方案' },
    ]
    studentAgentState.lastEvent = res.data.metadata?.degraded
      ? '小结已通过规则化安全模板完成并可查看'
      : '完整会话小结与下一步已经生成并通过输出复核'
  } catch (err) {
    console.error('小结生成失败:', err)
    summaryStatus.value = 'error'
    studentAgentState.status = 'error'
    studentAgentState.phase = 'summary'
    studentAgentState.lastEvent = '小结整理未完成，聊天记录仍然保留，可以重试'
  }
}

async function openSummaryDrawer() {
  if (summaryStatus.value === 'processing') return
  closeRoomWorkspaces('support')
  clearRoomFeature()
  showSupportDrawer.value = true
  supportDrawerMode.value = 'plan'
  summaryUnread.value = false
  window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  await nextTick()
  focusWithoutScroll(supportCloseButton.value)
}

function closeSupportDrawer() {
  showSupportDrawer.value = false
  editingSupportSummary.value = false
  supportFeedback.value = ''
  nextTick(() => {
    if (summaryOrbButton.value) focusWithoutScroll(summaryOrbButton.value)
    else focusWithoutScroll(chatNavButton.value)
  })
}

async function beginFreshConversation() {
  const res = await startChatSession(true)
  chatSessionId.value = res.data.session_id
  chatMessages.value = []
  chatInput.value = ''
  showEndConfirmation.value = false
  showSupportDrawer.value = false
  showChatPanel.value = true
  resetStudentAgentState()
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
    chatInput.value = ''
    showEndConfirmation.value = false
    showSupportDrawer.value = false
    showChatPanel.value = true
    await nextTick()
    scrollChatBottom()
    focusWithoutScroll(inputEl.value)
  } catch {
    showChatPanel.value = true
  }
}

async function startNewConversation() {
  try { await beginFreshConversation() } catch { showChatPanel.value = true }
}

function resetStudentAgentState() {
  Object.assign(studentAgentState, {
    status: 'standby', phase: 'waiting', riskLevel: 'unassessed', signal: 'continue', emotion: '',
    messageCount: 0, lastEvent: '等待你开始表达；普通聊天不弹出进度，安全信号会优先提示',
    verifiedSteps: [],
  })
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
    focusWithoutScroll(chatNavButton.value)
  } catch (err) {
    console.error('删除小结失败:', err)
    supportFeedback.value = '暂时无法删除，请稍后再试。'
  }
}

function cycleSupportAction() {
  selectedSupportNeed.value = '做一个小行动'
  const total = supportDraft.value.actions?.length || 1
  supportActionIndex.value = (supportActionIndex.value + 1) % total
  supportFeedback.value = '已经换成更轻一点的选择。'
}

function acceptSupportAction() {
  const item = { action: currentSupportAction.value, createdAt: new Date().toISOString(), status: 'accepted' }
  const key = `shengyu_student_micro_actions_${userStore.userId}`
  const previous = readSessionList(key)
  sessionStorage.setItem(key, JSON.stringify([item, ...previous].slice(0, 12)))
  supportFeedback.value = '记下了。只试这一小步就够了。'
}

function declineSupportAction() {
  selectedSupportNeed.value = '先被听见'
  supportFeedback.value = '可以，现在不行动也没关系。咕哝会先陪你把感受放在这里。'
}

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
  const asrUrl = `/api/chat/asr?session_id=${encodeURIComponent(chatSessionId.value || '')}`
  fetch(asrUrl, { method: 'POST', body: new Blob([wavBuffer], { type: 'audio/wav' }), headers: { 'Content-Type': 'audio/wav' } })
    .then(r => r.json())
    .then(data => { if (data.text) sendChatMsg(data.text); else chatMessages.value.push({ role: 'assistant', content: '没有听清，请再说一次~' }) })
    .catch(() => chatMessages.value.push({ role: 'assistant', content: '语音识别失败，请重试...' }))
    .finally(() => { chatLoading.value = false })
  audioChunks = []
}

function playTTS(text) {
  if (!text) return
  fetch('/api/chat/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, session_id: chatSessionId.value || null }) })
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
  openWorkspacePanel('chat')
  chatInput.value = ''
  try {
    const session = await startChatSession(false)
    chatSessionId.value = session.data.session_id
    const res = await getChatHistory(Number(userStore.userId), chatSessionId.value)
    if (res.data?.length) chatMessages.value = res.data
    else chatMessages.value = []
    scrollChatBottom()
  } catch {}
}

async function loadLatestConversationSummary() {
  try {
    const res = await getLatestChatSummary()
    if (applySummaryResponse(res.data, false)) {
      studentAgentState.status = 'ready'
      studentAgentState.phase = 'complete'
      studentAgentState.riskLevel = res.data.summary?.risk_level || 'routine'
      studentAgentState.emotion = res.data.summary?.dominant_emotion || ''
      studentAgentState.messageCount = res.data.metadata?.message_count || 0
      studentAgentState.verifiedSteps = [
        { id: 'observation', status: 'completed', summary: '已整合完整会话中的事件与表达' },
        { id: 'safety', status: 'completed', summary: '已完成整段会话安全复核' },
        { id: 'emotion', status: 'completed', summary: '已完成完整会话情绪线索归纳' },
        { id: 'response', status: 'completed', summary: '已生成并复核支持方案' },
      ]
      studentAgentState.lastEvent = '最近一次倾诉小结可再次查看'
    }
  } catch {}
}

onMounted(() => { tick(); timer = setInterval(tick, 30000); refreshWeather(); window.addEventListener('resize', onResize); buildStatusCalendar(); loadStats(); loadPetCompanions(); startPetAnimation(); loadLatestConversationSummary() })
onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (petAnimationTimer) clearInterval(petAnimationTimer)
  if (petMoveTimer) clearTimeout(petMoveTimer)
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
  top: 108px;
  left: 22px;
  z-index: 32;
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: min(326px, calc(100vw - 44px));
  pointer-events: none;
}
.daily-return-card,
.first-run-guide {
  position: relative;
  overflow: hidden;
  pointer-events: auto;
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.18);
  background: linear-gradient(145deg, rgba(18,24,32,0.72), rgba(48,45,61,0.58));
  color: #fff;
  box-shadow: 0 12px 32px rgba(0,0,0,0.28);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
.daily-return-card {
  padding: 15px;
}
.ritual-glow {
  position: absolute;
  right: -34px;
  top: -42px;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,220,156,0.42), rgba(255,220,156,0));
  pointer-events: none;
}
.ritual-meta-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.ritual-orb {
  width: 42px;
  height: 42px;
  border-radius: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.18);
  font-size: 22px;
}
.ritual-kicker {
  font-size: 12px;
  color: rgba(255,255,255,0.88);
  font-weight: 700;
}
.ritual-date {
  margin-top: 2px;
  font-size: 11px;
  color: rgba(255,255,255,0.58);
}
.ritual-title {
  position: relative;
  font-size: 17px;
  line-height: 1.35;
  font-weight: 800;
  text-wrap: pretty;
}
.ritual-copy {
  position: relative;
  margin: 7px 0 12px;
  color: rgba(255,255,255,0.78);
  font-size: 13px;
  line-height: 1.55;
}
.daily-check-row {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.daily-check-pill {
  border: 1px solid rgba(255,255,255,0.16);
  border-radius: 999px;
  padding: 5px 9px;
  background: rgba(255,255,255,0.09);
  color: rgba(255,255,255,0.78);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, color 0.18s ease;
}
.daily-check-pill:hover,
.daily-check-pill.active {
  transform: translateY(-1px);
  background: rgba(255, 230, 178, 0.94);
  color: #2f2114;
}
.ritual-action,
.guide-option,
.guide-secondary {
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.ritual-action {
  border-radius: 999px;
  padding: 8px 14px;
  background: rgba(255, 230, 178, 0.94);
  color: #2f2114;
  font-size: 13px;
  font-weight: 800;
  transition: transform 0.18s ease, background 0.18s ease;
}
.ritual-action:hover {
  transform: translateY(-1px);
  background: #fff0c6;
}
  .room-roaming-pet {
  position: fixed;
  z-index: 36;
  width: 88px;
  min-height: 92px;
  transform: translate(-50%, -78%);
  border: none;
  background: transparent;
  cursor: pointer;
  transition: left 0.68s cubic-bezier(0.22, 1, 0.36, 1), top 0.68s cubic-bezier(0.22, 1, 0.36, 1), filter 0.2s ease;
  pointer-events: auto;
}
.room-roaming-pet img {
  width: 86px;
  height: 86px;
  object-fit: contain;
  filter: drop-shadow(0 14px 18px rgba(0,0,0,0.34));
}
.room-roaming-pet span {
  position: absolute;
  left: 50%;
  top: -16px;
  transform: translateX(-50%);
  white-space: nowrap;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(38, 30, 42, 0.78);
  color: #fff8e8;
  font-size: 11px;
  font-weight: 800;
  box-shadow: 0 8px 18px rgba(0,0,0,0.2);
  opacity: 0;
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.room-roaming-pet:hover span,
.room-roaming-pet.moving span {
  opacity: 1;
  transform: translate(-50%, -4px);
}
.room-roaming-pet.moving img {
  animation: pet-run-bob 0.34s ease-in-out infinite;
}
@keyframes pet-run-bob {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-6px) scale(1.03); }
}
.pet-companion-card {
  position: fixed;
  right: 24px;
  top: 38%;
  z-index: 32;
  width: min(360px, calc(100vw - 48px));
  overflow: hidden;
  pointer-events: auto;
  display: grid;
  grid-template-columns: 74px 1fr;
  gap: 14px;
  padding: 16px;
  border-radius: 22px;
  border: 1px solid rgba(255, 232, 178, 0.34);
  background: linear-gradient(145deg, rgba(33, 27, 41, 0.88), rgba(70, 52, 62, 0.76));
  color: #fff8e8;
  box-shadow: 0 18px 44px rgba(0,0,0,0.36), 0 0 0 1px rgba(255,255,255,0.05) inset;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}
.pet-companion-card::before {
  content: '';
  position: absolute;
  right: -34px;
  top: -46px;
  width: 128px;
  height: 128px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 214, 126, 0.36), rgba(255, 214, 126, 0));
  pointer-events: none;
}
.pet-orb {
  position: relative;
  width: 74px;
  height: 74px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  background: rgba(255,255,255,0.14);
  border: 1px solid rgba(255,255,255,0.16);
}
.pet-orb.is-happy { background: rgba(255, 208, 112, 0.22); }
.pet-orb.is-tired, .pet-orb.is-annoyed { background: rgba(143, 183, 218, 0.24); }
.pet-orb.is-sleepy { background: rgba(122, 106, 168, 0.28); }
.pet-face { font-size: 34px; filter: drop-shadow(0 8px 16px rgba(0,0,0,0.24)); }
.pet-frame { width: 82px; height: 82px; object-fit: contain; filter: drop-shadow(0 10px 18px rgba(0,0,0,0.24)); transform: translateY(2px); }
.pet-body { position: relative; display: grid; gap: 6px; min-width: 0; }
.pet-kicker { font-size: 12px; color: rgba(255,248,232,0.68); font-weight: 700; }
.pet-body h3 { font-size: 16px; line-height: 1.35; }
.pet-body p { font-size: 13px; line-height: 1.55; color: rgba(255,248,232,0.78); }
.pet-meta-row { display: flex; gap: 8px; flex-wrap: wrap; font-size: 11px; color: rgba(255,248,232,0.66); }
.pet-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.pet-actions button {
  min-width: 74px;
  padding: 9px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.18);
  color: #fff8e8;
  font-size: 13px;
  font-weight: 800;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(0,0,0,0.16);
  transition: transform 0.18s ease, background 0.18s ease;
}
.pet-actions button:hover { transform: translateY(-1px); background: rgba(255,255,255,0.26); }
.pet-actions button.is-primary { background: rgba(255, 214, 126, 0.96); color: #3a2812; border-color: rgba(255, 214, 126, 0.9); }
.pet-actions .pet-open-btn { min-width: 132px; background: rgba(255, 248, 232, 0.92); color: #3a2812; }
.pet-panel-overlay { position: fixed; inset: 0; z-index: 500; display: flex; align-items: center; justify-content: center; padding: 24px; background: rgba(20, 17, 24, 0.48); backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); pointer-events: auto; }
.pet-panel-card { position: relative; width: min(430px, 100%); padding: 24px; border-radius: 26px; background: linear-gradient(145deg, rgba(42, 35, 48, 0.96), rgba(84, 63, 70, 0.94)); color: #fff8e8; box-shadow: 0 28px 80px rgba(0,0,0,0.42); border: 1px solid rgba(255, 232, 178, 0.28); }
.pet-panel-close { position: absolute; right: 16px; top: 14px; width: 34px; height: 34px; border-radius: 50%; border: none; background: rgba(255,255,255,0.12); color: #fff8e8; font-size: 22px; cursor: pointer; }
.pet-panel-head { display: grid; grid-template-columns: 86px 1fr; gap: 16px; align-items: center; }
.pet-panel-avatar { width: 86px; height: 86px; border-radius: 28px; display: grid; place-items: center; background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.16); }
.pet-panel-avatar span { font-size: 42px; }
.pet-panel-frame { width: 94px; height: 94px; object-fit: contain; filter: drop-shadow(0 12px 22px rgba(0,0,0,0.24)); }
.pet-panel-kicker { display: inline-flex; margin-bottom: 6px; color: rgba(255,248,232,0.68); font-size: 13px; font-weight: 800; }
.pet-panel-head h3 { font-size: 21px; margin-bottom: 8px; }
.pet-panel-head p { color: rgba(255,248,232,0.78); line-height: 1.65; }
.pet-panel-meta { display: flex; gap: 10px; flex-wrap: wrap; margin: 18px 0; }
.pet-panel-meta span { padding: 7px 10px; border-radius: 999px; background: rgba(255,255,255,0.12); color: rgba(255,248,232,0.76); font-size: 12px; }
.pet-playground-card { width: min(760px, calc(100vw - 32px)); max-height: min(88vh, 760px); overflow-y: auto; }
.pet-playground-stage { position: relative; margin: 18px 0; min-height: 260px; border-radius: 28px; display: grid; place-items: center; overflow: hidden; background: radial-gradient(circle at 50% 42%, rgba(255, 220, 148, 0.22), rgba(255,255,255,0.07) 42%, rgba(255,255,255,0.04)); border: 1px solid rgba(255,255,255,0.12); }
.pet-stage-hint { position: absolute; top: 14px; left: 16px; padding: 7px 11px; border-radius: 999px; background: rgba(255,255,255,0.12); color: rgba(255,248,232,0.72); font-size: 12px; font-weight: 800; }
.pet-stage-frame { width: min(220px, 52vw); height: min(220px, 52vw); object-fit: contain; filter: drop-shadow(0 22px 30px rgba(0,0,0,0.28)); animation: pet-idle-float 1.8s ease-in-out infinite; }
.pet-stage-bubble { position: absolute; right: 16px; bottom: 16px; max-width: min(320px, 72%); padding: 10px 13px; border-radius: 18px 18px 6px 18px; background: rgba(255, 214, 126, 0.94); color: #33220f; font-size: 13px; line-height: 1.5; font-weight: 800; }
@keyframes pet-idle-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.pet-panel-actions { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.pet-panel-actions button { min-height: 44px; border: none; border-radius: 15px; background: rgba(255,255,255,0.16); color: #fff8e8; font-size: 14px; font-weight: 900; font-family: inherit; cursor: pointer; }
.pet-panel-actions button.is-primary { background: #ffd67e; color: #33220f; }
.pet-visual-picker { margin-top: 16px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.12); }
.pet-visual-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
.pet-visual-option { min-height: 98px; padding: 9px; border-radius: 17px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.1); color: #fff8e8; font-family: inherit; cursor: pointer; }
.pet-visual-option.active { border-color: rgba(255,214,126,0.9); background: rgba(255,214,126,0.18); box-shadow: 0 12px 30px rgba(255,214,126,0.14); }
.pet-visual-option img { width: 58px; height: 58px; object-fit: contain; display: block; margin: 0 auto 6px; filter: drop-shadow(0 8px 14px rgba(0,0,0,0.22)); }
.pet-visual-option strong { display: block; text-align: center; font-size: 13px; }

.first-run-guide {
  padding: 15px;
  background: linear-gradient(145deg, rgba(28,31,42,0.82), rgba(70,54,66,0.68));
}
.guide-title {
  font-size: 16px;
  font-weight: 800;
  line-height: 1.35;
}
.guide-copy {
  margin: 7px 0 12px;
  color: rgba(255,255,255,0.72);
  font-size: 12px;
  line-height: 1.55;
}
.guide-progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 12px;
}
.guide-progress-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.64);
  font-size: 12px;
  font-weight: 800;
}
.guide-progress-dot.active,
.guide-progress-dot.done {
  background: rgba(255, 230, 178, 0.9);
  color: #2f2114;
}
.guide-progress-line {
  flex: 1;
  height: 1px;
  background: rgba(255,255,255,0.18);
}
.guide-option-grid {
  display: grid;
  gap: 8px;
}
.guide-option {
  display: flex;
  gap: 9px;
  align-items: center;
  width: 100%;
  padding: 10px;
  border-radius: 14px;
  background: rgba(255,255,255,0.09);
  color: #fff;
  text-align: left;
  transition: transform 0.18s ease, background 0.18s ease;
}
.guide-option.is-primary {
  background: rgba(255,230,178,0.18);
  outline: 1px solid rgba(255,230,178,0.3);
}
.guide-option:hover {
  transform: translateY(-1px);
  background: rgba(255,255,255,0.14);
}
.guide-option-icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.12);
  flex-shrink: 0;
}
.guide-option strong,
.guide-option em {
  display: block;
  font-style: normal;
}
.guide-option strong {
  font-size: 13px;
  margin-bottom: 2px;
}
.guide-option em {
  color: rgba(255,255,255,0.66);
  font-size: 11px;
  line-height: 1.4;
}
.guide-secondary {
  display: block;
  margin: 10px auto 0;
  padding: 4px 8px;
  background: transparent;
  color: rgba(255,255,255,0.5);
  font-size: 12px;
}
.guide-secondary:hover {
  color: rgba(255,255,255,0.8);
}
.guide-mood-card {
  display: grid;
  gap: 10px;
}
.guide-mood-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255,255,255,0.72);
  font-size: 12px;
  font-weight: 700;
}
.guide-mood-meta strong {
  color: rgba(255,255,255,0.94);
  font-size: 13px;
}
.guide-mood-suggestion {
  margin: 0 0 2px;
  padding: 9px 11px;
  border-radius: 14px;
  background: rgba(255, 230, 178, 0.12);
  color: rgba(255,255,255,0.8);
  font-size: 12px;
  line-height: 1.5;
}
.guide-mood-meta span {
  display: inline-flex;
  width: 30px;
  height: 30px;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(255,255,255,0.12);
  font-size: 18px;
}
.guide-target-hint { position: relative; display: grid; gap: 4px; margin: 10px 0 12px; padding: 12px 14px; border-radius: 16px; background: rgba(255, 239, 202, 0.16); border: 1px solid rgba(255, 226, 170, 0.26); box-shadow: inset 0 1px 0 rgba(255,255,255,0.18); }
.guide-target-kicker { font-size: 11px; color: rgba(255,255,255,0.66); }
.guide-target-hint strong { font-size: 15px; color: rgba(255,255,255,0.96); }
.guide-target-hint em { font-size: 12px; color: rgba(255,255,255,0.72); font-style: normal; line-height: 1.5; }
.is-guide-target { z-index: 31 !important; outline: 3px solid rgba(255, 230, 150, 0.95); outline-offset: 7px; box-shadow: 0 0 0 10px rgba(255, 209, 102, 0.2), 0 0 28px rgba(255, 219, 130, 0.78) !important; animation: guide-target-pulse 1.25s ease-in-out infinite; }
.guide-target-badge { position: absolute; left: 50%; top: -38px; transform: translateX(-50%); padding: 7px 12px; border-radius: 999px; background: rgba(35, 25, 14, 0.86); color: #fff4cc; font-size: 13px; font-weight: 800; white-space: nowrap; pointer-events: none; box-shadow: 0 8px 24px rgba(0,0,0,0.28); }
.nav-guide-badge { top: -36px; }
@keyframes guide-target-pulse { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.22); } }
@media (max-width: 760px) {
  .pet-companion-card {
    left: 12px;
    right: 12px;
    top: auto;
    bottom: 92px;
    width: auto;
    grid-template-columns: 56px 1fr;
    padding: 12px;
    border-radius: 18px;
  }
  .pet-orb { width: 56px; height: 56px; border-radius: 18px; }
  .pet-face { font-size: 28px; }
  .pet-body h3 { font-size: 14px; }
  .pet-body p { font-size: 12px; }
  .pet-actions button { min-width: 68px; padding: 8px 10px; font-size: 12px; }
  .pet-actions .pet-open-btn { min-width: 118px; }
  .pet-panel-card { padding: 18px; }
  .pet-panel-head { grid-template-columns: 64px 1fr; }
  .pet-panel-avatar { width: 64px; height: 64px; border-radius: 21px; }
  .pet-panel-avatar span { font-size: 32px; }
  .pet-panel-actions { grid-template-columns: 1fr; }
  .pet-playground-stage { min-height: 220px; }
  .room-roaming-pet { width: 72px; min-height: 76px; }
  .room-roaming-pet img { width: 70px; height: 70px; }
  .pet-visual-list { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .engagement-stack {
    top: auto;
    left: 12px;
    right: 12px;
    bottom: 96px;
    width: auto;
  }
  .daily-return-card {
    padding: 12px 13px;
  }
  .first-run-guide {
    padding: 13px;
  }
  .ritual-title,
  .guide-title {
    font-size: 15px;
  }
  .ritual-copy,
  .guide-copy {
    font-size: 12px;
  }
  .ritual-chip-row {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .ritual-action,
  .guide-option {
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
  transform: translate(-50%, -50%) rotate(15deg) scale(0.96);
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(18, 24, 32, 0.48);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  text-shadow: 0 1px 8px rgba(0,0,0,0.6);
  opacity: 0;
  pointer-events: none;
  white-space: nowrap;
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.zone-window:hover .window-label {
  opacity: 1;
  transform: translate(-50%, -50%) rotate(15deg) scale(1.04);
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
.leisure-overlay { z-index: 400; }
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
  z-index: 4; width: 44px; height: 44px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 0; background: rgba(255,255,255,0.08); color: rgba(200,200,200,0.6);
  cursor: pointer; transition: all 0.2s;
}
.panel-close:hover { background: rgba(255,255,255,0.15); color: white; }

/* 倾诉结束后的小结入口：像素品牌素材 + 可读的液态玻璃 */
.student-summary-orb {
  position: fixed; z-index: 238; top: 50%; right: clamp(18px, 3vw, 42px);
  display: flex; align-items: center; gap: 10px; min-width: 146px; min-height: 58px;
  padding: 8px 13px 8px 9px; transform: translateY(-50%);
  border: 1px solid rgba(255,255,255,.22); border-radius: 14px;
  color: #f5f0e8; background: rgba(19,23,29,.9); backdrop-filter: blur(18px) saturate(1.3);
  box-shadow: 0 5px 8px rgba(5,7,12,.28); cursor: pointer;
  transition: transform .2s cubic-bezier(.22,1,.36,1), background .2s ease;
}
.student-summary-orb:hover { transform: translateY(-50%) translateX(-3px); background: rgba(25,31,36,.96); }
.student-summary-orb:focus-visible { outline: 3px solid #c8ead9; outline-offset: 4px; }
.summary-orb-pixel { width: 40px; height: 40px; padding: 3px; border-radius: 9px 9px 9px 3px; background: rgba(188,217,202,.18); }
.summary-orb-pixel img { width: 100%; height: 100%; border-radius: 6px; object-fit: cover; image-rendering: pixelated; }
.summary-orb-copy { display: grid; gap: 2px; text-align: left; }
.summary-orb-copy strong { font-size: 13px; line-height: 1.2; }
.summary-orb-copy small { color: rgba(245,240,232,.74); font-size: 10px; }
.summary-unread-dot { position: absolute; top: 7px; right: 7px; width: 8px; height: 8px; border-radius: 2px; background: #f2d083; box-shadow: 0 0 0 2px rgba(19,23,29,.9); }
.student-summary-orb.is-processing .summary-orb-pixel { animation: summary-pixel-pulse 1.2s ease-in-out infinite; }
.student-summary-orb.is-error { border-color: rgba(242,191,171,.55); }
.student-summary-orb:disabled { cursor: progress; }
@keyframes summary-pixel-pulse { 50% { opacity: .58; transform: scale(.94); } }
.summary-orb-enter-active, .summary-orb-leave-active { transition: opacity .2s ease, transform .2s cubic-bezier(.22,1,.36,1); }
.summary-orb-enter-from, .summary-orb-leave-to { opacity: 0; transform: translate(16px, -50%); }
.summary-live-region { position: fixed; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }

/* 倾诉后行动抽屉：像素房间保持可见，组件沿用液态玻璃层次 */
.student-support-drawer {
  position: fixed;
  z-index: 245;
  top: 50%;
  right: clamp(18px, 4vw, 64px);
  width: min(410px, calc(100vw - 36px));
  max-height: min(760px, calc(100vh - 44px));
  overflow-y: auto;
  transform: translateY(-50%);
  padding: 30px 28px 24px;
  color: #f5f0e8;
  background: linear-gradient(150deg, rgba(18, 21, 27, .96), rgba(27, 25, 32, .94));
  border: 1px solid rgba(255, 255, 255, .18);
  border-radius: 22px;
  box-shadow: 0 24px 70px rgba(5, 7, 12, .42), inset 0 1px rgba(255, 255, 255, .08);
  backdrop-filter: blur(26px) saturate(1.35);
  font-family: 'PingFang SC','Microsoft YaHei','Noto Sans SC',sans-serif;
}
.student-support-drawer::-webkit-scrollbar { width: 0; }
.support-close {
  position: absolute; top: 14px; right: 16px;
  width: 44px; height: 44px; border: 1px solid rgba(255,255,255,.12); border-radius: 50%;
  color: #f5f0e8; background: rgba(255,255,255,.09); font-size: 22px; line-height: 1; cursor: pointer;
}
.support-eyebrow { margin: 0 0 8px; color: #a9c8ba; font-size: 12px; font-weight: 700; letter-spacing: .14em; }
.student-support-drawer h2 { margin: 0 42px 12px 0; font-size: 24px; line-height: 1.25; letter-spacing: .02em; }
.support-summary { margin: 0; color: rgba(245,240,232,.82); font-size: 15px; line-height: 1.75; }
.support-emotion-state { display: flex; align-items: center; gap: 11px; margin: 0 0 14px; padding: 12px 13px; border-radius: 12px; background: rgba(143,185,166,.12); }
.support-emotion-icon { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 9px; background: rgba(255,255,255,.08); font-size: 20px; }
.support-emotion-state div { display: grid; gap: 2px; }
.support-emotion-state small { color: rgba(245,240,232,.72); font-size: 11px; }
.support-emotion-state strong { color: #fff; font-size: 15px; }
.support-evidence { margin: 19px 0 0; }
.support-evidence h3 { margin: 0 0 8px; color: #dcebe3; font-size: 13px; }
.support-evidence ul { display: grid; gap: 7px; margin: 0; padding: 0; list-style: none; }
.support-evidence li { position: relative; padding-left: 16px; color: rgba(245,240,232,.8); font-size: 13px; line-height: 1.55; }
.support-evidence li::before { content: ''; position: absolute; top: .62em; left: 2px; width: 6px; height: 6px; border-radius: 2px; background: #a9c8ba; }
.support-need-block { display: grid; gap: 5px; margin: 18px 0; padding: 13px 14px; border-radius: 12px; background: rgba(255,255,255,.065); }
.support-need-block span { color: #a9c8ba; font-size: 11px; font-weight: 700; }
.support-need-block strong { font-size: 14px; line-height: 1.6; }
.support-professional-note { margin: 0 0 18px; padding: 14px; border-radius: 12px; color: #fff3dc; background: rgba(157,105,54,.24); }
.support-professional-note strong { font-size: 14px; }
.support-professional-note p { margin: 6px 0 0; color: rgba(255,243,220,.88); font-size: 12px; line-height: 1.65; }
.student-support-drawer textarea {
  width: 100%; min-height: 94px; box-sizing: border-box; resize: vertical;
  padding: 13px; border: 1px solid rgba(169,200,186,.42); border-radius: 14px;
  color: #f5f0e8; background: rgba(255,255,255,.07); font: inherit; line-height: 1.6; outline: none;
}
.support-summary-actions { display: flex; justify-content: flex-end; gap: 14px; margin: 8px 0 20px; }
.support-summary-actions button, .support-help-link { border: 0; padding: 3px 0; color: rgba(245,240,232,.9); background: transparent; font-size: 12px; cursor: pointer; }
.support-needs { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 7px; margin: 0 0 18px; padding: 0; border: 0; }
.support-needs legend { grid-column: 1 / -1; margin-bottom: 8px; color: rgba(245,240,232,.88); font-size: 12px; }
.support-needs button, .support-decision-row button, .support-person-grid button {
  min-height: 40px; padding: 8px 10px; border: 1px solid rgba(255,255,255,.11); border-radius: 12px;
  color: rgba(245,240,232,.94); background: rgba(255,255,255,.075); font-size: 12px; cursor: pointer;
}
.support-needs button.active, .support-person-grid button.active { color: #fff; border-color: rgba(169,200,186,.68); background: rgba(126,164,146,.22); }
.support-next-step { display: grid; gap: 7px; padding: 16px; border: 1px solid rgba(255,255,255,.1); border-radius: 16px; background: rgba(8,12,16,.28); }
.support-next-step span { color: #a9c8ba; font-size: 11px; font-weight: 700; letter-spacing: .08em; }
.support-next-step strong { font-size: 16px; line-height: 1.55; }
.support-next-step small { color: rgba(245,240,232,.88); line-height: 1.5; }
.support-next-step ol { display: grid; gap: 8px; margin: 0; padding-left: 22px; color: rgba(245,240,232,.78); font-size: 13px; line-height: 1.55; }
.support-next-step li.primary { color: #fff; font-weight: 700; }
.support-boundary { margin: 12px 0 0; color: rgba(245,240,232,.68); font-size: 11px; line-height: 1.55; }
.support-summary-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 16px; }
.support-summary-controls button { min-height: 44px; padding: 8px 10px; border: 1px solid rgba(255,255,255,.13); border-radius: 11px; color: #f5f0e8; background: rgba(255,255,255,.07); cursor: pointer; }
.support-delete-link { display: block; min-height: 44px; margin: 8px auto 0; padding: 10px; border: 0; color: rgba(245,240,232,.68); background: transparent; font-size: 11px; text-decoration: underline; text-underline-offset: 3px; cursor: pointer; }
.support-decision-row { display: grid; grid-template-columns: 1.1fr .8fr 1fr; gap: 8px; margin-top: 14px; }
.support-primary { color: #17231e !important; border-color: transparent !important; background: linear-gradient(135deg, #bcd9ca, #8fb9a6) !important; font-weight: 700; }
.support-help-link { display: block; margin: 18px auto 0; color: #bcd9ca; text-decoration: underline; text-underline-offset: 4px; }
.support-person-grid { display: grid; gap: 9px; margin: 20px 0 16px; }
.support-share-toggle { display: flex; gap: 8px; align-items: flex-start; color: rgba(245,240,232,.92); font-size: 13px; line-height: 1.5; }
.support-share-toggle input { margin-top: 3px; accent-color: #8fb9a6; }
.support-send-boundary { margin: 10px 0 0; color: rgba(245,240,232,.88); font-size: 12px; line-height: 1.55; }
.support-card-preview { display: grid; gap: 11px; margin-top: 18px; padding: 18px; border: 1px solid rgba(169,200,186,.35); border-radius: 16px; background: rgba(255,255,255,.065); }
.support-card-preview span { color: #a9c8ba; font-size: 12px; font-weight: 700; }
.support-card-preview p { margin: 0; color: rgba(245,240,232,.84); font-size: 15px; line-height: 1.7; }
.support-card-preview strong { color: #fff; font-size: 13px; line-height: 1.6; }
.support-submit-help { width: 100%; min-height: 44px; margin-top: 18px; border-radius: 13px; border: 0; cursor: pointer; }
.support-submit-help:disabled { opacity: .45; cursor: not-allowed; }
.support-drawer-enter-active, .support-drawer-leave-active { transition: opacity .25s ease, transform .25s ease; }
.support-drawer-enter-from, .support-drawer-leave-to { opacity: 0; transform: translate(32px, -50%); }
.student-support-drawer button:focus-visible,
.student-support-drawer textarea:focus-visible,
.student-support-drawer input:focus-visible { outline: 3px solid #c8ead9; outline-offset: 3px; }

@media (prefers-reduced-motion: reduce) {
  .support-drawer-enter-active, .support-drawer-leave-active, .summary-orb-enter-active, .summary-orb-leave-active { transition: none; }
  .student-summary-orb, .student-summary-orb.is-processing .summary-orb-pixel { transition: none; animation: none; }
}

@media (max-width: 767px) {
  .student-summary-orb { top: auto; right: 14px; bottom: calc(76px + env(safe-area-inset-bottom)); min-width: 58px; transform: none; padding: 8px; }
  .student-summary-orb:hover { transform: translateY(-2px); }
  .summary-orb-copy { display: none; }
  .summary-orb-enter-from, .summary-orb-leave-to { opacity: 0; transform: translateY(12px); }
  .student-support-drawer { top: auto; right: 10px; bottom: max(10px, env(safe-area-inset-bottom)); left: 10px; width: auto; max-height: 75vh; transform: none; padding: 26px 20px calc(20px + env(safe-area-inset-bottom)); border-radius: 20px; }
  .support-drawer-enter-from, .support-drawer-leave-to { opacity: 0; transform: translateY(24px); }
  .support-needs, .support-decision-row { grid-template-columns: 1fr; }
  .chat-end-confirm { align-items: stretch; flex-direction: column; }
  .chat-end-actions { justify-content: flex-end; }
  .chat-panel .chat-end-button { right: 70px; padding-inline: 8px; font-size: 11px; }
}

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
.chat-panel .chat-end-button {
  position: absolute; right: 70px; min-height: 44px; padding: 9px 11px;
  border: 1px solid rgba(188,217,202,.34); border-radius: 10px;
  color: #dcebe3; background: rgba(143,185,166,.12); font-size: 12px; cursor: pointer;
  transition: background .18s ease, border-color .18s ease, opacity .18s ease;
}
.chat-panel .chat-end-button:hover:not(:disabled) { background: rgba(143,185,166,.22); border-color: rgba(188,217,202,.58); }
.chat-panel .chat-end-button:disabled { opacity: .38; cursor: not-allowed; }
.chat-panel .chat-end-button:focus-visible { outline: 3px solid #c8ead9; outline-offset: 3px; }
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
.chat-end-confirm {
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
  margin: 0 16px 10px; padding: 12px 14px;
  border: 1px solid rgba(188,217,202,.32); border-radius: 12px;
  color: #f5f0e8; background: rgba(35,43,44,.94);
}
.chat-end-confirm > div:first-child { display: grid; gap: 3px; min-width: 0; }
.chat-end-confirm strong { font-size: 13px; line-height: 1.4; }
.chat-end-confirm span { color: rgba(245,240,232,.76); font-size: 11px; line-height: 1.45; }
.chat-end-actions { display: flex; gap: 7px; flex-shrink: 0; }
.chat-end-actions button { min-height: 44px; padding: 9px 12px; border: 1px solid rgba(255,255,255,.14); border-radius: 9px; color: #f5f0e8; background: rgba(255,255,255,.07); cursor: pointer; }
.chat-end-actions .chat-end-primary { color: #17231e; border-color: #bcd9ca; background: #bcd9ca; font-weight: 700; }
.chat-end-actions button:focus-visible { outline: 3px solid #c8ead9; outline-offset: 2px; }
@media (max-width: 767px) {
  .chat-end-confirm { align-items: stretch; flex-direction: column; }
  .chat-end-actions { justify-content: flex-end; }
  .chat-panel .chat-end-button { right: 70px; padding-inline: 8px; font-size: 11px; }
}

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
.beian-footer a:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 3px;
}
.icp-link { white-space: nowrap; }
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
.guardian-workbench-entry {
  position: fixed;
  top: 18px;
  right: 20px;
  z-index: 46;
  display: grid;
  gap: 2px;
  min-width: 176px;
  padding: 11px 14px;
  border-radius: 12px;
  background: rgba(20, 39, 34, 0.82);
  color: #fff;
  text-decoration: none;
  box-shadow: 0 6px 8px rgba(13, 34, 29, 0.16);
  backdrop-filter: blur(10px);
}
.guardian-workbench-entry span { font-size: 13px; font-weight: 800; }
.guardian-workbench-entry small { color: rgba(255,255,255,.72); font-size: 10px; }
.guardian-workbench-entry:focus-visible { outline: 3px solid #f4cc72; outline-offset: 3px; }
@media (max-width: 640px) {
  .guardian-workbench-entry { top: 12px; right: 12px; min-width: 0; padding: 9px 11px; }
  .guardian-workbench-entry small { display: none; }
}

/* v5.1 房间界面骨架：像素场景是主角，玻璃只承载状态和导航。 */
.room {
  --room-surface: rgba(16, 22, 28, .88);
  --room-surface-soft: rgba(22, 28, 35, .76);
  --room-ink: #f7f4ed;
  --room-muted: rgba(247, 244, 237, .74);
  --room-accent: #b8d7c7;
  color: var(--room-ink);
}
.top-bar {
  top: 14px;
  left: 50%;
  right: auto;
  width: max-content;
  min-width: 214px;
  padding: 9px 18px 10px;
  transform: translateX(-50%);
  border-radius: 14px;
  background: rgba(15, 20, 26, .72);
  box-shadow: 0 4px 8px rgba(5, 8, 12, .22);
  backdrop-filter: blur(16px) saturate(1.14);
}
.clock { margin: 0; color: rgba(247, 244, 237, .72); font-size: 11px; text-shadow: none; }
.greeting-text { color: var(--room-ink); font-size: 15px; letter-spacing: 0; text-shadow: none; }
.greeting-sub { color: rgba(247, 244, 237, .68); font-size: 10px; text-shadow: none; }
.engagement-stack { top: 102px; left: 20px; width: min(292px, calc(100vw - 40px)); gap: 9px; }
.daily-return-card,
.first-run-guide {
  border: 0;
  border-radius: 14px;
  background: var(--room-surface);
  box-shadow: 0 6px 8px rgba(5, 8, 12, .25);
  backdrop-filter: blur(18px) saturate(1.12);
}
.daily-return-card { padding: 13px; }
.ritual-glow,
.pet-companion-card::before { display: none; }
.ritual-orb { width: 36px; height: 36px; border: 0; border-radius: 10px; background: rgba(255, 255, 255, .09); font-size: 18px; }
.ritual-title { font-size: 15px; }
.ritual-copy { color: var(--room-muted); font-size: 12px; }
.daily-check-pill { border: 0; background: rgba(255, 255, 255, .08); color: rgba(247, 244, 237, .78); }
.daily-check-pill:hover,
.daily-check-pill.active { background: #e9d59b; color: #2f2615; }
.ritual-action { min-height: 38px; border-radius: 10px; background: #e9d59b; }
.pet-companion-card {
  top: auto;
  right: 20px;
  bottom: 104px;
  width: min(292px, calc(100vw - 40px));
  grid-template-columns: 62px 1fr;
  gap: 11px;
  padding: 13px;
  border: 0;
  border-radius: 14px;
  background: var(--room-surface);
  box-shadow: 0 6px 8px rgba(5, 8, 12, .25);
  backdrop-filter: blur(18px) saturate(1.12);
}
.pet-orb { width: 62px; height: 62px; border: 0; border-radius: 12px; }
.pet-frame { width: 68px; height: 68px; }
.pet-body { gap: 4px; }
.pet-body p { color: var(--room-muted); font-size: 11px; }
.pet-actions { margin-top: 4px; }
.pet-actions .pet-open-btn { min-width: 0; min-height: 36px; padding: 7px 10px; border: 0; border-radius: 10px; box-shadow: none; }
.bottom-nav { bottom: calc(18px + env(safe-area-inset-bottom)); }
.bottom-nav::before {
  width: 304px;
  border: 0;
  border-radius: 15px;
  background: rgba(16, 22, 28, .78) !important;
  box-shadow: 0 6px 8px rgba(5, 8, 12, .25) !important;
  backdrop-filter: blur(20px) saturate(1.15) !important;
}
.heart-island-door {
  position: fixed;
  right: clamp(92px, 12vw, 184px);
  top: 38%;
  z-index: 32;
  display: grid;
  justify-items: center;
  gap: 7px;
  width: 86px;
  min-height: 112px;
  padding: 8px;
  border: 0;
  color: #fff9e8;
  background: transparent;
  cursor: pointer;
  text-shadow: 0 2px 5px rgba(8, 11, 21, .72);
}
.heart-island-door-glow {
  width: 54px;
  height: 68px;
  border: 5px solid rgba(38, 31, 64, .86);
  border-bottom-width: 7px;
  border-radius: 28px 28px 8px 8px;
  background: linear-gradient(180deg, rgba(189, 174, 238, .94), rgba(115, 195, 174, .88));
  box-shadow: 0 0 0 3px rgba(235, 210, 141, .7), 0 0 24px rgba(167, 216, 196, .64), inset 0 0 20px rgba(255,255,255,.38);
  image-rendering: pixelated;
}
.heart-island-door-copy { display: grid; gap: 1px; padding: 5px 8px; border-radius: 8px; background: rgba(15, 20, 29, .76); backdrop-filter: blur(10px); }
.heart-island-door-copy strong { font-size: 12px; }
.heart-island-door-copy small { color: rgba(255, 249, 232, .74); font-size: 9px; }
.heart-island-door:hover .heart-island-door-glow { filter: brightness(1.12); transform: translateY(-2px); }
.heart-island-door:focus-visible { outline: 3px solid #f1d48c; outline-offset: 4px; border-radius: 12px; }
.profile-space-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.profile-space-grid button { min-height: 62px; padding: 11px; border: 1px solid rgba(255,255,255,.08); border-radius: 12px; color: #fff; background: rgba(255,255,255,.06); cursor: pointer; text-align: left; font-weight: 700; }
.profile-space-grid button small { display: block; margin-top: 4px; color: rgba(247,244,237,.65); font-size: 10px; font-weight: 500; }
.profile-space-grid button:focus-visible { outline: 3px solid #f1d48c; outline-offset: 3px; }
.nav-label { font-size: 10px; }
.student-summary-orb { right: 20px; }
.student-support-drawer {
  border: 0;
  border-radius: 16px;
  background: rgba(17, 22, 29, .96);
  box-shadow: 0 7px 8px rgba(5, 8, 12, .34);
}
.support-eyebrow { letter-spacing: .04em; }
.support-primary { background: #bcd9ca !important; }
.guardian-workbench-entry {
  top: 14px;
  right: 20px;
  border-radius: 12px;
  background: rgba(15, 20, 26, .82);
  box-shadow: 0 4px 8px rgba(5, 8, 12, .22);
  backdrop-filter: blur(16px) saturate(1.14);
}

@media (max-width: 899px) {
  .top-bar { left: 12px; min-width: 0; padding: 8px 11px; transform: none; align-items: flex-start; text-align: left; }
  .greeting-sub { display: none; }
  .guardian-workbench-entry { top: 12px; right: 12px; }
  .engagement-stack { top: 76px; bottom: auto; left: 12px; right: auto; width: min(246px, calc(100vw - 24px)); }
  .daily-return-card { padding: 11px; }
  .daily-return-card .ritual-copy:first-of-type { display: none; }
  .pet-companion-card { display: none; }
  .student-summary-orb { right: 154px; bottom: calc(84px + env(safe-area-inset-bottom)); }
  .student-support-drawer { border-radius: 16px; }
  .heart-island-door { right: 14px; top: 44%; transform: scale(.86); transform-origin: right center; }
}

@media (prefers-reduced-motion: reduce) {
  .heart-island-door-glow { transition: none; }
  .heart-island-door:hover .heart-island-door-glow { transform: none; }
}

@media (max-width: 520px) {
  .engagement-stack { top: 76px; bottom: auto; left: 12px; right: auto; width: min(226px, calc(100vw - 24px)); }
  .daily-check-row { margin-bottom: 8px; }
  .ritual-copy { margin-block: 5px 8px; }
  .student-summary-orb { right: 150px; }
}

@media (prefers-reduced-motion: reduce) {
  .room *,
  .room *::before,
  .room *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
  }
  .room-roaming-pet,
  .room-roaming-pet img,
  .splash-fade-leave-active { transition: none; animation: none; }
}

/* v5.1.0-alpha.3：主界面减法系统。场景承担导航，控制层只保留一个状态条和按需操作条。 */
.room-status-bar {
  position: fixed;
  top: 14px;
  left: 14px;
  right: 132px;
  z-index: 224;
  display: flex;
  align-items: center;
  width: max-content;
  max-width: calc(100vw - 160px);
  min-height: 46px;
  padding: 5px;
  border-radius: 14px;
  color: #f7f4ed;
  background: rgba(16, 22, 28, .84);
  box-shadow: 0 5px 8px rgba(5, 8, 12, .25);
  backdrop-filter: blur(18px) saturate(1.14);
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', system-ui, sans-serif;
}
.room-status-greeting {
  display: grid;
  min-width: 174px;
  padding: 3px 12px;
}
.room-status-greeting time { color: rgba(247, 244, 237, .68); font-size: 10px; }
.room-status-greeting strong { margin-top: 1px; font-size: 13px; line-height: 1.35; }
.room-status-checkin,
.room-status-utility {
  min-height: 36px;
  border: 0;
  border-radius: 10px;
  color: rgba(247, 244, 237, .9);
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}
.room-status-checkin {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 10px;
  border-inline: 1px solid rgba(255, 255, 255, .1);
  border-radius: 0;
}
.room-status-checkin > span:first-child { font-size: 17px; }
.room-status-checkin > span:last-child { display: grid; text-align: left; }
.room-status-checkin small { color: rgba(247, 244, 237, .62); font-size: 9px; }
.room-status-checkin strong { margin-top: 1px; font-size: 11px; }
.room-status-utility { display: flex; align-items: center; gap: 4px; padding: 0 9px; font-size: 11px; }
.room-status-checkin:hover,
.room-status-utility:hover { background: rgba(255, 255, 255, .1); }
.room-status-checkin:focus-visible,
.room-status-utility:focus-visible,
.hot-zone:focus-visible,
.room-onboarding-cue button:focus-visible { outline: 3px solid #f0d58e; outline-offset: 3px; }

.room-onboarding-cue {
  position: fixed;
  top: 76px;
  left: 14px;
  z-index: 223;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  width: min(470px, calc(100vw - 28px));
  padding: 9px 10px;
  border-radius: 12px;
  color: #f7f4ed;
  background: rgba(16, 22, 28, .9);
  box-shadow: 0 5px 8px rgba(5, 8, 12, .28);
  backdrop-filter: blur(18px) saturate(1.12);
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', system-ui, sans-serif;
}
.room-onboarding-step {
  display: grid;
  place-items: center;
  min-width: 38px;
  height: 32px;
  padding-inline: 7px;
  border-radius: 8px;
  color: #1d2a25;
  background: #b8d7c7;
  font-size: 10px;
  font-weight: 800;
}
.room-onboarding-cue > div { min-width: 0; }
.room-onboarding-cue strong,
.room-onboarding-cue small { display: block; }
.room-onboarding-cue strong { font-size: 12px; }
.room-onboarding-cue small { margin-top: 2px; overflow: hidden; color: rgba(247, 244, 237, .7); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.room-onboarding-cue button {
  min-height: 36px;
  padding: 0 11px;
  border: 0;
  border-radius: 9px;
  color: #1d261f;
  background: #e8d49b;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}
.room-onboarding-cue .room-onboarding-skip { width: 36px; padding: 0; color: #f7f4ed; background: rgba(255, 255, 255, .08); font-size: 18px; }

.hot-zone {
  appearance: none;
  padding: 0;
  border: 0;
  color: inherit;
  background: transparent;
  font: inherit;
}
.hot-zone::after {
  content: '';
  position: absolute;
  inset: 0;
  border: 1px solid transparent;
  border-radius: 10px;
  pointer-events: none;
  transition: border-color .18s ease, background-color .18s ease;
}
.hot-zone:hover::after,
.hot-zone:focus-visible::after,
.hot-zone.is-selected::after { border-color: rgba(240, 213, 142, .82); background: rgba(240, 213, 142, .08); }
.hot-zone:focus-visible .hover-tip,
.hot-zone:focus-visible .bed-label,
.hot-zone:focus-visible .window-label { opacity: 1; }
.hot-zone .hover-tip,
.hot-zone .bed-label,
.hot-zone .window-label {
  padding: 6px 9px;
  border-radius: 8px;
  color: #f7f4ed;
  background: rgba(16, 22, 28, .88);
  font-size: 10px;
  white-space: nowrap;
  box-shadow: none;
}
.zone-bed .bed-label,
.zone-window .window-label { pointer-events: none; }
.room-roaming-pet span { max-width: 164px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.beian-footer {
  right: 14px;
  bottom: 14px;
  left: auto;
  padding: 7px 10px;
  transform: none;
}
.beian-footer a { font-size: 11px; }

@media (max-width: 760px) {
  .room-status-bar {
    top: 10px;
    left: 10px;
    right: 112px;
    max-width: calc(100vw - 124px);
    min-height: 42px;
  }
  .room-status-greeting { min-width: 0; padding-inline: 8px; }
  .room-status-greeting time { display: none; }
  .room-status-greeting strong { max-width: 116px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .room-status-checkin { border-inline-end: 0; }
  .room-status-checkin > span:first-child,
  .room-status-checkin small { display: none; }
  .room-status-checkin strong { max-width: 70px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .room-status-utility { display: none; }
  .zone-speaker-left { top: 46%; left: 26%; width: 12%; height: 12%; }
  .zone-speaker-right { display: none; }
  .room-onboarding-cue { top: 64px; left: 10px; width: calc(100vw - 20px); }
  .room-onboarding-cue small { display: none; }
  .beian-footer {
    right: 8px;
    bottom: calc(98px + env(safe-area-inset-bottom));
    left: auto;
    max-width: calc(100vw - 16px);
    transform: scale(.78);
    transform-origin: right bottom;
  }
}

@media (max-width: 440px) {
  .room-onboarding-cue { grid-template-columns: auto minmax(0, 1fr) auto; }
}
</style>
