# 树莓派 API 统一入口架构 v1

> 部署: 2026-06-30

## 链路

```
Claude Code → permafrost(:8788) → proxy(:8787) → model-router(:18888) → ARK
Hermes ──────────────────────────────────────────→ model-router(:18888) → ARK
```

## 改动

| 文件 | 变更 |
|------|------|
| model_router.py | +/v1/messages Anthropic 端点 |
| claude-resilience-proxy.js | HTTP/HTTPS 自适应重写 |
| claude-proxy.service | 新建 systemd 单元 |

## 服务

| 端口 | 服务 | systemd |
|:----:|------|:------:|
| 8788 | permafrost | manual |
| 8787 | proxy | claude-proxy ✅ |
| 18888 | model-router | model-router ✅ |
| 10808 | xray | xray-proxy ✅ |
