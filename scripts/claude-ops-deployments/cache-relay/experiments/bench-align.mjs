#!/usr/bin/env node
// 性能基准：对比基线版与优化版在**真实请求路径**上的开销。
// 路径 = JSON.parse(raw) → alignRequest → JSON.stringify → Buffer.byteLength
// （与 serve() 里 step 1 完全一致；不含网络转发，那部分两者相同）
//
// 分三块输出：
//   ① 端到端路径对比（基线 vs 优化）
//   ② 阶段拆解（parse / align / stringify / byteLength）——判断 align 优化的天花板
//   ③ 单项微基准（readConfig / sortTools）
import { alignRequest as baseAlign, readConfig as baseCfg, sortTools as baseSort } from './cache-relay.baseline.mjs'
import { alignRequest as optAlign, readConfig as optCfg, sortTools as optSort } from '../cache-relay.mjs'
import { corpus } from './payloads.mjs'

const REPS = Number(process.env.BENCH_REPS ?? 25)
const WARM = 5

function stats(xs) {
  const s = [...xs].sort((a, b) => a - b)
  const q = (p) => s[Math.min(s.length - 1, Math.floor(p * s.length))]
  return { med: q(0.5), p95: q(0.95), min: s[0] }
}

function bench(fn, reps = REPS, warm = WARM) {
  for (let i = 0; i < warm; i++) fn()
  const ts = []
  for (let i = 0; i < reps; i++) {
    const t = process.hrtime.bigint()
    fn()
    ts.push(Number(process.hrtime.bigint() - t) / 1e6)
  }
  return stats(ts)
}

function pipeline(align, raw, provider) {
  const parsed = JSON.parse(raw)
  align(parsed, provider)
  const out = JSON.stringify(parsed)
  Buffer.byteLength(out, 'utf8')
  return out
}

const cases = corpus()

// ─────────────────────────── ① 端到端路径 ───────────────────────────
console.log(`① 端到端路径：parse → align → stringify → byteLength   (reps=${REPS})\n`)
console.log('用例'.padEnd(24) + '大小'.padEnd(10) + '基线'.padEnd(11) + '优化'.padEnd(11) + '提速'.padEnd(8) + '基线p95'.padEnd(12) + '优化p95')
console.log('-'.repeat(92))

let totBase = 0, totOpt = 0, totBytes = 0
const rows = []
for (const { name, provider, body } of cases) {
  const raw = JSON.stringify(body)
  const bytes = Buffer.byteLength(raw, 'utf8')
  const b = bench(() => pipeline(baseAlign, raw, provider))
  const o = bench(() => pipeline(optAlign, raw, provider))
  totBase += b.med; totOpt += o.med; totBytes += bytes
  rows.push({ name, provider, raw, bytes, b, o })
  console.log(
    name.padEnd(24) +
    ((bytes / 1024).toFixed(0) + 'KB').padEnd(10) +
    (b.med.toFixed(2) + 'ms').padEnd(11) +
    (o.med.toFixed(2) + 'ms').padEnd(11) +
    (b.med / o.med).toFixed(2) + '×' + ' '.repeat(3) +
    (b.p95.toFixed(2) + 'ms').padEnd(12) +
    o.p95.toFixed(2) + 'ms')
}
console.log('-'.repeat(92))
console.log('合计中位:  基线 ' + totBase.toFixed(2) + 'ms   优化 ' + totOpt.toFixed(2) + 'ms   →  ' + (totBase / totOpt).toFixed(2) + '×')
console.log('吞吐:      基线 ' + (totBytes / 1048576 / (totBase / 1000)).toFixed(1) + ' MB/s   优化 ' + (totBytes / 1048576 / (totOpt / 1000)).toFixed(1) + ' MB/s')

// ─────────────────────────── ② 阶段拆解 ───────────────────────────
console.log('\n② 阶段拆解（基线版，定位可优化空间）\n')
console.log('用例'.padEnd(16) + 'parse'.padEnd(10) + 'align'.padEnd(10) + 'stringify'.padEnd(11) + 'byteLen'.padEnd(9) + '合计'.padEnd(10) + 'align 占比')
console.log('-'.repeat(78))
const heavy = cases.filter((c) => ['main-full', 'main-heavy', 'classifier'].includes(c.name))
for (const { name, provider, body } of heavy) {
  const raw = JSON.stringify(body)
  const p = bench(() => JSON.parse(raw))
  const a = bench(() => baseAlign(JSON.parse(raw), provider))
  const s = bench(() => JSON.stringify(JSON.parse(raw)))
  const bl = bench(() => Buffer.byteLength(raw, 'utf8'))
  const sum = p.med + a.med + s.med
  console.log(
    name.padEnd(16) +
    (p.med.toFixed(2) + 'ms').padEnd(10) +
    (a.med.toFixed(2) + 'ms').padEnd(10) +
    (s.med.toFixed(2) + 'ms').padEnd(11) +
    (bl.med.toFixed(3) + 'ms').padEnd(9) +
    (sum.toFixed(2) + 'ms').padEnd(10) +
    (100 * a.med / sum).toFixed(0) + '%')
}
console.log('（parse/stringify/byteLen 不可动——上游拿到的字节必须一致；align 是可优化部分）')

// ─────────────────────────── ③ 微基准 ───────────────────────────
console.log('\n③ 微基准\n')
const cfgB = bench(() => baseCfg(), 2000, 50)
const cfgO = bench(() => optCfg(), 2000, 50)
console.log('  readConfig() ×2000:      基线 ' + cfgB.med.toFixed(4) + 'ms/次   优化 ' + cfgO.med.toFixed(4) + 'ms/次   (' + (cfgB.med / cfgO.med).toFixed(1) + '×)')

const tools = cases.find((c) => c.name === 'main-full').body.tools
const sortB = bench(() => baseSort({ tools: [...tools] }), 2000, 50)
const sortO = bench(() => optSort({ tools: [...tools] }), 2000, 50)
console.log('  sortTools(已序45) ×2000: 基线 ' + sortB.med.toFixed(4) + 'ms/次   优化 ' + sortO.med.toFixed(4) + 'ms/次   (' + (sortB.med / sortO.med).toFixed(1) + '×)')

const unsorted = cases.find((c) => c.name === 'main-unsorted-tools').body.tools
const sortBU = bench(() => baseSort({ tools: [...unsorted] }), 2000, 50)
const sortOU = bench(() => optSort({ tools: [...unsorted] }), 2000, 50)
console.log('  sortTools(乱序45) ×2000: 基线 ' + sortBU.med.toFixed(4) + 'ms/次   优化 ' + sortOU.med.toFixed(4) + 'ms/次   (' + (sortBU.med / sortOU.med).toFixed(1) + '×)')
