// 扰动分离模拟（sep-sim）：同 session 扰动 vs 分离两流（异 sid vs 同 sid）。
// 核心问题：把扰动流量从主流分离成独立流，能否消除对主流缓存的扰动？分离收益来自 sid 还是来自内容历史独立？
// 场景1 MIXED：单流共享前缀，早期共享块逐请求改写（唯一值，永不重复）→ 主请求每次只命中共享头（读量不增长）。
// 场景2 SEP-diff-sid：两流各自独立 system 前缀、不同 sid → 主请求读量随自身历史增长（全量命中）。
// 场景3 SEP-same-sid：同场景2 但两流同 sid → 若与场景2 逐字节相同 ⇒ 收益来自内容分离，与 sid 无关。
// 全部 flash，max_tokens=1；凭据读 settings.json env.ANTHROPIC_AUTH_TOKEN（不打印）。
import fs from 'node:fs'
import https from 'node:https'

const cfg = JSON.parse(fs.readFileSync('C:/Users/28064/.cache-relay/config.json', 'utf8'))
const upstream = cfg.defaultUpstream
let token = ''
for (const f of ['C:/Users/28064/.claude/settings.json', 'C:/Users/28064/.claude/settings.local.json']) {
  try { token = JSON.parse(fs.readFileSync(f, 'utf8'))?.env?.ANTHROPIC_AUTH_TOKEN ?? '' } catch {}
  if (token) break
}
if (!upstream || !token) { console.error('NO_CONFIG'); process.exit(1) }

const FLASH = 'deepseek-v4-flash'
const hostname = new URL(upstream).hostname
const WAIT = Number(process.env.SLEEP_MS ?? 90000)
let totalInputTokens = 0

// 内容构造
const S = 'SIM-SYS-' + 's'.repeat(2000)
const SM = 'SIM-MAIN-SYS-' + 'm'.repeat(2000)
const SC = 'SIM-CLS-SYS-' + 'c'.repeat(2000)
const block = (v) => `SIM-BLOCK-v${v}-` + (String(v) + 'b').repeat(800)
const mainT = (i) => `SIM-MAIN-T${i}-` + 'm'.repeat(1600)
const clsT = (i) => `SIM-CLS-T${i}-` + 'c'.repeat(1600)
const U = (c) => ({ role: 'user', content: c })
const A = () => ({ role: 'assistant', content: 'OK' })

function ask(sys, turns, sid) {
  return new Promise((resolve, reject) => {
    const u = new URL(upstream + '/v1/messages')
    const body = JSON.stringify({ model: FLASH, max_tokens: 1, messages: [{ role: 'system', content: sys }, ...turns] })
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

const read = (u) => Number(u?.cache_read_input_tokens ?? u?.prompt_cache_hit_tokens ?? 0)
const fmt = (r) => `${r.status} in=${r.usage?.input_tokens} read=${read(r.usage)} ratio=${r.usage ? Math.round((read(r.usage) / r.usage.input_tokens) * 100) : 0}%${r.err ? ' err=' + r.err : ''}`

const sleep = ms => new Promise(r => setTimeout(r, ms))
;(async () => {
  console.log(`host=${hostname} model=${FLASH} wait=${WAIT / 1000}s t0=${new Date().toISOString()}`)

  // 场景定义
  const mixed = {
    tag: 'MIXED', sid: 'mixed-sid',
    seq: [
      { name: 'M1 主turn1', sys: S + block(1), turns: [U(mainT(1))] },
      { name: 'P1 扰动', sys: S + block(2), turns: [U(mainT(1))] },
      { name: 'M2 主turn2', sys: S + block(3), turns: [U(mainT(1)), A(), U(mainT(2))] },
      { name: 'P2 扰动', sys: S + block(4), turns: [U(mainT(1)), A(), U(mainT(2))] },
      { name: 'M3 主turn3', sys: S + block(5), turns: [U(mainT(1)), A(), U(mainT(2)), A(), U(mainT(3))] },
    ],
  }
  const sep = (sidPair) => ({
    tag: sidPair.tag, mainSid: sidPair.mainSid, clsSid: sidPair.clsSid,
    seq: [
      { name: 'M1 主turn1', sys: SM, turns: [U(mainT(1))], sid: sidPair.mainSid },
      { name: 'C1 分turn1', sys: SC, turns: [U(clsT(1))], sid: sidPair.clsSid },
      { name: 'M2 主turn2', sys: SM, turns: [U(mainT(1)), A(), U(mainT(2))], sid: sidPair.mainSid },
      { name: 'C2 分turn2', sys: SC, turns: [U(clsT(1)), A(), U(clsT(2))], sid: sidPair.clsSid },
      { name: 'M3 主turn3', sys: SM, turns: [U(mainT(1)), A(), U(mainT(2)), A(), U(mainT(3))], sid: sidPair.mainSid },
    ],
  })
  const scenarios = [
    mixed,
    sep({ tag: 'SEP异sid', mainSid: 'sim-main-sid', clsSid: 'sim-cls-sid' }),
    sep({ tag: 'SEP同sid', mainSid: 'sim-shared-sid', clsSid: 'sim-shared-sid' }),
  ]

  // 阶段 W：各场景首请求预热（流水线）
  console.log('--- 阶段 W：预热 ---')
  for (const sc of scenarios) {
    const w = await ask(sc.seq[0].sys, sc.seq[0].turns, sc.sid ?? sc.seq[0].sid)
    sc.warm = w
    console.log(`${sc.tag.padEnd(9)} ${sc.seq[0].name.padEnd(10)} ${fmt(w)}`)
  }
  console.log(`等待 ${WAIT / 1000}s（异步写缓存）…`)
  await sleep(WAIT)

  // 阶段 T：顺序执行剩余请求
  console.log('--- 阶段 T：测试 ---')
  for (const sc of scenarios) {
    console.log(`  == ${sc.tag} ==`)
    let retried = false
    for (let i = 1; i < sc.seq.length; i++) {
      const s = sc.seq[i]
      let r = await ask(s.sys, s.turns, sc.sid ?? s.sid)
      // 就绪检查：首个后续请求 read=0 → 缓存未就绪，等 60s 重试一次
      if (i === 1 && read(r.usage) === 0 && !retried) {
        await sleep(60000)
        r = await ask(s.sys, s.turns, sc.sid ?? s.sid)
        retried = true
      }
      console.log(`    ${s.name.padEnd(10)} ${fmt(r)}`)
    }
  }

  console.log('')
  console.log('=== 汇总（主流 M2/M3 读量对比）===')
  console.log(`MIXED:    主流 read 保持≈共享头长度（不增长）→ 扰动持续破坏前缀`)
  console.log(`SEP异sid: 主流 read 随自身历史增长（M2≈前缀全量、M3 更大）→ 无扰动`)
  console.log(`SEP同sid: 与 SEP异sid 逐字节相同 ⇒ 收益来自内容分离，sid 无关`)
  console.log(`总输入token: ${totalInputTokens}`)
  console.log('DONE')
})().catch(e => { console.error('FAIL:', e.message); process.exit(1) })
