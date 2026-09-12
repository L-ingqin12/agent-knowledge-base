---
title: 来源登记 — DSH 与模型路由
aliases: [sources-dsh-routing, 模型路由来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-12
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

## 本机配置（含密钥，勿外传）

- 来源:: 本机 DSH settings.yaml
  use_when:: 改 provider/模型/思考强度；排查路由走了非预期模型
  url:: file:///C:/%USERPROFILE%/.dsh/settings.yaml
  answers:: agent-default-model、llm-pi-ai providers、逐请求重读行为、provider id 冲突原因
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
