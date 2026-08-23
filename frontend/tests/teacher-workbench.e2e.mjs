import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { chromium } from 'playwright-core'

const shouldRun = process.env.RUN_TEACHER_E2E === '1'
const baseURL = process.env.TEACHER_E2E_URL || 'http://127.0.0.1:5174/admin'
const edgePath = process.env.EDGE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const screenshotDir = process.env.TEACHER_E2E_SCREENSHOT_DIR || ''

const students = [
  { id: 21, nickname: '林同学', mood_count: 7, risk_level: 'middle', last_active: '今天 09:30', access: { status: 'direct', label: '管理员可直达' } },
  { id: 22, nickname: '陈同学', mood_count: 3, risk_level: 'low', last_active: '昨天 20:10', access: { status: 'not_requested', label: '未申请' } },
]

function json(route, value) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(value) })
}

test('teacher workbench renders today-first desktop and mobile layouts',
  { skip: shouldRun ? false : 'set RUN_TEACHER_E2E=1 with local frontend running' }, async () => {
    const browser = await chromium.launch({ executablePath: edgePath, headless: true })
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    const page = await context.newPage()
    const pageErrors = []
    page.on('pageerror', error => pageErrors.push(error.message))
    await page.addInitScript(() => {
      localStorage.setItem('shengyu_user_id', '2')
      localStorage.setItem('shengyu_nickname', '管理员教师')
      localStorage.setItem('shengyu_is_admin', '1')
      localStorage.setItem('shengyu_is_super_admin', '1')
      localStorage.setItem('shengyu_role', 'admin_teacher')
    })
    await page.route('**/api/**', route => {
      const url = new URL(route.request().url())
      if (!url.pathname.startsWith('/api/')) return route.continue()
      if (url.pathname === '/api/user/me') return json(route, { user_id: 2, nickname: '管理员教师', is_admin: true, is_super_admin: true, role: 'admin_teacher' })
      if (url.pathname.endsWith('/class-overview')) return json(route, { today_active: 2 })
      if (url.pathname.endsWith('/warning-list')) return json(route, { warnings: [
        { id: 101, student_id: 21, student_name: '林同学', risk_level: 'high', urgent: true, status: 'pending', reason: '出现明确安全求助表达', updated_at: '2026-08-24T09:30:00' },
        { id: 102, student_id: 22, student_name: '陈同学', risk_level: 'middle', urgent: false, status: 'pending', reason: '近期到校困难增多', updated_at: '2026-08-23T20:10:00' },
      ] })
      if (url.pathname.endsWith('/student-list')) return json(route, { students })
      if (url.pathname.endsWith('/lesson-plan/templates')) return json(route, { templates: [] })
      if (url.pathname.endsWith('/accounts')) return json(route, { accounts: [] })
      if (url.pathname.endsWith('/access-requests')) return json(route, { items: [
        { id: 301, request_code: 'REQ-301', status: 'pending', teacher_name: '王老师', student_name: '陈同学', reason: '近期持续缺课，需要制定线下支持安排' },
      ] })
      return json(route, {})
    })

    try {
      await page.goto(baseURL, { waitUntil: 'domcontentloaded', timeout: 15_000 })
      await page.waitForTimeout(800)
      await page.getByRole('heading', { name: '先处理最需要关注的事' }).waitFor({ timeout: 15_000 })
      assert.equal(await page.getByText('出现明确安全求助表达', { exact: true }).count(), 1)
      assert.equal(await page.getByText('当前队列状态', { exact: true }).count(), 1)
      assert.equal(await page.getByText('权限审批', { exact: true }).count(), 1)
      if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, '.codex-alpha3-teacher-desktop.png'), fullPage: true })

      await page.locator('.teacher-nav button').first().focus()
      assert.equal(await page.locator('.teacher-search input').evaluate(element => document.activeElement === element), false)
      await page.keyboard.press('Control+K')
      assert.equal(await page.locator('.teacher-search input').evaluate(element => document.activeElement === element), true)
      await page.locator('.teacher-search input').evaluate(element => element.blur())

      await page.setViewportSize({ width: 390, height: 844 })
      await page.waitForTimeout(250)
      assert.equal(await page.locator('.teacher-sidebar').isVisible(), true)
      assert.equal(await page.getByRole('heading', { name: '先处理最需要关注的事' }).isVisible(), true)
      if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, '.codex-alpha3-teacher-mobile.png'), fullPage: true })
      assert.deepEqual(pageErrors, [])
    } finally {
      await browser.close()
    }
  })
