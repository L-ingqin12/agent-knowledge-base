---
title: DeepSeek 缓存键与扰动分离实验
aliases: []
tags: [ai/ops]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# DeepSeek 缓存键实验 + 扰动分离模拟 + cache-relay 增强归档（2026-09-12）

> 状态：已完成，实测验证。实验脚本在 `scripts/claude-ops-deployments/cache-relay/experiments/`（`sid-experiment.mjs` / `sep-sim.mjs`，可直接复跑）。
> 相关：[[claude-cache-relay-design]]、[[claude-code-auto-mode-classifier-cache]]、[[claude-flash-primary-analysis]]。

## 一、结论速览

1. **DeepSeek 前缀缓存键 = model + 内容前缀，不含任何 session-id 头**（9/9 轮同体异 sid 全部命中）。
   > [!warning] 更正（2026-09-13）：**厂商从未定义缓存键的组成**——「键 = model + 内容前缀」是把本机 n=9 观测外推成了厂商语义（原表述如此）。正确口径：**在本机观测口径下，sid 头变化不影响该 Anthropic 兼容端点的前缀命中（9/9）**。厂商 Context Caching 页全文只讲「cache prefix unit 完整匹配」「best-effort、不保证 100% 命中」「构建需数秒、闲置数小时到数天自动清除」，**未提任何请求头是否参与**，故不可推广；Anthropic 兼容页的 Header 表也只列 `anthropic-beta` / `anthropic-version` / `x-api-key`。[来源](https://api-docs.deepseek.com/guides/kv_cache)、[来源](https://api-docs.deepseek.com/guides/anthropic_api)
2. **「扰动分离」能提升命中率，但机制是内容历史独立，不是 session-id**（sep-sim 三场景：SEP 同 sid 与异 sid 表现一致）。
3. cache-relay 新增：dump 请求头/首条消息/实际发出 sid 字段；分类器 sid 后缀改写（纯遥测隔离，缓存中立）。
4. 2026-09-12 起全部模型切 `deepseek-flash`（Claude Code + DSH 官方直连），GLM 保留备用、用户可选。
   > [!warning] 更正（2026-09-13）：`~/.dsh/settings.yaml` 注释里登记的**两个免费档已死**——`z-ai/glm-5.2:free`（记为 GLM 5.2 free primary）与 `minimax/minimax-m3:free`（记为 backup）实测 endpoints 均为 `[]`，且都不在 OpenRouter `/api/v1/models` 的 445 条列表中（该列表含 19 条 `:free`）。**但方向不可反转**：GLM 备用路径本身仍有效——`z-ai/glm-5.3-flash` 在架（endpoints 实测 26 个）。结论应写成「settings.yaml 的免费档 id 需换掉，GLM 备用路径（`glm-5.3-flash`）可用」。[来源](https://openrouter.ai/api/v1/models/z-ai/glm-5.2:free/endpoints)、[来源](https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints)

## 二、实验一：缓存键是否含 session-id

**方法**：同 model + 同 body，仅改 `x-claude-code-session-id` 头；另加扰动体（内容首字节不同）/ 无 session 头 / 只带 `x-deepseek-harness-session-id` 三组对照。flash 为主 + pro 对照。

**结果**：

| 实验 | 结果 |
|---|---|
| 同体异 sid（flash 7 轮 + pro 2 轮） | **9/9 全部 HIT**（cache_read 全量），0 miss |
| 扰动体（内容不同） | 2/2 正确 MISS → 命中指标确实反映内容前缀 |
| 无 session 头 / 换 DeepSeek 自有 harness 头 | 照常 HIT → 头存在性与头名均无关 |

**判读**：sid 不进缓存键；「不同 session-id → 缓存隔离」不成立。

> [!warning] 更正（2026-09-13）：「sid 不进缓存键」应限定为**本机观测口径**（n=9 = flash 7 轮 + pro 2 轮，单一 Anthropic 兼容端点）；厂商文档未定义缓存键组成（原表述把观测外推为厂商语义）。可保留的强结论是**反证方向**：「不同 session-id **不产生**缓存隔离」——这是实测否证，成立。

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

## 三·附：厂商侧缓存时序与计价口径（2026-09-13 补）

原文（含三节实验与结论速览）未提缓存构建/清除时序与闲时折扣，而这三条直接决定「扰动分离」实验结论的稳定性：

| 厂商明文 | 原文 | 对本文的影响 |
|---|---|---|
| 缓存构建需时间、闲时自动清除 | 「Cache construction takes seconds. Once the cache is no longer in use, it will be automatically cleared, usually within a few hours to a few days.」 | 连续改写早期共享块（MIXED 场景）会让缓存**来不及建立**——这是「恒 896 不增长」的**替代解释**，不能只归因于「历史零复用」 |
| 命中是尽力而为 | 「The cache system works on a best-effort basis and does not guarantee a 100% cache hit rate.」 | 单次 MISS 不足以证伪前缀假设；跨天复跑不可比（缓存可能已被 idle 清除） |
| 峰谷计价 | 「Off-peak rates are half of the peak rates. Peak hours are 01:00 - 04:00 and 06:00 - 10:00 UTC, Monday through Friday」 | 用 cache_read token 做成本比较时必须注明采样时段 |

> 来源：[DeepSeek Context Caching](https://api-docs.deepseek.com/guides/kv_cache)、[Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing)。§三 的「收益来自内容历史独立」仍成立（SEP 同/异 sid 一致是对照实验），但 MIXED 读数需加限定：可能是「前缀被改写」+「缓存来不及建立」两者叠加。

## 四、cache-relay 增强（cache-relay.mjs）

1. **dump 新字段**：`hdr`（请求头名 + 非敏感值，鉴权类脱敏）、`firstMsg`（首条真实消息 160 字符）、`sidSent`（实际发出的 sid，验证改写用）。
2. **分类器 sid 后缀**：`config.classifier.sessionIdSuffix`（当前 `-classifier`）→ 分类器请求转发前把 `x-claude-code-session-id` 改写为 `<原sid>-classifier`。主/分类器在提供方侧拆成两个会话桶（遥测隔离）；依据实验一，**对缓存无益无害**。
3. **分类器识别**：`isClassifierRequest` = 0 tools + system 含 "security monitor" + "autonomous"。
4. **headFp 会跨会话碰撞**（两会话注入同一份 CLAUDE.md 首消息，内容指纹相同）——会话区分只能用 `x-claude-code-session-id` 头，内容指纹不能当会话键。

## 四·附：可复跑手册与验收断言（2026-09-13 补）

原文只给脚本目录（`scripts/claude-ops-deployments/cache-relay/experiments/`）与字段名，换个人无法复跑。补齐：

1. **前置：确认请求真的经 relay**。本机 `~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL` 实取为 `https://api.deepseek.com/anthropic`（官方直连），只有 `~/.claude/settings.local.json` 指向 `http://127.0.0.1:8790`——两处并存且取值相反。**若生效值是直连，relay 的 dump 字段根本不会产生，实验等于没做**。自检：`node cache-relay.mjs deploy` 确认 :8790 在路径上，实验后 dump 里必须出现 `sidSent`。
2. **固定变量与冷却**：同 model、同 body，一次只改一个自变量（sid 头 / 内容首字节）；每组之间冷却到缓存构建完成（秒级，见 §三·附），整个窗口内不跨 idle 清除。
3. **验收断言**：① 响应中 `cache_read_input_tokens > 0`（该 Anthropic 兼容端点的口径，见 §二「口径提醒」）；② miss 部分稳定；③ dump 的 `sidSent` 与实际发出的头一致。
4. **结论分层**（原文把两条混在一起）：
   - 「内容历史独立」——已被 SEP 同/异 sid 一致**证实**，可作结论；
   - 「缓存键不含 sid」——无厂商文档支持，只能作**本机观测口径**（n=9），不可写成厂商语义。

## 五、全部模型切 deepseek-flash（2026-09-12）

| 位置 | 改动 | 生效时机 |
|---|---|---|
| `~/.claude/settings.json` env | `ANTHROPIC_MODEL` / `DEFAULT_OPUS` / `DEFAULT_SONNET` / `DEFAULT_HAIKU` / `CLAUDE_CODE_SUBAGENT_MODEL` 全 → `deepseek-flash`（⚠️ **2026-09-13 订正：正确值应为 `deepseek-flash[1m]`。当时丢了 `[1m]`，见下**） | 下次启动 Claude Code |
| `~/.dsh/settings.yaml` | `agent-default-model` → `deepseek-official`/`deepseek-flash`；移除 `llm-deepseek`/`web-search-deepseek` 指向 ds2ox 代理(:8899, ox-alpha 已死)的 baseURL → 官方直连 | 热加载，新会话 |
| `~/.dsh/profiles/tui/cordis.patch.yml` | main agent → `deepseek-flash`（TUI bundle 硬编码 pro，子代理继承 parent.options） | 重启 TUI 进程 |
| `~/.cache-relay/config.json` | `classifier.modelMap` 全 → `deepseek-flash` | 每请求热读，立即 |

- ⚠️ **2026-09-13 订正：本行原写「`deepseek-flash` 模型 id 已实测 200」——「端点返回 200」只证明连通，不证明能力保留，是个错结论**（同 [[CORRECTIONS]] C-009「把服务存在外推为效果出现」族）。
  **真实事实：改名时丢了 `[1m]` 后缀** ⇒ Claude Code 认不出该 ID、上下文窗口**静默**从 **1M 掉到 200K**
  ⇒ auto-compact 阈值由 ~784K 降到 ~144K ⇒ **compact 频率约 5.4 倍**。
  **上游能力没变** —— DeepSeek 官方 Models & Pricing 页对 `deepseek-flash` 与 `deepseek-v4-pro` **都标 1M 上下文 / 384K 最大输出**，差异**完全来自客户端那个字符串**。
  详见 [[claude-context-window-and-model-id]] 与 [[2026-09-12-flash-migration-context-shrink-postmortem]]。
- **GLM 备用（用户可选）**：DSH 切回 = `agent-default-model` 改回 `{provider: ox-openrouter, model: z-ai/glm-5.3-flash}`（llm-pi-ai 段保留未动）；Claude 侧 = relay `fallback`（400 内容审核 → GLM）不变。
  > [!warning] 更正（2026-09-13）：上面这条切换命令（指向 `z-ai/glm-5.3-flash`）**仍然有效**——该模型在架、endpoints 实测 26 个。但 `~/.dsh/settings.yaml` 注释里登记的两个免费档 `z-ai/glm-5.2:free`（GLM 5.2 free primary）与 `minimax/minimax-m3:free`（backup）**已下线**（endpoints 均为 `[]`、不在 445 条模型列表内），需换掉登记项。另注：本机 `~/.cache-relay/config.json` 的 `fallback.modelMap` 实测为 `{"deepseek-v4-pro[1m]", "deepseek-v4-flash", "*"} → z-ai/glm-5.3-flash`，与 DSH 侧「切回 GLM」**不是同一条路径**（relay 兜底 vs DSH 默认模型），排查时别混。[来源](https://openrouter.ai/api/v1/models)、[来源](https://openrouter.ai/api/v1/models/minimax/minimax-m3:free/endpoints)
- **回滚**：4 份备份 `*.pre-flash-20260912`（settings.json / settings.yaml / cordis.patch.yml / config.json）。切回 pro = settings.json 改回 `deepseek-v4-pro[1m]`。
- ~~遗留可清理项：`~/.dsh/ds2ox-proxy.mjs`（:8899）已无流量引用，Startup VBS 自启可停（未处理，待用户确认）。~~
  2026-09-12 复核更新：已完成**安全复核与脱敏归档**，退役判定成立（`settings.yaml` 无 8899 引用、进程未运行、密钥未进入 git 历史）。**仍有残留复活路径**（两份配置备份 `settings.yaml.pre-upgrade` / `.pre-flash-20260912` 仍指向 8899）。详见 [[ds2ox-proxy-retirement]]。原始条目所述「Startup VBS 自启」经核为**同名误判**——启动项指向的是 alist 的 `alist.vbs`，非本代理；本代理为手工前台运行，无自启条目。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 结论速览①与 §二判读把「缓存键 = model + 内容前缀」写成厂商语义 | 保留原句 + 就地更正：厂商 Context Caching 页**未定义缓存键组成、未提任何请求头是否参与**；改写为「本机观测口径下 sid 头不影响该 Anthropic 兼容端点的前缀命中（9/9）」，保留「不同 session-id 不产生缓存隔离」这一实测反证 |
| 纠错 | 结论速览④与 §五把 GLM 记为「保留备用」，未察 `settings.yaml` 登记的两个免费档已下线 | 保留原句 + 更正：`z-ai/glm-5.2:free` / `minimax/minimax-m3:free` endpoints 均为 `[]`、不在 445 条模型列表内；**但备用路径本身可用**（`z-ai/glm-5.3-flash` 在架、26 个端点），避免写成「GLM 备用失效」的反向错误。并写明 relay `fallback.modelMap` 与 DSH 切回是两条路径 |
| 补疏漏 | 全文未提厂商侧缓存构建/清除时序与闲时折扣，而这影响实验可复现性 | 新增「三·附」：缓存构建需数秒且闲置数小时到数天自动清除、best-effort 不保证 100% 命中、峰谷半价（周一至周五 01:00–04:00 与 06:00–10:00 UTC）；并给出 MIXED 场景「恒 896」的替代解释（缓存来不及建立） |
| 加厚 | §二方法/§四增强只有字段名罗列，无一条可复制命令与验收判据 | 新增「四·附」可复跑手册：前置 relay 生效自检（settings.json 直连 vs settings.local.json :8790）、固定变量与冷却、三条响应/dump 断言、结论分层（已证实 vs 仅本机观测） |

依据：[DeepSeek Context Caching](https://api-docs.deepseek.com/guides/kv_cache)、[DeepSeek Anthropic 兼容页](https://api-docs.deepseek.com/guides/anthropic_api)、[Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing)、[OpenRouter models](https://openrouter.ai/api/v1/models)。方法论回链：[[AGENTS]]。
