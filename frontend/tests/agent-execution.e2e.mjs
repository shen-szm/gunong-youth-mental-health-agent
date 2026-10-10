import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { chromium } from 'playwright-core'

const baseURL = process.env.AGENT_E2E_URL || 'http://127.0.0.1:5174/'
test('real agent plan supports node inspection, keyboard replay and urgent handoff', {
  skip: process.env.RUN_AGENT_E2E !== '1', timeout: 120000,
}, async () => {
  const browser = await chromium.launch({ executablePath: process.env.EDGE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', headless: true })
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' })
    const registration = await context.request.post(new URL('/api/user/register', baseURL).href, {
      data: { username: `agent_visual_${Date.now()}`, password: 'VisualTest_Only_34!', nickname: '小岛访客' },
    })
    assert.ok(registration.ok())
    const user = await registration.json()
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.addInitScript(userId => localStorage.setItem(`shengyu_first_run_guide_completed_version:${userId}`, '4.3.0'), user.user_id)
    await page.goto(new URL('/room', baseURL).href, { waitUntil: 'networkidle' })
    const splash = page.locator('.splash')
    if (await splash.isVisible().catch(() => false)) await splash.click()
    assert.equal(await page.locator('#student-agent-rail').count(), 0)
    await page.locator('.zone-monitor').focus()
    await page.keyboard.press('Enter')
    await page.locator('.room-action-bar').waitFor({ state: 'visible' })
    await page.keyboard.press('Enter')
    const panel = page.locator('.chat-panel')
    await panel.waitFor({ state: 'visible' })
    const sent = page.waitForResponse(response => response.url().includes('/api/chat/send') && response.request().method() === 'POST')
    await panel.locator('.input-wrap input').fill('最近考试让我很焦虑，睡眠也受到影响，我想理清今晚的准备。')
    await panel.locator('.send-btn').click()
    const run = (await (await sent).json()).agent_run
    assert.ok(run.plan.length > 3)
    await panel.getByRole('button', { name: '关闭倾诉面板' }).click()
    await page.locator('.student-agent-toggle').click()
    await page.getByRole('button', { name: '查看执行图与工具记录' }).click()
    await page.locator('.execution-node').first().waitFor()
    assert.equal(await page.locator('.execution-node').count(), run.plan.length)
    await page.getByRole('button', { name: '生成回应：完成', exact: true }).click()
    assert.ok((await page.locator('.execution-inspector').innerText()).includes('实际工具'))
    const slider = page.getByRole('slider')
    await slider.focus()
    await slider.press('Home')
    assert.equal(await page.locator('.execution-node.is-completed').count(), 0)
    assert.ok((await page.locator('.execution-inspector').innerText()).includes('尚无'))
    await page.getByRole('button', { name: '返回最新' }).click()
    assert.equal(await page.locator('.execution-node.is-completed').count(), run.events.filter(event => event.status === 'completed').length)
    await page.getByRole('button', { name: '生成回应：完成', exact: true }).click()
    await page.waitForTimeout(350)
    if (process.env.AGENT_E2E_SCREENSHOTS) await page.screenshot({ path: path.resolve(process.env.AGENT_E2E_SCREENSHOTS, '.codex-alpha34-agent-execution-desktop.png') })
    await page.setViewportSize({ width: 390, height: 844 })
    await page.waitForFunction(() => !document.querySelector('.execution-view'))
    assert.equal(await page.locator('.agent-graph-toggle').count(), 0)
    await page.setViewportSize({ width: 1440, height: 1000 })
    // Reload verifies restoration from the authenticated latest-run endpoint.
    await page.reload({ waitUntil: 'networkidle' })
    if (await splash.isVisible().catch(() => false)) await splash.click()
    await page.locator('.student-agent-toggle').click()
    await page.getByRole('button', { name: '查看执行图与工具记录' }).click()
    await page.locator('.execution-node').first().waitFor()
    assert.equal(await page.locator('.execution-node').count(), run.plan.length)

    // Local test identity only: create a crisis turn, then inspect the restored path.
    const session = await context.request.post(new URL('/api/chat/sessions', baseURL).href, { data: { force_new: true } })
    const urgentResponse = await context.request.post(new URL('/api/chat/send', baseURL).href, {
      data: { session_id: (await session.json()).session_id, message: '我现在想伤害自己' },
    })
    assert.ok(urgentResponse.ok())
    await page.reload({ waitUntil: 'networkidle' })
    if (await splash.isVisible().catch(() => false)) await splash.click()
    await page.locator('.student-agent-toggle').click()
    await page.getByRole('button', { name: '查看执行图与工具记录' }).click()
    await page.locator('.execution-node').first().waitFor()
    assert.equal(await page.locator('.execution-node').count(), 3)
    assert.equal(await page.getByRole('button', { name: /生成回应：/ }).count(), 0)
    assert.ok((await page.locator('.execution-notice').innerText()).includes('真人'))
    if (process.env.AGENT_E2E_SCREENSHOTS) await page.screenshot({ path: path.resolve(process.env.AGENT_E2E_SCREENSHOTS, '.codex-alpha34-agent-urgent-desktop.png') })
    assert.deepEqual(errors, [])
  } finally { await browser.close() }
})
