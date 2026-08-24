import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { chromium } from 'playwright-core'

const shouldRun = process.env.RUN_STUDENT_LEISURE_E2E === '1'
const baseURL = process.env.STUDENT_E2E_URL || 'http://127.0.0.1:5174/'
const edgePath = process.env.EDGE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const screenshotDir = process.env.STUDENT_E2E_SCREENSHOT_DIR || ''

test('student leisure hub supports desktop, mobile, keyboard and deterministic game progress',
  { skip: shouldRun ? false : 'set RUN_STUDENT_LEISURE_E2E=1 with the local frontend running' }, async () => {
    const browser = await chromium.launch({ executablePath: edgePath, headless: true })
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.addInitScript(() => {
      localStorage.setItem('shengyu_first_run_guide_completed_version', '4.3.0')
    })

    try {
      await page.goto(baseURL, { waitUntil: 'networkidle' })
      const splash = page.locator('.splash')
      if (await splash.isVisible().catch(() => false)) await splash.click()
      await page.getByRole('button', { name: '休闲' }).click()

      const hub = page.locator('.leisure-hub')
      await hub.waitFor({ state: 'visible' })
      assert.equal(await page.getByRole('heading', { name: '休闲陪伴 Agent' }).count(), 1)
      assert.equal(await page.getByText('等待你选择想要的节奏', { exact: true }).count(), 1)
      assert.equal(await page.locator('.leisure-close').evaluate(element => document.activeElement === element), true)

      await page.getByRole('button', { name: /找回掌控/ }).click()
      await page.getByRole('button', { name: '去试试' }).click()
      const firstPlot = page.locator('.garden-plot').first()
      await firstPlot.click()
      assert.equal(await firstPlot.getAttribute('aria-label'), '第1块田，浇水')
      assert.equal(await page.getByText('已记录“找回掌控”', { exact: true }).count(), 1)

      if (screenshotDir) {
        await page.screenshot({ path: path.join(screenshotDir, '.codex-alpha54-leisure-desktop.png') })
      }

      await page.setViewportSize({ width: 390, height: 844 })
      await page.waitForTimeout(200)
      const mobileBox = await hub.boundingBox()
      assert.ok(mobileBox.x >= 0)
      assert.ok(mobileBox.x + mobileBox.width <= 391)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
      if (screenshotDir) {
        await page.screenshot({ path: path.join(screenshotDir, '.codex-alpha54-leisure-mobile.png') })
      }

      await page.keyboard.press('Escape')
      await hub.waitFor({ state: 'detached' })
      assert.deepEqual(errors, [])
    } finally {
      await browser.close()
    }
  })

