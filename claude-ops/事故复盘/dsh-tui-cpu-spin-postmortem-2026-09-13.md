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

> [!warning] 残余复核（2026-09-13）：**「无关」只在已测的那个口径下成立，判为未定**。§二 的判别实验测的是
> 「会话文件是否在写」（QUIET 140.7% vs WRITING 141.9%），它**区分不了「回合已闭合」与「回合开着但没在写」**。
> 本机已核实的帧时钟模型是 `CPU ≈ 帧率 × 每帧成本`，而帧率由「有无未闭合回合 / spinner / activity 动画」决定 ——
> 无未闭合回合时共享帧时钟**不触发**；空会话头 10s 的 tick 是**开场动画**（`skipIntro` 只在无历史时播），之后归零。
> 原报告现场会话的末条恰是**未回答的 `ask_user_question`**（回合未闭合 ⇒ spinner 类动画活着）。⇒「无回合活动时照烧」
> **尚不成立**，本节「长时间挂着也在烧」应读作「挂着但**回合未闭合**时也在烧」。**未决的判别实验**：同一长会话，
> 「回合开着、零写入」vs「回合闭合、零写入」两组对照。**判据**：trace 窗口须跨过启动瞬态（**≥60s**），
> 取 **10s 之后**的 animation 帧数与 `clockKeepAlive`，**不是总量**（短窗口会把开场动画误判成常驻）。
- **RSS 增长需单独关注**：实测约 25 分钟内由 614MB 涨到 2246MB（≈3.7 倍）。这是**独立线索**，
  不要把「内存涨」和「布局贵」混为一谈 —— 前者可能是会话正常增长，也可能是未回收。

## 五、修法建议（⚠️ **未验证**）

> 按 [[CORRECTIONS]] C-018「把『应该有』当成『已有』」，以下均为**建议**，未经实施与验证。

> [!success] 残余复核（2026-09-13）：本条是**证据等级声明**，本身无待决问题（判为**非待办**）。下列四条已逐条回本机
> 装好的 `dsh-tui@0.10.1` 源码核对 —— 路径 `%USERPROFILE%\.dsh\profiles\dsh-tui\node_modules\@deepseek-harness-tui\dsh-tui\lib\types\`
> —— 其中 ②③④ 的**前提**已能定论（见下），①**在本机这份 Ink 里没有对应 API**。四条**修法本身仍未经实施与验证**，
> 本节「未验证」的定性不变。

1. **已完成的历史消息交给 Ink 的 `<Static>` 渲染**（写一次、永不重排版），只让布局引擎处理**活动尾部**——最对症。

> [!warning] 残余复核（2026-09-13）：**这条建议指向的 API 在本机这份 Ink 里不存在，故仍开放**。dsh-tui 把 Ink
> **内联**在 `lib/types/ink/`（不是依赖 npm `ink` 包）：`ui.js` 的 25 条导出与 `ink/components/` 下 19 个组件里
> **都没有 `Static`**；全包检索 `Static` 只命中无关文案与 `native-ts/yoga-layout/enums.js` 的枚举 `Static: 0`
> （`ink/root.js:44` 那句 “the subsequent Static write” 只是注释，无对应实现）。⇒ 建议①不能「直接用」，
> 须**先自行实现**「写一次、不再参与重排版」的原语，再真机长时采样验证。依据：本机源码全量检索（2026-09-13）。
2. 给渲染窗口设上限，不让整棵树参与布局。

> [!success] 残余复核（2026-09-13）：**前提不成立 —— 上游已经这么做了**。`components/MessageList.js:44`
> `const RENDERED_ROW_CAP = 120;`（历史行折进 Divider，`Ctrl+E` 展开），且 `:45-49` 明写离屏行渲染为**固定高度 spacer**、
> 「the pure-JS Yoga engine **never walks their subtrees**」⇒ 布局成本本来只在**挂载窗口**（≤120 行 + `OVERSCAN_LINES = 8`），
> 不是「整棵树」。据此 §三 的「Yoga 对**整棵会话界面树**重跑完整 flexbox 布局」表述过宽：随会话规模增长的**不是布局**，
> 而是**每帧 O(转录总行数) 的扫描/投影**。依据：本机源码 + `dsh-tui-perf/README.md` §1（「列表确实做了虚拟化，最多挂载
> 120 行 …… 剩余主因是每帧重新布局**挂载窗口** + 每帧若干次 O(转录总行数) 扫描」）。**注**：§三 的「节点数巨大」是
> **未测**量 —— RSS 涨不等于节点数涨（150s 净采样那次 RSS 575→603MB 平坦、零 GC，与 2246MB 那次不是同一实例）。
3. `components/BtwPanel.js:22` 与 `RecapPanel.js:24` 各有 `setInterval(() => setFrame(f => f+1), 80)`
   （12.5fps 强制重渲染）；**若这两个面板处于挂载态，它们就是触发器**。

> [!success] 残余复核（2026-09-13）：**引用属实，但「触发器」推论被源码否掉，该假设排除**。
> ① 位置逐行核对为真：`components/BtwPanel.js:22`、`components/RecapPanel.js:24` 确为
> `setInterval(() => setFrame(f => f + 1), 80)`；这两个文件**不在**本机补丁备份 `dsh-tui-perf/backup/` 内，
> 即上游原样代码（本机 5 个补丁文件是 `read-view.js` / `Chat.js` / `ClockContext.js` / `SplitDiffView.js` / `transcript.js`）。
> ② 但两处都在 `React.useEffect` 内**带前置守卫**：`if (!streaming || answer !== '') return;`
> （`RecapPanel` 对应 `summary !== ''`）—— **只在等首个字期间起跳**，首字到达即 `clearInterval`。
> ③ 面板挂载同样是条件式：`screens/Chat.js` 按 `btw !== null` / `recap !== null && (!recap.auto || recap.expanded)`
> 渲染，`Chat.js:420` 为 `const [btw, setBtw] = React.useState(null)`，⇒ 仅 `/btw`、`/recap` 覆盖层打开时存在。
> ⇒「**若这两个面板处于挂载态，它们就是触发器**」**不成立**：挂载 ≠ 计时器在跑，还要求一次**正在进行中**的侧问答。
> 依据：本机源码逐行核对（2026-09-13）。
4. `read-view.js:23 copy` 占 15.4%，疑似每帧重复派生视图数据。

> [!success] 残余复核（2026-09-13）：**标签准确、机制可复核，措辞需收窄**。`adapter/channel/read-view.js:23` 是 CDP 的
> **0 基**行号（`callFrame.lineNumber`）⇒ 对应 1 基第 **24** 行 `function copy(value, key = '', receiver)`，函数名对得上。
> 机制：`createChannelReadView()` 返回 `(value, nextVersion) => { version = nextVersion; return copy(value); }`，
> 由 `adapter/channel/ui.js:62` 以 `channel.version` 驱动 ⇒ **每次 channel 版本变更（每次追加/触碰）全量走一遍投影树**；
> 未变动的行靠 `dirtyRevisions`/`copies` 结构共享短路（`read-view.js:63-82`）⇒ 其成本是 **O(转录行数) 的遍历**，
> 不是深拷贝。⇒ 应把「疑似**每帧**重复派生」收窄为「**每次 channel 版本变更**重复派生」：同一版本内重复读会命中
> `prior.version === version` 短路（`:81`）。**已解决**（与 `dsh-tui-perf/README.md` §1「每帧若干次 O(转录总行数) 扫描」
> 同类，属剩余主因的一部分，但严格说不是「每帧」）。

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

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 非待办 | §五 开头的 `[[CORRECTIONS]]` C-018 证据等级声明（「以下均为建议，未经实施与验证」） | 本身无待决问题。四条建议已逐条回本机 `dsh-tui@0.10.1` 源码核对，「未实施」定性不变；核对面见本节 `[!success]` 残余复核块 |
| 仍开放 | §五-1 「历史消息交给 Ink 的 `<Static>` 渲染」 | **该 API 在本机这份 Ink 里不存在**：dsh-tui 内联 Ink 于 `lib/types/ink/`，`ui.js` 25 条导出与 `ink/components/` 19 个组件均无 `Static`（全包检索仅命中无关文案与 yoga 枚举 `Static: 0`）⇒ 须先自行实现「写一次、不再重排版」原语，再真机长时采样验证 |
| 已解决 | §五-2 「给渲染窗口设上限，不让整棵树参与布局」 | **前提上游已实现**：`components/MessageList.js:44 RENDERED_ROW_CAP = 120`、`:45-49` 离屏行渲染为固定高度 spacer 且 Yoga「never walks their subtrees」⇒ 布局只覆盖**挂载窗口**；据此 §三「整棵树重跑完整 flexbox 布局」收窄为「挂载窗口」，随会话增长的是每帧 O(转录行数) 的扫描/投影。依据：本机源码 + `dsh-tui-perf/README.md` §1 |
| 已解决 | §五-3（第 3 行）两处 `setInterval(…, 80)` 的引用 | 位置逐行核对为真（`components/BtwPanel.js:22`、`components/RecapPanel.js:24`），且二者不在本机补丁备份 `dsh-tui-perf/backup/` 内 = 上游原样 |
| 已解决 | §五-3（第 4 行）「若这两个面板处于挂载态，它们就是触发器」 | **推论不成立，该假设排除**：两处间隔都在 `React.useEffect` 内带 `if (!streaming \|\| answer !== '') return;` 守卫（`RecapPanel` 为 `summary !== ''`），只在等首字期间起跳；面板又按 `Chat.js:420 useState(null)` 的 `btw`/`recap` 条件挂载 ⇒ 挂载 ≠ 计时器在跑。依据：本机源码逐行核对 |
| 已解决 | §五-4 「`read-view.js:23 copy` 占 15.4%，疑似每帧重复派生视图数据」 | 标签准确（CDP 0 基 23 = 1 基 24 `function copy`）；`ui.js:62` 以 `channel.version` 驱动 ⇒ 每次版本变更全量遍历、未变动行结构共享（`read-view.js:63-82`）⇒ 措辞收窄为「**每次 channel 版本变更**」而非「每帧」。依据：本机源码 |
| 补疏漏 | §二/§四 断言「空转与回合活动无关/长时间挂着也在烧」 | 判别实验只测「会话文件是否在写」，**区分不了「回合闭合」与「回合开着未写」**；按已核实的帧时钟模型（`CPU ≈ 帧率 × 每帧成本`，无未闭合回合则时钟不跑、空会话头 10s 的 tick 是开场动画）判为**未定**，补「回合开着/闭合 × 零写入」对照实验与判据（≥60s 窗口、取 10s 后 animation 帧数与 `clockKeepAlive`） |

依据与索引：[[CORRECTIONS]]、[[DSH-TUI内部机制与键盘卡死陷阱]]、[[Claude-Ops-KB-Home]]
