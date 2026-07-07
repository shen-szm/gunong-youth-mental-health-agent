import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const GUIDE_TITLE = '\u8ddf\u7740\u63d0\u793a\u70b9\u4e24\u4e0b\uff0c\u9a6c\u4e0a\u4f1a\u7528\u5495\u54dd'
const CLICK_COMPUTER = '\u8bf7\u70b9\u51fb\u623f\u95f4\u91cc\u7684\u7535\u8111'
const CLICK_TREEHOLE = '\u8bf7\u70b9\u51fb\u5e95\u90e8\u5bfc\u822a\u7684\u6811\u6d1e'
const FIRST_CONFESSION_PROMPT = '\u628a\u4eca\u5929\u6700\u60f3\u8bf4\u7684\u4e00\u53e5\u8bdd\u4e22\u7ed9\u6211'
const MOOD_CARD_TITLE = '\u4eca\u65e5\u5fc3\u60c5\u5361'
const DAILY_RETURN_TITLE = '\u4eca\u5929\u4e5f\u7ed9\u81ea\u5df1\u7559\u4e00\u5206\u949f'

async function source(path) {
  return readFile(join(root, path), 'utf8')
}

function functionBody(src, name) {
  const start = src.indexOf(`function ${name}(`)
  assert.notEqual(start, -1, `${name} should exist`)
  const braceStart = src.indexOf('{', start)
  let depth = 0
  for (let i = braceStart; i < src.length; i += 1) {
    if (src[i] === '{') depth += 1
    if (src[i] === '}') depth -= 1
    if (depth === 0) return src.slice(braceStart + 1, i)
  }
  throw new Error(`${name} body not closed`)
}

test('room home offers first-run teaching for new visitors', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /first-run-guide/)
  assert.match(room, new RegExp(GUIDE_TITLE))
  assert.match(room, /handleGuideChatTarget/)
  assert.match(room, /handleGuideTreeholeTarget/)
  assert.match(room, /shengyu_first_run_guide_completed_version/)
})
test('v4.3 first-run loop completes only after a successful first confession', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /guideStage = ref\('computer'\)/)
  assert.match(room, /FIRST_RUN_GUIDE_VERSION = '4\.3\.0'/)
  assert.match(room, new RegExp(FIRST_CONFESSION_PROMPT))
  assert.match(room, /isFirstRunChatPending/)
  assert.match(room, /completeFirstRunAfterChat/)
  assert.match(room, /res\.data\?\.reply/)
  assert.match(room, /chatMessages\.value\.push/)
  assert.match(room, /role: 'assistant'/)
  assert.match(room, /content: res\.data\.reply/)
  assert.match(room, /emotion: res\.data\.emotion/)
  assert.match(room, /completeFirstRunAfterChat\(msg, res\.data\)/)
  const treeholeHandler = functionBody(room, 'handleGuideTreeholeTarget')
  assert.doesNotMatch(treeholeHandler, /localStorage\.setItem\(FIRST_RUN_GUIDE_KEY, FIRST_RUN_GUIDE_VERSION\)/)
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
  const selectMoodBody = functionBody(room, 'selectDailyMood')
  assert.match(selectMoodBody, /updateCompanionshipStreak\(\)/)
  const loadStreakBody = functionBody(room, 'loadCompanionshipStreak')
  assert.doesNotMatch(loadStreakBody, /updateCompanionshipStreak\(\)/)
  assert.doesNotMatch(loadStreakBody, /localStorage\.setItem/)
  const completeTaskBody = functionBody(room, 'completeDailyTask')
  assert.match(completeTaskBody, /updateCompanionshipStreak\(\)/)
})

test('room home replaces the old daily ritual with a daily return card', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /daily-return-card" v-else/)
  assert.match(room, /dailyReturnTask/)
  assert.match(room, /dailyReturnTasks/)
  assert.match(room, /completeDailyTask/)
  assert.match(room, /showTreeHolePanel.value = true/)
  assert.doesNotMatch(room, /daily-ritual-card" v-else/)
  assert.doesNotMatch(room, /dailyRitualSeed/)
  assert.doesNotMatch(room, /openDailyRitualAction/)
  assert.doesNotMatch(room, /shengyu_daily_ritual_seen/)
})

test('engagement cards are responsive and do not block core room interactions', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /\.engagement-stack/)
  assert.match(room, /pointer-events:\s*none/)
  assert.match(room, /\.daily-return-card,[\s\S]*?\.first-run-guide[\s\S]*?pointer-events:\s*auto/)
  assert.match(room, /@media \(max-width: 520px\)[\s\S]*?\.engagement-stack/)
})

test('onboarding highlights the exact room target users should click', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /guide-target-hint/)
  assert.match(room, new RegExp(CLICK_COMPUTER))
  assert.match(room, new RegExp(CLICK_TREEHOLE))
  assert.match(room, /:class="\['hot-zone zone-monitor'/)
  assert.match(room, /guideStage === 'computer'/)
  assert.match(room, /'is-guide-target': showFirstRunGuide && guideStage === 'computer'/)
  assert.match(room, /@click="handleGuideChatTarget"/)
  assert.match(room, /@click="handleGuideTreeholeTarget"/)
  assert.match(room, /guide-target-badge/)
})

test('air-conditioner and TV mini tools are removed completely', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.doesNotMatch(room, /mini-tools-bar/)
  assert.doesNotMatch(room, /openMiniApp/)
  assert.doesNotMatch(room, /miniAppUrl/)
  assert.doesNotMatch(room, /mini-app-iframe/)
  assert.doesNotMatch(room, /giao\.me\/air/)
  assert.doesNotMatch(room, /giao\.me\/itv/)
})

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
  assert.match(room, /\.pet-companion-card \{[\s\S]*?position:\s*fixed/)
  assert.match(room, /\.pet-companion-card \{[\s\S]*?right:\s*24px/)
  assert.match(room, /\.pet-actions button \{[\s\S]*?min-width:\s*74px/)
  assert.match(room, /@media \(max-width: 760px\)[\s\S]*?\.pet-companion-card \{[\s\S]*?left:\s*12px/)
})
