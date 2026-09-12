#!/usr/bin/env node
/**
 * ds2ox-proxy — 本地模型路由改写代理【已退役归档 · 脱敏版】
 *
 * ⚠️⚠️ 本文件是「知识归档」，不是可部署件。归档日期 2026-09-12。
 *
 *   ⛔ 不要直接重启本脚本。它有三处已知设计缺陷（见下），未经修复即运行会
 *      把本机的模型流量交给任何能抢占 127.0.0.1:8899 的进程。
 *
 * 【原始用途】
 *   把 DSH 的 deepseek-official 流量改写路由到 OpenRouter 上的免费模型，
 *   绕开 deepseek 按量计费。挂载方式是在 ~/.dsh/settings.yaml 写：
 *     llm-deepseek:
 *       baseURL: http://127.0.0.1:8899
 *   dsh-llm-deepseek 逐请求重读 settings.yaml，因此改配置无需重启。
 *
 * 【路由行为】
 *   POST /chat/completions          → 改写 body.model 后转发 OpenRouter
 *   上游 402/408/5xx/网络错误        → 回落 api.deepseek.com（透传原 body）
 *   上游 429                        → 先原地退避重放（2.5s / 5s），仍 429 则换备用模型
 *   滑动窗口成功率 < 0.4 且窗口已满   → 熔断 3 分钟，期间全走 deepseek
 *   ~/.dsh/ds2ox-proxy.disabled 存在 → 全量旁路到 deepseek（软回滚开关）
 *   /anthropic/v1/messages          → 默认透传 deepseek（web_search 用）
 *   ~/.dsh/ds2ox-search.stub 存在    → 返回空搜索结果（零成本）
 *
 * 【脱敏说明】
 *   原文件第 24 行硬编码 OpenRouter 密钥（明文，前缀 `sk-or-…`）。
 *   本文档按知识库既有范式（参见 scripts/claude-ops-deployments/cache-relay/
 *   cache-relay.mjs 的「密钥不落地（透传头）」）改为从环境变量读取，
 *   文件中不含任何真实凭据。
 *
 * 【已知设计缺陷 —— 重新启用前必须修复】
 *   D1. 无入站鉴权：任何本机进程都能借用该密钥发请求，或经它透传到带
 *       Authorization 的 deepseek 上游。修复：加一个随机 token 头校验。
 *   D2. 无 Host 头校验：存在浏览器侧 DNS 重绑定 / 跨站请求面。
 *       修复：校验 Host ∈ {127.0.0.1, localhost}。
 *   D3. 抢占即劫持：baseURL 逐请求读取，任何进程只要监听 8899 并伪装响应，
 *       即可在不触碰任何文件的情况下替换模型输出、窃取全部提示词与对话。
 *       修复：改用 Unix domain socket 或加进程间共享密钥；端口改为非固定值。
 *
 * 用法:
 *   DS2OX_PROXY_KEY=<your-openrouter-key> node ds2ox-proxy.mjs
 *
 * 环境变量:
 *   DS2OX_PROXY_KEY   必需。OpenRouter 密钥（原为硬编码，现外置）。
 *   DS2OX_PROXY_PORT  可选。监听端口，默认 8899。
 *   DS2OX_PROXY_HOST  可选。监听地址，默认 127.0.0.1（切勿改为 0.0.0.0）。
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { Readable } from "node:stream";

const PORT = Number(process.env.DS2OX_PROXY_PORT ?? 8899);
const HOST = process.env.DS2OX_PROXY_HOST ?? "127.0.0.1";
const HOME = process.env.USERPROFILE || process.env.HOME || ".";
const DISABLED_FILE = path.join(HOME, ".dsh", "ds2ox-proxy.disabled");
const SEARCH_STUB_FILE = path.join(HOME, ".dsh", "ds2ox-search.stub");
const LOG_FILE = path.join(HOME, ".dsh", "ds2ox-proxy.log");

// 脱敏：原为第 24 行硬编码的 OpenRouter 密钥，现从环境变量读取。
// 缺失即拒绝启动，避免"空密钥静默失败"。
const OR_KEY = process.env.DS2OX_PROXY_KEY;
if (!OR_KEY) {
  process.stderr.write("ds2ox-proxy: 缺少环境变量 DS2OX_PROXY_KEY，拒绝启动\n");
  process.exit(1);
}

const OR_URL = "https://openrouter.ai/api/v1/chat/completions";
const DS_URL = "https://api.deepseek.com/chat/completions";
// 原目标模型（历史值，随上游上下架变化）：
//   z-ai/glm-5.2:free（主）/ minimax/minimax-m3:free（备）
//   ox-alpha 曾等价于 z-ai/glm-5.3-flash，2026-08-26 起改用 glm-5.2:free
const TARGET_MODEL = process.env.DS2OX_PROXY_MODEL ?? "z-ai/glm-5.2:free";
const BACKUP_MODEL = process.env.DS2OX_PROXY_BACKUP_MODEL ?? "minimax/minimax-m3:free";
const FALLBACK_STATUSES = new Set([402, 408, 500, 502, 503, 504]);
const RETRY_DELAYS = [2500, 5000];   // 429 原地退避重放
const WIN_SIZE = 5;                  // 成功率滑动窗口
const COOLDOWN_MS = 3 * 60 * 1000;   // 熔断冷却
const BREAK_RATE = 0.4;              // 窗口满且成功率 < 0.4 则熔断
const window_ = [];
let cooldownUntil = 0;

function record(success) {
  window_.push(success);
  if (window_.length > WIN_SIZE) window_.shift();
}
function successRate() {
  return window_.length ? window_.filter(Boolean).length / window_.length : 1;
}
function inCooldown() { return Date.now() < cooldownUntil; }
function enterCooldown() {
  cooldownUntil = Date.now() + COOLDOWN_MS;
  log(`circuit-open winRate=${successRate().toFixed(2)} cooldown=${COOLDOWN_MS / 1000}s`);
}
function sleep(ms, signal) {
  return new Promise((resolve) => {
    if (signal?.aborted) return resolve();
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => { clearTimeout(t); resolve(); }, { once: true });
  });
}

function log(msg) {
  const line = `${new Date().toISOString()} ${msg}\n`;
  try { fs.appendFileSync(LOG_FILE, line); } catch {}
  process.stdout.write(line);
}

function rotateLog() {
  try {
    const st = fs.statSync(LOG_FILE);
    if (st.size > 512 * 1024) fs.renameSync(LOG_FILE, LOG_FILE + ".old");
  } catch {}
}

function isDisabled() {
  try { return fs.existsSync(DISABLED_FILE); } catch { return false; }
}

async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks);
}

function rewriteForOxAlpha(rawBody, model = TARGET_MODEL) {
  let body;
  try { body = JSON.parse(rawBody.toString("utf-8")); } catch { return null; }
  body.model = model;
  delete body.thinking;
  delete body.reasoning_effort;
  return JSON.stringify(body);
}

function deepseekFetch(headers, body, signal) {
  const auth = headers["authorization"];
  return fetch(DS_URL, {
    method: "POST",
    headers: {
      authorization: auth,
      "content-type": "application/json",
      accept: headers["accept"] || "text/event-stream"
    },
    body,
    signal
  });
}

async function route(req, res, headers, rawBody) {
  const start = Date.now();
  const incomingModel = (() => {
    try { return JSON.parse(rawBody.toString("utf-8")).model || "?"; } catch { return "?"; }
  })();

  if (isDisabled()) {
    log(`route=deepseek(kill-switch) model=${incomingModel}`);
    const up = await deepseekFetch(headers, rawBody, req.signal);
    relay(up, res);
    log(`route=deepseek(kill-switch) status=${up.status} ms=${Date.now() - start}`);
    return;
  }

  const oxBody = rewriteForOxAlpha(rawBody);
  if (oxBody === null) {
    res.writeHead(400, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: { message: "invalid JSON body" } }));
    return;
  }

  if (inCooldown()) {
    const up = await deepseekFetch(headers, rawBody, req.signal);
    relay(up, res);
    log(`route=deepseek(cooldown) model=${incomingModel} status=${up.status} ms=${Date.now() - start}`);
    return;
  }

  const oxHeaders = {
    authorization: `Bearer ${OR_KEY}`,
    "content-type": "application/json",
    accept: headers["accept"] || "text/event-stream"
  };
  let up;
  try {
    up = await fetch(OR_URL, { method: "POST", headers: oxHeaders, body: oxBody, signal: req.signal });
    let replayed = false;
    if (up.status === 429) {
      for (const delay of RETRY_DELAYS) {
        await sleep(delay, req.signal);
        up = await fetch(OR_URL, { method: "POST", headers: oxHeaders, body: oxBody, signal: req.signal });
        replayed = true;
        if (up.ok || up.status !== 429) break;
      }
      if (up.status === 429) {
        await sleep(1000, req.signal);
        up = await fetch(OR_URL, { method: "POST", headers: oxHeaders, body: rewriteForOxAlpha(rawBody, BACKUP_MODEL), signal: req.signal });
        if (up.ok) log(`route=ox-alpha(backup) model=${BACKUP_MODEL} ms=${Date.now() - start}`);
      }
    }
    if (up.ok) {
      record(true);
      relay(up, res);
      log(`route=ox-alpha${replayed ? "(retry)" : ""} winRate=${successRate().toFixed(2)} ms=${Date.now() - start}`);
      return;
    }
    record(false);
    if (up.status === 429) {
      if (window_.length >= WIN_SIZE && successRate() < BREAK_RATE) enterCooldown();
      relay(up, res);
      log(`route=ox-alpha-relay429 winRate=${successRate().toFixed(2)} ms=${Date.now() - start}`);
      return;
    }
    if (!FALLBACK_STATUSES.has(up.status)) {
      relay(up, res);
      log(`route=ox-alpha status=${up.status} ms=${Date.now() - start}`);
      return;
    }
    log(`route=fallback reason=openrouter-${up.status} model=${incomingModel}`);
    try { await up.body?.cancel(); } catch {}
  } catch (err) {
    log(`route=fallback reason=transport(${err.cause?.code || err.message}) model=${incomingModel}`);
  }
  const ds = await deepseekFetch(headers, rawBody, req.signal);
  relay(ds, res);
  log(`route=deepseek(fallback) model=${incomingModel} status=${ds.status} ms=${Date.now() - start}`);
}

function isSearchStub() {
  try { return fs.existsSync(SEARCH_STUB_FILE); } catch { return false; }
}

async function routeSearch(req, res, headers, rawBody) {
  const start = Date.now();
  const model = (() => {
    try { return JSON.parse(rawBody.toString("utf-8")).model || "?"; } catch { return "?"; }
  })();

  if (isSearchStub()) {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({
      id: "msg_ds2ox-search-stub",
      type: "message",
      role: "assistant",
      model,
      content: [{ type: "web_search_tool_result", tool_use_id: "stub_1", content: [] }],
      stop_reason: "tool_use",
      stop_sequence: null,
      usage: { input_tokens: 0, output_tokens: 0 }
    }));
    log(`route=search-stub model=${model} ms=${Date.now() - start}`);
    return;
  }

  const up = await fetch("https://api.deepseek.com/anthropic/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": headers["x-api-key"] || "",
      authorization: headers["authorization"] || "",
      "anthropic-version": headers["anthropic-version"] || "2023-06-01",
      "content-type": "application/json",
      accept: "application/json"
    },
    body: rawBody,
    signal: req.signal
  });
  relay(up, res);
  log(`route=search-passthrough model=${model} status=${up.status} ms=${Date.now() - start}`);
}

function relay(up, res) {
  const h = {
    "content-type": up.headers.get("content-type") || "text/event-stream",
    "cache-control": "no-cache"
  };
  const retryAfter = up.headers.get("retry-after");
  const requestId = up.headers.get("x-request-id");
  if (retryAfter) h["retry-after"] = retryAfter;
  if (requestId) h["x-request-id"] = requestId;
  res.writeHead(up.status, h);
  if (up.body) {
    Readable.fromWeb(up.body).pipe(res);
  } else {
    res.end();
  }
}

const server = http.createServer(async (req, res) => {
  const { pathname } = new URL(req.url, `http://${HOST}:${PORT}`);
  try {
    if (req.method === "GET" && (pathname === "/" || pathname === "/health")) {
      res.writeHead(200, { "content-type": "text/plain" });
      res.end(`ds2ox-proxy ok, disabled=${isDisabled()}\n`);
      return;
    }
    if (req.method === "POST" && (pathname === "/chat/completions" || pathname === "/v1/chat/completions")) {
      const rawBody = await readBody(req);
      await route(req, res, req.headers, rawBody);
      return;
    }
    if (req.method === "POST" && (pathname === "/anthropic/v1/messages" || pathname === "/v1/messages" || pathname === "/messages")) {
      const rawBody = await readBody(req);
      await routeSearch(req, res, req.headers, rawBody);
      return;
    }
    res.writeHead(404);
    res.end();
  } catch (err) {
    log(`error ${err.message}`);
    try {
      res.writeHead(502, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { message: `ds2ox-proxy: ${err.message}` } }));
    } catch {}
  }
});

server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    process.stdout.write("ds2ox-proxy: port already in use, exiting\n");
    process.exit(0);
  }
  log(`fatal ${err.message}`);
  process.exit(1);
});

server.listen(PORT, HOST, () => {
  rotateLog();
  log(`listening on ${HOST}:${PORT}`);
});
