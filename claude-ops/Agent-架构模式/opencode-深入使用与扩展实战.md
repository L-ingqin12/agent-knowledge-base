---
title: OpenCode深入使用与扩展实战
aliases: [opencode实战, opencode二开指南]
tags: [ai/agent, ai/ops]
created: 2026-08-26
updated: 2026-09-13
status: review
source: 基于库内实机核验结论（v1.18.23）整理的实操手册；版本敏感处标待确认，事实口径以 [[参考-OpenCode-技术调研报告]] §11 为准
fetched_at: 2026-08-26
---

# OpenCode 深入使用与扩展实战

> [!abstract] 定位
> 调研报告回答"OpenCode 是什么/缺什么"，本文回答"怎么用透/怎么扩展"：配置体系、四内置件路由、自定义 tool/agent 落码、plugin hook 实战、MCP 接线、serve/SSE 集成与排障。选型论证见 [[opencode-pi-base-development-analysis]]。

See also: [[Claude-Ops-KB-Home]] · [[参考-OpenCode-技术调研报告]] · [[agent-harness-anatomy]] · [[MEMORY-INDEX]]

## 一、配置体系速览（opencode.json）

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "theme": "dark", "autoupdate": true,
  "mcp": { "fs": { "type": "local", "command": ["npx","-y","mcp-server-fs"] } },
  "permission": {
    "edit": "allow", "bash": { "*": "ask", "git push*": "deny" },
    "webfetch": { "domain.com": "allow" }
  },
  "agent": { /* 见 §二 */ }
}
```

- **permission 是 last-match 规则引擎**：数组顺序即优先级，后命中覆盖先命中——写规则按"宽→窄"排
- 权限键实为 `doom_loop` 与 `external_directory` 等少数键+工具级 action（edit/bash/webfetch），不要臆造键名（§11 核验口径）
- MCP 工具命名空间：`<server>_<tool>`（非 Claude Code 的 mcp__server__tool 双下划线）——跨框架迁移脚本注意替换

## 二、Agent frontmatter 实战

```markdown
---
description: 日志包解析专家——只读分析，产出结构化结论
mode: subagent        # primary | subagent | all
model: ox-alpha       # 继承铁律: 不指定 provider 覆盖
temperature: 0.1
tools:
  write: false        # 只读件禁写
  bash: allow
---

你是日志根因分析专家…（系统提示词正文：角色/边界/输出 schema）
```

- `description` 同时是主 agent 的路由依据——**委派质量的上限写在 description 里**（对照 [[Anthropic多智能体研究系统拆解]] 委派三要素）
- 四内置件 build/plan/general/explore 各有默认 tools 集；explore 只读适合检索型 fan-out（§11.2 口径）
- task 委派四缺口（异步 #5887/嵌套 #9280/并行 #29638/resume #6584 未全解）决定编排策略：**同步扇出为主**，异步需求走外层编排器（下一节 serve 模式）

## 三、自定义 Tool 落码（TypeScript 插件式）

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ project, client }) => ({
  tool: {
    // 注册后以 mypkg_secure_read 出现在模型工具面
    "mypkg_secure_read": async (args: { path: string; max_bytes?: number }) => {
      const p = path.resolve(args.path)
      if (!p.startsWith(SANDBOX_ROOT)) throw new Error("path escapes sandbox")
      const stat = await fs.stat(p)
      const cap = args.max_bytes ?? 65536
      return { content: await readHead(p, cap), truncated: stat.size > cap,
               meta: { size: stat.size } }   // 结构化返回优于散文
    }
  }
})
```

要点：① 返回带 `truncated/meta` 的结构体，让模型可推理；② 边界校验放工具内层而非只靠 permission；③ 命名前缀=插件命名空间防撞。

## 四、Plugin Hook 实战清单

| Hook | 典型用途 | 注意 |
|------|---------|------|
| `chat.params` | 注入系统提示词片段(时间/环境) | 幂等注入防重复拼接 |
| `chat.headers` / `message` | 审计/打标 | 别在热路径做重 IO |
| `tool.execute.before` | 参数改写/敏感命令拦截 | 返回 abort 即阻断执行 |
| `tool.execute.after` | 结果脱敏/审计落盘 | 异步化避免拖慢回合 |
| event bus(`event` 订阅) | session.idle 触发归档、file watcher | 事件风暴下加节流 |

模式：审计类逻辑全部走 after/event 落 JSONL——天然形成 [[agent-evals-observability]] 需要的 trace 数据源。

## 五、服务化集成（serve + SSE）

```
opencode serve --port 4096
POST /session            → 建 session
POST /session/:id/message → 发消息(EventSource 流回 token/工具事件)
GET  /event              → 全局 SSE 总线
```

- Web/移动端壳或 CI 机器人都走此面；abort 用对应 message cancel 端点
- 会话池管理（多用户复用）：cache 亲和=同用户粘 session；背压=队列深度阈值拒绝——设计推演见 [[opencode-pi-base-development-analysis]] §会话池
- 已知缺口对冲：resume 弱(#6584) → 外层把 session id+checkpoint 自管；并行弱(#29638) → 多进程实例+前置路由

## 六、排障速查

| 症状 | 处置 |
|------|------|
| 工具没出现在面板 | 插件未加载(路径/schema)；`opencode debug` 类命令核对；MCP 命名 `<server>_<tool>` 是否记错 |
| permission 规则不生效 | last-match 顺序错——窄规则放后面 |
| 子代理不返回 | 同步委派超时；检查 description 是否被误当 primary(mode 配错) |
| MCP server 起不来 | stdio 命令路径/env；remote 型查 SSE 端点可达性 |
| 升级后行为漂移 | 0.x→1.x 式大版本破坏面；锁版本+回归脚本 |

## 七、待确认项

> ① plugin API 的稳定版本承诺(当前标注 experimental 的面有多大)；② permission 对 MCP 工具的细粒度键支持；③ LSP 集成对各语言的诊断回灌质量；④ #29638 并行委派 issue 的最新进展。

> [!success] 残余复核（2026-09-13）：四项**全部定论**（②④ 库内定论；① 由官方插件页定论；③ 由官方 LSP 页定论）。
> - **② 不支持 MCP 工具粒度的权限键**：权限键是**闭集**——`edit` / `bash`（通配模式映射）/ `webfetch` / `doom_loop` / `external_directory`，取值 `ask|allow|deny`，**没有** `<server>_<tool>` 这类 MCP 命名空间键（本库 [[参考-OpenCode-技术调研报告]] §11 实机核验「权限键全集」行；与本文 §一「不要臆造键名」一致）。要按单个 MCP 工具放行/拦截，走 plugin `permission.ask` 或 `tool.execute.before`，别指望配置键。
> - **④ #29638 已终结，不是「最新进展」**：`anomalyco/opencode` **#29638『Subagents dispatched sequentially instead of in parallel』现为 `closed` / `not planned`**（同批 #5887 亦 `not planned`；#6584 / #9280 为 `completed`）。依据 2026-09-13 GitHub API 逐个取回，缓存于本库 `_out/kb-completion-2026-09-13/C1-verified.json`。→ 本文 §二「同步扇出为主」的结论**不变**，且 §五「并行弱 → 多进程实例+前置路由」是**长期解**而非等待上游修复。
> - **① 「稳定版本承诺」= 官方**不给**任何承诺，唯一稳定性信号是 `experimental.` 前缀**：官方 Plugins 页（取回 2026-09-13）**没有** stability / LTS / breaking-change 政策段落（页面无 "stable"/"breaking" 表述），也未给版本承诺；实验面靠命名前缀自曝。**「experimental 面有多大」**：文档示例里只出现 **1 个**——`experimental.session.compacting`；而本库 [[参考-OpenCode-技术调研报告]] §11 从 plugin dist 的 `Hooks` 类型抄出的 experimental 子集为 **6 个**：`experimental.chat.system.transform`、`experimental.chat.messages.transform`、`experimental.session.compacting`、`experimental.provider.small_model`、`experimental.compaction.autocontinue`、`experimental.text.complete`（另有配置项 `experimental.policies`，见该报告 §7）——**文档面 << 类型面**，说明只读文档不足以摸清不稳定面。稳定的具名 hook 反例（官方示例在用）：`tool.execute.before` / `tool.execute.after` / `shell.env` / `event`。
>   版本事实：`@opencode-ai/plugin` npm latest **1.18.30**（registry time 2026-09-09），patch 级快发 → 实践对策仍是本文 §六「锁版本+回归脚本」。
>   依据（取回 2026-09-13）：<https://opencode.ai/docs/plugins/>
> - **③ 已定论：官方自己劝你别依赖 LSP，改用 CLI 诊断工具直接回灌**。官方 LSP 页「Best Practices」逐字立场：LSP「can help the agent find and fix issues by providing diagnostics from language servers. This is useful in some projects, but **it is not always a net positive**」——理由是 language server 会**失同步、吃内存、随版本/项目而异、拖慢 agent 工作流**；因此「in many projects it is better to have the agent **run lint, typecheck, or other diagnostic CLI tools directly**, so errors are fed back into the agent loop without those tradeoffs」，并要求把这些命令写进 AGENTS.md / skills 让 agent 知道跑什么。
>   **对本库的直接含义**：不要为「诊断回灌质量」去做多语言 LSP 实验——押注点应是**在 AGENTS.md 里固化 `lint`/`typecheck` 命令**这一更可控的回灌通道；LSP 仅在项目确有收益时才开（`lsp: true` 或按 server 配置）。
>   另附能力面（同页）：内置 LSP server 覆盖 astro/bash/clangd/csharp/clojure-lsp/dart/deno/elixir-ls/eslint/fsharp/gleam/gopls/hls 等，支持 `command`/`extensions`/`env`/`initialization`/`disabled` 配置与自定义 server。
>   依据（取回 2026-09-13）：<https://opencode.ai/docs/lsp/>

## Related

[[参考-OpenCode-技术调研报告]] · [[opencode-pi-base-development-analysis]] · [[pi-agent深入使用与扩展实战]] · [[main-subagent-realtime-interaction]] · [[agent-evals-observability]] · [[fan-out-subagent-pattern]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 定论 | §七 ②「permission 对 MCP 工具的细粒度键支持」 | 加复核块：权限键为**闭集**（edit/bash/webfetch/doom_loop/external_directory），无 MCP 命名空间键 → **不支持**；细粒度需走 plugin `permission.ask` / `tool.execute.before`。依据本库 [[参考-OpenCode-技术调研报告]] §11 权限键全集行 |
| 定论 | §七 ④「#29638 并行委派 issue 的最新进展」 | 加复核块：#29638 已 `closed` / `not planned`（#5887 同，#6584/#9280 为 completed）→ 不是「进展中」而是**已终结**；§二 同步扇出结论不变。依据 2026-09-13 GitHub API 取回，缓存于 `_out/kb-completion-2026-09-13/C1-verified.json` |
| 定论 | §七 ①「plugin API 的稳定版本承诺 / experimental 面有多大」 | 加复核块：官方 Plugins 页**无**任何 stability/LTS/breaking 承诺，唯一信号是 `experimental.` 前缀；文档面仅 1 个 experimental hook、dist 类型面 6 个 → 只读文档不足以摸清不稳定面。依据取回 2026-09-13：opencode.ai/docs/plugins/ |
| 定论 | §七 ③「LSP 集成对各语言的诊断回灌质量」 | 加复核块：官方 LSP 页 Best Practices 明确「not always a net positive」（失同步/吃内存/拖慢），建议多数项目改用 **CLI lint/typecheck 直接回灌** 并写进 AGENTS.md → 本库不应为此做多语言 LSP 实验。依据取回 2026-09-13：opencode.ai/docs/lsp/ |

回链：[[CORRECTIONS]] · [[AGENTS]]
