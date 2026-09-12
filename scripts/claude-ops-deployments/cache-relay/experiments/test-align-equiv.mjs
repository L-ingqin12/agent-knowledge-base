#!/usr/bin/env node
// 等价性测试：优化版与基线版对同一批 payload 的对齐结果必须**逐字节一致**。
// 判据（与 serve() 里的真实链路一致）：
//   raw JSON 串 → JSON.parse → alignRequest → JSON.stringify
// 两者产物字符串相同 = 发往上游的字节相同 = 缓存前缀行为不变。
//
// 额外断言缓存优化策略与 session id 分离的关键行为未被改动：
//   - tools 排序结果一致（且对已排序输入是幂等的）
//   - 分类器判定一致（0 tools + security monitor）
//   - 日期稳定化 / token 计数钉桩 / cache_control 剥离 结果一致
import { alignRequest as baseAlign, isClassifierRequest as baseIsCls, detectProvider as baseDetect } from './cache-relay.baseline.mjs'
import { alignRequest as optAlign, isClassifierRequest as optIsCls, detectProvider as optDetect } from '../cache-relay.mjs'
import { corpus, clone, sha } from './payloads.mjs'

let pass = 0
const fails = []
const t0 = Date.now()

for (const { name, provider, body } of corpus()) {
  const raw = JSON.stringify(body)

  // --- 对齐产物逐字节对比 ---
  let bOut, oOut
  try { bOut = JSON.stringify(baseAlign(JSON.parse(raw), provider)) } catch (e) { bOut = 'THROW:' + e.message }
  try { oOut = JSON.stringify(optAlign(JSON.parse(raw), provider)) } catch (e) { oOut = 'THROW:' + e.message }

  if (bOut === oOut) pass++
  else {
    // 定位第一处差异，便于排查
    let i = 0
    while (i < Math.min(bOut.length, oOut.length) && bOut[i] === oOut[i]) i++
    fails.push({
      name, provider, kind: '对齐产物不一致',
      at: i,
      base: bOut.slice(Math.max(0, i - 60), i + 60),
      opt: oOut.slice(Math.max(0, i - 60), i + 60),
      baseSha: sha(bOut), optSha: sha(oOut),
    })
  }

  // --- 快速预筛路径一致：带 raw 提示 vs 不带，产物必须逐字节相同 ---
  // （优化版用原文串预筛「要不要做整树 cache_control 剥离」，判据是必要条件；这里验证它没有漏判）
  let oHint
  try { oHint = JSON.stringify(optAlign(JSON.parse(raw), provider, raw)) } catch (e) { oHint = 'THROW:' + e.message }
  if (oHint === oOut) pass++
  else fails.push({ name, provider, kind: 'raw 预筛路径与全量路径不一致', base: oOut.slice(0, 160), opt: oHint.slice(0, 160) })

  // --- 对抗性：声明「原文不含 cache_control」时仍必须真的不含，否则预筛会漏剥 ---
  if (!raw.includes('cache_control') && oOut !== undefined) {
    const hasCctl = oHint.includes('cache_control')
    if (!hasCctl) pass++
    else fails.push({ name, provider, kind: '预筛漏判：原文无 cache_control 字面量，产物却含该键' })
  }

  // --- 分类器判定一致 ---
  const bc = baseIsCls(JSON.parse(raw)), oc = optIsCls(JSON.parse(raw))
  if (bc === oc) pass++
  else fails.push({ name, provider, kind: '分类器判定不一致', base: String(bc), opt: String(oc) })

  // --- 判源一致 ---
  const bd = baseDetect('https://api.deepseek.com/anthropic', body.model, '/v1/messages')
  const od = optDetect('https://api.deepseek.com/anthropic', body.model, '/v1/messages')
  if (bd === od) pass++
  else fails.push({ name, provider, kind: '判源不一致', base: bd, opt: od })
}

// --- 幂等性：对已对齐的产物再对齐一次，结果必须不变（保证每轮前缀稳定）---
for (const { name, provider, body } of corpus()) {
  const once = optAlign(JSON.parse(JSON.stringify(body)), provider)
  const twice = optAlign(JSON.parse(JSON.stringify(once)), provider)
  if (JSON.stringify(once) === JSON.stringify(twice)) pass++
  else fails.push({ name, provider, kind: '对齐不幂等（二次对齐产物变化）' })
}

const n = corpus().length
console.log(`用例 ${n} 组 × 3 项断言 + ${n} 项幂等 = ${pass + fails.length} 项`)
console.log(`通过 ${pass}  失败 ${fails.length}  (${Date.now() - t0}ms)`)
if (fails.length) {
  console.log('\n失败明细:')
  for (const f of fails.slice(0, 10)) console.log('  -', JSON.stringify(f, null, 1))
  process.exit(1)
}
console.log('✓ 对齐产物逐字节一致，缓存前缀行为与 session 分离逻辑不变')
