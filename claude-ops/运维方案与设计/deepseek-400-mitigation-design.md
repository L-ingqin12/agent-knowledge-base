---
title: DeepSeek 400 双类报错规避与恢复方案
aliases: [DeepSeek 400, Content Exists Risk 规避, Claude Code 内容审核兜底, thinking 协议 400]
tags: [ai/ops, ai/agent]
created: 2026-09-06
updated: 2026-09-13
status: review
---

# DeepSeek 400 双类报错 — 全局规避与恢复方案

See also: [[Claude-Ops-KB-Home]] · [[claude-cache-relay-design]] · [[claude-cache-optimization]] · [[tianshu-cache-aim-plan]] · [[claude-context-continuity-guide]] · [[deepseek-400-mitigation-usage|使用说明]]

> [!abstract] 概述
> Claude Code 经 [[claude-cache-relay-design|cache-relay]]（:8790）路由到 DeepSeek。2026-09-06 全天反复出现**两类 400**：内容审核（`Content Exists Risk`，~90%）与 thinking 协议（`reasoning_content must be passed back`，~10%）。二者都导致会话回合中断，且污染历史令之后每轮复发 → 会话"被动报废"。本文给出**预防 → 恢复 → 兜底**三层方案，核心原则「主路留 DeepSeek 同一模型，保缓存命中与上下文连续性；切供应商只作最后兜底」。

> [!danger] ⛔ 为什么必须做
> 一旦 400 命中，触发内容就"焊"进会话历史，之后每轮 `--continue` 都重发含毒历史 → 永远 400，只能新开会话。

---

## 一、根因（已取证坐实）

| # | 报错 | 占比 | 触发源 | 换模型能否规避 |
|---|---|---|---|---|
| A | `Content Exists Risk`（内容审核） | ~90%（300+ 次） | 历史混入代理节点域名/端口、订阅链接、地区绕过等 | ❌ 换另一个 DeepSeek 模型无效（同一审核层）；须换供应商 |
| B | `reasoning_content must be passed back` / `content[].thinking` / `prefill unsupported`（thinking 协议） | ~10%（26 次） | DeepSeek V4 思考模式 + 工具调用，`reasoning_content` 未回传 | ✅ 有透明修复，**不换供应商** |

关键事实：DeepSeek 是**生成前对整包请求体**（system + 多轮历史 + tool_result）做服务端预检，任一消息段命中即整包 400，**无官方参数可关**；400 属客户端错误，Claude Code 不重试，`fallbackModel` 只认 5xx/同端点不触发。

> [!warning] 更正（2026-09-13）：本节的「已取证坐实」应降级为「**本机实测现象 + 待厂商确认的归因**」（原表述为标题里的「根因（已取证坐实）」）。
> - **占比只有本机样本口径**：~90%（300+ 次）/ ~10%（26 次）取自本机日志，无外部对照。官方 [Error Codes](https://api-docs.deepseek.com/quick_start/error_codes) 页实取仅有 `400 - Invalid Format`、401/402/422/429/500/503，**没有任何内容审核条目**——「同一审核层」「无官方参数可关」是由**缺失证据反推**的，不能当既定事实。
> - **B 类归因需修正**：官方 Thinking Mode 页要求按 OpenAI 格式把 assistant 的 `reasoning_content` 随 messages 回填；Anthropic 兼容页则把 `content[] type=thinking` 列为 Supported——**两者是不同协议面**，故「`reasoning_content` 未回传」不能直接解释原生 `/anthropic` 路径的报错（§七 其实已自我怀疑）。[来源](https://api-docs.deepseek.com/guides/thinking_mode)、[来源](https://api-docs.deepseek.com/guides/anthropic_api)

## 二、设计原则

1. **主路留 DeepSeek 同一模型**，保 prompt 缓存命中 + 上下文连续性。
2. **切换供应商（GLM）只作最后兜底**，代价 = 缓存全丢 + 跨模型连续性断裂。
3. 一切改动**本地化、可逆、幂等**，软回滚优先、密钥不落地。

## 三、总体架构（三层，复用 [[claude-cache-relay-design|cache-relay]]）

```
Claude Code
   │ ANTHROPIC_BASE_URL = http://127.0.0.1:8790（settings.local.json）
   ▼
┌───────────────────────────────────────────────┐
│ cache-relay（已部署）                           │
│   ① 缓存对齐（strip cache_control/排序/稳定化） │
│   ② 内容审核 400 兜底：命中 → 改投 OpenRouter    │
│      z-ai/glm-5.3-flash（只换 auth+model）     │
└───────────────────────────────────────────────┘
   │（默认）              │（仅兜底，最后手段）
   ▼                      ▼
 DeepSeek 官方          OpenRouter GLM
```

- **第一层 预防**（§四）：不触发 400，主路留 DeepSeek。
- **第二层 恢复**（§五）：触发后剪除污染，继续留 DeepSeek。
- **第三层 兜底**（§六）：前两者都失效时才切 GLM（已实现进 cache-relay）。

> [!danger] 路由自检（2026-09-13 补）：生效 base URL 决定上面两层保护是否存在
> 本机实测冲突：`~/.claude/settings.json` L4 `"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic"`（官方直连，L6 另有 `ANTHROPIC_MODEL: deepseek-flash[1m]`），`~/.claude/settings.local.json` L3 `"ANTHROPIC_BASE_URL": "http://127.0.0.1:8790"`（走 relay）——**两处同时存在且取值相反**，生效值取决于 Claude Code 的配置合并优先级（公开文档未给可引用条目，故该项整体记 unverifiable）。
> - **若生效值是直连**：§三 的两层保护（缓存对齐 + 400 兜底）**同时失效且无任何告警**——请求根本不进 relay。
> - **自检方法**：跑一次会话后确认 relay 侧有无该请求（有 = 走 :8790；完全无 = 直连）；`node cache-relay.mjs doctor [baseUrl] [model]` 能判源，但不证明 CC 侧正在用哪个值。
> - **冲突处置规则**：`ANTHROPIC_BASE_URL` 只在一处声明（或让两处取值一致），改动后重复自检；直连状态下的降级动作是显式切回 :8790 或改走 §四 的预防层。

> [!success] 残余复核（2026-09-13）：**「整体 unverifiable」已被本机实测推翻——生效值是 `:8790`（走 relay），两层保护在场。**
> 上面「自检方法」里那条自检已跑：本机正在运行的 Claude Code 进程环境实测 `ANTHROPIC_BASE_URL=http://127.0.0.1:8790`（取自子进程继承的 env，只读，未改任何配置）；同期 `%USERPROFILE%\.cache-relay\dump.jsonl` 正在被写入，末条记录的 `firstMsg` 就是当次复核会话本身的提示词、`model=deepseek-flash` —— **请求确实进了 relay 而非直连**。故 `~/.claude/settings.local.json` 的取值压过 `~/.claude/settings.json`，上文「若生效值是直连则两层保护静默失效」的失效形态**当前不成立**。
> 定论口径说明：这里给的是**本机行为证据**（env + relay 侧收发记录），不是「配置合并优先级」的公开文档条目；换言之「谁赢」已实测确定，**但「为什么赢」（合并规则本身）仍无一手文档可引**。故上文那句「公开文档未给可引用条目」依然成立，只是不再影响结论。见 [[claude-cache-relay-design]]。

## 四、第一层：预防（主）— 已实现

**4.1 全局 `~/.claude/CLAUDE.md` 追加「会话红线」**：禁止回显裸节点域名、`host:port` 清单、订阅链接、base64 串；节点清单一律引用文件路径；脚本输出继续脱敏；讨论节点用稳定伪名。

**4.2 触发词表**：恢复脚本运行时现读 `node-pool.txt` + `proxy-nodes.json` 自动生成节点 token，另设 `sanitize-extra.txt`（话题词，事故驱动补充）。**新节点自动进表，零维护**。

## 五、第二层：恢复（次）— 待落地（需确认放行）

目标：把毒从会话 jsonl 里物理剪除，`claude --continue` 原地续聊，**留 DeepSeek 保连续性**（仅一次性缓存重建）。

**5.1 内置命令结论**：`/rewind` 只能一刀切回退 checkpoint、磁盘旧行不一定物理清除 → 只适合"毒在最近一两轮"；`/compact` 本身是会 400 的模型调用、且倾向原样保留 IP/端口 → 不可作主手段。

**5.2 `sanitize-session.py`**（落 `network/scripts/`，与 node-pool 同目录）：
- 只做**整行原始文本子串替换，绝不删行、不改 uuid/tool_use↔tool_result 配对**。
- 安全闸门：备份 → 逐行 `json.loads` 校验 → 结构指纹前后对比 → 原子写。
- `--check` 只读扫描只报命中行数；`--mode aggressive` 追加话题词 + `scheme://` 链接清洗。

> [!warning] 恢复脚本会改写 Claude Code 会话 transcript
> 属用户自有本机会话文件、用于从内容审核误报中救回上下文，非隐瞒/伪造。落地需用户明确确认「误报非篡改」（harness 拦截）。

## 六、第三层：兜底（备）— 已实现并部署

**在 [[claude-cache-relay-design|cache-relay.mjs]] 上扩展**，而非新建网关：

- 命中 `400 + "content exists risk" 关键词` → 同一请求体改投 OpenRouter `z-ai/glm-5.3-flash`（只换 `authorization` 头 + `model` 名，成功路径纯透传，零协议转换 → 结构上无 thinking/tool bug 风险）。
- 兜底 key 走 `authTokenSource` 指向 `~/.claude/oxalpha-settings.json`（**不落地到 config.json**，符合密钥不落地原则）。
  > [!warning] 待确认（2026-09-13 复核）：`~/.claude/oxalpha-settings.json` 确实存在（顶层键实测为 `model`、`env`），`~/.cache-relay/config.json` 的 `fallback.authTokenSource` 实测即指向该文件（密钥确未落到 relay 配置）。**但其中 OpenRouter key 是否仍有效、失效时 relay 会否把 401 误判为「兜底失败」而静默丢保护，无任何证据**；另注 `stealth/ox-alpha` 实测 endpoints 为空、不在 445 条模型列表中——文件名沿用已下线代称。建议补：启动时对 authTokenSource 做一次轻量 models 调用校验，失效即显式告警；文件名迁到中性名称。[来源](https://openrouter.ai/api/v1/models/stealth/ox-alpha/endpoints)
  > [!success] 残余复核（2026-09-13）：上面这条**拆成两半——「401 会否被静默吞掉」已由源码定论，只剩「key 是否仍有效」需联网。**
  > **① 「静默丢保护」不成立（读源码定论）**：`cache-relay.mjs` 兜底分支是 `if (fb.stream) { res.writeHead(fb.status, fb.headers); ... }`——OpenRouter 的 401/402 带响应体 ⇒ **原状态码直传客户端**，且必经 `console.log('[cache-relay] 400 risk → fallback ... status=401')`。**不存在把 401 当成「兜底失败」而静默吞掉的分支**。真正会「静默丢保护」的是另一条路：`fallbackConfig()` 在**读不到文件/读不到 `env.ANTHROPIC_AUTH_TOKEN` 时直接 `return null`**，此时内容审核 400 兜底**整体禁用且无任何告警**——这是比「key 失效」更该先加告警的分支。
  > **② 文件名问题比记录的更轻**：`oxalpha-settings.json` 顶层 `model` 实测已是 `z-ai/glm-5.3-flash`，**文件内容早已不指 ox-alpha**，只有文件名是遗留代称 ⇒ 「迁到中性名称」是纯 cosmetic，非风险项。（`stealth/ox-alpha` endpoints 为空一事仍成立，但已无路径引用它。）
  > **③ 仍未决（需联网，勿凭猜）**：key 是否仍有效。判据：`curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOK" https://openrouter.ai/api/v1/key` —— `200` = 有效，`401/403` = 已失效（`$TOK` 从该文件的 `env.ANTHROPIC_AUTH_TOKEN` 取，**勿回显**）。不改用户配置，故只记判据不代跑。
  > 方法论回链：[[CORRECTIONS]]。
- 配置：`~/.cache-relay/config.json` 的 `fallback` 块（`upstream` / `modelMap` / `riskKeywords` / `authTokenSource`）。
- 已热部署（:8790），语法校验通过。

**兜底自身的失败契约（2026-09-13 补，原文未定义超时/重试/终态）**：

| 项 | 待定义内容 |
|---|---|
| 单请求超时 | 兜底转发 OpenRouter 的超时上限（否则原本快速失败的 400 会变成长时间挂起） |
| 重试与退避 | 兜底侧 5xx / 超时后的最大重试次数与退避曲线 |
| 请求体处理 | 原 400 请求体是否裁剪后再投（含毒历史会被整包带上，等于把风险原样交给 GLM） |
| 兜底再失败的终态 | 502 透传，还是原样回上游错误？会话表现为「死」还是「降级」 |
| 自愈与钉住的先后 | A 类 400 会**焊进历史**，兜底只救当下回合；「会话钉住/熔断」（§九 P1）需与污染自愈排序——先判能否消毒，再决定是否钉住 |

> [!success] 残余复核（2026-09-13）：**上表「待定义内容」五项中四项已由 `cache-relay.mjs` 现码定义，表头可视为「已定义现状」而非待办。**
> | 项 | 实测定义（源码） |
> |---|---|
> | 单请求超时 | `const timeoutMs = Number(process.env.RELAY_TIMEOUT_MS ?? 180000)`；超时 `out.destroy()` → 返回 `{status:504, stream:null}`。**兜底与主路走同一个 `forward()` ⇒ 180s 上限同样约束兜底**，`RELAY_TIMEOUT_MS` 可覆盖 |
> | 重试与退避 | **无**：`forward()` 内无 retry/backoff 逻辑（无 `maxRetries`），单次失败即终态。原文担忧的「400 变长时间挂起」不成立（受 180s 封顶） |
> | 请求体处理 | **不裁剪**：`fbBody` 仅做 `p.model = map[p.model] ?? map['*']`，其余原包转发 ⇒ 含毒历史整包交给 GLM，原文的顾虑**已被源码证实**（属已知取舍，非疏漏） |
> | 兜底再失败的终态 | `if (fb.stream)` → **透传 `fb.status`+headers**（401/402/5xx 原样给客户端）；`stream` 为空（如超时 504）→ **回传原始 400 + 原 errBody**。两种都非静默，且都有 `console.log(...status=)` |
> | 自愈与钉住的先后 | **无从排序——「会话钉住/熔断」未实现**（源码内无按会话指纹钉源/熔断逻辑，见 §九 P1），故当前恒为「每请求兜底」 |
> **衍生发现（应补，属实现缺口）**：`deploy` 子命令以 `spawn(..., { detached:true, stdio:'ignore' })` 启动守护 ⇒ **relay 的 `console.log` 全部丢弃**。§八 让运维「观察日志 `[cache-relay] 400 risk → fallback ... status=200`」在已部署形态下**根本看不到该行**（见 §十 端到端验证条目）。依据：`scripts/claude-ops-deployments/cache-relay/cache-relay.mjs`（现码，只读）。

- 兜底目标合理性已核实：`z-ai/glm-5.3-flash` 在架，endpoints 实测 26 个。[来源](https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints)

> [!tip] 为什么不自研新网关、不用 CCR
> cache-relay 已经在路径上且做了缓存对齐，直接在其上加兜底最省、最贴合「结合缓存优化」；CCR v3 太重且配错协议会退化 OpenAI 转换引入 thinking bug；dsv4-cc-proxy / claude-code-fallback 均不处理 400 内容审核。

## 七、thinking-400 的归属（待确认）

`reasoning_content must be passed back` 是 OpenAI 转换路径的产物；本机走原生 `/anthropic`，理论上不该踩。但会话里确实扫到 ~10%。解释：那是原生端点的 adaptive/injection 边角（dsv4-cc-proxy 修的）。实施验证时若复现，把 dsv4-cc-proxy 的注入逻辑折进 cache-relay（多几十行，仍留 DeepSeek）。

> [!warning] 残余复核（2026-09-13）：**仍开放（须复现实验，本机离线手段只能缩小范围）。**
> 已排除的两种可能（读码/搜盘定论，非猜测）：**① relay 侧无任何 thinking 注入或修复逻辑**——`cache-relay.mjs` 全文 grep `thinking` / `reasoning_content` **零命中** ⇒ 该类 400 在原样透传下**无任何缓解**，发生即发生；**② 修复所依赖的 `dsv4-cc-proxy` 本机不存在**（已搜 `%USERPROFILE%` 深度 3、`D:\Document`、`D:\SoftWare` 深度 4，零命中，也未随仓库入库）⇒ 原文「折入其注入逻辑」目前**无源可取**，不是「多几十行」就能落地。
> 因此本节的归因（「原生端点 adaptive/injection 边角」）**仍是假设**：它既未被本机证据支持、也未被否证。
> 复核判据（须真机，勿凭猜）：把 relay 跑在前台（因 `deploy` 丢弃 stdout，见 §六 衍生发现）→ 用工具调用密集的会话连续跑 ≥20 轮 → 抓 `reasoning_content must be passed back` / `content[].thinking` 是否出现在**走 `/anthropic` 的这份请求**上。**期望看到什么**：若现，则「原生端点也会踩」成立，需先拿到 dsv4-cc-proxy 源码或自写注入；若连续 ≥20 轮零命中，则本节的 ~10% 应重新归因到历史样本口径（与 §一 更正块同一性质，属本机样本外推）。

## 八、实施状态与验证

| 层 | 状态 | 落地 |
|---|---|---|
| 预防 | ✅ 已实现 | `~/.claude/CLAUDE.md` 会话红线 + `sanitize-extra.txt` |
| 恢复 | ⏳ 待放行 | `sanitize-session.py`（harness 拦截，需确认误报） |
| 兜底 | ✅ 已部署 | cache-relay.mjs 扩展 + `~/.cache-relay/config.json` |

验证：兜底触发需构造审核命中请求，观察日志 `[cache-relay] 400 risk → fallback ... status=200`；恢复用 `--check` 扫描零命中后 `--continue`。

> [!warning] 残余复核（2026-09-13）：**上句的验证判据在「已部署」形态下失效——照它做必然误判。**
> `cache-relay.mjs` 的 `deploy` 以 `spawn(..., { detached:true, stdio:'ignore' })` 起守护 ⇒ **relay 的 `console.log` 没有任何落点**（既无日志文件、也无管道），上面那行 `400 risk → fallback ... status=200` **永远不会被看到**，会被误读成「兜底没触发」。
> 改为可执行判据：让 relay 前台/重定向运行（`node cache-relay.mjs daemon > relay.log 2>&1`），再构造审核命中请求，在 `relay.log` 中确认该行；**期望 `status=200`**（= GLM 放行，见 §九）。若要长期留证，应在 relay 内把该行写文件而非仅 stdout。

## 九、风险与待确认

- **GLM 是否放行被 DeepSeek 拦的内容**：同为国产模型，可能 200 软拒 → 需实测。
- **原生端点 thinking-400 是否复现**：若复现折入 dsv4-cc-proxy 注入逻辑。
- **会话钉住/熔断**（P1 优化）：命中后按会话指纹钉到备源，避免污染期每轮白打一次 DeepSeek。当前为每请求兜底。
- 凭据卫生：`settings.local.json` 权限列表、DSH 备份残留旧 key，建议清理/轮换。

> [!warning] 残余复核（2026-09-13）：**本节四条——两条实证未实现/无源，两条须真机，均仍开放。**
> - **GLM 是否放行被 DeepSeek 拦的内容**：仍开放。不能本机定论（要真发一次被拦内容）。判据：relay 前台运行下，构造成交触发词请求 → 看 `[cache-relay] 400 risk → fallback ... status=` ；**`status=200` = GLM 放行，`400` 或 `200` 但正文为软拒话术 = 不放行**。注意「同为国产模型 ⇒ 也会拒」目前只是猜测，未取证。
> - **原生端点 thinking-400 是否复现**：仍开放，判据与已排除项见 §七 复核块（relay 零 thinking 逻辑、`dsv4-cc-proxy` 本机不存在）。
> - **会话钉住/熔断（P1）**：**已确认未实现**（源码全文无按会话指纹钉源/熔断分支，只有互不相干的「钉桩」=前缀稳定化，「钉」字同名易混）。故「当前为每请求兜底」这句**属实**。该条仍是有效待办，不是文档笔误。
> - **跨库参考 [[tianshu-cache-aim-plan]] §七 P1–P5**：见 §十 复核，属对侧已登记的在册遗留，非本文待办。

> [!success] 残余复核（2026-09-13）：**「凭据卫生」里的 `settings.local.json` 权限列表一项已实测排除——无凭据泄漏。**
> 只读解析 `%USERPROFILE%\.claude\settings.local.json`：`permissions.allow` 共 **534 条，全部是工具权限模式**（`Bash(...)` / `Read(...)` / `mcp__...` 等，如 `Bash(wsl *)`、`Bash(reg query *)`），**非工具前缀条目 0 条**，且无任何形如 token/key/secret 的条目 ⇒ 权限列表**不含凭据**，原「建议清理」对这项可结案。
> **但「DSH 备份残留旧 key」经实测属实且比记录的更广**（只报文件与类型，**不回显任何值**）：`%USERPROFILE%\.dsh\ds2ox-proxy.mjs` 内**硬编码了一个 OpenRouter key（已脱敏）**，且该代理已判定退役却仍留在盘上；`settings.yaml` 的两份备份 `settings.yaml.pre-ds2ox` / `settings.yaml.pre-upgrade` 按注释即旧 key 的存放处；`%USERPROFILE%\.dsh\.credentials.yaml` 含 `DEEPSEEK_API_KEY`。**属用户侧清理/轮换动作，本次只做只读核查、未改用户配置**；另注该退役代理的复活路径（Startup 里的 `DS2OxProxy.vbs`）仍在，见 [[ds2ox-proxy-retirement]]。

## 十、遗留 / 后续清单（todo）

- [ ] 恢复脚本 `sanitize-session.py` 落地（harness 拦截，待用户确认"误报非篡改"）
- [ ] 兜底端到端验证：构造审核命中请求，确认日志 `400 risk → fallback ... 200`
- [ ] 会话钉住/熔断（P1）：命中后按会话指纹钉到备源，避免污染期每轮白打 DeepSeek
- [ ] 原生端点 thinking-400 复现确认：若复现，折入 dsv4-cc-proxy 注入逻辑
- [ ] GLM 对被 DeepSeek 拦截内容的放行实测
- [ ] 凭据卫生：清理 `settings.local.json` 权限列表 / DSH 备份残留旧 key
- [ ] 跨库参考 [[tianshu-cache-aim-plan]] 的 P1–P5 遗留（请求体快照 / 聚合 doctor / date-stability 守卫等）

> [!success] 残余复核（2026-09-13）：**七条清单逐条判定——2 条可结案、1 条属对侧在册、4 条仍开放（但判据已具体化）。**
> - **[可结案] `sanitize-session.py` 落地**：脚本**已在库** `network/scripts/sanitize-session.py`，可运行（实测 `--help` 正常，参数 `--session/--dir/--mode{safe,aggressive}/--replace-str/--check` 与 §5.2 设计**逐项对得上**）。剩下的只是**用户对「误报非篡改」的放行确认**（harness 拦截，属人工决策）⇒ 「落地」这部分完成，脚本本身无待补。
> - **[可结案] 跨库参考 [[tianshu-cache-aim-plan]] 的 P1–P5**：非本文待办。对侧 §七「遗留/后续（本轮不做）」已把 P1（请求体快照）/P2（聚合 `/doctor`）/P4（date-stability 守卫）/P5（permafrost coalescer + keepalive）**显式登记为不做的在册项**；本文这句是**回链**，把待办归属写清即可。
> - **[仍开放] 兜底端到端验证**（原文判据不可用，须改）：§八 让「观察日志 `[cache-relay] 400 risk → fallback ... status=200`」，但已部署形态下 `deploy` 用 `stdio:'ignore'` 起守护 ⇒ **该行永远不落任何地方，按原判据验证必然「看不到」而被误判为未触发**。可执行判据：以 `node cache-relay.mjs daemon > relay.log 2>&1 &`（或前台）跑，构造成交触发词请求，在 `relay.log` 里等 `400 risk → fallback ... status=200`。
> - **[仍开放] 会话钉住/熔断（P1）**：已确认源码未实现（见 §九 复核）。
> - **[仍开放] 原生端点 thinking-400 复现确认**：见 §七 复核（relay 零 thinking 逻辑；`dsv4-cc-proxy` 本机不存在，修复无源）。
> - **[仍开放] GLM 放行实测**：见 §九 复核（须真机发一次被拦内容）。
> - **[部分结案] 凭据卫生**：`settings.local.json` 权限列表实测无凭据（534 条全为工具模式，结案）；DSH 备份旧 key 属实且更广（含 `ds2ox-proxy.mjs` 硬编码 key，已脱敏不回显），须用户清理/轮换。见 §九 复核。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §一「根因（已取证坐实）」把本机日志占比与归因当既定事实 | 保留标题与原表 + 就地降级为「本机实测现象 + 待厂商确认的归因」：官方 Error Codes 页无任何内容审核条目 ⇒ 占比只有本机样本口径；B 类归因需修正（Thinking Mode 是 OpenAI 格式面、Anthropic 兼容页把 `content[] type=thinking` 列为 Supported，两者不同协议面） |
| 补疏漏 | §三架构图只写 `settings.local.json: ANTHROPIC_BASE_URL=:8790`，未说明实际两处配置取值相反、且直连会绕过 relay | 新增「路由自检」块：列出 settings.json（直连）/settings.local.json（:8790）实测冲突与优先级不可引用的事实；给出失效形态（两层保护静默失效）、自检方法、冲突处置规则 |
| 补疏漏 | §六兜底只描述「命中 → 改投 GLM」，无超时/重试/失败后再失败的契约 | 新增失败契约表五项：单请求超时、重试与退避、请求体是否裁剪、兜底再失败的终态、自愈与「会话钉住」的先后；并核实兜底目标 `z-ai/glm-5.3-flash` 在架（26 个 endpoints） |
| 补疏漏 | §六把 `authTokenSource` 只当密钥卫生的正面说明 | 保留原句 + 待确认块：文件与配置指向已核实，但 key 有效性、401 被误判为「兜底失败」而静默丢保护均无证据；建议启动时轻量校验 + 显式告警 + 中性文件名 |
| 残余复核 | §三 路由自检块自记「生效值取决于合并优先级，公开文档无可引用条目 ⇒ 整体 unverifiable」 | **实测推翻 unverifiable**：运行中的 CC 进程 env 实测 `ANTHROPIC_BASE_URL=http://127.0.0.1:8790`，且 `%USERPROFILE%\.cache-relay\dump.jsonl` 末条 `firstMsg` 即当次复核会话、`model=deepseek-flash` ⇒ 生效值为 relay，两层保护在场；仅「为何如此合并」仍无一手文档（不影响结论） |
| 残余复核 | §六 待确认：`authTokenSource` 的 key 有效性、401 会否被误判为兜底失败而静默丢保护 | **读源码分半定论**：① 「静默丢 401」不成立（`if (fb.stream)` 直传 `fb.status` 且必打 `status=401` 日志）；真正静默的分支是 `fallbackConfig()` 读不到文件/`env.ANTHROPIC_AUTH_TOKEN` 时 `return null` ⇒ 兜底整体禁用无告警，**该加告警的是这条**；② 文件名纯 cosmetic（实测顶层 `model` 已是 `z-ai/glm-5.3-flash`）；③ key 有效性仍需联网，已给 `curl .../api/v1/key` 判据 |
| 补疏漏 | §六 兜底失败契约表标题「待定义内容」五项未定 | **四项由现码定义**：超时 `RELAY_TIMEOUT_MS ?? 180000`→504（兜底同用 `forward()`）；**无重试无退避**；请求体**不裁剪**只换 model（含毒历史整包交 GLM，原文顾虑被证实）；再失败时 `fb.stream` 存在则透传状态、为空则回传原始 400；「钉住先后」无从排序因未实现。**衍生**：`deploy` 用 `stdio:'ignore'` ⇒ relay `console.log` 全丢，§八 的验证判据在部署形态下不可观测 |
| 残余复核 | §七 thinking-400 归属（标注待确认） | **仍开放**：读码排除两可能——relay 全文 grep `thinking`/`reasoning_content` **零命中**（无任何缓解）；`dsv4-cc-proxy` 本机不存在（搜 `%USERPROFILE%` 深 3 与 `D:\Document`/`D:\SoftWare` 深 4），修复**无源可取**；归因仍是假设，已给前台 relay + ≥20 轮工具密集会话的复现判据 |
| 残余复核 | §九/§十：GLM 放行、thinking-400 复现、会话钉住（P1） | GLM 放行与 thinking-400 **仍开放**（须真机，已给 `status=200` vs 软拒的判读口径）；**会话钉住/熔断已确认未实现**（源码无该分支，「钉桩」是同名易混的前缀稳定化）⇒「当前为每请求兜底」属实且该 todo 有效 |
| 残余复核 | §十：`sanitize-session.py` 落地、跨库 P1–P5、凭据卫生 | 脚本**已在库可用**（`network/scripts/sanitize-session.py`，`--help` 实测，参数与 §5.2 逐项对上），仅余用户「误报非篡改」放行（人工决策）；P1–P5 **属 [[tianshu-cache-aim-plan]] §七 在册遗留**，本文仅回链；`settings.local.json` 权限列表实测 **534 条全为工具模式、无凭据**（可结案），DSH 备份旧 key 属实且更广（`ds2ox-proxy.mjs` 硬编码 key，**已脱敏不回显**；`.credentials.yaml` 含 DeepSeek key）——**只读核查，未改用户配置** |

依据：[Error Codes](https://api-docs.deepseek.com/quick_start/error_codes)、[Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)、[Anthropic 兼容页](https://api-docs.deepseek.com/guides/anthropic_api)、[OpenRouter endpoints](https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints)。方法论回链：[[CORRECTIONS]] · [[AGENTS]]。
