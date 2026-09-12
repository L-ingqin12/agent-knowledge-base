---
title: 来源登记 — 代理与中继
aliases: [sources-proxy-relay, 代理中继来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-12
status: draft
---

# 来源登记 — 代理与中继

> [!abstract] 本页用途
> 存放「代理与中继」主题的来源条目，供 [[URL-Lookup]] 检索。
> 可读版见 [[URL-REGISTRY#3-代理与中继本库自有资产]]。

## 现役资产

- 来源:: cache-relay 实现
  use_when:: 要复用或排障现役中继（:8790）
  url:: file:///D:/Document/local/knowledge/scripts/claude-ops-deployments/cache-relay/cache-relay.mjs
  answers:: 多源缓存对齐策略、provider 自动识别、软回滚开关、健康检查路径
  authority:: 高
  verified:: 2026-09-12

- 来源:: 部署管控框架
  use_when:: 任何生产改动前，确认部署四规则（记录/预检/逃生/审计）
  url:: wikilink://deployment-framework
  answers:: 四规则定义、deploy.sh 与 rollback.sh 约定
  authority:: 高
  verified:: 2026-09-12

- 来源:: 部署审计日志
  use_when:: 查历史部署与逃生记录
  url:: file:///D:/Document/local/knowledge/scripts/claude-ops-deployments/deployment-log.md
  answers:: 每次部署的时间/变更/预检/E2E/逃生/commit
  authority:: 高
  verified:: 2026-09-12

## 已退役资产

- 来源:: ds2ox-proxy 脱敏归档
  use_when:: 要查已退役路由代理的实现或缺陷
  url:: file:///D:/Document/local/knowledge/scripts/claude-ops-deployments/ds2ox-proxy/ds2ox-proxy.mjs
  answers:: 路由改写逻辑、熔断策略、3 处设计缺陷；密钥已外置
  authority:: 高
  verified:: 2026-09-12

- 来源:: ds2ox-proxy 退役归档说明
  use_when:: 处置该代理的文件与凭据，或确认残留复活路径
  url:: wikilink://ds2ox-proxy-retirement
  answers:: 退役判定证据、凭据处置顺序、配置来源
  authority:: 高
  verified:: 2026-09-12

## 事故复盘（同类问题先查这里，避免重犯）

- 来源:: 代理部署事故复盘
  use_when:: 部署代理前，查已有踩坑记录
  url:: wikilink://claude-proxy-deployment-postmortem
  answers:: 代理部署中的失效模式
  authority:: 高
  verified:: 2026-09-12

- 来源:: cancel/retry hook 事故
  use_when:: 排查代理的取消/重试行为异常
  url:: wikilink://proxy-cancelretry-hook-incident
  answers:: cancel 与 retry 交互引发的问题
  authority:: 高
  verified:: 2026-09-12

- 来源:: 代理重启事故
  use_when:: 排查代理重启后的状态一致性问题
  url:: wikilink://claude-proxy-restart-incident
  answers:: 重启引发的故障与处置
  authority:: 高
  verified:: 2026-09-12

- 来源:: cache-relay 缓存事故
  use_when:: 排查缓存命中率异常
  url:: wikilink://claude-cache-incident-postmortem
  answers:: 缓存失效根因与修复
  authority:: 高
  verified:: 2026-09-12

- 来源:: 端口重绑定方案
  use_when:: 代理端口被占用或需换端口
  url:: wikilink://claude-port-rebind-solution
  answers:: 端口重绑定的做法
  authority:: 中
  verified:: 2026-09-12

- 来源:: 代理韧性优化
  use_when:: 要提升代理在断网/超时下的稳定性
  url:: wikilink://proxy-resilience-optimization-2026-07-09
  answers:: 代理韧性优化措施
  authority:: 中
  verified:: 2026-09-12

> [!tip] 新写代理时的最低要求（从 ds2ox 的 3 处缺陷反推）
> ① 入站鉴权 ② `Host` 头校验 ③ 不固定监听端口或改用本地套接字；
> ④ 密钥不落地（参照 cache-relay 的透传头做法）。

## 相关

- [[claude-resilience-architecture]]
