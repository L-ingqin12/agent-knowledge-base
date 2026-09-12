---
title: 来源登记 — 网络与设备
aliases: [sources-network-device, 网络设备来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-12
status: draft
---

# 来源登记 — 网络与设备

> [!abstract] 本页用途
> 存放「网络与设备」主题的来源条目，供 [[URL-Lookup]] 检索。
> 可读版见 [[URL-REGISTRY#4-网络与设备]]；子库入口 [[Network-KB-Home]]。

## 子库入口与手册

- 来源:: 网络子库 MOC
  use_when:: 不知道网络问题该看哪篇时的入口
  url:: wikilink://Network-KB-Home
  answers:: 网络子库全部文档地图
  authority:: 高
  verified:: 2026-09-12

- 来源:: 路由器完整能力手册
  use_when:: 查路由器型号/固件/SSH 接入方式
  url:: wikilink://ROUTER-FULL-CAPABILITY
  answers:: R4CM 192.168.31.1 fw 2.14.87、SSH root@22、legacy crypto 要求
  authority:: 高
  verified:: 2026-09-12

- 来源:: 小米路由器 API 认证与利用
  use_when:: 要通过 API 而非 SSH 操作路由器
  url:: wikilink://参考-小米路由器API认证与利用
  answers:: 小米路由器 API 的认证流程
  authority:: 高
  verified:: 2026-09-12

- 来源:: 网络路由与代理排障
  use_when:: 路由/代理分层排障
  url:: wikilink://参考-网络路由与代理排障
  answers:: 路由与代理的排障路径
  authority:: 中
  verified:: 2026-09-12

- 来源:: VPN 代理诊断与优化
  use_when:: 代理连通性/速度异常的诊断
  url:: wikilink://参考-VPN代理诊断与优化
  answers:: VPN/代理诊断与优化方法
  authority:: 中
  verified:: 2026-09-12

## 架构与日常操作

- 来源:: 网络架构说明
  use_when:: 要理解本机网络的整体拓扑与代理分层
  url:: wikilink://ARCHITECTURE
  answers:: 网络架构设计（v2rayN + xray 26.3.27，端口 10808）
  authority:: 高
  verified:: 2026-09-12

- 来源:: 网络日常操作指南
  use_when:: 执行日常网络操作
  url:: wikilink://GUIDE
  answers:: 日常操作步骤、配置脚本用法
  authority:: 高
  verified:: 2026-09-12

- 来源:: 网络优化总结
  use_when:: 回顾已完成的优化项
  url:: wikilink://FINAL-SUMMARY
  answers:: 优化成果与关键数据
  authority:: 中
  verified:: 2026-09-12

## 复盘与专项

- 来源:: 树莓派网络故障与路由器破解复盘
  use_when:: 处理路由器故障或需要完整排查复盘
  url:: wikilink://2026-07-21-树莓派网络故障与路由器破解完整复盘
  answers:: 完整故障链路与破解过程
  authority:: 高
  verified:: 2026-09-12

- 来源:: 路由器深度探索
  use_when:: 需要挖掘路由器未公开能力
  url:: wikilink://ROUTER-DEEP-EXPLORATION
  answers:: 路由器的深层能力探索记录
  authority:: 中
  verified:: 2026-09-12

- 来源:: 路由器优化
  use_when:: 优化路由器本身的配置
  url:: wikilink://ROUTER-OPTIMIZATION
  answers:: 路由器侧优化项
  authority:: 中
  verified:: 2026-09-12

- 来源:: 远程视频监控方案
  use_when:: 配置路由器的远程监控
  url:: wikilink://ROUTER-VIDEO-REMOTE-MONITOR
  answers:: 远程监控配置方法
  authority:: 低
  verified:: 2026-09-12

- 来源:: v2rayN 负载均衡复盘
  use_when:: 排查分流/负载均衡问题
  url:: wikilink://v2rayn-balancer-复盘-2026-08-09
  answers:: 负载均衡配置与失效模式
  authority:: 中
  verified:: 2026-09-12

> [!warning] 关联安全项（2026-09-12 审计）
> 本机 `~/.ssh/router_ssh.sh` 含**明文设备口令**，`router_root` 与 `id_rsa` 均为**未加密私钥**，且脚本设了 `StrictHostKeyChecking=no`。
> 路由器凭据应优先轮换——详见 `%USERPROFILE%\dsh-vulnerability-analysis.md` 的 S4 项。
