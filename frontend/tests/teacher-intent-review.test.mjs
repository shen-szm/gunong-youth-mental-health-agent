import test from 'node:test'
import assert from 'node:assert/strict'
import { localIntentReview } from '../src/utils/teacherIntentReview.js'

test('local review only displays known categories and never authorizes preparation', () => {
  const result = { source: 'local_policy', review_reason: 'risk_expression_requires_review', risk_categories: ['external_delivery', 'external_delivery', '<script>private</script>', '__proto__'], can_prepare: true }
  assert.deepEqual(localIntentReview(result), { labels: ['对外发送或公开'], canPrepare: false })
  assert.deepEqual(localIntentReview({ ...result, risk_categories: null }), { labels: [], canPrepare: false })
  assert.equal(localIntentReview({ ...result, source: 'model_extracted' }), null)
  assert.equal(localIntentReview(null), null)
})
