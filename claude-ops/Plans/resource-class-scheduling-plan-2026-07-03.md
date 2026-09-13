---
title: Phase 2d: 资源类别感知调度方案
aliases: []
tags: [ai/ops]
created: 2026-07-03
updated: 2026-09-13
status: deprecated
---

# Phase 2d: 资源类别感知调度方案

> [!warning] 此文档已废弃，请参考 [[subagent-resource-architecture-2026-07-03]]

See also: [[Claude-Ops-KB-Home]] · [[subagent-resource-architecture-2026-07-03]] · [[interactive-aware-subagent-plan-2026-07-03]]

> 日期: 2026-07-03 | 状态: 设计完成，待实施
> 依赖: Phase 2 (agent-gate.sh) 必须存在
> 定位: Phase 2d — 独立于 2b 的正交扩展

---

## 问题定性

subagent 数量只是代理指标。真正原因是**高资源消耗操作的并发冲突**：

- 2 个 subagent 同时 `npm install` → CPU+IO 尖峰 → 终端崩溃
- 1 个 subagent `grep -r /` + 另一个大文件分析 → IO 竞争 → OOM
- 5 个 subagent 只读文件/写编辑 → 完全正常

**本质是资源调度问题，不是数量问题。**

---

## 关键发现：Hook 限制

Claude Code PreToolUse hook 的 `matcher` 只匹配**工具名**（如 "Bash"），无法读取命令参数。因此**不能在 hook 内做命令模式匹配**。

解决方案分两层：
- **Layer 1 (Agent hook)**：spawn 前检查资源锁状态，冲突则 DENY
- **Layer 2 (Wrapper脚本)**：透明包装 Bash，spin-wait 获取锁后执行原命令

> [!warning] 更正（2026-09-13）：上面第 1 段是误读，Layer 2 Wrapper 的立论不成立（原表述为「`matcher` 只匹配工具名…无法读取命令参数。因此不能在 hook 内做命令模式匹配」）
> hook **从 stdin 拿到 `tool_input.command`**——官方逐字「Claude Code sends the tool input as JSON on stdin to the hook」，官方示例脚本即 `COMMAND=$(jq -r '.tool_input.command')`。因此**完全可以在 hook 内做命令模式匹配，并以 exit 2 阻断**。`matcher` 限制的是「**何时触发**」，不是「hook 能读到什么」。
> **正确的最小实现（替代 Layer 2）**：PreToolUse hook 读 stdin → 匹配 `resource-patterns.conf` → 命中则 `acquire` 锁；**取不到锁就 `exit 2`（在 stderr 携带原因）**，无需包装 Bash。
> 附带问题：原 wrapper 里的 `eval "$*"` 会丢失原始引号与重定向语义，本来就构不成「透明包装」。
> 结论：Layer 1 的方向正确（实现载体改为 PreToolUse hook，而非只匹配 Agent 工具）；**Layer 2 应作废**，其职责并入 Layer 1。
> 依据：<https://code.claude.com/docs/en/hooks>

---

## 资源类别

| 类别 | 示例 | 并发限制 |
|------|------|---------|
| `cpu` | npm install, cmake, gcc, pip install | 互斥 (1) |
| `io` | grep -r /, find /, rsync, tar | 互斥 (1) |
| `net` | curl -O, wget, git clone | 最大 2 |
| `mem` | python train, ffmpeg, convert | 互斥 (1) |
| `light` | echo, ls, cat, 简单读写 | 不限 |

---

## 文件锁机制

```
/tmp/claude-resource-locks/
  cpu.lock  → "PID EPOCH"  (互斥锁)
  io.lock   → "PID EPOCH"  (互斥锁)
  net.count → 数字 0-2     (计数器)
  mem.flag  → "PID EPOCH"  (互斥锁)
```

- **获取**: `agent-gate.sh acquire <class> [--wait N]` — 自旋等待 N 秒
- **释放**: `agent-gate.sh release <class|all>`
- **过期**: 600s TTL + PID 存活检测 → 自动偷锁
- **重入**: 同 PID 同 class → 立即返回 (幂等)

> [!warning] 补（2026-09-13）：锁机制缺三件事——原子性、双持有、TTL 依据
> ①**原子性**：`net.count` 是「读 → 改 → 写」的计数器，**没有任何原子性设计**；两个 subagent 同时 acquire 会丢更新、突破上限 2。必须改用 `flock`，或用 `mkdir`（原子占位）作为取锁原语。
> ②**双持有**：「600s TTL + PID 存活检测 → 自动偷锁」在「持有者仍存活但执行很慢」时，会让**同一资源被两个 PID 同时持有**。需改为心跳续租，或采用「**不偷活锁**」策略（只回收 PID 已消失的锁）。
> ③**TTL 依据**：600s 是按什么分布定的、从哪来，文档没写；每个数字都要给出处与对应验证用例。

### acquire / release 接口语义（2026-09-13 补）

「重入: 同 PID 同 class → 立即返回 (幂等)」与 `release` 的配合从未定义：**嵌套 acquire 两次、只 release 一次，锁就被放掉了**。需引入 per-class 引用计数（或在锁文件里记录深度），并把返回值与错误码写死：

| 场景 | 期望返回 | 锁状态 |
|------|----------|--------|
| 首次 `acquire cpu` | 0 | 本 PID 持有，深度 1 |
| 同 PID 二次 `acquire cpu` | 0（幂等） | 深度 2 |
| 同 PID `release cpu` | 0 | 深度 1，**仍持有** |
| 同 PID 再次 `release cpu` | 0 | 释放 |
| 非持有者 `release cpu` | 非 0 | 不变 |
| 他人持有 + `acquire`（无 `--wait`） | 非 0 | 不变（调用方据此 DENY） |

> 姊妹文档 [[subagent-lessons-learned-2026-07-03]] 刚记过「`lock_is_held` 返回值语义反转」，正说明该模块的接口语义必须先定义再实现——不然同类错误会反复出现。

---

## 命令模式检测

`/root/.claude/resource-patterns.conf`:
```
cpu:(npm|yarn) (install|build)
cpu: pip(3)? install
cpu: cmake|make\b|(gcc|g\+\+)
io: grep\s+-r\s+/|find\s+/
io: rsync|dd\b|tar\s+-[cx]
net: curl\s+.*-[oO]\s|wget\b
net: git\s+(clone|pull)
mem: python3? .*(train|model)
mem: ffmpeg\b|convert\b
```

> [!warning] 补（2026-09-13）：9 条正则只有清单，没有样例与误判代价分析
> 条数核对：**9 条**（cpu 3 + io 2 + net 2 + mem 2）无误。缺的是下面四项：
> - **样例集**：每类 5~10 条真实命令，**应命中与不应命中各半**（例：`npm install` 命中 / `npm ls` 不命中；`grep -r /var` 命中 / `grep -r ./src` 不命中）。
> - **`detect` 的输出格式**：单值还是多值？`npm install && grep -r /` 这种组合命令归到哪一类？
> - **既定行为**：管道（`cat x | grep -r /`）、`sudo` 前缀、shell 别名、`xargs`、`$(...)` 嵌套分别怎么判——现在都没有写。
> - **误判代价与取舍**：明确「**宁可漏判不可误判**」的 allowlist 取舍——误判会把轻量命令按互斥锁串行化，直接拖慢日常操作，比漏判一个重命令更伤。

---

## 新增子命令 (~150 行)

```
agent-gate.sh acquire <class> [--wait N]  — 获取资源锁
agent-gate.sh release <class|all>         — 释放资源锁
agent-gate.sh lock-status [--json]        — 查看锁状态
agent-gate.sh detect <command>            — 检测命令类别
```

**do_check() 修改**: 新增第 6 步 — 资源锁冲突检查
- cpu/io/mem 锁被其他 PID 持有 → DENY
- net.count == 2 → WARN

---

## Wrapper 脚本

`/root/claude-gate-bash.sh` (~35 行):
```bash
#!/bin/bash
# 透明包装: 检测命令类别 → 获取锁 → 执行 → 释放锁
CLASS=$(agent-gate.sh detect "$*")
[ -n "$CLASS" ] && agent-gate.sh acquire "$CLASS" --wait 30
eval "$*"
RC=$?
[ -n "$CLASS" ] && agent-gate.sh release "$CLASS"
exit $RC
```

> [!warning] 更正（2026-09-13）：这个 wrapper 在 Claude Code 里**没有接入点**，也没有任何能证明它生效的验证步骤（原表述为上面整节）
> Claude Code 的 Bash 工具**默认不经过这个脚本**，本节从未说明「如何让每次 Bash 调用都走 wrapper」。真正可用的是 PreToolUse hook（见「关键发现」节的更正块）。另外 `eval "$*"` 不构成透明包装（丢原始引号与重定向）。
> 本文 `status: deprecated`，属历史记录，但该结论（缺接入点）仍然成立，故保留原文并标注。

---

## Hook 配置

新增的 hook（合并到 settings.local.json；历史草稿，未验证）：

```json
"PreToolUse": [
  {"matcher": "", "hooks": [{"command": "agent-gate.sh mark-interactive"}]},
  {"matcher": "Agent", "hooks": [{"command": "agent-gate.sh check"}]},
  {"matcher": "Bash", "hooks": [{"command": "agent-gate.sh acquire auto --try-only"}]}
],
"PostToolUse": [
  {"matcher": "Bash", "hooks": [{"command": "agent-gate.sh release acquired"}]}
]
```

---

## 三层防护总结

| 层 | 机制 | 保护什么 | 触发时机 |
|----|------|---------|---------|
| L1 | 进程数+内存门禁 | 不崩 (OOM) | Agent spawn 前 |
| L2 | 交互感知 renice | 不卡 (交互) | 每次工具调用 |
| L3 | 资源类锁调度 | 不撞 (重载) | 重量级 Bash 命令 |

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 纠错 | 「关键发现：Hook 限制」称 hook 无法读取命令参数、故不能在 hook 内做模式匹配——前提错误，Layer 2 Wrapper 立论不成立 | 保留原文并加更正块：hook 从 stdin 拿到 `tool_input.command`，可匹配并以 `exit 2` 阻断；给出正确最小实现（PreToolUse hook 读 stdin → 匹配 → acquire，取不到锁 exit 2），并指出 `eval "$*"` 丢引号/重定向。依据 <https://code.claude.com/docs/en/hooks> |
| 补疏漏 | Wrapper 脚本 `/root/claude-gate-bash.sh` 缺接入点与验证步骤 | 「Wrapper 脚本」节加更正块：Bash 工具默认不经过该脚本，真实可用载体是 PreToolUse hook；保留原文（`status: deprecated`，历史记录），仅标注结论仍成立 |
| 补疏漏 | 文件锁机制缺原子性、双持有与 TTL 依据 | 「文件锁机制」后补三点：`net.count` 读-改-写无原子性（需 `flock` / `mkdir` 原子占位）；TTL 偷锁会造成同资源双持有（需心跳续租或「不偷活锁」）；600s 依据待补 |
| 加厚 | 「重入: 同 PID 同 class → 立即返回 (幂等)」与 release 语义未定义 | 新增「acquire / release 接口语义」表六行（首次/二次 acquire、一次/二次 release、非持有者 release、他人持有）= 期望返回值与锁状态，并关联姊妹文档的 `lock_is_held` 语义反转教训 |
| 加厚 | 「命令模式检测」9 条正则只有清单，没有样例与误判代价分析 | 条数核对为 9（cpu 3 + io 2 + net 2 + mem 2）；补四项：命中/不命中各半的样例集、`detect` 输出格式与组合命令归属、管道/sudo/别名/xargs/`$()` 的既定行为、「宁可漏判不可误判」的 allowlist 取舍 |

回链：[[CORRECTIONS]] · [[AGENTS]]
