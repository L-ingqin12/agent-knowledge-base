---
title: 来源登记 — DSH 与模型路由
aliases: [sources-dsh-routing, 模型路由来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-13
status: draft
---

# 来源登记 — DSH 与模型路由

> [!abstract] 本页用途
> 存放「DSH 与模型路由」主题的来源条目，供 [[URL-Lookup]] 检索。
> 可读版见 [[URL-REGISTRY#2-dsh-与模型路由]]。

## 上游 API 文档

- 来源:: OpenRouter API 文档
  use_when:: 要改 provider / baseURL，或确认端点与鉴权头写法
  url:: https://openrouter.ai/docs
  answers:: 端点路径、请求格式、provider 路由规则
  authority:: 高
  verified:: 2026-09-12

- 来源:: OpenRouter 模型列表
  use_when:: **路由失效首查**——确认某个免费模型是否仍在上架
  url:: https://openrouter.ai/models
  answers:: 模型 id、上下架状态、定价、可用性
  authority:: 高
  verified:: 2026-09-12

- 来源:: DeepSeek 官方 API 文档
  use_when:: 查 deepseek 端点与 anthropic 兼容路径（web_search 走此路径）
  url:: https://api-docs.deepseek.com
  answers:: chat/completions 与 anthropic/v1/messages 端点、参数
  authority:: 高
  verified:: 2026-09-12

- 来源:: Anthropic API 文档
  use_when:: 核对 anthropic 消息格式与 web_search 工具声明
  url:: https://docs.anthropic.com
  answers:: Messages API、工具调用、web_search 工具规范
  authority:: 高
  verified:: 2026-09-12

- 来源:: deepseek-harness 官方 README（master）
  use_when:: 引用「官方推荐/唯一推荐的发现问题机制」一类论断前，核对原话与同节的其它渠道
  url:: https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/README.md
  answers:: 「Add the `dsh-plugin` topic to your plugin repository for discoverability」；同节另有 GitHub Discussions 与 Discord；首屏指向文档站
  authority:: 高
  verified:: 2026-09-13

- 来源:: DSH 官方文档站
  use_when:: 需要官方文档正文入口（README 首屏指向这里）
  url:: https://deepseek-harness.github.io/deepseek-harness/
  answers:: 官方文档首页与导航
  authority:: 高
  verified:: 2026-09-13

- 来源:: 官方 Session 格式发布状态
  use_when:: 需要「已发布格式的兼容义务」这一契约出处，或核对当前已发布格式版本
  url:: https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/session-format-status.zh.md
  answers:: latestReleasedVersion=3、evidenceTag=dsh-v0.1.5-alpha.1；alpha/beta/rc 发布同样确立持久化义务
  authority:: 高
  verified:: 2026-09-13

- 来源:: 官方 capability seams 文档
  use_when:: 查插件可消费的 ctx 服务/接缝清单与角色（seam / core / bundle）
  url:: https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/capability-seams.zh.md
  answers:: 服务角色全景表、mcp-client 等子系统的接缝归属
  authority:: 高
  verified:: 2026-09-13

- 来源:: 官方 CLI package.json（master）
  use_when:: 核对上游 master 的 CLI 版本号，与本机安装版本对照
  url:: https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/apps/cli/package.json
  answers:: version=0.1.5-rc.2（2026-09-13）
  authority:: 高
  verified:: 2026-09-13

## 本机配置（含密钥，勿外传）

- 来源:: 本机 DSH settings.yaml
  use_when:: 改 provider/模型/思考强度；排查路由走了非预期模型
  url:: file:///%USERPROFILE%/.dsh/settings.yaml
  answers:: agent-default-model、llm-pi-ai providers、逐请求重读行为、provider id 冲突原因。更正（2026-09-13，C8 复核同批）：本条原 url 为 `file:///C:/%USERPROFILE%/.dsh/settings.yaml`（原表述）——`file://` URI 里的 `%USERPROFILE%` 不会被展开、点不开；实测 `%USERPROFILE%\.dsh\settings.yaml` 存在（Test-Path 为 True）
  authority:: 高
  verified:: 2026-09-12

- 来源:: DSH TUI 插件使用手册
  use_when:: 查 TUI 安装、快捷键、端点配置
  url:: wikilink://DSH-TUI插件使用手册
  answers:: @dsh-tui/dsh-tui 用法与端点设置
  authority:: 高
  verified:: 2026-09-12

- 来源:: DSH 插件与 Hook 开发最佳实践
  use_when:: 要写 Cordis 插件 / 工具 / hook
  url:: wikilink://DSH插件与Hook开发最佳实践
  answers:: Cordis 插件体系、开发与发布清单
  authority:: 高
  verified:: 2026-09-12

## 模型切换与缓存（本库调研）

- 来源:: flash / ox-alpha 主模型切换分析
  use_when:: 要切换主模型或理解 ox-alpha 的定位
  url:: wikilink://claude-flash-primary-analysis
  answers:: 各模型切换影响面与结论
  authority:: 高
  verified:: 2026-09-12

- 来源:: DeepSeek 缓存键与扰动分离实验
  use_when:: 查缓存键构成、模型切换记录、ds2ox 原始拆解
  url:: wikilink://deepseek-cache-key-and-sep-experiments
  answers:: 前缀缓存键 = model + 内容前缀；不含 session-id
  authority:: 高
  verified:: 2026-09-12

- 来源:: cache-relay 设计文档
  use_when:: 要复用现役中继（密钥不落地、含健康检查与回滚）
  url:: wikilink://claude-cache-relay-design
  answers:: 多源缓存对齐中继的设计与回滚方式
  authority:: 高
  verified:: 2026-09-12

- 来源:: ds2ox-proxy 退役归档
  use_when:: 查已退役的本地路由代理及其 3 处设计缺陷
  url:: wikilink://ds2ox-proxy-retirement
  answers:: 路由行为、缺陷 D1-D3、残留复活路径
  authority:: 高
  verified:: 2026-09-12

- 来源:: Ark Agent Plan 计费与配置
  use_when:: 查 Ark 计划的计费方式与配置
  url:: wikilink://参考-Ark-Agent-Plan计费与配置
  answers:: Ark Agent Plan 计费与配置细节
  authority:: 中
  verified:: 2026-09-12

> [!note] 常见故障排查顺序
> 走错模型 → ① 查 `agent-default-model` ② 查是否有残留 `baseURL` 指向本地代理端口 ③ 查上游模型是否已下架

## A2 复核新增（2026-09-13）：DeepSeek / OpenRouter 上游口径

> 本次回写实际打开并逐字核对的官方来源；`use_when` 写「什么时候要回查」。

- 来源:: DeepSeek Models & Pricing（定价、模型名脚注与能力面）
  use_when:: 核对 flash / pro 的价格档位、off-peak 折扣、模型改名与上下文/并发/Vision 口径
  url:: https://api-docs.deepseek.com/quick_start/pricing
  answers:: 四档价（off-peak|peak，$/1M）：flash 0.003|0.006 / 0.15|0.30 / 0.60|1.20；pro 0.022|0.044 / 0.66|1.32 / 1.98|3.96；peak=周一至周五 01:00–04:00 与 06:00–10:00 UTC；脚注(1) 旧名 `deepseek-v4-flash` 仍接受但模型已退役、由 DeepSeek-V4.1-Flash 承接；脚注(2) V4 Pro 服务在 2026-09-14 之后延续；flash 1M 上下文 / 384K 输出 / 并发 2500 / 支持 Vision
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek Anthropic API 兼容页
  use_when:: 核对 `/anthropic` 端点的模型映射与 Header 表（判断「模型名写错会不会静默降级」）
  url:: https://api-docs.deepseek.com/guides/anthropic_api
  answers:: `claude-opus*`→`deepseek-v4-pro`（按 Pro 价计费）、`claude-haiku*`/`claude-sonnet*`→`deepseek-flash`、**不支持的模型名自动映射为 flash**；Header 表只列 anthropic-beta / anthropic-version / x-api-key（无 session-id 头）；`content[] type=thinking` 列为 Supported
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek Context Caching（前缀缓存）
  use_when:: 回答「缓存键由什么组成」「为什么这次没命中」时回查厂商口径
  url:: https://api-docs.deepseek.com/guides/kv_cache
  answers:: cache prefix unit 完整匹配；best-effort、不保证 100% 命中；构建需数秒、闲置数小时到数天自动清除；**未定义缓存键组成、未提任何请求头是否参与**
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek Error Codes
  use_when:: 归因某次 4xx/5xx 前先查官方错误码表，避免把「表里没有」当成「官方承认」
  url:: https://api-docs.deepseek.com/quick_start/error_codes
  answers:: 仅 400 Invalid Format、401/402/422/429/500/503；**无任何内容审核条目**
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek Thinking Mode
  use_when:: 排查 reasoning_content / thinking 协议类报错
  url:: https://api-docs.deepseek.com/guides/thinking_mode
  answers:: 要求按 OpenAI 格式把 assistant 的 `reasoning_content` 随 messages 回填（与 Anthropic 兼容面的 `content[] type=thinking` 属不同协议面）
  authority:: 高
  verified:: 2026-09-13

- 来源:: OpenRouter 模型清单与端点接口（JSON）
  use_when:: 判断某模型是否在架——脚本核对用 JSON 接口，别用网页列表
  url:: https://openrouter.ai/api/v1/models
  answers:: 实测 445 条模型（含 19 条 `:free`）；单模型端点走 `/api/v1/models/<id>/endpoints`，实测 `z-ai/glm-5.2:free` 与 `minimax/minimax-m3:free` 的 endpoints 均为 `[]`（已下线），`z-ai/glm-5.3-flash` 为 26 个
  authority:: 高
  verified:: 2026-09-13

- 来源:: OpenRouter 兜底目标端点（`z-ai/glm-5.3-flash`）
  use_when:: 400 兜底改投前确认目标模型在架；或核对兜底成本
  url:: https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints
  answers:: endpoints 26 个；pricing prompt $0.15/M、completion $0.5/M、cache_read $0.03/M
  authority:: 高
  verified:: 2026-09-13

## A3 复核新增（2026-09-13）：DeepSeek 缓存的粒度与命中口径

- 来源:: DeepSeek 上下文硬盘缓存发布公告（news0802）
  use_when:: 需要缓存**存储粒度**与**命中保证**的原文口径时（回答「小于多少 token 不会被缓存」「命中率能不能保证」）
  url:: https://api-docs.deepseek.com/news/news0802/
  answers:: *The cache system uses 64 tokens as a storage unit; content less than 64 tokens will not be cached*；缓存系统 **best-effort、不保证 100% 命中**；未使用条目通常在**数小时到数天**内清除；命中情况由响应里的 `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` 暴露
  authority:: 高
  verified:: 2026-09-13

## C4 复核新增（2026-09-13）：缓存单元语义与 Anthropic 兼容口径

- 来源:: DeepSeek Context Caching（官方指南）
  use_when:: 写缓存相关结论 / 判据前核对**现行**语义（「字节级前缀匹配 + ≥64 token 最小单元」是已过期的旧说法）
  url:: https://api-docs.deepseek.com/guides/kv_cache
  answers:: 命中需**完整匹配某个缓存前缀单元**（*Each cached prefix is an independent, complete unit*）；落盘单元三类（请求边界 / 公共前缀检测 / 固定 token 间隔）；TTL *usually within a few hours to a few days*；命中率口径只看 `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek Anthropic API 兼容（Claude Code 接入页）
  use_when:: 配置 `ANTHROPIC_BASE_URL`、写代理路径拼接逻辑，或核对 `cache_control` 是否真被处理
  url:: https://api-docs.deepseek.com/guides/anthropic_api
  answers:: `base_url = https://api.deepseek.com/anthropic`（请求落到 `/anthropic/v1/messages`）；兼容表：`tools[]` 与 message content 各块（text / tool_use / tool_result）的 `cache_control` 均为 *Ignored*（`system` 行只写 *Fully Supported*，未列 `cache_control`）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude 官方 prompt caching 文档
  use_when:: 对比两侧 TTL 与前缀匹配语义，或为「稳定在前、易变在后」补可引用判据
  url:: https://code.claude.com/docs/en/prompt-caching.md
  answers:: *The API caches by matching the start of each request, called the prefix*；TTL 有两档——*a five-minute TTL, and a one-hour TTL*（1 小时档按更高写入价计费，可用 `ephemeral_1h_input_tokens` / `ephemeral_5m_input_tokens` 观测）
  authority:: 高
  verified:: 2026-09-13

## 相关文档

- [[URL-Lookup]]
- [[URL-REGISTRY]]
- [[claude-flash-primary-analysis]]

## C6 复核新增（2026-09-13）：DeepSeek 计费口径（cache hit / miss 与空闲 / 峰值）

> C6 簇在核 `api-key-leak-postmortem` 事件 C 的「约 150 元 / 5 亿+ token」时发现：该数字**没有模型名、没有 hit/miss 拆分、没有计价日期**，导致「命中率必须 >95%」这类结论只在按高价模型计价时才成立。以下价目表是判别依据。

- 来源:: DeepSeek 官方 API 文档 · 模型与价格
  use_when:: 把「消耗了多少钱 / 多少 token」换算成模型与命中率，或反推某笔异常消耗是否可能
  url:: https://api-docs.deepseek.com/quick_start/pricing
  answers:: 2026-09-13 实测——`deepseek-flash`：cache-hit **$0.003**（空闲）/ $0.006（峰值），cache-miss **$0.15** / $0.3；`deepseek-v4-pro`：cache-hit **$0.022** / $0.044，cache-miss **$0.66** / $1.32。**空闲价 = 峰值价的一半；hit 与 miss 单价相差约 50 倍**。据此反推：¥150 ÷ 5×10⁸ token ≈ ¥0.3/M（≈$0.042/M）的混合单价，隐含命中率约 flash **74–88%**、v4-pro **≈97%**——所以「命中率 >95% 才可能」只在按 v4-pro 计价时成立，按 flash 计价 75% 上下即可
  authority:: 高
  verified:: 2026-09-13

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 本机 `settings.yaml` 条目的 url 写成 `file:///C:/%USERPROFILE%/.dsh/settings.yaml`——`file://` URI 不展开变量，点不开（C8 复核在 `sources/dep-cve.md`、`sources/security-audit.md` 发现同类写法，此为同批一致性修正） | 改为绝对路径 `file:///%USERPROFILE%/.dsh/settings.yaml`（2026-09-13 Test-Path 为 True）；原写法保留在条目 `answers` 的更正句内 |

> 说明：本篇主体内容由 DSH 路由相关簇维护，本行只是 C8 复核的附带路径修正（其余条目不在 C8 范围）。见 [[CORRECTIONS]]、[[AGENTS]]。
