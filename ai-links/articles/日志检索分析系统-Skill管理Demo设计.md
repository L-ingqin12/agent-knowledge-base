---
title: "日志检索分析系统——Skill 管理框架应用 Demo 设计"
aliases: [日志系统Skill Demo, Skill管理Demo, 日志检索Skills]
tags: [ai/skills, ai/learning]
created: 2026-06-22
updated: 2026-09-13
status: review
source: "系统设计"
date: "2026-06-22"
fetched_at: "2026-06-22"
---

# 日志检索分析系统——Skill 管理框架应用 Demo 设计

See also: [[AI-Links-KB-Home]] | [[Articles-Index]] | [[Agent驱动Skill迁移设计]] | [[Skill规模化管理-从渐进式披露到检索式发现]] | [[Claude-Code记忆机制源码拆解]]

## 背景

将 Skill 规模化管理框架（命名空间 + 依赖声明 + 条件匹配 + 检索式发现）应用到一个具体的大型系统上，验证框架在真实场景下的可用性。

> [!warning] 补（2026-09-13）：背景写了「验证框架在真实场景下的可用性」，但全文没有验收判据（原表述为上一句）
> 本文描述了目标架构与一个 skill 示例，却没有成功标准、评测集与退出条件——「可用性」因此**不可判定**。该补：
> - **≥N 个代表性任务清单**（覆盖 5 个命名空间，含正例与负例）。
> - **每个任务的期望被选中 skill 集合**（这是唯一能把「检索式发现」判对错的依据）。
> - **判定指标与通过阈值**：选对率、平均加载 token、级联深度、冲突触发次数。
> - **退出条件**：达到阈值即结束 Demo；未达到则记录失败任务与原因。
> 核对：审计括注的落盘位置经复核**确认存在**——`scripts/claude-ops-deployments/demos/logsystem/skills/{shared,queries,alerts,workflows,dashboards}` 已落盘，可直接作为评测集的实际载体。

选定场景：**大型日志检索分析系统**——天然具备多数据源、多查询模式、多分析工作流的特征，skill 数量可以轻松从几十增长到上百。

## 场景定义

```
系统规模：
  - 数据源：Elasticsearch（应用日志）、Loki（容器日志）、ClickHouse（指标）、Kafka（实时流）
  - 日均日志量：~50TB
  - 用户角色：SRE（全权限）、Dev（只读应用日志）、Sec（只读审计日志）
  - 预置查询模板：~60 个
  - 告警响应流程：~15 条
  - 分析 Workflow：~20 个（异常检测 / 根因分析 / 容量预测 / 告警关联）
```

## 目标 Skill 架构

### 命名空间划分

```
logs/
├── shared/                         # namespace: logs/shared
│   ├── es-query-builder/           # ES DSL 构建器（30+ skill 依赖它）
│   ├── loki-query-builder/         # Loki LogQL 构建器
│   ├── time-range-parser/          # 时间范围解析（"最近一小时"→timestamp）
│   ├── result-formatter/           # 结果格式化（table/json/csv）
│   └── auth-checker/               # 权限校验（SRE/Dev/Sec 角色映射）
│
├── queries/                        # namespace: logs/queries
│   ├── error-search/               # 错误日志搜索 → es-query-builder, time-range-parser
│   ├── trace-search/               # 链路追踪搜索 → es-query-builder
│   ├── container-log-search/       # 容器日志搜索 → loki-query-builder
│   ├── slow-query-search/          # 慢查询检测 → es-query-builder, result-formatter
│   ├── security-audit-search/      # 安全审计搜索 → es-query-builder, auth-checker
│   ├── app-log-search/             # 应用日志全量搜索
│   ├── metric-query/               # ClickHouse 指标查询
│   └── log-aggregation/            # 日志聚合统计
│
├── alerts/                         # namespace: logs/alerts
│   ├── k8s-oom-alert/              # K8s OOM 告警响应 → error-search, slow-query-search
│   ├── disk-full-alert/            # 磁盘满告警 → container-log-search
│   ├── spike-detection/            # 流量突增检测 → es-query-builder, result-formatter
│   ├── error-rate-alert/           # 错误率告警
│   ├── latency-alert/              # 延迟告警
│   └── cert-expiry-alert/          # 证书过期告警
│
├── workflows/                      # namespace: logs/workflows
│   ├── rca-pipeline/               # 根因分析 → error-search + trace-search + spike-detection
│   ├── capacity-forecast/          # 容量预测 → slow-query-search + result-formatter
│   ├── alert-correlation/          # 告警关联分析 → spike-detection + k8s-oom-alert
│   └── incident-report/            # 事故报告生成 → 多查询 + result-formatter
│
└── dashboards/                     # namespace: logs/dashboards
    ├── sre-overview/               # SRE 总览看板
    └── error-budget/               # 错误预算看板
```

### Demo 规模

25 个代表性 skill 覆盖 5 个命名空间：

| 命名空间 | Skill 数 | 示例 |
|---------|----------|------|
| `logs/shared` | 5 | es-query-builder, loki-query-builder, time-range-parser, result-formatter, auth-checker |
| `logs/queries` | 8 | error-search, trace-search, container-log-search, slow-query-search, security-audit-search, app-log-search, metric-query, log-aggregation |
| `logs/alerts` | 6 | k8s-oom-alert, disk-full-alert, spike-detection, error-rate-alert, latency-alert, cert-expiry-alert |
| `logs/workflows` | 4 | rca-pipeline, capacity-forecast, alert-correlation, incident-report |
| `logs/dashboards` | 2 | sre-overview, error-budget |

### 依赖关系（15 条 includes）

共享层被依赖：
- `es-query-builder` ← error-search, trace-search, slow-query-search, security-audit-search, spike-detection, rca-pipeline
- `loki-query-builder` ← container-log-search
- `time-range-parser` ← error-search, slow-query-search, metric-query
- `result-formatter` ← slow-query-search, spike-detection, capacity-forecast, incident-report
- `auth-checker` ← security-audit-search

工作流层跨命名空间依赖：
- `rca-pipeline` ← error-search + trace-search + spike-detection
- `alert-correlation` ← spike-detection + k8s-oom-alert
- `capacity-forecast` ← slow-query-search + result-formatter

> [!warning] 更正（2026-09-13）：标题的「15 条」只等于共享层之和，本节实列 22 条（原表述为标题里的 15）
> 逐条重算：
> - **共享层** 6 + 1 + 3 + 4 + 1 = **15** ✓（标题取的是这个数）
> - **工作流层** 3 + 2 + 2 = **7**
> - 本节合计 **22 条边**，标题的 15 只覆盖了不到一半。
> - 上面的命名空间树另声明了 **3 条**本节任何一行都没列出的边：`k8s-oom-alert → error-search`、`k8s-oom-alert → slow-query-search`、`disk-full-alert → container-log-search`。按树展开共 **25 条**。
> 因此「15」与本节内容、与架构树**三者不一致**。除非明确写出「只统计指向 shared 层的边」这类口径说明，否则标题应改为 **22**（或按树补齐后写 **25**）。
> 顺带一个口径细节：`capacity-forecast ← result-formatter` 与工作流层的 `result-formatter ← capacity-forecast` 是**同一条边**，只能计一次。

### Token 预算对比

| 方案 | System prompt 开销 | 节省 |
|------|-------------------|------|
| 全量列出（25 skill） | ~750 token | 基线 |
| 只列顶层入口 | ~200 token | 73% |
| 检索式发现（search_skills + 依赖级联） | ~30 token | 96% |

> [!note] 「只列顶层入口」的顶层集合口径 = workflows（4）+ alerts（6）两类入口；shared/queries 多为依赖目标，由 includes 级联加载，不占顶层名额。

> [!warning] 更正（2026-09-13）：本表三行口径不同却被并列，且单价不自洽（原表述为上面整张表）
> 算术核对：25 个 skill → ~750 token，即 **30 token/skill**；顶层 10 个入口（workflows 4 + alerts 6）→ ~200 token，即 **20 token/入口**。同一批 `name + description` 出现**两种单价**，说明两行的统计文本不是一个口径。
> 更关键的**语义**问题：「检索式发现 ~30 token，节省 96%」只是**发现索引的开销**——skill 被激活后，`SKILL.md` 全文**仍要进上下文**。所以 96% 是「**索引开销**的节省」，不是「**总上下文**的节省」。
> 该补三列：**tokenizer 名称**（cl100k / o200k / 其它）、**被统计的确切文本**（只有 `name` + `description`，还是含 paths / frontmatter）、以及**「激活后总上下文」**（发现索引 + 级联加载的 SKILL.md 全文之和）。没有这三列，73% / 96% 无法复核。

## Skill 示例：rca-pipeline 的完整声明

```yaml
---
name: rca-pipeline
description: 根因分析流水线——自动关联错误日志、调用链和异常指标，定位根因
namespace: logs/workflows
paths:
  - "**/incidents/**"
  - "**/postmortems/**"
includes:
  - error-search
  - trace-search
  - spike-detection
optional_includes:
  - incident-report
conflicts:
  - alert-correlation
---

# 根因分析流水线

## 触发条件
- 告警升级为 incident
- 手动触发 "/rca <incident-id>"

## 流程
1. 根据 incident 时间窗口，调用 error-search 提取异常日志
2. 对异常日志中的 trace_id，调用 trace-search 还原调用链
3. 调用 spike-detection 检查关联指标是否异常
4. 输出：根因定位报告（含置信度）

## 输出格式
table: timestamp | service | error_type | root_cause_candidate | confidence
```

## 与 Skill 管理框架的对应

| 框架组件 | 日志系统中的落点 |
|---------|----------------|
| 命名空间隔离 | `logs/shared` / `logs/queries` / `logs/alerts` / `logs/workflows` / `logs/dashboards` |
| 依赖链级联 | rca-pipeline → 自动加载 error-search + trace-search + spike-detection |
| paths 条件匹配 | `security-audit-search` 的 paths: `["**/audit/**", "**/auth.log"]` |
| conflicts 互斥 | `rca-pipeline` 和 `alert-correlation` 互斥（避免同时排查两条线索） |
| 检索式发现 | search_skills("K8s 集群 Pod 频繁重启") → [container-log-search, k8s-oom-alert, rca-pipeline] |
| Stale 管理 | ES 版本升级后 `es-query-builder` 标记 stale，提示 review |

> [!warning] 补（2026-09-13）：`conflicts` 只声明了互斥，没定义冲突发生时的行为（原表述为表中「conflicts 互斥」这一行）
> 是**硬报错**、按 namespace 优先级**择一**、还是**串行化**，三种都没定义，也没有验证用例。该补一张「冲突处理表」与一条负向测试：
>
> | 冲突对 | 检测时机 | 处置 | 用户可见提示 |
> |--------|----------|------|--------------|
> | `rca-pipeline` ↔ `alert-correlation` | 第二个 skill 被匹配到时 | 待定（硬报错 / 取 namespace 优先级高者 / 串行） | 待定 |
>
> 负向测试：同时命中两个互斥 skill → 期望行为必须**唯一且可观测**（例如「后加载者被拒绝 + 明确提示原因」），而不是静默把两个都装上。

## 权限维度的命名空间交叉

日志系统有一个通用 Skill 框架未覆盖的维度：**权限**。不同角色的用户能访问的 skill 不同：

| 角色 | 可访问的命名空间 | 限制 |
|------|---------------|------|
| SRE | 全部 | 无限制 |
| Dev | queries/（不含 security-audit-search） | auth-checker 拦截 |
| Sec | queries/security-audit-search | 仅审计相关 |

`auth-checker` 作为 shared 层 skill，在 queries/workflows/alerts 等 skill 的 `includes` 中被声明——每次数据访问前先过权限。

> [!warning] 补（2026-09-13）：这句话读起来像机制，实际只是一条声明（原表述为上一句）
> 缺的是：**谁在何时调用 auth-checker**（LLM 自觉调用，还是运行时强制）、**拒绝后的行为**、**越权尝试的日志与告警**、以及**验证方法**（以 Dev 身份请求 `security-audit-search` 必须被拒）。
> 「在 `includes` 中被声明」只是**提示 LLM 去加载**，不等于强制——这正是「**把声明当机制**」的典型风险。安全边界必须落在运行时，不能靠 prompt 约定。

## Demo 文件结构

以下为目标结构（规划稿），实际落盘见 scripts/claude-ops-deployments/demos/logsystem/skills/ 的 `<namespace>/<name>/SKILL.md` 三层结构：

```
scripts/migration/demo-old-system/
├── shared/
│   ├── es-query-builder.md
│   ├── loki-query-builder.md
│   ├── time-range-parser.md
│   ├── result-formatter.md
│   └── auth-checker.md
├── queries/
│   ├── error-search.md
│   ├── trace-search.md
│   ├── container-log-search.md
│   ├── slow-query-search.md
│   ├── security-audit-search.md
│   ├── app-log-search.md
│   ├── metric-query.md
│   └── log-aggregation.md
├── alerts/
│   ├── k8s-oom-alert.md
│   ├── disk-full-alert.md
│   ├── spike-detection.md
│   ├── error-rate-alert.md
│   ├── latency-alert.md
│   └── cert-expiry-alert.md
├── workflows/
│   ├── rca-pipeline.md
│   ├── capacity-forecast.md
│   ├── alert-correlation.md
│   └── incident-report.md
├── dashboards/
│   ├── sre-overview.md
│   └── error-budget.md
└── registry.json    # Skill Registry 索引（MEMORY.md 风格）
```

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 纠错 | 「依赖关系（15 条 includes）」的 15 只等于共享层 5 组之和，加上工作流层 3 组应为 22，命名空间树里还有 3 条未计入的入边 | 保留标题与条目并加更正块：共享层 6+1+3+4+1=15、工作流层 3+2+2=7 ⇒ 本节 22 条边，按树展开共 25 条；要求写明统计口径或改标题数字，并指出 `capacity-forecast ↔ result-formatter` 是同一条边 |
| 纠错 | Token 预算对比表三行口径不同却被并列，单价不自洽（750/25=30 vs 200/10=20），且 96% 只是索引开销的节省 | 加更正块：指出两种单价共存；明确「激活后 SKILL.md 全文仍进上下文」；要求补 tokenizer 名称、被统计的确切文本、「激活后总上下文」三列 |
| 补疏漏 | 背景写「验证框架在真实场景下的可用性」，但全文没有验收判据 | 「背景」节补评测集与判据四项（≥N 任务清单、每任务期望 skill 集合、指标与阈值、退出条件），并核对落盘位置 `scripts/claude-ops-deployments/demos/logsystem/skills/` 确实存在，可作为评测集载体 |
| 加厚 | `auth-checker`「在 includes 中被声明——每次数据访问前先过权限」只给了角色表，没给机制 | 「权限维度」节补四点：谁在何时调用、拒绝后的行为、越权尝试的日志与告警、验证方法（Dev 请求 security-audit-search 必须被拒）；点明「声明 ≠ 强制」 |
| 加厚 | `conflicts` 只声明了互斥，未定义冲突发生时的行为 | 「与 Skill 管理框架的对应」表后补「冲突处理表」模板（冲突对｜检测时机｜处置｜用户可见提示）与一条负向测试要求 |

回链：[[CORRECTIONS]] · [[AGENTS]]
