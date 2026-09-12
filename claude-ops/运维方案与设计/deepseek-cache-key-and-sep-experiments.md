# DeepSeek 缓存键实验 + 扰动分离模拟 + cache-relay 增强归档（2026-09-12）

> 状态：已完成，实测验证。实验脚本在 `scripts/claude-ops-deployments/cache-relay/experiments/`（`sid-experiment.mjs` / `sep-sim.mjs`，可直接复跑）。
> 相关：[[claude-cache-relay-design]]、[[claude-code-auto-mode-classifier-cache]]、[[claude-flash-primary-analysis]]。

## 一、结论速览

1. **DeepSeek 前缀缓存键 = model + 内容前缀，不含任何 session-id 头**（9/9 轮同体异 sid 全部命中）。
2. **「扰动分离」能提升命中率，但机制是内容历史独立，不是 session-id**（sep-sim 三场景：SEP 同 sid 与异 sid 表现一致）。
3. cache-relay 新增：dump 请求头/首条消息/实际发出 sid 字段；分类器 sid 后缀改写（纯遥测隔离，缓存中立）。
4. 2026-09-12 起全部模型切 `deepseek-flash`（Claude Code + DSH 官方直连），GLM 保留备用、用户可选。

## 二、实验一：缓存键是否含 session-id

**方法**：同 model + 同 body，仅改 `x-claude-code-session-id` 头；另加扰动体（内容首字节不同）/ 无 session 头 / 只带 `x-deepseek-harness-session-id` 三组对照。flash 为主 + pro 对照。

**结果**：

| 实验 | 结果 |
|---|---|
| 同体异 sid（flash 7 轮 + pro 2 轮） | **9/9 全部 HIT**（cache_read 全量），0 miss |
| 扰动体（内容不同） | 2/2 正确 MISS → 命中指标确实反映内容前缀 |
| 无 session 头 / 换 DeepSeek 自有 harness 头 | 照常 HIT → 头存在性与头名均无关 |

**判读**：sid 不进缓存键；「不同 session-id → 缓存隔离」不成立。

**口径提醒**：该 Anthropic 端点的 `input_tokens` 只报 miss 部分；命中率 = `cache_read / (cache_read + input_tokens)`，直接看 `cache_read_input_tokens` 绝对值。

## 三、实验二：扰动分离模拟（三场景，全 flash 同 model）

**场景**：MIXED（单流共享前缀 + 早期共享块逐请求改写，模拟同 session 扰动）/ SEP异sid（两流独立 system 前缀 + 不同 sid）/ SEP同sid（同 SEP 但两流同 sid）。

**结果（主流 cache_read 轨迹）**：

| 场景 | 主流 read | 命中占比 |
|---|---|---|
| MIXED | 恒 896 不增长（历史零复用） | 29%→26%→23% 递减 |
| SEP异sid | 896→1280 随历史增长 | 66%→72% |
| SEP同sid | 1152→1536 增长（顺序靠后命中更满） | 84%→86% |

**判读**：分离把主流命中率抬 ~2.5-3 倍；SEP同sid 与 SEP异sid 一致 ⇒ **收益 100% 来自内容历史独立（两流前缀互不掺合/改写），与 sid 无关**。

**异常点**：SEP异sid 分类器首请求报 read=768，无法用前缀匹配解释（疑似端点计量/写入时序 artifact），不影响主流轨迹结论。

## 四、cache-relay 增强（cache-relay.mjs）

1. **dump 新字段**：`hdr`（请求头名 + 非敏感值，鉴权类脱敏）、`firstMsg`（首条真实消息 160 字符）、`sidSent`（实际发出的 sid，验证改写用）。
2. **分类器 sid 后缀**：`config.classifier.sessionIdSuffix`（当前 `-classifier`）→ 分类器请求转发前把 `x-claude-code-session-id` 改写为 `<原sid>-classifier`。主/分类器在提供方侧拆成两个会话桶（遥测隔离）；依据实验一，**对缓存无益无害**。
3. **分类器识别**：`isClassifierRequest` = 0 tools + system 含 "security monitor" + "autonomous"。
4. **headFp 会跨会话碰撞**（两会话注入同一份 CLAUDE.md 首消息，内容指纹相同）——会话区分只能用 `x-claude-code-session-id` 头，内容指纹不能当会话键。

## 五、全部模型切 deepseek-flash（2026-09-12）

| 位置 | 改动 | 生效时机 |
|---|---|---|
| `~/.claude/settings.json` env | `ANTHROPIC_MODEL` / `DEFAULT_OPUS` / `DEFAULT_SONNET` / `DEFAULT_HAIKU` / `CLAUDE_CODE_SUBAGENT_MODEL` 全 → `deepseek-flash` | 下次启动 Claude Code |
| `~/.dsh/settings.yaml` | `agent-default-model` → `deepseek-official`/`deepseek-flash`；移除 `llm-deepseek`/`web-search-deepseek` 指向 ds2ox 代理(:8899, ox-alpha 已死)的 baseURL → 官方直连 | 热加载，新会话 |
| `~/.dsh/profiles/tui/cordis.patch.yml` | main agent → `deepseek-flash`（TUI bundle 硬编码 pro，子代理继承 parent.options） | 重启 TUI 进程 |
| `~/.cache-relay/config.json` | `classifier.modelMap` 全 → `deepseek-flash` | 每请求热读，立即 |

- `deepseek-flash` 模型 id 已实测 200（Anthropic 端点）。
- **GLM 备用（用户可选）**：DSH 切回 = `agent-default-model` 改回 `{provider: ox-openrouter, model: z-ai/glm-5.3-flash}`（llm-pi-ai 段保留未动）；Claude 侧 = relay `fallback`（400 内容审核 → GLM）不变。
- **回滚**：4 份备份 `*.pre-flash-20260912`（settings.json / settings.yaml / cordis.patch.yml / config.json）。切回 pro = settings.json 改回 `deepseek-v4-pro[1m]`。
- 遗留可清理项：`~/.dsh/ds2ox-proxy.mjs`（:8899）已无流量引用，Startup VBS 自启可停（未处理，待用户确认）。
