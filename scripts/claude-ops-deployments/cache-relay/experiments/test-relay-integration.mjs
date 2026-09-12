#!/usr/bin/env node
// 集成测试：真起一个假上游 + 真起中继子进程，走完整 HTTP 链路。
// 覆盖纯函数测试覆盖不到的部分（本轮改动的 serve/forward）：
//   ① 主会话请求被对齐（日期钉桩/token 钉桩/剥 cache_control/工具排序）
//   ② 分类器请求：model 重映射 + session-id 后缀（会话桶分离必须不变）
//   ③ 上游连接复用（keep-alive）
//   ④ 客户端断连 → 上游请求被销毁（省 token）
//   ⑤ 热改 config.json 免重启生效（含 dump 开关）
//   ⑥ 内容审核 400 → 备用上游兜底
import http from 'node:http'
import { spawn, execFileSync } from 'node:child_process'
import { mkdtempSync, writeFileSync, readFileSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const RELAY = join(HERE, '..', 'cache-relay.mjs')
const NODE = process.execPath

let pass = 0
const fails = []
const ok = (cond, label, detail = '') => {
  if (cond) { pass++; console.log(`  ✓ ${label}`) }
  else { fails.push(label + (detail ? ` — ${detail}` : '')); console.log(`  ✗ ${label}${detail ? ' — ' + detail : ''}`) }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// ── 假上游 ────────────────────────────────────────────────────────────
function startUpstream({ delayMs = 0, status = 200, body = null, risk400 = false } = {}) {
  const seen = { reqs: [], sockets: new Set(), abortedEarly: 0, finished: 0 }
  const srv = http.createServer(async (req, res) => {
    seen.sockets.add(req.socket)
    const chunks = []
    for await (const c of req) chunks.push(c)
    const raw = Buffer.concat(chunks).toString('utf8')
    let parsed = null
    try { parsed = JSON.parse(raw) } catch { /* 非 JSON */ }
    seen.reqs.push({ headers: req.headers, raw, parsed })

    const aborted = { v: false }
    res.on('close', () => {
      if (!res.writableFinished) { aborted.v = true; seen.abortedEarly++ } else seen.finished++
    })

    if (delayMs) await sleep(delayMs)
    if (aborted.v) return
    if (risk400) {
      res.writeHead(400, { 'content-type': 'application/json' })
      res.end(JSON.stringify({ error: { message: 'Content Exists Risk' } }))
      return
    }
    const payload = body ?? JSON.stringify({ ok: true, model: parsed?.model ?? null })
    res.writeHead(status, { 'content-type': 'application/json', 'content-length': Buffer.byteLength(payload) })
    res.end(payload)
  })
  return new Promise((resolve) => {
    srv.listen(0, '127.0.0.1', () => resolve({ srv, port: srv.address().port, seen }))
  })
}

const freePort = () => new Promise((resolve) => {
  const s = http.createServer()
  s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => resolve(p)) })
})

/** 中继健康检查（与 relay 内建 HEALTH_PATH 一致） */
const health = (port) => new Promise((resolve) => {
  const req = http.get({ host: '127.0.0.1', port, path: '/__relay__/health', timeout: 800 }, (res) => {
    let s = ''; res.setEncoding('utf8')
    res.on('data', (c) => { s += c })
    res.on('end', () => { try { const j = JSON.parse(s); resolve(j?.relay === 'cache-relay' ? j : null) } catch { resolve(null) } })
    res.on('error', () => resolve(null))
  })
  req.on('error', () => resolve(null))
  req.on('timeout', () => { req.destroy(); resolve(null) })
})

const isPidAlive = (pid) => { try { process.kill(pid, 0); return true } catch { return false } }

// ── 发一个请求到中继 ──────────────────────────────────────────────────
function send(port, { body, headers = {}, timeoutMs = 15000 } = {}) {
  return new Promise((resolve) => {
    const data = typeof body === 'string' ? body : JSON.stringify(body)
    const req = http.request({
      host: '127.0.0.1', port, path: '/v1/messages', method: 'POST',
      headers: { 'content-type': 'application/json', 'content-length': Buffer.byteLength(data), ...headers },
      agent: false,
    }, (res) => {
      const cs = []
      res.on('data', (c) => cs.push(c))
      res.on('end', () => resolve({ status: res.statusCode, text: Buffer.concat(cs).toString('utf8'), req }))
      res.on('error', () => {})
    })
    req.on('error', (e) => resolve({ status: 0, text: '', error: e.message, req }))
    req.setTimeout(timeoutMs, () => { req.destroy(); resolve({ status: 0, text: '', error: 'timeout', req }) })
    req.end(data)
    resolve._last = req
    return req
  })
}

/** 发请求并把「中继→客户端」的 socket 交出来，便于中途掐断 */
function sendAbortable(port, body, abortAfterMs) {
  return new Promise((resolve) => {
    const data = JSON.stringify(body)
    const req = http.request({
      host: '127.0.0.1', port, path: '/v1/messages', method: 'POST',
      headers: { 'content-type': 'application/json', 'content-length': Buffer.byteLength(data) },
      agent: false,
    }, (res) => { res.on('data', () => {}); res.on('error', () => {}) })
    req.on('error', () => {})
    req.end(data)
    setTimeout(() => { req.destroy() }, abortAfterMs)
    resolve(req)
  })
}

// ── 主流程 ────────────────────────────────────────────────────────────
const STATE = mkdtempSync(join(tmpdir(), 'relay-it-'))
const upA = await startUpstream()
const upB = await startUpstream()          // 热切换目标
const upFB = await startUpstream()         // 400 兜底目标
const upSlow = await startUpstream({ delayMs: 3000 })  // 断连测试
const upRisk = await startUpstream({ risk400: true })

const PORT = await freePort()
// 判源注意：假上游是 127.0.0.1，host 不含已知域名，而路径是 /v1/messages
// → detectProvider 会兜底判成 anthropic（该分支按设计**不**剥 cache_control、**不**钉 token）。
// 生产走 https://api.deepseek.com/anthropic 会自动判为 deepseek，这里显式钉住以便测对齐策略。
// ⑧ 单独验证生产 URL 的判源结果确实正确。
const cfgFor = (upstream, extra = {}) => JSON.stringify({
  forceProvider: 'deepseek',
  defaultUpstream: upstream,
  ...extra,
})

writeFileSync(join(STATE, 'config.json'), cfgFor(`http://127.0.0.1:${upA.port}`, {
  dump: false,
  classifier: { enabled: false, sessionIdSuffix: '-classifier', modelMap: { 'deepseek-v4-pro[1m]': 'deepseek-flash', '*': 'deepseek-flash' } },
  fallback: { upstream: `http://127.0.0.1:${upFB.port}`, authToken: 'test-fallback-token' },
}))

const relay = spawn(NODE, [RELAY, 'start'], {
  env: { ...process.env, RELAY_PORT: String(PORT), RELAY_STATE_DIR: STATE, RELAY_DEFAULT_UPSTREAM: '' },
  stdio: ['ignore', 'pipe', 'pipe'],
})
let relayLog = ''
relay.stdout.on('data', (c) => { relayLog += c })
relay.stderr.on('data', (c) => { relayLog += c })
// 等监听
for (let i = 0; i < 100 && !relayLog.includes('listening'); i++) await sleep(50)
ok(relayLog.includes('listening'), '中继子进程启动并监听')

const mainBody = () => ({
  model: 'deepseek-v4-pro',
  max_tokens: 100,
  system: [{ type: 'text', text: "Today's date is 2026-09-12. You are Claude Code." }],
  tools: [{ name: 'Write' }, { name: 'Bash' }, { name: 'Read' }],
  messages: [
    { role: 'user', content: [{ type: 'text', text: 'hi', cache_control: { type: 'ephemeral' } }] },
    { role: 'user', content: '<system-reminder><total_tokens>999123 tokens left</total_tokens></system-reminder>' },
  ],
})
const classifierBody = () => ({
  model: 'deepseek-v4-pro[1m]',
  max_tokens: 64,
  system: [{ type: 'text', text: 'You are a security monitor for autonomous AI coding agents.' }],
  tools: [],
  messages: [{ role: 'user', content: 'Action: rm -rf /tmp/x' }],
})

console.log('\n① 主会话对齐')
const r1 = await send(PORT, { body: mainBody(), headers: { 'x-claude-code-session-id': 'SID-MAIN' } })
const s1 = upA.seen.reqs.at(-1)
ok(r1.status === 200, '请求 200 返回', `status=${r1.status}`)
ok(s1?.parsed != null, '上游收到 JSON body')
ok(JSON.stringify(s1.parsed).includes('2000-01-01'), '日期已钉桩为 2000-01-01')
ok(!JSON.stringify(s1.parsed).includes('2026-09-12'), '真实日期已被替换')
ok(JSON.stringify(s1.parsed).includes('<total_tokens>1000000 tokens left'), 'token 计数已钉桩')
ok(!JSON.stringify(s1.parsed).includes('cache_control'), 'cache_control 已剥离')
ok(JSON.stringify(s1.parsed.tools.map((t) => t.name)) === JSON.stringify(['Bash', 'Read', 'Write']), '工具已按 name 排序')
ok(s1.headers['x-claude-code-session-id'] === 'SID-MAIN', '主会话 session-id 未被改写')
ok(s1.headers.authorization === undefined || typeof s1.headers.authorization === 'string', '鉴权头透传（不落地密钥）')

console.log('\n② 分类器：模型重映射 + 会话桶分离')
const r2 = await send(PORT, { body: classifierBody(), headers: { 'x-claude-code-session-id': 'SID-CLS' } })
const s2 = upA.seen.reqs.at(-1)
ok(r2.status === 200, '分类器请求 200 返回', `status=${r2.status}`)
ok(s2.parsed?.model === 'deepseek-flash', 'pro[1m] 已重映射为 deepseek-flash', `model=${s2.parsed?.model}`)
ok(s2.headers['x-claude-code-session-id'] === 'SID-CLS-classifier', '分类器 session-id 追加了 -classifier 后缀', `got=${s2.headers['x-claude-code-session-id']}`)
ok(s2.headers['x-claude-code-session-id'] !== 'SID-MAIN', '主/分类器落在不同会话桶')

console.log('\n③ 上游连接复用')
const before = upA.seen.sockets.size
for (let i = 0; i < 4; i++) await send(PORT, { body: mainBody() })
ok(upA.seen.sockets.size === before, `连续请求复用同一连接（新开 ${upA.seen.sockets.size - before} 条，应为 0）`)

console.log('\n④ 客户端断连 → 销毁上游请求')
const abortedBefore = upSlow.seen.abortedEarly
writeFileSync(join(STATE, 'config.json'), cfgFor(`http://127.0.0.1:${upSlow.port}`, {
  dump: false,
  classifier: { enabled: false, sessionIdSuffix: '-classifier', modelMap: {} },
}))
await sleep(20)
await sendAbortable(PORT, mainBody(), 300)
await sleep(800)
ok(upSlow.seen.abortedEarly > abortedBefore, `上游请求被中途掐断（abortedEarly ${abortedBefore} → ${upSlow.seen.abortedEarly}）`)

console.log('\n⑤ 热改 config.json 免重启生效')
writeFileSync(join(STATE, 'config.json'), cfgFor(`http://127.0.0.1:${upB.port}`, {
  dump: true,
  classifier: { enabled: false, sessionIdSuffix: '-classifier', modelMap: {} },
}))
await sleep(20)
const bBefore = upB.seen.reqs.length
const dBefore = existsSync(join(STATE, 'dump.jsonl')) ? readFileSync(join(STATE, 'dump.jsonl'), 'utf8').length : 0
const r5 = await send(PORT, { body: mainBody() })
ok(upB.seen.reqs.length > bBefore, '未重启即切到新的 defaultUpstream')
ok(r5.status === 200, '热切换后请求仍 200')
const dAfter = existsSync(join(STATE, 'dump.jsonl')) ? readFileSync(join(STATE, 'dump.jsonl'), 'utf8').length : 0
ok(dAfter > dBefore, '未重启即开启 dump（热生效）')
const dumpLine = existsSync(join(STATE, 'dump.jsonl')) ? readFileSync(join(STATE, 'dump.jsonl'), 'utf8').trim().split('\n').at(-1) : ''
ok(dumpLine && JSON.parse(dumpLine).hdr.detail.authorization === undefined, 'dump 里不出现鉴权头原文')
ok(!/sk-|Bearer [A-Za-z0-9]{8}/.test(dumpLine), 'dump 行不含明文密钥')

console.log('\n⑥ 内容审核 400 → 备用上游兜底')
writeFileSync(join(STATE, 'config.json'), cfgFor(`http://127.0.0.1:${upRisk.port}`, {
  fallback: { upstream: `http://127.0.0.1:${upFB.port}`, authToken: 'test-fallback-token' },
  classifier: { enabled: false },
}))
await sleep(20)
const fbBefore = upFB.seen.reqs.length
const r6 = await send(PORT, { body: mainBody() })
ok(upFB.seen.reqs.length > fbBefore, '命中 400 后改投备用上游')
ok(r6.status === 200, '兜底返回 200（会话不中断）', `status=${r6.status}`)
ok(upFB.seen.reqs.at(-1)?.headers.authorization === 'Bearer test-fallback-token', '兜底携带备用鉴权头')

console.log('\n⑦ 判源（生产 URL 必须判对，否则对齐策略会走错分支）')
const { detectProvider } = await import('../cache-relay.mjs')
const D = [
  ['https://api.deepseek.com/anthropic', 'deepseek-v4-pro', '/v1/messages', 'deepseek'],
  ['https://api.deepseek.com', 'deepseek-chat', '/chat/completions', 'deepseek'],
  ['https://open.bigmodel.cn/api/anthropic', 'glm-4.6', '/v1/messages', 'glm'],
  ['https://openrouter.ai/api/v1', 'z-ai/glm-4.6', '/chat/completions', 'openrouter'],
  ['https://api.anthropic.com', 'claude-sonnet-5', '/v1/messages', 'anthropic'],
]
for (const [url, model, path, expect] of D) {
  const got = detectProvider(url, model, path)
  ok(got === expect, `${url} → ${expect}`, got === expect ? '' : `实际 ${got}`)
}

console.log('\n⑧ 非 JSON / 无上游 的健壮性')
const r7 = await send(PORT, { body: 'not json at all' })
ok([200, 400, 502].includes(r7.status), '非 JSON body 不崩（透传）', `status=${r7.status}`)
ok(!relayLog.includes('UnhandledPromiseRejection'), '无未处理异常')

console.log('\n⑨ pid 文件失效不再误杀（stop 以健康检查识别身份）')
// 起一个「旁观者」进程（与中继无关），把它的 pid 写进 relay.pid，模拟 pid 被系统复用/文件过期。
// 旧的 stop 会照着 pid 文件裸 kill —— 那就会杀掉这个无辜进程。新的 stop 靠健康检查认身份。
const bystander = spawn(NODE, ['-e', 'setTimeout(() => {}, 120000)'], { stdio: 'ignore' })
await sleep(300)
ok(isPidAlive(bystander.pid), '旁观者进程已启动')
writeFileSync(join(STATE, 'relay.pid'), String(bystander.pid))

const cliEnv = { ...process.env, RELAY_PORT: String(PORT), RELAY_STATE_DIR: STATE }
const stopOut = execFileSync(NODE, [RELAY, 'stop'], { env: cliEnv, encoding: 'utf8' })
ok(stopOut.includes('已停止'), 'stop 认出真实中继并停止（健康检查路径）', stopOut.trim())
ok(isPidAlive(bystander.pid), 'pid 文件里的旁观者进程未被误杀')

let gone = false
for (let i = 0; i < 60; i++) { if (!(await health(PORT))) { gone = true; break } await sleep(100) }
ok(gone, '中继确实已退出（端口无应答）')
ok(!existsSync(join(STATE, 'relay.pid')), '停止后 pid 文件已清理')

// 再 stop 一次应安全幂等
const stopOut2 = execFileSync(NODE, [RELAY, 'stop'], { env: cliEnv, encoding: 'utf8' })
ok(!stopOut2.includes('已停止'), '重复 stop 幂等（不会误杀）', stopOut2.trim())
ok(isPidAlive(bystander.pid), '重复 stop 后旁观者仍存活')
try { bystander.kill() } catch { /* 已退出 */ }

// ── 收尾 ──
relay.kill()
for (const u of [upA, upB, upFB, upSlow, upRisk]) u.srv.close()

console.log(`\n通过 ${pass}  失败 ${fails.length}`)
if (fails.length) {
  console.log('\n失败明细:')
  for (const f of fails) console.log('  - ' + f)
  console.log('\n--- 中继日志 ---\n' + relayLog.slice(-2000))
  process.exit(1)
}
console.log('✓ 集成测试全过：对齐/分离/复用/断连/热配置/兜底 行为符合预期')
process.exit(0)
