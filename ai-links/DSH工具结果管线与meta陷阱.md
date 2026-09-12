---
title: DSH 工具结果管线与 meta 陷阱
aliases: [tools/execute, post-execute, presentationMeta 泄漏]
tags: [ai/tools, ai/agent, ai/skills]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# DSH 工具结果管线与 meta 陷阱

See also: [[AI-Links-KB-Home]] | [[DSH插件与Hook开发最佳实践]] | [[DSH会话日志格式与读取端约束]] | [[DSH会话持久化与活跃改写安全]] | [[CORRECTIONS]]

> [!abstract] 本文只回答一个问题
> **一次工具调用从「参数落盘」到「成为下一次请求里的那条消息」，中间有哪些可拦截的接缝、按什么顺序生效、各自能改什么**——以及为什么在 `tools/post-execute` 上**替换 `content` 不足以脱敏**：那条路径会把原结果整体展开，`meta` 存活，而 `meta` 是被**逐字持久化**的。
>
> 面向要写「结果改写 / 结构化最小化 / 内容策略」插件的人。日志格式与读取端合法性归 [[DSH会话日志格式与读取端约束]]，已落盘日志的原地改写归 [[DSH会话持久化与活跃改写安全]]，本文只讲 append **之前**的那条管线。

> [!danger] 三句话结论
> 1. **落盘的 `tool/result` 就是面向模型的那条消息**：`deriveEventMessage` 对 `tool/result` 直接 `return event.data.message`（`dsh-session/lib/index.js:216`），而请求每轮由 `session.deriveMessages()` 从日志折叠（`dsh-agent-loop/lib/index.js:1204`）。所以 append 之前做的决定，同时固定了日志与未来**每一次**请求。
> 2. **`tools/post-execute` 的 `accept{content}` 是「展开原结果再换 content」**（`dsh-tools/lib/index.js:3401-3405`）——`meta` 一并留下；只有 `accept{value}` 会让注册表从 value **重新派生 content 与 meta**（`:3395` → `createSuccessResult` 的 `:3422` / `:3428-3436`）。
> 3. **`web_search` 把同一段 `snippet` 同时投进渲染文本与 `presentationMeta`**（`dsh-tool-web/lib/index.js:69` 与 `:107`，答案同理见 `:64` 与 `:122`），所以「只改 content」= **命中文本随 `meta` 落盘**。

## 〇、判据、范围与标注规则

| 项 | 值 |
|---|---|
| 源码根 | `C:\%USERPROFILE%\nodejs-x64\node-v22.21.0-win-x64\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\` |
| 证据形态 | **源码直读**（本机安装树，下称「相对路径」一律相对上面的源码根）＋引用本库已有实测报告；**本文未新增运行时实验** |
| 出结论前的回查 | 已按 [[AGENTS]] §六·五回查 [[CORRECTIONS]]：本主题最易复发的两条是 **C-005**（拿工具自检当读取端验收）与 **C-009**（把服务/接缝存在当成效果出现）——「接缝存在」不等于「改写生效」，见第七节第 1 条 |
| 未读内容声明 | 全程**未读取**任何真实会话内容、缓存或 `*.jsonl.zstd`；本文不含任何 session id |

> [!note] 标注规则
> 未标注 = 已源码直读（行号精确到本次读到的版本）；**`未验证`** = 仅源码推断、本次未实测。

## 一、为什么这条管线决定一切：落盘的那条事件就是模型看到的那条消息

DSH 的会话是事件溯源的：`Session.append` 把事件推进内存日志（`dsh-session/lib/index.js:1200`），而「请求」不是另存一份的结构，而是**每轮从日志重新折叠出来**的（`dsh-agent-loop/lib/index.js:1204`，模块注释直言 "Every request is derived from the session log"，`:717-718`）。

中间那层投影只有一个函数：

```js
// dsh-session/lib/index.js:209-219
function deriveEventMessage(event) {
  switch (event.type) {
    case "user/message": return event.data;
    case "system/message":
    case "assistant/message":
      if (event.data.message.content.length === 0) return null;
      return event.data.message;
    case "tool/result": return event.data.message;   // ← 直接就是 message
    default: return null;
  }
}
```

于是「工具结果的落盘形态」与「模型读到的形态」是**同一份数据**，两者之间没有第二道转换点：

| 后果 | 证据 |
|---|---|
| 它成为持久日志里的一行 | `dsh-agent-loop/lib/index.js:703-712`（`session.append("tool/result", { turn, step, message, …result.meta })`） |
| 它是未来每一次请求里那条工具结果消息 | `dsh-session/lib/index.js:216`；请求由 `:1269-1284` 的 `deriveMessages()` 增量折叠，再由 `dsh-agent-loop/lib/index.js:1204` 交给 `buildRequest` |
| 执行期的规范值**不**落盘 | `dsh-tools/lib/types/index.d.ts:392`（`ToolExecutionSuccess.value`："deliberately omitted from durable events"）——落盘的只有 `content` 与 `meta` |

> [!warning] 这条推论的方向很重要
> 反过来读：**任何「事后」工具（离线改写日志）都慢一步**——内容在 append 的那一刻已经同时进了日志和下一次请求。想「让它根本不进来」，只能在 append 之前动手；而参数更早，见第六节。

## 二、接缝排名（最早生效的在前）

每条接缝的签名与模式取自类型声明，行为取自分派器实现。**「能改什么」一栏是这条接缝的真实能力边界**，超出即无效。

| # | 接缝 / 事件签名 | 模式 | 能改什么（能 / 不能） | 出处 |
|---|---|---|---|---|
| 1 | `system-prompt/assemble(assembly, context, next)` | waterfall | 可换整个 assembly（sections / tools / variables）——**管不了任何工具结果**；且「注册的完整 section 会在瀑布之后被恢复」，故不能添加或替换该 scope 的系统提示 | `dsh-system-prompt/lib/types/index.d.ts:15-27` |
| 2 | `tools/pre-execute(exec, next)` | waterfall | 只能 `{kind:'allow'}` / `{kind:'deny';reason}` / `{kind:'ask';reason?}`；**参数不可改写**——类型注释写明 "Input rewriting is excluded because arguments are already logged and presented" | `dsh-tools/lib/types/index.d.ts:38`、`:413-427`；派发 `dsh-tools/lib/index.js:3116-3139` |
| 2b | `ctx.tools.guard(fn)`（不是事件） | 同步、单调 | 只能收紧：返回字符串即拒绝，`undefined` 放行；**没有 allow 结果 ⇒ 监听器顺序无法把拒绝变回允许** | `dsh-tools/lib/types/index.d.ts:481-489`、`:620`；求值点 `dsh-tools/lib/index.js:3127` |
| 3 | `tools/execute(exec, next)` | waterfall | **环绕分派**：可超时/重试/度量；返回值会被注册表**重新规范化**，并成为下游每一个监听器看到的 `result`。只能替换 `exec.signal`（调用方 signal 会在函数体前重新融合），调用身份不可变 | `dsh-tools/lib/types/index.d.ts:49`；`dsh-tools/lib/index.js:3213-3214`、`:3447-3462` |
| 4 | `tools/post-execute(exec, result, next)` | waterfall | `{kind:'accept'; content?}`（只换展示投影）、`{kind:'accept'; value}`（换规范值 ⇒ content 与 meta 一起重派生）、`{kind:'block'; feedback}`（反馈变 error）；**`content` 与 `value` 互斥**，且**失败结果不能换 value** | `dsh-tools/lib/types/index.d.ts:61`、`:428-446`；`dsh-tools/lib/index.js:3377-3406` |
| 5 | `finalizeContent(exec, result)`（工具定义自带，不是事件） | 同步、恰好一次 | 只能换 `content`（返回值 `undefined` 表示保留）；「每个归一化结果恰好调用一次」，**失败的流水线也走**；必须是 total 且不抛异常 | `dsh-tools/lib/types/index.d.ts:119-131`；`dsh-tools/lib/index.js:3052-3053`、`:3266`、`:3274-3282` |
| 6 | `tools/result(exec, result)` | **emit** | 只读观察：结果已深冻结，无返回值通道，监听器异常被包含并只记警告 | `dsh-tools/lib/types/index.d.ts:76-83`；`dsh-tools/lib/index.js:3283-3302` |
| 7 | 支线：`tools/ptc-dispatch-log(dispatch, next)` | waterfall | 只改 **`run_code` 子调用在日志副本里**的 content（程序自己拿到的是完整值，模型两者都看不到） | `dsh-tools/lib/types/index.d.ts:62-75`、`:240-253` |
| 8 | `session.append(type, data, …)` | **无钩子** | 事件在内存日志里被推入（`:1200`）并校验形状；**没有任何 waterfall 能拦它**；重入直接报错 | `dsh-session/lib/index.js:1170-1210`（重入 `:1181`） |
| 9 | `session/event(session, event)` | emit | **提交后**、fire-and-forget 的追加快照：监听器快照在 push 之前解析、回调在 push **之后**运行，观察者失败不会让已提交的 append 失败 | `dsh-session/lib/types/index.d.ts:51-62`；`dsh-session/lib/index.js:1192-1202` |

### 2.1 顺序的直接后果：兄弟监听器看到的是「策略前」的结果

Cordis 的 waterfall 是 Koa 式的：**每个监听器拿到的是同一个原始参数**，`next()` 才进入内层链，最外层监听器的返回值即最终值（`cordis/lib/index.js:307-321`："Listeners run outermost-first; a listener that does not call `next()` vetoes the rest of the chain"）。

由此得到一条容易被忽略的性质：

> [!important] `tools/post-execute` 上的一个监听器，**改不了兄弟监听器已经读过的东西**
> - 先读 `result`、再 `next()` 的监听器，读到的是**本接缝入口处**的结果，而不是别人的替换结果；
> - 只有 `await next()` 之后改写 `decision.content` 的监听器，才能覆盖内层**已经产出**的投影。
>
> 两个 shipped 桥接就是这个形状：Claude Code 桥用 `result.content` 拼好 hook payload（`postToolPayload`，`dsh-hooks-claude-code/lib/index.js:375-383`，`blocksToText` 只取 text 块 `:343-345`）**之后**才 `next()`（`:265-291`，`next()` 在 `:281`）；Codex 桥同构（`dsh-hooks-codex/lib/index.js:245-262`，`next()` 在 `:261`；payload 在 `:338-342`）。**桥只看到原始结果，看到的不是同接缝上别人的改写。**

同一接缝上的先后由注册顺序决定，`{ prepend: true }` 让监听器排到**最外层**（shipped 的 spill 策略就是这么挂的，见第五节）。

## 三、meta 陷阱：换 `content` 不等于擦掉内容

> [!danger] 这是本文的核心，也是「工具报告成功、内容却还在」的成因
> `tools/post-execute` 的 `accept{content}` 分支实现是**展开原结果、只覆盖 content 一个键**：
>
> ```js
> // dsh-tools/lib/index.js:3401-3405
> return this.markCanonical(exec, {
>   ...result,
>   ...decision.content !== void 0 ? { content: decision.content } : {},
>   ...additionalContexts.length > 0 ? { additionalContexts } : {}
> });
> ```
>
> `meta` 不在被覆盖之列 ⇒ **它带着原文活下来**。而 `meta` 会在 append 时被逐字写入：
>
> ```js
> // dsh-agent-loop/lib/index.js:707-708
> ...result.error?.info ? { error: result.error.info } : {},
> ...result.meta !== void 0 ? { meta: result.meta } : {}
> ```
>
> 类型声明把这件事写得很直白：`meta`「**is persisted verbatim** on `tool/result`」，核心对它不透明，**持久日志在 replay 时复现完全相同的卡片**（`dsh-session/lib/types/types.d.ts:340-361`、`dsh-tools/lib/types/index.d.ts:180-186`）。

### 3.1 `web_search`：同一段文本的两条通道

| 通道 | 代码 | 同一段文本怎么进去的 |
|---|---|---|
| 渲染文本（→ `content`） | `dsh-tool-web/lib/index.js:62-79` | `meta.push(source.snippet)` 后拼进 markdown 源列表（`:69-72`）；答案 `result.content` 直接 `parts.push`（`:64`） |
| 持久 `meta`（→ `presentationMeta`） | `dsh-tool-web/lib/index.js:118-124`，挂载点 `:303` | `sources: value.sources.map(projectSource)`，而 `projectSource` 原样带上 `snippet`（`:103-109`）；答案进 `answer`（`:122`） |

**所以对 `web_search` 的「只改 content」= 同一段 snippet 仍以 `meta.sources[].snippet` 落盘**，并在 UI/replay 卡片里继续出现。

> [!note] 一个必须记住的对照：`web_fetch` 不在同一个形状里
> `web_fetch` 的 `presentationMeta` 只投影 `{ url, statusCode, truncated }`（`dsh-tool-web/lib/index.js:670-675`、挂载点 `:799`），**正文不在 meta 里**。但结论不是「web_fetch 安全」：`url` 本身就是持久字段，且它同样由 content 替换路径保活——命中 URL 的脱敏同样会漏。

### 3.2 正确动作：换 `value`，让注册表自己重算两条投影

`accept{value}` 走的是另一条路：

```js
// dsh-tools/lib/index.js:3391-3399
if (Object.hasOwn(decision, "value")) {
  if (result.isError) throw new TypeError("tools/post-execute cannot replace the value of a failed result");
  const tool = this.resolveExecution(exec.name, exec.agent, exec.parent !== void 0);
  ...
  const replaced = this.createSuccessResult(exec, tool, decision.value);
```

而 `createSuccessResult` 是唯一的规范化入口，它一次性把三条投影都从 value 重算：

```js
// dsh-tools/lib/index.js:3415-3445（摘）
const detached = snapshotToolValue(tool.name, candidate);
const violations = validateJsonSchemaValue(tool.output.schema, detached, "value");   // :3417
if (violations.length > 0) throw new ToolOutputError(tool.name, violations);          // :3418
const value = deepFreeze(detached);
rendered = tool.output.render(exec.arguments, value);                                // :3422
meta = tool.output.presentationMeta(exec.arguments, value);                           // :3428-3436
```

**换 value ⇒ `content` 与 `meta` 同时变成干净的**；只换 content ⇒ 只有前者。

### 3.3 换 value 的两条硬约束

| 约束 | 说明 | 出处 |
|---|---|---|
| 必须仍满足工具的 `output.schema` | 违规抛 `ToolOutputError`，随后被 `catch` 转成**终态错误结果**（`INVALID_TOOL_OUTPUT`）——**整条调用变成错误**，不是静默保留 | `dsh-tools/lib/index.js:3417-3418`、`:3226-3231`、`:3447-3462` |
| **失败结果不可换 value** | `throw new TypeError("tools/post-execute cannot replace the value of a failed result")`；失败结果只能重建 `{isError:true, error, content}`（重建时会丢 meta），或 `block` | `dsh-tools/lib/index.js:3392`、`:3380-3387`、`:3449-3455` |

补充两条同形状的事实：

- `accept` 决策**不能同时**给 `content` 与 `value`（`:3389` 显式抛错）——这正是「展示策略 vs 内容策略」互斥的落地形式。
- `finalizeContent` 也是 `{...result, content}`（`:3274-3282`）：**它同样改不动 `meta`**。第 5 与第 4 号接缝在这一点上完全同形。

> [!tip] 一句话判据
> 判断一个结果改写策略是否真的生效，**不要看它是否报了成功**，要同时核两处：`result.content` 里还有没有命中文本，以及 `tool/result` 事件的 `data.meta` 里还有没有。只核前者，就是 [[CORRECTIONS]] C-005 的形状（自检通过 ≠ 读取端干净）。

## 四、一次工具调用的端到端顺序

每一步都给出唯一出处；括号内是「这一步之后，什么已经确定」。

1. **参数落盘**：`appendToolCall()` 把模型产出的原始 `arguments` 字符串写进 `tool/call`（`dsh-agent-loop/lib/index.js:586`，实现 `:688-694`）。（此刻参数的命运已定——没有任何接缝能改写它。）
2. **落盘检查点**：shipped 的 checkpoint 策略在 `tools/execute` 外层 `await ctx.sessions.flush(...)`，让已记录的 call 先 durable，再让函数体开跑（`dsh-session-checkpoint-policy/lib/index.js:66-71`；声明 `lib/types/index.d.ts:12-18`）。
3. **`tools/pre-execute`**：waterfall 出 allow/deny/ask（`dsh-tools/lib/index.js:3116`）；`ask` 经审批服务解析（`:3117-3126`）；`allow` 时再过单调 guard（`:3127`）。deny 会直接物化一个 error 结果并**跳到 post-execute**（`:3128-3139`）——所以「拒绝」也走第 6 步。
4. **`tools/execute` 环绕 → 工具体**：`ctx.waterfall(carrier, "tools/execute", mutableExec, () => this.dispatchToolBody(...))`（`:3213`）；函数体返回规范值后立刻 `createSuccessResult`（`:3192-3193`）。
5. **规范化**：wrap 的返回值经 `normalizeDispatchResult`（`:3214`、`:3447-3462`）——非本 token 规范化的成功结果会**重新走一遍 schema 校验 + render + presentationMeta**。
6. **`tools/post-execute`**：`ctx.waterfall(..., "tools/post-execute", exec, result, …)`（`:3378`），应用 accept/block（`:3380-3405`）。
7. **`finalizeContent`**：定义自带的最后一公里变换（`:3266`、`:3274-3282`），在 post-execute **之后**。
8. **`tools/result`**：`Object.freeze(exec)` 后 emit，结果深冻结，观察者异常被包含（`:3283-3302`）。
9. **durable append**：agent-loop 的提交循环按模型顺序 `appendToolResult(...)`（`:571-582`、`:697-712`）——把 `message`（由 `result.content` 构造）与 `result.meta` 写进 `tool/result`。
10. **下一次请求从日志折叠**：`session.deriveMessages()`（`dsh-agent-loop/lib/index.js:1204`）→ 第 1 节那条投影规则 → 这条结果成为请求里的一条消息。

> [!warning] 第 9 步的「落盘」是异步滞后的
> `session.append` 只是把事件推入**内存**日志并运行提交后观察者（`dsh-session/lib/index.js:1200-1202`）；真正 durable 由检查点在**下一个边界**触发：下一个 `llm/stream` 请求前、下一个 `agent/pre-step` 前、或下一次顶层工具分派前（`dsh-session-checkpoint-policy/lib/index.js:61-75`）。
> 两个后果：① 「append 之后立刻读文件」不一定读得到；② 并行组里各调用虽可重叠执行，**结果的提交顺序仍是模型顺序**（`dsh-agent-loop/lib/index.js:571-582` 的 `commitReady`），所以第 4～8 步的完成时刻与第 9 步的先后**可以不一致**。

## 五、平台已经做了什么：`dsh-spill-policy` 的边界

shipped 的体量约束策略挂的就是 4 号接缝（`{ prepend: true }`，`:155-172`）。

| 维度 | 事实 | 出处 |
|---|---|---|
| 配置开关 | `maxInlineBytes`（UTF-8 字节）。**省略 ⇒ 插件一个监听器都不注册**（真真空操作）；shipped 组合里给了 `50000` | `dsh-spill-policy/lib/types/index.d.ts:49-56`；`dsh-spill-policy/lib/index.js:74`、`:104`；`dsh-base/cordis.patch.yml:383-386` |
| 触发 | 决策不是 value 替换、且 `exec.parent === void 0`、且工具名不是 `read` 时，取最终 content 拍平成纯文本，超过预算即触发 | `dsh-spill-policy/lib/index.js:157-161` |
| 它做什么 | 全文存进会话级 spill 工件（`ctx.spillStore`），模型看到的是**头尾预览 + 「省略 N bytes · Full formatted result stored at: <locator>」+ 取回提示** | `dsh-spill-policy/lib/index.js:114-153`、`:21-23`、`:88-101` |
| **明确的适用范围限制** | 「**仅纯文本**：只要结果里含任何非 `text` 块就整体不处理」——`flattenPlainText` 遇非 text 块返回 `undefined`；嵌套复合调用跳过面向模型的那条 arm；`read` 跳过以避免 `read → spill → read` 循环；无 session owner / 无后端 / 保存失败一律保留原样 | `dsh-spill-policy/lib/index.js:75-83`；`dsh-spill-policy/lib/types/index.d.ts:18-41` |
| 第二条 arm | 同一预算也用在 `tools/ptc-dispatch-log` 上，约束 `run_code` 子调用**日志副本**的 content | `dsh-spill-policy/lib/index.js:173-185` |
| **它留下的缺口** | ① **结构化结果完全不碰**（`web_search` 这类 `output.schema` 为对象的工具，`dsh-spill-policy/lib/index.js:75-83`）；② 它是 `accept{content}`，因此**同样不 bound `meta`**（`dsh-tools/lib/index.js:3401-3405` 的展开路径）——即超长结构化结果里的 `meta` 可以原样进日志（源码推断，端到端 `未验证`） | `dsh-spill-policy/lib/index.js:155-172` |

> [!info] 缺口就是位置
> 「量大但你可能要看」→ 调 `maxInlineBytes`；「**这类字段你根本不想要**」→ 需要一条**结构化最小化**策略补在 `tools/execute`（更早，见第七节）。本机 `web` profile 的补丁层与 home 级补丁层都没有覆盖 `spill-policy`（`dsh plugin` 侧的 `profiles/web/cordis.patch.yml` 只有 `compaction-basic` 一条），故生效值就是 shipped 的 `50000`——**若启动时另有 `--patch` overlay 则不适用**。（本地插件 README 记其机器上是 `4000`，本次未复核。）

## 六、没有任何接缝能修的

> [!warning] 下面每一条都是「管线边界」，不是「还没找到钩子」
> 1. **工具调用参数**：`appendToolCall()` 在 `tools/pre-execute` **之前**（`dsh-agent-loop/lib/index.js:586` 早于 `:588`），且 `PreToolDecision` 根本没有改写字段（`dsh-tools/lib/types/index.d.ts:416-417`）。`deny` 只能阻止执行与结果产生，**参数早已入库**。
> 2. **已经落盘的内容**：本文所有接缝都在 append 之前；历史日志属于 [[DSH会话日志格式与读取端约束]] 与 [[DSH会话持久化与活跃改写安全]] 的范围。
> 3. **已经发给 provider 的内容**：改写只影响从此刻起的后续请求。
> 4. **工具自己写的文件**：`write` / `edit` / pwsh 落盘的任何东西——包括 spill 工件本身（`ctx.spillStore` 保存的是**原文全文**，`dsh-spill-policy/lib/index.js:114-153`）。
> 5. **子代理 / workflow 的产出**：它们有**自己的会话与会话日志**，本管线的接缝按 scope 过滤派发（agent-scoped 监听器只收到自己 agent 的调用），跨 agent 不生效。
> 6. **模型自己的输出**（assistant 消息、思考块）与**系统提示**——`system-prompt/assemble` 管的是提示词组装，不是工具结果。
> 7. **`user/message`**（用户输入与注入的 context）。
> 8. **工具自带 `finalizeContent` 若从参数重拼 content**：顺序上它在 `tools/post-execute` **之后**（`:3243` → `:3266`），所以它的 content 是最终值。**未验证**：本机 shipped 工具中是否存在这种从参数重拼的实现（我确认了顺序，未找到实例）。

## 七、给「结果改写 / 结构化最小化」策略的实现检查清单

1. **选接缝：结果改写选 `tools/execute`**——它最早（规范化之前），且它的返回值会被注册表重新规范化后交给下游所有监听器（`dsh-tools/lib/index.js:3213-3214`、`:3447-3462`）。次选 `tools/post-execute` + `accept{value}`。不要指望 `pre-execute` 改参数（不可能），不要在 `tools/result` 上白费力气（emit、只读、结果已冻结）。
2. **改 `value`，不改 `content`**。理由只有一条：`content` 与 `meta` 两条投影都从 value 派生（`createSuccessResult`），而只换 content 的分支展开原结果、保活 `meta`（第三节）。
3. **改完必须仍满足 `output.schema`**：先读 `ctx.tools.get(name, scope).output.schema` 判定哪些键是 required（编译后的对象级 `required` 数组），注意 `additionalProperties: false` 下不能加键；违规 = **整条调用变成终态错误**（`:3417-3418` → `:3226-3231`）。
4. **无法安全改写时，宁可响亮失败**：`block`（把纠正反馈变成 error 结果，`:3380-3387`）或让策略自身拒绝装配；**不要**静默保留载荷——那等于策略没生效却报告成功。
5. **失败结果走另一条路**：没有 value 可换（`:3392`），只能重建 `{isError:true, error, content}` —— 重建即丢 `meta`（`:3449-3455` 是这条路径的形状）。
6. **查不到 schema 就放行并告警**，不要猜 required；真违约时注册表会抛 `ToolOutputError`（响亮，不静默）。
7. **注意嵌套与日志副本**：`exec.parent !== void 0` 的嵌套子调用**不产 `presentationMeta`**（`:3428`），也不进模型历史；`tools/ptc-dispatch-log` 那条接缝**只有 content 块**（`dsh-tools/lib/types/index.d.ts:240-253`），value 级改写在那里无从下手。
8. **同接缝顺序要有意为之**：默认注册顺序 = 后来者在内层；`{ prepend: true }` = 最外层。想让别人看到你的输出、想连别人的替换一起被约束，就用 prepend（shipped 的 spill 策略正是这个形状，`:155-172`）；想看到别人已产出的投影，就 `await next()` 之后再改。
9. **日志只记计数，不记命中文本**：改写策略的日志/通知里只出现「工具名 + 规则 id + 计数 + 字节数」，绝不打印被处理的原文。
10. **不要声称做了你没做的事**：只改 content 的实现必须在文档里写明「`meta` 未处理」，否则下一个人会以为日志干净了。

> [!note] 既有实现参照（本地未发布仓库）
> `C:\%USERPROFILE%\dsh-redaction\packages\dsh-plugin-content-policy\README.zh.md` 是这条管线上**预防式**的对应物：挂在 `tools/execute`，成功后按字段路径做结构化最小化（`strip[]` / `stripDefaults`）再跑内容改写（`rules[]`），并把它自己的接缝表（含「只换 content 会留下旧 meta」「meta 会被持久化」「失败结果不能替换 value」三条）逐条对到 shipped 源码。它是「改 value 而不是 content」这一取舍的现成落点——本文不复述其配置细节。

## 八、未验证 / 待确认

| 项 | 状态 |
|---|---|
| `dsh-spill-policy` 不 bound `meta` 的端到端实测 | **未验证**（源码推断：`dsh-spill-policy/lib/index.js:155-172` 的 accept-content ＋ `dsh-tools/lib/index.js:3401-3405` 的展开） |
| 本机 shipped 工具中是否存在「`finalizeContent` 从参数重拼 content」的实现 | **未验证**（顺序已确认：`dsh-tools/lib/index.js:3243` → `:3266`；未找到实例） |
| 同一接缝上多个改写者同时给 `accept{value}` 时「谁赢」的实测 | **未验证**（规则上由注册顺序决定，但本次未构造夹具） |
| 本地插件 README 记的 `maxInlineBytes: 4000` 与本机 shipped `50000` 的差异 | **未复核**（本机 `web` profile 与 home 级补丁层均无该行；其余 profile 与启动 overlay 未穷尽） |
| 本文全部结论的运行期实测 | 本文**未新增**运行时实验；结论为源码直读，或引自本库已有实测报告 |

## Related

- [[DSH插件与Hook开发最佳实践]] — 工具定义字段、pre/post-execute 与 hooks 桥接的上游规范（本文只补「顺序与 meta」这一层）
- [[DSH会话日志格式与读取端约束]] — 落盘之后：`tool/result` 在盘上的形状与读取端接纳规则（本文刻意不展开）
- [[DSH会话持久化与活跃改写安全]] — 已落盘内容的改写安全（「事后」那条路）
- [[DSH会话脱敏插件缺陷档案]] — 把「自检通过」当「读取端验收」的完整失败样本族
- [[DSH会话脱敏项目方法论复盘]] — 这些缺陷为什么能活到红队介入
- [[DSH插件组合与启动中止语义]] — 插件行挂载失败如何中止整个 profile（配置校验属共享启动路径）
- [[CORRECTIONS]] — 出结论前的回查入口（C-005 / C-009 与本主题直接相关）
- [[AI-Links-KB-Home]] — AI 链接收藏库 MOC
