# Claude Code 接入排查复盘

> 耗时: 2026-06-30 ~ 2026-07-02 | 修复次数: 9 次

---

## 时间线

| 时间 | 发现 | 修复 | 耗时 |
|------|------|------|:--:|
| 06-30 22:00 | Claude 连接 api.anthropic.com 直连 401 | 设 ANTHROPIC_BASE_URL + key | 30min |
| 06-30 23:00 | Proxy 路径双拼 `/v1/v1/messages` | 修正 opts.path | 10min |
| 07-01 00:00 | 模型列表仅 router-v3，Claude 不认 | 返回真实 model ID | 10min |
| 07-01 00:30 | 双 ARK key 不同 endpoint | 模型路由器按协议分流 | 20min |
| 07-01 01:00 | Permafrost 自启动无 UPSTREAM | 补 .bashrc 环境变量 | 10min |
| 07-01 07:20 | `?beta=true` query string → 404 | strip 查询参数 | 30min |
| 07-01 07:34 | xray 断连 → 500 | 重启 xray | 10min |
| 07-02 07:18 | list content → classify_difficulty 崩溃 | 增加 `_get_content()` 处理 | 10min |
| 07-02 07:20 | ✅ 200 | | |

---

## 根因 — 为什么排查了这么久

### 1. 没有一次性枚举差异

Claude 的真实请求 vs 测试请求存在 3 个差异，但每次只发现一个：

| 差异 | Claude 实际发送 | curl 测试发送 | 发现延迟 |
|------|----------------|-------------|:--:|
| 查询参数 | `/v1/messages?beta=true` | `/v1/messages` | 3 轮修复后才发现 |
| content 格式 | `[{"type":"text","text":"..."}]` | `"hi"` | 最后一轮才发现 |
| 模型列表 | 需要真实 model ID | 不需要验证 | 第 3 轮才发现 |

**教训**: 接入新客户端时，应第一时间**捕获真实请求的完整 body 和 headers**，与测试 payload 做 diff。

### 2. 错误日志缺失

模型路由器的异常被 `except Exception as e` 吞掉了，只返回 `{"error": str(e)}`，不记录 traceback。500 错误原因完全不可见。

```python
# 修复前
except Exception as e:
    self.send_response(500)
    
# 修复后
except Exception as e:
    sys.stderr.write(f"[ROUTER-500] {traceback.format_exc()}\n")
```

**教训**: 所有 HTTP 500 必须记录完整 traceback。

### 3. 逐层排查而非端到端对比

每次只查一个组件 (proxy、router、xray)，没有一次性做端到端对比：

```
应该: Claude 请求 ↔ curl 模拟 → 对比响应差异 → 定位所有差异 → 一次性修复
实际: Claude 报错 → 查 proxy → 修 → Claude 报错 → 查 router → 修 → ... (循环 9 次)
```

### 4. 测试覆盖不足

curl 测试只覆盖了简单 payload:
```bash
curl -d '{"messages":[{"role":"user","content":"hi"}]}'  # 只有 str content
```

Claude 真实请求:
```bash
curl -d '{"messages":[{"role":"user","content":[{"type":"text","text":"..."}]}],"betas":[...]}'  # list content + 额外字段
```

---

## 最终架构

```
Claude Code
  ANTHROPIC_BASE_URL=http://127.0.0.1:8788
  ↓ list content → Anthropic 格式
permafrost (:8788)
  PERMAFROST_UPSTREAM=http://127.0.0.1:8787
  ↓ 前缀锚定
proxy (:8787, systemd)
  ↓ 透传, bug修复: path=opts.path (非 pathname+path)
model-router (:18888)
  ↓ strip ?query, handle list content
  ↓ Anthropic→/api/coding+v1/messages+ark-<REDACTED>
  ↓ OpenAI→/api/coding/v3+chat/completions+ark-<REDACTED>
ARK API
```

## 后续防护

1. 模型路由器加 `_get_content()` 处理 list content (已完成)
2. 所有 500 加 traceback 日志 (已完成)
3. Proxy 不拼 pathname (已完成)
4. 接入新客户端前先抓包对比
