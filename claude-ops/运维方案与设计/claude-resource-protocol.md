---
title: Claude Resource Protocol
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-07-01
updated: 2026-09-13
status: review
---

# Claude Resource Protocol

See also: [[Claude-Ops-KB-Home]] · [[claude-unattended-operation-plan]] · [[AGENTS]]

> System prompt injection — teaches Claude how to work within environment resource limits.

## Environment

- Android Termux + PRoot, 7.4 GB total RAM (~2 GB available)
- Each `claude` process ~200 MB RSS
- Oversubscribing triggers OOM kills (no swap)

> 采集口径（2026-09-13 复核）：总内存与可用内存取自 `/proc/meminfo`（`MemTotal`、`MemAvailable`，kB ÷ 1024 = MB），`free -m` 输出同源；单进程 RSS 用 `ps -o rss= -p <pid>`（kB ÷ 1024）。**上面三行是部署时的单次观察，原文未附采样时间与样本量**：7.4 GB 为设备标称内存，`~2 GB available` 与 `~200 MB RSS` 随负载波动，不是统计量。
>
> 阈值出处：下表 GREEN/YELLOW/RED 的数值来自 `/root/claude-agent-gate.sh` 的常量 `MIN_MEM_GREEN=1200`、`MIN_MEM_RED=800`（另含 swap 档 `SWAP_YELLOW=55`、`SWAP_RED=70`）；**不在** `resource-patterns.conf`——后者只做 cpu/io/net/mem 的命令分类正则。

## Before spawning subagents

**Always run:**

```
bash /root/claude-agent-gate.sh status
```

This is non-negotiable. Do not skip it.

## Gate commands

| Command | What it does |
|---------|-------------|
| `bash /root/claude-agent-gate.sh status` | Quick state check (prints one line) |
| `bash /root/claude-agent-gate.sh check` | Full gate (returns JSON with `GREEN`/`YELLOW`/`RED`/`DENY`) |

## Resource tiers

| Status | Meaning | What to do |
|--------|---------|------------|
| **GREEN** | Memory healthy | Up to **2 concurrent** subagents OK |
| **YELLOW** | Tight | **1 subagent max** — serial only |
| **RED** / **DENY** | Critical / throttled | **Don't spawn**. Wait 10–30 s, retry. |

## Fan-out pattern

Never spawn all subagents at once. Follow this rhythm:

1. Spawn **2**
2. **Wait** for both to complete
3. Spawn **next 2**
4. Repeat

Maximum 2 in-flight at any time, regardless of tier.

## Interactive awareness

- **User actively chatting** → subagents auto-throttled (gate returns DENY more aggressively)
- **User idle** → subagents get full resources (gate relaxes)

Let the gate decide — do not second-guess it.

## If denied

1. Wait **10–30 seconds**
2. Re-run `bash /root/claude-agent-gate.sh check`
3. If GREEN/YELLOW → proceed. If still DENY → **serialize the work**: run subtasks one at a time, no parallelism.

## Golden rule

One `check` before every subagent spawn. No exceptions.

### 验收判据（2026-09-13 补）

| # | 用例 | 操作 | 通过判据 |
|---|------|------|----------|
| 1 | 门控脚本回归 | `bash tests/agent-gate-test.sh`（仓库内；`/root/claude-agent-gate.sh` 缺席时套件会回退到仓库路径） | 退出码 `0`、末行 `✓ 全部通过`、`FAIL=0` |
| 2 | 状态行格式 | `bash /root/claude-agent-gate.sh status` | 单行含 `MemAvail=…MB SwapUsed=…% ClaudeProcs=… MemLevel=… State=…`；单进程时以 `Locks=[skipped:single]` 结尾 |
| 3 | RED/DENY 下不 spawn | 在 `MemLevel=RED` 或 `check` 返回退出码 `2` 时尝试 spawn | 拒绝 spawn 并回落串行；`check` 输出形如 `{"status":"DENY",…}` |
| 4 | 内存拒绝文案 | `bash /root/claude-agent-gate.sh memcheck` | DENY 时输出形如 `memcheck: DENY (…MB available < 800MB, swap …%)` |

## Resource lock awareness (Phase 2d)

When running heavy commands (npm install, pip install, cmake, grep -r /, etc.), the system automatically serializes conflicting operations:

- **CPU ops** (npm install, make, cmake) — only 1 at a time
- **IO ops** (grep -r /, find /, rsync) — only 1 at a time
- **Network ops** (curl -O, git clone) — max 2 concurrent
- **Light ops** (echo, cat, ls) — unlimited, zero overhead

In non-fan-out mode (single session, no subagents), all lock overhead is skipped. The mechanism only activates when subagents are running.

To check lock status: `bash /root/claude-agent-gate.sh lock-status`（`--json` 输出 `{"locks":{"cpu":{"pid":…,"age":…},…,"net":{"count":…,"max":2}}}`）
To manually gate a heavy command: `/root/claude-gate-bash.sh <command>`

### 锁的实现细节（2026-09-13 补）

- **锁表位置**：`/tmp/claude-resource-locks/`（常量 `RESOURCE_LOCK_DIR`）。`cpu.lock` / `io.lock` / `mem.flag` 的内容是 `<PID> <EPOCH 秒>`；`net` 不是互斥锁，而是计数器 `net.count` + 持有者名单 `net.pids`（上限 `NET_MAX=2`）。
- **等待上限**：默认自旋等待 `SPIN_DEFAULT_TIMEOUT=30` 秒（间隔 `SPIN_INTERVAL=0.5` 秒）；`claude-gate-bash.sh` 显式传 `--wait 30`。
- **超时后行为**：**不阻塞调用者**——`acquire` 打印 `acquire: <class> BUSY (waited 30s), proceeding anyway` 并按忙返回，命令照常执行；包装器只在 stderr 打印 `[gate] resource '<class>' busy after 30s, proceeding anyway`。
- **死锁 / 残留锁回收**：锁文件超过 `LOCK_TTL=600` 秒，或持有者 PID 已不存在时，`lock_cleanup_stale` 会在 `check` / `lock-status` 时自动删除；也可手工 `bash /root/claude-agent-gate.sh release all`。注意 `net.count` **不自动清理**（靠 `release net` 递减），异常退出后需手工 `bash /root/claude-agent-gate.sh release net` 或删除该计数文件。
- **是否处于 fan-out 模式**：按 `pgrep -x claude` 计数的 `ClaudeProcs` 判定——只有 `> 1` 才检查锁（`status` 输出 `Locks=[CPU:… IO:… NET:n/2]`）；`= 1` 时跳过锁检查并输出 `Locks=[skipped:single]`，即「非 fan-out 零开销」。

## 门控失效时的逃生（fail-safe）

| 故障 | 默认行为 / 兜底动作 |
|------|---------------------|
| `claude-agent-gate.sh` 缺席、权限错误或内部报错 | 退出码约定为 `0 = 通过` / `1 = 降级` / `2 = 拒绝` / **其他 = 故障安全（允许，不阻塞）**——非 0/1/2 的退出码按允许处理，不会因门控自身故障锁死 spawn |
| 疑似脏锁导致误判 DENY | 先 `bash /root/claude-agent-gate.sh lock-status` 看 `PID=… age=…s`；确认持有者已死或 `age > 600s` 后 `bash /root/claude-agent-gate.sh release all`（紧急时 `rm -f /tmp/claude-resource-locks/*.lock`） |
| 不想等自旋超时 | 直接用原命令（不经 `claude-gate-bash.sh`）：门控只做串行化，不阻断执行——超时路径本身也是「打印 BUSY 后照常执行」 |
| 怀疑门控结论 | 跑 `bash tests/agent-gate-test.sh` 回归；再在 RED/DENY 下手工 spawn 一次，确认被拒绝并回落串行 |

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 补疏漏 | Environment 的 RAM/RSS 数字与 GREEN/YELLOW/RED 阈值无采集口径、时间与出处 | 补采集命令（`/proc/meminfo`、`free -m`、`ps -o rss=`）与阈值出处（`claude-agent-gate.sh` 的 `MIN_MEM_GREEN=1200`、`MIN_MEM_RED=800`、`SWAP_YELLOW=55`、`SWAP_RED=70`），并标明原值为单次观察、非统计量 |
| 补疏漏 | 全文无门控失效（脚本挂了、脏锁误判）时的逃生与降级路径 | 新增「门控失效时的逃生（fail-safe）」表：退出码故障安全语义、脏锁判定与手工清理、绕过方式与复验步骤 |
| 补疏漏 | §Golden rule 只有规则，没有「规则是否生效」的验证方式 | 新增验收判据表（`tests/agent-gate-test.sh` 期望 `FAIL=0` / `✓ 全部通过`；期望输出按脚本真实格式 `MemAvail=…MB … MemLevel=…` 与 `memcheck: DENY (…MB available < 800MB, swap …%)`） |
| 加厚 | §Resource lock awareness 列出四类锁与上限，但未给锁表位置、超时与死锁处理 | 补锁文件路径与格式（`<PID> <EPOCH>`）、`LOCK_TTL=600`、`SPIN_DEFAULT_TIMEOUT=30`、超时后不阻塞、`net.count` 不自动清理，以及 fan-out 判定（`ClaudeProcs > 1`） |

回链：[[CORRECTIONS]]

