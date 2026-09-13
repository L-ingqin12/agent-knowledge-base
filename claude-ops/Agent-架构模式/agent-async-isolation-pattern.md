---
title: Agent 同步调用异步隔离模式
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-08-10
updated: 2026-09-13
status: stable
---

# Agent 同步调用异步隔离模式

> [!abstract] 同步 Agent 调用的异步隔离通用模式 — ThreadPoolExecutor + asyncio.wait_for + 超时兜底

See also: [[Claude-Ops-KB-Home]] · [[log-analysis-agent-windows-architecture]] · [[pi-agent-framework-knowledge]]

## 问题

opencode / Pi Agent / Claude Code 等 Agent 框架的调用接口通常是同步阻塞的（subprocess 调用或同步 SDK）。直接放在 Tornado/FastAPI 的 async handler 中会阻塞事件循环，导致所有请求排队。

## 解决方案

三层包装模式:

```
async handler
  │
  ├─ asyncio.wait_for(future, timeout=T1)     ← L1: 事件循环超时
  │     │
  │     └─ loop.run_in_executor(pool, fn)      ← L2: 线程池隔离
  │           │
  │           └─ AgentClient.method(timeout=T2) ← L3: Agent 自身超时
```

## 关键参数

| 参数 | 推荐值 | 原则 |
|------|--------|------|
| ThreadPoolExecutor.max_workers | 8 per process | 不超过 CPU 核数 × 2 |
| asyncio.wait_for timeout | 60s | 略大于 Agent 超时 |
| AgentClient timeout | 50-60s | Agent 任务的实际时间上限 |

> [!warning] 更正（2026-09-13）：「不超过 CPU 核数 × 2」查无官方出处（原表述为右列那句）
> Python 官方给的默认值是 **`min(32, os.cpu_count() + 4)`**（3.13 起为 `min(32, (os.process_cpu_count() or 1) + 4)`），文档里给不出「×2」的来源；而且本场景是**子进程 / SDK 等待型（I/O 密集）**，取值应由并发目标与内存预算反推，不该照 CPU 核数套公式。见 <https://docs.python.org/3/library/concurrent.futures.html>。
>
> **推导：8 是怎么算出来的** — 每线程峰值 RSS × 同时开工线程数 + 队列积压 ≤ 进程内存预算。例：单次分析峰值 RSS ≈ 120 MB、进程预算 ≈ 1 GB ⇒ 可同时开工 ≈ 8。落地时必须先实测单次峰值 RSS，再回填此数并写明**超限时的失效现象**（不是变慢，而是内存耗尽）。
> **验收判据**：①超时率 < 1%；②队列深度 P95 < `max_workers`；③连续 1000 次人为超时后 `active` 线程数不增长（证明线程被回收而非泄漏）。
> **实测表（待补）**：机器规格 / 日志规模 / P50·P95·P99 / 超时次数——没有这张表，上表三行只是推荐值，不是结论。

## 注意事项

1. **线程无法被 asyncio 真正取消**: `wait_for` 超时后线程仍在后台运行。AgentClient 内部必须有自己的超时。
2. **线程池大小固定**: 线程池满后新任务排队。通过增加进程数水平扩容，而非增大线程池。
   > [!warning] 补（2026-09-13）：排队不是「等一下就好」，要补背压设计
   > `ThreadPoolExecutor` 的提交队列**没有容量上限**（官方文档未给容量条款，此结论来自实现语义），而本文第 1 条已承认「提交后超时的请求其线程仍被占用」。于是「请求体可达 50 MB × 无界队列」的表现是**内存持续增长**，而不是快速失败。三条必补：
   > ①队列深度上限与拒绝策略（超限返回 **503 + `Retry-After`** 或 429，而不是继续排队）；
   > ②在途任务计数指标（提交 +1 / 完成 −1），并同时暴露 `queue_depth` 与 `max_workers`；
   > ③超时后线程回收的观测（`active` vs `queued` 两条曲线）——否则「线程池满」在监控上不可见。

3. **优雅关闭**: `executor.shutdown(wait=True)` 等待正在执行的任务完成。
   > [!warning] 更正 / 取舍（2026-09-13）：官方明确**不建议**把 ThreadPoolExecutor 用于长任务
   > 原文逐字：「All threads enqueued to ThreadPoolExecutor will be joined before the interpreter can exit. Note that the exit handler which does this is executed before any exit handlers added using `atexit`. … **For this reason, it is recommended that ThreadPoolExecutor not be used for long-running tasks.**」（<https://docs.python.org/3/library/concurrent.futures.html>）
   > 本模式处理的恰好是 50–60s 级任务，正落在这条建议的覆盖范围内：等待排空发生在 `atexit` 处理器**之前**，真超时场景下 `shutdown(wait=True)` 会变成**关不掉**。
   > 替代方案（按代价递增）：①超时后不等待排空，改为给每个任务单独的**进程级超时 kill**；②把长任务下沉到带 TTL 的任务系统（队列 + 独立 worker 进程）；③纯 CPU 密集部分改用 `ProcessPoolExecutor`。

## 适用场景

- Tornado async handler 中调用同步 Agent
- FastAPI async handler 中调用同步 Agent
- 任何 async web framework + 同步 Agent SDK 的组合

**Why:** Python 的 GIL 意味着 CPU 密集型 Agent 调用必须在线程池中执行才能释放事件循环。这是连接 async web framework 和 sync agent SDK 的桥梁模式。
**How to apply:** 复制 `_run_agent_with_timeout` 方法模板，替换 `AgentClient.analyze_log` 为实际调用。

> [!warning] 更正（2026-09-13）：上面 `Why` 那句的因果写反了
> 官方原文（`ThreadPoolExecutor` 的 3.8 变更条）逐字：「This default value preserves at least 5 workers for I/O bound tasks. It utilizes at most 32 CPU cores for CPU bound tasks **which release the GIL**.」——线程池的并行收益来自**会释放 GIL 的任务**（I/O、子进程 / SDK 等待）；**纯 CPU 密集的 Python 代码在线程池里拿不到并行度**。
> 措辞也要收紧：GIL 会周期性切换，事件循环不是被彻底饿死，而是**延迟与吞吐显著劣化**；真正的处置是 `ProcessPoolExecutor`。
> 本模式的真实机制是：**Agent 调用属 subprocess / SDK 等待型（阻塞但不持 GIL）**，因此放进线程池能把事件循环让出来——桥梁作用成立，但理由不是「CPU 密集」。见 <https://docs.python.org/3/library/concurrent.futures.html>。

## 最小配置示例 (settings.json 片段)

```json
{
  "timeouts": {
    "nginx_proxy_read": 120,
    "asyncio_wait_for": 60,
    "agent_client": 60
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "agent-guardian.sh preflight",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**超时行为说明**:
- 外层必须大于内层: nginx 120s > `asyncio.wait_for` 60s ≥ AgentClient 60s，否则外层先超时返回 504，内层仍在空转浪费线程。
- `asyncio.wait_for` 超时 → 抛 `TimeoutError` 并记录日志；线程池中的线程无法被杀，靠 AgentClient 自身 timeout 兜底退出。
- hook 的 `timeout: 30` 防止 hook 命令自身卡死；PreToolUse hook 超时/失败即阻断该工具执行。

> [!warning] 更正（2026-09-13）：hook 超时 / 失败**不阻断**工具执行（原表述为上一行后半句）
> 官方 Timeouts 节逐字：「A timed-out command, http, or mcp_tool hook **doesn't block** the tool call. The call continues through the normal permission flow, so **don't count on a stalled hook to act as a gate**.」（只有 Agent SDK 的 callback hook 超时才阻断）
> 失败同理：**exit 2 才阻断**（「Exit 2 means a blocking error… PreToolUse blocks the tool call」），exit 1 等其它退出码是 non-blocking；路径写错（127）也落进同一桶——官方原文「a mistyped path in settings.json leaves the gate silently disabled」。
> 默认值口径也要分清：`command` / `http` / `mcp_tool` 的**默认 timeout 是 600 秒**（30 秒只适用于 `prompt` 类型及少数被下调的事件），所以「`timeout: 30`」本身不是错，**错的是「超时即阻断」这个语义**。这正属 [[CORRECTIONS]] 记的「把现象当结论」。
> 依据：<https://code.claude.com/docs/en/hooks>

## 关联

- [[log-analysis-agent-windows-architecture]] — 本模式在日志分析服务中的具体应用
- [[fan-out-subagent-pattern]] — 多维度分析时本模式的并行扩展
- [[claude-interruption-resilience-guide]] — 长任务恢复 (与本模式的超时互补)

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 纠错 | 「Python 的 GIL 意味着 **CPU 密集型** Agent 调用必须在线程池中执行才能释放事件循环」因果写反 | 「适用场景」节保留原句并加更正块：线程池收益来自**会释放 GIL 的任务**，纯 CPU 密集拿不到并行度；本模式的真实机制是 subprocess/SDK 等待型（阻塞但不持 GIL）；依据 <https://docs.python.org/3/library/concurrent.futures.html> |
| 纠错 | 「PreToolUse hook 超时/失败即阻断该工具执行」与官方语义相反 | 「超时行为说明」保留原句并加更正块：超时的 command/http/mcp_tool hook **不阻断**，只有 exit 2 阻断、路径写错（127）落进 non-blocking 桶；另更正默认 timeout 是 600s（30s 仅 prompt 类型）。依据 <https://code.claude.com/docs/en/hooks> |
| 纠错 | `max_workers` 原则「不超过 CPU 核数 × 2」无官方来源 | 「关键参数」保留原表并加更正块：官方默认 `min(32, os.cpu_count() + 4)`；本场景按内存预算反推，并写明 8 的推导与超限失效现象 |
| 补疏漏 | 把 ThreadPoolExecutor 当 50–60s 长任务的正规载体，未记录官方反面建议 | 注意事项第 3 条加更正块：官方逐字「recommended that ThreadPoolExecutor not be used for long-running tasks」，并给三条替代方案（进程级 kill / 带 TTL 任务系统 / ProcessPoolExecutor） |
| 补疏漏 | 第 2 条只写「新任务排队」，没写排队的代价与背压设计 | 第 2 条补背压三条：队列深度上限 + 503/429 拒绝策略、在途任务计数指标、超时后线程回收观测（active vs queued） |
| 加厚 | 「关键参数」表（8 / 60s / 50–60s）与「超时行为说明」只有推荐值，没有推导与验收判据 | 表下补「8 的推导」「验收判据三条（超时率 < 1% / 队列深度 P95 < max_workers / 1000 次超时后 active 不增长）」与「实测表（待补）」 |

回链：[[CORRECTIONS]] · [[AGENTS]]
