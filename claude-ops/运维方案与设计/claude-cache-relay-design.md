---
title: 通用多源缓存对齐中继设计（cache-relay）
aliases: [通用缓存中继, cache alignment relay]
tags: [ai/ops, ai/agent]
created: 2026-09-06
updated: 2026-09-06
status: review
---

# 通用多源缓存对齐中继设计（cache-relay）

See also: [[Claude-Ops-KB-Home]] · [[claude-cache-optimization]] · [[tianshu-cache-aim-plan]] · [[PERMAFROST_MODIFICATIONS]]

> 背景：permafrost 的 `align_request()` 是为「Claude Code → DeepSeek Anthropic 端点」单一来源定制的（去 cache_control、工具排序、currentDate 稳定化、env 冻结）。本方案把它**泛化为多源缓存对齐中继**：自动识别来源 provider 类型，选对应的缓存策略，一个中继服务所有上游。要求：尽量通用、自动判源、软回滚优先、使用说明保留。

---

## 一、核心思想：按来源分派缓存策略

不同 provider 的缓存机制**本质不同**，不能一刀切：

| Provider | 缓存类型 | 命中关键 | 需要的对齐动作 |
|---|---|---|---|
| **DeepSeek** | 隐式 exact-prefix（byte 0 起逐字节） | 前缀字节稳定 | 去 cache_control、工具按 name 排序、currentDate 稳定化、env 冻结+增量 |
| **Anthropic/Claude** | 显式 `cache_control` 断点 | 断点位置稳定、稳定内容在前 | **保留**断点、把稳定块放前、易变块放断点后（不 strip） |
| **GLM/Zhipu** | 隐式前缀（deepseek-native） | 前缀字节稳定 | 同 DeepSeek：排序 + 稳定化 + 冻结 |
| **OpenRouter** | 透传（缓存由最终上游模型决定） | 取决于下游 | 仅工具排序 + 确定性 JSON（最小干预） |
| **通用 OpenAI 兼容** | 未知/无 | 保守 | 工具排序 + 确定性序列化（安全默认） |

**判源依据**：`baseUrl` host + `model` 名 + `protocol`（OpenAI `chat/completions` vs Anthropic `messages`）。

## 二、判源与分派（detect → dispatch）

```
agent 请求 ──▶ cache-relay ──▶ detectProvider(baseUrl, model, protocol)
                  │
                  ├─ deepseek   → alignDeepSeek()   (strip cache_control + sort + stabilize + freeze)
                  ├─ anthropic  → alignAnthropic()  (keep breakpoints, 稳定前置校验)
                  ├─ glm        → alignDeepSeek()   (同 DeepSeek)
                  ├─ openrouter → alignPassthrough()(sort + canonical JSON)
                  └─ default    → alignGeneric()    (sort + canonical JSON)
```

判源规则（可 env 覆盖）：

```
host 含 deepseek.com            → deepseek
host 含 anthropic.com 或 protocol=anthropic → anthropic
host 含 bigmodel.cn / zhipu     → glm
host 含 openrouter.ai           → openrouter
host 含 minimaxi.com            → deepseek（隐式前缀，同策略）
其余                             → generic
```

## 三、对齐动作（复用 permafrost 算法，按源裁剪）

| 动作 | deepseek/glm | anthropic | openrouter/generic |
|---|---|---|---|
| strip cache_control | ✅（DeepSeek 不识别，位置漂移破坏前缀） | ❌（显式断点，保留） | — |
| 工具按 name 排序 | ✅ | ✅（确定性） | ✅ |
| currentDate 稳定化 | ✅（→ 2000-01-01） | ✅（system 别插日期） | ✅ |
| env/易变块冻结+增量 | ✅（freeze_volatile） | ✅（易变块放断点后） | 可选 |
| 规范 JSON 序列化 | ✅ | ✅ | ✅ |

## 四、架构与部署

- **形态**：Node.js HTTP 中继（跨平台、无编译依赖），`cache-relay.mjs`。
- **链路**：agent → cache-relay(:8790) → 上游（baseUrl 由 agent 通过 `RELAY_UPSTREAM` 或请求头指定）。
- **多源并发**：单进程监听，按请求独立判源分派，互不污染。
- **密钥**：中继**不落地任何密钥**，透传 `Authorization`/`api-key` 头；上游地址用 env `RELAY_DEFAULT_UPSTREAM`，不硬编码。

## 五、逃生与回滚通道（软回滚优先，禁止硬删除）

| 级别      | 类型  | 操作                                                    | 场景                        |
| ------- | --- | ----------------------------------------------------- | ------------------------- |
| E0 停中继  | 逃生  | `node cache-relay.mjs stop`（读 pid kill）               | 中继异常，立即止血                 |
| S0 软回滚  | 软回滚 | `touch ~/.cache-relay/.disabled` 或 `RELAY_DISABLED=1` | 不需要缓存对齐时禁用（**不删脚本**，随时恢复） |
| P0 单源降级 | 逃生  | `RELAY_FORCE_PROVIDER=passthrough`（全部直通，不做对齐）         | 某 provider 对齐逻辑出问题，一键全直通  |
| R0 硬回滚  | 硬回滚 | `git revert <commit>`（**不 `rm`**）                     | 正式撤销部署                    |

> **软回滚原则**：停用/降级一律走 `.disabled`/env 开关，**绝不删脚本**；`RELAY_FORCE_PROVIDER=passthrough` 是「全直通」逃生阀，保证对齐层挂了也能透传。

## 六、使用说明

```bash
node cache-relay.mjs start        # 前台启动（:8790，日志 stdout）
node cache-relay.mjs daemon       # 后台（写 pid）
node cache-relay.mjs stop         # 停（读 pid）
node cache-relay.mjs doctor       # 判源自测：给定 baseUrl/model 打印判定结果
```

环境变量：`RELAY_PORT`（默认 8790）· `RELAY_DEFAULT_UPSTREAM`（默认透传请求自带的目标）· `RELAY_FORCE_PROVIDER`（可选：强制某策略，`passthrough`=全直通逃生）· `RELAY_DISABLED=1`（软回滚开关）。

### 6.1 健康检查与「认身份再停」（2026-09-12 修）

中继内建 `GET /__relay__/health`（**自己应答，绝不转发上游**，且在软回滚判断之前——已 `.disabled` 但仍运行的中继也要能被停掉），返回 `{relay, pid, port, uptimeSec}`。

**为什么需要它**：原先 `stop` 是照 `relay.pid` 裸 kill。两个坑——① 用 `start` 前台启动时根本不写 pid 文件，文件一直是上一轮的过期值；② pid 会被系统复用，裸 kill 有**误杀无关进程**的风险（本机就出现过 pid 文件里的 28160 已被 conhost 复用）。现在改成：

- `stop` / `undeploy`：先探健康检查，**只 kill「确证是本中继」的那个 pid**；健康检查不通时只清理过期 pid 文件并明确告知，绝不乱杀。
- `start`：启动时用 `claimPidFile()` 登记自己的 pid 并在退出时清理；端口已有本中继在听则拒绝重复启动（否则 bind 失败前会先把 pid 文件写坏）。
- `doctor`：除判源外，追加打印真实运行态（以健康检查为准），并在 pid 文件与实况不符时给出提示。

集成测试第 ⑨ 项专测这条：故意把「旁观者进程」的 pid 写进 `relay.pid`，断言 `stop` 仍能认出真中继并停掉、而**旁观者毫发无伤**，且重复 `stop` 幂等。

## 七、测试计划（跑通再部署）

| 项 | 命令 | 通过标准 |
|---|---|---|
| 判源自测 | `node cache-relay.mjs doctor`（deepseek/anthropic/glm/openrouter/generic 各一例） | 判定正确 |
| 对齐单测 | 对每种 provider 发一个带 cache_control/乱序工具/currentDate 的样例请求 | deepseek 剥离+排序+稳定；anthropic 保留断点；generic 排序 |
| 透传逃生 | `RELAY_FORCE_PROVIDER=passthrough` 发请求 | 字节不变直通 |
| 软回滚 | `touch .disabled` 后 start | 静默退出 |

## 八、应用的本库经验教训

1. **先仓库后部署**（本 doc 先落盘）。
2. **改配置不动代码**（判源/开关全走 env，不写死）。
3. **如果没坏就别修**（对齐动作尽量保守，generic 只排序+规范序列化）。
4. **软回滚优先，禁止硬删除**（`.disabled`/`RELAY_FORCE_PROVIDER=passthrough` 双逃生阀）。
5. **只 dump/透传，不重启上游**。
6. **密钥不落地**（透传，不存储）。

## 九、dump 观测格式与样例

`config.dump=true` 时中继把**对齐 + 重映射之后**的锚点指纹逐条追加到 `~/.cache-relay/dump.jsonl`（每请求一行 JSON）。开关**热生效**——`readConfig()` 是每请求调用的，改 config 不需要重启中继。

| 字段 | 含义 |
|---|---|
| `t` | 毫秒时间戳 |
| `fp` | 锚点指纹 = sha256(tools + system + params)，**不含 model 名** |
| `headFp` | 首条消息前 200 字符的 sha256 前 12 位 |
| `model` | 重映射之后实际发往上游的 model |
| `nMsgs` | messages 条数（突降 = 压缩/截断，前缀已重置） |
| `tools` | 工具名列表（仅 name，不含 schema） |
| `system` | 各 system 块前 100 字符 |
| `firstMsg` | 首条消息前 160 字符 |
| `hdr` | 请求头摘要；`authorization` 恒为 `<redacted>`，中继从不落地密钥 |
| `sidSent` | 改写后发出的 `x-claude-code-session-id`（分类器带 `-classifier` 后缀） |

**脱敏样例**：同目录 `dump.sample.jsonl`（2 条，主会话 + 分类器）。脱敏只做两件事——session uuid 换成占位 uuid、确认 `authorization` 已是 `<redacted>`；其余字段原样，不含密钥、不含节点域名。

> **现状（2026-09-12）**：命中率已稳定（最近 20 分钟 95.6%，两个会话分别 96.0% / 94.2%），故 `dump` 置 `false` 并清空 `dump.jsonl`，只保留脱敏样例。日后需要再做请求侧观测（如锚点跨会话复用验证、`stabilizeTokens` 单变量 A/B）时把开关改回 `true` 即可，无需重启。

## 十、性能优化与测试台（2026-09-12）

### 10.1 度量方法：先拆阶段，再决定优化谁

中继每请求串行走 `parse → align → stringify → byteLength`。**必须先把这四段的占比量出来**，否则容易在只占小头的部分使劲：

| 用例 | parse | align | stringify | byteLength | 合计 | align 占比 |
|---|---|---|---|---|---|---|
| main-full (293KB) | 0.71ms | 0.82ms | 2.11ms | 0.14ms | 3.99ms | ~20% |
| main-heavy (779KB) | 1.81ms | 1.87ms | 4.14ms | 0.38ms | 9.51ms | ~20% |
| classifier (4KB) | 0.01ms | 0.19ms | 0.02ms | 0.002ms | 0.22ms | 87% |

**结论：`parse`/`stringify` 合计约占 70%，且不可动**（上游拿到的字节必须一致，改了就是缓存前缀变更）。`align` 是唯一可优化段，天花板约 20% 的端到端提升。分类器请求则是另一回事——包体极小，align 占比 87%，优化收益最明显。

再往下拆 align 内部（基线上 293KB 主请求）：`stabilizeTokens` 38% + `stabilizeDates` 28% + `stripCacheControl` 16% + `relocateVolatile` 4% + `sortTools` 2%。

### 10.2 改了什么（全部保持产物逐字节不变）

| # | 优化 | 依据 |
|---|---|---|
| 1 | `readConfig()` 按 (mtimeMs, size) 缓存 | 每请求要读 3~4 次；文件一变立即失效，热改语义不变 |
| 2 | 日期与 token 稳定化**合并为一次遍历** | 原来是两次全量 `map`，各自走一遍全部消息 |
| 3 | 稳定化加 `indexOf` 预筛，未命中直接跳过 | `DATE_RE` 各分支必含 `Today`/`currentDate`/`今天`；`TOKEN_LEFT_*_RE` 必含 `tokens left` —— 都是**必要条件**，不是启发式 |
| 4 | 只在「确实变了」时才复制消息对象 | 原来逐条 `{...m}` 无条件复制 900 次 |
| 5 | `stripCacheControl` 用 `for...in` 代替 `Object.keys()` | 上万个节点，省掉逐节点一个键数组 |
| 6 | `stripCacheControl` 用**原文串**预筛 | 原文既无 `cache_control` 字面量、也无任何 `\u` 转义 ⇒ 解析结果必无该键（键名字符无需转义，`\uXXXX` 是唯一隐藏途径） |
| 7 | `sortTools` 复用单个 `Intl.Collator` + 已序预检 | `localeCompare` 每次调用都新建 collator，45 个工具要建 ~130 次；CC 发来的工具本身已序 → 直接跳过 |
| 8 | 整包只编码一次（`Buffer` 算长度并直接发送） | 原来 `Buffer.byteLength(body)` + `end(body)` 把整包编码了两遍 |
| 9 | 分类器 model 重映射移到 `stringify` 之前 | 原来分类器路径要序列化两遍整包 |
| 10 | 客户端断连 → 销毁上游请求 | 无人接收的后续 token 是真金白银 |
| 11 | 服务端与上游 socket 都 `setNoDelay(true)` | SSE 是小块高频，Nagle 攒包直接抬高逐字延迟 |
| 12 | `isClassifierRequest` 每请求只算一次 | 原来算 3~4 次 |
| 13 | 请求 URL 只解析一次 | 原来 `pathname`/`search` 各解析一遍 |

### 10.3 实测（Windows / Node 22，取中位）

| 指标 | 基线 | 优化后 | 提升 |
|---|---|---|---|
| `alignRequest` @293KB | 0.84ms | 0.42ms | **2.0×** |
| `alignRequest` @779KB | 1.87ms | 0.87ms | **2.15×** |
| 稳定化(日期+token) @779KB | 1.34ms | 0.62ms | 2.2× |
| `readConfig()` | 0.129ms/次 | 0.061ms/次 | 2.1× |
| 端到端路径 @293KB | 3.09ms | 2.89ms | 1.07× |
| 端到端路径 @779KB | 6.86ms | 6.30ms | 1.09× |
| 端到端 · 分类器 | 0.21ms | 0.13ms | 1.6× |

> **不要误读**：端到端只有 7~9%，因为 align 只占路径 20%，剩下 70% 是动不了的 `parse`/`stringify`。**relay 的 CPU 也不是用户感知延迟的主要来源**（上游本身 100ms~2s），它的真正代价是——中继是单线程的，这几毫秒的阻塞会同时压住其他并发会话的 SSE 转发。所以 CPU 优化的收益要按「并发下的转发抖动」理解，不是按单请求延迟。

### 10.4 测试台（`scripts/claude-ops-deployments/cache-relay/experiments/`）

| 脚本 | 作用 | 通过标准 |
|---|---|---|
| `payloads.mjs` | 按真实 CC 形状生成语料（45 个真实工具名、锚点~25K token、易变量开关） | — |
| `cache-relay.baseline.mjs` | 改动前的冻结副本，作为等价性基准 | — |
| `test-align-equiv.mjs` | 基线 vs 优化：19 组用例 × (对齐产物 + raw 预筛路径 + 分类器判定) + 幂等 = **112 项** | 全过 |
| `test-relay-integration.mjs` | 真起假上游 + 中继子进程，走完整 HTTP 链路：对齐 / 模型重映射 / **sid 分离** / 连接复用 / 断连销毁 / 热配置 / 400 兜底 / 判源 = **31 项** | 全过 |
| `bench-align.mjs` | 端到端基准 + 阶段拆解 | — |
| `probe-steps.mjs` | align 内部逐步耗时，基线 vs 优化并排 | — |

跑法：`node experiments/test-align-equiv.mjs` · `node experiments/test-relay-integration.mjs`。

**这次测试真的抓到了一条行为变更**：把 `stabilizeDates`+`stabilizeTokens` 合并时，`anthropic` 分支被顺手带上了 token 钉桩——而 anthropic 策略原本**只**稳定日期、不钉 token。等价性测试直接报了字节差异（`999700 tokens left` vs `1000000 tokens left`），随即改为 `stabilizeVolatileText(body, { tokens: false })`。**合并遍历这类「看起来纯机械」的改动，必须靠逐字节等价测试兜底。**

### 10.5 一个判源陷阱（既有设计，非本次引入）

假上游若用裸 IP（`127.0.0.1:PORT`）+ `/v1/messages` 路径，`detectProvider` 会兜底判成 **anthropic** —— 该分支按设计**不**剥 `cache_control`、**不**钉 token。生产走 `api.deepseek.com` 会自动判对，但**换任何未知域名+`/v1/messages` 都会静默走 anthropic 策略**。集成测试因此显式 `forceProvider` 钉住，并单列一节验证生产 URL 的判源结果。

### 10.6 安全性质：改文件不影响运行中的中继

Node 启动时已把脚本载入内存，**编辑 `cache-relay.mjs` 不会影响正在服务的进程**，只有重启才生效。因此可以在不打断在途会话的前提下改代码、跑测试、提交；重启是独立的最后一步。

### 10.7 未采用：把 parse/align/stringify 丢进 worker 线程

理论上能让事件循环不被阻塞，但每请求要把 1.5MB 缓冲跨线程搬运（约 1ms 拷贝 + 往返延迟），且徒增复杂度与故障面；在 align 已被压到 0.4~0.9ms 的前提下收益不成立，故不做。
