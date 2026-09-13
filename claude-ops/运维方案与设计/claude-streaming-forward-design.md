---
title: Proxy 流式转发 + Model Router 协同方案
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-06-17
updated: 2026-09-13
status: review
---

# Proxy 流式转发 + Model Router 协同方案

See also: [[Claude-Ops-KB-Home]] · [[claude-flash-primary-analysis]] · [[PERMAFROST_MODIFICATIONS]]

> 日期: 2026-06-17 | 状态: 代码已就绪，待隔离测试(:8789)

---

## 一、现状

```
CC → permafrost(:8788) → proxy(:8787) → DeepSeek
       ✅ 已流式(chunked)         ❌ 全量缓冲
       嗅探head 256KB                  ↓
       嗅探tail 64KB              先收完再发给 CC
       model_router 反馈挂载点       (瓶颈: 25s 平均延迟)
```

**只需改 proxy 一处**。permafrost 已经是流式的。

---

## 二、Proxy 改动: 缓冲 → pipe

### 当前代码 (缓冲模式)

```javascript
// doRequest() — 第28-34行
res.on('data', c => data.push(c));
res.on('end', () => resolve({
    status: res.statusCode,
    headers: res.headers,
    body: Buffer.concat(data),
}));

// createServer — 第94行
clientRes.writeHead(result.status, resHeaders);
clientRes.end(result.body);  // 一次性发送
```

### 目标代码 (流式模式)

```javascript
// doRequest() — 改为直接返回 upstream response
function doRequest(opts, body, retries) {
    return new Promise((resolve, reject) => {
        const req = https.request({
            hostname: TARGET_URL.hostname, port: 443,
            path: TARGET_URL.pathname + opts.path,
            method: opts.method,
            headers: { ...opts.headers, host: TARGET_URL.hostname },
            timeout: 180000,
        }, (res) => {
            // 直接返回 response stream, 不缓冲
            resolve({ status: res.statusCode, headers: res.headers, stream: res });
        });
        req.on('error', reject);
        if (body) req.write(body);
        req.end();
    });
}

// createServer — 改为 pipe
clientRes.writeHead(result.status, resHeaders);
result.stream.pipe(clientRes);  // 边收边发
```

### 重试兼容

流式模式下已开始写响应头，不能重试。改为只在连接建立阶段重试：

```javascript
req.on('error', (err) => {
    // 只重试连接错误（响应头还没写）
    if (!clientRes.headersSent && isRetryable(err) && retries > 0) {
        setTimeout(() => doRequest(opts, body, retries - 1).then(...), delay);
    } else {
        // 已经开始写响应了 → 记录错误, 客户端会看到断开
        console.error(`[proxy] stream error: ${err.message}`);
        if (!clientRes.headersSent) {
            clientRes.writeHead(502, { 'Content-Type': 'application/json' });
            clientRes.end(JSON.stringify({ error: 'upstream_error' }));
        }
    }
});
```

---

## 三、Model Router 质量反馈

### 当前: 读 permafrost 已嗅探的 head

permafrost_proxy.py `_forward()` 中已有：

```python
head = bytearray()   # 前 256KB (第一个 chunk 通常是完整响应)
tail = bytearray()   # 后 64KB

# 每收一个 chunk:
head.extend(chunk[: _SNIFF_HEAD - len(head)])
tail.extend(chunk)
if len(tail) > _SNIFF_TAIL: del tail[:-_SNIFF_TAIL]

# 转发后, 已有的调用:
u_head = _sniff_usage(bytes(head).decode(...))
u_tail = _sniff_usage(bytes(tail).decode(...))
# → 这里已经有完整的响应文本
```

### Model router 复用这个 head:

```python
# 在现有 STATS.record_usage 之后
if os.environ.get("PERMAFROST_MODEL_ROUTING") == "1":
    resp_text = bytes(head).decode("utf-8", "replace")
    from model_router import feedback_flash_response
    feedback_flash_response(session, resp_text)
```

**代码已就绪，待隔离测试（无需改动）。**

---

## 四、改动清单

| 文件 | 改动 | 行数 |
|------|------|------|
| `claude-resilience-proxy.js` | 缓冲→pipe, 重试逻辑适配 | ~30行 |
| permafrost: 无改动 | 已经是流式 | 0 |
| model_router: 无改动 | 已复用 head 嗅探 | 0 |

---

## 五、质量反馈兼容性分析

permafrost 的流式嗅探机制天然兼容质量反馈：

```
DeepSeek 响应 → permafrost 收 chunk
                  ├─ head buffer (前256KB) → 质量反馈: 长度/拒绝/空回复
                  ├─ tail buffer (后64KB)  → token 统计: hit/miss
                  └─ _write_chunk() → 立即发给 CC (流式)
```

| 质量信号 | 覆盖范围 | 说明 |
|---------|---------|------|
| 回复过短 (<50 chars) | head ✅ | 前几个 chunk 就能判断 |
| 模型拒绝 ("I cannot") | head ✅ | 拒绝语在回复开头 |
| 显式退出/错误 | head ✅ | 异常回复通常很短 |
| 工具调用结果 | head ✅ | tool_use block 在 256KB 内 |
| 只有 >256KB 的超长回复 | tail ⚠️ | 极少，且本身说明是复杂任务 |

**flash 简单回复 100% 落在 256KB head 内，质量反馈完全不受影响。**

## 六、预期效果（设计目标，未验证）

| 指标 | 当前 | 优化后 |
|------|------|--------|
| CC 收到首字节延迟 | 平均 25s (等完整响应) | ~2-3s (第一个chunk) |
| 感知延迟 | 76s (最坏) | ~3-5s (流式首字节) |
| 重试能力 | 全量重试 | 连接阶段重试 |
| 内存占用 | 缓冲全量 (~1MB) | 流式 (~16KB) |

> [!note] 口径与采集方式（2026-09-13 补）
> 上表是**设计目标，不是实测结论**。原表的「平均 25s」「76s (最坏)」均未记录样本量、采集时间与口径（均值还是单次观察），「~2-3s / ~3-5s / ~16KB」是改造后的目标值。改造前没有任何一次可复核的采集记录。
> 后续按以下口径回填实测值：
> - 首字节/整响应耗时：现行 Node 代理在响应结束时打印耗时行 `[proxy] POST /v1/messages → 200 (12345ms)`（全量缓冲模式下该值≈首字节延迟），从 `proxy.log` 统计：
>   `grep -oE '→ 200 \([0-9]+ms\)' proxy.log | grep -oE '[0-9]+' | sort -n | awk '{a[NR]=$1} END{print "n="NR, "p50="a[int((NR+1)*0.5)], "p95="a[int((NR+1)*0.95)]}'`
> - 流式落地后的 TTFB 需在客户端侧量：`curl -s -o /dev/null -w 'ttfb=%{time_starttransfer}s\n' http://127.0.0.1:8787/anthropic/v1/messages ...`
> - 内存：`ps -o rss= -p <proxy_pid>`（单位 KB），取改造前后各 ≥30 次请求的峰值。
> - 判定门槛：改造前后各取 ≥30 次样本，比较 TTFB 的 p50/p95 与 RSS 峰值；样本不足 30 次时只写「单次观察，非统计量」。

---

## 附1: Proxy 层工具归一化 (预研, 待落地)

### 方案
proxy.js 第73行后插入 ~15行, 读取 `~/.claude/tool-anchor.json` 配置,
剥离非锚点工具后转发。version-hook.sh 自动维护配置。

### 状态
- 代码已就绪，待隔离测试(:8789)
- 逃生: 删除配置文件 → 恢复全量工具; L0a关闭permafrost补丁
- 风险: 极低(解析失败原样转发, 仅影响POST /v1/messages)

### 落地条件
1. 隔离测试通过
2. 逃生通道验证
3. 当前 permafrost 补丁稳定运行 ≥1周

### 隔离测试清单与通过标准（2026-09-13 补）

| 测试项 | 操作 | 通过标准 |
|---|---|---|
| 正常 POST 转发 | 在隔离端口启动改造后的 proxy，`curl` 一条最小 `/v1/messages` 请求（命令见 §六） | HTTP 200，响应体与直连一致（仅非锚点工具被剥离），日志无异常 |
| 解析失败原样转发 | 把 `~/.claude/tool-anchor.json` 写成非法 JSON 后发同一请求 | 不报错、按原工具列表全量转发；日志留下解析失败的回退记录 |
| 配置缺失行为 | 重命名/删除 `tool-anchor.json` 后发同一请求 | 行为与改造前完全一致（全量工具），无需重启 CC |
| 锚点工具缺失 | 配置里保留一个不存在的工具名 | 告警或忽略并记录，**不**产生空 `tools` 数组（空数组会被上游判 400） |
| 非 POST /v1/messages 流量 | GET `/v1/models` 等其它路径 | 原样转发，不被归一化逻辑触碰 |
| 逃生通道 | 删除配置文件 + 关闭 permafrost 补丁（L0a） | 一步操作内恢复改造前行为 |

- 重复次数与超时：每个用例重复 3 次；任一用例出现 5xx 或响应体不一致即判失败，回退到改造前配置。
- 「≥1 周」的度量口径：以 permafrost 补丁进程的**连续运行时间**计（`ps -o etime= -p <pid>` ≥ 7 天），且期间无因该补丁导致的会话中断或工具丢失记录；只数日历天数不算。
- 端口核实（2026-09-13）：:8789 **不能假定空闲** —— 诊断中继 `diagnostic-relay/relay.js` 默认 `RELAY_PORT=8789`，`claude-permafrost-deploy.sh` 也把 8789 列入候选端口池。隔离测试前先 `ss -tlnp | grep 8789` 确认，或改用 8791+ 的空闲端口。

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 加厚 | §六 预期效果表（25s / 76s / ~1MB→~16KB）无样本量、无采集命令与测量条件 | 标题改标「设计目标，未验证」，补口径说明与采集命令（proxy.log 耗时行取 p50/p95、`curl -w '%{time_starttransfer}'` 取 TTFB、`ps -o rss=` 取内存），并给出 ≥30 次样本的判定门槛 |
| 加厚 | 附1 只写「待隔离测试(:8789)」，无测试项、通过标准、超时与「≥1 周」口径 | 补隔离测试清单表（含解析失败/配置缺失/锚点缺失/逃生）、通过与回退判据、「≥1 周」按进程连续运行时间计；并核实 :8789 为 diagnostic-relay 默认端口与 permafrost 候选端口，落地前需 `ss` 确认 |

回链：[[CORRECTIONS]] · [[AGENTS]]
