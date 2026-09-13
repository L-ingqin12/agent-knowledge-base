---
title: Hermes 缓存分析 — 现状与优化方案
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-06-29
updated: 2026-09-13
status: review
---

# Hermes 缓存分析 — 现状与优化方案

See also: [[Claude-Ops-KB-Home]] · [[claude-cache-strategy]] · [[2026-06-24-hermes-feishu-outage-postmortem]]

> 分析日期: 2026-06-29 | 环境: Raspberry Pi 4B | Hermes 通过 model-router → ARK API

---

## 一、请求链路

```
┌─────────────────────────────────────────────────────────────┐
│                      Hermes 请求链路                          │
│                                                             │
│  Hermes Agent (gateway/ranzi)                               │
│      │                                                      │
│      ▼                                                      │
│  Model-Router (:18888)  ← 五层分级 (L1→L5)                  │
│      │                                                      │
│      ├── L1: doubao-seed-2-0-mini  ──┐                      │
│      ├── L2: doubao-seed-2-0-lite  ──┤                      │
│      ├── L3: deepseek-v4-flash     ──┤→ ARK API (直连)      │
│      ├── L4: deepseek-v4-pro       ──┤  ark.cn-beijing      │
│      └── L5: deepseek-v4-pro       ──┘  .volces.com         │
│                                                             │
│  ❌ 不经过 Permafrost (:8788) — 无缓存优化                    │
│  ❌ 不经过 Resilience Proxy (:8787) — 无重试/keepalive       │
│                                                             │
│  对比 Claude Code:                                           │
│  CC → Permafrost :8788 → Proxy :8787 → DeepSeek             │
│       (缓存对齐)        (韧性)                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、为什么 Hermes 没有缓存

### 2.1 架构差异

| 维度 | Claude Code | Hermes |
|------|:----------:|:------:|
| 模型调用路径 | CC → permafrost → proxy → DeepSeek | Hermes → model-router → ARK |
| 缓存对齐 | permafrost (去 cache_control + 工具排序 + currentDate 稳定化) | 无 |
| 网络韧性 | proxy (重试3次 + keepalive 60s) | model-router 内置降级链 |
| 工具集 | 9 锚点 + ScheduleWakeup 等变数工具 (CC 原生) | 27+ tools (Hermes 全功能) |
| 模型分层 | Pro/Flash (CC 内部) | L1-L5 (model-router 分类) |

> [!note] 口径注: 「keepalive 60s」为 TCP keepalive 内核参数；「45s」为应用层心跳间隔（MOC 口径），两层独立，勿混用。

> [!note] 补：L1–L5 判据与降级链（2026-09-13）
>
> | 判定 | 规则 | 命中层 |
> |---|---|---|
> | 关键词匹配 | L1/L2/L4/L5 各一组正则 | 对应层 |
> | 消息结构 | 连续 3 条短消息 | L1 |
> | Token 感知 | >50K tokens / >100K tokens | L4 / L5 |
> | 兜底 | 无命中 | L3（默认） |
>
> 降级链：`L1 → L2 → L3 → L4 → L5`（当前层模型不可用/限流时自动尝试下一层），判据明细见 [[hermes-session-optimization-report]] §2.2–2.3。
> 本文未附真实分类样本（输入消息 + 命中层 + 命中关键词）——库内无该记录，需从 model-router 日志补取。

### 2.2 核心障碍

**Permafrost 的 9 锚点工具是为 Claude Code 设计的**，Hermes 工具集完全不同：

```
CC 锚点工具:  Agent, AskUserQuestion, Bash, Edit, Read, Skill, 
              ToolSearch, Workflow, Write

Hermes 工具:  browser, clarify, code_execution, computer_use, context_engine,
              cronjob, delegation, file, image_gen, memory, messaging,
              session_search, skills, spotify, terminal, todo, tts, video,
              video_gen, vision, web, x_search, ...
```

如果 Hermes 直接接入 permafrost，`normalize_tools()` 会剥离 Hermes 的大部分工具 → 功能受损。

### 2.3 模型差异

Hermes L1/L2 使用 **doubao** 模型（火山引擎），不走 DeepSeek 缓存，天然无缓存收益。只有 L3/L4/L5 使用 deepseek 模型时才有缓存潜力。

当前统计（model-router stats）:
```
L1 (doubao-mini):  7 次   ← 无缓存可能
L2 (doubao-lite):  162 次 ← 无缓存可能
L3 (deepseek-flash): 0 次 ← 理论可缓存
L4 (deepseek-pro):   0 次 ← 理论可缓存
L5 (deepseek-pro):   0 次 ← 理论可缓存
```

> [!warning] 更正（2026-09-13）：上表是**单次抽样观察**（分析日 2026-06-29 读取），未记录统计起止时间、采集命令与原始输出，不足以单独支撑长期定量结论；复现前应补 stats 端点的原文输出与统计窗口。（原表述为「当前统计（model-router stats）:」，未标窗口）
>
> 口径澄清：本库 `scripts/claude-ops-deployments/patches/model_router.py`（109 行，`route_model()` / `get_session_stats()`）是 **permafrost 侧的 Flash/Pro 路由补丁**（由 `PERMAFROST_MODEL_ROUTING=1` 控制），**不是**本节的 Hermes L1–L5 路由器，勿混用。

**结论**: Hermes 当前几乎不使用 deepseek 模型，缓存优化的 ROI 极低。

---

## 三、优化方案

### 方案 A: 仅监控（推荐，已实施）

```
Hermes → model-router → ARK API (不变)
                │
                └── hermes-cache-monitor.sh (监控 permafrost + router)
```

- **成本**: 零（不改变架构）
- **收益**: 及时发现缓存/路由异常
- **适用**: 当前 Hermes 几乎不用 deepseek 的场景

### 方案 B: model-router 上游改为 permafrost

```
Hermes → model-router → permafrost :8788 → proxy :8787 → DeepSeek
```

- **优点**: L3/L4/L5 请求自动享受缓存
- **缺点**: 
  - permafrost 的 normalize_tools 会剥离 Hermes 非锚点工具 → **需要关闭 normalize_tools**
  - Hermes 和 CC 共享 permafrost → 不同工具集会破坏彼此的缓存锚点
  - 需要改造 permafrost 支持多租户（不同 session 使用不同锚点集）
- **风险**: 高 — 可能破坏 CC 缓存
- **建议**: 仅在 Hermes 大量使用 deepseek 模型时考虑

### 方案 C: Hermes 独立 permafrost 实例

```
Hermes → model-router → permafrost-hermes :8789 → DeepSeek
CC     → permafrost-cc :8788 → proxy :8787 → DeepSeek
```

- **优点**: 完全隔离，互不影响
- **缺点**: 
  - 双倍 permafrost 进程（~50MB 内存 × 2）
  - 需要配置 Hermes 专用锚点工具集
  - Hermes L1/L2 用 doubao 不走此路径
- **建议**: 仅在 Hermes deepseek 流量占比 >50% 时考虑

---

## 四、监控设置

### 4.1 缓存监控守护

```bash
# 手动检查
bash /home/pi/hermes-cache-monitor.sh once

# 后台守护 (每 60s 检查)
bash /home/pi/hermes-cache-monitor.sh daemon

# 查看状态
bash /home/pi/hermes-cache-monitor.sh status
```

### 4.2 监控阈值

| 指标 | 告警 | 触发 dump |
|------|:----:|:---------:|
| permafrost 命中率 | <75% | <60% |
| model-router 状态 | ≠ ok | ≠ ok |
| router 错误增量 | — | >5 |
| 前缀变化 | — | ≥2 |

### 4.3 与 CC 监控的关系

| 维度 | claude-cache-monitor.sh | hermes-cache-monitor.sh |
|------|:----------------------:|:-----------------------:|
| 监控对象 | permafrost 缓存命中率 | permafrost + model-router |
| 命中率 dump 阈值 | <70% | <60%（更宽松） |
| 独有功能 | proxy 502 检测 | router 健康检测 |
| 监控目录 | ~/.permafrost/monitor/ | ~/.hermes-cache/monitor/ |

---

## 五、DeepSeek 后台缓存检查

Hermes 的 L3/L4/L5 请求（deepseek 模型）在 DeepSeek 后台的理论缓存行为：

1. **前提**: 请求前缀 ≥ 64 tokens 且逐字节匹配
2. **实际**: Hermes 每次请求的 system prompt + tools 不同 → 前缀不匹配 → **缓存命中率 ~0%**
3. **验证方法**: 在 DeepSeek/ARK 后台按 API key 过滤，对比 CC 和 Hermes 的缓存命中率

> [!warning] 更正（2026-09-13）：第 1 条的「64 tokens」是缓存的**存储单位**（小于 64 token 的内容不被缓存），**不是**「命中所需的最小前缀」；命中口径的官方说法是「请求必须**完整匹配一个 cache prefix unit**」，「逐字节匹配」是转述而非原文。（原表述为「**前提**: 请求前缀 ≥ 64 tokens 且逐字节匹配」；64 这一数字保留，仅补出处与定性）
> 依据：https://api-docs.deepseek.com/news/news0802/（核验于 2026-09-13）
> 依据：https://api-docs.deepseek.com/guides/kv_cache（核验于 2026-09-13）

---

## 六、决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-06-29 | Hermes 不接入 permafrost | 工具集不兼容，且当前流量几乎全走 doubao |
| 2026-06-29 | 部署 hermes-cache-monitor.sh | 低成本监控，异常时及时感知 |
| 2026-06-29 | 方案 B/C 标记为「待评估」 | 等 Hermes deepseek 流量占比增加后再考虑 |

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §五 把 DeepSeek 缓存的 64 tokens 写成命中前提，并把命中口径写成「逐字节匹配」 | 保留原句并就地标注：64 tokens 是缓存**存储单位**（小于 64 token 的内容不被缓存），命中口径为「完整匹配一个 cache prefix unit」；出处见正文引用块（news0802 发布公告 / kv_cache 指南） |
| 补疏漏 | §2.3 stats 表（L1 7 / L2 162 / L3–L5 各 0）无统计窗口、采集命令与原始输出 | 降级为「2026-06-29 单次抽样观察」并写明复现要求；澄清库内同名 `patches/model_router.py` 是 permafrost 侧 Flash/Pro 路由补丁，不是 Hermes L1–L5 路由器 |
| 加厚 | §2.1 只写「L1-L5（model-router 分类）」，未给判据与降级链 | 补判据/命中层对照表 + 降级链，链至 [[hermes-session-optimization-report]] §2.2–2.3；未附分类样本的缺口如实标注 |

回链：[[CORRECTIONS]] · [[AGENTS]]
