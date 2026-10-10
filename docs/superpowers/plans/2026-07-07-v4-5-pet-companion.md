# v4.5.0 Pet Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight pet companion system to the student home room that improves daily return motivation through mood-aware pet state, local affinity, and three simple interactions.

**Architecture:** Keep v1 frontend-only. Add a focused pet state block inside `RoomHomeView.vue`, reuse existing daily mood and chat-opening flows, and protect the behavior with source-level tests. Persist state in `localStorage` under a versioned key.

**Tech Stack:** Vue 3 Composition API, Vite, localStorage, existing Node test runner.

---

## File Structure

- Modify `frontend/src/views/RoomHomeView.vue`: add pet companion card, state model, interactions, mood linkage, and styles.
- Modify `frontend/tests/engagement-entry.test.mjs`: add assertions for pet companion UI and behavior markers.
- Modify `frontend/tests/onboarding-versioning.test.mjs`: update expected version/changelog from `4.4.1` to `4.5.0`.
- Modify `frontend/package.json` and `frontend/package-lock.json`: bump version to `4.5.0`.
- Modify `CHANGELOG.md`: add `4.5.0` feature update.

---

### Task 1: Lock pet companion expectations in tests

**Files:**
- Modify: `frontend/tests/engagement-entry.test.mjs`

- [ ] **Step 1: Add a failing pet companion test**

Append this test near the existing engagement tests:

```js
test('student room includes mood-aware pet companion loop', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /pet-companion-card/)
  assert.match(room, /咕哝小伙伴/)
  assert.match(room, /PET_COMPANION_STATE_KEY/)
  assert.match(room, /petCompanionState/)
  assert.match(room, /petMoodStatus/)
  assert.match(room, /petAffinityLabel/)
  assert.match(room, /petCompanionMessage/)
  assert.match(room, /petPetting/)
  assert.match(room, /feedPetSnack/)
  assert.match(room, /talkWithPet/)
  assert.match(room, /updatePetFromMood/)
})
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```powershell
node --test frontend/tests/engagement-entry.test.mjs
```

Expected: FAIL because `pet-companion-card` does not exist yet.

---

### Task 2: Add pet state and interaction logic

**Files:**
- Modify: `frontend/src/views/RoomHomeView.vue`

- [ ] **Step 1: Add constants and state near daily return state**

Add these near the existing `DAILY_RETURN_STATE_KEY` block:

```js
const PET_COMPANION_STATE_KEY = 'shengyu_pet_companion_v4_5_0'
const petMoodMessages = {
  tired: ['今天有点累的话，先靠着我坐一会儿。', '不用马上恢复精神，我会慢慢陪你。'],
  annoyed: ['烦的时候不用讲清楚全部，先说一句也可以。', '我在这里，先把最吵的那件事放下来。'],
  okay: ['今天能回来看看自己，就已经很好了。', '我们先安静待一分钟。'],
  happy: ['你今天轻一点了，我也跟着开心。', '这份轻松值得被记住。'],
  sleepy: ['夜深了，我陪你把声音放轻一点。', '今天先不用逞强，早点休息也很好。'],
}
const petCompanionState = reactive(loadPetCompanionState())
```

- [ ] **Step 2: Add load/save helpers**

Add:

```js
function loadPetCompanionState() {
  try {
    const saved = JSON.parse(localStorage.getItem(PET_COMPANION_STATE_KEY) || 'null')
    if (saved && typeof saved === 'object') {
      return {
        affinity: Number.isFinite(Number(saved.affinity)) ? Number(saved.affinity) : 1,
        lastInteractionDate: saved.lastInteractionDate || '',
        pettedDate: saved.pettedDate || '',
        fedDate: saved.fedDate || '',
        mood: saved.mood || '',
        status: saved.status || 'okay',
        message: saved.message || '我在这里，等你回来。',
      }
    }
  } catch {}
  return { affinity: 1, lastInteractionDate: '', pettedDate: '', fedDate: '', mood: '', status: 'okay', message: '我在这里，等你回来。' }
}

function savePetCompanionState() {
  localStorage.setItem(PET_COMPANION_STATE_KEY, JSON.stringify({ ...petCompanionState }))
}
```

- [ ] **Step 3: Add computed labels and message picker**

Add:

```js
const petMoodStatus = computed(() => {
  if (timeOfDay.value === 'night' && !['很累', '有点烦'].includes(petCompanionState.mood)) return 'sleepy'
  return petCompanionState.status || 'okay'
})

const petAffinityLabel = computed(() => {
  if (petCompanionState.affinity >= 8) return '它已经习惯等你回来'
  if (petCompanionState.affinity >= 4) return '它开始记得你常来的时间'
  return '它还在慢慢认识你'
})

const petCompanionMessage = computed(() => petCompanionState.message || pickPetMessage(petMoodStatus.value))

function pickPetMessage(status) {
  const list = petMoodMessages[status] || petMoodMessages.okay
  const seed = todayKey.split('').reduce((sum, ch) => sum + ch.charCodeAt(0), 0) + petCompanionState.affinity
  return list[seed % list.length]
}
```

- [ ] **Step 4: Add interaction functions**

Add:

```js
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

function talkWithPet() {
  bumpPetAffinityOnce('talkDate')
  setPetStatus(petMoodStatus.value, '我会听你说完，不急着给答案。')
  openChatPanel()
}
```

- [ ] **Step 5: Link daily mood to pet state**

Inside existing `selectDailyMood(option)`, after `saveDailyReturnState()`, call:

```js
updatePetFromMood(option)
```

Add:

```js
function updatePetFromMood(option) {
  petCompanionState.mood = option
  if (option === '很累') setPetStatus('tired')
  else if (option === '有点烦') setPetStatus('annoyed')
  else if (option === '轻松' || option === '开心') setPetStatus('happy')
  else setPetStatus('okay')
}
```

- [ ] **Step 6: Link daily task completion to pet state**

Inside existing `completeDailyTask()`, after `saveDailyReturnState()`, add:

```js
bumpPetAffinityOnce('taskDate')
setPetStatus('happy', '你完成了今天的小照顾，它也替你松了一口气。')
```

---

### Task 3: Add pet companion UI and styles

**Files:**
- Modify: `frontend/src/views/RoomHomeView.vue`

- [ ] **Step 1: Insert pet card after the daily return card**

Add this section after the first-run/daily-return card block:

```vue
<section class="pet-companion-card">
  <div class="pet-orb" :class="`is-${petMoodStatus}`">
    <span class="pet-face">{{ petMoodStatus === 'sleepy' ? '😴' : petMoodStatus === 'tired' ? '🥺' : petMoodStatus === 'annoyed' ? '😿' : petMoodStatus === 'happy' ? '😸' : '🐾' }}</span>
  </div>
  <div class="pet-body">
    <div class="pet-kicker">咕哝小伙伴</div>
    <h3>{{ petAffinityLabel }}</h3>
    <p>{{ petCompanionMessage }}</p>
    <div class="pet-meta-row">
      <span>亲密度 {{ petCompanionState.affinity }}</span>
      <span>陪伴 {{ companionshipStreak }} 天</span>
    </div>
    <div class="pet-actions">
      <button @click="petPetting">摸摸</button>
      <button @click="feedPetSnack">喂点心</button>
      <button class="is-primary" @click="talkWithPet">说句话</button>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Add styles near daily card styles**

Add:

```css
.pet-companion-card {
  position: absolute;
  left: 84px;
  top: 230px;
  z-index: 24;
  width: min(360px, calc(100vw - 32px));
  display: grid;
  grid-template-columns: 74px 1fr;
  gap: 14px;
  padding: 16px;
  border-radius: 22px;
  background: rgba(28, 24, 35, 0.62);
  color: #fff8e8;
  border: 1px solid rgba(255, 232, 178, 0.24);
  box-shadow: 0 18px 48px rgba(0,0,0,0.28);
  backdrop-filter: blur(16px);
}
.pet-orb { width: 74px; height: 74px; border-radius: 24px; display: grid; place-items: center; background: rgba(255,255,255,0.14); }
.pet-orb.is-happy { background: rgba(255, 208, 112, 0.2); }
.pet-orb.is-tired, .pet-orb.is-annoyed { background: rgba(143, 183, 218, 0.22); }
.pet-orb.is-sleepy { background: rgba(122, 106, 168, 0.25); }
.pet-face { font-size: 34px; filter: drop-shadow(0 8px 16px rgba(0,0,0,0.24)); }
.pet-body { display: grid; gap: 6px; min-width: 0; }
.pet-kicker { font-size: 12px; color: rgba(255,248,232,0.68); }
.pet-body h3 { font-size: 16px; line-height: 1.35; }
.pet-body p { font-size: 13px; line-height: 1.55; color: rgba(255,248,232,0.78); }
.pet-meta-row { display: flex; gap: 8px; flex-wrap: wrap; font-size: 11px; color: rgba(255,248,232,0.66); }
.pet-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.pet-actions button { padding: 7px 10px; border-radius: 999px; background: rgba(255,255,255,0.14); color: #fff8e8; font-size: 12px; }
.pet-actions button.is-primary { background: rgba(255, 214, 126, 0.92); color: #3a2812; font-weight: 800; }
@media (max-width: 760px) {
  .pet-companion-card { left: 14px; right: 14px; top: 220px; width: auto; }
}
```

---

### Task 4: Version, changelog, verification, commit

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/tests/onboarding-versioning.test.mjs`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump version to 4.5.0**

Set `version` in both package files to `4.5.0`.

- [ ] **Step 2: Add changelog entry**

Add:

```markdown
## [4.5.0] - 2026-07-07

功能更新

- 从 4.4.1 -> 4.5.0：新增学生端宠物陪伴系统第一版。
- 新增“咕哝小伙伴”卡片，包含宠物状态、亲密度、陪伴天数和今日陪伴语。
- 宠物会根据每日心情签到切换平静、担心、开心、困困状态。
- 新增摸摸、喂点心、说句话三个轻互动，增强每日回访动力。
- 第一版使用 localStorage 保存本地状态，不引入后端同步风险。
```

- [ ] **Step 3: Update version test**

Update `frontend/tests/onboarding-versioning.test.mjs` to expect `4.5.0`, changelog `4.5.0`, and `4.4.1 -> 4.5.0`.

- [ ] **Step 4: Run verification**

Run:

```powershell
node --test frontend/tests/engagement-entry.test.mjs frontend/tests/onboarding-versioning.test.mjs
npm --prefix frontend run build
git diff --check
```

Expected: tests pass, build succeeds, no diff check errors.

- [ ] **Step 5: Commit**

Run:

```powershell
git add CHANGELOG.md frontend/package.json frontend/package-lock.json frontend/src/views/RoomHomeView.vue frontend/tests/engagement-entry.test.mjs frontend/tests/onboarding-versioning.test.mjs docs/superpowers/specs/2026-07-07-v4-5-pet-companion-design.md docs/superpowers/plans/2026-07-07-v4-5-pet-companion.md
git commit -m "feat: add student pet companion loop"
```
