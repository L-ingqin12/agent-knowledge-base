#!/usr/bin/env node
// 步骤剖析：alignRequest 内部每一步耗时，基线 vs 优化并排。
// 方法：预生成 N 份克隆（克隆开销不计入），对每一步在干净克隆上计时，取中位。
import * as B from './cache-relay.baseline.mjs'
import * as O from '../cache-relay.mjs'
import { corpus } from './payloads.mjs'

const N = Number(process.env.PROBE_N ?? 120)
const CASES = ['main-full', 'main-heavy', 'main-bare']

function timeIt(fn) {
  const t = process.hrtime.bigint()
  fn()
  return Number(process.hrtime.bigint() - t) / 1e6
}

/** 在干净克隆上反复计时某一步，返回中位毫秒。 */
function median(fn, clones) {
  for (let i = 0; i < 10; i++) fn(clones[i])           // 预热
  const ts = []
  for (let i = 0; i < N; i++) ts.push(timeIt(() => fn(clones[i % clones.length])))
  ts.sort((a, b) => a - b)
  return ts[Math.floor(ts.length / 2)]
}

const SAME = [
  ['stripCacheControl', (m) => (b) => m.stripCacheControl(b)],
  ['sortTools', (m) => (b) => m.sortTools(b)],
  ['relocateVolatile', (m) => (b) => m.relocateVolatile(b)],
]
const REPLACED = [
  ['稳定化(日期+token)', 'stabilizeDates+stabilizeTokens', 'stabilizeVolatileText'],
]
// 总时长：必须带上 provider，否则会走 default 分支（只排序），测出来是假的
const TOTAL = [['alignRequest(总)', (m, provider) => (b) => m.alignRequest(b, provider)]]

for (const name of CASES) {
  const { body, provider } = corpus().find((c) => c.name === name)
  const raw = JSON.stringify(body)
  const clones = Array.from({ length: 32 }, () => JSON.parse(raw))
  console.log(`\n${name}  (${(Buffer.byteLength(raw) / 1024).toFixed(0)}KB, provider=${provider})`)
  console.log('  步骤'.padEnd(26) + '基线'.padEnd(12) + '优化'.padEnd(12) + '提速')
  console.log('  ' + '-'.repeat(58))

  for (const [label, mk] of SAME) {
    const b = median(mk(B), clones)
    const o = median(mk(O), clones)
    console.log('  ' + label.padEnd(24) + (b.toFixed(3) + 'ms').padEnd(12) + (o.toFixed(3) + 'ms').padEnd(12) + (b / o).toFixed(2) + '×')
  }
  // 被合并替换的那一步：基线的两次 map 合起来 vs 优化的一次遍历
  const baseTwo = median((b) => { B.stabilizeDates(b); B.stabilizeTokens(b) }, clones)
  const optOne = median((b) => { O.stabilizeVolatileText(b) }, clones)
  console.log('  ' + '稳定化(日期+token)'.padEnd(24) + (baseTwo.toFixed(3) + 'ms').padEnd(12) + (optOne.toFixed(3) + 'ms').padEnd(12) + (baseTwo / optOne).toFixed(2) + '×')

  for (const [label, mk] of TOTAL) {
    const b = median(mk(B, provider), clones)
    const o = median(mk(O, provider), clones)
    console.log('  ' + label.padEnd(24) + (b.toFixed(3) + 'ms').padEnd(12) + (o.toFixed(3) + 'ms').padEnd(12) + (b / o).toFixed(2) + '×')
  }
}
console.log('\n注：每步在独立干净克隆上计时（不含克隆开销）；N=' + N + ' 取中位。')
