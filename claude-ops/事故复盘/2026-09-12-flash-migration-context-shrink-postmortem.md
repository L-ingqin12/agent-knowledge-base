---
title: 事故复盘 — 2026-09-12 flash 迁移丢失 [1m] 后缀致窗口静默降级
aliases: [context-shrink, 1m-lost, flash-migration-incident]
tags: [ai/ops, incident]
created: 2026-09-13
updated: 2026-09-13
status: stable
---

# 事故复盘 — 2026-09-12 flash 迁移丢失 `[1m]` 后缀致窗口静默降级

See also: [[claude-context-window-and-model-id]] · [[deepseek-cache-key-and-sep-experiments]] · [[Claude-Ops-KB-Home]] · [[CORRECTIONS]]

## 一、现象

全模型切 flash 之后，会话 **compact 频率显著变高**；单个会话反复被压缩，长任务频繁被打断。
上游模型能力没有变化（同一端点、同样可达、价格更低），因此一度没有明确怀疑对象。

## 二、时间线

| 时间 | 事件 |
|---|---|
| 2026-09-12 | 全模型切 `deepseek-flash`：`~/.claude/settings.json` 五个槽位由 `deepseek-v4-pro[1m]` 改为 `deepseek-flash` |
| 2026-09-12 | 现场记录写下一句 **「`deepseek-flash` 模型 id 已实测 200」** —— 把「端点可达」当成了「能力保留」（见 §五错误链） |
| 2026-09-13 | 用户提出疑问：flash 与 pro **同为 1M 上下文**，为何 flash 的 compact 频繁得多？ |
| 2026-09-13 | 定位：改名时**丢了 `[1m]`**；反编译 `claude.exe` 确认解析链；受控 A/B 确认后缀不上线路 |
| 2026-09-13 | 修复：五槽位全改为 `deepseek-flash[1m]`，重启 Claude Code |

## 三、根因

**Claude Code 的上下文窗口由模型 ID 字符串在本地决定**（见 [[claude-context-window-and-model-id]]）。
`deepseek-flash` 不是它认识的 ID ⇒ 回落 **200K** ⇒ auto-compact 阈值 **~144K**。
迁移前是 `deepseek-v4-pro[1m]` ⇒ **1M** ⇒ 阈值 **~784K**。

**compact 频率差 ≈ 5.4 倍。与上游模型无关**——DeepSeek 官方页对 flash 与 pro **都标 1M 上下文**。

**这是一次「配置语义的静默降级」**：改名看起来只是替换模型名，实际上把一个**功能开关**（`[1m]`）
当作装饰性尾巴丢掉了。没有任何报错，只有行为变差。

## 四、影响面

- 主会话、opus/sonnet 槽：窗口 1M → 200K。
- **subagent 与 haiku 两槽在迁移前就已是 `deepseek-v4-flash`（无后缀）** ⇒ 它们**一直是 200K**，
  即**并发 subagent 长期按 200K 压缩**。排查时不要只盯主会话。
- 本机实测：修复后单会话连续 42 次请求，`nMsgs` 187→310、**零压缩**、上下文达 ~264K 仍维持 97.6–99.2% 命中率。

## 五、错误链（可复用）

1. **把「端点返回 200」当成「能力未变」** —— 请求成功只证明连通，不证明窗口、限额、语义未变。
   这与 [[CORRECTIONS]] C-009「把服务存在外推为效果出现」同族。
2. **把带语义的标记当装饰照抄** —— `[1m]` 被当作模型名的一部分复制，没有任何文档解释它是什么。
   这正是本次新增 [[claude-context-window-and-model-id]] 的直接动因。
3. **改配置时只逐一比对「值是否被替换」，没有比对「原值里的结构成分是否被保留」** ——
   迁移核查清单应包含「原值中是否有不含字母数字的语法标记」。

## 六、修复与验证

```
ANTHROPIC_MODEL            = deepseek-flash[1m]
ANTHROPIC_DEFAULT_OPUS_MODEL   = deepseek-flash[1m]
ANTHROPIC_DEFAULT_SONNET_MODEL = deepseek-flash[1m]
ANTHROPIC_DEFAULT_HAIKU_MODEL  = deepseek-flash[1m]
CLAUDE_CODE_SUBAGENT_MODEL     = deepseek-flash[1m]
```

**必须重启 Claude Code** —— env 是进程级配置，启动时读取；**不重启等于没改**。

**验证口径**：① 环境行显示 `deepseek-flash[1m]`；② 无 `unrecognized_model` 告警；
③ relay `dump` 显示转发前 `model` 为**不带后缀**的 `deepseek-flash`（证明后缀已剥、未污染上游）；
④ 长会话 `cache_read` 单调增长且**不再周期压缩**。

## 七、残留风险 / 未结

- **`[1m]` 是否随请求上线路** 曾一度存疑（二进制读到候选表把带后缀的排第一）。**已由 dump 实测裁定：不上线路。**
- Node 侧 `--profile` 曾被误当作性能剖析开关 —— 它其实是**配置档选择器**（`dsh --profile <name>`）。与本次事故无关，但同属「看名字猜语义」，记此备查。

Related: [[claude-cache-relay-design]]、[[claude-cache-strategy]]
