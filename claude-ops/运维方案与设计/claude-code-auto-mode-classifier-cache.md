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

> [!success] 残余复核（2026-09-13）：**「TTL 取值待证」已结案——不改语义、改为可证的精确表述：TTL 取值是条件式的 `1h` / `5m`，不是固定 `1h`。**
> 证据来自**第一方产物本身**（优于文档、且完全离线）：本机 Claude Code CLI 二进制 `claude.exe`（WinGet 安装，226MB Node SEA 包）内嵌 JS 实测——
> - **写入侧**：`function U1({scope:e,ttl:t}={}){return{type:"ephemeral",...t&&{ttl:t},...e==="global"&&{scope:e}}}`；调用处 `let Jt=B1(e.querySource)?"1h":void 0; … let rn=Jt?xt.map((Ht)=>hJe(Ht,Jt)):xt`，而 `function hJe(e,t){if(!("cache_control"in e)||!e.cache_control||e.cache_control.ttl)return e;return{...e,cache_control:{...e.cache_control,ttl:t}}}` ⇒ 只在 `cache_control` 已存在且**尚无 ttl** 时补写，**不会覆盖**已有取值。
> - **取值来源**：同一二进制内 `…prompt_cache_1h_config",{allowlist:[...DEe]}).allowlist??[],rTn(g);return LEe(e,g)?{ttl:"1h",reason:"subscriber"}:{ttl:"5m",reason:"default"}` ⇒ **`1h` 仅对「订阅者/命中 1h 白名单」成立，否则默认 `5m`**；`1h` 路径同时挂 beta 头 `PDe=Te("extended_cache_ttl","extended-cache-ttl-2025-04-11")`。
> - **附带**：CC 自身的 400 分类器把含 `\bttl\b` 的报错归为 `cache_control_field` 类（`Aie()` 内 `if(/\bttl\b/i.test(e))return!1`）⇒ 说明 `ttl` 字段是会被上游拒的敏感字段，这与本文链路的相关性见下。
> **对本篇结论的影响**：① §二 原「1h TTL」**只在订阅者场景对**，作为无条件陈述不成立——已按上表精确表述；② §三 表「`cache_control`（TTL 取值待证）」一行同理结案，可读作「`1h`（订阅者）/ `5m`（默认），二者均在 relay 被 `stripCacheControl` 整体剥离 ⇒ 到不了 DeepSeek」；③ 该 TTL 与 beta 头**在用户链路上被彻底剥离**，故对 ~52% 命中率的成因**无贡献**（与 §五 订正一致：成因是 ID 掉后缀、`relocateVolatile`、离散重置）。见 [[claude-cache-relay-design]]。

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

> [!success] 残余复核（2026-09-13）：**方向 2「需用户拍板」的现状已核实——代码早已就位，只差一个开关，决策点比原文更具体。**
> `cache-relay.mjs` 内分类器分流**已实现**：识别判据为「0 tools + system 含 `security monitor` + `autonomous`」，命中后按 `cfg.classifier.upstream || fallback.upstream` 改投、可配 `cfg.classifier.authToken` 与 `cfg.classifier.modelMap`，并打 `[cache-relay] classifier → … status=`；另有 `cfg.classifier.sessionIdSuffix` 改写分类器请求的 `x-claude-code-session-id`（将其会话与主会话分开）。
> **但 `%USERPROFILE%\.cache-relay\config.json` 实测 `classifier.enabled = false`（代码默认即关）** ⇒ 该分流**当前未生效**，主会话仍与分类器同源。
> 所以「需用户拍板」是**安全 vs 省钱的取舍决策**，不是待开发项：开启 = 改一个配置键（`enabled: true`；`modelMap` 与 `sessionIdSuffix` 实测均已就绪）。见 [[claude-cache-relay-design]]。
> **开启前须先解一处配置疑点（本次未定，勿盲开）**：`config.json` 未设 `classifier.upstream` ⇒ 现码会退回 `fallback.upstream`（OpenRouter），而 `classifier.modelMap` 实测把各模型映射到 **`deepseek-flash`**。「OpenRouter 上游 + `deepseek-flash` 模型 id」这一组合是否成立**未有证据**（OpenRouter 侧模型 id 通常带厂商前缀）。判据：开 `enabled: true` 后前台跑 relay，看 `[cache-relay] classifier → … status=` 是否非 2xx；或先直接查 OpenRouter `/api/v1/models` 有无该 id。

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

> [!success] 残余复核（2026-09-13）：**该待办已闭环，这次复核逐字核对确认。**
> `逃生回滚导航.md` §四 表格「分类器缓存 52% 根因 ⚠️**已订正**」行的现有文字为：「**原「两条世系互顶」不成立**：缓存是前缀精确匹配，分类器 `tools=0` 与主会话 `tools=39` **从第一个 token 就分叉**，不可能共享前缀、无从互相驱逐。实为多因叠加：…」——**转引口径与本文 §五 完全一致**，无残留旧结论。
> 故本条从待办转为**已同步**，无需再动 [[逃生回滚导航]]。复核方式：仓库内只读 `grep`，非抽样推断。

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
| 残余复核 | §二 注 / §三 表：`cache_control` 的「1h TTL」标为待证、无一手文档 | **结案并精确化**：第一方二进制 `claude.exe` 内嵌 JS 实测 TTL 为**条件式**——`U1({scope,ttl})` 产出 `{type:"ephemeral",ttl}`，写入方 `hJe` 仅在无 `ttl` 时补齐；取值解析处 `LEe(...)?{ttl:"1h",reason:"subscriber"}:{ttl:"5m",reason:"default"}` ⇒ **`1h` 仅订阅者/1h 白名单，默认 `5m`**，`1h` 挂 beta `extended-cache-ttl-2025-04-11`。故原「1h TTL」仅在订阅者场景成立。另：该字段与 beta 在链路被 `stripCacheControl` 整体剥离 ⇒ 对 ~52% 无贡献 |
| 残余复核 | §四 方向 2「分流分类器到独立缓存…需用户拍板」未记实现状态 | 核实**已实现但默认关**：现码含 `security monitor`+0 tools 识别、`classifier.upstream/authToken/modelMap/sessionIdSuffix`，配置实测 `classifier.enabled=false` ⇒ 决策是「翻一个键」而非待开发；同时记下一处未定疑点（`classifier.upstream` 缺省退到 OpenRouter 而 modelMap 指向 `deepseek-flash`，组合成立性无证据）+ 判据 |

回链：[[CORRECTIONS]] · [[AGENTS]]
