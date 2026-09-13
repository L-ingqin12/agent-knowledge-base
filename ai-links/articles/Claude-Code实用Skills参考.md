---
title: "Claude Code 实用 Skills 参考"
aliases: [Claude Code Skills, 实用Skills清单, 小金AI Skills]
tags: [ai/skills, ai/learning]
created: 2026-06-17
updated: 2026-09-13
status: stable
source: "微信公众号"
source_urls:
  - "https://mp.weixin.qq.com/s/gRzmPovqR3ygTDuxkMX-4w"
author: "小金AI"
date: "2026-06-17"
fetched_at: "2026-06-22"
---

# Claude Code 实用 Skills 参考

See also: [[AI-Links-KB-Home]] | [[Articles-Index]] | [[Anthropic-Skill系统深度分析]] | [[Skill规模化管理-从渐进式披露到检索式发现]] | [[上下文工程落地实践-从理论到Claude-Code实现]]

## 摘要

覆盖开发全流程的 10 个 Skills：Superpowers（TDD+Code Review 流程约束）、Everything Claude Code（现名 ECC，多 Agent 分工防上下文腐化）、Doc Co-Authoring（PRD/技术方案协作写作）、UI UX Pro Max（设计系统生成）、sanyuan-skills（多维度代码审查）、Web Access（CDP 浏览器自动化）、Webapp Testing（Playwright 本地验收）、MCP Builder（内部 API→Agent 工具封装）、Claude API（SDK/流式/缓存参考）、skill-creator（元技能创建工具）；补录官方 marketplace 的 document-skills（xlsx/docx/pptx/pdf）。

核心原则：Superpowers 和 sanyuan-skills 兜底开发流程与代码质量；Webapp Testing 补前端验收；MCP Builder 和 skill-creator 面向团队工具化。按需选取，不必全装。

---

## 技能清单

### 1. Superpowers — 开发流程约束

将需求澄清、方案拆解、Git Worktree、TDD、Code Review、调试、完成前验证固化为 Skills，让 AI 按固定步骤执行。

| 技能 | 触发 | 功能 |
|------|------|------|
| brainstorming | `/superpowers:brainstorm` | 追问目标/约束/边界 → 设计文档 |
| using-git-worktrees | 自动 | 独立 Git worktree 隔离任务 |
| writing-plans | 自动 | 拆成 2-5 分钟粒度小任务 |
| test-driven-development | 自动 | 红-绿-重构，先补测试再补实现 |
| subagent-driven-development | 自动 | 独立子 Agent 执行，事后检查 |
| requesting-code-review | 自动 | 合入前派发 reviewer 子 Agent 做第二轮质量检查 |
| receiving-code-review | 触发式 | 按严重度回应审查意见 |
| systematic-debugging | 触发式 | 分阶段定位问题来源 |
| verification-before-completion | 自动 | 无测试/日志/命令输出则不能宣布完成 |
| finishing-a-development-branch | 触发式 | 合并/PR/保留/丢弃决策 + 清理 worktree |
| executing-plans | 触发式 | 分批执行 + 人工检查点 |
| dispatching-parallel-agents | 触发式 | 并行子 Agent 分派 |
| writing-skills | 触发式 | 编写新 skill |
| using-superpowers | 触发式 | 技能体系入口/元技能 |

安装（按 README 的优先级）：首选官方 marketplace —— `/plugin install superpowers@claude-plugins-official`（入口 [claude.com/plugins/superpowers](https://claude.com/plugins/superpowers)）；其次第三方 —— `/plugin marketplace add obra/superpowers-marketplace` → `/plugin install superpowers@superpowers-marketplace`

仓库：[github.com/obra/superpowers](https://github.com/obra/superpowers)

**已知失败模式（官方 README）**：

- **bootstrap 丢失**：README 原文「post-compaction hook, so a very long session that compacts over its first turn loses the bootstrap — start a fresh session if skills stop triggering」——超长会话一旦把首轮压缩掉，技能会集体不再触发；处置办法是**新开会话**，不是重装。
- **遥测**：README 专设「Visual companion telemetry」节——brainstorming 的可视化配套功能默认从作者网站加载带版本号的 Prime Radiant logo，可用 `SUPERPOWERS_DISABLE_TELEMETRY` 关闭，并遵循 Claude Code 的 `DISABLE_TELEMETRY` / `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`；安装前应知情。

> [!warning] 更正（2026-09-13）：
> 1. 原表第 6 行写的技能名 `code-review` **在仓库里不存在**（原表述为「code-review | 自动 | 合入前第二轮质量检查」）。README 的 What's Inside 与 The Basic Workflow 列出的名字是 `requesting-code-review`（Pre-review checklist；「Activates between tasks. Reviews against plan, reports issues by severity. Critical issues block progress.」）与 `receiving-code-review`（Responding to feedback）；`skills/requesting-code-review/SKILL.md` 的 frontmatter 确认为 `name: requesting-code-review`，description 为「Use when completing tasks, implementing major features, or before merging to verify work meets requirements」——与表内「合入前第二轮质量检查」的功能描述吻合，属**技能名写错**。该 SKILL.md 明确要求派发一个 general-purpose subagent 而非自己看 diff。
> 2. 原表漏了 Superpowers 的五个技能：`finishing-a-development-branch`、`executing-plans`、`dispatching-parallel-agents`、`writing-skills`、`using-superpowers`，均在 README 中逐条列出（现表已补）。
> 3. 安装路径优先级订正：README 把「official Claude plugin marketplace」列为第一条，`obra/superpowers-marketplace` 是第二条（「The Superpowers marketplace provides Superpowers and some other related plugins for Claude Code.」），并非首选。
> 来源：https://raw.githubusercontent.com/obra/superpowers/main/README.md ；https://raw.githubusercontent.com/obra/superpowers/main/skills/requesting-code-review/SKILL.md

### 2. Everything Claude Code（现名 ECC）— 多 Agent 分工

将 Claude Code 工作拆到 Agents/Skills/Hooks/Rules/Commands 五类配置中，对抗长任务上下文腐化。

- Agents：规划、架构、TDD、审查分别交给不同子 Agent
- Skills：沉淀可复用工作流（测试优先、后端规范等）
- Hooks：关键节点自动检查（提交前扫调试日志）
- Rules：团队/个人长期生效的编码规则
- Commands：`/tdd`、`/code-review` 等快捷触发

仓库：[github.com/affaan-m/ECC](https://github.com/affaan-m/ECC)（原名 `affaan-m/everything-claude-code`）

> [!warning] 更正（2026-09-13）：该实体已**改名并扩张**（原表述为「仓库：github.com/affaan-m/everything-claude-code」，定位描述也只有「五类配置 + 对抗上下文腐化」）。
> - 现 `full_name` = `affaan-m/ECC`，description =「The agent harness performance optimization system. Skills, instincts, memory, security, and research-first development for Claude Code, Codex, Opencode, Cursor and beyond.」，`created_at` = 2026-01-18T00:51:51Z，homepage = https://ecc.tools；复核日 `stargazers_count` = 257,373（同日稍早快照为 257,361，方向一致，宜写「约 25.7 万」）。
> - README 首页自述「ECC - the agent harness operating system」，能力已从「五类配置」扩张到：instinct 式持续学习（`/instinct-status`、`/instinct-import`、`/instinct-export`、`/evolve` 把 instinct 聚类成 skill）、安全扫描（`/security-scan` 扫描 CLAUDE.md / settings.json / MCP 配置 / hooks / agent 定义 / skills，14 条密钥模式，`--opus` 走红队/蓝队/审计三 Agent 流水线，严重发现 exit code 2，配套 [github.com/affaan-m/agentshield](https://github.com/affaan-m/agentshield)）以及多 harness 支持。
> - 因此「五类配置」应读作**旧定位**；条目名保留原写法以便回溯，但检索时请用 ECC。
> 来源：https://api.github.com/repos/affaan-m/ECC ；https://raw.githubusercontent.com/affaan-m/everything-claude-code/main/README.md

### 3. Doc Co-Authoring — 需求文档协作

编码前使用，将模糊需求整理为 PRD、技术方案、决策文档、RFC。

三阶段流程：
1. Context Gathering — 收集背景、约束、历史讨论、架构依赖
2. Refinement & Structure — 按章节打磨：提问→展开→筛选→成段
3. Reader Testing — 换全新上下文 Claude 读文档，检查遗漏和误解

安装：`/plugin marketplace add anthropics/skills` → `/plugin install example-skills@anthropic-agent-skills`

仓库：[github.com/anthropics/skills](https://github.com/anthropics/skills)

### 4. UI UX Pro Max — 设计系统生成

根据产品类型和行业特性自动输出完整设计系统（Design System）。

内置知识库（截至 2026-09-13）：79 种可检索 UI 风格（其中 50 个 active）、192 个行业色板、74 组字体搭配、192 条推理规则、119 条 UX 准则、22 个框架/技术栈指南、34 个 landing-page 结构模式、1,934 个已审定 Google Fonts。

安装：`/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill` → `/plugin install ui-ux-pro-max@ui-ux-pro-max-skill`

替代方案：Anthropic 官方 `frontend-design` skill，轻量级，专注避免 AI 生成的套路美学。

仓库：[github.com/nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)

**常见故障处置（官方 README Troubleshooting）**：

| 症状 | 处置 |
|------|------|
| 安装报 `Zip file contains a symbolic link` | v2.5.1 之前的已知问题（仓库内部用了 symlink）→ 改用 CLI 安装器 `npm install -g ui-ux-pro-max-cli && uipro init --ai claude` 或 `npx ui-ux-pro-max-cli init --ai claude` |
| 全局安装权限报错 | 用 Node 版本管理器，或直接 `npx` 免全局 |
| 提示找不到 Python | 需自行安装 Python 3.x（README 明确「AI agents should not install it for you — they are instructed to ask you instead」） |
| 输出被截断 | 人类可读输出把长字段截到 300 字符，改用 `python3 .claude/skills/ui-ux-pro-max/scripts/search.py 'SaaS' --domain style --json` 取完整数据 |

> [!warning] 更正（2026-09-13）：原「内置知识库」一行的**六个数字全部过期**（原表述为「67 种 UI 风格、161 个行业色板、57 种字体搭配、161 条推理规则、99 条 UX 准则、13 种技术栈」）。按 README 现状：顶部徽章标注 `reasoning_rules-192` 与 `UI_styles-79_searchable`；正文「Core UI/UX Intelligence」段写「79 searchable UI styles (50 active), 192 product types, color palettes, and curated font pairings」；分项列「192 Color Palettes - Industry-specific palettes aligned 1:1 with the 192 product types」「74 Font Pairings」「119 UX Guidelines」及「Stack-specific guidelines supporting 22 major frameworks」。active 集覆盖 43 个通用视觉族、2 个移动专属风格、3 个官方平台/设计系统（Fluent 2 / Shopify Polaris / Adobe Spectrum）、1 个平台 material、1 个核心分析风格。此类计数易漂移，引用时请带「截至 2026-09-13」或直接回查 README。
> 来源：https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/main/README.md

### 5. sanyuan-skills — 多维度代码审查

三个核心技能：

| 技能 | 功能 |
|------|------|
| Code Review Expert | SOLID/安全/性能/错误处理/边界条件/代码质量审查 |
| Sigma | 基于 Bloom's 2-Sigma 理论的苏格拉底式 AI 导师 |
| Skill Forge | 元技能，内置 12 种实战技术用于创建新 Skill |

安装：`npx skills add sanyuan0704/sanyuan-skills --path skills/code-review-expert`

仓库：[github.com/sanyuan0704/sanyuan-skills](https://github.com/sanyuan0704/sanyuan-skills)

### 6. Web Access — 浏览器自动化

补足 Claude Code 自带 WebSearch/WebFetch 的编排和浏览器自动化缺口。

能力：自动工具选择（WebSearch/WebFetch/curl/Jina/CDP）、CDP 直连 Chrome 携带登录态、并行分治多目标、站点经验跨会话积累、DOM 边界穿透（Shadow DOM/iframe）。

前置条件：Node.js 22+；Chrome（`chrome://inspect/#remote-debugging`）**或 Edge**（`edge://inspect/#remote-debugging`，勾选 "Allow remote debugging for this browser instance"）开启远程调试。

安装：`npx skills add eze-is/web-access`（README 标注的「方式一：npx skills 一键安装（推荐）」）；另有「方式二：让 Agent 自动安装」「方式三：Plugin 安装（Claude Code）」——即 `git clone https://github.com/eze-is/web-access ~/.claude/skills/web-access`——与「方式四：手动」。

仓库：[github.com/eze-is/web-access](https://github.com/eze-is/web-access)

> [!warning] 更正（2026-09-13）：原安装行直接给 `git clone`，读者会以为那是标准做法——它其实是 README 的**方式三**，推荐方式是 `npx skills add`（原表述为「前置条件：Node.js 22+，Chrome 开启远程调试（chrome://inspect/#remote-debugging）。安装：git clone https://github.com/eze-is/web-access ~/.claude/skills/web-access」）。
> 另订正两点：①CDP 通道**已不再绑定 Chrome**——README 更新记录原文「Microsoft Edge 支持 — CDP Proxy 不再绑定 Chrome，新增 Edge 适配（及 Chromium、Chrome Canary 等 Chromium 系，通过同一套自动发现机制接入）」；可用 `config.env` 的 `WEB_ACCESS_BROWSER` 固定默认浏览器，也支持单次覆盖 `--browser <chrome|edge>`。②Node.js 22+ 与 `chrome://inspect/#remote-debugging` 两项核对无误，保留并并列补上 Edge 入口。
> 仓库本体：`created_at` = 2026-03-18，复核日 stargazers 8,922、forks 638。
> **使用前提醒（README）**：通过浏览器自动化操作社交平台存在账号被限流或封禁风险，建议使用小号。
> 来源：https://raw.githubusercontent.com/eze-is/web-access/main/README.md ；https://api.github.com/repos/eze-is/web-access

### 7. Webapp Testing — 本地前端验收

基于 Playwright 的本地 Web 应用交互测试。

能力：服务生命周期管理（自动启停）、networkidle 后 DOM 检查、截图与控制台日志捕获、元素发现→可靠选择器。

典型用法：AI 写完管理后台页面后，打开 `localhost:5173`，检查按钮/表单/弹窗/暗色模式/移动端布局。

最小验收动作：其 SKILL.md 明确要求「**Always run scripts with `--help` first**」，故第一步是 `python scripts/with_server.py --help`（可验证、低成本，先确认脚本存在且参数对得上，再写测试）。

Common Pitfall（SKILL.md 原文）：❌ 在动态应用上未等 `networkidle` 就检查 DOM。

仓库：[github.com/anthropics/skills](https://github.com/anthropics/skills)

> 来源：https://raw.githubusercontent.com/anthropics/skills/main/skills/webapp-testing/SKILL.md

### 8. MCP Builder — 内部 API 封装

指导构建 MCP Server，将内部 API 封装为 Agent 可调用工具。覆盖 Python FastMCP 和 Node/TypeScript MCP SDK。

适用场景：OpenAPI→MCP 工具、数据库受控查询、部署/日志/告警平台动作封装、团队 Agent 工具层沉淀。

仓库：[github.com/anthropics/skills](https://github.com/anthropics/skills)

### 9. Claude API — SDK 开发参考

覆盖模型选择、价格、参数、流式输出、工具调用、MCP、Agent、缓存、Token 计算、模型迁移。支持 Python/TypeScript/Java/Go/Ruby/PHP/C#/cURL。

核心约束：「先查文档再写代码」——遇到 SDK 方法名、参数、流式事件时禁止凭印象写。

安装：`/plugin install claude-api@anthropic-agent-skills`——**`claude-api` 是独立插件**，不属于 `example-skills`（原清单把它与 example-skills 混在一起）。

仓库：[github.com/anthropics/skills](https://github.com/anthropics/skills)

### 10. skill-creator — 元技能

创建、修改、优化 Skill 的开发工具。

工作流：意图捕获 → 起草 SKILL.md → 测试验证（有 Skill vs 无 Skill 对比实验）→ 迭代优化 → description 优化。

内置可视化评测报告系统。

仓库：[github.com/anthropics/skills](https://github.com/anthropics/skills)

### 11. Document Skills — 官方文档处理四件套（2026-09-13 补）

原清单 10 条完全没有覆盖 Anthropic 官方 `anthropics/skills` 里最常用的 document-skills，也没交代各技能所属的插件名——这直接决定安装命令写对没写对。

官方 marketplace（`name` = `anthropic-agent-skills`）共 5 个插件：

| 插件 | 内容 | 安装 |
|------|------|------|
| `document-skills` | `xlsx` / `docx` / `pptx` / `pdf` 四个文档处理技能——官方最核心的一类 | `/plugin install document-skills@anthropic-agent-skills` |
| `example-skills` | 恰好 12 个：`algorithmic-art`、`brand-guidelines`、`canvas-design`、`doc-coauthoring`、`frontend-design`、`internal-comms`、`mcp-builder`、`skill-creator`、`slack-gif-creator`、`theme-factory`、`web-artifacts-builder`、`webapp-testing` | `/plugin install example-skills@anthropic-agent-skills` |
| `claude-api` | 单技能插件（见第 9 条） | `/plugin install claude-api@anthropic-agent-skills` |
| `academy-guide` | 单技能插件 | 同上形式 |
| `discernment-nudge` | 单技能插件 | 同上形式 |

本文第 3 条 Doc Co-Authoring 写的 `/plugin install example-skills@anthropic-agent-skills` 经核对**正确**（marketplace 名与插件名均对应），可作为其余条目的写法模板。

> 来源：https://raw.githubusercontent.com/anthropics/skills/main/.claude-plugin/marketplace.json ；https://code.claude.com/docs/en/skills

---

## 通用安装与验收协议（2026-09-13 补）

本清单多数条目原来只有「一句功能 + 仓库链接」，缺安装命令、最小验收动作与失败处置。补一套通用三段式，配合各条目已有的具体故障表现使用：

1. **安装** —— 尽量写成 `plugin@marketplace` 或 `npx skills add <owner/repo>` 的完整形式，不要用裸 `git clone`（那是插件安装路径之一，不是首选）；装前先确认 marketplace 名（如 `anthropic-agent-skills`、`claude-plugins-official`）。
2. **最小验收** —— 官方口径「Seeing a skill trigger tells you Claude found it, not that it did what you intended.」因此要**新开会话**做「技能可用 vs 禁用」的基线对比，而不是在同一会话里看它有没有被调用；对带脚本的技能，先跑 `--help` 确认入口存在（见第 7 条）。
3. **失败处置** —— 记下「症状 → 处置」的对应关系（第 4 条的 Troubleshooting 表即范例）；技能集体不触发时先怀疑 bootstrap 与会话长度（见第 1 条），不要急着重装。

> 来源：https://code.claude.com/docs/en/skills

---

## 选取建议

| 场景 | 推荐 |
|------|------|
| 通用开发流程 | Superpowers |
| 多角色长任务 | ECC（原 Everything Claude Code） |
| 需求文档化 | Doc Co-Authoring |
| 文档处理 | Document Skills（xlsx/docx/pptx/pdf） |
| UI 设计 | UI UX Pro Max（重）/ frontend-design（轻） |
| 代码审查 | sanyuan-skills |
| 网页操作 | Web Access |
| 本地前端验收 | Webapp Testing |
| 工具集成 | MCP Builder |
| API 开发 | Claude API |
| 自制 Skill | skill-creator |

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 第 4 条 UI UX Pro Max 的六个计数全部过期（67/161/57/161/99/13） | 改为 79 风格（50 active）/192 色板/74 字体搭配/192 推理规则/119 UX 准则/22 框架 + 34 landing 模式 + 1,934 Google Fonts，并加「截至 2026-09-13」口径（来源 README） |
| 纠错 | 第 2 条仓库与定位为旧名 `everything-claude-code` | 标注现名 `affaan-m/ECC`、约 25.7 万 star、homepage ecc.tools，能力扩张到 instinct/安全扫描/多 harness；「五类配置」标为旧定位 |
| 纠错 | 第 1 条技能表 `code-review` 在仓库中不存在 | 拆为 `requesting-code-review`（派发 reviewer 子 Agent）与 `receiving-code-review`，并补回漏列的五个技能（来源 superpowers README + SKILL.md） |
| 纠错 | 第 6 条 Web Access 以 `git clone` 作安装行、CDP 绑定 Chrome | 改为推荐 `npx skills add eze-is/web-access`（git clone 是方式三），并列 Edge 入口与 `WEB_ACCESS_BROWSER`；补账号限流风险的知情提醒 |
| 纠错 | 第 9 条把 `claude-api` 与 `example-skills` 混在一起 | 标注 `claude-api` 为独立插件，补 `/plugin install claude-api@anthropic-agent-skills` |
| 补疏漏 | 全文没有官方 document-skills，也未交代技能所属插件名 | 新增第 11 条：`anthropic-agent-skills` marketplace 的 5 个插件结构（document-skills / example-skills 12 项 / claude-api / academy-guide / discernment-nudge） |
| 补疏漏 | 第 1 条无已知失败模式与使用前提醒 | 补 README 的三条：bootstrap 丢失须新开会话、Visual companion 遥测及关闭开关、官方 marketplace 为首选安装路径 |
| 加厚 | 全篇条目缺「安装 → 最小验收 → 常见故障处置」 | 新增「通用安装与验收协议」一节 + 第 4 条 Troubleshooting 表（4 条症状→处置）+ 第 7 条 `--help` 最小验收与 Common Pitfall |

来源登记：[[sources/learning-notes]]（B7 复核新增一节）
回链：[[CORRECTIONS]] | [[AGENTS]]
