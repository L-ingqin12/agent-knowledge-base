---
title: 跨 PRoot Session 任务分发 — 预探索方案
aliases: []
tags: [ai/ops]
created: 2026-07-06
updated: 2026-09-13
status: deprecated
---

# 跨 PRoot Session 任务分发 — 预探索方案

> [!warning] 此文档已废弃，请参考 [[multi-session-architecture-2026-07-09]]

See also: [[Claude-Ops-KB-Home]] · [[multi-session-architecture-2026-07-09]] · [[claude-unattended-operation-plan]]

> 日期: 2026-07-06 | 状态: 预探索，待测试验证 | 风险: 🔴 高

---

## 背景

PRoot 下每个 session 的 I/O 路径独立。当前 fan-out 的 Agent 子代理与主 session 共享同一 I/O 路径 → D 状态阻塞传染。将重负载任务分发到独立 proot session，可实现真正的 I/O 隔离。

## 风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|:--:|------|------|
| 跨 session 通信不可靠 | 中 | 高 | 文件轮询 + TTL 超时兜底 |
| Worker session 资源泄漏 | 中 | 中 | 任务级 TTL + 定期清理 |
| 主 session 写入但 worker 未读 | 低 | 中 | 双向确认 (ack 文件) |
| 文件锁跨 session 不一致 | 低 | 中 | 独立锁命名空间 |
| Termux OOM (多 proot) | 低 | 高 | worker 用 haiku 模型 + 内存限制 |

## 测试阶梯 (必须按顺序)

### 阶段 A: 基础连通性 (零风险)

```
目标: 验证跨 session 文件通信可用
测试:
  A1. 主 session 写 /tmp/cross-session-test/hello → worker session 读
  A2. Worker session 写 /tmp/cross-session-test/response → 主 session 读
  A3. 延迟测量: write → detect → read 全链路
  A4. 并发: 同时写 3 个 task, worker 串行处理
  A5. 异常: 主 session 进程被杀 → worker 检测 TTL → 清理

通过条件: 5/5 全过, 延迟 < 5s
```

### 阶段 B: I/O 隔离验证 (低风险)

```
目标: 证明独立 session 不会 D-state 传染
测试:
  B1. Worker 执行 dd if=/dev/urandom of=/tmp/big bs=1M count=100
      同时主 session 执行 echo hello (测量响应时间)
  B2. 对比: Agent 子代理执行同样 dd → 主 session 响应时间
  B3. Worker 内存超限 (填满 /tmp) → 主 session 不受影响

通过条件: B1 响应 <1s, B2 响应显著慢于 B1, B3 主 session 存活
```

> [!warning] 补（2026-09-13）：「B2 响应显著慢于 B1」不是可判定判据（原表述为上一行）
> 「显著」既没有数值阈值，也没有测量口径，会让这个预探索**永远无法结题**。补三项：
> - **阈值**：B2 中位响应 **≥ 5× B1**，或 **≥ 2s**（取先满足者）。
> - **测量口径**：墙钟还是工具耗时？每档重复 N 次（建议 ≥10）取中位数；`dd` 的 `bs`/`count` 必须固定（本例 `bs=1M count=100`）。
> - **反例判据**：若 B2 ≈ B1（未达阈值），说明 **D-state 传染假设不成立**，应**停止后续阶段**并把结论写回本文，而不是继续往阶段 C 走。

### 阶段 C: 最小可行分发 (中风险)

```
目标: 单任务端到端: 主 session 派发 → worker 执行 → 取回结果
设计:
  通信目录: /tmp/claude-cross-session/
  
  任务文件: task-{id}.json
    {"id":"[已脱敏]","prompt":"...","model":"claude-haiku-4-5","ttl":300,"status":"pending"}
  
  结果文件: result-{id}.json  
    {"id":"[已脱敏]","status":"done","output":"...","exit":0}
  
  ack 文件:  ack-{id} (worker 创建, 表示已接手)
  
  流程:
    1. 主 session: write task-001.json → wait ack-001 (max 10s) → wait result-001
    2. Worker:    poll tasks/ → create ack → claude -p → write result
    3. 主 session: read result → 清理 task/ack/result
  
  Worker 守护 (轻量, bash 实现):
    while true; do
      for task in /tmp/claude-cross-session/task-*.json; do
        [ -f "$task" ] || continue
        id=$(basename "$task" .json | sed 's/task-//')
        [ -f "ack-$id" ] && continue  # 已被其他 worker 接手
        touch "ack-$id"
        prompt=$(grep -oP '"prompt":"\K[^"]+' "$task")
        model=$(grep -oP '"model":"\K[^"]+' "$task")
        echo "{\"id\":\"$id\",\"status\":\"done\",\"output\":\"$(claude -p "$prompt" --model "$model" 2>&1 | head -c 5000)\"}" > "result-$id.json"
        rm "$task" "ack-$id"
      done
      sleep 2
    done

通过条件: 派发 3 个独立任务, 全部取回结果, 无超时
```

> [!warning] 更正（2026-09-13）：上面的 Worker 守护脚本有三处会真实出错（原表述为上面 `Worker 守护` 段）
> **①两处都会产出非法 JSON**
> - `grep -oP '"prompt":"\K[^"]+'`：JSON 字符串里的**转义引号 / 换行 / 反斜杠**会让 `\K[^"]+` 提前截断，或把控制字符带进模型输入。
> - `echo "{\"...output\":\"$(claude -p …)\"}"`：只要 `claude -p` 的输出含引号、换行或反斜杠就**破坏 JSON**；`head -c 5000` 还会**在 UTF-8 中间截断**。
> 修法：用 `jq -r .prompt` 取值、`jq -n --arg` 生成结果；验收用例必须包含「含引号 / 换行 / CJK 的 prompt」。
> **②路径不一致**：`for task in /tmp/claude-cross-session/task-*.json` 是**绝对路径**，而 `[ -f "ack-$id" ]`、`touch "ack-$id"`、`result-$id.json`、`rm` 全是**相对路径**——只有 worker 的 CWD 恰好等于通信目录时才工作。应统一为 `${DIR}/ack-$id`、`${DIR}/result-$id.json`，并把 `DIR` 作为 worker 的启动参数。
> **③任务独占是 TOCTOU**：`[ -f "ack-$id" ] && continue` 与随后的 `touch "ack-$id"` 之间存在窗口，**两个 worker 可以同时通过检查**（风险矩阵里列了「文件锁跨 session 不一致」，但 C 阶段脚本没实现任何锁）。修法：用 `mkdir "${DIR}/ack-$id"`（原子）或 `set -o noclobber; : > "${DIR}/ack-$id"` 作为独占原语，并要求 worker **只处理「自己成功创建 ack」的任务**。
>
> 修正后的片段（供直接替换）：
> ```bash
> DIR=${1:?usage: worker.sh <comm-dir>}
> while true; do
>   for task in "$DIR"/task-*.json; do
>     [ -f "$task" ] || continue
>     id=$(basename "$task" .json); id=${id#task-}
>     mkdir "$DIR/ack-$id" 2>/dev/null || continue      # 原子独占：失败即已被他人接手
>     prompt=$(jq -r .prompt "$task")
>     model=$(jq -r .model "$task")
>     out=$(claude -p "$prompt" --model "$model" 2>&1 | jq -Rs '.[0:5000]')  # 码点级截断 + 正确转义
>     jq -n --argjson out "$out" --arg id "$id" \
>       '{id:$id,status:"done",output:$out,exit:0}' > "$DIR/result-$id.json"
>     rm "$task"
>   done
>   sleep 2
> done
> ```

## 失败分支与判据（2026-09-13 补）

原方案每个阶段只写「通过条件」，**没写不通过怎么办**；「逃生通道」也只覆盖「人工 kill worker」。ack 超时、result 缺失、worker 崩溃、任务永久 pending 时主 session 的行为此前完全未定义。补齐：

| 触发 | 判定 | 处置 |
|------|------|------|
| 阶段 A 未 5/5 全过 | 跨 session 文件通信不可用 | **终止整个方案**（不进入 B），结论写回本文 |
| A3 延迟 ≥ 5s | 轮询间隔（`sleep 2`）与 TTL 不匹配 | 先调小轮询间隔重测；仍不达标 → 终止 |
| B2 ≈ B1 | D-state 传染假设不成立 | 停止后续阶段，改走「单 session 内限流」路线 |
| B3 主 session 不存活 | I/O 隔离失败 | 终止 |
| ack 超时（> max 10s） | worker 未接手或已崩溃 | 主 session 将任务标记 `pending-timeout`，**不重派同一 id**；连续 2 次则判定 worker 不可用 |
| 有 ack 但无 result | worker 中途崩溃 | 保留 ack 供排查；超 TTL 后由 `cross-session-cleanup` 回收 |
| 任务永久 pending | 无 worker 存活 | 按逃生通道第 2 条，由主 session Agent 接管 |
| worker 进程消失 | 守护者缺失 | 需定义「谁拉起 worker」——现方案没有守护者，临时口径：主 session 派发前先探活 |

通信目录还需定义**清理与 TTL 判定规则**：`ttl` 字段以哪个时间戳为起点（写入还是首次读取）、到期后 `task-*.json` 是删除还是标记 `expired`、`ack-*` 与 `result-*` 各保留多久。

## 集成点

完成阶段 C 后可集成到现有体系:

```
agent-gate.sh 新增:
  cross-session-dispatch <prompt> [--model haiku]  → 写任务到通信目录
  cross-session-status  <task-id>                   → 查结果
  cross-session-cleanup                             → 清理过期任务

claude-resource-protocol.md 新增:
  重负载任务路由规则:
    短任务 (<10 tool calls)  → Agent 子代理 (低延迟)
    长任务 (≥10 tool calls)  → 跨 session 分发 (I/O 隔离)
    重 I/O 任务 (grep/find)  → 跨 session 分发 (防 D-state)
```

> [!warning] 补（2026-09-13）：阈值「10 tool calls」没有依据（原表述为上面路由规则）
> 阈值来源、收益口径、并发 worker 数与队列策略都缺。附两条核对：
> - worker 守护是**单线程串行 + 每轮 `sleep 2`**，吞吐上限约 **0.5 task/s**——跨 session 的收益在 **I/O 隔离**，不在吞吐，别把它当吞吐方案用。
> - 路由规则应改成「**按资源类型**路由」（重 I/O → 跨 session；纯计算 / 轻量 → 子代理），而不是按 tool calls 计数。若要保留「10」，必须给出可复现的测量依据（例如「子代理超过 10 次工具调用后，主 session 响应延迟中位数翻倍」这种可复核的观察）。

## 逃生通道

```
1. 停止 worker:  kill worker-daemon → 任务堆积在通信目录 (不丢失)
2. 回退到 Agent:  删除通信目录 → 所有未处理任务由主 session Agent 接管
3. 完全卸载:      rm -rf /tmp/claude-cross-session/ + kill worker
```

## 不做的

- 不用 proot-distro login 嵌套 (已验证不可用)
- 不用命名管道/FIFO (PRoot 下不可靠)
- 不用 TCP socket (增加复杂性, 文件通信更简单可审计)
- 不做持久化任务队列 (那是 Kanban 的事)

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 纠错 | Worker 守护用 `grep -oP` 取 JSON 字段、用 `echo` 拼结果 JSON，两处都会产出非法 JSON（转义引号/换行/反斜杠破坏结构，`head -c 5000` 会在 UTF-8 中间截断） | 保留原脚本并加更正块，给出 `jq` 取值 / `jq -n --arg` 生成 / `jq -Rs '.[0:5000]'` 码点级截断的修正片段，并把「含引号/换行/CJK 的 prompt」列为验收用例 |
| 纠错 | task 用绝对路径而 ack/result 用相对路径，只有 worker 的 CWD 恰好等于通信目录时才工作 | 更正块指明逐行差异，统一为 `${DIR}/…` 并把 `DIR` 作为 worker 启动参数 |
| 补疏漏 | 用 `[ -f "ack-$id" ] && continue` + `touch ack-$id` 做任务独占是 TOCTOU，两个 worker 可同时通过 | 更正块改为原子独占原语（`mkdir` 或 `set -o noclobber`），并要求 worker 只处理「自己成功创建 ack」的任务；同时点出风险矩阵已列该风险但脚本未实现 |
| 加厚 | 阶段 B 通过条件「B2 响应显著慢于 B1」不是可判定判据 | 补数值阈值（≥5×B1 或 ≥2s）、测量口径（墙钟/重复 N 次取中位数/固定 dd 参数）与反例判据（B2≈B1 → 假设不成立，停止后续阶段） |
| 补疏漏 | 测试阶梯只有「通过条件」，没有「不通过怎么办」；逃生通道只覆盖人工 kill worker | 新增「失败分支与判据」表八行（阶段 A 未过即终止、ack 超时、有 ack 无 result、任务永久 pending、worker 消失无守护者等），并补通信目录的清理与 TTL 判定规则 |
| 加厚 | 集成点路由阈值「短任务 <10 tool calls / 长任务 ≥10」无依据 | 补两点核对：worker 单线程串行 + `sleep 2` ⇒ 吞吐上限约 0.5 task/s，收益在 I/O 隔离而非吞吐；路由应改为按资源类型，保留「10」须给可复现依据 |

回链：[[CORRECTIONS]] · [[AGENTS]]
