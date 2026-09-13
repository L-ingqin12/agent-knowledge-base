---
title: 代理部署事故复盘 — Python→Node.js 迁移
aliases: []
tags: [ai/ops, incident]
created: 2026-06-11
updated: 2026-09-13
status: stable
---

# 代理部署事故复盘 — Python→Node.js 迁移

See also: [[Claude-Ops-KB-Home]] · [[claude-resilience-architecture]] · [[claude-deployment-record]]

> 时间: 2026-06-11
> 事件: Python 代理部署后 Claude 无法连接 API, 回滚后恢复, 最终以 Node.js 重写解决
> 影响: 代理方案部署受阻, 用户手动回滚

---

## 一、时间线

```
T+0     部署 Python 代理 v2 (claude-resilience-proxy.py)
        - sysctl TCP keepalive 调优 (失败, PRoot 无权限)
        - 启动代理 (PID 18473, localhost:8787)
        - 更新 .zshrc / .bashrc 中 ANTHROPIC_BASE_URL
        - curl 端到端测试: HTTP 200 ✅
        
T+5min  用户打开新 Claude 会话
        - Claude 使用新 URL → 走代理
        - 代理接收请求, 转发到 DeepSeek
        - Claude 一直重试连接 → 无法正常工作 ❌
        
T+10min 用户手动执行回滚 (bash /root/claude-rollback.sh)
        - 代理进程被杀
        - shell 配置恢复为直连 DeepSeek
        - Claude 恢复正常 ✅
        
T+30min 分析 Python 代理失败原因
        发现: Python http.server (HTTP/1.1) 与 Claude Code (Node.js HTTP/2+SSE)
              协议栈不兼容
        
T+45min 用 Node.js 重写代理
        发现: 路径转发缺少 /anthropic 前缀 → 修复
        
T+60min Node.js 代理测试: HTTP 200 ✅
        部署: shell 配置更新, 代理后台运行, 逃生通道保留
```

## 二、问题清单

### 问题 1: TCP keepalive 调优失败

**现象**: `sysctl -w net.ipv4.tcp_keepalive_time=60` → Permission denied

**根因**: PRoot 容器无权访问 `/proc/sys/net/`。这是 PRoot 的安全限制，不是 bug。

**解决**: 在代理应用层为每个 socket 设置 `SO_KEEPALIVE + TCP_KEEPIDLE`。Node.js 版本用 `socket.setKeepAlive(true, 60000)`。

> [!warning] 补疏漏（2026-09-13）：`setKeepAlive(true, 60000)` 只是首个探测的启动延迟
> 内核默认值（`ip-sysctl` / `man 7 tcp` 逐条核对）：`tcp_keepalive_time` 默认 7200 s（2 hours）、`tcp_keepalive_intvl` 默认 75 s、`tcp_keepalive_probes` 默认 9，man 页另注 *the connection will be aborted after ~11 minutes of retries*。改后最坏判死时间 ≈ `60 + 9×75 = 735 s ≈ 12.3 分钟`——60 s 是首个探测的启动延迟，不是发现死连接的时限。
> 要更快发现死连接应加**应用层超时**（如 `AbortSignal.timeout`），而不是继续压 keepalive；验收判据：断开上游后 `ss -tnp | grep 8787` 的 established 连接数回落到基线。
> 来源：https://docs.kernel.org/networking/ip-sysctl.html ｜ https://man7.org/linux/man-pages/man7/tcp.7.html

**教训**: PRoot 环境下内核级网络调优不可用。所有调优必须在应用层完成。

### 问题 2: Python 代理端到端测试通过但 Claude 无法使用

**现象**: 
- `curl` 通过代理调用 DeepSeek → HTTP 200 ✅
- Claude Code 通过代理调用 → 一直重试, 无法连接 ❌

**根因**: 协议栈不兼容。
- Claude Code 使用 Node.js undici `fetch()`, 默认 HTTP/2
- Python `http.server` 只支持 HTTP/1.1
- Node.js 的 HTTP/2 客户端发送的请求格式 (HPACK header compression, multiplexed streams) Python HTTPServer 无法正确解析

**关键线索**: curl 测试通过是因为 curl 使用的是 HTTP/1.1，恰好与 Python http.server 兼容。但 Claude 用的是完全不同的协议。

> [!warning] 更正（2026-09-13）：这条根因对明文链路不成立（原表述为「Claude Code 使用 Node.js undici `fetch()`, 默认 HTTP/2；Python `http.server` 只支持 HTTP/1.1 → 协议协商失败」）
> undici 官方文档逐字：`allowH2` 为 *Enables HTTP/2 support when the server assigns it a higher priority through ALPN negotiation*（默认 true），`h2Options.useH2c` 为 *Enforces h2c (HTTP/2 cleartext) for non-HTTPS connections*（默认 **false**），HTTP/2 一节另写 *The server must support HTTP/2 and select it during ALPN negotiation*。本链路是明文 `http://127.0.0.1:8787`——无 TLS 即无 ALPN，`allowH2` 无从生效，实际仍是 HTTP/1.1。故该结论应降级为**未验证假设**，方向不算误判但不足以定根因。
> 对照实验：用 `curl --http1.1` 与 `curl --http2-prior-knowledge` 各发一次流式请求比对；同时把「`http.server` 不支持流式/SSE」作为先排除的候选机制（Python 官方文档：*http.server is not recommended for production*）。
> 来源：https://undici.nodejs.org/api/Client ｜ https://docs.python.org/3/library/http.server.html

**解决**: 放弃 Python, 用 Node.js 重写代理。Node.js `http` 模块与 Claude Code 使用相同的底层协议栈。

**教训**: 代理的测试不仅要测 curl，必须用与真实客户端相同协议栈的工具测试。测试环境≠生产环境。

### 问题 3: 路径转发 404

**现象**: Node.js 代理首次测试返回 HTTP 404

**根因**: 
- DeepSeek 的 Anthropic 兼容 API 路径为 `/anthropic/v1/messages`
- Claude 发送请求到 `/v1/messages` (因为 `ANTHROPIC_BASE_URL=http://127.0.0.1:8787`)
- Python 版本的 ANTHROPIC_BASE_URL 是 `http://127.0.0.1:8787/anthropic` → Claude 自动加了 `/anthropic` 前缀 → 代理收到 `self.path = /anthropic/v1/messages`
- Node.js 版本的 ANTHROPIC_BASE_URL 改为 `http://127.0.0.1:8787` (无 `/anthropic`) → Claude 发送 `/v1/messages` → 代理未补全路径 → DeepSeek 返回 404

**解决**: 在代理中, 转发前将 `TARGET_URL.pathname` (`/anthropic`) 拼接到 `req.url` 前面。

> [!note] 补疏漏（2026-09-13）：路径结论有官方出处（正文结论不改）
> DeepSeek 官方文档《Use DeepSeek in Claude Code》逐字给出 `base_url = https://api.deepseek.com/anthropic` 与 `export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`；带 `/anthropic` 的 base URL 使请求落到 `/anthropic/v1/messages`，代理必须把上游 pathname 拼在 `req.url` 前。§6.3 记录的「路径错→404 / 代理活着→认证错误」与该行为自洽。（「Claude 自动加前缀」属通用约定，官方页未逐字写明。）
> 来源：https://api-docs.deepseek.com/guides/anthropic_api

**教训**: URL 路径拼接是代理开发中最容易出错的环节。必须在设计阶段明确: Claude 发送什么路径、代理转发什么路径、上游期望什么路径。

### 问题 4: Python 代理门控冷启动 bug

**现象**: 第一次请求被误判为"网络不稳定"并挂起 90 秒

**根因**: `StabilityTracker.recent_streak(3)` 在历史数据不足 3 条时返回 `False`。对于首次启动(0 条历史), `should_gate()` 的逻辑是: `score=1.0 AND streak_ok=False → gate=True` (门控打开)。这是逻辑错误——无历史数据应假设正常，而非不正常。

**解决**: 在 `should_gate()` 中增加冷启动检测: 无历史数据 → 不放行; 有数据但全是成功且总数不足 streak_n → 不放行。

**教训**: 门控/限流逻辑的默认状态必须是"放行" (fail-open), 不能是"阻止" (fail-closed)。首次启动是门控逻辑最常见的 bug 触发点。

### 问题 5: 后台进程测试持续超时

**现象**: `node proxy.js & sleep 2; curl test` 反复超时 (exit 144)

**根因**: shell 管道问题。`timeout 10 curl ... | tail -3` 中, `timeout` 命令的 SIGTERM 会影响管道中的所有进程。在 PRoot/Termux 环境中, 进程组管理行为可能与标准 Linux 有差异。

> [!warning] 更正（2026-09-13）：这条根因缺少机制支持（原表述为「`timeout` 的 SIGTERM 会影响管道中的所有进程」，并以「反复 exit 144」为佐证）
> GNU coreutils 官方手册逐条：退出码为 124（超时且未用 `--preserve-status`）/125（timeout 自身失败）/126/127/137（KILL，128+9），**144（=128+16）不在其列**，故不能当作被 SIGTERM 杀掉的证据；且 timeout 默认会**新建独立程序组**，只有 `--foreground` 才是 *Don't create a separate background program group*。
> 处置：标为未验证；记录原始退出码与 `timeout --version`，或改用 `setsid` 启动做对照。§6.4 已自行加了「Termux/PRoot 与标准 Linux 不同」的限定，写成「未验证」比写成根因更准确。
> 来源：https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html

**解决**: 使用 `run_in_background` 启动代理进程, 然后用独立的 `curl` 测试, 避免管道和进程组干扰。

**教训**: PRoot 环境中后台进程的行为可能有细微差异。后台进程测试应使用独立的启动和测试步骤, 不要用 `&` + 后续命令在同一 shell 中执行。

## 三、Python vs Node.js 代理对比

| 维度 | Python (失败) | Node.js (成功) |
|------|--------------|---------------|
| HTTP 协议 | HTTP/1.1 only | HTTP/1.1 (与 Claude 兼容) |
| SSE 流支持 | 需手动实现 | 原生 `pipe()` 流式转发 |
| 连接复用 | 手动实现连接池 | 原生 `Agent.keepAlive` |
| 代码行数 | ~400 行 | ~120 行 |
| 依赖 | 标准库, 无外部依赖 | 标准库, 无外部依赖 |
| Claude 兼容 | ❌ 协议不匹配 | ✅ 同协议栈 |
| 稳定性门控 | 已实现 (有冷启动 bug) | 未实现 (保持简单) |
| HEAD 预检 | 已实现 | 未实现 (可后续加) |

## 四、最终方案架构

```
Claude Code (Node.js undici fetch)
  │ ANTHROPIC_BASE_URL=http://127.0.0.1:8787
  │ HTTP/1.1 请求 → /v1/messages
  ▼
Node.js 代理 (http.createServer)
  │ 路径拼接: /anthropic + /v1/messages
  │ 透明转发 headers (去 hop-by-hop)
  │ 流式管道: upstream.pipe(client)
  │ socket.setKeepAlive(true, 60s)
  │ 错误重试: 3次 (1s/3s/8s)
  ▼
https://api.deepseek.com/anthropic/v1/messages
  │ 服务器收到的请求与直连完全相同
```

## 五、仍存在的问题

| 问题 | 状态 | 计划 |
|------|------|------|
| 稳定性门控 | 未实现 | 先验证基本代理稳定性, 后续按需加 |
| HEAD 预检 | 未实现 | 同上门控 |
| TCP keepalive (内核) | PRoot 不可用 | 应用层已覆盖, 无计划 |
| 代理崩溃恢复 | 未守护 | 用户手动重启, 或后续加 systemd/tmux |
| 流式响应缓冲 | 当前用 pipe (边收边转) | 如果 SSE 流中断, Node.js pipe 会自然传播错误 → 触发重试 |

> [!warning] 补疏漏（2026-09-13）：代理是唯一 API 通路，「未守护」不能一笔带过
> - **方案对照与取舍**：systemd user unit（`Restart=always`、`RestartSec=2`、`After=network-online.target`；PRoot/Termux 下 systemd 可能不可用）／tmux 会话（简单但不会自愈）／nohup + 看门狗脚本（最可移植，需自写探活）。
> - **最小验收判据**：`kill -9` 代理后 ≤10 s 内 `ss -tlnp | grep 8787` 重新有监听，且 `curl` 返回预期状态码而非 `000`。
> - 选定方案应把 unit/脚本落到本库 `scripts/claude-ops-deployments/`，否则下次仍靠人工重启。

## 六、排查过程（逐步骤记录）

### 6.1 部署后"连不上 API"

```
用户反馈: "部署后一直连不上api，一直在API连接重试"
用户状态: 已执行回滚 → 恢复直连 → Claude 正常工作
```

**排查逻辑链**:

```
Step 1: 确认代理是否还在运行
  → pgrep -f "claude-resilience-proxy" → 发现残留进程
  → 但 ss -tlnp | grep 8787 → 端口未监听
  → 结论: 代理进程存在但 socket 未启动 (崩溃/启动失败)

Step 2: 确认 shell 配置是否正确回滚
  → grep ANTHROPIC_BASE_URL /root/.zshrc /root/.bashrc
  → 显示 https://api.deepseek.com/anthropic ✅
  → 回滚脚本正常执行
  
Step 3: 确认直连 DeepSeek 是否可达
  → curl -sI https://api.deepseek.com/anthropic/v1/messages
  → HTTP 405 (HEAD 不支持, 但说明服务器可达) ✅
  → 排除网络整体故障
  
Step 4: 确认当前会话环境变量
  → echo $ANTHROPIC_BASE_URL
  → https://api.deepseek.com/anthropic ✅
  → 当前会话的环境变量已恢复(用户手动 export 的)
```

**结论**: 回滚成功, 服务恢复。问题出在代理自身。

### 6.2 为什么 curl 测试通过但 Claude 通不过

```
已知事实:
  A. curl → 代理 → DeepSeek → HTTP 200 ✅
  B. Claude → 代理 → DeepSeek → 连不上 ❌
  
假设 1: 代理在 curl 测试后崩溃了?
  验证: 查看代理日志 → 空 (Python stdout 缓冲导致)
  验证: ps 查看进程状态 → 进程在, 端口未监听
  → 部分支持: 代理确实有问题, 但不能解释 curl vs Claude 的差异

假设 2: Claude 的请求格式与 curl 不同?
  验证: Claude Code 使用 Node.js undici fetch()
        curl 使用 libcurl
  验证: Node.js fetch 默认 HTTP/2, 可能发送不同的请求格式
        Python http.server 只支持 HTTP/1.1
  → ✅ 这是根因!（2026-09-13 更正：此判断对明文链路不成立 —— undici 的 HTTP/2 依赖 TLS ALPN，`http://` 下仍是 HTTP/1.1，详见 §二 问题 2 的更正块）

关键证据: 
  - Python http.server.HTTPServer → 基于 TCPServer → HTTP/1.1 only
  - Node.js undici → HTTP/2 优先, 回退 HTTP/1.1
  - 两者握手时协议协商失败 → Claude 收到连接错误 → 重试 → 循环
```

### 6.3 Node.js 重写后的路径 bug

```
现象: Node.js 代理 → DeepSeek → HTTP 404

排查:
  Step 1: 确认代理代码正确
    → node --check → OK, 无语法错误

  Step 2: 测试代理基本功能
    → curl http://127.0.0.1:8787/ → "Authentication Fails (governor)"
    → 代理在运行, 且成功转发到了 DeepSeek (DeepSeek 返回了认证错误)
    
  Step 3: 完整 API 调用测试
    → curl -X POST ... /v1/messages → HTTP 404
    → 路径错误!

  Step 4: 追溯路径拼接
    → TARGET = https://api.deepseek.com/anthropic
    → Claude 发送: /v1/messages
    → 代理转发: api.deepseek.com/v1/messages (少了 /anthropic!)
    → DeepSeek: 404 (没有 /v1/messages, 只有 /anthropic/v1/messages)
    
  fix: path = TARGET_URL.pathname + req.url
       → /anthropic + /v1/messages = /anthropic/v1/messages ✅
```

### 6.4 后台进程测试反复超时

```
现象: node proxy.js & sleep 2; timeout 10 curl ... → 反复 exit 144

尝试1: 加 nohup → 仍然超时
尝试2: 输出重定向到文件 → 文件有内容(代理启动成功), curl 仍超时
尝试3: timeout curl ... | tail → 怀疑管道干扰 → 去掉 tail → 仍然超时
尝试4: 直接在 Node 内自测 → HTTP 200! 
       → 说明代理功能正常, 问题在 shell 进程管理

发现: timeout 命令在 Termux/PRoot 环境中对进程组的处理与标准 Linux 不同
      当 timeout 超时时, 它向整个进程组发 SIGTERM, 包括刚才 bg 的 node 进程

解决: 使用 Bash 工具的 run_in_background 功能独立启动代理,
      然后独立测试, 避免进程组干扰
```

> [!warning] 更正（2026-09-13）：同上 —— 「timeout 向整个进程组发 SIGTERM」缺机制支持；exit 144 不在 coreutils 定义的退出码表（124/125/126/127/137）内，不能作为证据。原始退出码与 `timeout --version` 需补录。

### 6.5 完整的排查方法论

```
┌─ 问题报告 ──────────────────────────────┐
│ "部署后连不上"                              │
└──────────────────────────────────────────┘
              │
              ▼
┌─ 三板斧: 先把服务恢复 ──────────────────┐
│ 1. 确认回滚脚本已执行                       │
│ 2. 确认配置文件已恢复                       │
│ 3. 确认直连可用                             │
│ → 服务恢复 ✅ (此时可从容排查根因)           │
└──────────────────────────────────────────┘
              │
              ▼
┌─ 隔离变量 ────────────────────────────┐
│ "curl 能通, Claude 不能通"                 │
│ → 差在哪? curl vs Claude                  │
│ → 协议栈不同: HTTP/1.1 vs HTTP/2          │
│ → 这就是根因                               │
└──────────────────────────────────────────┘
              │
              ▼
┌─ 最小验证 ────────────────────────────┐
│ 用同协议栈重写 → 验证 → 通过               │
│ → 确认根因分析正确                         │
└──────────────────────────────────────────┘
              │
              ▼
┌─ 回归测试 ────────────────────────────┐
│ 端到端 API 调用 → HTTP 200 ✅              │
│ shell 配置更新, 逃生通道保留                │
└──────────────────────────────────────────┘
```

## 七、关键经验

1. **代理测试必须用真实客户端协议栈** — curl ≠ Claude Code
2. **默认状态必须 fail-open** — 门控、限流首次启动不能阻塞
3. **PRoot 环境网络调优只能在应用层** — sysctl 不可用
4. **路径拼接是代理 bug 的第一来源** — 必须在设计阶段对齐三种路径
5. **逃生通道必须在部署前就绪** — 用户用回滚脚本几分钟内恢复服务
6. **Node.js 是同语言代理的最佳选择** — 与 Claude Code 同协议栈, 无兼容性问题

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | §二 问题 2 根因「undici 默认 HTTP/2 × Python 只支持 HTTP/1.1 → 协商失败」，§6.2 标注「✅ 这是根因!」 | 保留原表述并加更正：undici `allowH2` 需 TLS ALPN、`useH2c` 默认 false，明文 `http://127.0.0.1:8787` 无 ALPN，实际仍是 HTTP/1.1；降级为未验证假设，补 `curl --http1.1` / `--http2-prior-knowledge` 对照实验与「http.server 不支持流式/SSE」候选机制 |
| 纠错 | §二 问题 5 / §6.4「`timeout` 的 SIGTERM 波及整个进程组」以 exit 144 为证 | 保留原表述并加更正：coreutils 退出码为 124/125/126/127/137，144（128+16）不在其列；默认新建独立程序组，只有 `--foreground` 才共享；标为未验证，补 `timeout --version` 与原始退出码 |
| 加厚 | §二 问题 1 只有一句 `socket.setKeepAlive(true, 60000)` | 补内核默认值（7200 s / 75 s / 9 probes）与上界算式 `60+9×75 = 735 s ≈ 12.3 min`；指出 60 s 只是首个探测延迟，更快判死需应用层 `AbortSignal.timeout`；给 established 连接数回落验收判据 |
| 加厚 | §五「代理崩溃恢复｜未守护」只有一行三列 | 补 systemd user unit / tmux / nohup + 看门狗方案对照与 PRoot 取舍、`kill -9` 后 ≤10 s 重新监听 + curl 非 `000` 的验收判据、`Restart=always` 等 unit 要点 |
| 补疏漏 | §二 问题 3 的路径结论无官方出处 | 补 DeepSeek 官方 anthropic 接入页（`base_url` 带 `/anthropic` → 请求落到 `/anthropic/v1/messages`），结论不改 |

依据与索引：[[CORRECTIONS]] · [[AGENTS]]
