---
title: API Key 泄漏事故复盘
aliases: [API Key 泄漏复盘, Hermes Key 泄漏事故, 飞书会话明文曝光]
tags: [ai/ops, incident]
created: 2026-09-12
updated: 2026-09-12
status: draft
---

# API Key 泄漏事故复盘 (WIP)

See also: [[Claude-Ops-KB-Home]] · [[final-postmortem]] · [[pi-audit-plan]] · [[CORRECTIONS]]

> 日期: 2026-06-29  
> 状态: 阶段性归档, `sk-<REDACTED>` 路径待补充

---

## 一、事件 A: 模型路由器错误使用手机 ARK Key — 已修复

### 结论
`ark-<REDACTED>...` 是正常为树莓派购买的 ARK key (无问题)。`ark-<REDACTED>...` 是手机 key, 被模型路由器错误使用。

### 发生时间
2026-06-16 ~ 2026-06-29 01:09

### 泄漏链路

```
model_router.py PID 967 (启动于 6月16日, systemd 单元无 --api-key 参数)
    │
    ├── main() 第 240-248 行: 无 --api-key → 回退到 config["model"]["api_key"]
    │
    ├── config.yaml → api_key: ark-<REDACTED> (手机ARK)
    │                     ↑ 错误的 key, 应为 ark-<REDACTED>... (树莓派专用)
    │
    └── 每次 hermes API 调用 → :18888 → ARK API → 手机账户计费
```

### 证据

| # | 证据 | 来源 |
|---|------|------|
| 1 | 6月28日 252 次 API 调用, base_url 全部 `http://127.0.0.1:18888/v1` | `/home/pi/.hermes/logs/agent.log` |
| 2 | 峰值: 01:00(81次) 23:00(78次) 19:00(47次) 00:00(37次) | 同上 |
| 3 | 6月24日配置备份含手机 key 3 处 | `config.yaml.bak.20260624` |
| 4 | `model_router.py:240-248` 无 `--api-key` 时回退到 config | 源码 |
| 5 | model-router systemd 单元直到 6月29日修复前无 `--api-key` 参数 | systemd journal |

### 修复
2026-06-29 01:09 更新 `model-router.service`, 显式指定 `--api-key ark-<REDACTED>...`

---

## 二、事件 B: 飞书会话 Key 明文曝光 (已证实)

### 触发操作

用户通过飞书发送 API Key, 要求 Hermes Agent 写入配置文件。

### 精确时间线

```
2026-06-23 22:29:37  → "API Key: sk-<REDACTED>"
2026-06-24 00:06:16  → "API Key:sk-<REDACTED> 请写入bashrc的环境变量，这样方便你"
                       → Gateway 收到 SIGTERM, 处理中断
2026-06-24 00:51:27  → "API Key:sk-<REDACTED> 请写入bashrc的环境变量，这样方便你"
                       → 用户点击 Feishu 审批按钮 → 39.8s 返回
2026-06-24 07:03:29  → "API Key:sk-<REDACTED> 作为工作流的环境变量值写入配置文件内，需"
                       → Agent 尝试写入 → 被 patch/terminal 保护拒绝
                       00:07:04:09 → patch 拒绝写入 config.yaml
                       00:07:04:19 → hermes config 命令失败
                       00:07:04:46 → read_file 拒绝读取 .env
2026-06-24 07:05:54  → "应该是AGNES_API_KEY吧"
2026-06-25 08:26:11  → "当前使用的API Key是什么"
2026-06-25 08:41:08  → "API Key:sk-<REDACTED>"
```

### 泄漏机制

```
飞书消息 → Hermes 创建会话
  session.title  = 消息首段
  session.preview = 消息内容 (含完整 key 明文)
  messages → state.db 持久化
  hermes sessions list → 终端显示完整 key
```

### 受影响会话 (4个, 已清除)

| 会话 ID | 泄漏 Key | 状态 |
|----------|---------|:--:|
| `20260624_070329_fd1af830` | sk-<REDACTED>... | 已删除 |
| `20260624_115108_f29e1d` | sk-<REDACTED>... | 已删除 |
| `20260624_234635_821627` | sk-<REDACTED>... | 已删除 |
| `20260625_025611_7f3e6e` | sk-<REDACTED>... | 已删除 |

### 说明
- Gateway 日志自行脱敏 (显示 `sk-<REDACTED>`)
- 会话预览未脱敏 (显示完整 key → 这是 hermes 的 bug)
- `sk-<REDACTED>` 未被用于 API 消费
- 该 key 对应用户已自行撤销

---

## 三、事件 C: `sk-<REDACTED>` DeepSeek Key 异常消耗 (核心问题, 待查)

### 状态: 🔴 这是真正的异常 — ARK 两条 key 都有合理解释, 唯独 sk-<REDACTED> 不该被消费

### 已知事实
- key 存在于 `/home/pi/.claude/settings.local.json` 的 3 处 curl 命令中 (Claude Code 配置)
- key 已被用户销毁
- 用户报告消耗约 150 元 / 5 亿+ token, **集中在 6月28日一天**
- **飞书对话记录中未搜到该 key** — 不是通过飞书泄漏
- **不在 hermes config 中** — 不是通过 hermes 消费

### 待查路径
1. Claude Code permafrost 代理链 (`:8788 → :8787 → API`) 是否使用了该 key
2. 6月28日 permafrost 缓存命中率 — 如果缓存未命中则全量 token 计费
3. Claude Code 当日有什么任务在运行

### 待补充
- [ ] permafrost 缓存命中率日志
- [ ] Claude Code 6月28日 API 调用统计
- [ ] 精确日消耗分布

---

## 四、已完成修复

| 措施 | 日期 | 状态 |
|------|------|:--:|
| model-router 显式 `--api-key` | 06-29 | ✅ |
| 手机 ARK key 从 config 移除 | 06-29 | ✅ |
| 4 个泄漏会话删除 | 06-29 | ✅ |
| state.db 中 15 条 key 消息清除 | 06-29 | ✅ |
| model-router 不再从 config 回退读 key | 06-29 | ✅ |
| hermes 会话预览脱敏 | — | ❌ (需上游修复) |

---

## 五、关键教训

1. **`model_router.main()` 的回退机制是根因**: 无 `--api-key` 时静默从 config 读取, 导致 key 替换不可见
2. **systemd 单元应始终显式传参**: 不应依赖 config 回退
3. **hermes 会话预览无脱敏**: `sk-`/`ark-` 模式应自动替换
4. **飞书不是发送 key 的安全通道**: 应通过 SSH 直接编辑配置文件
