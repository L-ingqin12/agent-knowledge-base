---
title: DSH 跨框架 Skills/MCP 加载指南
aliases: [DSH加载外部技能, dsh-bridges, DSH MCP 配置]
tags: [ai/agent, ai/skills, ai/links]
created: 2026-08-17
updated: 2026-09-13
status: review
source: "官方仓库 deepseek-ai/deepseek-harness + dsh-bridges 文档（2026-08 快照）"
source_urls:
  - "https://github.com/deepseek-ai/deepseek-harness"
  - "https://github.com/yhlooo/dsh-bridges"
fetched_at: 2026-08-19
---

# DSH 跨框架 Skills/MCP 加载指南

See also: [[AI-Links-KB-Home]] | [[2026-08-16-AI链接综述与归档]] | [[DSH-TUI插件使用手册]] | [[AGENTS]]

> [!abstract] 概述
> DeepSeek Harness（DSH）加载外部生态的 Agent Skills / MCP 有三条路径：**原生文件系统发现**（`.dsh/skills`、`.agents/skills`）、**原生 MCP 客户端插件**（`@deepseek-ai/dsh-mcp-client`）、以及社区桥接插件 **[dsh-bridges](https://github.com/yhlooo/dsh-bridges)**（把 Claude Code / CodeBuddy / OpenCode / Codex / Pi / Gemini CLI / Cursor 项目的技能、记忆、hooks、权限与 MCP 原样桥接进来，免迁移）。
> 依据官方仓库（deepseek-ai/deepseek-harness, dsh 0.1.0-rc 线）与 dsh-bridges 文档整理，2026-08 快照。

## 一、原生 Skill 发现（零配置）

DSH 的 skill 能力族（`dsh-skill` / `dsh-skill-filesystem` / `dsh-tool-skill`）从本地文件系统自动发现技能，模型通过 `skill` 工具加载。发现优先级（rank 小者优先，重名时近层胜出）：

| Rank | 来源 | 根目录 |
|---|---|---|
| 100 | 项目级 DSH | `<projectRoot>/.dsh/skills` |
| 200 | 项目级 agents 约定 | `<projectRoot>/.agents/skills` |
| 300 | 自定义 | `Config.customSkillDirs` |
| 400 | 用户级 DSH | `<dshHome>/skills` |
| 500 | 用户级 agents 约定 | `<agentsHome>/skills` |
| 600 | 随包内置 | `Config.bundledSkillDir` |

- **格式**：目录包 `<name>/SKILL.md` 或扁平文件 `<name>.md`；名称 kebab-case（`^[a-z0-9]+(?:-[a-z0-9]+)*$`）；不支持嵌套递归 `**/SKILL.md`。
- **项目根** = 向上最近的含 `.git` 目录；watcher 热更新，改技能无需重启会话。
- 模型目录里只暴露 `name` + `description`，正文通过 `skill` 工具按需加载。

> [!note] 2026-09-13 复核：rank 表逐项无误
> 六个 rank（100/200/300/400/500/600）与各自根目录一一对应，复核无误。其中「项目级 agents 约定」另有侧证：上游 `docs/session-format-status.zh.md` 正文即链接 `../.agents/notes/implemented/architecture/*.zh.md`，说明 `.agents` 是仓库级约定目录（`.claude` 本次未独立复核，不列为证据）。
> 来源：https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/session-format-status.zh.md

> [!tip] 含义：遵循 Claude Code 约定的 `.agents/skills` 目录（Codex 风格）在 DSH 里**原生可用**——把技能目录放到项目或用户 agents 根即可，无需任何插件。

## 二、原生 MCP 客户端（mcp-client）

`@deepseek-ai/dsh-mcp-client` 把外部 MCP 服务器工具注册进 `ctx.tools`，模型看到 `mcp__<serverName>__<rawName>` 形式（与 Claude Code / Codex 相同的服务器限定命名）。在 profile 的 `cordis.yml` / 补丁层中每服务器一个实例：

```yaml
- id: mcp-github
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: github
    transport: stdio            # 或 streamable-http
    command: npx
    args: ['-y', '@modelcontextprotocol/server-github']
    env:
      GITHUB_TOKEN: !!js process.env.GITHUB_TOKEN

- id: mcp-web
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: web
    transport: streamable-http
    url: http://localhost:3000/mcp
```

| 关键字段 | 说明 |
|---|---|
| `transport` | `stdio`（spawn 命令）或 `streamable-http`（远程 URL） |
| `serverName` | 工具命名空间，`[A-Za-z0-9_-]{1,32}` |
| `command` / `args` / `env` / `cwd` | stdio 传输用 |
| `url` / `headers` | HTTP 传输用（认证头） |
| `toolCallTimeoutMs` | 单次调用超时，默认 60000 |
| `failOnStartupError` | 启动失败是否拒绝激活，默认 false（静默降级） |
| `reconnect.*` | 自动重连：指数退避（初始 500ms 翻倍，上限 30s，连续 10 次放弃） |

行为要点：热更新（改配置即断连重连，`serverName` 不变则工具名不变）；`notifications/tools/list_changed` 自动重同步；命名冲突/重复 serverName 会报错回滚。
限制：**只桥接工具能力**，MCP 的 resources/prompts 暂不支持。

## 三、dsh-bridges：跨框架免迁移桥接（重点）

[dsh-bridges](https://github.com/yhlooo/dsh-bridges)（npm 同名包）是一个 DSH 插件：在**已为其他 Agent 配置过的项目**里，把现有 skills、commands、memory、hooks、权限与 MCP 原样桥接进 DSH，无需迁移任何文件。

### 3.1 安装与验证

```sh
dsh plugin --profile <profile-name> add dsh-bridges   # web 或 headless profile
dsh web                                               # 或 dsh --profile <profile-name>
dsh --profile <profile-name> --dump-config            # 应出现 dsh-bridges 行
```

> [!warning] `--profile` 的名字随本机安装形态变化（2026-09-13 复核）
> 「web 或 headless」不是固定集合：本机 2026-09-13 实测的 profiles 是 `desktop` / `dsh-tui` / `headless` / `web` / `tui.retired-20260912`（`node_modules` 另计），而本簇三篇文档对 profile 名单给出过三种答案。安装前先列目录：`dir %USERPROFILE%\.dsh\profiles`（POSIX：`ls "$DSH_HOME/profiles"`）。
> `--dump-config` 的期望片段是**出现 `# == dsh-bridges` 层标记 + 该行的完整 config**；同时记住它**只证明配置组合、从不 import 模块**（[[DSH插件发布与分发]] §1.5），不能当作"插件装好了"的证据。

headless（一次性 CLI）同样支持：`dsh plugin --profile headless add dsh-bridges` 后在项目目录 `dsh --profile headless "list the skills available in your catalog"`。从仓库安装：`pnpm install && pnpm build && dsh plugin --profile <p> add .`。

### 3.2 支持矩阵

资产按会话工作区发现（项目级 + 用户级位置），全部桥默认开启，可在补丁层按工具开关/配置：

| Agent 工具 | Skills/commands | Memory | Hooks | Permissions | MCP |
|---|---|---|---|---|---|
| Claude Code | ✓ | ✓ | ✓ | ✓ | ✓ |
| CodeBuddy Code | ✓ | ✓ | ✓ | ✓ | ✓ |
| **OpenCode** | ✓ | ✓ | — | ✓ | ✓ |
| Codex | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pi | ✓ | ✓ | — | — | — |
| Gemini CLI | ✓ | ✓ | ✓ | ✓ | ✓ |
| Cursor | ✓ | ✓ | ✓ | ✓ | ✓ |

> [!note] 矩阵的口径（2026-09-13 复核）
> - **对应版本**：本矩阵对应 `dsh-bridges` **0.2.4**（npm `latest`）；其 description 列出 Claude Code / Codex / opencode / CodeBuddy Code / pi / Gemini CLI / Cursor 七家，与本表七行一致，`repository` = yhlooo/dsh-bridges。来源：https://registry.npmjs.org/dsh-bridges/latest
> - **`—` 的两种含义要分开**：「上游根本没有这种配置」（如 OpenCode 无 hooks）与「上游有、本桥暂未实现」不是一回事，本表当前把两者写成了同一个符号——按工具逐项核对后应拆开标注。
> - **32 KiB 记忆预算超限时的可观测性**（§3.5）未记录：裁剪是静默发生还是有告警，本页未核实。

### 3.3 配置（补丁层覆盖）

```yaml
# 例：禁用 Pi 桥 / 关闭 Claude Code 桥
- id: bridges
  config:
    pi:
      enabled: false
```

### 3.4 OpenCode 桥接细节（示例）

- **Skills/commands**：读取 `.opencode/skills/<name>/SKILL.md`、`.opencode/commands/<name>.md`、`opencode.json(c)` 的 `command.<name>`，注册到 DSH skill 注册表（provider `opencode`），出现在模型技能目录、经 `skill` 工具加载、可用 `/name` 调用。目录**向上**发现到 git root；`skills.paths` 增加额外根；名称须合法（小写字母数字+单连字符），frontmatter 需 `name`（等于目录名）+ `description`（1-1024 字符）；`agent.<id>`（subagent/all 模式）转成 delegation-spec 技能。
- **Memory**：注入 `~/.config/opencode/AGENTS.md`（缺省回退 `~/.claude/CLAUDE.md`）、向上最近的 `AGENTS.md`、`instructions` 文件与 glob、`references` 的 `@alias`；预算 32 KiB（宽泛的用户级先裁，具体的最先截断）；远程 URL/git 引用不抓取。
- **Permissions**：读 `opencode.json(c)` 的 `permission`（bare 字符串或按 family 的对象，last-match 规则），在 `tools/pre-execute` 缝上执行；工具族映射 `read/edit/write→edit、bash→bash、subagent→task、web_search→websearch` 等；未映射工具（todo、MCP 工具等）回退 DSH 自身审批策略；未配置 permission 时桥完全让路。
- **MCP**：`opencode.json(c)` 的 `mcp` 条目桥为 `mcp__opencode__<server>__<tool>`：`type:"local"` → stdio（command 数组 + environment），`type:"remote"` → streamable-http（url + headers）；启动失败 fail open。
- **不桥接**：hooks（OpenCode 无此配置）、JS 插件系统与自定义工具（需要 OpenCode 运行时）、`$ARGUMENTS`/`@file` 模板替换、`skills.urls`（网络）、`agent/model/subtask` 命令选项、远程 config 层、provider/model 路由等。

### 3.5 所有桥的通用行为

- **原生技能优先**：重名时原生 DSH 技能（`.dsh/skills`、`.agents/skills`、runtime）遮蔽桥接资产。
- **32 KiB 记忆预算**：每桥独立，用户级宽泛段落先被裁。
- **热更新**：技能根与配置文件被 watch，会话内即时生效。
- **工具名翻译**：上游 hook 写的工具名自动翻译为 DSH 名，hooks 原样可用。
- **Fail open**：hook 超时/失败不阻塞动作（Cursor 的 `failClosed: true` 是唯一例外）。

## 四、实操速查

```sh
# 原生：把 skill 放进这些目录即可被模型看见
<project>/.dsh/skills/<name>/SKILL.md     # rank 100
<project>/.agents/skills/<name>/SKILL.md  # rank 200（Codex 约定）
~/.dsh/skills/…                           # rank 400

# 原生 MCP：profile 补丁（cordis.patch.yml）加 mcp-client 实例

# 跨框架：装桥接插件
dsh plugin --profile web add dsh-bridges
dsh web
dsh --profile web --dump-config | grep -A2 bridges
```

## 五、与本机环境的对应

- 本机 profiles（2026-09-13 复核）：`web`（dsh-base + dsh-web-app）、`desktop`、`headless`、`dsh-tui`（[[DSH-TUI插件使用手册]]），另有已退役目录 `tui.retired-20260912`。原表述为「`web`（dsh-base + dsh-web-app）、`tui`」——**`tui` 这个名字在本机已不复存在**。
- dsh CLI **0.1.5-rc.1**（原表述为 v0.1.0-rc.6）；上游 master `apps/cli/package.json` = 0.1.5-rc.2，npm dist-tags = `latest: 0.1.5-rc.1` / `next: 0.1.5-rc.2` / `alpha: 0.1.5-alpha.2`（自查：`npm view @deepseek-ai/dsh dist-tags`）。配套 Node 22.21（`%USERPROFILE%\nodejs-x64\node-v22.21.0-win-x64\`），系统 PATH 里的 node 仍是 v18（TUI 需要 ^22.19，勿混用）。
  来源：https://registry.npmjs.org/@deepseek-ai/dsh
- 与 [[2026-08-16-AI链接综述与归档]] 的关联：#1 antigravity-awesome-skills（1900+ 技能聚合）、#6 i-have-adhd（SKILL.md 最小样本）、#14/#15 图表技能，均可在 DSH 中以原生 skill 或 bridges 方式使用。

> [!warning] 时效性
> dsh-bridges 与官方 rc 线仍在快速迭代，矩阵与字段以上游最新文档为准；本文为 2026-08 快照。

## Related

- [[2026-08-16-AI链接综述与归档]] — 16 链接综述（技能生态条目）
- [[DSH-TUI插件使用手册]] — 本机 TUI 插件手册
- [[TYPORA-KB-Home]] — Skills 打包机制对照（typora-activation）
- [[AGENTS]] — 知识库规范

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §五 写「本机 profiles：`web`、`tui`」且 dsh CLI 为 v0.1.0-rc.6 | 改为现行五个 profile（含 `desktop` / `headless` / `dsh-tui` 与已退役的 `tui.retired-20260912`）与 CLI 0.1.5-rc.1，原表述保留在句内；依据 `$DSH_HOME/profiles` 实测与 npm dist-tags |
| 加厚 | §3.2 支持矩阵未标 dsh-bridges 版本；`—` 把「上游无此配置」与「本桥未实现」混为一谈；32 KiB 超预算是否可观测未记 | 矩阵后补口径块（对应 0.2.4）与两条待拆项；依据 https://registry.npmjs.org/dsh-bridges/latest |
| 加厚 | §一 rank 表正确但无复核痕迹 | 补 2026-09-13 复核块，并以官方 `docs/session-format-status.zh.md` 的路径侧证 `.agents` 约定 |
| 加厚 | §3.1 安装命令把 profile 名写死成「web 或 headless」，且未给 `--dump-config` 的期望输出 | 补 profile 名随安装形态变化的警告、列目录命令与期望片段（含「只证明配置组合」的限定） |

更正与依据登记：[[CORRECTIONS]]
