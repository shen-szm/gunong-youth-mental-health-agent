import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { chromium } from 'playwright-core'

const shouldRun = process.env.RUN_STUDENT_E2E === '1'
const baseURL = process.env.STUDENT_E2E_URL || 'http://127.0.0.1:5174/'
const edgePath = process.env.EDGE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const screenshotDir = process.env.STUDENT_E2E_SCREENSHOT_DIR || ''

test('student summary browser flow keeps chat open, confirms ending, restores context and deletes privately',
  { skip: shouldRun ? false : 'set RUN_STUDENT_E2E=1 with local frontend/backend running' }, async () => {
    const browser = await chromium.launch({ executablePath: edgePath, headless: true })
    const context = await browser.newContext({ viewport: { width: 1280, height: 820 } })
    const page = await context.newPage()
    const pageErrors = []
    page.on('pageerror', error => pageErrors.push(error.message))
    page.on('dialog', dialog => dialog.accept())
    await page.addInitScript(() => {
      localStorage.setItem('shengyu_first_run_guide_completed_version', '4.3.0')
    })

    try {
      await page.goto(baseURL, { waitUntil: 'networkidle' })
      const splash = page.locator('.splash')
      if (await splash.isVisible().catch(() => false)) await splash.click()
      await page.waitForFunction(() => Boolean(localStorage.getItem('shengyu_user_id')))
      await page.evaluate(async () => {
        const latest = await fetch('/api/chat/sessions/latest-summary').then(response => response.json())
        if (latest.status === 'ready' && latest.session_id) {
          await fetch(`/api/chat/sessions/${latest.session_id}/summary`, { method: 'DELETE' })
        }
        await fetch('/api/chat/sessions', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ force_new: true })
        })
      })
      await page.reload({ waitUntil: 'networkidle' })
      if (await splash.isVisible().catch(() => false)) {
        await splash.click()
        await splash.waitFor({ state: 'detached' })
      }
      const agentToggle = page.locator('.student-agent-toggle')
      await agentToggle.waitFor({ state: 'visible' })
      assert.equal(await agentToggle.getAttribute('aria-label'), '展开咕哝智能体进度')
      await agentToggle.click()
      assert.equal(await agentToggle.getAttribute('aria-label'), '收起咕哝智能体进度')
      const agentRail = page.locator('#student-agent-rail')
      await agentRail.waitFor({ state: 'visible' })
      assert.equal(await agentRail.getByText('安全优先分流').count(), 1)
      await page.waitForTimeout(250)
      if (screenshotDir) {
        await page.screenshot({ path: path.join(screenshotDir, '.codex-alpha51-room-desktop.png') })
        await page.setViewportSize({ width: 390, height: 844 })
        await page.waitForTimeout(250)
        await page.screenshot({ path: path.join(screenshotDir, '.codex-alpha51-room-mobile.png') })
        await page.setViewportSize({ width: 1280, height: 820 })
        await page.waitForTimeout(250)
      }
      await agentRail.getByRole('button', { name: '收起智能体进度' }).click()
      await page.locator('.zone-monitor').click()
      const panel = page.locator('.chat-panel')
      await panel.waitFor({ state: 'visible' })

      const input = panel.locator('.input-wrap input')
      const sendAndWait = async message => {
        const previousReplies = await panel.locator('.msg-row.assistant').count()
        await input.fill(message)
        await panel.locator('.send-btn').click()
        await page.waitForFunction(expected => document.querySelectorAll('.chat-panel .msg-row.assistant').length > expected, previousReplies)
      }

      await sendAndWait('考试让我很焦虑，最近也总睡不着')
      assert.equal(await panel.isVisible(), true)
      assert.equal(await page.locator('.student-summary-orb').count(), 0)

      await sendAndWait('谢谢你，但我还想继续说')
      assert.equal(await page.locator('.chat-end-confirm').count(), 0)

      await sendAndWait('谢谢你')
      const confirmation = page.locator('.chat-end-confirm')
      await confirmation.waitFor({ state: 'visible' })
      await confirmation.getByRole('button', { name: '继续聊' }).click()
      assert.equal(await confirmation.count(), 0)
      assert.equal(await input.evaluate(element => document.activeElement === element), true)

      await panel.getByRole('button', { name: '结束本次倾诉' }).click()
      const oldUserMessageCount = await page.locator('.chat-panel .msg-row.user').count()
      const originalMessage = page.getByText('考试让我很焦虑，最近也总睡不着', { exact: true })
      assert.equal(await originalMessage.count(), 1)
      await confirmation.getByRole('button', { name: '生成小结' }).click()
      const orb = page.locator('.student-summary-orb:not(:disabled)')
      await orb.waitFor({ state: 'visible' })
      await panel.waitFor({ state: 'hidden' })
      assert.equal(await panel.isVisible(), false)

      await orb.click()
      const drawer = page.locator('.student-support-drawer')
      await drawer.waitFor({ state: 'visible' })
      await agentRail.waitFor({ state: 'detached' })
      assert.equal(await page.evaluate(() => window.scrollY), 0)
      await drawer.getByText('不是心理诊断或量表结果', { exact: false }).waitFor()
      if (screenshotDir) {
        await page.waitForTimeout(250)
        await page.screenshot({ path: path.join(screenshotDir, '.codex-alpha51-summary-desktop.png') })
        await page.setViewportSize({ width: 390, height: 844 })
        await page.waitForTimeout(250)
        await page.screenshot({ path: path.join(screenshotDir, '.codex-alpha51-summary-mobile.png') })
        await page.setViewportSize({ width: 1280, height: 820 })
        await page.waitForTimeout(250)
      }
      await drawer.getByRole('button', { name: '继续倾诉' }).first().click()
      await panel.waitFor({ state: 'visible' })
      assert.equal(await page.locator('.chat-panel .msg-row.user').count(), oldUserMessageCount)
      assert.equal(await originalMessage.count(), 1)

      await orb.click()
      await drawer.getByRole('button', { name: '开始新话题' }).click()
      await panel.waitFor({ state: 'visible' })
      await page.waitForFunction(() => document.querySelectorAll('.chat-panel .msg-row.user').length === 0)
      assert.equal(await page.locator('.chat-panel .msg-row.user').count(), 0)

      await page.getByLabel('关闭倾诉面板').click()
      await orb.click()
      await drawer.getByRole('button', { name: '删除本次小结' }).click()
      await orb.waitFor({ state: 'detached' })
      assert.equal(await page.locator('.bottom-nav button').first().evaluate(element => document.activeElement === element), true)
      assert.deepEqual(pageErrors, [])
    } finally {
      await browser.close()
    }
  })
