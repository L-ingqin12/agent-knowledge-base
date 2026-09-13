---
title: 终端崩溃改进方案 — 实施计划
aliases: []
tags: [ai/ops]
created: 2026-07-03
updated: 2026-09-13
status: deprecated
---

# 终端崩溃改进方案 — 实施计划

> [!warning] 此文档已废弃，请参考 [[subagent-resource-architecture-2026-07-03]]

See also: [[Claude-Ops-KB-Home]] · [[subagent-resource-architecture-2026-07-03]] · [[subagent-lessons-learned-2026-07-03]]

> 日期: 2026-07-03 | 来源: 多次 agent/subagent 终端崩溃事故分析
> 状态: 设计完成，待实施

---

## 背景

分析 7 起终端崩溃/卡死事故，分两类：

| 类型 | 占比 | 根因 | 故障域 |
|------|------|------|--------|
| A: 代理层单点故障 | 57% (4起) | proxy.js 被直接编辑、诊断代码混入控制流、竞态条件 | TCP/HTTP 代理 |
| B: Agent 资源耗尽 | 43% (3起) | fan out subagents 无并发限制、孤儿进程堆积、OOM | 进程/内存 |

详见 crash-analysis-2026-07-03（⚠️ 原记忆文档未随迁移入库，本库无等价文件，见 [[MEMORY-INDEX]]）

> [!warning] 补（2026-09-13）：上表的原始归类依据未入库，无法复核
> 百分比算术**无误**（4/7 = 57.1%、3/7 = 42.9%），但「哪 7 起、各自归哪一类、按什么判据归类」没有任何可复核材料（L30 已自曝原记忆文档未入库）。补一张**最小证据表**，否则后续事故无法沿用同一分类口径：
>
> | 日期 | 症状 | 关键日志片段 | 归类 | 判据（为什么算 A 而不是 B） |
> |------|------|--------------|------|------------------------------|
> | 待补 | 待补 | 待补 | A | 待补 |
> | …（共 7 行：A 类 4 行、B 类 3 行） | | | | |
>
> 填表纪律：**判据列不能空**——「A 是代理层单点故障、B 是资源耗尽」这条分界线只有写成可判定的条件（例如「崩溃点在 proxy.js 进程内 / 崩溃点为内核 OOM killer」），换个人才能得到同样的归类。

---

## Phase 1: Proxy 变更管控门禁

**依赖**: 无，可独立部署
**目标**: 防止 proxy.js 被直接在生产路径编辑

### 1.1 proxy.js 添加诊断代码隔离声明

- **文件**: `claude-resilience-proxy.js`
- **变更**: 文件头添加 `DO NOT ADD DIAGNOSTIC CODE HERE` 注释块
- **原则**: proxy.js 只做两件事 — 透明转发 + socket 重试

### 1.2 workspace→production 同步门禁 gate.sh

- **新建**: `deployments/proxy-gate/gate.sh`
- **子命令**:
  - `check` — 对比生产 vs 仓库 md5，不匹配则 WARN
  - `sync` — 备份 → 复制仓库版本到生产 → 更新 manifest
  - `guard` — SessionStart 用，静默 warn
- **新建**: `deployments/proxy-gate/rollback.sh`

### 1.3 Pre-commit Hook

- **新建**: `.githooks/pre-commit`
- **逻辑**: proxy.js 有变更时，检查 deploy.sh 存在 + 无诊断代码
- **配置**: `git config core.hooksPath .githooks`

### 1.4 SessionStart 集成

- **修改**: `claude-version-hook.sh` full() 中追加 `gate.sh guard`
- **特性**: 只读检测，失败不阻塞 session

### 验证

| 检查项 | 方法 |
|--------|------|
| 直接编辑 proxy.js 被检测 | `gate.sh check` 返回 WARN |
| workspace→生产同步 | `gate.sh sync` 后 md5 一致 |
| pre-commit 拦截 | 直接改 proxy.js `git commit` 被 hook 阻止 |
| 逃生回滚 | `rollback.sh` 恢复原文件 |

---

## Phase 2: Subagent 孤儿清理 + 并发限制

**依赖**: Phase 1 应先部署（避免混淆故障类型）
**目标**: 防止 agent 并发耗尽内存、孤儿堆积

### 2.1 agent-gate.sh

- **新建**: `/root/claude-agent-gate.sh`
- **子命令**:
  - `cleanup` — 清理孤儿 claude 进程（PPID=1 且运行 >5min）
  - `count` — 计数运行中 claude 进程（默认上限 5）
  - `memcheck` — 读取 `/proc/meminfo`（默认门槛 1GB 可用）
  - `check` — 组合：cleanup → count → memcheck，返回 OK/DENY

> [!warning] 补（2026-09-13）：`cleanup` 是**破坏性操作**，缺审计与演练设计
> 现方案的风险缓解只有「年龄过滤 >5min + PID 排除当前 session」两条，不够。按本库「部署四规则」的「日志可审计」，补三项：
> ①**`--dry-run`**：只列出「将杀哪些进程」及各自的命令行 / 启动时间 / 内存占用，人工确认后再真杀；
> ②**杀前日志**：把 PID / 命令 / 开始时间 / 内存落盘（可回查「当时为什么杀它」）；
> ③**多 session 排除清单**：只排除「当前 session」不够——fan-out 时**其它 session 的子代理**同样可能被 reparent 成 PPID=1 且已运行 >5min，会被误杀。排除清单应基于进程树/会话标识，而不是单看 PPID。
> 配套：`cleanup` 需要一条演练用例（起若干假孤儿 → dry-run 命中数 = 实际杀数）。

> [!warning] 补（2026-09-13）：`count` 的「默认上限 5」与 `memcheck` 的「默认门槛 1GB」都没有推导过程
> 需要补：①**设备规格**（Termux / PRoot 下可用内存总量是多少）；②**单个 subagent 峰值 RSS 实测**；③上限 5 的来历（例如 `5 × 峰值 RSS ≈ 可用内存 × 安全系数`，把安全系数写出来）；④阈值触发的**实测输出**（起 5+ 进程后 `check` 返回 `DENY` 的原文）。
> 没有这四项，这两个默认值换台机器就会失准，而失准的方向是**OOM**（门槛过高）或**误拒正常作业**（门槛过低）。

### 2.2 SessionStart 孤儿清理

- **修改**: `claude-version-hook.sh` full() 顶部追加 `agent-gate.sh cleanup`
- **特性**: 幂等，多次运行安全

### 2.3 资源指导注入

- **新建**: `/root/.claude/resource-guidance.txt`
- **内容**: delegate_task 前先跑 `agent-gate.sh check`，拒绝则降级为 Kanban

### 2.4 注册为 shell tool

- **修改**: `settings.local.json`
- **变更**: 添加 `agent-gate` tool，Claude 可在 spawn 前直接查询

### 验证

| 检查项 | 方法 |
|--------|------|
| 孤儿清理 | 后台起 claude，杀父进程，cleanup 清理孤儿 |
| 并发上限 | 起 5+ 进程，check 返回 DENY |
| 内存门槛 | 设低阈值，check 返回 DENY |
| SessionStart 自动清理 | session 启动前后 ps 对比 |

---

## Phase 3: 内存看守 + 长任务路由

**依赖**: Phase 2 (agent-gate.sh 可用)
**目标**: 内存自保 + 长任务走 Kanban 持久化

### 3.1 内存状态文件

- **新建**: `/root/.claude/memory.state`
- **更新**: 每次 `agent-gate.sh check` 写入 JSON（timestamp + mem_mb + status）
- **原则**: 无后台 daemon，按需写入

### 3.2 Kanban 路由助手

- **新建**: `/root/claude-kanban-helper.sh`（~50行）
- **功能**: `create`/`swarm`/`link` 薄封装 hermes kanban CLI
- **新建**: `/root/.claude/task-routing-guide.md`
  - delegate_task: 短任务(<50轮)、无需崩溃恢复、最大5并发
  - Kanban: 长任务(>50轮)、跨session、需要人工介入

### 验证

| 检查项 | 方法 |
|--------|------|
| Kanban helper 创建任务 | `kanban-helper.sh create "test" "desc"` |
| 路由指南可注入 | Claude session 询问路由决策规则 |

---

## 风险评估

| 变更 | 风险 | 缓解 |
|------|------|------|
| gate.sh sync | 复制错误文件 | sync 前创建时间戳备份，rollback 可用 |
| pre-commit hook | 拦截合法变更 | `git commit --no-verify` 可绕过 |
| SessionStart 集成 | hook 失败阻塞启动 | `|| true` 保底 |
| agent-gate cleanup | 误杀进程 | 年龄过滤 >5min + PID 排除当前 session |
| 并发检查 | spawn 时竞态窗口 | 非硬锁，checkpoint 式检查，窗口 <100ms |

> [!warning] 补（2026-09-13）：竞态窗口只给了量级，没给后果与兜底
> 补三项：①**窗口量级的来源**（`<100ms` 是怎么测出来的：两次 check 间隔的实测分布？还是估的？）；②**最坏情况的后果**（该窗口内最多可能超发几个进程——由 spawn 速率 × 窗口长度推算）；③**超发时的自动降级动作**（spawn 后自检发现超限 → 主动退出并记录，而不是等 OOM）与对应的日志字段。
> 没有第 ③ 项时，「窗口 <100ms」等于承认门禁可以被绕过而不留痕。

### 回滚策略

| 组件 | 回滚命令 |
|------|----------|
| Phase 1 (gate) | `bash deployments/proxy-gate/rollback.sh` |
| Phase 2 (agent-gate) | `rm /root/claude-agent-gate.sh` + 移除 hook |
| Phase 3 (Kanban) | `rm /root/claude-kanban-helper.sh /root/.claude/task-routing-guide.md` |

每阶段独立回滚，无跨阶段依赖。

> [!warning] 补（2026-09-13）：Phase 2 / 3 只有手工 `rm`，缺脚本、基线与验证方法
> Phase 1 有 `rollback.sh`，Phase 2 / 3 却只有一行 `rm` + 「移除 hook」，而「移除 hook」还要人工编辑 `settings.local.json`——这正是最容易改坏、最需要脚本的地方。按「部署四规则」的**逃生机制（rollback）**补齐：
> ①新增 `rollback-agent-gate.sh`（Phase 2）与 `rollback-kanban-helper.sh`（Phase 3），与 Phase 1 同级；
> ②`settings.local.json` **改前备份 + 改后 diff 校验**（回滚时按备份还原，而不是凭记忆删键）；
> ③**「怎么确认回滚成功」**：回滚后 `agent-gate.sh check` 不再被 session 调用、session 启动耗时回到基线（基线值需先记录）、`settings.local.json` 与备份 `diff` 为空。

---

## 文件清单

### 新建 (6 文件, ~340 行)

| 文件 | Phase | 行数 |
|------|-------|------|
| `deployments/proxy-gate/gate.sh` | 1 | ~80 |
| `deployments/proxy-gate/rollback.sh` | 1 | ~30 |
| `.githooks/pre-commit` | 1 | ~40 |
| `/root/claude-agent-gate.sh` | 2 | ~100 |
| `/root/.claude/task-routing-guide.md` | 3 | ~40 |
| `/root/claude-kanban-helper.sh` | 3 | ~50 |

### 修改 (3 文件)

| 文件 | Phase | 变更 |
|------|-------|------|
| `claude-resilience-proxy.js` | 1 | 添加诊断隔离声明注释 |
| `claude-version-hook.sh` | 2 | 追加 cleanup + guard 调用 |
| `/root/.claude/settings.local.json` | 2,3 | 注册 agent-gate tool + cleanup hook |

### 零外部依赖

仅使用: `bash`, `pgrep`/`pkill`, `/proc/meminfo`, `md5sum` (全在 PRoot/Android 环境已可用)

---

## 相关记忆

- claude-code-preflight-checklist（⚠️ 原文档未随迁移入库，见 [[MEMORY-INDEX]] 散落条目）— 行动前强制检查清单
- [[claude-socket-error-elimination-guide]] — 四层防御体系
- [[claude-interruption-resilience-guide]] — 中断恢复方案
- [[hermes-parallel-task-report]] — delegate_task vs Kanban 能力边界
- [[interactive-aware-subagent-plan-2026-07-03]] — Phase 2b: 交互感知动态资源分配（PreToolUse/Stop hook 状态机）
- [[resource-class-scheduling-plan-2026-07-03]] — Phase 2d: 资源类别感知调度（cpu/io/net/mem 文件锁 + wrapper 脚本）

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 补疏漏 | 「7 起事故分两类 57%(4起)/43%(3起)」的原始归类依据未入库，无法复核 | 百分比算术核对无误（4/7=57.1%、3/7=42.9%）；「背景」节补最小证据表模板（日期｜症状｜关键日志片段｜归类｜判据），并写明「判据列不能空」的填表纪律 |
| 补疏漏 | `cleanup`（PPID=1 且 >5min）作为破坏性操作缺审计与演练设计 | §2.1 补三项：`--dry-run` 只列不杀、杀前日志（PID/命令/开始时间/内存落盘）、多 session 排除清单（fan-out 时其它 session 子代理会被 reparent 误杀），并配演练用例 |
| 加厚 | `count` 默认上限 5、`memcheck` 默认门槛 1GB 没有推导过程 | §2.1 补四项：设备可用内存规格、单 subagent 峰值 RSS 实测、上限 5 的算式（含安全系数）、阈值触发的实测 DENY 原文 |
| 加厚 | 风险评估承认 spawn 竞态窗口 `<100ms` 却不给后果与兜底 | 「风险评估」表后补三项：窗口量级的测量来源、最坏情况最大超发数、超发时的自动降级动作（spawn 后自检超限即主动退出并记录）与日志字段 |
| 补疏漏 | 回滚策略表 Phase 2/3 只有手工 `rm`（Phase 1 有 `rollback.sh`），「移除 hook」需人工编辑 `settings.local.json`，无脚本、基线与验证方法 | 「回滚策略」后补三项：新增 Phase 2/3 rollback 脚本、`settings.local.json` 改前备份 + 改后 diff 校验、回滚成功的验证方法（check 不再被调用 / 启动耗时回基线 / diff 为空） |

回链：[[CORRECTIONS]] · [[AGENTS]]
