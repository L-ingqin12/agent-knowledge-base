---
title: Subagent 资源管理实施经验 (2026-07-03)
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-07-03
updated: 2026-09-13
status: stable
---

# Subagent 资源管理实施经验 (2026-07-03)

See also: [[Claude-Ops-KB-Home]] · [[subagent-resource-architecture-2026-07-03]] · [[resource-class-scheduling-plan-2026-07-03]]

> 从崩溃分析到三层防护体系落地的关键教训

---

## 1. 问题定性演变

| 阶段 | 认知 | 纠正 |
|------|------|------|
| 初判 | subagent 数量太多导致崩溃 | 数量是代理指标，真正原因是资源冲突 |
| 再判 | 应该限制并发数 | 静态限制太粗糙，需要感知交互状态 |
| 最终 | 交互感知 + 资源类调度的三层体系 | 数量门禁(L1) + 交互优先(L2) + 同类互斥(L3) |

核心教训：**不要用 proxy metric（数量）替代 root cause（资源冲突）**。

## 2. Hook 系统能力边界

| 能做到 | 不能做到 |
|--------|---------|
| 匹配工具名（Agent, Bash） | 读取工具参数（Bash 的命令行） |
| PreToolUse 同步执行 | 阻塞/取消工具执行 |
| PostToolUse 清理释放 | 获取 Claude 的"思考"状态 |
| Stop 检测空闲 | 检测用户正在输入 |

> [!warning] 更正（2026-09-13）：右列前两格与官方语义相反（原表述为上面表格右列第 1、2 行）
> - **「不能读取工具参数」是错的**。官方逐字：PreToolUse「Claude Code sends the tool input as **JSON on stdin** to the hook」，示例就是 Bash 的 `tool_input`（含 `command`）；官方示例脚本用 `COMMAND=$(jq -r '.tool_input.command')` 取值。`matcher` 只是 `settings.json` 里的**过滤字段**（纯工具名走精确匹配，含其它字符走 JS 非锚定正则），它限制的是「**何时触发**」，不是「hook 能读到什么」——「matcher 限制 stdin 字段」这一说法在本轮取证中为 NOT FOUND。
> - **「不能阻塞/取消工具执行」也是错的**。官方表逐字「| PreToolUse | Yes | **Blocks the tool call** |」，且「Exit 2 means a blocking error… even a JSON `permissionDecision` of allow can't override it」。**exit 2 是唯一仅凭退出码即可阻断的路径**（exit 1 等在多数事件上是 non-blocking）。
> - 依据：<https://code.claude.com/docs/en/hooks> · <https://code.claude.com/docs/en/hooks-guide>

> [!warning] 更正（2026-09-13）：核心教训的前提不成立，结论要改写（原表述为下一行）
> 上文两条「不能做到」既然是误读，「Hook 是 advisory 的，不是 enforcement 的」这个推论就随之作废。正确教训是：
> **matcher 只能匹配工具名，但 hook 能读 `tool_input` 并用 exit 2 强制阻断**——所以硬约束的**第一选择就是 hook**，不是文件锁。
> 文件锁的定位要收窄：它用于**跨进程互斥**（多个 session 争抢重资源），理由**不是**「因为 hook 不能 enforce」。
> 影响面提示：[[resource-class-scheduling-plan-2026-07-03]] 的 Layer 2「透明包装 Bash + spin-wait 取锁」正是建立在这个错误前提上的，而该 wrapper 在 Claude Code 里没有接入点（详见该文档的更正块）。

> [!warning] 补（2026-09-13）：hook 的失败/超时语义必须写进「能力边界」
> 对自建门禁而言，下面两条官方语义比「能做什么」更致命，此前完全缺失：
> ①**超时不阻断**：「A timed-out command, http, or mcp_tool hook **doesn't block** the tool call. The call continues through the normal permission flow, so **don't count on a stalled hook to act as a gate**.」
> ②**hook 起不来等于门禁静默失效**：路径写错（退出码 127）落进 non-blocking 桶——官方原文「a mistyped path in settings.json leaves the gate silently disabled」。
> 结论：本表应把这两条放在首位。另外 `command` / `http` / `mcp_tool` 的**默认 timeout 是 600 秒**（30 秒只适用于 `prompt` 类型），指望「30 秒兜底」也是误配。

核心教训：**Hook 是 advisory 的，不是 enforcement 的。硬约束靠文件锁 + 自旋等待。**

## 3. 快速路径设计

非 fan-out 模式（单 claude 进程）下，所有锁逻辑跳过。实现方式：

```bash
# agent-gate.sh acquire 第一行
total_procs=$(count_claude_procs)
[ "$total_procs" -le 1 ] && { echo "skipped (single)"; return 0; }
```

效果：非 subagent 场景零开销（~0.1s → ~0.01s）。

> [!warning] 补（2026-09-13）：上面那对数字缺测量口径（原表述为「~0.1s → ~0.01s」）
> 需要补：`time agent-gate.sh acquire cpu` 的**原始输出**、样本量（建议 ≥30 次取中位数）、机器规格，以及「是否把进程启动计入」。没有这些，「~0.1s → ~0.01s」无法被复核，也无法判断后续改动是否造成回归。
> 另一处措辞收紧：片段里 `return 0` 的注释是「# agent-gate.sh acquire 第一行」——**若 `acquire` 是函数，`return` 本来就是对的**，只有脚本顶层才需要改成 `exit 0`。所以这里**不是错误**，只是文档没写清上下文（该片段所处的函数/脚本边界），补一句说明即可。

核心教训：**优化常见路径。单 session 是常态，subagent 是少数。**

## 4. Bug 发现

| Bug | 原因 | 修复 |
|-----|------|------|
| lock_is_held 返回值语义反转 | `lock_is_held` 返回 0=free 但命名暗示 0=held | 统一为 bash 惯例: 0=held (true), 1=free (false) |
| interactive DENY 死循环 | PreToolUse→interactive→Agent check→DENY，用户请求的 spawn 也被拒 | 改为降并发上限，不拒绝 |
| check cooldown 过短 | 连续两次 check 间隔 <5s 被拒绝 | 这是设计意图，但需文档说明 |

## 5. 测试策略

回归测试套件 `tests/agent-gate-test.sh` 覆盖：
- Phase 2: cleanup, count, memcheck, status, check
- Phase 2b: mark-interactive/idle, read-state, prioritize, interactive 降并发
- Phase 2d: detect, acquire, release, lock-status
- 快速路径: 单进程零开销
- 语法和健壮性

**升级前必须跑这个套件。**

> [!warning] 补（2026-09-13）：只列了 Phase 编号，缺运行命令、通过判据与失败处置
> 补齐四项：①运行命令 `bash tests/agent-gate-test.sh`，并贴**实测输出**；②退出码约定 **0 = 全过**，非 0 即视为上线阻塞；③标明哪几项是**上线阻塞项**（`acquire`/`release` 互斥、快速路径、语法与健壮性），哪几项只是观察项；④失败处置：回滚到上一版 `agent-gate.sh`，并把失败用例登记到 [[CORRECTIONS]] 之外的测试记录里。
> 依据本库「部署四规则」（记录可追溯 · 部署前验证 · 逃生机制（rollback）· 日志可审计）——这份经验文档应当留下**可复制的验证记录**，而不只是套件清单。

## 6. 部署原则

1. 先在仓库编写测试 → 通过 → 用户确认 → 部署
2. 生产路径 `/root/claude-agent-gate.sh` 从仓库 `cp`
3. `settings.local.json` 手动合并 hook 配置
4. 部署后跑回归测试确认

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 纠错 | 「Hook 系统能力边界」表把「读取工具参数（Bash 的命令行）」列为不能做，与官方语义相反 | 保留原表并加更正块：PreToolUse 把 `tool_input` 以 JSON 放在 stdin，官方示例用 `jq -r '.tool_input.command'`；`matcher` 只决定何时触发，不限制 hook 能读到什么。依据 <https://code.claude.com/docs/en/hooks> · <https://code.claude.com/docs/en/hooks-guide> |
| 纠错 | 同表把「阻塞/取消工具执行」列为不能做，与官方 exit code 2 语义相反 | 更正块补官方表「PreToolUse → Yes → Blocks the tool call」与 exit 2 是唯一仅凭退出码阻断的路径 |
| 纠错 | 「核心教训：Hook 是 advisory 的，不是 enforcement 的。硬约束靠文件锁 + 自旋等待。」建立在前两条错误观察之上，并直接影响了后续架构 | 保留原句并加更正块：正确教训为「matcher 只能匹配工具名，但 hook 能读 `tool_input` 并用 exit 2 强制阻断」，硬约束第一选择是 hook；文件锁定位收窄为跨进程互斥；同时标注其对 [[resource-class-scheduling-plan-2026-07-03]] Layer 2 的影响 |
| 补疏漏 | 文档未记录 hook 的失败/超时语义 | 「能力边界」后补两条官方语义：超时的 command/http/mcp_tool hook **不阻断**；路径写错（127）导致门禁静默失效；并更正默认 timeout 为 600s（30s 仅 prompt 类型） |
| 加厚 | 「~0.1s → ~0.01s」没有测量方法 | §3 补测量口径（命令、原始输出、≥30 次取中位数、机器规格、是否含进程启动）；并把 `return 0` 一条收紧为「函数内正确、顶层才需 `exit 0`」的上下文说明，不判为错误 |
| 加厚 | 「测试策略」只列 Phase 编号，没有运行命令、通过判据与失败处置 | §5 补四项：`bash tests/agent-gate-test.sh` 运行命令与实测输出、退出码约定 0 = 全过、上线阻塞项清单、失败回滚处置 |

回链：[[CORRECTIONS]] · [[AGENTS]]
