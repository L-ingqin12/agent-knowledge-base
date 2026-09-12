---
title: ds2ox-proxy 目录说明（归档）
aliases: [ds2ox-proxy README, 模型路由代理归档说明]
tags: [ai/ops, security]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# ds2ox-proxy — 已退役归档

> [!danger] 本目录内容不可直接部署
> 这是**知识归档**，不是可运行资产。归档文件中的凭据已外置为环境变量，且脚本含三处已知设计缺陷。
> 完整说明见 [[ds2ox-proxy-retirement]]。

## 目录内容

| 文件 | 说明 |
|---|---|
| `ds2ox-proxy.mjs` | 脱敏归档正文（原 `~/.dsh/ds2ox-proxy.mjs`）。密钥/端口/模型均改为环境变量 |
| `README.md` | 本文件 |

## 归档信息

| 项 | 值 |
|---|---|
| 原始位置 | `~/.dsh/ds2ox-proxy.mjs` |
| 原始用途 | 把 DSH `deepseek-official` 流量改写路由到 OpenRouter 免费模型 |
| 监听 | `127.0.0.1:8899` |
| 退役判定 | 死代码（`settings.yaml` 已无 8899 引用，进程未运行） |
| 最后活跃 | 2026-08-26 14:43 |
| 归档日期 | 2026-09-12 |
| 脱敏方式 | 密钥外置为 `DS2OX_PROXY_KEY`（参照 cache-relay 的「密钥不落地」范式） |

## 已知缺陷摘要

| # | 缺陷 | 影响 |
|---|---|---|
| D1 | 无入站鉴权 | 本机任意进程可借用密钥 / 透传上游 |
| D2 | 无 Host 头校验 | DNS 重绑定、跨站请求面 |
| D3 | 抢占即劫持 | 监听 8899 即可替换模型输出、窃取对话（无需触碰文件） |

详见 [[ds2ox-proxy-retirement#三、三处设计缺陷（重新启用前必须修复）]]。

## 相关

- [[ds2ox-proxy-retirement]] —— 安全复核与退役归档（主文档）
- [[deepseek-cache-key-and-sep-experiments]] —— 该代理的原始拆解记录
- [[claude-cache-relay-design]] —— 现役替代方案
