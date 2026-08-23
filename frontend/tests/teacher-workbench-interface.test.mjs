import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const view = readFileSync(new URL('../src/views/AdminView.vue', import.meta.url), 'utf8')
const today = readFileSync(new URL('../src/components/TeacherTodayDashboard.vue', import.meta.url), 'utf8')
const adminApi = readFileSync(new URL('../../backend/api/admin.py', import.meta.url), 'utf8')
const teacherApi = readFileSync(new URL('../../backend/api/teacher.py', import.meta.url), 'utf8')

test('teacher application uses a consistent sidebar and today-first hierarchy', () => {
  assert.match(view, /const tab = ref\('today'\)/)
  assert.match(view, /teacher-sidebar/)
  assert.match(view, /teacher-topbar/)
  assert.match(view, /visibleNavItems/)
  assert.match(view, /搜索当前职责范围内的学生/)
  assert.match(view, /event\.metaKey \|\| event\.ctrlKey/)
  assert.match(today, /今日任务队列/)
  assert.match(today, /当前队列状态/)
  assert.match(today, /教师裁决/)
})

test('teacher workbench exposes verified progress without private reasoning', () => {
  assert.match(today, /不代表一次 Agent 运行/)
  assert.match(today, /不展示私有思维过程/)
  assert.match(today, /不会自动联系学生或家长/)
  assert.doesNotMatch(today, /思考过程|思维链详情|置信度\s*\d/)
  assert.match(today, /item\.urgent === true/)
  assert.match(today, /\.sort\([\s\S]*?\.slice\(0, 5\)/)
  assert.doesNotMatch(today, /risk_level === 'high' \? 'urgent'/)
})

test('admin-only views are guarded in navigation, state changes, and rendering', () => {
  assert.match(view, /adminOnly: true/)
  assert.match(view, /!item\.adminOnly \|\| userStore\.isSuperAdmin/)
  assert.match(view, /!visibleNavItems\.value\.some\(item => item\.id === name\)/)
  assert.match(view, /tab === 'students' && userStore\.isSuperAdmin/)
  assert.match(view, /tab === 'accounts' && userStore\.isSuperAdmin/)
})

test('teacher reports avoid non-standard emotion averages and diagnostic claims', () => {
  assert.doesNotMatch(view, /平均情绪|情绪记录均值|健康状态阈值/)
  assert.doesNotMatch(adminApi, /情绪记录均值为/)
  assert.doesNotMatch(teacherApi, /"avg_score": avg/)
  assert.doesNotMatch(teacherApi, /"avg_mood_score"/)
  assert.doesNotMatch(adminApi, /"avg": round\(sum/)
  assert.match(view, /不作心理测评或诊断/)
  assert.match(adminApi, /学生意愿和线下观察/)
  assert.match(view, /规则化记录整理/)
})

test('teacher layout includes mobile and reduced-motion behavior', () => {
  assert.match(view, /@media \(max-width: 760px\)/)
  assert.match(view, /prefers-reduced-motion: reduce/)
  assert.match(today, /@media \(max-width: 720px\)/)
  assert.match(today, /prefers-reduced-motion: reduce/)
})
