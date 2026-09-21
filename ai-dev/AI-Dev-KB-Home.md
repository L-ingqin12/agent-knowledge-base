---
title: AI Dev KB Home — LLM 应用开发实战专题库
aliases: [AI开发MOC, LLM应用开发首页, AI-Dev-KB]
tags: [ai, moc, ai/learning]
created: 2026-08-25
updated: 2026-09-22
status: review
---

# AI Dev KB Home

> [!abstract] 本子库定位
> 《AI大模型应用开发工程师》课程体系的知识库落盘：**一文档一问题**，每个专题独立成文、可运行 Demo 齐备、图表统一 Excalidraw。
> 理论基础（Transformer 手推/术语解析/源码）见 [[AI大模型开发]]；本页是实战层的总入口。

## 2026-09-12 合并入库的子库（原独立仓库）

> 由账号下**描述同类任务**的独立仓库合并而来，原仓库可直接归档。

| 子目录 | 原仓库 | 内容 |
|--------|--------|------|
| `agent-learn/` | `L-ingqin12/agent-learn` | AI Agent 开发学习项目：知识文档 + Python 包（`agent_learn/`，含 `adapters/`）+ 可运行示例 |
| `mcp-learn/` | `L-ingqin12/mcp-learn` | MCP 协议学习指南 13 篇：核心概念 / 快速上手 / 服务端·客户端开发 / tools-resources-prompts / 传输 / 最佳实践 / MCP-vs-Skill / 跨平台 / 测试调试 / 真实案例 / 生态项目 |

> 与本库既有文档的关系：[[MCP协议开发实战]] 是实战向；`mcp-learn/` 是**体系化教程向**（13 篇递进），两者互补而非重复。

## 文档地图

| # | 专题文档 | 一句话解决的问题 | 配套图 |
|---|----------|------------------|--------|
| 1 | [[Prompt-Engineering入门与Demo]] | 如何写出稳定可控的 prompt（few-shot/LtM/CoT/结构化输出） | ![[Prompt-Engineering-LtM-Flow.excalidraw]] |
| 2 | [[Function-Calling工具调用实战]] | 让模型"说→做"：双轮调用与四大进阶挑战 | ![[Function-Calling-Sequence.excalidraw]] |
| 3 | [[RAG检索增强生成实战]] | 私域知识问答：架构演进/选型/性能优化/评估 | ![[RAG-Pipeline.excalidraw]] |
| 4 | [[GraphRAG知识图谱增强实战]] | 全局性/多跳问题：实体抽取+社区检测+Local/Global Query | ![[GraphRAG-Flow.excalidraw]] |
| 5 | [[LLM-Agent开发基础]] | Agent 四组件与手写 ReAct 循环 | ![[ReAct-Agent-Loop.excalidraw]] |
| 6 | [[MCP协议开发实战]] | 工具生态标准化：Server/Client/三种传输 | ![[MCP-Architecture.excalidraw]] |
| 7 | [[A2A多智能体协作协议]] | 跨框架 Agent 互操作：Agent Card/Task/委托 | — |
| 8 | [[LangChain-LangGraph框架实战]] | LCEL 与状态机式 Agent：State/Checkpointer/Supervisor | ![[Multi-Agent-Supervisor.excalidraw]] |
| 9 | [[LLM推理部署与量化]] | Ollama/vLLM/Ray 多机多卡与量化选型 | ![[Training-vs-Inference.excalidraw]]（复用） |
| 10 | [[LoRA参数高效微调实战]] | 低秩旁路微调原理 + Llama-Factory 实操 + 监控指标 | ![[LoRA-Principle.excalidraw]] |
| 11 | [[强化学习对齐-RLHF到GRPO]] | PPO/DPO/GRPO 对齐算法谱系与奖励模型 | ![[RLHF-GRPO-Pipeline.excalidraw]] |
| 12 | [[微调数据工程与模型蒸馏]] | SFT/COT/偏好数据集构建 + R1 式黑箱蒸馏 | ![[Training-vs-Inference.excalidraw]]（复用） |
| 13 | [[Agent-Skills技能开发实战]] | SKILL.md 规范与渐进式披露：给 Agent 写"说明书"（课程第13章补齐） | — |
| 14 | [[多模态Agent平台实战]] | 语音/视觉管线四层架构与延迟预算（课程第21章补齐） | — |
| 15 | [[LLM架构进阶-从注意力变体到推理引擎]] | MHA/GQA/MLA 演化账本、RoPE 外推、MoE 工程真相、连续批处理/PagedAttention/投机解码机制级（2026-08-26 新增） | — |
| 16 | [[本地LLM部署与显存实测-4GB卡]] | **4GB 显存卡上哪些本地模型真能跑、跑多快、坑在哪**——7 模型实测基准 + 长对话体感 + 多模态 + 本地 API/DSH 接入（2026-09-22 新增） | — |
| 17 | [[本地推理栈探测与调优方法论]] | **怎么问一个不透明的推理栈**——探针设计、录包法、测量纪律、调优策略、失败模式速查（2026-09-22 新增） | — |
| 18 | [[本地模型能力矩阵与任务路由]] | **哪个任务给哪个模型**——7 模型实测能力矩阵 + 任务标签表 + 输出成本路由规则 + 证据弱点（2026-09-22 新增） | — |

## 脚本清单

本子库涉及的脚本集中在 [[Ollama本地推理脚本集|scripts/ollama-local/]]：

| 用途 | 脚本 |
|---|---|
| 一行式推理入口 | `llm.py` / `llm.cmd` |
| 烤入调优参数 | `apply_tuning.py` · `apply_sampling.py` |
| 基准与验证 | `verify_tuning.py` · `tune_ctx_speed.py` · `bench_model.py` · `stress_chat.py` · `test_longrun.py` · `test_accuracy.py` |
| 多模态验证 | `test_vision.py` + `make_testimage.py` |
| **逃生机制** | `modelfiles_backup/`（7 份原始 Modelfile，唯一还原依据） |


## 课程外增补雷达（2026 时效性缺口）

> 课程内容相对行业演进存在滞后，以下主题按需展开（有 ✓ 者已在本库覆盖）：

| 主题 | 一句话要点 | 状态 |
|---|---|---|
| Prompt/Context Caching | 前缀缓存可省 75-90% 输入费用；DeepSeek 自动、Anthropic 显式断点 | ⏳ 待专题（现有素材：[[LLM推理部署与量化]] 的 `--enable-prefix-caching` 与「前缀缓存只对共享前缀生效」的坑；**该文件并无独立缓存节**，命中/未命中的计费差与 block 粒度待补） |
| Structured Outputs | JSON Schema 强约束输出，取代"请输出 JSON"祈祷式提示 | ✓ 见 [[Prompt-Engineering入门与Demo]] |
| Agent 可观测性 | Langfuse/LangSmith 追踪每次工具调用与 token 流水，评估驱动迭代 | ⏳ 待专题 |
| Guardrails 与安全护栏 | 注入防御、输出过滤、越权工具调用的白名单治理 | ⏳ 待专题（部分见 [[Agent-Skills技能开发实战]] allowed-tools） |
| Computer/Browser Use | 截图→定位→点击的 GUI 操作型 Agent，MCP 化浏览器控制 | ⏳ 待专题 |

> [!warning] 补疏漏（2026-09-13）：上表只有「一句话要点 + 状态」两列，缺触发条件与验收判据——读者不知道"补到什么程度算完成"（原表头为「主题 / 一句话要点 / 状态」三列）
> 逐条补上触发条件与最小验收判据：
>
> | 主题 | 触发条件 | 最小验收判据 |
> |---|---|---|
> | Prompt/Context Caching | 对外服务开始按 token 计费，或 prompt 前缀重复率高 | 能对一个真实负载算出命中率与省下的费用；能说清命中条件（前缀完全一致 + block 对齐）与 `--enable-prefix-caching` 的显存代价 |
> | Structured Outputs | 解析模型输出失败率已影响下游 | 用 JSON Schema 强约束跑通一次；非法输出率相对"祈祷式提示"明显下降到 0 |
> | Agent 可观测性 | 上线对外服务前 | 能追出一次工具调用的完整 span 与 token 流水，并有至少一条离线评估基线；素材见 [[agent-evals-observability]] |
> | Guardrails 与安全护栏 | 工具具备写操作/外发能力之前 | 红队注入样例 ≥20 条；拦截率与误杀率各出一个数；素材见 [[Agent-Skills技能开发实战]] 的 allowed-tools、[[上下文工程-注意力预算与四层解法]] |
> | Computer/Browser Use | 需要在没有 API 的界面上操作时 | 一条"截图→定位→点击"的端到端回放可重复成功，失败可归因（定位错 / 超时 / 权限） |

## 学习路径（建议顺序)

```
理论基础 [[AI大模型开发]]
   ↓
② API 开发 → ④ 提示词/FC → ⑤ Agent 基础 (5→6→7)      ← 应用层主线
   ↘ ③ 部署 (9)                                        ← 自托管支线
   ↘ ⑦ RAG (3→4) → ⑥ 框架 (8)                          ← 知识增强主线
⑧ 微调 (12→10→11)                                      ← 定制化主线
   ↓
⑨ 大型项目综合演练
```

> [!note] 编号口径与新增支线（2026-09-13 补注）
> 图中**圈码 ②-⑨ = 课程阶段**，**括号里的数字 = 文档地图编号（1-15）**——两套编号同现是本路径易误读之处（如 ④ 与 (5→6→7) 并非同一套序号）。
> 另：文档 **15 [[LLM架构进阶-从注意力变体到推理引擎]]** 此前未进入本路径，建议挂在阶段 ③ 部署之后（第 9 篇 [[LLM推理部署与量化]] 的机制层补充：MHA/GQA/MLA 演化、RoPE 外推、MoE、连续批处理 / PagedAttention / 投机解码）。
> 阶段 ⑨「大型项目综合演练」在文档地图 1-15 中没有对应条目，其落点见下方「项目案例地图」。

## 项目案例地图

| 课程项目 | 综合运用的知识点 | 相关专题 |
|----------|------------------|----------|
| ChatBI / iQuery Agent | Function Calling 调 MySQL + Python 解释器 + Memory + Planning | [[Function-Calling工具调用实战]] [[LLM-Agent开发基础]] |
| 企业智能问数系统 | Milvus + Neo4j + LangGraph 多智能体（意图识别/SQL生成/校验/执行/图表） | [[LangChain-LangGraph框架实战]] [[GraphRAG知识图谱增强实战]] |
| 高性能 RAG 商业项目 | 亿级语料入库 + rerank + Ragas 评估 + 联网问答 + Agent 化 RAG | [[RAG检索增强生成实战]] |
| 企业级智能体客服 v1/v2 | 压测 + 语义缓存 + minerU PDF 解析 + GraphRAG 工程化 + Multi-Agent 护栏 | [[LLM推理部署与量化]] [[GraphRAG知识图谱增强实战]] |

## 图表索引（diagrams/）

全部为 Excalidraw 格式，绘图规范见 [[AGENTS#十一、图表与可视化约定]] 与 [[ARROW-CHECKLIST]]：

本子库文档嵌入的图：`Prompt-Engineering-LtM-Flow`（文档 1） · `Function-Calling-Sequence`（2） · `RAG-Pipeline`（3） · `GraphRAG-Flow`（4） · `ReAct-Agent-Loop`（5） · `MCP-Architecture`（6） · `Multi-Agent-Supervisor`（8） · `Training-vs-Inference`（9、12 复用） · `LoRA-Principle`（10） · `RLHF-GRPO-Pipeline`（11）

> [!warning] 补疏漏（2026-09-13）：原清单只列 8 张，漏了文档 1 自己嵌入的 `Prompt-Engineering-LtM-Flow`（原表述为 `Function-Calling-Sequence` · `ReAct-Agent-Loop` · `RAG-Pipeline` · `GraphRAG-Flow` · `MCP-Architecture` · `Multi-Agent-Supervisor` · `LoRA-Principle` · `RLHF-GRPO-Pipeline`）
> `diagrams/` 目录全量为 **22 张 `.excalidraw.md`**（另有 1 个 `.excalidraw` 与各 1 个含 excalidraw 名的 `.ps1` / `.py`，合计 25 个文件）。本页只维护"子库嵌入了哪些图"，需要全量清单请直接看 `diagrams/` 目录——避免每新增一张图就要改一处易漏清单。

## 标签索引

- `#ai/learning` — 教程型专题（1,2,3,4,9,10,11,12,14,15）〔2026-09-13 更正：原为 1,3,4,9,10,11,12,14，漏了 2 [[Function-Calling工具调用实战]] 与 15 [[LLM架构进阶-从注意力变体到推理引擎]]，两者 tags 均含 ai/learning〕
- `#ai/agent` — Agent/协议类（5,6,7,8,13,14）〔2026-09-13 更正：原为 5,6,7,8,13，漏了 14 [[多模态Agent平台实战]]〕
- `#moc` — 本页

## 关联入口

- [[AI大模型开发]] — 理论根基与本子库的课程映射表（课程知识地图）
- [[AI-Links-KB-Home]] — AI 链接收藏库（工程方法论综述）
- [[Claude-Ops-KB-Home]] — Agent 运维实践（Harness Engineering 的真实战例）

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 第 53 行「Prompt/Context Caching … ✓ 见 [[LLM推理部署与量化]] 缓存节」指向不存在的小节（目标文件无「缓存」标题，只有 `--enable-prefix-caching` 参数与「前缀缓存只对共享前缀生效」的坑） | 状态改回 **⏳ 待专题**，并注明现有素材与缺口（命中/未命中的计费差、block 粒度待补） |
| 补疏漏 | 标签索引与实际 frontmatter 不一致：`#ai/learning` 漏 2、15；`#ai/agent` 漏 14 | 两行就地更正为 `#ai/learning`（1,2,3,4,9,10,11,12,14,15）与 `#ai/agent`（5,6,7,8,13,14），并在行内留原文以便追溯 |
| 补疏漏 | 图表索引只列 8 张，漏了文档 1 嵌入的 `Prompt-Engineering-LtM-Flow`；文档地图第 1 行「配套图」仍为「—」 | 索引改为"子库嵌入图清单（10 张，按文档编号）+ 指向 `diagrams/` 全量 22 张 `.excalidraw.md`"两段式；文档地图第 1 行补上该图 |
| 补疏漏 | 学习路径把圈码（课程阶段）与括号数字（文档地图编号）混用，且文档 15 既不在路径也不在索引 | 路径下补「编号口径与新增支线」注记：圈码=课程阶段、括号=文档编号；文档 15 挂到阶段 ③ 之后；并说明阶段 ⑨ 的落点在项目案例地图 |
| 补疏漏 | 「课程外增补雷达」5 个主题只有一句话要点 + ✓/⏳，无触发条件与验收判据 | 表下补逐条"触发条件 + 最小验收判据"表（如可观测性要能追出完整 span 与 token 流水、Guardrails 要 ≥20 条注入样例与拦截率/误杀率） |
| 补疏漏 | frontmatter 的 `updated` 停留在 2026-08-25，正文却含 2026-09-12 合并入库小节与 2026-08-26 新增条目，按时效筛选会漏内容 | `updated` 改为 2026-09-13（本次实质修改日期）；2026-09-12 合并批的来源与核验状态见本页第 16-25 行 |

> 说明：本次审计对「第 22-23 行 L-ingqin12 两个原仓库是否可核验」一条已由复核**驳回**（GitHub API 实测两仓库均 HTTP 200、`"private":false`、公开可见），故本页该处未作改动。
> 待人工确认：学习路径是否改成「阶段名 + 文档 wikilink 列表」两列式、`diagrams/` 是否加全量清单页——两项属结构调整，本次只做最小安全修改。

回链：[[CORRECTIONS]]（本库更正总表）
