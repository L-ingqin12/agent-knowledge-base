---
title: Hermes 会话优化与模型调度系统报告
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-06-16
updated: 2026-09-13
status: review
---

# Hermes 会话优化与模型调度系统报告

See also: [[Claude-Ops-KB-Home]] · [[hermes-parallel-task-report]] · [[2026-06-24-hermes-feishu-outage-postmortem]]

> 分析日期: 2026-06-16  
> 环境: Raspberry Pi 4B (raspberrypi, aarch64, Debian)  
> 关联: 巨型会话拆解 → 调度系统修复 → 会话策略优化

---

## 一、故障诊断与修复

### 1.1 模型路由器死循环 (已修复)

**根因**: `model_router.py` 在 `main()` 中读取 `config["model"]["base_url"]` 作为上游地址，但该字段已被配成 `http://127.0.0.1:18888/v1` (指向路由器自己)，导致无限循环转发 → 超时 → 502。

```
修复前: Hermes → :18888 router → 读 config → base_url=:18888 → 自己 ↻ 超时
修复后: Hermes → :18888 router → --upstream ARK API → 正常响应
```

**修复内容**:
- v2: 添加 `--upstream` 参数，默认值 `https://ark.cn-beijing.volces.com/api/coding/v3`
- v3: 流式转发 + 故障降级链 + token 感知分类 + 超大会话拒绝保护
- systemd service 持久化，`--upstream` 参数写入 service 文件

### 1.2 systemd 端口冲突 (已修复)

手动 `nohup` 启动的进程与 systemd service 争抢 `:18888`。修复：统一切换到 systemd 管理。

---

## 二、模型调度系统 v3 架构

### 2.1 五层分级

```
L1 迷你: doubao-seed-2-0-mini   → 问候、状态查询、简短确认
L2 轻量: doubao-seed-2-0-lite   → 文件读取、简单命令、列表
L3 标准: deepseek-v4-flash      → 日常编码、工具调用 (默认)
L4 复杂: deepseek-v4-pro        → 多步推理、架构设计、重构
L5 专家: deepseek-v4-pro        → 安全审计、深度调试
```

### 2.2 分类方法

- **关键词匹配** (L1/L2/L4/L5 各一组正则)
- **消息结构分析**: 连续 3 条短消息 → L1; 长上下文 → 升级
- **Token 感知**: >50K tokens → L4; >100K tokens → L5
- **默认 L3** (标准级)

### 2.3 故障降级链

```
L1 → L2 → L3 → L4 → L5
(若当前层模型不可用/限流, 自动尝试下一层)
```

> [!note] 补：降级的可观测条件与未测项（2026-09-13）
> - **可观测出口**：`GET /stats` 的「分层调用统计 + 降级次数 + 错误数 + 最近记录」（见 §2.5）是本链唯一判读入口；触发条件即「当前层模型不可用/限流」。
> - **降级时是否保留 messages**：本文未记录，**未实测**；换层即换模型 id，原前缀能否继续命中官方未作说明、库内亦无实测——降级后的命中率与 token 成本变化需实测后才能下结论。
> 依据：https://api-docs.deepseek.com/guides/kv_cache（核验于 2026-09-13）

### 2.4 超大会话保护

```python
MAX_SESSION_TOKENS = 150000  # 超过此值直接返回 HTTP 413
```

### 2.5 监控端点

| 端点 | 功能 |
|------|------|
| `GET /health` | 健康检查 + 版本号 |
| `GET /stats` | 分层调用统计 + 降级次数 + 错误数 + 最近记录 |
| `GET /config` | 当前分层配置 + 降级链 |
| `PUT /feedback` | 接收 token 消耗反馈 (由 token_feedback.py 调用) |

---

## 三、会话优化策略 (五层防御)

### 3.1 策略总览

```
第 1 层 — 压缩提前触发
  model.context_length: auto(1M) → 131072
  compression.threshold:   0.5 → 0.35    → 触发点: 500K → 45K tokens
  compression.target_ratio: 0.2 → 0.12   → 压缩后: 200K → 15K tokens

第 2 层 — 硬限制
  hygiene_hard_message_limit: 800 → 120

第 3 层 — 会话生命周期
  session_reset:         none → daily
  max_turns:             150 → 100
  gateway_auto_continue_freshness: 3600 → 300 (5 min)

第 4 层 — 网关保护
  gateway_timeout: 1800 → 900 (15 min)
  router MAX_SESSION_TOKENS: 150000 (HTTP 413)

第 5 层 — 定时清理
  cron: 每天 03:30 → sessions prune --older-than 7 + optimize
```

### 3.2 关键指标对比

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 压缩触发 tokens | ~500,000 | ~45,875 |
| 压缩后 tokens | ~200,000 | ~15,728 |
| 单会话最大消息数 | 800 | 120 |
| 会话最长生命周期 | 无限制 | 每日重置 |
| 空闲续约窗口 | 1 小时 | 5 分钟 |
| 网关超时 | 30 分钟 | 15 分钟 |
| 路由器 token 上限 | 无 | 150,000 |

> [!warning] 更正（2026-09-13）：「~45,875 / ~15,728」不是实测值，而是**按配置推算**：`context_length 131072 × threshold 0.35 = 45,875.2`、`131072 × target_ratio 0.12 = 15,728.64`（配置见 §3.1）；「优化前 ~500,000 / ~200,000」同法来自旧配置（1M × 0.5 / 1M × 0.2）。表中其余行（消息数、生命周期、续约窗口、超时、token 上限）是配置值本身，可直接核。实测口径需另附 `state.db` / 日志查询语句与样本窗口，当前缺失。（原表述为上表「压缩触发 tokens / 压缩后 tokens」两行，未区分观测与推算）

### 3.3 记忆系统不受影响

会话优化措施仅作用于会话消息存储 (`state.db`) 和会话生命周期，不触及持久记忆系统 (`~/.hermes/memories/`):

- 记忆通过 system prompt 独立注入，与当前会话大小无关
- `hermes sessions prune` 只清理 state.db 中的会话行
- `compression` 只压缩会话消息，不碰 memories 文件
- 新建会话后记忆知识仍然加载

---

## 四、已归档会话

巨型会话 `20260614_210340_28ae3ca6` (586 条消息, ~232K tokens) 已重命名为 `[DONE] 模型调度系统构建完成` 并归档。

该会话经历了 5 次 gateway 重启中断，每次自动续约重新加载上下文导致大量 token 浪费。优化后的配置可防止此类情况再次发生。

---

## 五、运行状态

| 组件 | 状态 |
|------|------|
| model-router v3 (systemd) | ✅ active, :18888 |
| hermes-gateway (default) + feishu | ✅ connected |
| hermes-gateway-ranzi | ✅ active |
| session-cleanup cron | ✅ 每天 03:30 |
| kanban dispatcher | ✅ 每 60s |

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §3.2 指标对比表把 45,875 / 15,728 与「~500,000 / ~200,000」并列，未区分实测与推算 | 就地标注为**配置推算值**（131072 × 0.35 = 45,875.2；131072 × 0.12 = 15,728.64，配置见 §3.1），并说明优化前两数同法来自旧配置（1M × 0.5 / 1M × 0.2）；实测口径待补 `state.db`/日志查询与样本窗口 |
| 补疏漏 | §2.3 降级链无并发/降级行为实测，未说明是否保留 messages、是否打断进行中的会话 | 补「可观测出口 = `GET /stats` 的分层统计与降级次数」+ 两项未测项（换模型后原前缀能否继续命中、降级后命中率与 token 成本变化），依据 kv_cache 指南口径，缺口如实标注为未实测 |

回链：[[CORRECTIONS]] · [[AGENTS]]
