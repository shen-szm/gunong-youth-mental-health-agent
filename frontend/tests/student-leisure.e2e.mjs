import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { chromium } from 'playwright-core'

const shouldRun = process.env.RUN_STUDENT_LEISURE_E2E === '1'
const baseURL = process.env.STUDENT_E2E_URL || 'http://127.0.0.1:5175/'
const edgePath = process.env.EDGE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const screenshotDir = process.env.STUDENT_E2E_SCREENSHOT_DIR || ''

test('heart island supports lazy loading, repeated lifecycle, keyboard focus and mobile controls',
  { skip: shouldRun ? false : 'set RUN_STUDENT_LEISURE_E2E=1 with the local frontend running' }, async () => {
    const browser = await chromium.launch({ executablePath: edgePath, headless: true })
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } })
    const page = await context.newPage()
    const errors = []
    const islandRequests = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', request => {
      if (/createIslandGame|phaser/i.test(request.url())) islandRequests.push(request.url())
    })
    await page.addInitScript(() => {
      localStorage.setItem('shengyu_first_run_guide_completed_version', '4.3.0')
    })

    try {
      await page.goto(baseURL, { waitUntil: 'networkidle' })
      const splash = page.locator('.splash')
      if (await splash.isVisible().catch(() => false)) await splash.click()
      assert.equal(await page.locator('.island-game-host canvas').count(), 0)
      assert.equal(islandRequests.length, 0)

      const explore = page.getByRole('button', { name: '探索', exact: true })
      for (let cycle = 0; cycle < 3; cycle += 1) {
        await explore.click()
        const dialog = page.getByRole('dialog', { name: '和咕团沿着光，选一件今晚想做的小事' })
        await dialog.waitFor({ state: 'visible' })
        await page.locator('.island-game-host canvas').waitFor({ state: 'visible' })
        assert.equal(await page.locator('.island-game-host canvas').count(), 1)
        await page.locator('.island-game-surface').press('Escape')
        await dialog.waitFor({ state: 'detached' })
        assert.equal(await page.locator('.island-game-host canvas').count(), 0)
        assert.equal(await explore.evaluate(element => document.activeElement === element), true)
      }
      assert.ok(islandRequests.length > 0)

      await explore.click()
      await page.locator('.island-game-host canvas').waitFor({ state: 'visible' })
      const surface = page.getByLabel('心岛地图控制区')
      await surface.press('ArrowRight')
      await surface.press('ArrowDown')
      await page.getByRole('button', { name: /云顶暖房/ }).click()
      assert.match(await page.locator('#island-live-status').textContent(), /正在前往云顶暖房/)

      await page.setViewportSize({ width: 390, height: 844 })
      await page.waitForTimeout(200)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
      assert.equal(await page.locator('.island-mobile-controls').evaluate(element => getComputedStyle(element).display), 'grid')
      const up = page.getByRole('button', { name: '向上移动' })
      await up.dispatchEvent('pointerdown', { pointerId: 7, pointerType: 'touch', isPrimary: true })
      await page.waitForTimeout(120)
      await up.dispatchEvent('pointercancel', { pointerId: 7, pointerType: 'touch', isPrimary: true })

      if (screenshotDir) {
        await page.screenshot({ path: path.join(screenshotDir, 'heart-island-e2e-mobile.png') })
      }
      assert.deepEqual(errors, [])
    } finally {
      await browser.close()
    }
  })
