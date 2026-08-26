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
      localStorage.clear()
      localStorage.setItem('shengyu_first_run_guide_completed_version', '4.3.0')
    })

    try {
      await page.goto(baseURL, { waitUntil: 'networkidle' })
      const splash = page.locator('.splash')
      if (await splash.isVisible().catch(() => false)) await splash.click()
      assert.equal(await page.locator('.island-game-host canvas').count(), 0)
      assert.equal(islandRequests.length, 0)

      const explore = page.getByRole('button', { name: '进入心岛探索' })
      for (let cycle = 0; cycle < 3; cycle += 1) {
        await explore.click()
        const dialog = page.getByRole('dialog', { name: '和咕团沿着光，选一件此刻想做的小事' })
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
      await page.getByRole('button', { name: /月光钓鱼湾/ }).click()
      assert.match(await page.locator('#island-live-status').textContent(), /正在前往月光钓鱼湾/)
      const fishingEntry = page.getByRole('button', { name: '坐到水边钓鱼' })
      await fishingEntry.waitFor({ state: 'visible', timeout: 20_000 })
      assert.equal(await fishingEntry.evaluate(element => document.activeElement === element), true)
      await fishingEntry.click()
      await page.getByRole('heading', { name: '慢钓台', exact: true }).waitFor({ state: 'visible' })
      assert.equal(await page.locator('.game-tabs').getByRole('button', { name: /慢钓台/ }).getAttribute('aria-current'), 'page')

      await page.getByRole('button', { name: /幸福交换/ }).click()
      const happinessInput = page.getByLabel('一件令你幸福的小事')
      await happinessInput.fill('今天放学时，风吹过树叶的声音很好听。')
      await page.getByRole('button', { name: '放进树洞并交换' }).click()
      await page.getByText('咕哝预写的幸福灵感卡 · 不是其他用户的实时分享', { exact: true }).waitFor({ state: 'visible' })
      assert.match(await page.locator('.happiness-book').textContent(), /风吹过树叶/)

      await happinessInput.fill('我刚刚吞了很多药')
      await page.getByRole('button', { name: '放进树洞并交换' }).click()
      await page.getByRole('heading', { name: '先确认你现在的安全' }).waitFor({ state: 'visible' })
      assert.equal(await happinessInput.inputValue(), '')
      assert.equal(await page.getByRole('link', { name: '拨打 12356' }).getAttribute('href'), 'tel:12356')
      assert.doesNotMatch(await page.locator('.happiness-book').textContent(), /吞了很多药/)

      await page.getByRole('button', { name: '进入心岛漫游' }).click()
      await page.locator('.island-game-host canvas').waitFor({ state: 'visible' })
      if (screenshotDir) {
        await page.screenshot({ path: path.join(screenshotDir, 'design-qa-prototype-final.jpg'), type: 'jpeg', quality: 92 })
      }

      await page.setViewportSize({ width: 390, height: 844 })
      await page.waitForTimeout(200)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
      assert.equal(await page.locator('.island-mobile-controls').evaluate(element => getComputedStyle(element).display), 'grid')
      assert.equal(await page.locator('.island-mobile-controls button').count(), 9)
      assert.equal(await page.getByRole('button', { name: '向右下移动' }).count(), 1)
      const up = page.getByRole('button', { name: '向上移动' })
      await up.dispatchEvent('pointerdown', { pointerId: 7, pointerType: 'touch', isPrimary: true })
      await page.waitForTimeout(120)
      await up.dispatchEvent('pointercancel', { pointerId: 7, pointerType: 'touch', isPrimary: true })

      if (screenshotDir) {
        await page.screenshot({ path: path.join(screenshotDir, 'design-qa-mobile.png') })
      }
      assert.deepEqual(errors, [])
    } finally {
      await browser.close()
    }
  })
