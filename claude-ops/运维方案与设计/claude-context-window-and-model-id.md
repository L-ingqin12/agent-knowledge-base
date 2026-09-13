---
title: Claude Code 上下文窗口由模型 ID 决定（[1m] 后缀机制）
aliases: [context-window, 1m-suffix, auto-compact-threshold]
tags: [ai/ops, ai/agent]
created: 2026-09-13
updated: 2026-09-13
status: review
---

# Claude Code 上下文窗口由模型 ID 决定（[1m] 后缀机制）

See also: [[Claude-Ops-KB-Home]] · [[deepseek-cache-key-and-sep-experiments]] · [[claude-cache-relay-design]] · [[CORRECTIONS]]

> **一句话**：Claude Code **不问上游要窗口**，它在本地按**模型 ID 字符串**查表。认不出的 ID 一律按 **200K** 处理 ⇒
> auto-compact 会在 ~144K 就触发。给 ID 加 **`[1m]`** 后缀即切到 1M（阈值 ~784K）。**后缀在发包前被剥掉，不会上线路。**

## 一、解析链（反编译 `claude.exe` 实证）

```js
mu(e)   = { if (kO()) return false; return /\[1m\]/i.test(e) }   // 裸正则，无模型白名单
Yw(e,t) = { if (mu(e)) return 1e6; if (t?.includes(BA.header) && Ck(e)) return 1e6;
            if (gb(e)) return 1e6; … return S6e }                // S6e = 200000 硬默认
```

- `mu()` 是**裸正则**——`[1m]` 对**任意** ID 生效，不是第一方模型的专属语法。
- 旁路 `kO()` 读取 `CLAUDE_CODE_DISABLE_1M_CONTEXT`。
- **显式指定**：`CLAUDE_CODE_MAX_CONTEXT_TOKENS=<真实窗口>`（对非 `claude-` 前缀的 ID 生效）。这是比加后缀更直白的旋钮，Claude Code 自己的告警里也推荐它。

**认不出的 ID 会得到一句明确告警**（可据此自检）：

> `"<id>" is not a model this version of Claude Code recognizes, so auto-compact will keep this session within 200k tokens (the context window it assumes). If the model accepts more, append [1m] to the model name for 1M, or set CLAUDE_CODE_MAX_CONTEXT_TOKENS to its real window`

## 二、auto-compact 阈值公式

**不是按窗口的固定百分比**，而是：

```
阈值 ≈ 0.8 × (窗口 − min(maxOutputTokens, 20000))
```

| 窗口 | 阈值 |
|---|---|
| 200K | **~144K** |
| 1M | **~784K** |

常量来自二进制：`precomputeBufferFraction` 默认 `0.2`（另有 warn 线再低 20000、blocked 线为阈值−3000）。
可用 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 覆盖。

> ⚠️ **常见误记是「~92%」**。按 92% 会算出 184K / 920K —— **错的**。实测请以 144K / 784K 为准。

## 三、后缀不会上线路（受控 A/B 实证）

| 设置 | 请求体 `model` | `anthropic-beta` 含 `context-1m-2025-08-07` |
|---|---|---|
| `ANTHROPIC_MODEL=deepseek-flash` | `"deepseek-flash"` | **否** |
| `ANTHROPIC_MODEL=deepseek-flash[1m]` | `"deepseek-flash"` | **是** |

⇒ 后缀**纯粹是客户端标记**，发包前被剥离；上游收到的是干净 ID。**因此加后缀不会把畸形 ID 打到上游，是安全的。**
（relay 主路径对 `model` **原样透传**、不做校验或剥离，故中继侧也不受影响。）

## 四、事故：2026-09-12 flash 迁移丢了后缀

详见 [[2026-09-12-flash-migration-context-shrink-postmortem]]。要点：

`ANTHROPIC_MODEL` 由 `deepseek-v4-pro[1m]` 改成 `deepseek-flash` 时**丢了 `[1m]`**，窗口**静默**从 1M 掉到 200K，
compact 频率约 **5.4 倍**。**与上游模型能力无关**——DeepSeek 官方 Models & Pricing 页对 `deepseek-flash` 与
`deepseek-v4-pro` **都标 1M 上下文 / 384K 最大输出**，差异完全来自客户端那个字符串。

同时注意：迁移前 **subagent 与 haiku 两槽本就无 `[1m]`**（一直是 200K），即并发 subagent 长期按 200K 压缩。

**修复** = 五个槽位全部写 `deepseek-flash[1m]`，**且必须重启 Claude Code**（env 是进程级配置，启动时读取；不重启等于没改）。

## 五、实测收益（2026-09-13，relay 探针）

修复后单个会话连续 42 次主会话请求：`nMsgs` 187→310，**零次压缩**，上下文涨到 **~264K** 仍带
**97.6–99.2%** 命中率平稳运行。按旧的 200K 假设（阈值 ~144K）该会话早该被反复压缩。

## 六、自检方法

1. 启动后看有无 `unrecognized_model` 告警——有则说明该 ID 被按 200K 处理。
2. 查 `~/.claude/settings.json` 的五个槽位是否都带 `[1m]`（漏掉 subagent/haiku 两槽是常见疏漏）。
3. relay 侧开 `dump: true`，看**转发前**的 `model` 值是否被剥掉后缀（主路径不重映射，所见即所发）。

Related: [[deepseek-400-context-overflow-recovery]]、[[claude-cache-strategy]]
