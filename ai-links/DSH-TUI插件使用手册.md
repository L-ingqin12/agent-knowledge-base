---
title: DSH TUI 插件使用手册
aliases: [dsh-tui, DSH终端UI, TUI手册]
tags: [ai/agent, ai/tools, ai/links]
created: 2026-08-17
updated: 2026-09-13
status: review
source: "官方手册 README.zh.md（MIT 许可）；现行上游为 ccch1mneyyy/dsh-TUI（2026-09-13 复核）"
source_urls:
  - "https://github.com/ccch1mneyyy/dsh-TUI"
  - "https://www.npmjs.com/package/@deepseek-harness-tui/dsh-tui"
  - "https://github.com/dsh-tui/dsh-tui"
  - "https://www.npmjs.com/package/@dsh-tui/dsh-tui"
fetched_at: 2026-08-19
---

# DSH TUI 插件使用手册

See also: [[AI-Links-KB-Home]] | [[2026-08-16-AI链接综述与归档]] | [[DSH跨框架Skills与MCP加载]] | [[AGENTS]]

> [!abstract] 摘要
> 本文档是插件 `@dsh-tui/dsh-tui` 官方手册（README.zh.md，MIT 许可）的知识库落盘。该插件是 DeepSeek Harness 智能体的交互式终端（TUI）入口，以树外 dsh 插件 bundle 形式安装，在终端里提供 Claude Code / Codex 同款对话体验。

> [!warning] 2026-09-13 复核：包名与 profile 名都已变更（先读这段）
> 本文主体写于 2026-08-17～08-30，此后上游把 TUI 移到了新包与新 profile：
>
> | 项 | 本文原表述 | 现行（2026-09-13 实测） |
> |---|---|---|
> | npm 包 | `@dsh-tui/dsh-tui` | **`@deepseek-harness-tui/dsh-tui`**（`latest` = 0.10.1；旧包停在 0.1.2 且仅 1 个版本） |
> | profile | `tui` | **`dsh-tui`**（`tui` 已改名为 `tui.retired-20260912`） |
> | 上游仓库 | github.com/dsh-tui/dsh-tui（★31，2026-08-14 后无推送） | **ccch1mneyyy/dsh-TUI**（★2995，2026-09-13 仍在推送） |
> | 本机 dsh CLI | 0.1.0-rc.6 | **0.1.5-rc.1**（上游 master 0.1.5-rc.2） |
>
> 下文已按现行值改写命令与清单；**仍以旧包名叙述的段落（定位、功能特性等）指的是同一条产品线**，其历史值保留在上表里。
> 来源：https://registry.npmjs.org/@deepseek-harness-tui/dsh-tui ；https://registry.npmjs.org/@dsh-tui/dsh-tui ；https://api.github.com/search/repositories?q=user:ccch1mneyyy

## 定位

- **是什么**：DeepSeek Harness 智能体的交互式终端（TUI）入口——在终端里获得 Claude Code / Codex 同款的对话体验。
- **形态**：树外（out-of-tree）dsh 插件 bundle；基于 [`@earendil-works/pi-tui`](https://www.npmjs.com/package/@earendil-works/pi-tui) 构建。
- **与官方的关系**：组合在官方 `@deepseek-ai/dsh-base` bundle 之上，与官方 web 界面共享同一套插件生态——shell 与文件系统工具、技能、子代理、工作流、沙箱审批——**不 fork、不魔改**。

> [!tip] 一句话定位
> 同一个插件生态，换一个终端交互入口。

> [!info] 实现细节
> pi-tui 钉在 0.80.7 并带一个 pnpm 补丁（编辑器提示符前缀能力），构建时打包进 `lib/`，因此仓库之外的安装方永远不会拿到未打补丁的副本。

## 本机状态（2026-08-17 实测；2026-09-13 复核并更正）

| 项 | 实测值 |
|------|----------|
| 安装位置 | profile **`dsh-tui`**：`%USERPROFILE%\.dsh\profiles\dsh-tui\package.json`（原写 profile `tui`） |
| 依赖 | **`@deepseek-harness-tui/dsh-tui` `^0.10.1`**（原写 `@dsh-tui/dsh-tui` `^0.1.2`） |
| bundles | `dsh.profile.bundles` = `["@deepseek-ai/dsh-base", "@deepseek-harness-tui/dsh-tui", "dsh-plugin-redact", "dsh-plugin-content-policy"]`（原写前两项） |
| patchReload | `live` |
| dsh CLI | `%USERPROFILE%\nodejs-x64\node-v22.21.0-win-x64\dsh.ps1`，版本 **0.1.5-rc.1**（原写 0.1.0-rc.6） |
| dsh 自带 Node | `node-v22.21.0-win-x64\node.exe` → v22.21.0 |
| 系统 PATH node | v18.16.1（⚠ 不满足插件要求） |

> [!warning] Node 版本注意
> 插件要求 Node `^22.19 || >=24`，而系统 PATH 上的 node 是 v18.16.1。须用 dsh 自带 Node 22.21 环境：`dsh.ps1` 通过同目录 `node.exe` 调用 dsh（`node_modules/@deepseek-ai/dsh/lib/bin.js`），直接执行该 shim 即自动使用正确的 Node。

## 功能特性

- 模型输出与思考过程的**流式 Markdown 渲染**。
- **工具调用卡片**（terminal / diff / generic 三种渲染意图）；`Ctrl+O` 三档切换：预览 → 展开 → 隐藏。
- 工具审批与 `ask_user_question` 对话框，含 **plan 模式评审**。
- `@文件` 路径自动补全与 `@session` 会话引用卡片。
- 斜杠命令：`/model`（含推理力度选择）、`/resume`、`/compact`、`/details`、`/help`，以及其他插件注册的全部命令。
- 常驻 **todo 面板**、token 用量与上下文压力状态栏、会话标题。
- 可配置主题；从 `COLORTERM` 自动检测真彩色。

## 安装

前置要求：Node `^22.19 || >=24` 和 `dsh` CLI（`npm i -g @deepseek-ai/dsh@next`）。

> [!tip] `@next` 比 `latest` 新（2026-09-13 复核）
> `npm view @deepseek-ai/dsh dist-tags` 实测：`latest` = **0.1.5-rc.1**、`next` = **0.1.5-rc.2**、`alpha` = 0.1.5-alpha.2。所以上面用 `@next` 是有意的；**按默认 `npm i -g @deepseek-ai/dsh` 会装到较旧的 rc.1**。双向验收：`dsh --version` 与 `npm view @deepseek-ai/dsh dist-tags` 对照。
> 来源：https://registry.npmjs.org/@deepseek-ai/dsh

```sh
dsh plugin --profile dsh-tui add @deepseek-harness-tui/dsh-tui
```

**跟踪仓库最新代码**（而非 npm 发布版）：

```sh
dsh plugin --profile dsh-tui add github:ccch1mneyyy/dsh-TUI
```

git 安装的插件在安装时通过 `prepare` 脚本构建，pnpm 默认拦截构建脚本：若该 `add` 失败，按它打印的键名在 `~/.dsh/profiles/dsh-tui/pnpm-workspace.yaml` 里追加 `allowBuilds` 后重跑——

```yaml
allowBuilds:
  "@deepseek-harness-tui/dsh-tui": true
```

**API Key**：在环境变量（或启动目录 / `$DSH_HOME` 下的 `.env`）里设置 `DEEPSEEK_API_KEY`。

## 运行

```sh
dsh --profile dsh-tui                        # 在当前目录开启会话
dsh --profile dsh-tui --resume <session-id>  # 恢复历史会话
```

## 本地 / 自部署 DeepSeek 端点

零代码配置，三选一：

| 方式 | 配置 |
|------|----------|
| 1. 环境变量 | `DEEPSEEK_BASE_URL=http://localhost:8000/v1` 搭配 `DEEPSEEK_API_KEY` |
| 2. 设置文件（热加载） | `$DSH_HOME/settings.yaml` 中配置 `llm-deepseek.baseURL` |
| 3. OpenAI 兼容网关 | profile 补丁 `$DSH_HOME/profiles/dsh-tui/cordis.patch.yml` 声明 `llm-pi-ai` 路由并把默认模型指过去（vLLM、SGLang 等；参见 dsh 的 providers 指南） |

```yaml
# $DSH_HOME/settings.yaml（方式 2，热加载）
llm-deepseek:
  baseURL: http://localhost:8000/v1
```

## 独立客户端路线（2026-08-30 实测；2026-09-13 降级为「可选原型」）

> [!success] 另一条安装路线：`npm i -g dsh-tui`（npm 包 **`dsh-tui` v0.2.19**，GitHub MashedPotato817/dsh-tui）
> 与本文档主体（插件包，profile 集成）**不是同一个包**。独立包是薄客户端：**后端跑 `dsh web`（host，默认 http://127.0.0.1:3080）+ 前端 `dsh-tui` 直连**，直接 `dsh-tui` 命令启动，`DSH_URL` 环境变量可改 host 地址。

> [!warning] 2026-09-13 复核：这是**停更的早期原型**，不再是推荐路线
> npm `dsh-tui` `latest` = **0.2.19**（与原文一致），`repository` = git+https://github.com/MashedPotato817/dsh-tui.git ，description 逐字为「Terminal client for DeepSeek Harness: a TUI over the DSH client contract (ctx.remote)」——与"经 HTTP 连 host"方向一致且更精确。但该仓库实测 **★0、默认分支 `feat/dsh-tui`、npm 末次发布 2026-08-14（此后无更新）** ⇒ 应按「可选独立客户端（原型，2026-08-14 后无更新）」引用，不要当主力路线。
> 来源：https://registry.npmjs.org/dsh-tui/latest ；https://api.github.com/search/repositories?q=dsh-tui+user:MashedPotato817

| 项 | 插件版 `@deepseek-harness-tui/dsh-tui` (profile) | 独立包 `dsh-tui` (host+client) |
|---|---|---|
| 安装 | `dsh plugin --profile dsh-tui add @deepseek-harness-tui/dsh-tui` | `npm i -g dsh-tui` |
| 启动 | `dsh --profile dsh-tui` | `dsh web`(后台) + `dsh-tui` |
| 架构 | cordis 插件 bundle（与 host 同进程） | 独立 Ink TUI，经 HTTP 连 host |
| 思考强度控制 | 自带 `/model`（含推理力度选择） | **无**（源码核查，见下） |
| 适用 | 单进程一体化 | host 独立运行，客户端可随时重连 |

> [!warning] 独立版思考强度控制：TUI 内**无**内置开关
> 2026-08-30 源码级核查（feat/dsh-tui 分支 lib/commands.js）：本地斜杠命令仅 `new/resume/exit/quit/list/status/clear/help`；`:w/:cancel/:q`；CLI 参数无 model/effort；`session.create/prompt` 载荷**不传递** model/reasoningEffort。思考强度只能由 **host 端**决定：
> - settings.yaml `agent-default-model.reasoningEffort`（**热加载**，新会话生效）
> - 模型条目 `reasoningEfforts` 声明可选档位（官方 7 档 off/minimal/low/medium/high/xhigh/max）
> - Web 客户端模型选择器 + `/model` 斜杠命令（官方 UI 槽位 `conversation.input.model`）

### 独立路线本机实测（2026-08-30）

- `dsh` 0.1.0-rc.6 → **0.1.1-rc.2**；`dsh-tui` 全局安装 v0.2.19
- `dsh-tui run "..."` 一次调用验证：host + 客户端链路通，请求直达上游模型
- 会话请求头实测：`model: z-ai/glm-5.3-flash` + `reasoningEffort: "low"`（见 [[DSH提效与Token插件调研#思考强度控制实证]]）
- ⚠️ 工作区建议：在**项目子目录**启动（用户根目录会使临时目录落在工作区内被沙箱拒绝）

## 状态与已知限制

> [!warning] 2026-09-13 复核：下面两条「已知限制」是**旧线 0.1.2 的原文**，对现行线已不适用
> 按版本线拆开读：

| 版本线 | 状态 | 这里的「已知限制」怎么读 |
|---|---|---|
| 旧线 `@dsh-tui/dsh-tui@0.1.2`（已退役） | 停在 0.1.2、仅 1 个版本；上游 `dsh-tui/dsh-tui` ★31、2026-08-14 后无推送 | 下面前两条逐字来自它的 registry README：peer 依赖全部钉在 `^0.1.0-rc.6`；`tests/`「尚不可运行」 |
| 活跃线 `@deepseek-harness-tui/dsh-tui@0.10.1` | `latest` = 0.10.1；上游 ccch1mneyyy/dsh-TUI 2026-09-13 仍在推送 | 上述两条**不适用**；`engines.node` = `^22.19 \|\| >=24` |

- 基于 pre-release 的 `@deepseek-ai/dsh` **rc 线**开发，上游稳定前随时可能 breaking；peer 依赖钉在验证过的 rc 版本。
- 恢复出来的测试套件（`tests/`）先于本次移植，目前**尚不可运行**。
- 真实模型回合需要可达的 DeepSeek 兼容端点；请求之前的一切（组合、渲染、审批、resume）**无需 key 即可工作**。

**版本自检**（一条命令）：读 profile 安装树下该包 `package.json` 的 `version` 字段，确认它与你以为的版本线一致：

```powershell
Get-Content "$env:USERPROFILE\.dsh\profiles\dsh-tui\node_modules\@deepseek-harness-tui\dsh-tui\package.json" | Select-String '"version"'
```

来源：https://registry.npmjs.org/@deepseek-harness-tui/dsh-tui

## 来源与许可

- 许可：**MIT**。
- 出处：**据包自身 README 自述**，TUI 实现恢复自 DeepSeek Harness 仓库历史（`packages/ui/tui`），并移植到已发布的 rc API；上游版权声明保留在 LICENSE 中。
  > [!warning] 更正（2026-09-13）：commit `10bb9cbf4a` 无法证实
  > 原表述为「上游于 commit `10bb9cbf4a` 移除」。该 commit 经多次抓取无法证实（commit 页面与 `.patch` 均无法区分「不存在」与「抓取受阻」）⇒ 按本库硬约束记为 **unverifiable**，已把"恢复自某 commit"降级为"**据其 README 自述**"。
  > 已可证实的是包元数据：`@deepseek-harness-tui/dsh-tui` 的 `homepage`/`repository` = **ccch1mneyyy/dsh-TUI**，`engines.node` = `^22.19 || >=24`（与 0.10.1 一致）；其 registry README 亦自述同一「恢复自 `packages/ui/tui`」说法。
  > 来源：https://registry.npmjs.org/@deepseek-harness-tui/dsh-tui
- 仓库 / 包：`github:ccch1mneyyy/dsh-TUI`，npm 包 `@deepseek-harness-tui/dsh-tui`（原表述为 `github:dsh-tui/dsh-tui` + npm `@dsh-tui/dsh-tui`）。

## Related

- [[2026-08-16-AI链接综述与归档]] — README 友情链接条目 dsh-TUI/dsh-tianshu-tui 的调研归档
- [[DSH跨框架Skills与MCP加载]] — 跨框架 Skills / MCP 加载
- [[AI-Links-KB-Home]] — AI 链接收藏 MOC
- [[AGENTS]] — 知识库 AI 协作规范

## 验证清单

- [ ] `dsh --profile dsh-tui --dump-config` 输出中出现 `@deepseek-harness-tui/dsh-tui`
- [ ] 校验 profile 目录 `package.json`：`dependencies` 含 `@deepseek-harness-tui/dsh-tui`（`^0.10.1`），`dsh.profile.bundles` = `["@deepseek-ai/dsh-base", "@deepseek-harness-tui/dsh-tui", "dsh-plugin-redact", "dsh-plugin-content-policy"]`
- [ ] 首次启动 `dsh --profile dsh-tui` 看到 welcome / todo 面板与状态栏
- [ ] 确认用 dsh 自带 Node 22.21 环境启动（而非系统 PATH 的 v18.16.1）
- [ ] `Ctrl+O` 三档切换工具卡片：预览 → 展开 → 隐藏
- [ ] 配置 `DEEPSEEK_API_KEY`（或本地端点三选一）后完成一次真实模型回合

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §本机状态与 §验证清单写 profile `tui`、依赖 `@dsh-tui/dsh-tui` `^0.1.2`、安装命令 `--profile tui add @dsh-tui/dsh-tui` | 全页命令与清单改为 profile `dsh-tui` + `@deepseek-harness-tui/dsh-tui` `^0.10.1`（含 bundles 四项、`patchReload: live`）；原值保留在页首对照表与各行括注。依据两个包的 npm 元数据 |
| 纠错 | §来源与许可 把出处钉在 commit `10bb9cbf4a` | 该 commit 无法证实 → 降级为「据其 README 自述」，原表述保留在更正块内；补上可证实的包元数据（repository = ccch1mneyyy/dsh-TUI、`engines.node`）。依据 npm registry |
| 加厚 | §独立客户端路线 标为「当前推荐」，未记仓库活跃度 | 改为「可选原型」：补 ★0、默认分支 `feat/dsh-tui`、末次发布 2026-08-14 后无更新，并保留 `dsh-tui@0.2.19` 与 description 核实结果；依据 npm registry 与 GitHub 搜索 API |
| 加厚 | §安装 未说明 `@next` 与 `latest` 的关系 | 补 dist-tags 对照（`latest` 0.1.5-rc.1 / `next` 0.1.5-rc.2 / `alpha` 0.1.5-alpha.2）与双向验收命令；依据 npm registry |
| 加厚 | §状态与已知限制 把旧线 0.1.2 的限制当作现行限制 | 拆成「旧线 0.1.2 / 活跃线 0.10.1」两行表，并补一条读安装树 `package.json` 的版本自检命令 |

更正与依据登记：[[CORRECTIONS]]
