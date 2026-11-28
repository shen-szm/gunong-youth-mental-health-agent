# V4.3 Engagement Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the V4.3 lightweight activation and daily return loops for the room homepage.

**Architecture:** Keep V4.3 frontend-only and local-storage backed. Extend `RoomHomeView.vue` in place because the current room page already owns first-run guidance, chat panel state, daily card state, and room hot zones. Add tests that assert static source structure and release versioning before implementation.

**Tech Stack:** Vue 3 `<script setup>`, Vite, Node test runner, localStorage, existing chat API.

---

## File Structure

- Modify `frontend/src/views/RoomHomeView.vue`
  - Replace the current two-step first-run guide with a three-state guide: click computer, send one sentence, see mood card / go tree hole.
  - Replace the simple daily ritual card with a daily return card containing task, mood check-in, and companionship streak.
  - Add local-storage helpers for first-run completion, daily check-in, daily task state, streak, last active date, and last mood card.
  - Update chat prompt and `sendChatMsg` so first-run completion happens only after a successful assistant response.
  - Add CSS for the daily loop and mood card.
- Modify `frontend/tests/engagement-entry.test.mjs`
  - Add tests for the V4.3 first-run completion rule, chat prompt, mood card, daily check-in, streak, and local-only persistence keys.
  - Keep tests proving removed mini tools stay absent.
- Modify `frontend/tests/onboarding-versioning.test.mjs`
  - Update expected package/changelog version from `4.2.5` to `4.3.0`.
  - Update first-run assertions to match the new `guideStage` / completion-after-chat behavior.
- Modify `frontend/package.json`
  - Set version to `4.3.0`.
- Modify `frontend/package-lock.json`
  - Set root and package version to `4.3.0`.
- Modify `CHANGELOG.md`
  - Add `## [4.3.0] - 2026-07-06` with a feature-level update note.

---

### Task 1: Add failing V4.3 product-loop tests

**Files:**
- Modify: `frontend/tests/engagement-entry.test.mjs`
- Modify: `frontend/tests/onboarding-versioning.test.mjs`

- [ ] **Step 1: Add source assertions for V4.3 engagement loop**

Append these constants near the existing constants in `frontend/tests/engagement-entry.test.mjs`:

```js
const FIRST_CONFESSION_PROMPT = '\u628a\u4eca\u5929\u6700\u60f3\u8bf4\u7684\u4e00\u53e5\u8bdd\u4e22\u7ed9\u6211'
const MOOD_CARD_TITLE = '\u4eca\u65e5\u5fc3\u60c5\u5361'
const DAILY_RETURN_TITLE = '\u4eca\u5929\u4e5f\u7ed9\u81ea\u5df1\u7559\u4e00\u5206\u949f'
```

Add these tests to `frontend/tests/engagement-entry.test.mjs`:

```js
test('v4.3 first-run loop completes only after a successful first confession', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /guideStage = ref\('computer'\)/)
  assert.match(room, /FIRST_RUN_GUIDE_VERSION = '4\.3\.0'/)
  assert.match(room, new RegExp(FIRST_CONFESSION_PROMPT))
  assert.match(room, /isFirstRunChatPending/)
  assert.match(room, /completeFirstRunAfterChat/)
  assert.match(room, /chatMessages\.value\.push\(\{ role: 'assistant', content: res\.data\.reply, emotion: res\.data\.emotion \}\)/)
  assert.match(room, /completeFirstRunAfterChat\(msg, res\.data\)/)
  assert.doesNotMatch(room, /function handleGuideTreeholeTarget\(\)[\s\S]*?localStorage\.setItem\(FIRST_RUN_GUIDE_KEY, FIRST_RUN_GUIDE_VERSION\)/)
})

test('v4.3 first-run mood card directs users to tree hole resonance', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /firstRunMoodCard/)
  assert.match(room, new RegExp(MOOD_CARD_TITLE))
  assert.match(room, /openTreeHoleFromMoodCard/)
  assert.match(room, /\u53bb\u6811\u6d1e\u770b\u770b/)
  assert.match(room, /buildFirstRunMoodCard/)
  assert.match(room, /localStorage\.setItem\(FIRST_RUN_MOOD_CARD_KEY/)
})

test('v4.3 daily return card includes task check-in and companionship streak', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /daily-return-card/)
  assert.match(room, new RegExp(DAILY_RETURN_TITLE))
  assert.match(room, /dailyCheckInOptions/)
  assert.match(room, /selectDailyMood/)
  assert.match(room, /completeDailyTask/)
  assert.match(room, /companionshipStreak/)
  assert.match(room, /shengyu_daily_return_state/)
  assert.match(room, /shengyu_companionship_streak/)
  assert.match(room, /shengyu_last_active_date/)
})
```

- [ ] **Step 2: Update versioning tests to expect 4.3.0**

In `frontend/tests/onboarding-versioning.test.mjs`, change the release test body to:

```js
test('feature release continues from latest 4.2.5 baseline and records changelog', async () => {
  const pkg = JSON.parse(await source('frontend/package.json'))
  const lock = JSON.parse(await source('frontend/package-lock.json'))
  const changelogPath = join(root, 'CHANGELOG.md')
  const info = await stat(changelogPath)
  assert.ok(info.isFile())
  const changelog = await source('CHANGELOG.md')

  assert.equal(pkg.version, '4.3.0')
  assert.equal(lock.version, '4.3.0')
  assert.equal(lock.packages[''].version, '4.3.0')
  assert.match(changelog, /## \[4\.3\.0\] - 2026-07-06/)
  assert.match(changelog, /4\.2\.5 -> 4\.3\.0/)
})
```

Update the first-run guide test to assert the new stage names:

```js
test('first-run guide requires a chat confession before completion', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /guideStage = ref\('computer'\)/)
  assert.match(room, /handleGuideChatTarget/)
  assert.match(room, /guideStage\.value = 'confession'/)
  assert.match(room, /completeFirstRunAfterChat/)
  assert.match(room, /guideStage\.value = 'mood-card'/)
  assert.match(room, /localStorage\.setItem\(FIRST_RUN_GUIDE_KEY, FIRST_RUN_GUIDE_VERSION\)/)
})
```

- [ ] **Step 3: Run the new tests and confirm they fail**

Run:

```powershell
node --test frontend/tests/engagement-entry.test.mjs frontend/tests/onboarding-versioning.test.mjs
```

Expected: tests fail because `guideStage`, `firstRunMoodCard`, daily return keys, and version `4.3.0` are not implemented yet.

---

### Task 2: Implement first-run activation loop

**Files:**
- Modify: `frontend/src/views/RoomHomeView.vue`
- Test: `frontend/tests/engagement-entry.test.mjs`
- Test: `frontend/tests/onboarding-versioning.test.mjs`

- [ ] **Step 1: Replace first-run template states**

In `frontend/src/views/RoomHomeView.vue`, replace the current `<section class="first-run-guide" v-if="showFirstRunGuide">...</section>` content with this structure while keeping the outer section:

```vue
<div class="guide-title">先完成一次小倾诉，马上会用咕哝</div>
<p class="guide-copy">跟着提示做完一次：点电脑、说一句、收下一张心情卡，再去树洞看看共鸣。</p>
<div class="guide-progress-row">
  <span :class="['guide-progress-dot', { active: guideStage === 'computer', done: guideStage !== 'computer' }]">1</span>
  <span class="guide-progress-line"></span>
  <span :class="['guide-progress-dot', { active: guideStage === 'confession', done: guideStage === 'mood-card' }]">2</span>
  <span class="guide-progress-line"></span>
  <span :class="['guide-progress-dot', { active: guideStage === 'mood-card' }]">3</span>
</div>

<div class="guide-target-hint" v-if="guideStage === 'computer'">
  <span class="guide-target-kicker">第一步</span>
  <strong>请点击房间里的电脑</strong>
  <em>电脑位置会发光，点它打开倾诉窗口。</em>
</div>
<div class="guide-target-hint" v-else-if="guideStage === 'confession'">
  <span class="guide-target-kicker">第二步</span>
  <strong>在倾诉窗口发出一句话</strong>
  <em>不用整理好语言，把今天最想说的一句话丢给咕哝就行。</em>
</div>
<div class="guide-mood-card" v-else>
  <span class="guide-target-kicker">完成一次倾诉</span>
  <strong>今日心情卡</strong>
  <p>{{ firstRunMoodCard.summary }}</p>
  <div class="guide-mood-meta">
    <span>{{ firstRunMoodCard.emoji }}</span>
    <span>{{ firstRunMoodCard.emotion }}</span>
  </div>
  <em>{{ firstRunMoodCard.suggestion }}</em>
</div>

<button v-if="guideStage !== 'mood-card'" class="guide-option is-primary" @click="focusGuideTarget">
  <span class="guide-option-icon">👆</span>
  <span>
    <strong>{{ guideStage === 'computer' ? '我知道了，带我去点电脑' : '我知道了，去说一句' }}</strong>
    <em>{{ guideStage === 'computer' ? '看房间里的电脑高亮' : '打开倾诉窗口后直接发送' }}</em>
  </span>
</button>
<button v-else class="guide-option is-primary" @click="openTreeHoleFromMoodCard">
  <span class="guide-option-icon">🌙</span>
  <span>
    <strong>去树洞看看</strong>
    <em>看看有没有人也有类似心情。</em>
  </span>
</button>
<button class="guide-secondary" @click="skipFirstRunGuide">跳过教学</button>
```

- [ ] **Step 2: Add first-run state and helpers**

In the script section near current first-run constants, replace the current first-run constants and state with:

```js
const FIRST_RUN_GUIDE_KEY = 'shengyu_first_run_guide_completed_version'
const FIRST_RUN_GUIDE_VERSION = '4.3.0'
const FIRST_RUN_MOOD_CARD_KEY = 'shengyu_first_run_mood_card'
const DAILY_RETURN_STATE_KEY = 'shengyu_daily_return_state'
const COMPANIONSHIP_STREAK_KEY = 'shengyu_companionship_streak'
const LAST_ACTIVE_DATE_KEY = 'shengyu_last_active_date'
const todayKey = new Date().toISOString().slice(0, 10)
const showFirstRunGuide = ref(localStorage.getItem(FIRST_RUN_GUIDE_KEY) !== FIRST_RUN_GUIDE_VERSION)
const guideStage = ref('computer')
const firstRunMoodCard = ref(loadFirstRunMoodCard())
const isFirstRunChatPending = computed(() => showFirstRunGuide.value && guideStage.value === 'confession')

function loadFirstRunMoodCard() {
  try {
    return JSON.parse(localStorage.getItem(FIRST_RUN_MOOD_CARD_KEY) || 'null') || {
      emoji: '🌿',
      emotion: '被听见',
      summary: '你已经把心里的话说出来了一点，这就很重要。',
      suggestion: '接下来可以看看树洞里有没有相似的心情。'
    }
  } catch {
    return {
      emoji: '🌿',
      emotion: '被听见',
      summary: '你已经把心里的话说出来了一点，这就很重要。',
      suggestion: '接下来可以看看树洞里有没有相似的心情。'
    }
  }
}

function buildFirstRunMoodCard(message, data) {
  const emotion = data?.emotion || '被听见'
  return {
    emoji: getEmotionEmoji(emotion),
    emotion,
    summary: message?.length > 18 ? '这句话里有一些不容易，你愿意说出来已经是在照顾自己。' : '这句话很短，但它已经让咕哝更靠近你一点。',
    suggestion: emotion === '疲惫' ? '先做一个很小的休息动作，比如喝水或离开屏幕一分钟。' : '如果愿意，可以去树洞看看有没有人也有类似心情。'
  }
}

function completeFirstRunAfterChat(message, data) {
  if (!showFirstRunGuide.value || guideStage.value !== 'confession') return
  firstRunMoodCard.value = buildFirstRunMoodCard(message, data)
  localStorage.setItem(FIRST_RUN_MOOD_CARD_KEY, JSON.stringify(firstRunMoodCard.value))
  localStorage.setItem(FIRST_RUN_GUIDE_KEY, FIRST_RUN_GUIDE_VERSION)
  guideStage.value = 'mood-card'
}
```

- [ ] **Step 3: Update target handlers and prompt**

Replace `onboardingStep` references in first-run target handling:

```js
function focusGuideTarget() {
  const selector = guideStage.value === 'computer' ? '.zone-monitor' : '.chat-panel .input-wrap input'
  document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
  if (guideStage.value === 'confession') {
    showChatPanel.value = true
    nextTick(() => inputEl.value?.focus?.())
  }
}

function handleGuideChatTarget() {
  goToChat()
  if (showFirstRunGuide.value && guideStage.value === 'computer') {
    guideStage.value = 'confession'
  }
}

function openTreeHoleFromMoodCard() {
  showFirstRunGuide.value = false
  showTreeHolePanel.value = true
}

function handleGuideTreeholeTarget() {
  showTreeHolePanel.value = true
  if (showFirstRunGuide.value && guideStage.value === 'mood-card') {
    showFirstRunGuide.value = false
  }
}

function skipFirstRunGuide() {
  showFirstRunGuide.value = false
  localStorage.setItem(FIRST_RUN_GUIDE_KEY, FIRST_RUN_GUIDE_VERSION)
}
```

Change the chat input placeholder to:

```vue
<input
  v-model="chatInput"
  :placeholder="isFirstRunChatPending ? '把今天最想说的一句话丢给我' : '说说你的感受...'"
  @keyup.enter="sendChatMsg()"
  :disabled="chatLoading"
  ref="inputEl"
/>
```

- [ ] **Step 4: Complete first-run only after successful assistant reply**

In `sendChatMsg`, immediately after pushing the successful assistant message:

```js
if (res.data?.reply) {
  chatMessages.value.push({ role: 'assistant', content: res.data.reply, emotion: res.data.emotion })
  completeFirstRunAfterChat(msg, res.data)
} else {
  chatMessages.value.push({ role: 'assistant', content: '抱歉，我暂时无法回复，请稍后再试...' })
}
```

- [ ] **Step 5: Run tests for this task**

Run:

```powershell
node --test frontend/tests/engagement-entry.test.mjs frontend/tests/onboarding-versioning.test.mjs
```

Expected: first-run tests pass or only daily/version tests still fail.

---

### Task 3: Implement daily return card

**Files:**
- Modify: `frontend/src/views/RoomHomeView.vue`
- Test: `frontend/tests/engagement-entry.test.mjs`

- [ ] **Step 1: Replace daily card template**

Replace the current `<section class="daily-ritual-card" v-else>` with:

```vue
<section class="daily-return-card" v-else>
  <div class="ritual-glow"></div>
  <div class="ritual-meta-row">
    <div class="ritual-orb">{{ dailyReturnTask.emoji }}</div>
    <div>
      <div class="ritual-kicker">今日咕哝</div>
      <div class="ritual-date">你已经陪自己 {{ companionshipStreak }} 天了</div>
    </div>
  </div>
  <div class="ritual-title">今天也给自己留一分钟</div>
  <p class="ritual-copy">{{ dailyReturnTask.copy }}</p>
  <div class="daily-check-row">
    <button
      v-for="option in dailyCheckInOptions"
      :key="option.value"
      :class="['daily-check-pill', { active: dailyReturnState.mood === option.value }]"
      @click="selectDailyMood(option.value)"
    >
      <span>{{ option.emoji }}</span>
      {{ option.label }}
    </button>
  </div>
  <button class="ritual-action" @click="completeDailyTask">
    {{ dailyReturnState.taskDone ? '今天已经照顾过自己一点了' : dailyReturnTask.actionText }}
  </button>
</section>
```

- [ ] **Step 2: Add daily state helpers**

Add this script block after first-run helpers:

```js
const dailyCheckInOptions = [
  { value: 'tired', label: '很累', emoji: '😴' },
  { value: 'annoyed', label: '有点烦', emoji: '😕' },
  { value: 'okay', label: '还可以', emoji: '🙂' },
  { value: 'relaxed', label: '轻松', emoji: '🌤️' },
  { value: 'happy', label: '开心', emoji: '😊' },
]

const dailyReturnTasks = [
  { emoji: '💬', copy: '把今天最累的一件事说出来，不需要解释清楚。', actionText: '说出今天最累的一件事', action: 'chat' },
  { emoji: '🌙', copy: '去树洞看看一个相似心情，知道不是只有你这样。', actionText: '去树洞看看', action: 'treehole' },
  { emoji: '🌿', copy: '给自己写一句安慰，哪怕很短也算数。', actionText: '写一句安慰', action: 'chat' },
]

const dailyReturnTask = computed(() => {
  const sum = [...todayKey].reduce((total, char) => total + char.charCodeAt(0), 0)
  return dailyReturnTasks[sum % dailyReturnTasks.length]
})

const dailyReturnState = reactive(loadDailyReturnState())
const companionshipStreak = ref(loadCompanionshipStreak())

function loadDailyReturnState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(DAILY_RETURN_STATE_KEY) || '{}')
    if (parsed.date === todayKey) return { date: todayKey, mood: parsed.mood || '', taskDone: Boolean(parsed.taskDone) }
  } catch {}
  return { date: todayKey, mood: '', taskDone: false }
}

function saveDailyReturnState() {
  localStorage.setItem(DAILY_RETURN_STATE_KEY, JSON.stringify(dailyReturnState))
}

function loadCompanionshipStreak() {
  const raw = Number(localStorage.getItem(COMPANIONSHIP_STREAK_KEY) || '0')
  return Number.isFinite(raw) && raw > 0 ? raw : 1
}

function updateCompanionshipStreak() {
  const last = localStorage.getItem(LAST_ACTIVE_DATE_KEY)
  if (last === todayKey) return
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  companionshipStreak.value = last === yesterday ? companionshipStreak.value + 1 : 1
  localStorage.setItem(COMPANIONSHIP_STREAK_KEY, String(companionshipStreak.value))
  localStorage.setItem(LAST_ACTIVE_DATE_KEY, todayKey)
}

function selectDailyMood(value) {
  dailyReturnState.mood = value
  saveDailyReturnState()
  updateCompanionshipStreak()
}

function completeDailyTask() {
  dailyReturnState.taskDone = true
  saveDailyReturnState()
  updateCompanionshipStreak()
  if (dailyReturnTask.value.action === 'treehole') {
    showTreeHolePanel.value = true
    return
  }
  goToChat()
}
```

- [ ] **Step 3: Update card CSS class aliases**

Update CSS selectors that currently target `.daily-ritual-card` to also target `.daily-return-card`:

```css
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
.daily-check-row {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0 12px;
}
.daily-check-pill {
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 999px;
  padding: 5px 8px;
  background: rgba(255,255,255,0.09);
  color: rgba(255,255,255,0.78);
  font-size: 11px;
  cursor: pointer;
}
.daily-check-pill.active {
  background: rgba(255,230,178,0.92);
  color: #2f2114;
  font-weight: 800;
}
.guide-mood-card {
  display: grid;
  gap: 6px;
  margin: 10px 0 12px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 239, 202, 0.16);
  border: 1px solid rgba(255, 226, 170, 0.26);
}
.guide-mood-card p {
  margin: 0;
  color: rgba(255,255,255,0.78);
  font-size: 12px;
  line-height: 1.5;
}
.guide-mood-meta {
  display: inline-flex;
  width: max-content;
  gap: 6px;
  align-items: center;
  border-radius: 999px;
  padding: 4px 8px;
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.82);
  font-size: 11px;
}
```

- [ ] **Step 4: Run tests for this task**

Run:

```powershell
node --test frontend/tests/engagement-entry.test.mjs frontend/tests/onboarding-versioning.test.mjs
```

Expected: daily return tests pass or only version tests still fail.

---

### Task 4: Update version and changelog

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `CHANGELOG.md`
- Test: `frontend/tests/onboarding-versioning.test.mjs`

- [ ] **Step 1: Update package versions**

Set `frontend/package.json`:

```json
"version": "4.3.0"
```

Set both version fields in `frontend/package-lock.json`:

```json
"version": "4.3.0"
```

and:

```json
"packages": {
  "": {
    "version": "4.3.0"
  }
}
```

- [ ] **Step 2: Prepend changelog entry**

Add this entry at the top of `CHANGELOG.md`, below the title:

```markdown
## [4.3.0] - 2026-07-06

功能更新

- 从 4.2.5 -> 4.3.0，新增轻量双闭环：首次倾诉闭环与每日回访机制。
- 首次体验改为“点击电脑、发送一句话、生成今日心情卡、引导树洞共鸣”，仅在成功收到 AI 回复后才标记完成。
- 每日卡片升级为今日小任务、情绪签到与连续陪伴天数，使用本地记录保持轻量可用。
```

- [ ] **Step 3: Run version tests**

Run:

```powershell
node --test frontend/tests/onboarding-versioning.test.mjs
```

Expected: all tests in the file pass.

---

### Task 5: Full verification, commit, and deploy

**Files:**
- Verify all modified files.
- Commit all V4.3 implementation files.
- Deploy with existing script.

- [ ] **Step 1: Run full frontend source tests**

Run:

```powershell
node --test frontend/tests/onboarding-versioning.test.mjs frontend/tests/engagement-entry.test.mjs frontend/tests/ops-polish.test.mjs frontend/tests/public-entry-polish.test.mjs frontend/tests/demo-auto-entry.test.mjs frontend/tests/teacher-portal-labels.test.mjs
```

Expected: `# fail 0`.

- [ ] **Step 2: Run production build**

Run:

```powershell
npm.cmd run build
```

from `frontend`.

Expected: Vite build completes and emits `dist/index.html` plus asset files.

- [ ] **Step 3: Check source hygiene**

Run:

```powershell
git diff --check
rg -n "mini-tools-bar|openMiniApp|miniAppUrl|mini-app-iframe|giao\\.me/air|giao\\.me/itv|showMiniApp|小空调|小电视|小掌机" frontend/src/views/RoomHomeView.vue
git status --short
```

Expected: `git diff --check` has no errors; `rg` finds no source match; `git status --short` lists only intended files.

- [ ] **Step 4: Commit**

Run:

```powershell
git add CHANGELOG.md frontend/package-lock.json frontend/package.json frontend/src/views/RoomHomeView.vue frontend/tests/engagement-entry.test.mjs frontend/tests/onboarding-versioning.test.mjs
git commit -m "feat: add v4.3 engagement loop"
```

Expected: commit succeeds.

- [ ] **Step 5: Deploy to Tencent Cloud**

Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy-frontend.ps1
```

Expected: script builds and prints:

```text
Frontend deployed to ubuntu@43.136.69.47:/opt/shengyu/frontend/dist
Version: 4.3.0+<commit>
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

- [ ] **Step 6: Verify online deployment**

After deployment, run:

```powershell
$idx=Join-Path (Get-Location) '.codex-online-index.html'
$js=Join-Path (Get-Location) '.codex-online-app.js'
curl.exe -I https://www.guunoo.online/
curl.exe -L https://www.guunoo.online/ -o $idx
$asset=(Select-String -Path $idx -Pattern '/assets/index-[^"'']+\.js').Matches.Value | Select-Object -First 1
curl.exe -L "https://www.guunoo.online$asset" -o $js
$text=[System.IO.File]::ReadAllText($js)
Write-Output ("has_version=" + $text.Contains('4.3.0+'))
Write-Output ("has_daily_loop=" + $text.Contains('今天也给自己留一分钟'))
Write-Output ("has_first_prompt=" + $text.Contains('把今天最想说的一句话丢给我'))
Write-Output ("removed_air=" + (-not $text.Contains('giao.me/air')))
Write-Output ("removed_itv=" + (-not $text.Contains('giao.me/itv')))
Remove-Item -LiteralPath $idx,$js -Force
```

Expected:

```text
HTTP/1.1 200 OK
has_version=True
has_daily_loop=True
has_first_prompt=True
removed_air=True
removed_itv=True
```

---

## Self-Review

- Spec coverage: covered first-run activation, daily return loop, local persistence, versioning, error handling, tests, build, and deployment.
- Scope check: no backend changes, no teacher dashboard, no tree hole rewrite, no room growth system.
- Placeholder scan: no placeholder markers or unspecified implementation steps remain.
- Type consistency: first-run state uses `guideStage`, local card uses `firstRunMoodCard`, daily state uses `dailyReturnState`, and version is consistently `4.3.0`.
