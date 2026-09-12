---
title: DSH-TUI 内部机制与键盘卡死陷阱
aliases: [tuiDialogs, 命令结果渲染, 200格截断, 键盘让出]
tags: [ai/tools, ai/agent]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# DSH-TUI 内部机制与键盘卡死陷阱

See also: [[DSH-TUI插件使用手册]] | [[DSH插件与Hook开发最佳实践]] | [[AI-Links-KB-Home]] | [[DSH提效与Token插件调研]] | [[AGENTS]]

> [!abstract] 这份文档解决什么问题
> [[DSH-TUI插件使用手册]] 是**使用者视角**（怎么装、怎么跑、有哪些功能）；本文是**插件作者视角**：dsh-tui 给插件开了哪几道缝、每道缝的真实边界，以及**为什么把对话框的 Promise 停进宿主的 store 会让用户键盘失去响应**。
> 目的很具体：让你在**动笔写代码之前**就能判断「我这个插件会不会锁住终端」。
>
> **结论先行**：`ctx.tuiDialogs` 是唯一能"让用户从列表里选一项"的缝，也是唯一**能让终端失去键盘**的缝。不用它 ⇒ 结构上不可能冻结。

## 一、证据基线与引用约定

所有 `文件:行号` 都指**本机安装的那一份打包产物**（tsc 输出，不是源码仓库）；下文裸写的 `xxx.js` 一律指安装根下的 `lib\types\dsh-adapter\xxx.js`，`Chat.js`/`PromptInput.js`/`ExtensionDialog.js` 则分别在 `lib\types\screens\` 与 `lib\types\components\` 下；`index.js` 与 profile 补丁层另行标注。
基线：包 `@deepseek-harness-tui/dsh-tui` **0.10.1**，安装根 `C:\%USERPROFILE%\.dsh\profiles\dsh-tui\node_modules\@deepseek-harness-tui\dsh-tui\`（即 `$DSH_HOME/profiles/dsh-tui/…`），文件时间 2026-09-12 15:13（全部同步）。

| 文件 | 字节 | SHA256（前 8 … 后 8） |
|---|---|---|
| `lib\types\screens\Chat.js` | 216863 | `2EC8C096…F06EEFDA` |
| `lib\types\components\PromptInput.js` | 166373 | `11BA0956…234C799F` |
| `lib\types\components\ExtensionDialog.js` | 13126 | `AE87EC11…4484CAEE` |
| `lib\types\dsh-adapter\dialogs.js` | 15334 | `83108BCE…A6A5CCF3` |
| `lib\types\dsh-adapter\sanitize.js` | 3765 | `A5D33327…773AA92B` |
| `cordis.patch.yml` | 22044 | `2B3E5D32…416DC5D3` |

> [!warning] 引用前提
> **行号随版本漂移**（打包产物，升级即失效，改版后请按 SHA256 复核）；`Chat.js` 的部分行是几千字符的 JSX，标 `:3585` 指**那一行**而非列；凡我没亲自跑出来的，一律标 **未验证**。

---

## 二、命令面：注册、准入、渲染

### 2.1 注册与"白名单"问题

宿主侧服务是 `@deepseek-ai/dsh-commands`（`ctx.commands`，装于 `$DSH_HOME/profiles/node_modules/`）。插件用 `ctx.commands.register({ name, description, input?, handler })` 注册，`handler` 返回 `{ kind: 'success' | 'error', text }`；**命令与结果都不会变成模型消息**（`@deepseek-ai/dsh-commands/README.zh.md:32-46`）。同一作用域重复注册同名命令**会抛异常**（同上 `:46`）。

**没有名字白名单**。注册本身是开放的，真正存在的两道门是：

| 门 | 位置 | 拒绝时的表现 |
|---|---|---|
| 语法/名字解析 | `dsh-commands` 的 `execute()`；未知名或不合法语法返回 `undefined` | TUI 弹 `command-not-found`（`screens/Chat.js:1078-1081`） |
| `commands.invoke` 授权 | `dsh-adapter/channel/external-commands.js:16-32` 的 `authorize()`，读统一 GrantStore | 红色提示 "invocation denied"，不执行 handler |

授权按**归属**判定：命令所有者由 plugin-host 行通过 `registerCommand(pluginCtx, definition)` **中介注册**时打标（`dsh-adapter/command-attribution.js:12-24`）。直接 `ctx.get('commands').register()` 注册的命令**没有归属**，只按 root 授权检查——归属只会**收紧**检查，不会放宽（同文件 `:20-24`）。

### 2.2 渲染约束（本节的每一条都是硬约束）

命令结果的 `text` 不会原样显示。它先过 `cleanRenderText(text, COMMAND_RESULT_CELLS)`：常量 `COMMAND_RESULT_CELLS = 200`（`screens/Chat.js:120`），调用点在 `screens/Chat.js:1082`，实现（`dsh-adapter/sanitize.js:26-35`）：

```js
const flat = withoutAnsi.replace(/[\x00-\x1f\x7f-\x9f]/g, ' ').replace(/\s+/g, ' ').trim();
if (stringWidth(flat) <= maxCells)
    return flat;
let out = '';
for (const ch of flat) {
    if (stringWidth(out + ch) > maxCells - 1)
        break;
    out += ch;
}
return `${out}…`;
```

两件事同时发生，都绕不过去：

1. **所有空白被压平**：`\n`、`\t`、连续空格全部并成一个空格 —— **多行输出必然变成一行**。
2. **按 200 个显示格截断**，末尾补 `…`。宽度是终端显示格，**CJK 一字算 2 格** → 中文实际只有约 100 个字的预算。

再叠上通知条本身的形态：`channel.notifications` **只渲染最后一条**（`components/PromptInput.js:2710`），且是一个 `position: absolute`、`height: 1`、`wrap: "truncate"` 的单行浮层（同文件 `:3066`），默认 4 秒后消失（`dsh-adapter/channel/notifications.js:6`）。handler 抛异常走 `cleanCommandError`（`Chat.js:121-129`），同样受 200 格限制。

> [!warning] 四条实践后果（照这个前提设计，而不是事后补救）
> 1. **插件的输出永远是一行**——想排版成多行，一定被压平。
> 2. **最重要信息必须放最前**。备份文件名、拒绝原因、下一步出路都往前挪；尾巴被砍是常态而不是意外。
> 3. **不要围绕"从通知里复制一长串东西"设计工作流**。长路径/长行号可能已被截掉，通知条本身也不好选中，而且 4 秒后就没了。
> 4. **自己先截断**，别等渲染端砍。装出去的命令若返回长文本，应该在 handler 里就先按同一规则收敛（见 §七 的 `clamp`/`clampResult`）。

> [!tip] 分页与"少列几条"
> 200 格装不下时，正确做法是**按显示格预算主动少列几条**并给出后继指引（`…另M个` / `续 /redact nodes 2`），而不是把关键字段挤掉。分页要按**格数**切块，不能按固定条数——固定 8 条/页时若一页只放得下 3 条，第 4~8 条将永远看不到。

---

## 三、其它扩展面：各自能做什么、不能做什么

`dsh-tui-extensions` 一行挂载全部插件面服务（`cordis.patch.yml:321-322`；实现 `dsh-adapter/extensions.js:43-51`：`tuiDialogs` / `tuiStatus` / `tuiShortcuts` / `tuiRenderers` / `tuiToast` / `tuiThemes`）。逐个体检：

| 缝 | 能呈现什么 | 用户能"从列表里选"吗 | 会占住键盘吗 | 最坏后果 |
|---|---|---|---|---|
| 命令结果通知 | 单行、≤200 格、4s | ❌ | 不会 | 截断/被下一条覆盖 |
| `tuiToast.show()` | 单行 ≤200 格 | ❌ | 不会 | 被限流丢弃；无 sink 时返回 `false` |
| `tuiStatus.set(key,text)` | 单行 ≤200 格，最多 20 条并列 | ❌ | 不会 | 超限被拒 |
| `tuiStatus.registerView()` | 宿主 React 组件，`maxRows` 1–3，**全局 6 行预算** | ❌（拿不到按键） | 不会 | 超预算被拒 |
| `tuiShortcuts.register()` | 一个组合键 → handler | ⚠️ 只能"按键 N = 第 N 项" | 不会 | 组合键被拒 |
| `tuiSettingsSections.register()` | 设置屏里的一段字段（**只是显示元数据**） | ❌ | 不会 | 非法 ns 会抛 |
| `tuiScenes.register()` + `open()` | 整屏自定义界面，自己 `useInput` | ✅ 但要自己实现，且**整屏替换对话** | 不夺输入框 | 崩了有关闭边界 |
| `tui/rewind-prompt` 决策事件 | ❌ 只由 `/rewind` 发起 | ❌ | — | 默认拒绝（需显式授权） |
| **`tuiDialogs.select`** | **多行列表 + ↑/↓ + description** | **✅ 唯一现成的** | **会（无条件）** | **键盘死锁** |

关键数字与依据：

- **toast**：文本 200 格、默认 4000ms、下限 500 / 上限 12000、**每分钟最多 20 条**（`toast.js:20-26`）；`show()` 在无 sink 或超限时返回 `false`（`:93-152`）。**没有 `hasSink()` 之类的插件面探针**——它只在 host-only 的 store 上（`:39-41`）。
- **status**：文本 `TEXT_CELLS=200`、`MAX_ENTRIES=20`、键必须是 `plugin` 或 `plugin:sub` 形态的小写 slug（`status.js:21-25`）；富视图 `MAX_VIEW_ROWS=3`、`MAX_VIEW_ROW_BUDGET=6`（`:24-25`），`registerView` **被拒时返回 `undefined`**（注释 `:290-293`，实现 `:295-392`），所以它是**可拿来做"我是否被宿主接纳"探针**的缝——但它拿不到 `input`/`channel`/原生终端，只拿到指针型 UI 组件（`Chat.js:110-117` 的 `STATUS_VIEW_UI`），因此**做不了选择**。
- **快捷键**：必须带 ctrl/alt；保留组合键在注册期就被拒（`shortcuts.js:11-18`、`:149-167`）。分发是**火后不管**（`:226-241`），Chat 侧只在"干净聊天态"匹配，浮层/对话框/整屏期间不匹配（`Chat.js:3328-3336`）。
- **场景**：`open()` 对未注册 id 返回 `false`（`scenes.js:124-128`、`:166-171`）；场景打开时 Chat 直接早返回整屏渲染它（`Chat.js:3377-3383`），键盘归场景自己（`Chat.js:2477-2479` 注释）。
- **`tui/rewind-prompt`**：只在 `/rewind` 确认一条消息时发起（`dsh-adapter/channel.js:380-393` → `channel/session-actions.js:5-28`），返回 `'cancel'` / `{modes}` / `null`，插件**无法主动触发**；它属于 intercept 类决策事件，需要 `session.rewind.intercept` 授权（`adapter/spec/protocol-constants.js:81-86`），授权文件 `~/.dsh-tui/extension-grants.json` **默认拒绝**（`dsh-adapter/extensions.js:17-26`；`decision-guard.js:1-19`）。本机上该文件**不存在**（`~/.dsh-tui/` 目录存在，无 `extension-grants.json`）⇒ 当前一律拒绝。

> [!warning] 上表里唯一"开箱即用"的可选列表只有 `ctx.tuiDialogs.select`——`tuiShortcuts` 只能凑出"按键 N 执行第 N 项"，`tuiScenes` 要整屏替换并自己实现选择逻辑，`registerView` 只读且拿不到按键。

---

## 四、`ctx.tuiDialogs`：契约与边界

服务是 `TuiDialogRuntime`（`dsh-adapter/dialogs.js:182-299`），三个方法：`select` / `confirm` / `input`，各有 `(request)` 与 `(owner, request)` 两种重载（`.d.ts:133-141`）。

### 4.1 请求形状与校验上界

| 项 | 规则 | 证据 |
|---|---|---|
| `select` | `{ title, options: [{ id, label, description? }], signal?, timeoutMs? }` | `dialogs.js:216-249` |
| `confirm` | `{ title, message?, confirmLabel?, cancelLabel?, signal?, timeoutMs? }` | `:250-277` |
| `input` | `{ title, placeholder?, initial?, signal?, timeoutMs? }` | `:278-298` |
| 标题/标签 | 120 显示格；清洗后为空 → **拒绝**（`select` 回 `undefined`，`confirm` 回 `false`）+ 一条 warn | `:31-32`、`:237-240`、`:255-259` |
| `message` | 400 格；空则整个字段省略 | `:33`、`:260`、`:267` |
| 选项数 | 上限 **100**，超出**静默截断保留前 100** | `:38`、`:224` |
| 选项 `id` / `label` | `id` 必须是**非空字符串**且**原样保留**（它是回给插件的令牌，不清洗）；`label` 清洗后为空（含只有控制字符）→ 该选项被**静默丢弃** | `:225-232` |
| `input` 值上限 | `INPUT_CELLS = 500`，面板在**每一条编辑路径**（打字与粘贴）都强制 | `:34-37`；`.d.ts:77-80` |
| 默认超时 | `DIALOG_DEFAULT_TIMEOUT_MS = 30_000`；`timeoutOf()` 把"缺失/非数/≤0"一律映射成它，并把有效值夹到 **24h** | `:39-40`、`:211-215` |

> [!warning] store 层**没有**"默认超时"这回事
> `TuiDialogStore.ask()` 只认调用方传入的 `timeoutMs`（`dialogs.js:100-102`）；默认 30000 是**服务层**补的。谁直接 `new TuiDialogStore()` 且不传超时，谁就能造出**永久挂起**。

### 4.2 Promise 语义：畸形请求不抛，只有一条路会抛

`select` / `confirm` / `input` 全部遵循同一约定：**请求非法 → 只写一条 logger warning + 返回取消值**（`undefined` / `false`），**绝不抛异常**（契约写在 `.d.ts:119-124`，实现见 `dialogs.js:237-248`、`:255-276`、`:284-297`）。

- 取消值统一语义：`select`/`input` → `undefined`，`confirm` → `false`；`select` 只把**字符串**当选择，`confirm` 只把 `=== true` 当确认（`dialogs.js:243`、`:271`）。
- 结束一个请求的六种方式：用户作答、Esc 取消、调用方 `AbortSignal`、调用方超时、服务卸载、以及入队时归属绑定失败。`decide`/`cancel` **按 key 校验**：key 不匹配就忽略（`:129-146`）。
- **唯一真实的抛错路径**：`assertCapabilityShadowPolicy(...)` 写在 `try` **之外**（`dialogs.js:217`、`:251`、`:279`）。在 `DSH_TUI_ADAPTER_MODE=passive-shadow | replay-shadow` 下会**同步抛** `shadow policy denies mutate in <mode> mode`。插件把 `await` 包在 `try/catch` 里就能转成"看得见的失败"。

---

## 五、键盘死锁：三件套 + 一个不对称

> [!danger] 冻结不是插件的 bug，是"把 Promise 停进一个不保证被渲染的 FIFO"的必然代价：只要 store 里出现 `active`，**键盘就已经不属于用户了**——至于面板会不会出现，是另一件独立、且**不受插件控制**的事。

### 5.1 三件套（缺一不可）

**（1）Promise 停在 store 里成为 `active`。** `ask()` 把请求推进 FIFO（`dialogs.js:112-113`），`advance()` 把它提升成 `this.active`（`:164-169`），`getSnapshot()` 返回 `this.active?.snapshot ?? null`（`:117-119`）。插件的 `select()` 就是一个只会被上述六种方式之一结束的 Promise。

**（2）`Chat` 无条件让出键盘。** `Chat.js:2562-2567`：

```js
// The questionnaire / approval panel / managed plugin dialog owns the
// keyboard while one is pending … the prompt input is suspended.
if (questionSnapshot !== null || approvalSnapshot !== null || dialogSnapshot !== null)
    return;
```

这是 Chat 全局 `useInput`（注册于 `Chat.js:2447`）里的一条**无条件让出**：对话框一挂起，Chat 后续所有键（Esc / Ctrl+C / Ctrl+D / 全部快捷键）都不再处理。

**（3）输入框被停用。** `PromptInput` 的监听器 `isActive: !suspended`（`PromptInput.js:2456`），而 `suspended` 来自 `Chat.js:3478-3483 promptReplacementOpen`，其中包含 `dialogSnapshot !== null`。光标还在闪，但**打字完全没有反应**——这就是"卡死"的主观体感。

### 5.2 不对称：面板只有一个挂载点，而且 approval 优先

`ExtensionDialog` 在整个 screens 树里**只有一处实例化**（`Chat.js:28` 的 import 与 `:3585` 的挂载）。挂载点是提示槽 children 的三元链（`Chat.js:3585`，节选）：

```js
approvalPanelNode !== null ? (approvalPanelNode)
: dialogSnapshot !== null ? (<ExtensionDialog dialog={dialogSnapshot} … />)
: overlay.kind === 'tips' ? …
: questionPanelNode !== null ? (questionPanelNode) : null
```

**approval 面板排在最前**。于是：`approvalSnapshot !== null` 时，插件对话框**永远不会挂载**，而 store 里的 `active` 依然存在。而 `ApprovalStore` **没有任何超时**（`dsh-adapter/approvals.js` 全文无 `setTimeout`，只在 abort / 卸载时回收）⇒「有审批挂着」是一个**稳态**，不是瞬态。

### 5.3 键盘让出后，谁还听得见按键？

- 让出者 `Chat.js:2566`（Chat 的监听器注册在先，它先跑、先 return）；接管者**只有挂载出来的 `ExtensionDialog`**（三个子面板各自 `useInput(..., { isActive: true })`，Esc/Ctrl+C → `onCancel()`：`ExtensionDialog.js:66-70`、`:112-116`、`:174-178`）；`PromptInput` 已停用。
- **没有任何兜底监听者。** 且 **Ctrl+C 也不会退出程序**：整个 TUI 以 `exitOnCtrlC: false` 渲染（`dsh-adapter/plugin.js:1536`），App 级退出分支只在 `props.exitOnCtrlC` 为真时生效（`ink/components/App.js:481-485`），Chat 自己的 Ctrl+C 分支（`Chat.js:3250`）在 `:2566` 就被 return 挡掉了。

⇒ **面板没挂载时，`Esc` 与 `Ctrl+C` 都没有语义，程序也退不出去。**

### 5.4 死锁状态矩阵

除 approval 抢占外，`Chat.js` 还有一整排**整屏早返回**，每一条都让 `:3585` 整体不执行，而键盘让出依旧成立（行号均在 `Chat.js` 内）：`:3360 interruptPanel + screenOpen`、`:3378 插件 scene`、`:3388 agentView`、`:3408 会话浏览器`、`:3421 会话树`、`:3430 设置屏`、`:3436 subagent 详情`、`:3452 jobs 面板`、`:3464 subagent 仪表盘`、`:3492 轨迹屏`；另有 `:3506-3507`（`overlay.kind === 'permission'` 且三面板任一非空 → 浮层不挂载）与 `:3585`（approval 在链上抢在 dialog 之前）。

状态矩阵（`dialogSnapshot !== null` = 键盘已让出）：

| 状态 | 面板挂载 | Chat 让出键盘 | 输入框 | 结果 |
|---|---|---|---|---|
| 理想态：只有对话框挂起 | ✅ | ✅ | 停用 | 正常（面板可操作） |
| **A1：有 approval 挂起** | ❌（`:3585` 抢占） | ✅ | 停用 | **死锁** |
| **A2：approval + 整屏** | ❌（`:3360`） | ✅ | 停用 | **死锁** |
| **B1：插件 scene 打开** | ❌（`:3378`） | ✅ | 停用 | **死锁** |
| **B2：会话浏览器** | ❌（`:3408`） | ✅ | 停用 | **死锁** |
| **B3：设置屏** | ❌（`:3430`） | ✅ | 停用 | **死锁** |
| **B4：jobs 面板** | ❌（`:3452`） | ✅ | 停用 | **死锁** |
| **B5：subagent 详情/仪表盘** | ❌（`:3436`/`:3464`） | ✅ | 停用 | **死锁** |
| C：无对话框（对照） | — | 不 | 活跃 | 正常 |
| D：只有 approval（对照，正常审批 UX） | ✅ | ✅ | 停用 | 正常 |

> [!bug] 这张矩阵的来源要如实说明
> 上表是**逐条转写 `Chat.js` 判据表达式**在状态空间上求值的结果，**不是** headless 挂载真实 `Chat` 跑出来的（`Chat` 不在包的 `exports` 表里，也没有无 TTY 挂载它的公开 API）。行 A1 是**代码级确定**的；B1–B5 需要"对话框挂起期间又打开了整屏"，其**实际可达路径未经端到端点击验证（未验证）**——键盘路径被 `:2566` 挡住，现实中更可能经由鼠标点击或后台异步事件触发。

### 5.5 唯一无条件的自救：调用方自己的超时

恢复链路（全部在 `dialogs.js`）：`:100-102` 挂定时器 → `:79-98 onAbort` 从队列摘除/清 `active` → `:92` 结算为 `undefined` → `:97 advance()` → `:170-173 emit()` → Chat 的订阅者被唤醒（`Chat.js:235-236`）→ `dialogSnapshot` 变回 `null` → `:2566` 不再 return、`PromptInput.js:2456` 恢复 `isActive: true`。

实测（真实 `TuiDialogStore`，无 TTY）：**15011 ms / 15026 ms 结算**；把事件循环同步阻塞约 4 秒只是推迟、不会丢定时器。服务卸载时 `settleAll()` 把所有排队 + 活动请求以 `undefined` 结清（`:148-157`，注册于 `:193`）。
**所以 15 秒是"有界"，不是"修复"**：它把一次交互变成一次全局键盘封锁。

---

## 六、能不能在弹窗之前先探测"有没有渲染者"？——不能

四条线索逐一查过，结论是**可靠的前置检查不存在**：

1. **插件面没有就绪信号。** 插件能看到的 `tuiDialogs` 只有 `select` / `confirm` / `input` 三个业务方法（类定义 `dialogs.js:182-299`；`getHostDialogStore` 虽然存在（`:319-328`）但**故意不是包导出**，见 `:300-304` 的注释）。枚举整个公开面**没有** `ready` / `rendered` / `mounted` / `availability` 这类成员（`dialogs.js` 类体本身即可证实；早前一份报告另行枚举过运行时原型，结论一致）。
2. **订阅者数量与"可见性"无关。** `TuiDialogStore.listeners`（`dialogs.js:47`）确实能反映"有几个渲染者订阅了"，但 `Chat` 是**恒定订阅**的（`Chat.js:235-236`）：屏幕挂载期间订阅数一直是 1，**无论面板会不会被渲染**。所以这个信号不承载你要的信息。
3. **准入守卫不等于渲染保证。** `requirePluginCaller`（`host-access.js:631-652`，关键判据是 `trustedFibers.has(fiber)`，`:553`）只能证明"本行是一个已登记的活跃非 root 激活"，**证明不了 15 秒后是否会有人渲染**。而且准入通过 → 请求进 store → **恰恰是这一步造成了键盘让出**。
4. **即使探测成功也不够——TOCTOU。** 让出条件是在**渲染时刻**求值的（`Chat.js:2566` 每次 render 读快照），而 approval / 整屏可以在 `ask()` 之后的任何时刻出现。任何"先探测、再弹窗"的方案都有一个无法关闭的竞态窗口。

> [!danger] 结构结论：**唯一不会冻结的做法，就是不把 Promise 停进 store。** 不是"小心使用"，是"换机制"。

---

## 七、需要"选择"时的安全模式：两条同步命令 + 序号

**判据**：冻结的充要条件是「store 里出现 `active`」。因此 **不使用 `tuiDialogs` ⇒ 死锁在结构上不可能**，而不是"15 秒后有界"。

已落地的做法（`dsh-plugin-redact`，本机 profile 以 `link:C:/%USERPROFILE%/dsh-plugin-redact` 安装，与仓库副本 `C:\%USERPROFILE%\dsh-redaction\packages\dsh-plugin-redact\index.js` 文件大小/时间逐项一致 ⇒ 以下行号对两者都成立）：

1. **handler 保持同步返回**，输出自己先收敛到 200 格以内：`clamp()`（`index.js:41-52`）与 `clampResult()`（`:56-61`），在注册处包住整个 handler（`:1190`）。
2. **第一条命令打印编号清单**（单行，最新在前）：`/redact nodes`（`:951-1023`），按显示格预算分页；`nodes full` 把完整清单**落盘**到 `%TEMP%\dsh-redact-nodes-<会话 id>.txt`（`:967-985`），绕过"通知只有一行"的限制；**第二条命令只带一个序号**：`/redact hide <序号> --commit`（`:1025-1059`）——短到**不需要从通知里复制任何字符**。
3. **序号必须对着快照校验**（这一步是安全性的关键）：`nodes` 记录 `{ items, newestSeq }`（`:963`）；`hide <n>` 时重新采集一次，若最新节点已变则**拒绝执行**并提示重新运行 `nodes`（`:1036-1042`），越界则报 `序号 N 超出范围`（`:1044`）。理由是列表**最新在前**：期间只要新落一个工具结果，全部序号就整体位移，而遮蔽**不可撤销**——不校验就会点错目标。

> [!tip] 模态路径可以保留，但要默认关闭
> `/redact pick` 仍然存在，但**默认关闭**（`allowDialogs: false`，`:601-604`、`:861-866`）；没打开时它**连对话框服务都不会碰**。打开需要两件事同时成立：配置 `allowDialogs: true` **且** 行级 `inject: [commands, tuiDialogs]`；代价是——在没有 `tuiDialogs` 提供者的 profile 上，该行会**永远 PENDING**，而启动器把 PENDING 当致命错误，**整个 profile 起不来**。

**不要做的事**：不要为了"探测渲染者"去深挖 `node_modules` 拿 `getHostDialogStore`。它既依赖非公开导出，又解决不了 §六 的 TOCTOU。

| 选项 | 判定 |
|---|---|
| 继续把 `select` 当常规交互用 / 把超时调短 | ❌ 都不行：前者把"全局键盘封锁"做成了正常流程的一部分，后者 1 秒和 15 秒一样是"按什么都没反应" |
| 默认禁用但保留开关 | ⚠️ 不够：机制仍在，且配置项不会告诉用户"现在能不能安全开" |
| 换成两条同步命令（+序号快照校验） | ✅ 结构上不可能冻结，功能等价物完整 |

---

## 八、运维：卡住了怎么办，以及两个启动期陷阱

### 8.1 用户此刻正卡住

| 手段 | 有效吗 | 依据 |
|---|---|---|
| **什么都不按，等超时** | ✅ **唯一无条件的自救** | `dialogs.js:100-102` → `:79-98` → `:170-173` → `Chat.js:236` → `:2566` → `PromptInput.js:2456` |
| `Esc` | ⚠️ **只有当面板真的挂载了才行** | `ExtensionDialog.js:66-70`；没挂载时 `Esc`/`Ctrl+C` **都没有任何监听者** |
| `Ctrl+C` 想退出程序 | ❌ 无效 | `plugin.js:1536`（`exitOnCtrlC: false`）、`App.js:481-485`、`Chat.js:3250` 被 `:2566` 挡掉 |
| 切会话 / `/resume` | ❌ 无效 | store 属于 `dsh-tui-extensions` 行的运行时，Chat 只是订阅者 |
| 重启 TUI | ✅ 有效（但通常没必要） | 服务卸载 → `:193` → `settleAll()`（`:148-157`） |
| 再敲一次同一个命令 | ⚠️ 不会延长，但会**续上新一轮** | 排队请求用**自己的**定时器；前一个超时后它立刻变 active |

一句话给用户：**什么都别按，等超时；超时后回车即可恢复。别按 Ctrl+C——它退不出去，也取消不了。**

### 8.2 启动期陷阱一：准入竞态会让对话框"静默取消"

调用方必须是**已登记在册的活跃非 root 激活**（`requirePluginCaller`，`host-access.js:631-652`）。这份登记由**第一个构造服务的 dsh-tui 适配器模块**建立（在本 profile 里最早的是 `dsh-tui-workspaces` 行 → `cordis.patch.yml:288-289` → `workspaces.js:37` 的 `compositionRoot(ctx)`）。若插件行比它更早进入 ACTIVE，`ask()` 里的归属绑定会失败并**立刻以取消结清**（`dialogs.js:103-111`）——**面板根本不弹，用户只看到"已取消"**。

- **为什么要写行级 `inject`**：`inject: [commands, tuiDialogs]` 让 Cordis 等服务就绪再激活本行（行级 `inject` 是**追加**而非替换，重复声明 `commands` 无害）；"软探测"绕不开它——软探测只判断服务在不在，判断不了时序。
- **怎么识别**：用耗时区分"人取消"与"宿主未接纳"——人按 Esc 不可能在 50 ms 内完成（`index.js:907-916`、`:934-939`）。这条启发式值得抄。
- **本机现状（2026-09-12 复核后已修正）**：`profiles/dsh-tui/cordis.patch.yml:33-41` 那一行现在**同时**带 `inject: [commands, tuiDialogs]` 与 `allowDialogs: true`，`--dump-config` 已确认四项 config 齐全。
  > [!warning] 这条曾被漏掉过一次，教训值得记
  > 起初那一行只写了 `inject` + 三个 config 字段，**漏了 `allowDialogs: true`**。因为 patch 命中的行是**整个 config 被替换**（不是深合并），漏写就落回默认 `false` ⇒ `/redact pick` 静默走「默认关闭」降级分支，**那行 `inject` 等于白加**。
  > 通用教训：**patch 层的 config 是整值替换**——凡是「默认值与期望不符」的字段都必须显式写出；**改了插件的默认值，就要回头检查每一处覆盖该行的 patch**。
  > （这条只对**当前这份用户补丁层**成立；真实进程内的行激活顺序**未直接观测**，见"未验证清单"。）

### 8.3 启动期陷阱二：不要用 `disabled` 做"自动二选一"

`Entry.disabled` 是**实时 getter**，判据会随挂载进度翻转；实测用 `!!js` 的自禁用守卫会让**整个 boot 中止**（提供者排在后面时必炸）。包内注释与用户补丁层都明确记了这一条（`packages/dsh-plugin-redact/cordis.patch.tui.yml:24-26`；`README.zh.md:170`）。**要条件化就行级 `inject` + 优雅降级，不要条件化行本身。**

---

## 未验证清单

| # | 项 | 状态 |
|---|---|---|
| 1 | §五 的死锁矩阵 | 判据**转写自** `Chat.js`，非真实组件挂载；A1 为代码级确定，B1–B5 的可达路径未做端到端验证 |
| 2 | 真实 TUI 进程内的行激活顺序、`requirePluginCaller` 追踪器与真实 boot 的先后 | 未启动/未重启 TUI；只给出离线模拟与"重启后自测法"（依赖模块导入耗时竞争，离线无法判定） |
| 3 | 修复后的插件在真实前端里的面板行为 | 无 TTY，键位/滚动只在代码层核对 |

## Related

- [[DSH-TUI插件使用手册]] — 使用者视角：安装、运行、快捷键、端点配置
- [[DSH插件与Hook开发最佳实践]] — Cordis 插件模型、服务/事件/`inject` 语义
- [[DSH提效与Token插件调研]] — 官方与社区插件清单及推荐组合
- [[AI-Links-KB-Home]] — 本子库 MOC（本文的文档地图入口）
- [[AGENTS]] — 知识库写作与链接规范
