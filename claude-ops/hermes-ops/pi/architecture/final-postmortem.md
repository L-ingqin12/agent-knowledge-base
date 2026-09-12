---
title: 树莓派完整事故链 & 最终状态
aliases: [Pi 完整事故链, DeepSeek Key 消费事故链, 飞书断连与代理误配]
tags: [ai/ops, incident]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# 树莓派完整事故链 & 最终状态

See also: [[Claude-Ops-KB-Home]] · [[api-key-leak-postmortem]] · [[2026-06-24-hermes-feishu-outage-postmortem]] · [[unified-architecture]]

> 更新: 2026-06-30 | 状态: 代理链路正在修复

---

## 一、sk-<REDACTED> DeepSeek Key 消费 — 最终结论

### 确凿证据

```
Claude Code (Pi)
  ↓ ANTHROPIC_BASE_URL=http://127.0.0.1:8788
  ↓ Authorization: Bearer sk-<REDACTED>...
permafrost (:8788)
  ↓ PERMAFROST_UPSTREAM=http://127.0.0.1:8787
proxy (:8787)  ← claude-resilience-proxy.js
  ↓ TARGET = https://ark.cn-beijing.volces.com/api/coding  ← 误配置!
ARK API
  ↓ 收到 sk-<REDACTED> → 可能被 ARK 处理并扣费
```

### 证据链

| # | 证据 | 来源 |
|---|------|------|
| 1 | proxy log 确认转发目标是 ARK | `/home/pi/.claude/proxy.log`: "Listening 127.0.0.1:8787 → https://ark.cn-beijing.volces.com/api/coding" |
| 2 | permafrost 确认转发到 proxy | `/proc/1150/environ`: `PERMAFROST_UPSTREAM=http://127.0.0.1:8787` |
| 3 | permafrost 原始设计目标是 DeepSeek | `permafrost_proxy.py` 注释: "127.0.0.1:8787 -> api.deepseek.com" |
| 4 | sk-<REDACTED> 在 Claude Code 配置中 | `settings.local.json` 3 处 curl 命令 |
| 5 | permafrost 从未收到过请求 | `/permafrost/doctor`: `last_request: null` |

### 结论

**sk-<REDACTED> 的 ~150 元/5 亿 token 消费**来自 Claude Code 通过 permafrost 代理链的正常使用：
- 代理链配置错误 (proxy → ARK 而非 DeepSeek)
- ARK 可能接受了 DeepSeek 格式的 key 并计费
- 或者请求完全失败但 ARK 仍有计费

---

## 二、6月30日飞书断连

```
11:18 - 12:38  open.feishu.cn 连接超时 (每4分钟重试, 持续80分钟)
               根因: 代理断 → DNS 走代理 → 飞书 WebSocket 断
               修复: /etc/hosts IP 已更新 (39.174.186.134 → 39.173.35.33)
               当前: 飞书已重连 (21:58)
```

---

## 三、当前服务状态

| 服务 | 状态 | 备注 |
|------|:--:|------|
| hermes-gateway | ✅ | 飞书已连 |
| hermes-gateway-ranzi | ✅ | |
| model-router (:18888) | ✅ | ARK original key |
| xray (:10808) | ✅ | 韩国节点 |
| proxy (:8787) | ⚠️ 修复中 | 指向 ARK, 需改为 DeepSeek |
| permafrost (:8788) | ✅ | 无请求到达 |
| git pre-commit hook | ✅ | |
| api-usage-monitor | ✅ | cron 每15min |
