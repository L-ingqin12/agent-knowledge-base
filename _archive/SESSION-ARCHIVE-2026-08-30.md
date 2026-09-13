---
title: SESSION-ARCHIVE 2026-08-30
aliases: [会话归档 2026-08-30, DSH升级与思考控制归档]
tags: [meta, session-archive, ai/agent]
created: 2026-08-30
updated: 2026-09-13
status: review
---

# 会话归档 — 2026-08-30：dsh/dsh-tui 升级 + 思考强度控制 + Token 优化

See also: [[AI-Links-KB-Home]] | [[DSH-TUI插件使用手册]] | [[DSH提效与Token插件调研]] | [[AGENTS]]

> [!abstract] 主题
> 1) 升级 DeepSeek Harness 与 TUI 客户端；2) 修正 dsh-tui 安装方式为直连路线；3) 思考强度（reasoning effort）开关配置；4) 自动 compact + 降低过度思考 token 耗用。

## 一、操作记录

### 1. 升级（已完成 ✅）

| 项 | 旧 | 新 | 方式 |
|---|---|---|---|
| `@deepseek-ai/dsh`（全局） | 0.1.0-rc.6 | **0.1.1-rc.2** | `npm i -g @deepseek-ai/dsh@latest` |
| `dsh-tui`（全局） | 未装（profile 集成旧路线） | **0.2.19** | `npm i -g dsh-tui` |

> [!note] 2026-09-13 复核回标（版本演进，上表原文不改）：npm registry 实测 dist-tags 为 `latest=0.1.5-rc.1`、`next=0.1.5-rc.2`、`alpha=0.1.5-alpha.2`——今天 `npm i -g @deepseek-ai/dsh@latest` 装到的不再是 0.1.1-rc.2，更新的 rc 在 `next` 通道而非 `latest`，上表方式列按当时记录保留但已不宜照抄。升级前先看 dist-tags，再决定用 `@latest` 还是 `@next`。
>
> 来源：https://registry.npmjs.org/@deepseek-ai%2Fdsh

### 2. 安装方式修正（已完成 ✅）

- 旧路线：`dsh --profile tui`（cordis 插件包 `@dsh-tui/dsh-tui`，profile 集成）
- 新路线（当前）：**`dsh web` 起 host（127.0.0.1:3080）+ `dsh-tui` 直连**，直接 `dsh-tui` 命令启动
- 端到端验证：`dsh-tui run "..."` 一次调用成功（非 429），会话请求头实测 `z-ai/glm-5.3-flash` + `reasoningEffort:"low"`

### 3. 模型路由修正（已完成 ✅）

- 默认模型 `z-ai/glm-5.2:free` → **`z-ai/glm-5.3-flash`**（:free 上游共享池持续 429；minimax-m3:free 实测无响应已标注失效）
- settings.yaml：`agent-default-model` 加 `reasoningEffort: low`；`reasoningEfforts` 声明 low/high/max（OpenRouter 实测仅此三档有效）

### 4. 思考强度控制（已完成 ✅，按需调整）

- **独立 dsh-tui 无内置思考控制**（源码核查 lib/commands.js：无 /model、/effort、/thinking）
- 控制入口 = **host 端 settings.yaml 热加载**：改 `agent-default-model.reasoningEffort` 新会话即生效；或 Web 端模型选择器 /model
- GLM-5.3-flash 实证：默认 max 思考（最费），`low` 有效降档（say ok 仅 26 reasoning tokens）；`disabled`/`none` 无效（GLM 思考不可关）

> [!note] 2026-09-13 复核回标（时效性快照）：§3/§4 的模型侧结论（默认模型改 glm-5.3-flash、`reasoningEfforts` 仅 low/high/max 有效、minimax-m3:free 无响应、GLM 思考不可关）均属 2026-08-30 的一次性实测，未经外部佐证——复核时抓 OpenRouter 模型页只得前端渲染骨架，无可引用文本，故不构成定论。复现方法：
>
> | 待复核项 | 复核方法 |
> |---|---|
> | 模型是否仍在列 | 调 `GET /api/v1/models` 读返回清单，不靠页面肉眼读 |
> | 档位是否有效 | 同一提示词分别用 low/high/max 发最小请求，比对返回的 reasoning token 数 |
> | 失效模型 | 保留请求 ID 与响应体再判失效，不凭单次超时下结论 |
>
> 来源：https://openrouter.ai/models

### 5. 自动 compact（已完成 ✅）

- web profile `cordis.patch.yml`：`compaction-basic` 配置 `auto: true` + `thresholdRatio: 0.75`（默认 0.8）+ 主力模型 0.7
- 工具结果压缩 `tool-result-pruner` 为 dsh-base 内建（8192/4096/1024），未改

> [!note] 2026-09-13 复核回标（补验收判据）：本机 `~/.dsh/profiles/web/cordis.patch.yml` 实测确含 `id: compaction-basic`、`auto: true`、`thresholdRatio: 0.75` 与主力模型段 `0.7`，与上文数字一致；缺的是「怎么判断它真的触发了」。补：
>
> | 项 | 判据 / 操作 |
> |---|---|
> | 触发证据 | 触发时要落盘字段名 + 输出片段：会话中出现 compact 触发条目及其 token 占比；无条目即未见触发 |
> | 阈值回归 | 0.75 与默认 0.8 各跑一次等长会话，对比触发时机先后 |
> | 失败信号 | 阈值过低 → 上下文被过早截断，表现为前文结论在后续轮次丢失 |
> | 生效方式 | `~/.dsh/settings.yaml` 热加载（新会话即生效）；`cordis.patch.yml` 需重启 host 才生效——改完要重启的是 host，不是 TUI |

## 二、排障过程（429 限流）

1. `dsh-tui run` 首次报 **429 `z-ai/glm-5.2:free is temporarily rate-limited upstream`**（OpenRouter 免费共享池）
2. 重试 6s 后仍 429 → 判定免费模型不可用
3. 直测 OpenRouter API：glm-5.3-flash 正常（付费）；minimax-m3:free 无响应（失效）
4. 切换默认模型 → 端到端恢复 ✅

## 三、关键结论

1. **免费模型不可作主力**（共享池限流 + GLM-5.2 最低思考档 high，省不了 token）
2. **GLM 系思考不可关闭，最低档 low**——省 token 唯一途径是降档
3. dsh 插件生态分 host 侧（TUI 生效）与 Web 侧（面板类，TUI 无效）；TUI 场景压缩插件官方 compaction-basic 已够用
4. settings.yaml **热加载** vs profile patch（cordis.patch.yml）**重启生效**，两者修改路径不同

## 四、产出

- [[DSH-TUI插件使用手册]] — 新增"独立客户端路线"章节（updated 2026-08-30）
- [[DSH提效与Token插件调研]] — 新增"思考强度控制实证"章节（updated 2026-08-30）
- 配置变更：`~/.dsh/settings.yaml`、`~/.dsh/profiles/web/cordis.patch.yml`（未入库，本地生效）

## 五、未解决问题 / 后续

- [ ] dsh-tui 交互式 TUI 未在真实 TTY 人工验收（本会话仅验证 run 模式）；建议用户在项目子目录跑 `dsh-tui` 体验
- [ ] 长期费用治理（budget 告警）尚未装（Web 面插件 dsh-cost-meter / dsh-budget，TUI 场景可后续评估）
- [ ] 升级到 rc.2 后 profile tui（旧路线）未验证，已保留未删
- [ ] 官方文档站 https://deepseek-harness.github.io/deepseek-harness/ 可作为后续配置查阅源

> [!note] 2026-09-13 复核回标：该站实测 HTTP 200、标题 DeepSeek Harness，可从「待确认的查阅源」升级为**已确认入口**；DeepSeek 官方 API 文档已把它列为 Agent Integrations 入口，具体路径为 `https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart`（Quick Start）。
>
> 来源：https://deepseek-harness.github.io/deepseek-harness/ ；https://api-docs.deepseek.com/

> [!success] 残余复核（2026-09-13）：§五 清单逐条本机核对（**只读**——未改配置、未装包、未起停任何服务）。
> - 「升级到 rc.2 后 profile tui（旧路线）未验证，已保留未删」→ **已变动，本条可结**：`%USERPROFILE%\.dsh\profiles\` 现为 `desktop`/`dsh-tui`/`headless`/`web` + **`tui.retired-20260912`** ⇒ 旧路线是**主动退役**（2026-09-12 改名归档），不是"留着待验证"。现行路线见 [[DSH-TUI插件使用手册]]。
> - 「长期费用治理（budget 告警）尚未装」→ **仍成立**：`npm ls -g --depth=0`（2026-09-13）仅 `@deepseek-ai/dsh@0.1.5-rc.1` 与 `@deepseek-harness-tui/dsh-tui@0.10.1`，无 cost/budget 类插件 ⇒ 保持未装，无需改动。
> - 「dsh-tui 交互式 TUI 未在真实 TTY 人工验收」→ **仍开放**（需人机交互，本次复核不具备条件）。判据：在项目子目录实跑 `dsh-tui`，确认无 [[DSH-TUI内部机制与键盘卡死陷阱]] 所记的输入卡死现象。
> - 顺带核到的版本漂移：本机 `dsh-tui@0.10.1`、`@deepseek-ai/dsh@0.1.5-rc.1`，均高于本归档记录的 `0.2.19` / `0.1.1-rc.2`（§一.1 的 dist-tags 回标方向一致）。

## Related

- [[DSH-TUI插件使用手册]] — TUI 两种安装路线
- [[DSH提效与Token插件调研]] — token 优化配置
- [[DSH插件与Hook开发最佳实践]] — 插件机制
- [[AI-Links-KB-Home]] — MOC
- [[AGENTS]] — 知识库规范

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 加厚 | 升级记录止于 0.1.1-rc.2，未标版本边界与通道语义 | §一.1 回标：npm registry 实测 dist-tags `latest=0.1.5-rc.1` / `next=0.1.5-rc.2` / `alpha=0.1.5-alpha.2`；原文不改，升级前先看 dist-tags |
| 加厚 | 模型侧结论（默认模型 / 档位 / 失效模型）无时效标注 | §一.4 回标：标为 2026-08-30 一次性实测快照，补 `/api/v1/models` 与最小请求比对 reasoning token 的复现方法 |
| 补疏漏 | compaction-basic 只记配置数字，无验收判据与生效路径 | §一.5 回标：补触发证据、0.75/0.8 对比回归、阈值过低失败信号，以及 settings.yaml 热加载 vs cordis.patch.yml 重启生效 |
| 加厚 | 官方文档站只写「可作为后续配置查阅源」 | §五 回标：实测 HTTP 200 升级为已确认入口，补 Quick Start 具体路径 |
| 排除 | §五「profile tui（旧路线）未验证，已保留未删」 | 本机 `%USERPROFILE%\.dsh\profiles\` 实测为 `tui.retired-20260912/`（另有 desktop/dsh-tui/headless/web）⇒ 旧路线已主动退役而非待验证；本条可结 |
| 补疏漏 | §五 budget 插件与 TTY 人工验收两项无判据 | budget 项：`npm ls -g --depth=0` 仅 dsh 与 dsh-tui，确认未装（仍成立）；TTY 项仍开放并补判据（实跑 `dsh-tui` 查键盘卡死）。附核版本漂移：dsh-tui 0.10.1 / dsh 0.1.5-rc.1 |

复核入口：[[CORRECTIONS]]（本批审计与复核结论）
