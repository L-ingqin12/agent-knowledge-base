// 多轮对照实验（v3）：核心问题「同体异 sid 缓存是否复用」多轮重复，降低单次随机干扰。
// 轮次上限：flash 6 轮 + pro 1 轮（成本受控，pro 按 ~4x 计价故只 1 轮）；另 1 组扰动体对照。
// 每轮 = 预热(唯一内容 + 唯一 sid Xi) → 统一等待 → 异sid测试(Yi) → 同sid对照(Xi)。
// 流水线：所有预热先发，一次等待后统一测试（省时）；无效轮（同sid MISS=缓存未就绪）重试一次。
// 判读：同sid HIT 且 异sid HIT ⇒ sid 不参与缓存键；
//       同sid HIT 且 异sid MISS ⇒ sid 参与缓存键；同sid MISS ⇒ 该轮无效。
// 凭据读 settings.json env.ANTHROPIC_AUTH_TOKEN（与真实链路同源），一律不打印。
import fs from 'node:fs'
import https from 'node:https'

const cfg = JSON.parse(fs.readFileSync('C:/Users/28064/.cache-relay/config.json', 'utf8'))
const upstream = cfg.defaultUpstream
let token = ''
for (const f of ['C:/Users/28064/.claude/settings.json', 'C:/Users/28064/.claude/settings.local.json']) {
  try { token = JSON.parse(fs.readFileSync(f, 'utf8'))?.env?.ANTHROPIC_AUTH_TOKEN ?? '' } catch {}
  if (token) break
}
if (!upstream) { console.error('NO_UPSTREAM'); process.exit(1) }
if (!token) { console.error('NO_TOKEN'); process.exit(1) }

const FLASH = 'deepseek-v4-flash'
let PRO = 'deepseek-v4-pro[1m]'
try {
  const rows = fs.readFileSync('C:/Users/28064/.cache-relay/dump.jsonl', 'utf8').trim().split('\n').filter(Boolean)
    .map(l => { try { return JSON.parse(l) } catch { return null } }).filter(Boolean)
  const main = [...rows].reverse().find(r => (r.tools || []).length > 0)
  if (main?.model) PRO = main.model
} catch {}

const hostname = new URL(upstream).hostname
const ROUNDS = [
  ...Array.from({ length: 6 }, (_, i) => ({ model: FLASH, tag: `R${i + 1}`, prefix: `ROUND-${i + 1}-` + 'x'.repeat(20000) })),
  { model: PRO, tag: 'R7(pro)', prefix: 'ROUND-7-PRO-' + 'z'.repeat(20000) },
]
const PERTURB_PREFIX = 'ROUND-1-PERTURB-' + 'x'.repeat(20000) // 与 R1 前缀从首字节起不同
const WAIT = Number(process.env.SLEEP_MS ?? 90000)
let totalInputTokens = 0

function ask(model, sid, prefix) {
  return new Promise((resolve, reject) => {
    const u = new URL(upstream + '/v1/messages')
    const body = JSON.stringify({ model, max_tokens: 8, messages: [{ role: 'user', content: prefix + '\n\nReply with exactly: OK' }] })
    const headers = {
      'content-type': 'application/json',
      'authorization': '[已脱敏] ' + token,
      'anthropic-version': '2023-06-01',
      ...(sid === null ? {} : { 'x-claude-code-session-id': sid }),
    }
    const req = https.request({ host: u.hostname, path: u.pathname, method: 'POST', timeout: 120000, headers }, res => {
      let raw = ''
      res.on('data', c => { raw += c })
      res.on('end', () => {
        let j = null
        try { j = JSON.parse(raw) } catch {}
        totalInputTokens += Number(j?.usage?.input_tokens ?? 0)
        resolve({ status: res.statusCode, usage: j?.usage ?? null, err: res.statusCode >= 400 ? String(j?.error?.message ?? raw).slice(0, 100) : null })
      })
    })
    req.on('timeout', () => req.destroy(new Error('timeout')))
    req.on('error', e => reject(e))
    req.end(body)
  })
}

function cacheRead(u) { return Number(u?.cache_read_input_tokens ?? u?.prompt_cache_hit_tokens ?? 0) }
const hit = u => cacheRead(u) > 0

const sleep = ms => new Promise(r => setTimeout(r, ms))
const short = (u) => u ? `in=${u.input_tokens} read=${cacheRead(u)}` : 'no-usage'

;(async () => {
  console.log(`host=${hostname} flash=${FLASH} pro=${PRO} rounds=${ROUNDS.length} wait=${WAIT / 1000}s t0=${new Date().toISOString()}`)
  // 阶段 W：全部预热（流水线）
  console.log('--- 阶段 W：预热（每轮唯一内容 + sid Xi）---')
  for (const [i, r] of ROUNDS.entries()) {
    const w = await ask(r.model, `round-${i + 1}-X`, r.prefix)
    console.log(`${r.tag.padEnd(9)} warm sid=X${i + 1}   status=${w.status} ${short(w.usage)}${w.err ? ' err=' + w.err : ''}`)
  }
  console.log(`等待 ${WAIT / 1000}s（异步写缓存）…`)
  await sleep(WAIT)
  // 阶段 T：统一测试（异sid + 同sid 对照）
  console.log('--- 阶段 T：异sid测试 + 同sid对照 ---')
  const results = []
  for (const [i, r] of ROUNDS.entries()) {
    const t = await ask(r.model, `round-${i + 1}-Y`, r.prefix)
    const c = await ask(r.model, `round-${i + 1}-X`, r.prefix)
    results.push({ round: r, test: t, ctrl: c })
    const verdict = !hit(c.usage) ? '无效(缓存未就绪)' : hit(t.usage) ? 'sid无关' : 'sid参与!'
    console.log(`${r.tag.padEnd(9)} 异sid=Y${i + 1} ${hit(t.usage) ? 'HIT ' : 'MISS'} ${short(t.usage)} | 同sid=X${i + 1} ${hit(c.usage) ? 'HIT ' : 'MISS'} ${short(c.usage)} | ${verdict}`)
  }
  // 阶段 R：无效轮重试一次（缓存就绪晚到）
  for (const res of results) {
    if (hit(res.ctrl.usage)) continue
    const i = ROUNDS.indexOf(res.round)
    await sleep(60000)
    const t = await ask(res.round.model, `round-${i + 1}-Y`, res.round.prefix)
    const c = await ask(res.round.model, `round-${i + 1}-X`, res.round.prefix)
    res.test = t; res.ctrl = c
    const verdict = !hit(c.usage) ? '仍无效(缓存未就绪)' : hit(t.usage) ? 'sid无关' : 'sid参与!'
    console.log(`${res.round.tag.padEnd(9)} 重试 异sid ${hit(t.usage) ? 'HIT ' : 'MISS'} ${short(t.usage)} | 同sid ${hit(c.usage) ? 'HIT ' : 'MISS'} ${short(c.usage)} | ${verdict}`)
  }
  // 阶段 P：扰动体对照（应 MISS，验证计量有效）
  const p = await ask(FLASH, 'round-1-X', PERTURB_PREFIX)
  console.log(`${'扰动体'.padEnd(9)} 同sid=X1  ${hit(p.usage) ? 'HIT(意外)' : 'MISS(符合内容敏感预期)'} ${short(p.usage)}`)
  // 汇总
  const valid = results.filter(r => hit(r.ctrl.usage))
  const diffSidHits = valid.filter(r => hit(r.test.usage)).length
  const sidPartitions = valid.filter(r => !hit(r.test.usage)).length
  console.log('')
  console.log('=== 汇总 ===')
  console.log(`有效轮: ${valid.length}/${results.length} | 异sid命中: ${diffSidHits} | 异sid未命中: ${sidPartitions}`)
  console.log(`扰动体: ${hit(p.usage) ? '意外命中' : '正确未命中'} | 总输入token: ${totalInputTokens}`)
  console.log('DONE')
})().catch(e => { console.error('FAIL:', e.message); process.exit(1) })
