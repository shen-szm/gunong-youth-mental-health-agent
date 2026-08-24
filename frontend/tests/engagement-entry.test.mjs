import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const GUIDE_TITLE = '\u5148\u4ece\u623f\u95f4\u91cc\u7684\u7535\u8111\u5f00\u59cb'
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

  assert.match(room, /room-onboarding-cue/)
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

test('daily check-in is consolidated into the room status and action system', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')
  const actionBar = await source('frontend/src/components/RoomActionBar.vue')

  assert.match(room, new RegExp(DAILY_RETURN_TITLE))
  assert.match(room, /room-status-checkin/)
  assert.match(room, /selectRoomFeature\('daily', \$event\)/)
  assert.match(actionBar, /room-action-moods/)
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

test('room home removes the old daily card while preserving its task loop', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.doesNotMatch(room.slice(0, room.indexOf('<script setup>')), /daily-return-card/)
  assert.match(room, /dailyReturnTask/)
  assert.match(room, /dailyReturnTasks/)
  assert.match(room, /completeDailyTask/)
  assert.match(room, /openWorkspacePanel\('treehole'\)/)
  assert.doesNotMatch(room, /daily-ritual-card" v-else/)
  assert.doesNotMatch(room, /dailyRitualSeed/)
  assert.doesNotMatch(room, /openDailyRitualAction/)
  assert.doesNotMatch(room, /shengyu_daily_ritual_seen/)
})

test('one responsive action bar replaces stacked engagement cards', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')
  const actionBar = await source('frontend/src/components/RoomActionBar.vue')

  assert.match(room, /<RoomActionBar/)
  assert.match(room, /selectedRoomFeature/)
  assert.match(room, /runSelectedRoomFeature/)
  assert.match(actionBar, /bottom:\s*calc\(112px \+ env\(safe-area-inset-bottom\)\)/)
  assert.match(actionBar, /bottom:\s*calc\(100px \+ env\(safe-area-inset-bottom\)\)/)
  assert.match(actionBar, /@media \(max-width: 640px\)/)
})

test('onboarding highlights the exact room target users should click', async () => {
  const room = await source('frontend/src/views/RoomHomeView.vue')

  assert.match(room, /:class="\['hot-zone zone-monitor'/)
  assert.match(room, /guideStage === 'computer'/)
  assert.match(room, /'is-guide-target': showFirstRunGuide && guideStage === 'computer'/)
  assert.match(room, /@click\.stop="selectRoomFeature\('chat', \$event\)"/)
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

  assert.doesNotMatch(room.slice(0, room.indexOf('<script setup>')), /pet-companion-card/)
  assert.match(room, /PET_COMPANION_STATE_KEY/)
  assert.match(room, /petCompanionState/)
  assert.match(room, /petMoodStatus/)
  assert.match(room, /petAffinityLabel/)
  assert.match(room, /petCompanionMessage/)
  assert.match(room, /petPetting/)
  assert.match(room, /feedPetSnack/)
  assert.match(room, /talkWithPet/)
  assert.match(room, /updatePetFromMood/)
  assert.match(room, /showPetCompanionPanel/)
  assert.match(room, /pet-panel-overlay/)
  assert.match(room, /room-roaming-pet/)
  assert.match(room, /handleRoomPetMove/)
  assert.match(room, /openPetPlayground/)
  assert.match(room, /pet-playground-stage/)
  assert.match(room, /ROOM_PET_POSITION_KEY/)
  assert.match(room, /@click\.stop="selectRoomFeature\('pet', \$event\)"/)
  assert.match(room, /@click\.stop="petPetting"/)
  assert.match(room, /@click\.stop="feedPetSnack"/)
  assert.match(room, /@click\.stop="talkWithPet"/)
  assert.match(room, /id: 'pet'[\s\S]*?actionLabel: '\u548c\u5b83\u5f85\u4e00\u4f1a'/)
  assert.match(room, /PET_COMPANION_PROFILES/)
  assert.match(room, /petCompanionActive/)
  assert.match(room, /pet-companion-list/)
  assert.match(room, /pet-companion-chat/)
  assert.match(room, /startPetCompanion/)
  assert.match(room, /sendPetCompanionMsg/)
  assert.match(room, new RegExp('/api/companion/list'))
  assert.match(room, /sendMessage\(/)
  assert.doesNotMatch(room, new RegExp('/api/companion/chat'))
  assert.match(room, /PET_VISUALS/)
  assert.match(room, /selectedPetFrame/)
  assert.match(room, /selectPetVisual/)
  assert.match(room, /pet-visual-picker/)
  assert.match(room, /pet-visual-list/)
  assert.match(room, new RegExp('/pets/bubu/'))
  assert.doesNotMatch(room, new RegExp('/pets/snorlax/'))
  assert.doesNotMatch(room, new RegExp('/pets/kabi/'))
})
