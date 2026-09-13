---
title: Agent 评测与可观测性知识
aliases: [Agent评测, agent-evals, LLM-as-Judge, 可观测性知识]
tags: [ai/ops, ai/agent]
created: 2026-08-26
updated: 2026-09-13
status: review
source: 外部依据：Anthropic Building Effective Agents/Multi-Agent Research System 评测章节、LangSmith trajectory evals 与 online evaluators 文档、LLM-as-Judge 校准实践；内部锚点：质量门控/实时交互/LogNet 各文档
fetched_at: 2026-08-26
---

# Agent 评测与可观测性知识

> [!abstract] 定位
> 库内已有"质量门控状态机"（怎么判 RETRY/ESCALATE），但**评测方法论本身**（判据从哪来、怎么校准、trace 怎么采）无沉淀。本文补齐：评测对象三层次、四层方法栈（含校准与在线评估）、可观测 trace 采集要点、回归门控集成与成本维度。Anthropic 的立场是评测先于复杂度——成功标准不定，一切架构讨论都是空转。

See also: [[state-machine-quality-gate-loop]] · [[agent-harness-anatomy]] · [[Anthropic多智能体研究系统拆解]] · [[main-subagent-realtime-interaction]] · [[Claude-Ops-KB-Home]]

## 一、评测先行（为什么排第一）

Anthropic《Building Effective Agents》的构建顺序是：**定义成功标准 → 建最小评测集 → 再谈架构复杂度**。没有可度量判据时：① 无法判断 workflow→agent 的升级是否为正收益；② 多代理 15× token 放大失去对照基线；③ 质量门控的阈值沦为拍脑袋。
库内映射：[[lognet-rootcause-multiagent-architecture]] §九.3 的 PoC 假设清单就是该原则的实例（每阶段带验收口径）。

## 二、评测对象三层次

| 层次 | 对象 | 典型断言 | 工具形态 |
|------|------|---------|---------|
| L1 单步 | 单次工具调用/单轮回复 | 参数 schema 合法？检索命中？ | 单元式断言集 |
| L2 轨迹 (trajectory) | 整个执行路径 | 步骤顺序合理？没绕路？工具选择对？ | LangSmith [trajectory evals](https://langchain-5e9cc07a.mintlify.app/langsmith/trajectory-evals)：对比参考轨迹或按规则评分 |
| L3 端到端 (outcome) | 最终交付物 | 报告引用保真？根因结论正确？ | rubric 打分 + 人工抽检 |

> [!tip] 本库对应
> LogNet PoC 的 27 项测试 = L1；多代理展开后的"根因命中率"（Doc D §十 M2 口径）= L3；L2 目前缺位——可在 Sidecar 里以结构化 step 日志 + 规则评分补齐（见 §四）。

## 三、方法栈四层（由便宜到贵）

1. **确定性断言**：schema 校验、引用可回溯（如 query_logs refs 指针能 reopen 到原始字节——已在 PoC 测试落地）
2. **LLM-as-Judge + rubric**：固定评分维度（groundedness/覆盖/平衡），few-shot 锚点样例定标；judge 与人类分歧需定期抽样校准（[LangChain 校准实践](https://www.langchain.com/resources/llm-as-a-judge)）
3. **人工盲测**：真实任务对比基线（单代理 vs 多代理），防"基准好看没人用"
4. **在线评估**：生产流量采样跑 evaluator，持续回归（[LangSmith online evaluators](https://langchain-5e9cc07a.mintlify.app/langsmith/online-evaluations-multi-turn)，支持多轮会话级判定）

Anthropic 多代理系统的三件套（rubric judge / 人工真实任务 / 生产遥测）正是 2+3+4 的组合，详见 [[Anthropic多智能体研究系统拆解]] §四。

## 四、可观测性采集要点

- **Trace 结构化**：每次 LLM 调用/工具调用记为 span（输入摘要/输出摘要/token/延迟/错误）；父子关系=委派树。OpenTelemetry GenAI 语义约定可作为字段命名基准（成熟度演进中，**待确认**当前版本号）

> [!success] 残余复核（2026-09-13）：**没有「稳定版本号」可填**——GenAI 约定整体仍在 experimental 面。
> 本机依赖树内 `@opentelemetry/semantic-conventions@1.43.0`（DSH profile 的 node_modules）中，`gen_ai.*` 属性**全部**落在 `experimental_attributes`（83 处 `GEN_AI_*` 命中，含 `GEN_AI_AGENT_NAME` / `GEN_AI_INPUT_MESSAGES` / `GEN_AI_CONVERSATION_ID` 等），`stable_attributes` **零命中**；`index-incubating` 亦无 gen_ai。故字段命名基准可用，但引用时必须写成「semconv 包的 experimental 模块 + 所依包版本」，**不能**宣称 stable。
> 依据（本机）：`%USERPROFILE%\.dsh\profiles\node_modules\@opentelemetry\semantic-conventions\`（`experimental_attributes.d.ts` vs `stable_attributes.d.ts`）

- **本库既有实践**：
  - DSH `session.jsonl`（事件级全量回放，本会话重建即靠它）
  - `builder.stats` 结构化统计（解析侧可审计性，见 deployment-log 2026-08-26 条目）
  - job/goal 生命周期事件（后台任务的活性观测原语）
- **多代理特有**：委派边界必须落 span 边界——否则子代理耗时/失败无法归因（[[main-subagent-realtime-interaction]] T0 感知的数据基础）

## 五、回归与门控集成

```
评测分 ──▶ 质量门控状态机（[[state-machine-quality-gate-loop]]）
   ├─ ≥ 阈值A ──▶ PASS 归档
   ├─ A > x ≥ B ──▶ RETRY（换策略重跑，预算内 N 次）
   └─ < B    ──▶ ESCALATE（人工/更强模型）
```

- 阈值必须来自 §三 第 2/3 层的历史分布（分位数定标），不是整数美感
- CI 内置 agent 冒烟：每次 harness 配置变更（提示词/权限/工具面）跑 L1+采样 L2，防止"改一句 prompt 崩一条链路"
- 升级阶梯与看门狗联动：连续 ESCALATE 触发 T2/T3（[[main-subagent-realtime-interaction]]）

## 六、成本维度

- 计量口径统一到 span：tokens/调用次数/墙钟分别入账，才能定位"慢在哪、贵在哪"
- 多代理预算闸在编排层实现（fan-out 前 check 余量），参考 15× 系数做容量规划
- 评测本身也有成本：judge 用小模型 + 分层采样（L1 全量、L2 按失败率采样、L3 定期抽检）

## 七、待确认项

> ① OpenTelemetry GenAI 语义约定的稳定版本号与字段全集；② LangSmith 在线评估对本库私有部署形态的支持方式；③ judge 校准的最小标注样本量经验值（文献口径不一）；④ DSH 侧 trace 导出为 OTLP 的可行性。

> [!success] 残余复核（2026-09-13）：①④ 已就地定论。
> - **① 稳定版本号不存在**，字段全集 = semconv `experimental_attributes` 的 `GEN_AI_*` 集（随包版本演进）——见 §四 复核块。
> - **④ 可行，但导出的是「会话日志」不是「span trace」**：DSH 自带官方后端 `@deepseek-ai/dsh-session-telemetry-otel`，经 OTel JS SDK 走 **OTLP/HTTP logs 信号**（端点形如 `<collector>/v1/logs`，由 `DSH_TELEMETRY_OTLP_URL` 覆盖默认值；该包依赖 `exporter-logs-otlp-http` 而非 trace 导出器），**并非 traces/span**；且 mode 只有 `FEEDBACK_ONLY`（默认）与 `DISABLED` 两态，`FULL` 被显式拒绝，而本库 dsh-tui profile 又把 mode 钉在 `DISABLED`（`DSH_TELEMETRY_MODE` 可覆盖）。
>   结论：**要 span 级 trace 得自建**——本库 `session.jsonl`（§四 既有实践）就是现成数据源，别指望官方导出器产出委派树 span；「委派边界落 span 边界」这条多代理特有要求，在 DSH 上目前无官方出口。
> - 依据（本机）：`%USERPROFILE%\.dsh\profiles\node_modules\@deepseek-ai\dsh-session-telemetry-otel\README.zh.md`、同 profile 的 `@deepseek-harness-tui\dsh-tui\cordis.patch.yml`（`session-telemetry-otel` 行）
> - **② 有官方私有部署形态，但门槛是 Enterprise 授权**：LangSmith **Self-hosted** 是 **Enterprise 套餐的附加项（add-on，需 license key）**，可在自有基础设施（AWS / GCP / Azure，Kubernetes + Terraform 装机，亦提供 BYOC）内跑完整栈——服务含 frontend(nginx)/backend/Platform backend/Playground/queue/ACE；存储依赖 **ClickHouse（traces+feedback）+ PostgreSQL（运维数据）+ Redis（队列与缓存）**，另可选 blob。→ 结论：**技术上支持私有部署，但不是零成本自托管**；对本库这种个人/小规模形态，自建 ClickHouse+PG+Redis 的代价高于收益，在线评估若要用，仍以走云版或改用轻量自研采样评估更划算。
>   依据（取回 2026-09-13）：<https://docs.langchain.com/langsmith/self-hosted>
> - **③ 有可用经验口径，「口径不一」的根因是 N 应由统计目标反推而非取常数**：绝对下限 **50** 条人工标注（低于 50 被视为统计上无意义）；生产常用 **100–200**，未测过 judge 一致性时以 **N=200** 作初始默认；若要求 95% CI 半宽 ≤0.10 或存在稀有类（如 ~6% 基率的安全违规），需抬到 **300–400+**。可达性锚点：**用 100–200 条专家金标注可把 judge 与人类一致率校准到 ~85%**（Netflix 案例：4 个质量维度、100–200 条 gold 标注、与专业编剧一致率 >85%）。另：judge 提示内的 few-shot（2–3 条/维度）与「人工标注校准集」是两件事，别混算。
>   依据（取回 2026-09-13）：<https://labelstud.io/learningcenter/getting-started-with-llm-evaluation/>、<https://www.langchain.com/resources/llm-as-a-judge>（后者给流程与 ~80% 人类一致率锚点，**不给**最小样本量——这正是「文献口径不一」的来源）

## Related

[[agent-harness-anatomy]] · [[state-machine-quality-gate-loop]] · [[Anthropic多智能体研究系统拆解]] · [[main-subagent-realtime-interaction]] · [[lognet-rootcause-multiagent-architecture]] · [[opencode-pi-base-development-analysis]] · [[Claude-Ops-KB-Home]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 定论 | §四「OpenTelemetry GenAI 语义约定…待确认当前版本号」 | 加复核块：本机 semconv 1.43.0 中 `gen_ai.*` 全部只在 `experimental_attributes`（83 命中）、`stable_attributes` 零命中 → **无稳定版本号**，引用须标 experimental；依据本机依赖树 |
| 定论 | §七 ①「GenAI 语义约定稳定版本号与字段全集」 | 同上一行结论；「字段全集」= experimental 的 `GEN_AI_*` 集，随 semconv 包版本演进，不可当稳定契约 |
| 定论 | §七 ④「DSH 侧 trace 导出为 OTLP 的可行性」 | 加复核块：DSH 有官方 `dsh-session-telemetry-otel`，但走 **OTLP logs 信号**（非 traces）、mode 仅 FEEDBACK_ONLY/DISABLED，本库 profile 钉在 DISABLED → span 级 trace 需自建（`session.jsonl` 为现成源）；依据本机 README 与 profile 配置 |
| 定论 | §七 ②「LangSmith 在线评估对本库私有部署形态的支持方式」 | 加复核块：官方 **Self-hosted** 为 Enterprise 附加项（需 license key），AWS/GCP/Azure + K8s/Terraform，存储依赖 ClickHouse+PostgreSQL+Redis → 技术上支持但非零成本自托管。依据取回 2026-09-13：docs.langchain.com/langsmith/self-hosted |
| 定论 | §七 ③「judge 校准的最小标注样本量经验值（文献口径不一）」 | 加复核块给出可用口径：下限 50、生产 100–200、未测一致性时默认 N=200、CI≤0.10 或稀有类需 300–400+；100–200 条专家金标注可达 ~85% 一致率（Netflix 案例）。根因说明：N 应由目标 kappa/CI 与类别平衡反推，故文献无普适常数。依据取回 2026-09-13：labelstud.io 学习中心 + langchain.com/resources/llm-as-a-judge |

回链：[[CORRECTIONS]] · [[AGENTS]]
