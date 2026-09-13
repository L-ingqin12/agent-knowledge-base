---
title: Claude Code 韧性代理 — 架构总览
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-06-12
updated: 2026-09-13
status: review
---

# Claude Code 韧性代理 — 架构总览

See also: [[Claude-Ops-KB-Home]] · [[claude-resilience-usage]] · [[claude-deployment-record]]

> 当前运行版本: Node.js 代理 + Permafrost 缓存层, 部署于 2026-06-12（现行链路 = 方案 C: CC → Permafrost :8788 → proxy :8787 → DeepSeek）
> 缓存优化方案详见: [claude-cache-optimization.md](claude-cache-optimization.md)

---

## 一、文件清单（按职能）

```
缓存优化层 (Permafrost)
├── ~/.claude/plugins/cache/permafrost/ ← permafrost v0.3.0 插件
└── ~/.permafrost/proxy.log             ← permafrost 运行日志

双层管理 (3 个)
├── /root/claude-permafrost-deploy.sh   ← 方案 B↔C 切换 (start/rollback/stop/status)
├── /root/claude-permafrost-rollback.sh ← 独立 C→B 逃生通道
└── /root/claude-cache-optimization.md  ← 缓存优化方案文档

底层代理 (3 个)
├── /root/claude-resilience-proxy.js    ← Node.js 韧性代理 (:8787)
├── /root/claude-resilience-deploy.sh   ← proxy 启停脚本 (历史兼容)
└── /root/claude-rollback.sh            ← 完全回滚到直连 DeepSeek

配置文件 (2 个)
├── /root/.zshrc (line 107)             ← ANTHROPIC_BASE_URL
└── /root/.bashrc (line 150)            ← ANTHROPIC_BASE_URL

运行时文件 (3 个，自动生成)
├── /root/.claude/proxy.pid             ← 代理进程 PID
├── /root/.claude/proxy.log             ← 代理运行日志
└── /root/.claude/resume-prompt-header.txt ← 中断恢复协议模板

文档 (GitHub, ~15 个)
└── /root/workspace/claude-code-knowledge/ → L-ingqin12/claude-code-knowledge
```

## 二、数据链路图

### 历史应急架构 (方案 B — 应急，proxy 不可用时降级链路)

```
Claude Code
  │  ANTHROPIC_BASE_URL = http://127.0.0.1:8788
  │  (从 settings.local.json 读取)
  ▼
Permafrost :8788 (Python)
  │  upstream = https://api.deepseek.com/anthropic
  │  ├─ 去 cache_control
  │  ├─ 工具排序
  │  ├─ env 冻结 + 增量
  │  └─ 规范 JSON 序列化
  ▼
api.deepseek.com/anthropic
```

### 目标架构 (方案 C — 双层生产)

```
Claude Code
  │  ANTHROPIC_BASE_URL = http://127.0.0.1:8788
  ▼
┌─────────────────────────────────────────┐
│  Permafrost :8788 (缓存对齐层)           │
│  upstream = http://127.0.0.1:8787       │
│                                         │
│  aggressive mode:                        │
│  ├─ 去 cache_control                    │
│  ├─ 工具按 name 排序                     │
│  ├─ env 块冻结 + 仅传增量               │
│  ├─ 规范 JSON 序列化                     │
│  ├─ 冷锚点合并 (并行子 agent 共享预热)    │
│  └─ 空闲保活 (opt-in)                    │
└────────────┬────────────────────────────┘
             │ http://127.0.0.1:8787
             ▼
┌─────────────────────────────────────────┐
│  claude-resilience-proxy.js (韧性层)     │
│  upstream = https://api.deepseek.com    │
│                                         │
│  ├─ 透明转发                             │
│  ├─ socket 错误自动重试 (3次, 1s/3s/8s)  │
│  └─ TCP keepalive (60s)                 │
└────────────┬────────────────────────────┘
             │ https://api.deepseek.com:443/anthropic/v1/messages
             ▼
┌─────────────────────────────────────────┐
│  api.deepseek.com (Anthropic 兼容层)     │
└─────────────────────────────────────────┘
```

> [!note] proxy 层位置注记: claude-resilience-proxy.js 位于 Permafrost 之后（:8787），CC 的请求先经 Permafrost :8788（缓存对齐）再转发至 proxy（韧性层），最后到 DeepSeek。

### 逃生路径

```
方案 C ──(proxy故障)──▶ 方案 B ──(permafrost故障)──▶ 直连 DeepSeek
  ↑                        ↑                          ↑
  deploy.sh start     deploy.sh rollback        claude-rollback.sh
```

## 三、部署运维

```bash
# 查看完整链路状态
bash /root/claude-permafrost-deploy.sh status

# 方案 C 部署 (permafrost → proxy → DeepSeek)
bash /root/claude-permafrost-deploy.sh start

# 方案 C→B 逃生 (绕过 proxy)
bash /root/claude-permafrost-deploy.sh rollback

# 完全回滚 (绕过所有代理)
bash /root/claude-rollback.sh

# 查看 permafrost 实时缓存命中率
curl -s http://127.0.0.1:8788/permafrost/stats | python3 -m json.tool
```

### 启停状态机

```
                        deploy.sh start
   ┌──────────┐ ──────────────────────────→ ┌──────────────┐
   │ 方案 B    │                              │ 方案 C        │
   │ pf → DS  │ ←────────────────────────── │ pf → px → DS │
   └──────────┘      deploy.sh rollback      └──────────────┘
        │                                           │
        └──────────── claude-rollback.sh ──────────▶ 直连 DS
```

## 四、错误处理路径

```
请求到达代理
     │
     ▼
  https.request → 成功? → pipe 响应 → Claude 收到 HTTP 200
     │
     ├─ socket 错误 → retry #1 (1s 后)
     │     ├─ 成功 → Claude HTTP 200
     │     └─ 失败 → retry #2 (3s 后)
     │           ├─ 成功 → Claude HTTP 200
     │           └─ 失败 → retry #3 (8s 后)
     │                 ├─ 成功 → Claude HTTP 200
     │                 └─ 失败 → Claude HTTP 502
     │                           │
     │                           ▼
     │                      Claude 显示错误
     │                      等待用户输入
     │                      (会话历史完整保留)
     │
     └─ 非socket错误 (4xx/5xx) → 直接转发给 Claude
```

> [!note] 补疏漏（2026-09-13）：流式响应（SSE）中途断流的续传语义
> 上图只覆盖 socket 错误重试与 4xx/5xx 转发，**未讨论响应已开始流出后中途断流**。客户端侧规则（官方 errors 参考页）：
> - 服务端错误 / 过载 / 超时只有**在 Claude 响应开始流出之前**才走完整重试预算；
> - 连接掉线若发生在**响应尚未产出时**（包括已开始流式输出文本），会**重发同一请求**；
> - 若发生在**思考完成之后、文本或工具调用开始之前**，最多**快速重发两次**，随后以 `Connection lost before a response was produced` 结束。
>
> 上游侧证据：DeepSeek 的 Anthropic 兼容端点上 stream 标为 **Fully Supported**。
> ⇒ **中继的重试语义必须与客户端重试规则对齐**，否则同一请求会被中继与客户端各重试一次，形成双重重试（重复计费 + 重复副作用）。
>
> 来源：<https://code.claude.com/docs/en/errors.md> · <https://api-docs.deepseek.com/guides/anthropic_api>

## 五、逃生通道

```
正常状态:         Claude → proxy → DeepSeek
                      
逃生触发:         bash /root/claude-rollback.sh
                     │
                     ├─ 杀掉代理进程
                     ├─ .zshrc → https://api.deepseek.com/anthropic
                     └─ .bashrc → https://api.deepseek.com/anthropic

逃生后:           Claude → DeepSeek (直连, 绕过代理)
                      
重新启用:         bash /root/claude-resilience-deploy.sh start
```

> [!warning] 更正（2026-09-13）：改 rc 文件对**已运行**的会话无效
> 上面 `claude-rollback.sh` 把 `.zshrc`/`.bashrc` 里的 `ANTHROPIC_BASE_URL` 改回直连后，**正在运行的 Claude Code 不会改道**——官方在 `CLAUDE_CODE_PROJECT_DIR_NAME` 一节明确 *Claude Code reads it once at startup from that environment*：环境变量在**进程启动时读取一次**。因此逃生脚本生效的前提是**重启会话**（不写这条会让人以为脚本一跑就恢复，实际仍在走故障链路）。
> 验证手段（要求把输出贴进部署记录）：① `echo $ANTHROPIC_BASE_URL`（新起 shell 读到的值）；② 直接看 proxy 日志**是否还有新请求**（无新请求才算真绕过）；③ `curl` 本地代理端口确认已无监听。
> 另注意：**登录 shell 与非登录 shell 读不同文件**，`.zshrc`/`.bashrc` 只改一个会出现「有的终端生效、有的没生效」。
>
> 来源：<https://code.claude.com/docs/en/sessions.md>

## 六、当前环境约束

| 约束 | 影响 | 缓解 |
|------|------|------|
| PRoot 无 sysctl | 内核 TCP keepalive 不可调 | 应用层 socket.setKeepAlive(60s) |
| 无 systemd | 代理不能自启/自恢复 | 手动 deploy.sh start |
| 移动网络 NAT 30-120s | 空闲连接易断 | 代理 keepalive + 重试 |
| Android 进程管理 | Termux 可能被杀 | 需 wake-lock + 电池白名单 (未部署) |

> [!warning] 更正（2026-09-13）：「无 systemd」不等于「只能手动」
> 上表「无 systemd → 代理不能自启/自恢复 → 缓解：**手动 deploy.sh start**」把唯一解写成人工，且与同库其他页面冲突（无人值守方案用会话内调度与后台保活，本页却回到人工）。可用替代：
> 1. 用会话内调度（`CronCreate` / `/loop`，见 [[claude-unattended-operation-plan]] §4）做**周期性健康探测并尝试重启**；
> 2. 把 proxy 进程纳入**同一套守护**（与后台会话/守护脚本一起拉起），而不是靠人记得；
> 3. 把「机器重启后代理不自启」列为**已知断点**写进部署记录。
>
> 又：上表末行「需 wake-lock + 电池白名单（**未部署**）」是**状态性描述**，必须带日期戳——否则半年后仍显示「未部署」而无法判断是否过期。截至 **2026-09-13 仍未部署**。
>
> 来源：<https://code.claude.com/docs/en/agent-view.md>

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 补疏漏 | §四 失败终态只到「Claude 显示错误」，无流式（SSE）中途断流的续传语义 | 补客户端重试分级规则（响应流出前走完整预算 / 已流出则重发 / 思考后至文本前最多快速重发两次）与「中继重试须与客户端对齐，否则双重重试」（errors 官方页 · DeepSeek 兼容页） |
| 加厚 | §五 逃生通道未说明改 rc 文件何时生效，也无验证命令 | 补「环境变量仅在进程启动时读取一次 ⇒ 必须重启会话」、三条验证手段与登录/非登录 shell 读不同文件的陷阱（sessions 官方页） |
| 纠错 | §六 约束表把「无 systemd」的唯一缓解写成手动重启，且「未部署」缺日期戳 | 补三条替代（会话内健康探测、纳入同一套守护、记入已知断点），并给未部署项加日期戳 2026-09-13 |

回链：[[CORRECTIONS]] · [[AGENTS]]
