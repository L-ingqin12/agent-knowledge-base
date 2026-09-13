---
title: Claude Code auto-mode 分类器缓存分析（security monitor）
aliases: [分类器缓存, auto-mode classifier cache, security monitor 缓存]
tags: [ai/ops, ai/agent]
created: 2026-09-06
updated: 2026-09-13
status: review
---

# Claude Code auto-mode 分类器缓存分析

See also: [[Claude-Ops-KB-Home]] · [[claude-cache-relay-design]] · [[claude-deployment-record]] · [[claude-cache-optimization]]

> 背景：cache-relay 部署后命中率仍锁死在 ~52%（21:00-22:00：16.39M 命中 / 15.22M 未命中）。dump 定位到根因：两条「世系」在 DeepSeek 隐式前缀缓存里互相驱逐。

---

## 一、根因（dump 实证）

relay 的锚点 dump（`~/.cache-relay/dump.jsonl`，后已清除）抓到 5 条请求、**2 个唯一指纹**、交替出现：

| 指纹 | 类型 | tools | system |
|---|---|---|---|
| `b791e1f46fb6` | 主会话 | 45 个（含 13 个 `mcp__codebase-memory-mcp__*`） | "You are Claude Code..." |
| `effb55f14385` | **auto-mode 权限分类器** | 0 个 | "You are a security monitor for autonomous AI coding agents..." |

序列：`主会话 → 分类器 → 分类器 → 主会话 → 分类器`。两条世系前缀不同、交替送达 → DeepSeek byte-0 隐式缓存互相驱逐 → 命中率钉在 ~52%。

## 二、公开知识（分类器机制，来源见文末）

- **分类器是独立模型**：原生跑 **Sonnet 5**（即使主会话用别的模型）；分类器模型由 **Anthropic 服务端配置时优先**于该默认值，仅当会话模型为 Sonnet 4.6、或 `availableModels` 排除 Sonnet 5 时，才改用会话模型。独立模型 = 独立缓存命名空间，天然不与主会话互顶。
- **两阶段**：Stage 1 快速 yes/no（`max_tokens=64`+stop seq）；Stage 2 思考（仅 Stage 1 报警触发）。两者共享 system+transcript 前缀，Stage 2 命中 Stage 1 缓存。
- **缓存设计**：system prompt / CLAUDE.md / action blocks 用 `cache_control`（Anthropic 显式；**TTL 取值待证**，见下注）。
- **Tier 3 才过分类器**：shell、web fetch、外部工具、subagent 派生、项目外文件操作；项目内读写（Tier 1/2）不过分类器。
- **推理盲**：分类器只看 user 消息 + tool 调用，不看 assistant 正文和 tool 结果。
- `autoMode.classifyAllShell`（v2.1.193+）：把所有 shell 命令都送分类器（否则部分安全 shell 可跳过）。

> [!warning] 更正（2026-09-13）：分类器默认模型已由 **Sonnet 4.6 更新为 Sonnet 5**，且**服务端配置的模型优先**（原表述为「原生跑 **Sonnet 4.6**（即使主会话用别的模型）」，未提服务端优先）；「独立于主会话模型」的定性仍成立。
> 另：`cache_control` 的「1h TTL」**未取得一手文档佐证**，暂降级为待验证——可复核判据 = 抓请求体看 `cache_control` 是否含 `ttl` 字段及取值，并对照服务端返回的 cache 统计（原表述为「用 `cache_control`（Anthropic 显式，1h TTL）」）。
> 依据：https://code.claude.com/docs/en/permission-modes.md（核验于 2026-09-13）

## 三、为什么在 DeepSeek 链路上失效

| 环节 | 原生 Anthropic | 用户 DeepSeek 链路 |
|---|---|---|
| 分类器模型 | Sonnet 5（独立模型；服务端配置的模型优先） | deepseek-v4-pro（与主会话同模型 id） |
| 缓存隔离 | 不同模型 → 不同 cache 命名空间 | **不存在共享**：分类器 `tools=0`、主会话 `tools=39`，两条世系从第一个 token 就分叉，永不共享前缀（见 §五 订正） |
| 缓存标记 | `cache_control`（TTL 取值待证，见 §二 注） | relay `stripCacheControl` 剥掉 → 退回隐式前缀 |

**结论**：原生设计靠「不同模型 + cache_control」隔离分类器缓存；用户链路虽把两者都落在同一个 `deepseek-v4-pro`，但 DeepSeek 缓存是**前缀精确匹配**，分类器与主会话从第一个 token 即分叉，「两条世系互顶」不成立——~52% 的多因构成见 §五。

> [!warning] 更正（2026-09-13）：本表原行为「分类器模型 | Sonnet 4.6（独立模型）| deepseek-v4-pro（与主会话同模型）」与「缓存隔离 | 不同模型 → 不同 cache 命名空间 | 同模型 + 同 key → 共享一个缓存」，原结论为「用户链路把它俩拍扁成『同一个 deepseek-v4-pro + 隐式前缀』，于是两条世系互顶」。「路由到同一模型 id 就共享一个前缀缓存」的说法与 §五 订正矛盾（前缀从第一个 token 即分叉），故按 §五 口径重写本行。
> 依据：https://code.claude.com/docs/en/permission-modes.md（核验于 2026-09-13）

## 四、修复方向

1. **降分类器频率（配置层，零安全风险，优先）**：关 `autoMode.classifyAllShell` / 收窄 auto-mode 规则，减少 shell 命令触发分类器。coding agent shell 极高频，这是频率主因。
2. **relay 分流分类器到独立缓存（有安全折中）**：relay 识别「0 tools + system 含 `security monitor`」→ 改投独立上游（复用 GLM fallback）。恢复原生「独立缓存」隔离，主会话命中率应回 ~85%+。**代价**：分类器从 Sonnet 4.6（默认已为 Sonnet 5，见 §二 更正）降到 GLM，安全判断力下降——省钱 vs 安全的权衡，需用户拍板。
3. **修分类器报错**：`Request was aborted`（疑似 DeepSeek 400 内容审核，分类器 transcript 含敏感内容）→ 分流 GLM 或 sanitize。

## 五、结论一句话

⚠️ **2026-09-13 订正：本句「不是……是……」的排他性归因不成立。**

**「两条世系互相驱逐」在机制上不可能**：DeepSeek 缓存是**前缀精确匹配**，分类器发 `tools=0`、主会话发 `tools=39`，
**从第一个 token 就分叉，永远不可能共享前缀**，也就无从互相驱逐。

~52% 的真正构成是**多因叠加，不存在单一根因**：

1. **模型 ID 掉 `[1m]` 后缀致窗口静默 1M→200K**，compact 频率约 5.4 倍（2026-09-12 引入，见 [[2026-09-12-flash-migration-context-shrink-postmortem]]）；
2. `relocateVolatile` 把整段 system 搬出缓存前缀 ⇒ 每轮重算（见 [[claude-cache-relay-design]] §十一）；
3. **离散重置事件**（压缩 + 空闲过期）——占未命中 token 的 **83.1%**（实测 51 次 / 9.6M token）；
   其中**空闲过期在 ≤3 分钟间隔尺度上实测并不存在**（42 次请求 `cache_read` 单调增长、间隔 168.9s 命中率仍 99.0%）。

分类器仍是一条**独立且几乎不复用的谱系**，白加约 **26%** 请求量 —— 但那是**成本问题，不是互顶问题**。
逃生回滚导航侧已于 [[逃生回滚导航]] §四 同步（原待办：「`逃生回滚导航.md` 转引本结论处需一并订正。」）。

## 来源

- [Auto mode for Claude Code（官方博客）](https://claude.com/blog/auto-mode)
- [Configure auto mode（官方文档）](https://code.claude.com/docs/s/claude-code-auto-mode)
- [permission-modes.md（社区镜像）](https://github.com/ericbuess/claude-code-docs/blob/main/docs/permission-modes.md)
- [Claude Code 源码揭秘：2 阶段分类](https://cloud.tencent.cn/developer/article/2653444)
- [Simon Willison: Auto mode](https://simonwillison.net/2026/mar/24/auto-mode-for-claude-code/)

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §二/§三 把分类器默认模型写作 Sonnet 4.6，且未提服务端优先 | 更新为 **Sonnet 5** 并保留「服务端配置的模型优先」（仅会话模型为 Sonnet 4.6、或 `availableModels` 排除 Sonnet 5 时才改用会话模型）；原表述在更正块中保留；依据 permission-modes 文档 |
| 纠错 | §三 由「同模型 + 同 key → 共享一个缓存」推出「两条世系互顶」，与 §五 订正矛盾 | 按 §五 口径重写该行与结论：分类器 `tools=0`、主会话 `tools=39`，从第一个 token 即分叉，不存在共享前缀与互顶；未采用「路由到同一 deepseek 模型 id 导致共享」的说法 |
| 纠错 | §二「`cache_control`（Anthropic 显式，1h TTL）」不可核验 | 降级为待验证并给出可复核判据（抓请求体看 `ttl` 字段及取值 + 对照服务端 cache 统计）；未取得一手文档前不断言 TTL |
| 纠错 | §五 末句「`逃生回滚导航.md` 转引本结论处需一并订正」为过期待办 | 改为「已于 [[逃生回滚导航]] §四 同步」，原句以引文保留 |

回链：[[CORRECTIONS]] · [[AGENTS]]
