---
title: 事故复盘 — dsh-tui 长会话 CPU 空转（Yoga 布局重排整棵会话树）
aliases: [dsh-cpu-spin, dsh-tui-perf, yoga-relayout]
tags: [ai/ops, incident]
created: 2026-09-13
updated: 2026-09-13
status: stable
---

# 事故复盘 — dsh-tui 长会话 CPU 空转（Yoga 布局重排整棵会话树）

See also: [[Claude-Ops-KB-Home]] · [[DSH-TUI内部机制与键盘卡死陷阱]] · [[explorer-cpu-spin-postmortem-2026-08-28]] · [[CORRECTIONS]]

## 一、现象

DSH 会话用久了**卡顿**；`@deepseek-harness-tui/dsh-tui` 的 harness 进程**在没有任何回合活动时**
持续烧掉约 **1.3–1.4 个核**（12 核机器）。

## 二、判别实验（每一步都排除一个假设）

| 假设 | 判别方法 | 结果 |
|---|---|---|
| 孤儿 runner 泄漏 | 全机进程普查 | ❌ 需 200–345 个同时存活才凑得出；实测**只有 1 个、每个 0.40% 单核** |
| GC 抖动 | RSS 采样 | ❌ 全程 **0 次** GC 事件（后随堆增大才出现零星 75MB 级回收） |
| 外部 CPU 争抢 | 先清掉外部失控进程再复测 | ❌ 清掉后 **136.3%**（原 138.8%），纹丝不动 |
| `--profile` 剖析开销 | 查 `--help` | ❌ **`--profile <name>` 是配置档选择器**（`dsh --profile web` ≡ `dsh web`），与 CPU 剖析无关 |
| 它真在干活 | 逐拍对齐「CPU」与「会话文件是否在写」 | ❌ QUIET(n=11) **140.7%** vs WRITING(n=61) **141.9%**，差 1.2pp |
| 启动路径空转 | 冷启动 harness（空会话、无任务） | ❌ 启动尖峰后 65 秒**恒为 0%** |

**绝对量校核**：`TotalProcessorTime / wall` ⇒ 终生均值 0.956 → 1.009 核（与近期窗口自洽）。**整进程测法可信。**

## 三、根因（CDP CPU profile，6193 采样 / 10s）

**热点是 TUI 的布局引擎，不是 agent 逻辑：**

| 自身耗时占比 | 位置 |
|---|---|
| **17.7%** | `layoutNode` @ `native-ts/yoga-layout/index.js` |
| 3.1% / 2.9% / 1.8% / 1.5% / 0.9% | 同文件 `resolveFlexibleLengths` / `computeFlexBasis` / `cacheWrite` / `collectLayoutChildren` / `resolveGap` |
| **15.4%** | `copy` @ `adapter/channel/read-view.js:23` |
| 9.6% | `(garbage collector)` |
| 8.5% | `react-reconciler` |
| ~10% | Ink 侧 `dom.js measureTextNode` / `line-width-cache` / `measure-text` / `stringWidth` / `tabstops` |

**按文件聚合：`yoga-layout` 32.0% / `read-view` 15.5% / react-reconciler 8.5%** ⇒ 六成以上是**把界面重新排版一遍**。

**机制**：Ink/React 每帧重渲染 ⇒ Yoga 对**整棵会话界面树**重跑完整 flexbox 布局，
**成本 ∝ 节点数**。会话涨到 **2246MB**（早期 614MB）时，节点数巨大 ⇒ 稳定烧 ~1.4 核。
**冷启动实验互相印证**：空会话没有节点可排版，故为 0% —— 决定因素是**会话规模**，不是启动路径。

## 四、影响与关联

- 空转与回合活动无关，**长时间挂着也在烧**；会话越大越严重。
- **RSS 增长需单独关注**：实测约 25 分钟内由 614MB 涨到 2246MB（≈3.7 倍）。这是**独立线索**，
  不要把「内存涨」和「布局贵」混为一谈 —— 前者可能是会话正常增长，也可能是未回收。

## 五、修法建议（⚠️ **未验证**）

> 按 [[CORRECTIONS]] C-018「把『应该有』当成『已有』」，以下均为**建议**，未经实施与验证。

1. **已完成的历史消息交给 Ink 的 `<Static>` 渲染**（写一次、永不重排版），只让布局引擎处理**活动尾部**——最对症。
2. 给渲染窗口设上限，不让整棵树参与布局。
3. `components/BtwPanel.js:22` 与 `RecapPanel.js:24` 各有 `setInterval(() => setFrame(f => f+1), 80)`
   （12.5fps 强制重渲染）；**若这两个面板处于挂载态，它们就是触发器**。
4. `read-view.js:23 copy` 占 15.4%，疑似每帧重复派生视图数据。

## 六、复用装置

`dsh-tui-perf/repro/` 下：`harness-trace.ps1`（CPU/RSS/GC 采样）、`count-runners.ps1`、
`dsh-activity-correlate.ps1`（CPU × 会话写入相关性）、`dsh-boot-cpu.ps1`（冷启动对照）、
**`dsh-cpu-profile.mjs`（CDP 采样器：`process._debugProcess(pid)` + `Profiler.start`）**。

⚠️ **副作用**：inspector 一旦开启，**在该进程存活期内无法关闭**（仅监听 `127.0.0.1`），需等 harness 重启。

## 七、方法论教训

1. **CPU 成本的判别顺序**：先排外因（清掉自己留下的失控进程）→ 再排启动路径（冷启动对照）→ 再排除活动相关性（逐拍对齐）
   → 最后才上 profiler。**每一步都排除一个假设**，而不是一次下结论。
2. **Node 的 JS 只跑在一个线程上** ⇒ 进程烧 >1 核意味着**至少一部分在 JS 线程之外**（libuv 线程池/内部线程）。
   这条物理约束能把搜索空间砍掉一半。
3. **`Win32_Thread` 的 `UserModeTime`/`KernelModeTime` 经 CIM 取不到**（实测逐线程求和 0% vs 整进程 144.2%，物理不可能）
   ⇒ **每线程分解此路不通，别再用**。
4. **看名字猜语义会翻车**：`--profile` 是配置档选择器，不是性能剖析（见 [[CORRECTIONS]]）。

Related: [[DSH-TUI插件使用手册]]、[[DSH-TUI内部机制与键盘卡死陷阱]]、[[explorer-cpu-spin-postmortem-2026-08-28]]

> [!note] 更正（2026-09-13，知识库补完会话）
> 上一行原写作 `[[dsh-tui-clock-idle-is-silent]]、[[DRSH-TUI插件使用手册]]`：前者全库无此文档（悬空链接），后者是 `DSH-TUI插件使用手册` 的拼写错误。已按「禁止死链」要求修正，链到本库真实存在的三个相关文档。
