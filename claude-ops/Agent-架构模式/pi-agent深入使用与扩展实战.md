---
title: Pi-Agent深入使用与扩展实战
aliases: [pi实战, pi二开指南]
tags: [ai/agent, ai/ops]
created: 2026-08-26
updated: 2026-09-13
status: review
source: 基于库内实机核验结论（@earendil-works/pi-coding-agent@0.84.3 全源码）整理；版本敏感处标待确认，事实口径以 [[参考-Pi-Agent-技术调研报告]] §11 为准
fetched_at: 2026-08-26
---

# Pi Agent 深入使用与扩展实战

> [!abstract] 定位
> 调研报告回答"Pi 是什么"，本文回答"怎么嵌入/怎么扩展/怎么排障"：库优先三层 API、TypeBox 自定义 tool 全码、steer/followUp 双队列语义与代码、extension 事件面、RPC 模式协议、JSONL 会话格式解析（可喂给 LogNet！）。选型论证见 [[opencode-pi-base-development-analysis]]。

See also: [[Claude-Ops-KB-Home]] · [[参考-Pi-Agent-技术调研报告]] · [[opencode-深入使用与扩展实战]] · [[main-subagent-realtime-interaction]]

## 一、库优先：三层 API 心智图

```
L1 createAgentSession(cfg)          ← 产品级: 自带循环/UI 粘合
L2 AgentSession(低阶)               ← 库级: 完全掌控回合与队列 (推荐二开层)
L3 流原语(streamFn+tools)           ← 极客层: 自己当 harness
```

- 二开建议钉在 **L2**：拿得到事件流与双队列，又不背 UI 包袱
- 无内置权限内核（默认放行）→ **宿主进程必须自建闸门**（secure_read 类工具 + 进程沙箱），对照 [[agent-harness-anatomy]] §2.4

## 二、自定义 Tool 全码（TypeBox 契约）

```typescript
import { Type, defineTool } from "@earendil-works/pi-coding-agent" // 具名导出面以 0.84.x 为准

const LogQuery = defineTool(
  {
    name: "lognet_query",
    description: "FTS5 全文检索日志库, 返回带 rowid 引用的结构化命中",
    parameters: Type.Object({
      q: Type.String({ description: "FTS5 MATCH 表达式" }),
      limit: Type.Optional(Type.Integer({ minimum: 1, maximum: 50 }))
    }),
    returns: Type.Object({ hits: Type.Array(Type.Object({
      rowid: Type.Integer(), ts: Type.Number(), line: Type.String() })) })
  },
  async (args) => queryLogs(dbPath, args.q, args.limit ?? 20)   // 复用 LogNet PoC!
)
```

- 契约即提示词：description/字段 description 都会进模型上下文——**写工具=写微型系统提示词**
- 返回结构体优于拼字符串（模型可按字段推理）；错误抛 Error 带 `code` 前缀便于模型自纠

## 三、steer / followUp 双队列（实时交互核心语义）

```typescript
session.prompt("开始解析这个包")            // 入队新回合
session.steer("只看 hilog, 跳过 kmsg")      // 注入当前进行中的回合 → 模型下一思考点看到
session.followUp("完成后输出摘要")          // 排队为紧随的后续回合
session.abort()                             // AbortSignal 打断当前流
```

| 队列 | 语义 | 对应交互原语 |
|------|------|-------------|
| steer | 当轮内改道（模型已启动，下次"呼吸"时读到） | T1.5 当轮注入（[[main-subagent-realtime-interaction]]） |
| followUp | 回合后追加 | 邮箱通知类 |
| abort | 流级打断+AbortSignal 传播 | T2 打断抢占 |

- 实战规则：**纠偏用 steer，追加任务用 followUp，紧急停止用 abort**——三者混用是交互混乱之源
- 看门狗集成：超时未产出 → 先 steer 提示收敛 → 再 followUp 要求落盘中间态 → 最后 abort（T0→T2 升阶梯的库内实现路径）

## 四、Extension 事件面（25+ 事件选讲）

| 事件 | 用途示例 |
|------|---------|
| session start/end | 会话审计落 JSONL（喂 LogNet 的数据源！） |
| message start/update/end | token 计量、流式转发到自有 UI |
| tool_call before/after | 权限闸门(自定义 allow/deny)/结果脱敏——**补齐无内核权限的关键位** |
| agent steering | 收到 steer 时打标，评估改道有效性 |

写法：`pi.extend(({ on }) => { on("tool_call", async (ev) => {...}) })` 形态（签名以 0.84.x d.ts 为准，**待确认**逐字口径）。

> [!success] 残余复核（2026-09-13）：**口径已逐字定论，且原写法有错——`pi.extend(...)` 不存在，应改 `pi.on(...)`**。
> 取回 `@earendil-works/pi-coding-agent@0.85.1` 的 `dist/core/extensions/types.d.ts`（1350 行）逐字核验：
> - 扩展入口是**工厂函数**，不是 `extend` 方法：`export type ExtensionFactory = (pi: ExtensionAPI) => void | Promise<void>;`（line 1159）。
> - `on(event, handler)` 是 **`ExtensionAPI` 上的方法**（不是工厂参数解构出来的独立函数），共 **36 个强类型事件重载**，逐字如 `on(event: "tool_call", handler: ExtensionHandler<ToolCallEvent, ToolCallEventResult>): void;`（line 939）、`on(event: "tool_result", ...)`（line 940）。
> - **全文无 `extend` 方法**——`extend` 仅作为 TS 关键字 `extends` 出现在接口继承里。故原句 `pi.extend(({ on }) => { on("tool_call", ...) })` 两处皆误（无 `extend`；`on` 也不是可解构的独立函数）。正确形态：
>   ```ts
>   const myExt: ExtensionFactory = (pi) => {
>     pi.on("tool_call", async (ev) => { /* ... */ })
>   }
>   ```
> - **连带更正 §四 表的事件名**：真实事件名是 **snake_case**，不是空格/`before`/`after` 形态——表内 `session start/end` 应为 `session_start` / `session_shutdown`；`tool_call before/after` 应为 **`tool_call`** 与 **`tool_result`**（配对靠事件语义，不靠前后缀命名）；`agent steering` **无此事件**（最接近的是 `input`）。同表「25+ 事件」可收紧为**实取 36 个**（`on(event:)` 重载计数，与 [[pi-agent-framework-knowledge]] 里「25+ 无出处」那条互为印证）。
>   完整事件名册（36）：`project_trust` `resources_discover` `session_start` `session_info_changed` `session_before_switch` `session_before_fork` `session_before_compact` `session_compact` `session_compact_failed` `session_shutdown` `session_before_tree` `session_tree` `context` `before_provider_request` `before_provider_headers` `after_provider_response` `before_agent_start` `agent_start` `agent_end` `agent_settled` `ui_prompt_start` `ui_prompt_end` `turn_start` `turn_end` `message_start` `message_update` `message_end` `tool_execution_start` `tool_execution_update` `tool_execution_end` `model_select` `thinking_level_select` `tool_call` `tool_result` `user_bash` `input`
>   依据（取回 2026-09-13）：<https://cdn.jsdelivr.net/npm/@earendil-works/pi-coding-agent@0.85.1/dist/core/extensions/types.d.ts>（包根具名导出面见 `dist/index.d.ts`，`package.json` 的 `exports["."]` 指向它）

## 五、RPC 模式与嵌入式集成

- `--mode rpc`：stdin/stdout JSON-RPC 行协议——把 Pi 当子进程引擎嵌进任何宿主（Python/Electron/Go）
- 消息族：请求(prompt/interrupt)+响应(result)+异步事件(event) 三类帧；宿主负责重连与背压
- 与 OpenCode serve/SSE 的取舍：stdio RPC 更适合**单机桌面 Sidecar**（零端口暴露），HTTP/SSE 适合 Web 多用户（[[opencode-pi-base-development-analysis]] 跨平台矩阵）

## 六、JSONL 会话格式解析 → LogNet 数据源

- 会话树状 JSONL：每行一个事件(session/message/toolCall/…)，parent 字段构成树
- 解析要点：① 树重建靠 parent id；② toolCall 结果可能跨行引用；③ 0.x 版本 schema 变更风险→解析器带 version 分支
- 本库映射：把 Pi/OpenCode 会话行事件映射成 LogNet EventNode（ts=时间戳, entity=sessionId, content=text），复用 PoC 的折叠+FTS5 即得"Agent 会话根因检索器"——M1 后备数据通道之一

## 七、排障速查

| 症状 | 处置 |
|------|------|
| 工具参数校验不过 | TypeBox schema 写严了(min/max)；模型重试链看 event 流 |
| steer 不生效 | 当前无进行中回合（应走 followUp/prompt）；或模型已完成该步 |
| Windows 路径/编码异常 | 已知坑清单见调研报告 §Windows；统一 UTF-8 + 正斜杠 API |
| 升级破坏 | 0.84.x 锁版本；changelog diff 驱动回归脚本 |
| 嵌入端内存涨 | 会话树不裁剪→定期 fork 截断+归档 JSONL 到 LogNet |

## 八、待确认项

> ① defineTool/extend 的导出符号精确路径（以 node_modules d.ts 为准复核）；② RPC 帧完整 schema 文档化程度；③ 多模态输入(图片)的工具返回约定；④ 作用域包迁移(@earendil-works)后的旧包维护期。

> [!success] 残余复核（2026-09-13）：四项**全部定论**（①②④ 由本次取回的上游分发物/官方文档/registry 定论，③ 由本机源码定论）。
> - **① defineTool 的精确路径已有被核验的答案**：声明于 `dist/core/extensions/types.d.ts`（line 386），签名 `export declare function defineTool<TParams extends TSchema, TDetails = unknown, TState = any>(tool: ToolDefinition<TParams, TDetails, TState>)`，schema 来自 **`typebox`**（非 zod）；注册入口 `registerTool` 在同文件 line 927。来源：本库 [[参考-Pi-Agent-技术调研报告]] §11.1（npm 分发物逐文件核验，并附 `npm pack` 开放复核路径）。**`extend` 已核验为不存在**——见 §四 复核块（正确形态是 `ExtensionFactory` + `pi.on(...)`）。
> - **③ 工具返回图片的约定已定论**：`ToolResultMessage.content` 的类型是 **`(TextContent | ImageContent)[]`**——工具结果**原生支持与文本并列的图片内容块**，`ImageContent = { type: "image"; data: string; mimeType: string }`（base64 + MIME）；用户侧同理 `UserMessage.content: string | (TextContent | ImageContent)[]`。即「多模态工具返回」不是外挂约定，而是消息线格式的一等公民。依据（本机）：`%USERPROFILE%\.dsh\profiles\node_modules\@earendil-works\pi-ai@0.85.1\dist\types.d.ts`。**注意边界**：这是 **pi-ai（LLM 提供方层）** 的线格式，`pi-coding-agent` 的工具包装层是否原样透传未核。
> - **② RPC 帧 schema 已定论：官方成文且相当完整**。上游 `docs/rpc.md` 实为 **42.7 KB 的完整协议文档**，不是「仅知有 rpc/ 目录」：含 **Framing**（stdin/stdout 行协议，一行一 JSON）、**Commands**（约 40 个，逐个分节给参数——prompt / steer / follow_up / abort / clear_queue / new_session、get_state / get_messages、set_model / cycle_model / get_available_models、set_thinking_level 系列、set_steering_mode / set_follow_up_mode、compact / set_auto_compaction、set_auto_retry / abort_retry、bash / abort_bash、get_session_stats / export_html / switch_session / fork / clone / get_fork_messages / get_entries / get_tree / get_last_assistant_text / set_session_name、get_commands）、**Events**（约 20 类逐个分节：agent_start / agent_end / agent_settled、turn_start / turn_end、message_start / message_end、message_update 流式、bash_execution_update、tool_execution_start|update|end、queue_update、compaction_start|end、auto_retry_start|end、summarization_retry_* 、extension_error）、**Extension UI Protocol**（select / confirm / input / editor / notify / setStatus / setWidget / setTitle / set_editor_text 及其应答与取消）、**Error Handling**、**Types**（Model / UserMessage / AssistantMessage / ToolResultMessage / BashExecutionMessage / Attachment），并附 Python 与 Node.js 两个可跑客户端示例。→ 本文 §五「三类帧」的表述（请求/响应/异步事件）与官方一致，可放心引用。
>   依据（取回 2026-09-13）：<https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc.md>
> - **④ 旧作用域包维护期：官方**未**标 deprecated，但三包均已停更——即「无维护期承诺，事实停更」**。npm registry 逐包实取（2026-09-13）：`@vaayne/pi-coding-agent` latest **0.0.1**、最后发布 **2026-01-22**；`@vandeepunk/pi-coding-agent` latest **1.0.0**、最后发布 **2026-04-15**；`@pie-lab/coding-agent` latest **0.3.0**、最后发布 **2026-07-02**——**三者的 `deprecated` 字段均为空**。即：不会被 npm 警告、仍可安装，但都已被 `@earendil-works/pi-coding-agent`（latest 0.85.1，45 个版本，最近发布 2026-09-05）甩开数个版本且长期无更新。**结论：迁移到 `@earendil-works` 后不要指望旧包有维护期，视同停更。**
>   依据（取回 2026-09-13）：`https://registry.npmjs.org/@vaayne%2Fpi-coding-agent`、`…/@vandeepunk%2Fpi-coding-agent`、`…/@pie-lab%2Fcoding-agent`、`…/@earendil-works%2Fpi-coding-agent`

## Related

[[参考-Pi-Agent-技术调研报告]] · [[pi-agent-framework-knowledge]] · [[opencode-深入使用与扩展实战]] · [[main-subagent-realtime-interaction]] · [[lognet-rootcause-multiagent-architecture]] · [[agent-harness-anatomy]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 定论 | §八 ①「defineTool/extend 的导出符号精确路径」 | 加复核块：`defineTool` 声明于 `dist/core/extensions/types.d.ts` line 386、schema 来自 `typebox`、注册入口 `registerTool`（同文件 line 927）；依据本库 [[参考-Pi-Agent-技术调研报告]] §11.1 的 npm 分发物逐文件核验。`extend` 部分仍开放 |
| 定论 | §八 ③「多模态输入(图片)的工具返回约定」 | 加复核块：`ToolResultMessage.content: (TextContent \| ImageContent)[]`、`ImageContent = { type: "image"; data; mimeType }`（base64+MIME）→ 图片是消息线格式一等公民；依据本机 `%USERPROFILE%\.dsh\profiles\node_modules\@earendil-works\pi-ai@0.85.1\dist\types.d.ts` |
| 纠错 | §四 `pi.extend(({ on }) => ...)` 的写法（原标「待确认逐字口径」） | 加更正块：取回 `@0.85.1` 的 `dist/core/extensions/types.d.ts` 逐字核验——入口为 `ExtensionFactory = (pi: ExtensionAPI) => void | Promise<void>`（L1159），`on(event, handler)` 是 ExtensionAPI 方法（36 个重载，L939 `tool_call`、L940 `tool_result`），**全文无 `extend` 方法** → 应改 `pi.on("tool_call", ...)`。依据取回 2026-09-13：cdn.jsdelivr.net/npm/@earendil-works/pi-coding-agent@0.85.1/dist/core/extensions/types.d.ts |
| 纠错 | §四 表的「25+ 事件」与事件名形态（`session start/end`、`tool_call before/after`、`agent steering`） | 更正块内附实取事件名册：**36 个** snake_case 事件；`session_start`/`session_shutdown`；`tool_call` 与 `tool_result`（非 before/after 配对）；**无 `agent steering`**（最近似为 `input`）。与 [[pi-agent-framework-knowledge]]「25+ 无出处」条互为印证 |
| 定论 | §八 ②「RPC 帧完整 schema 文档化程度」 | 加复核块：上游 `docs/rpc.md` 为 **42.7 KB 完整协议文档**（Framing + ~40 命令 + ~20 事件 + Extension UI 协议 + Error Handling + Types + Python/Node 示例）→ 文档化程度高，本文 §五 三类帧表述与官方一致。依据取回 2026-09-13：raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc.md |
| 定论 | §八 ④「作用域包迁移后旧包维护期」 | 加复核块：npm registry 实取三包 `deprecated` 均为空但**均已停更**（@vaayne 0.0.1/2026-01-22、@vandeepunk 1.0.0/2026-04-15、@pie-lab 0.3.0/2026-07-02），新包 0.85.1（45 版本，2026-09-05）→ 视同停更、无维护期承诺。依据取回 2026-09-13：registry.npmjs.org |

回链：[[CORRECTIONS]] · [[AGENTS]]
