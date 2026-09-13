---
title: 来源登记 — 学习与调研
aliases: [sources-learning-notes, 学习来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 来源登记 — 学习与调研

> [!abstract] 本页用途
> 存放「学习与调研」主题的来源条目，供 [[URL-Lookup]] 检索。
>
> **注意**：本主题已有成熟索引，**优先查它们**，避免重复登记：
> [[Articles-Index]]（文章库，15 篇）、[[AI-Links-KB-Home]]（链接收藏，18 条）、[[AI-Dev-KB-Home]]、[[CS-KB-Home]]。
> 更正（2026-09-13）：[[Articles-Index]] 原记「14 篇」，复核为 **15 篇**（`ai-links/articles/` 实测 16 个 `.md`，含索引页自身）。

## 已有索引（先查这里）

- 来源:: 文章库索引
  use_when:: 找可解释性 / 上下文工程 / Skill / 机制拆解类深度文章
  url:: wikilink://Articles-Index
  answers:: 15 篇文章的分主题索引（含「回答的问题」一列）；2026-09-13 复核：`ai-links/articles/` 实测 16 个 `.md`（含索引页自身）= 15 篇文章，索引页统计行自写「文章总数 15（articles/ 12 篇 + 仓库根目录 2 篇 + 2026-08-18 新增 K3 章节总结 1 篇）」。原登记为「14 篇」（过期数字，可追溯到 `_archive/SESSION-ARCHIVE-2026-08-18.md` 的「14 篇远程文章」）
  authority:: 高
  verified:: 2026-09-12

- 来源:: AI 链接收藏库 MOC
  use_when:: 找 Agent 技能 / 编码 Agent / 推理工程的收藏链接
  url:: wikilink://AI-Links-KB-Home
  answers:: 18 条链接的调研综述与学习价值评级
  authority:: 高
  verified:: 2026-09-12

- 来源:: AI 链接综述主文档
  use_when:: 要全景表 + 逐条分析 + 学习路线
  url:: wikilink://2026-08-16-AI链接综述与归档
  answers:: 全景表、9 类逐条分析、七条主线综述、四阶段学习路线
  authority:: 高
  verified:: 2026-09-12

- 来源:: LLM 应用开发实战子库
  use_when:: 学 Prompt / RAG / Agent / MCP / 微调
  url:: wikilink://AI-Dev-KB-Home
  answers:: LLM 应用开发各专题
  authority:: 高
  verified:: 2026-09-12

- 来源:: 计算机基础子库
  use_when:: 查语言/算法/系统/数据库/工具链
  url:: wikilink://CS-KB-Home
  answers:: 计算机基础各专题
  authority:: 高
  verified:: 2026-09-12

## 编码 Agent 调研（本库产出）

- 来源:: OpenCode 技术调研报告
  use_when:: 要参考 OpenCode 的 Agent/Plugin/Skills/MCP 机制
  url:: wikilink://参考-OpenCode-技术调研报告
  answers:: 全机制调研：Agent、Plugin-Hook、自定义工具、Skills、MCP、Server-SDK
  authority:: 高
  verified:: 2026-09-12

- 来源:: Pi Agent 技术调研报告
  use_when:: 要参考 Pi 的 SDK 嵌入与权限模型
  url:: wikilink://参考-Pi-Agent-技术调研报告
  answers:: SDK 嵌入、steer-followUp 队列、扩展系统、权限与风险
  authority:: 高
  verified:: 2026-09-12

- 来源:: Agent Harness 解剖
  use_when:: 要理解 Agent Harness 的组成
  url:: wikilink://agent-harness-anatomy
  answers:: Harness 结构与组件职责
  authority:: 中
  verified:: 2026-09-12

## 学习资源（外部，按需）

- 来源:: arXiv
  use_when:: 要找论文原文
  url:: https://arxiv.org/
  answers:: 论文预印本
  authority:: 高
  verified:: 2026-09-12

- 来源:: Obsidian 帮助文档
  use_when:: 查 Obsidian 语法/插件用法（本 vault 的前置字段、双链、Dataview）
  url:: https://obsidian.md/help/
  answers:: 语法、双链、插件配置；2026-09-13 实测该地址 HTTP 200（标题 Home - Obsidian Help）。更正（2026-09-13）：本条原 url 为 `https://help.obsidian.md/`（原表述）——实测跨域重定向到 `https://obsidian.md`，属上游迁移型失效；库内 `scripts/check-links.py` 跟随重定向、只记最终状态码，故巡检不会报出这类失效
  authority:: 高
  verified:: 2026-09-13

- 来源:: Dataview 文档
  use_when:: 写/改本库的 Dataview 查询（如 [[URL-Lookup]]）
  url:: https://blacksmithgu.github.io/obsidian-dataview/
  answers:: DQL 语法、内联字段、TABLE/LIST 查询写法。具体页：内联字段/元数据 https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/ （2026-09-13 实测 200：字段名可用任意 UTF-8 字符，内建隐式字段含 `file.cday` / `outlinks` / `etags` / `lists` / `tasks`——这正是 `sources/` 用 `字段:: 值` 语法的直接依据）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Dataview 发布版本（GitHub Release API）
  use_when:: 核对本机装的 Dataview 是否落后、升级前评估影响面（本页查询依赖它）
  url:: https://api.github.com/repos/blacksmithgu/obsidian-dataview/releases/latest
  answers:: 2026-09-13 实测 `tag_name = 0.5.70`（published_at 2025-04-07，body「Still attempting to fix #2557」）；本机 `.obsidian/plugins/dataview/manifest.json` 为 0.5.68——与 [[URL-Lookup]] 的版本策略条目一致
  authority:: 高
  verified:: 2026-09-13

## B3 复核新增（2026-09-13）：RAG / GraphRAG / 可解释性

> 均为本次复核实际打开并逐字核对的**官方**来源；`use_when` 写「什么时候要回查」。

- 来源:: Ragas PyPI 与官方迁移指南
  use_when:: 复核 Ragas 版本线与升级改法（0.1.x 函数式 / 0.2–0.3 类式 / 0.4+ collections）
  url:: https://pypi.org/project/ragas/
  answers:: 最新 0.4.3（2026-01-13）；v0.3→v0.4 迁移 https://docs.ragas.io/en/stable/howtos/migrations/migrate_from_v03_to_v04/ ；v0.1.21 context_precision 口径 https://docs.ragas.io/en/v0.1.21/concepts/metrics/context_precision.html
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek-V3 官方模型卡 / README
  use_when:: 核对 DeepSeek-V3 参数量与训练算力口径
  url:: https://raw.githubusercontent.com/deepseek-ai/DeepSeek-V3/main/README.md
  answers:: 671B total / 37B activated；2.788M H800 GPU hours（预训练 2.664M + 后训练 0.1M）；权重 685B = 671B + MTP 14B
  authority:: 高
  verified:: 2026-09-13

- 来源:: RAG 演进论文群（arXiv 原文）
  use_when:: 复核 Naive / Advanced / Modular 三段演进、长上下文位置效应、自纠错检索
  url:: https://arxiv.org/abs/2312.10997
  answers:: 2312.10997 RAG 综述（Modular 模块清单）；2310.11511 Self-RAG；2401.15884 CRAG；2307.03172 Lost in the Middle
  authority:: 高
  verified:: 2026-09-13

- 来源:: FlagEmbedding 官方 README（BGE 模型说明）
  use_when:: 写 BGE 检索代码前查 query instruction 与 v1.5 行为
  url:: https://raw.githubusercontent.com/FlagOpen/FlagEmbedding/master/README.md
  answers:: query instruction「为这个句子生成表示以用于检索相关文章：」；v1.5 的目的（without instruction 也能检索）；对称任务不加前缀
  authority:: 高
  verified:: 2026-09-13

- 来源:: numpy Generator 文档 / FAISS 度量说明
  use_when:: 复核「随机伪向量做召回」为何无效、内积与余弦的适用前提
  url:: https://numpy.org/doc/stable/reference/random/generator.html
  answers:: default_rng 语义（独立随机数流）；FAISS 度量类型 https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances
  authority:: 高
  verified:: 2026-09-13

- 来源:: Microsoft GraphRAG 官方文档（index / query）
  use_when:: 查 GraphRAG 索引方法与查询模式的官方口径
  url:: https://raw.githubusercontent.com/microsoft/graphrag/main/docs/index/methods.md
  answers:: Standard vs FastGraphRAG（抽取约占 75% 成本）；docs/query/overview.md 五类查询；docs/query/drift_search.md；docs/get_started.md（Python 3.10-3.12）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Microsoft GraphRAG CLI 与配置源码
  use_when:: 核对 CLI 子命令、默认参数、--root 默认值、增量更新与层级聚类实现
  url:: https://raw.githubusercontent.com/microsoft/graphrag/main/packages/graphrag/graphrag/cli/main.py
  answers:: init/index/update/prompt-tune/query 与 --method；defaults.py（chunk 1200/100、update_output、DRIFT 参数）；global_search_config.py（dynamic community selection 五参数）；cluster_graph.py（hierarchical_leiden）；pyproject.toml（graspologic-native 锁版本）
  authority:: 高
  verified:: 2026-09-13

- 来源:: graphrag PyPI 版本页
  use_when:: 锁 GraphRAG 版本或确认当前发布版
  url:: https://pypi.org/project/graphrag/
  answers:: 当前 3.1.2
  authority:: 高
  verified:: 2026-09-13

- 来源:: Microsoft Research — GraphRAG dynamic community selection
  use_when:: 解释 global search 的动态社区选择机制
  url:: https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/
  answers:: 机制定位（不重跑聚类，按社区报告相关性剪枝/下钻）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Neo4j Cypher 手册 — 全文索引
  use_when:: 要在 Neo4j 里做真正的全文/模糊检索（而非 CONTAINS 子串匹配）
  url:: https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/
  answers:: CREATE FULLTEXT INDEX / db.index.fulltext.queryNodes；Lucene 打分与模糊语法；与 range/text 索引的区别
  authority:: 高
  verified:: 2026-09-13

- 来源:: Leiden 论文《From Louvain to Leiden》
  use_when:: 说明 Leiden 与 Louvain 的实质差异（社区连通性保证）
  url:: https://arxiv.org/abs/1810.08473
  answers:: Leiden 保证社区内部连通；Louvain 不保证
  authority:: 高
  verified:: 2026-09-13

- 来源:: Gemma Scope 2 官方博文
  use_when:: 选 SAE / transcoder 做特征扫描前确认覆盖模型与发布状态
  url:: https://deepmind.google/blog/gemma-scope-2-helping-the-ai-safety-community-deepen-understanding-of-complex-language-model-behavior/
  answers:: 2025-12-19 发布；覆盖 Gemma 3；除 SAE 外含 transcoder
  authority:: 高
  verified:: 2026-09-13

- 来源:: circuit-tracer 官方 README（Anthropic 开源电路追踪）
  use_when:: 复现归因图前确认现成权重、后端与硬件门槛
  url:: https://raw.githubusercontent.com/decoderesearch/circuit-tracer/main/README.md
  answers:: 现成权重 Gemma-2 2B（426K/2.5M CLTs）与 Llama-3.2 1B（524k）；TransformerLens 覆盖限制；nnsight 仍 experimental；--dtype；Neuronpedia 零安装
  authority:: 高
  verified:: 2026-09-13

- 来源:: Anthropic — Natural Language Autoencoders (NLA)
  use_when:: 追 2026 年「激活直接翻译成自然语言」这条新路线
  url:: https://www.anthropic.com/research/natural-language-autoencoders
  answers:: 2026-05-07 发布；Opus 4.6 写诗前规划韵脚 rabbit；安全测试中的被测试意识与作弊；与 SAE / 归因图并列的定位
  authority:: 高
  verified:: 2026-09-13

- 来源:: Anthropic — 开源电路追踪工具公告
  use_when:: 确认「开源」范围与可复现对象
  url:: https://www.anthropic.com/research/open-source-circuit-tracing
  answers:: 发布于 2025-05-29；库名是 **circuit-tracer**（github.com/safety-research/circuit-tracer），官方原文「supports the generation of attribution graphs on popular open-weights models」——**不覆盖 Claude**；前端由 Neuronpedia 托管（交互入口 neuronpedia.org/gemma-2-2b/graph）；「led by participants in our Anthropic Fellows program, in collaboration with Decode Research」
  authority:: 高
  verified:: 2026-09-13

- 来源:: Transformer Circuits 论文库（Anthropic 可解释性）
  use_when:: 按时间线读叠加 → 单义性 → 归因图 → NLA 的原始论文
  url:: https://transformer-circuits.pub/2022/toy_model/index.html
  answers:: 2022 叠加；2023 monosemantic-features（SAE 起点）；2024 scaling-monosemanticity；2025 attribution-graphs/biology（对象 Claude 3.5 Haiku、覆盖率约 1/4）；2026/may-update
  authority:: 高
  verified:: 2026-09-13

- 来源:: tuned-lens 官方 README
  use_when:: 区分 logit lens 与 tuned lens 的训练与适用条件
  url:: https://raw.githubusercontent.com/AlignmentResearch/tuned-lens/main/README.md
  answers:: affine translator 概念；以 KL 散度对齐最终输出分布；与直接 unembed 的 logit lens 的区别
  authority:: 高
  verified:: 2026-09-13

## B6 复核新增（2026-09-13）：agent-learn / mcp-learn 上游

> 本次回写实际打开并逐条核对的**上游主源**（GitHub 主源 / PyPI / 官方规范页）；`use_when` 写「什么时候要回查」。

- 来源:: oh-my-openagent 上游仓库（含 dev 分支 AGENTS.md / ROADMAP.md）
  use_when:: 核对 oh-my-opencode→oh-my-openagent 的版本线、Agent 名册、工具与 hook 计数、运行时状态目录
  url:: https://github.com/code-yeongyu/oh-my-openagent
  answers:: release 线 v5.0.0-beta.x 与 `omo-ai@beta`、git tag（≥ v4.5.12）、12-38 registry tools、54-62 lifecycle hooks、11 agents、`.sisyphus/`→`.omo/` 迁移、ROADMAP 实际条目与 Team Mode 现状
  authority:: 高
  verified:: 2026-09-13

- 来源:: oh-my-opencode npm 包元数据
  use_when:: 判断该 CLI 的现行发行标识、安装命令与 bin 别名
  url:: https://registry.npmjs.org/oh-my-opencode/latest
  answers:: latest 4.19.4（v5 线走 `omo-ai@beta`）、license SUL-1.0、bin 五别名（omo / lazycodex / lazycodex-ai / oh-my-opencode / oh-my-openagent）
  authority:: 高
  verified:: 2026-09-13

- 来源:: jsDelivr GitHub 源文件与文件清单接口
  use_when:: GitHub trees API 被 403 限流时，按 ref 逐文件核对源码或取整仓文件清单
  url:: https://data.jsdelivr.com/v1/packages/gh/<owner>/<repo>@<ref>?structure=flat
  answers:: 指定 ref 的完整文件清单；单文件原文走 `cdn.jsdelivr.net/gh/<owner>/<repo>@<ref>/<path>`
  authority:: 中
  verified:: 2026-09-13

- 来源:: agent-learn 上游仓库（L-ingqin12/agent-learn）
  use_when:: 核对该学习项目的文档 / 示例 / 模块清单与 README 是否同步
  url:: https://github.com/L-ingqin12/agent-learn
  answers:: main 分支 docs 01–14、examples 01–11、agent_learn 13 模块 + adapters/；仓库 created 2026-05-30、无 LICENSE 文件
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP 规范 2026-07-28 · 变更日志
  use_when:: 判断 MCP 鉴权与协议的现行口径（哪项刚被弃用、哪项成为首选）
  url:: https://modelcontextprotocol.io/specification/2026-07-28/changelog
  answers:: OAuth 2.0 Dynamic Client Registration (RFC 7591) 正式弃用、Client ID Metadata Documents 成为首选注册机制
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP 规范 2026-07-28 · 弃用登记
  use_when:: 查某项特性的弃用日期与移除时间
  url:: https://modelcontextprotocol.io/specification/2026-07-28/deprecated
  answers:: HTTP+SSE 双端点传输由 SEP-2596 归档为 Deprecated（移除=SEP-2596 Final 后三个月）；DCR 移除时间为「First revision released on or after 2027-07-28」
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP 规范 · Streamable HTTP 传输
  use_when:: 需要确认「SSE 到底废没废」——废弃的是传输还是流式机制
  url:: https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http
  answers:: 请求级 SSE 流语义（请求相关通知 + 最终响应）、长连接变更通知由 `subscriptions/listen` 响应流交付
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP 官方教程 · 构建服务器（2026-07-28）
  use_when:: 需要一个「写服务器 → 接入 host → 调用工具」的可验收路径
  url:: https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server
  answers:: 服务器开发的完整验收链路与 host 接入步骤（教程用 Claude for Desktop）
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP Python SDK v2 · 更新说明
  use_when:: 把 v1 的 `FastMCP` 代码迁到 v2，或判断某教程写法属于哪一代 SDK
  url:: https://py.sdk.modelcontextprotocol.io/v2/whats-new/
  answers:: v2 为当前稳定线、`FastMCP`→`MCPServer`、传输配置移入 `run()`、客户端侧新增能力
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP Python SDK v2 · 迁移指南
  use_when:: 逐条替换 v1 API（模块路径、context 参数、注册与校验行为）
  url:: https://py.sdk.modelcontextprotocol.io/v2/migration/
  answers:: 模块迁至 `mcp.server.mcpserver`、`get_context()` 移除、`call_tool`/`read_resource`/`get_prompt` 带 context、RFC 9207 `iss` 校验与 `application_type`
  authority:: 高
  verified:: 2026-09-13

- 来源:: Anthropic 工程博客 · 多 Agent 研究系统
  use_when:: 引用「MAS 消耗 15× token」这类多 Agent 成本结论时，回到原文与适用条件
  url:: https://www.anthropic.com/engineering/multi-agent-research-system
  answers:: 原文口径「agents ~4× chat tokens / multi-agent ~15× chat tokens」，语境为 BrowseComp 类研究任务 + 需任务价值足够高
  authority:: 高
  verified:: 2026-09-13

## B5 复核新增（2026-09-13）：微调与对齐

> 本次回写（LoRA / RLHF-GRPO / 微调数据工程与蒸馏三篇）实际打开并逐字核对的来源；含论文原文、官方文档与上游源码，`use_when` 写「什么时候要回查」。

- 来源:: Qwen2.5-0.5B 模型配置
  use_when:: 要按真实 config 复算 LoRA 可训练参数量与占比（笔记里的"≈0.5%"就是在这算错的）
  url:: https://huggingface.co/Qwen/Qwen2.5-0.5B/raw/main/config.json
  answers:: hidden_size=896、24 层、num_key_value_heads=2；r=8 挂 q/k/v 时 trainable=737,280，占 494,032,768 的 0.1492%
  authority:: 高
  verified:: 2026-09-13

- 来源:: LoRA 论文（arXiv:2106.09685）
  use_when:: 查低秩旁路、α/r 缩放与"可训练参数降 10000 倍"的原始口径
  url:: https://arxiv.org/abs/2106.09685
  answers:: r=4 只挂 q/v 时 checkpoint 约 350GB→35MB；on-par 证据限定在 RoBERTa / DeBERTa / GPT-2 / GPT-3
  authority:: 高
  verified:: 2026-09-13

- 来源:: LoRA Learns Less and Forgets Less（arXiv:2405.09673）
  use_when:: 判断"LoRA 少遗忘"与"能追平全量微调"的边界（两者是交换关系）
  url:: https://arxiv.org/abs/2405.09673
  answers:: 标准低秩设置下 LoRA 明显弱于全量微调，但目标域外的基座能力保持更好
  authority:: 高
  verified:: 2026-09-13

- 来源:: QLoRA 论文全文（arXiv:2305.14314v1）
  use_when:: 核对 4bit/NF4 与"全线性层"结论；验证"QLoRA 官方建议 ZeRO 配置"是否真有出处
  url:: https://arxiv.org/html/2305.14314v1
  answers:: 「LoRA on all linear transformer block layers are required to match full finetuning performance」；全文检索 "ZeRO" 命中 0 次
  authority:: 高
  verified:: 2026-09-13

- 来源:: HF Transformers TrainingArguments 文档
  use_when:: 确认 eval_strategy 等训练参数默认值（解释为什么 Demo 里没有 eval_loss）
  url:: https://huggingface.co/docs/transformers/main/en/main_classes/trainer
  answers:: eval_strategy 默认 "no"：训练期间不评测
  authority:: 高
  verified:: 2026-09-13

- 来源:: LLaMA-Factory 现存 LoRA SFT 示例
  use_when:: 要一条真能跑通的 llamafactory-cli train 示例（旧 qwen2_5_lora_sft.yaml 已被上游移除）
  url:: https://raw.githubusercontent.com/hiyouga/LLaMA-Factory/main/examples/train_lora/qwen3_lora_sft.yaml
  answers:: 现存的 LoRA SFT 示例文件；examples/train_lora/ 下只有 qwen3_* / qwen3vl_*
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSpeed ZeRO 论文（arXiv:1910.02054）
  use_when:: 核对 ZeRO 三级显存倍数与通信代价的原句（勿再把 400 GPUs 记成 400B 模型）
  url:: https://arxiv.org/abs/1910.02054
  answers:: P_os=4×、P_os+g=8× 且通信量与 DP 相同；仅 P_os+g+p 通信 +50%；实测是 100B/170B 模型跑在 400 块 V100 上
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSpeed 官方 zero.md
  use_when:: 查 ZeRO Stage1/2/3 各自分片什么的权威定义
  url:: https://raw.githubusercontent.com/microsoft/DeepSpeed/master/docs/_tutorials/zero.md
  answers:: Stage1 优化器状态、Stage2 再分片 16-bit 梯度、Stage3 再分片参数
  authority:: 高
  verified:: 2026-09-13

- 来源:: LLaMA-Factory README（EasyR1 公告）
  use_when:: 确认 GRPO 由谁承担——本仓库还是姊妹项目
  url:: https://raw.githubusercontent.com/hiyouga/LLaMA-Factory/main/README.md
  answers:: 「[25/02/24] Announcing EasyR1, an efficient, scalable and multi-modality RL training framework for efficient GRPO training」
  authority:: 高
  verified:: 2026-09-13

- 来源:: LLaMA-Factory tuner.py（stage 分发）
  use_when:: 核对 --stage 到底支持哪些训练阶段（GRPO 在不在内）
  url:: https://raw.githubusercontent.com/hiyouga/LLaMA-Factory/main/src/llamafactory/train/tuner.py
  answers:: stage 分发只有 pt / sft / rm / ppo / dpo / kto，无 grpo 模块
  authority:: 高
  verified:: 2026-09-13

- 来源:: TRL DPOTrainer 源码（main）
  use_when:: 写 DPOTrainer 调用前确认形参名（processing_class 还是 tokenizer）
  url:: https://raw.githubusercontent.com/huggingface/trl/main/trl/trainer/dpo_trainer.py
  answers:: __init__ 形参含 processing_class，没有 tokenizer、也没有 **kwargs
  authority:: 高
  verified:: 2026-09-13

- 来源:: TRL DPOTrainer 源码（v0.25.0）
  use_when:: 复现旧版 TRL 写法报 TypeError 时，确认旧版形参
  url:: https://raw.githubusercontent.com/huggingface/trl/v0.25.0/trl/trainer/dpo_trainer.py
  answers:: v0.25.0 同样没有 tokenizer 形参（新旧两版都会抛 TypeError）
  authority:: 高
  verified:: 2026-09-13

- 来源:: PyPI trl 版本元数据
  use_when:: 查 TRL 当前版本与发布时间，判断笔记里的版本描述是否过期
  url:: https://pypi.org/pypi/trl/json
  answers:: 最新 1.13.0（2026-09-10 上传）；v0.25.0 为 2025-11
  authority:: 高
  verified:: 2026-09-13

- 来源:: verl 仓库
  use_when:: 要找支持 PPO/GRPO 的大规模 RL 框架
  url:: https://github.com/volcengine/verl
  answers:: 字节开源的大规模 RL 框架，支持 PPO/GRPO
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek-R1 论文全文（arXiv:2501.12948v2）
  use_when:: 核对 R1 的 RL 硬件与成本、奖励设计（为何不用神经 RM）、蒸馏 800K 数据配方与超参、学习率表
  url:: https://arxiv.org/html/2501.12948v2
  answers:: 64×8 H800 / 198 小时、147K GPU 小时 / $294K、Reward_rule=Reward_acc+Reward_format、batch 512 由 32 题组成、每 400 步刷新 ref、最大长度 32768、B.4.3 表 6 学习率（1.5B 1e-4 → 70B 2e-5）、600K 推理数据来自拒绝采样
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek-V3 论文全文（arXiv:2412.19437v2）
  use_when:: 区分 V3 与 R1 的训练集群、查 V3 预训练规模
  url:: https://arxiv.org/html/2412.19437v2
  answers:: 「DeepSeek-V3 is trained on a cluster equipped with 2048 NVIDIA H800 GPUs」（R1 的 2048 块说法来源于此）
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeekMath / GRPO 原始论文（arXiv:2402.03300v3）
  use_when:: 查 GRPO 原始超参（组大小、学习率、KL 系数）
  url:: https://arxiv.org/html/2402.03300v3
  answers:: 64 samples/question、lr 1e-6、KL 系数 0.04
  authority:: 高
  verified:: 2026-09-13

- 来源:: Understanding R1-Zero-Like Training（arXiv:2503.20783）
  use_when:: 诊断 GRPO 训练中回答变长的偏置，找无偏替代（Dr. GRPO）
  url:: https://arxiv.org/abs/2503.20783
  answers:: GRPO「artificially increases response length (especially for incorrect outputs) during training」
  authority:: 高
  verified:: 2026-09-13

- 来源:: DPO 论文（arXiv:2305.18290）
  use_when:: 评估 DPO 的分布外退化风险（"离线即稳"是否成立）
  url:: https://arxiv.org/abs/2305.18290
  answers:: §6.3 表 1：CNN/DailyMail 新分布上 DPO 0.36 vs PPO 0.26
  authority:: 高
  verified:: 2026-09-13

- 来源:: RewardBench 2（arXiv:2506.01937）
  use_when:: 选 RM 时判断"只报 RewardBench v1 分数"会不会系统性高估
  url:: https://arxiv.org/abs/2506.01937
  answers:: 模型在 v2 上平均比 v1 低约 20 分
  authority:: 高
  verified:: 2026-09-13

- 来源:: Hinton 知识蒸馏原文（arXiv:1503.02531）
  use_when:: 要 KD 的温度软标签公式、1/T² 梯度约束与硬软损失组合方式
  url:: https://ar5iv.labs.arxiv.org/html/1503.02531
  answers:: q_i=exp(z_i/T)/Σ_j exp(z_j/T)；soft target 梯度按 1/T² 缩放、同用时需乘 T²
  authority:: 高
  verified:: 2026-09-13

- 来源:: bash(1) 手册页
  use_when:: 写多行 shell 命令时确认续行与注释的边界
  url:: https://man7.org/linux/man-pages/man1/bash.1.html
  answers:: 只有「反斜杠紧跟换行」才是续行；`\` 后跟注释会断句，后续行各自成命令
  authority:: 高
  verified:: 2026-09-13

- 来源:: LLaMA-Factory 官方文档站（readthedocs）
  use_when:: 查 LLaMA-Factory 的训练阶段与配置（原 docs.llamafactory.online 域名证书过期，属死链）
  url:: https://llamafactory.readthedocs.io/zh-cn/latest/
  answers:: 数据准备、训练配置等官方文档；实测 HTTP 200
  authority:: 高
  verified:: 2026-09-13

- 来源:: Argilla
  use_when:: 需要可自建的偏好对标注/质检工具（课程内 labeler 无法核实）
  url:: https://argilla.io
  answers:: 开源数据标注与偏好排序平台
  authority:: 中
  verified:: 2026-09-13

- 来源:: Label Studio
  use_when:: 需要通用开源标注工具做偏好对与人工质检
  url:: https://labelstud.io
  answers:: 多模态标注平台，可替代课程内 labeler
  authority:: 中
  verified:: 2026-09-13

## B2 复核新增（2026-09-13）：Prompt / Function Calling / 上下文工程

> 本次回写实际打开并逐字核对的一手来源（官方工程博客 / 一手论文 / 官方仓库与规格生成的 SDK 文档）；`use_when` 写「什么时候要回查」。

- 来源:: Anthropic — Effective context engineering for AI agents
  use_when:: 引用「注意力预算 / 有限资源」「n² 成对关系」「渐变而非断崖」，或压缩 / 结构化笔记的官方口径时回到原文
  url:: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
  answers:: attention budget 与 finite resource 原文；performance gradient rather than a hard cliff；compaction 定义与「先最大化召回、再提精确率」；子 Agent 回传 often 1,000-2,000 tokens；just-in-time 轻量标识符；structured note-taking 与压缩并列
  authority:: 高
  verified:: 2026-09-13

- 来源:: Chroma 技术报告 — Context Rot
  use_when:: 需要 Context Rot 的准确定义与实测曲线（而非「轨迹垃圾堆积」的误用）时
  url:: https://www.trychroma.com/research/context-rot
  answers:: Context Rot = 输入 token 增长导致**召回能力**下降（2025-07-14）；18 个模型实测；Impact of Distractors 专节；注意力层面机制被正文明确列为范围之外
  authority:: 高
  verified:: 2026-09-13

- 来源:: Simon Willison — How to fix your context
  use_when:: 要把「轨迹里过期 / 矛盾 / 自我引用内容堆积」归到正确术语（Poisoning / Distraction / Confusion / Clash）时
  url:: https://simonwillison.net/2025/Jun/29/how-to-fix-your-context/
  answers:: 逐条转述 Drew Breunig《How Long Contexts Fail》(2025-06-22) 的四类失效模式
  authority:: 中
  verified:: 2026-09-13

- 来源:: Addy Osmani — Loop Engineering / Practical Loop Engineering
  use_when:: 核对「五件套」构成、第六件 memory、harness engineering 归属、作者头衔时
  url:: https://addyosmani.com/blog/loop-engineering/
  answers:: 五件套 = Automations / Worktrees / Skills / Plugins and connectors / Sub-agents，第六件 = memory；"Loop engineering sits one floor above the harness."；token 成本警告；后续定义见 https://addyosmani.com/blog/practical-loop-engineering/ ；"Viv Trivedy coined the term harness engineering" 见 https://addyosmani.com/blog/agent-harness-engineering/
  authority:: 高
  verified:: 2026-09-13

- 来源:: Anthropic Claude Code — CHANGELOG 与 Release API
  use_when:: 核对 `/loop`、`/goal`、`/proactive` 的上线版本与自定节奏的官方措辞
  url:: https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
  answers:: `/loop` = v2.1.71（2026-03-07 UTC）；`/goal` = v2.1.139（2026-05-11 UTC）；"self-paced dynamic mode"（2.1.248）；`/usage` Loops 面板（2.1.243）；远程会话不再推广 `/loop`（2.1.172）；`/proactive` 别名（2.1.105）；Release 正文见 https://api.github.com/repos/anthropics/claude-code/releases/tags/v2.1.71 与 https://api.github.com/repos/anthropics/claude-code/releases/tags/v2.1.139
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — scheduled-tasks / goal
  use_when:: 引用循环任务的会话级生命周期，或「/loop 不能替代 cron」的边界时
  url:: https://code.claude.com/docs/en/scheduled-tasks.md
  answers:: 会话级（新会话即停、关终端即停）、7 天过期、Esc 清 pending wakeup、self-paced 在 resume 不恢复；Routines / Desktop scheduled tasks / GitHub Actions 的分工；`/goal` 由小模型判定完成 https://code.claude.com/docs/en/goal.md
  authority:: 高
  verified:: 2026-09-13

- 来源:: OpenAI openai-python 类型规格（由 OpenAPI 规格生成，含当期文档地址）
  use_when:: 核对 `strict` / `tool_choice` / `temperature` 的字段语义与条件默认值，或确认 OpenAI 文档主域迁移
  url:: https://raw.githubusercontent.com/openai/openai-python/main/src/openai/types/shared_params/function_definition.py
  answers:: strict 定义（默认 false、只支持 JSON Schema 子集）与 developers.openai.com 指南地址；tool_choice 四形态与条件默认值 https://raw.githubusercontent.com/openai/openai-python/main/src/openai/types/chat/completion_create_params.py ；「强制指定某一个函数」形态 https://raw.githubusercontent.com/openai/openai-python/main/src/openai/types/chat/chat_completion_named_tool_choice_param.py ；temperature 0–2 与「higher 更随机 / lower 更确定」描述
  authority:: 高
  verified:: 2026-09-13

- 来源:: 推理技法原始论文（NeurIPS 2022 / ACL 2022）
  use_when:: 引用 CoT 的规模边界、zero-shot CoT 触发词、示例顺序敏感性时回到论文
  url:: https://proceedings.neurips.cc/paper_files/paper/2022/hash/9d5609613524ecf4f15af0f7b31abca4-Abstract-Conference.html
  answers:: Wei et al. CoT（"emerge naturally in sufficiently large language models"）；Kojima et al. zero-shot CoT https://nips.cc/virtual/2022/poster/54287 （MultiArith 17.7%→78.7%、GSM8K 10.4%→40.7%，text-davinci-002）；Lu et al. 示例顺序敏感 https://aclanthology.org/2022.acl-long.556/
  authority:: 高
  verified:: 2026-09-13

- 来源:: 智谱 GLM 官方模型文档
  use_when:: 核对 GLM 系列的当期模型名单（避免继续以 GLM-4-Flash 作对照基线）
  url:: https://docs.bigmodel.cn/cn/guide/models/text/glm-4
  answers:: GLM-4 系列 = Plus / Air-250414 / AirX / FlashX-250414 / Flash-250414（无独立 GLM-4-Flash）；当期主力 GLM-5.3 / GLM-5.3-Flash / GLM-5.2 见 https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3
  authority:: 高
  verified:: 2026-09-13

## B1 复核新增（2026-09-13）：LLM 理论笔记与推理工程数值纠错

> 本次回写（[[AI大模型开发]] 的位置编码 / 残差 / 激活函数纠错，[[LLM推理部署与量化]] 的显存预算与多机拓扑纠错）实际抓取并核对的一手来源（官方文档 / 官方仓库源码）；`use_when` 写「什么时候要回查」。

- 来源:: PyTorch — torch.nn.SiLU
  use_when:: 要确认 SiLU/Swish 的值域与单调性（写激活函数、门控机制说明时）
  url:: https://docs.pytorch.org/docs/2.14/generated/torch.nn.SiLU.html
  answers:: SiLU(x)=x·σ(x) 的定义；据此纠正「SiLU 输出在 0~1」（被压到 0~1 的是 σ(x)，SiLU 值域 [-0.2785, +∞)）
  authority:: 高
  verified:: 2026-09-13

- 来源:: PyTorch — torch.nn.RMSNorm
  use_when:: 要写现代 LLM 的归一化选型（LayerNorm vs RMSNorm）或确认 RMSNorm 已是框架内置算子
  url:: https://docs.pytorch.org/docs/2.14/generated/torch.nn.RMSNorm.html
  answers:: RMSNorm 公式（按均方根缩放、无均值中心化与 β）与 PyTorch 内置事实；LLaMA/Qwen/Gemma 默认归一化的旁证
  authority:: 高
  verified:: 2026-09-13

- 来源:: torchtitan — feed_forward.py（compute_ffn_hidden_dim）
  use_when:: 要确认 SwiGLU 中间维为什么取 8d/3（"参数量多 50%" 的前提与取舍）
  url:: https://raw.githubusercontent.com/pytorch/torchtitan/main/torchtitan/models/common/feed_forward.py
  answers:: Llama3/4 系 hidden_dim = int(2*4*dim/3)，docstring 明写 "applies the 2/3 scaling"：3·d·(8d/3)=8d² 与 ReLU-4d 持平
  authority:: 高
  verified:: 2026-09-13

- 来源:: zubnet.ai wiki — SwiGLU
  use_when:: 要 8d/3 取舍的第二处旁证（非官方，仅作交叉印证）
  url:: https://zubnet.ai/wiki/en/SwiGLU/
  answers:: "To keep parameter count constant, the intermediate dimension is typically reduced from 4×model_dim to (8/3)×model_dim"
  authority:: 中
  verified:: 2026-09-13

- 来源:: EleutherAI — Rotary Embeddings: A Relative Revolution
  use_when:: 要解释 RoPE 的相对位置性质、以及"朴素 RoPE 不能直接外推"的边界（PI / NTK / YaRN）
  url:: https://blog.eleuther.ai/rotary-embeddings/
  answers:: RoPE 定义（统一绝对与相对位置编码）、无位置参数、训练长度外的性能取决于外推方案
  authority:: 高
  verified:: 2026-09-13

- 来源:: vLLM 官方文档 — Engine Arguments（现路径）
  use_when:: 查 vLLM 参数默认值与 KV/显存预算相关参数，或复核旧链接是否失效
  url:: https://docs.vllm.ai/en/latest/configuration/engine_args/
  answers:: gpu_memory_utilization / max_model_len / swap_space 等参数口径；原 /models/engine_args.html 已 404（Engine Arguments 页迁至 /configuration/）
  authority:: 高
  verified:: 2026-09-13

- 来源:: vLLM 官方文档 — Automatic Prefix Caching（现路径）
  use_when:: 查前缀缓存机制，或复核旧链接是否失效
  url:: https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/
  answers:: 前缀缓存文档的现行路径；原 /design/automatic_prefix_caching.html 已被重定向到 /contributing/
  authority:: 高
  verified:: 2026-09-13

- 来源:: vLLM 源码 — config/parallel.py（ParallelConfig）
  use_when:: 要判断多机多卡拓扑是否自洽（worker 数怎么算、TP×PP 与每机卡数的关系）
  url:: https://raw.githubusercontent.com/vllm-project/vllm/main/vllm/config/parallel.py
  answers:: world_size = TP × PP 且决定 worker 数量；据此纠正「2 机 × 1 卡 + TP=2 + PP=2」装不下 4 个 worker
  authority:: 高
  verified:: 2026-09-13

- 来源:: vLLM 论坛 — gpu_memory_utilization 包含哪些部分
  use_when:: 估算并发容量时确认 KV Cache 是否算在 gpu_memory_utilization 之内
  url:: https://discuss.vllm.ai/t/what-does-gpu-memory-utilisation-include/1651
  answers:: 0.9 的预算是权重 + 激活 + KV cache 合计；剩余 10% 留给 CUDA graphs / kernels / fragmentation 等开销
  authority:: 中
  verified:: 2026-09-13

- 来源:: Ollama 源码 — envconfig/config.go
  use_when:: 要确认 OLLAMA_SCHED_SPREAD / OLLAMA_NUM_PARALLEL / num_gpu 各自的官方语义（多卡调度易混）
  url:: https://raw.githubusercontent.com/ollama/ollama/main/envconfig/config.go
  answers:: SchedSpread = "Always schedule model across all GPUs"（把模型摊到所有 GPU，非请求级轮询）；OLLAMA_NUM_PARALLEL = "Maximum number of parallel requests"（默认 1）
  authority:: 高
  verified:: 2026-09-13

- 来源:: vLLM 官方博客
  use_when:: 要引用 vLLM 官方发布/测评口径（如 PagedAttention 吞吐倍数），或区分官方口径与第三方个人博客
  url:: https://vllm.ai/blog
  answers:: 官方博客入口（tildalice.io 那篇 24× 文章不在此列，属个人站点）
  authority:: 高
  verified:: 2026-09-13

## A3 复核新增（2026-09-13）：Claude Code 官方文档（记忆 / hooks / 权限 / 会话 / 调度）

> 本簇（claude-ops 架构模式与无人值守）回写时实际打开并逐条核对的官方文档；`use_when` 写「什么时候要回查」。

- 来源:: Claude Code 官方文档 — Memory（CLAUDE.md 与 auto memory）
  use_when:: 回答「压缩后什么会重载」「auto memory 截断规则」「子代理能否持久记忆」「知识库注入算不算硬约束」
  url:: https://code.claude.com/docs/en/memory.md
  answers:: CLAUDE.md 层级（企业/用户/项目/子目录）启动即载入、**项目根 CLAUDE.md 在 `/compact` 后从磁盘重读并重新注入**；auto memory 每次启动仅载入 `MEMORY.md` **前 200 行或 25KB**、超限写入报错要求重写索引；`/memory` 打开、`/context` 看占用；子代理须加 `memory` 字段才有独立持久记忆；**「context 不是 enforced configuration，要无条件阻止某动作请用 PreToolUse hook」**
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — Hooks 参考
  use_when:: 判断某事件能否**阻断**工具调用/停止，或找「框架层注入、不靠模型自觉」的原生落点
  url:: https://code.claude.com/docs/en/hooks.md
  answers:: Exit code 2 表——`PreToolUse` 阻断该次工具调用、`UserPromptSubmit` 阻断并擦除 prompt、`Stop` 阻止停止并继续对话；**`PermissionRequest` 不采纳 exit 2**（须用 decision 对象显式 deny）；`UserPromptSubmit` 的纯文本 stdout 作为 Claude 可见上下文注入；`SubagentStart`/`SubagentStop` 输入含 `agent_id`/`agent_type`；`TeammateIdle` 空闲事件；hooks 可绑定到 skill/agent 内部
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — Skills
  use_when:: 写 SKILL.md 前确认 frontmatter 契约与调用控制字段
  url:: https://code.claude.com/docs/en/skills.md
  answers:: SKILL.md = YAML frontmatter + 正文渐进披露（正文仅在被使用时载入）；`disable-model-invocation: true`（禁止自动加载、只能人工 `/name`）、`user-invocable: false`（人不可调、模型仍可调）、`allowed-tools`（该轮免逐次审批、**下一条消息后授权清除**）；`skillOverrides` 可在不改文件时控制可见性；自定义命令已并入 skills（`.claude/commands/x.md` 等价 `.claude/skills/x/SKILL.md`）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 上下文窗口分解
  use_when:: 给 system prompt / memory 估 token 预算时（别再写死「≤2k」）
  url:: https://code.claude.com/docs/en/context-window.md
  answers:: 页面自述**代表值**：系统提示词约 4,200 token、auto memory（MEMORY.md）约 680、环境信息约 280、MCP 工具（延迟加载 schema、仅列名）约 120；并提示用 `/context` 查看本人会话的真实分解
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 权限规则语法
  use_when:: 写 allow/deny 规则、排查「规则写了却不生效」或推送被 scope 拦下
  url:: https://code.claude.com/docs/en/permissions.md
  answers:: `Tool(param:value)` 参数匹配**仅用于 deny/ask**，allow 继续用各工具自己的 specifier 语法；不允许对 `command`/`file_path` 做主内容字段匹配（`Bash(command:rm *)` 被忽略并告警）；`*` 匹配任意文本、**无 `*` 要求完全相等**、`*` 在子命令前会告警；Bash 规则是**字面前缀**（`git -C . push` 不被 `Bash(git push *)` 覆盖）；`--bare` 不读 hooks/skills/自定义命令/子代理/插件
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 权限模式
  use_when:: 给无人值守任务选档位，或核对各模式的放行范围
  url:: https://code.claude.com/docs/en/permission-modes.md
  answers:: 六种、配置值 camelCase——`default`（CLI/扩展显示为 Manual）/`acceptEdits`/`plan`/**`auto`**/**`dontAsk`**/`bypassPermissions`；`auto` 由第二个模型（classifier）逐条审动作，是官方长任务推荐档、Pro/Max/Team 默认起始模式；`acceptEdits` = 读 + 文件编辑 + 常见文件系统命令（mkdir/touch/mv/cp），**网络不自动放行**；`dontAsk` 只放行预批准工具、其余直接拒；关键路径删除（含命令替换写法）在所有模式下由 CLI 自身无条件拒绝
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 会话与 transcript
  use_when:: 找会话文件位置、写恢复脚本，或核对环境变量的读取时机
  url:: https://code.claude.com/docs/en/sessions.md
  answers:: transcript 默认 JSONL 存于 `~/.claude/projects/<project>/<session-id>.jsonl`，`<project>` 由工作目录路径**把非字母数字替换为 `-`** 得到（>200 字符截断并追加完整路径哈希）；恢复用 `claude --resume`（选择器）/ `--resume <session-id>` / **直接传 transcript 绝对路径**；环境变量（如 `ANTHROPIC_BASE_URL`）**仅在进程启动时读取一次**（改 rc 文件须重启会话）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 定时任务
  use_when:: 设计无人值守调度时核对任务生命周期、恢复语义与触发漂移
  url:: https://code.claude.com/docs/en/scheduled-tasks.md
  answers:: 底层为 `CronCreate`/`CronList`/`CronDelete`（**无 `/cron` 斜杠命令**）；仅在 Claude Code 运行且空闲时触发；**新开对话清空会话级任务**，`--resume`/`--continue` 会恢复 CronCreate 任务（过期 recurring 与过时一次性除外，自定步长 `/loop` 不恢复）；recurring **7 天过期**；单会话 ≤**50** 个；确定性 jitter（recurring 最多晚 30 分钟或半间隔、整点/半点一次性最多提前 90 秒）；Cloud Routines / Desktop scheduled tasks / `/loop` 对照表与 Channels 事件驱动
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 命令表
  use_when:: 确认某个斜杠命令到底存不存在（例：并没有 `/cron`）
  url:: https://code.claude.com/docs/en/commands.md
  answers:: 官方斜杠命令清单及定位（`/memory`、`/context`、`/background`、`/tasks`、`/loop` 等）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 子代理
  use_when:: 查子代理嵌套层级、并发上限与 fork 式子任务所需版本
  url:: https://code.claude.com/docs/en/sub-agents.md
  answers:: 默认允许再生成子代理（最多三层）；`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` 默认 **20**，超限报 `Concurrent subagent limit reached`（需 ≥ v2.1.217）；fork 式 `/subtask` 需 ≥ v2.1.212
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — Agent view（后台会话监控）
  use_when:: 设计不依赖 daemon 的保活方案，或回答「机器重启后会话怎么办」
  url:: https://code.claude.com/docs/en/agent-view.md
  answers:: `/background` 把会话脱离终端；`claude agents` 按 **Needs input / Working / Completed** 分组监控并可 attach 进去回复；重启后 **48 小时内**会话显示 `failed`、attach 或回复即**从断点续跑**，**超过 48 小时**显示 `stopped`、可 `claude attach <id>` 恢复；transcript 清理由 `cleanupPeriodDays` 控制
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — Agent teams（实验性）
  use_when:: 需要 teammate 间直接消息与集中管理前，先看实验开关与已知限制
  url:: https://code.claude.com/docs/en/agent-teams.md
  answers:: 需 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`；teammate 间直接消息与集中管理；已知限制——**lead 不可转让**、**teammate 不能起后台子代理**
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 跨会话消息
  use_when:: 要在会话之间传消息而不自建文件邮箱时
  url:: https://code.claude.com/docs/en/cross-session-messaging
  answers:: 会话间直接传消息的机制与适用范围（对应本库「Mailbox 通知」原语的原生实现）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 错误与重试
  use_when:: 设计中继/代理重试策略，或排查 `Connection lost before a response was produced`、502
  url:: https://code.claude.com/docs/en/errors.md
  answers:: 服务端错误/过载/超时只有**在响应开始流出之前**才走完整重试预算；断线若发生在响应尚未产出时（含刚开始流式输出文本）会**重发同一请求**；若在思考完成之后、文本或工具调用开始之前，最多**快速重发两次**即结束
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 — 更新日志（changelog）
  use_when:: 核对某版本是否已发布、某机制从哪个版本起可用
  url:: https://code.claude.com/docs/en/changelog.md
  answers:: **2026-09-12 发布 v2.1.270**（2.1.269 为 09-11）；`cc-daemon-*` 临时目录残留修复、daemon lock file 指向被复用 pid 的修复、background daemon start 等条目
  authority:: 高
  verified:: 2026-09-13

## A4 复核新增（2026-09-13）：cs-base 系统 / 网络 / 数据库（官方文档）

> 本簇（操作系统 / 组成原理 / 计算机网络 / 高并发 / 网络编程 / 数据库 / Redis / Raft / 容器 / LLVM / LibC）回写时逐字核对的一手来源；`use_when` 写「什么时候要回查」。

- 来源:: Linux 内核 EEVDF 调度器文档
  use_when:: 核对 EEVDF（6.6+ 内核过渡）的 eligible / 虚拟截止期 / lag decay 规则与 CFS 的关系
  url:: https://docs.kernel.org/scheduler/sched-eevdf.html
  answers:: 过渡起点、lag≥0 筛 eligible、取 VD 最早者、睡眠任务 lag decay 防套利、sched_setattr 申请时间片
  authority:: 高
  verified:: 2026-09-13

- 来源:: Linux 内核 CFS 调度器文档
  use_when:: 核对 CFS 记账口径与"CFS 正在让位 EEVDF"的官方表述
  url:: https://docs.kernel.org/scheduler/sched-design-CFS.html
  answers:: 纳秒级记账、不依赖 jiffies/HZ、"has no notion of timeslices"、唯一中央旋钮 base_slice_ns
  authority:: 高
  verified:: 2026-09-13

- 来源:: Linux 内核 PSI（Pressure Stall Information）文档
  use_when:: 判断"快 OOM / 快被内存拖死"，或给 cgroup 做压力阈值告警
  url:: https://docs.kernel.org/accounting/psi.html
  answers:: /proc/pressure/{cpu,memory,io} 的 some/full 语义、avg10/60/300 与 total、cgroup2 每层 pressure 文件、写阈值 + poll()+POLLPRI 等待
  authority:: 高
  verified:: 2026-09-13

- 来源:: Linux 内核 PTI（页表隔离）文档
  use_when:: 核对 Meltdown/PTI 缓解机制，以及 PCID/INVPCID 与 global page 的性能含义
  url:: https://docs.kernel.org/arch/x86/pti.html
  answers:: PCID 免整表 TLB 刷新、INVPCID 只失效非当前 PCID、global page 禁用开销「never exceeding 1%」、entry_64.S 中页表切换与 PCID 配合
  authority:: 高
  verified:: 2026-09-13

- 来源:: epoll_ctl(2) man 手册
  use_when:: 写 epoll 代码或排查 EINVAL、惊群、EPOLLRDHUP/EPOLLHUP 处理
  url:: https://man7.org/linux/man-pages/man2/epoll_ctl.2.html
  answers:: EPOLLEXCLUSIVE（4.5+）四条使用契约（仅 ADD 可用 / MOD 报错 / 混标志 EINVAL / 目标为 epoll 实例 EINVAL）、EPOLLRDHUP（2.6.17）、EPOLLERR|EPOLLHUP 必返回
  authority:: 高
  verified:: 2026-09-13

- 来源:: io_uring_setup(2) man 手册
  use_when:: 确认某项 io_uring 能力（尤其 SQPOLL）的最低内核版本
  url:: https://man7.org/linux/man-pages/man2/io_uring_setup.2.html
  answers:: 各 flag 的 Available since 标注（5.10/5.11/5.13/5.18/5.19/6.18）；SQPOLL 5.11 起免注册文件、5.11 非 root 需 CAP_SYS_NICE、5.13 放宽；能力位 IORING_FEAT_SQPOLL_NONFIXED
  authority:: 高
  verified:: 2026-09-13

- 来源:: io_uring(7) man 手册
  use_when:: 查 io_uring 的环结构、注册接口与整体语义
  url:: https://man7.org/linux/man-pages/man7/io_uring.7.html
  answers:: SQ/CQ 环、sqe/cqe、注册与能力位总览
  authority:: 高
  verified:: 2026-09-13

- 来源:: Linux 内核 arch/x86/boot/a20.c（GitHub 镜像）
  use_when:: 写引导代码要开 A20，或核对三种开法的实现顺序与自证方式
  url:: https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/boot/a20.c
  answers:: BIOS 法 0x2401、键盘控制器法 0xd1/0xdf + empty_8042、Fast A20 0x92（注释「Do not reset machine」）、a20_test_short 回环自证、A20_ENABLE_LOOPS=255。注：git.kernel.org 的 /tree/ 与 /plain/ 链接会返回 Anubis 反爬挑战页
  authority:: 高
  verified:: 2026-09-13

- 来源:: Linux 内核 vgacon.c（GitHub 镜像）
  use_when:: 核对 VGA 文本缓冲基址（彩色 0xB8000 / 单色 0xB0000）
  url:: https://raw.githubusercontent.com/torvalds/linux/master/drivers/video/console/vgacon.c
  answers:: vga_vram_base = 0xb8000；模式 7 单色分支 0xb0000
  authority:: 高
  verified:: 2026-09-13

- 来源:: nginx CHANGES
  use_when:: 核对某版本移除/变更了哪个特性（如 HTTP/2 server push）
  url:: https://nginx.org/en/CHANGES
  answers:: 1.25.1（2023-06-13）移除 HTTP/2 server push 与 http2_push 指令族
  authority:: 高
  verified:: 2026-09-13

- 来源:: tcp(7) man 手册
  use_when:: 排查 Nagle × 延迟 ACK，确认 TCP_NODELAY / TCP_QUICKACK 语义
  url:: https://man7.org/linux/man-pages/man7/tcp.7.html
  answers:: TCP_QUICKACK（2.4.4+）非永久、会被后续 TCP 处理重置；TCP_NODELAY
  authority:: 高
  verified:: 2026-09-13

- 来源:: RFC 9112（HTTP/1.1）
  use_when:: 判定 HTTP/1.1 某行为"是否仍合法"（如管线化）
  url:: https://www.rfc-editor.org/rfc/rfc9112.html
  answers:: §9.3.2 Pipelining 仍定义客户端 MAY pipeline、服务端 MAY 按序处理；STD 99，Obsoletes 7230，June 2022
  authority:: 高
  verified:: 2026-09-13

- 来源:: nginx ngx_http_limit_req_module 文档
  use_when:: 配置/排查限流，确认漏桶语义、zone 容量与观测变量
  url:: https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
  answers:: 漏桶实现；1MB zone ≈ 16k 个 64B 或 8k 个 128B 状态；zone 满按 LRU 淘汰、再建不了则终止请求；$limit_req_status 五态（1.17.6+）、limit_req_dry_run（1.17.1+）
  authority:: 高
  verified:: 2026-09-13

- 来源:: RFC 9562（UUID）
  use_when:: 设计分布式 ID 时确认 UUIDv7 的标准出处与位布局
  url:: https://www.rfc-editor.org/rfc/rfc9562.html
  answers:: Standards Track（2024-05）、Obsoletes 4122；v7 = 48 位毫秒时间戳 + 4 位版本 + 随机位；v6/v8 的存在
  authority:: 高
  verified:: 2026-09-13

- 来源:: DPDK System Requirements
  use_when:: 部署 DPDK 前确认 BIOS / 大页 / NUMA 前置条件
  url:: https://doc.dpdk.org/guides/linux_gsg/sys_reqs.html
  answers:: BIOS 设置前提；hugepage 为 packet buffer 硬需求、64 位推荐 1GB 页、mount -t hugetlbfs、fstab 持久化；双路 NUMA 均分；in-memory 模式免配置
  authority:: 高
  verified:: 2026-09-13

- 来源:: makecontext(3) man 手册
  use_when:: 实现有栈协程时核对 ucontext 系 API 的族属与语义
  url:: https://man7.org/linux/man-pages/man3/makecontext.3.html
  answers:: makecontext/swapcontext 属 System V ucontext 系（libc 提供）
  authority:: 高
  verified:: 2026-09-13

- 来源:: getcontext(3) man 手册
  use_when:: 确认协程切换到底保存了什么（是否含信号掩码）
  url:: https://man7.org/linux/man-pages/man3/getcontext.3.html
  answers:: ucontext_t 含 uc_link / uc_sigmask / uc_stack / uc_mcontext——信号掩码也在保存恢复之列
  authority:: 高
  verified:: 2026-09-13

- 来源:: SQLite FTS5 官方文档
  use_when:: 设计全文检索时选分词器，或区分 external content / contentless 表
  url:: https://sqlite.org/fts5.html
  answers:: 4.3.1 unicode61（默认，Unicode 6.1）/ 4.3.3 porter / 4.3.4 trigram；4.4.3 External Content Table 与 4.4.1 Contentless Table 的区别（后者不能读列值，4.4.2 另有 contentless-delete）
  authority:: 高
  verified:: 2026-09-13

- 来源:: SQLite WAL 官方文档
  use_when:: 论证 WAL 的持久性/损坏风险，或确认 WAL 的前置条件
  url:: https://sqlite.org/wal.html
  answers:: §11 The WAL-Reset Bug（3.7.0–3.51.2 受影响，3.51.3 修复，3.44.6/3.50.7 回移）；VFS 共享内存要求（xShmMap/xShmLock/xShmBarrier/xShmUnmap）与 locking_mode=EXCLUSIVE 降级
  authority:: 高
  verified:: 2026-09-13

- 来源:: Redis 持久化官方文档
  use_when:: 设计 RDB/AOF/混合持久化，或写 AOF 备份 SOP
  url:: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
  answers:: 7.0 起多部分 AOF（base 文件 + 增量文件、appenddirname、manifest）；重写进行中直接拷贝会得到无效备份及正确备份步骤（停 auto-aof-rewrite → 确认 aof_rewrite_in_progress=0 → 复制目录 → 恢复配置）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Redis 8.0 GA 官方博文
  use_when:: 确认 Redis 最新版本口径、新数据结构与支持策略
  url:: https://redis.io/blog/redis-8-ga.md
  answers:: 2025-05-01 GA；更名 Redis Open Source（AGPLv3）；新增 8 种数据结构（vector set / JSON / time series + Bloom / cuckoo / count-min sketch / top-k / t-digest）；30+ 性能改进；Redis Stack 6.2/7.2/7.4 补丁 2025-09-15 停止
  authority:: 高
  verified:: 2026-09-13

- 来源:: TiKV Multi-Raft 深入解析
  use_when:: 核对 TiKV 的共识分片形态（per-Region Multi-Raft）
  url:: https://tikv.org/deep-dive/scalability/multi-raft/
  answers:: 「Here Multi-Raft only means we manage multiple Raft consensus groups on one node」；按 Region 切分且 Region 可 split/merge
  authority:: 高
  verified:: 2026-09-13

- 来源:: Apache Kafka 4.0.0 发布公告
  use_when:: 核对 KRaft 现状、Pre-Vote（KIP-996）与 ZooKeeper 移除
  url:: https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/
  answers:: 4.0 起以 KRaft 模式运行、为首个完全不需要 ZooKeeper 的大版本；KIP-996 Pre-Vote 减少不必要的 KRaft leader 选举
  authority:: 高
  verified:: 2026-09-13

- 来源:: Docker 多阶段构建官方文档
  use_when:: 写 Dockerfile 多阶段构建，或排查阶段/产物拷贝问题
  url:: https://docs.docker.com/build/building/multi-stage/
  answers:: 每个阶段必须以 FROM … AS <stage> 开头；阶段命名与 COPY --from
  authority:: 高
  verified:: 2026-09-13

- 来源:: namespaces(7) man 手册
  use_when:: 核对 Linux namespace 种类、内核版本与 /proc 呈现
  url:: https://man7.org/linux/man-pages/man7/namespaces.7.html
  answers:: cgroup（CLONE_NEWCGROUP，/proc/pid/ns/cgroup，4.6）、time（CLONE_NEWTIME，5.6；time_for_children 5.6、max_time_namespaces 5.7）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Linux 内核 overlayfs 文档
  use_when:: 解释容器"写时复制"的真实粒度与性能含义
  url:: https://docs.kernel.org/filesystems/overlayfs.html
  answers:: 文件级 copy-up（含父目录）；未显式 fsync 时崩溃可留下全零上层文件，故 rename(2)/link(2) 完成 copy up 前会 fsync；metacopy 只先拷元数据
  authority:: 高
  verified:: 2026-09-13

- 来源:: Linux 内核 cgroup v2 文档
  use_when:: 核对 cgroup v2 层级约束、memory.oom.group 与控制器文件
  url:: https://docs.kernel.org/admin-guide/cgroup-v2.html
  answers:: no internal process 约束与 threaded subtree；memory.oom.group 语义；cgroup 内触发 OOM killer 不会杀到该 cgroup 之外
  authority:: 高
  verified:: 2026-09-13

- 来源:: Clang 14.0.0 Release Notes
  use_when:: 确认 DWARF 默认版本变更与退回开关
  url:: https://releases.llvm.org/14.0.0/tools/clang/docs/ReleaseNotes.html
  answers:: 默认 DWARF 版本 v4→v5；-gdwarf-4 / -fdebug-default-version=4 退回；Darwin/Android/SCE opt out
  authority:: 高
  verified:: 2026-09-13

- 来源:: LLVM Opaque Pointers 文档
  use_when:: 读新旧 LLVM IR 时解释 ptr 与类型化指针的差异
  url:: https://llvm.org/docs/OpaquePointers.html
  answers:: LLVM 15 默认开启不透明指针、16 best-effort、17 仅支持不透明指针；LLVMGetElementType() 等 API 移除
  authority:: 高
  verified:: 2026-09-13

- 来源:: Clang HWASan 设计文档
  use_when:: 选型内存安全工具，或核对 HWASan 的硬件依赖与影子内存比例
  url:: https://clang.llvm.org/docs/HardwareAssistedAddressSanitizerDesign.html
  answers:: 对象按 TG 对齐、指针 TS 位 tag、TG=>1 影子内存；AArch64 Address Tagging；x86_64 用页别名且 Currently only heap tagging is supported
  authority:: 高
  verified:: 2026-09-13

- 来源:: glibc NEWS（glibc-cvs 归档，2.34 库合并）
  use_when:: 解释 glibc 2.34 之后 -lpthread/-ldl 为何不再必要，以及旧的空 .so 行为
  url:: https://sourceware.org/pipermail/glibc-cvs/2021q3/073885.html
  answers:: libpthread/libdl/libutil/libanl 功能并入 libc；提供空的兼容 .a；2.33 及更早链接的程序仍会加载空 .so、preload libpthread.so.0 时弱引用风险
  authority:: 高
  verified:: 2026-09-13

- 来源:: musl time64 说明
  use_when:: 核对 32 位平台 2038 问题的时间64位化分界点
  url:: https://musl.libc.org/time64.html
  answers:: musl 1.2.0 起全架构 time_t 为 64 位；time32↔time64 翻译与库间 time_t 定义不一致的 ABI 错配风险
  authority:: 高
  verified:: 2026-09-13

- 来源:: GCC Link Options 手册
  use_when:: 确认 PIE / 静态 PIE 的链接开关与配套编译选项
  url:: https://gcc.gnu.org/onlinedocs/gcc/Link-Options.html
  answers:: -static-pie / --static-pie 语义（无需动态链接器即可加载到任意地址）与需同用 -fpie/-fPIE 的要求
  authority:: 高
  verified:: 2026-09-13

## B4 复核新增（2026-09-13）：Agent / MCP / A2A / LangGraph

> 本次回写（[[MCP协议开发实战]] / [[A2A多智能体协作协议]] / [[LangChain-LangGraph框架实战]] / [[LLM-Agent开发基础]]）实际打开并逐条核对的**官方**来源（规范页 / 官方仓库 / PyPI / 官方文档站）；`use_when` 写「什么时候要回查」。与 B6 已登记的 MCP 条目互补，不重复。

- 来源:: MCP 规范 · 版本与协商规则（versioning）
  use_when:: 判断「MCP 该按哪一版写」——当前修订是什么、握手式流程还能不能用
  url:: https://modelcontextprotocol.io/docs/learn/versioning.md
  answers:: Current = **2026-07-28**；2026-07-28 自述「since the previous revision, 2025-11-25」，2025-11-25 自述「since the previous revision, 2025-06-18」（故本库原登记的 2025-06-18 落后两个修订，而非三个）；`initialize` 握手仅适用 2025-11-25 及更早，属向后兼容路径
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP 规范 2026-07-28 · Transports 总览
  use_when:: 回答「MCP 到底有几种传输」——SSE 还算不算标准绑定
  url:: https://modelcontextprotocol.io/specification/2026-07-28/basic/transports.md
  answers:: 只列 **stdio** 与 **Streamable HTTP** 两个标准绑定；SSE 不在其列（弃用登记见 B6 的 deprecated 条目）；另移除 Streamable HTTP 的协议级会话与 `Mcp-Session-Id` 头
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP 规范 2025-11-25 · 变更日志
  use_when:: 核对「客户端侧能力」是哪个修订引入的（写 Server/Client 三资产对照时）
  url:: https://modelcontextprotocol.io/specification/2025-11-25/changelog.md
  answers:: URL 模式 elicitation、sampling 的 `tools` / `toolChoice`、`ElicitResult` / `EnumSchema` 扩展均在 2025-11-25 引入；Default JSON Schema dialect 为 2020-12
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP Python SDK v2 README（含 FastMCP 归属证据）
  use_when:: 判断某段 MCP 代码是 v1 还是 v2 写法，或回答「fastmcp 是不是官方包」
  url:: https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md
  answers:: 横幅「This is v2 of the MCP Python SDK, the current stable release line」「pip install mcp now installs 2.x」；v1.x 留在 v1.x 分支仅收关键修复与安全补丁，官方建议未迁移前锁 `mcp>=1.28,<2`；v2 一等公民 Client `async with Client("http://localhost:8000/mcp") as client`。**FastMCP 非官方**：README 署名 Made with 💙 by Prefect，文档站 gofastmcp.com，升级指南已到「Upgrading from FastMCP 3」→ <https://raw.githubusercontent.com/jlowin/fastmcp/main/README.md>
  authority:: 高
  verified:: 2026-09-13

- 来源:: MCP Inspector 官方文档
  use_when:: 调 MCP Server 时选 Inspector 形态，或判断「连不上」是协议纪元问题还是传输问题
  url:: https://modelcontextprotocol.io/docs/tools/inspector
  answers:: 三种客户端——Web（默认 `npx @modelcontextprotocol/inspector`）、CLI（`--cli`，面向 CI / 流水线 / 编码 Agent）、TUI（`--tui`）；并做 legacy 与 modern（2026-07-28）协议纪元协商
  authority:: 高
  verified:: 2026-09-13

- 来源:: A2A 官方 CHANGELOG + IANA well-known URI 登记表
  use_when:: 核对 Agent Card 的发现路径（`agent.json` 还是 `agent-card.json`）
  url:: https://raw.githubusercontent.com/a2aproject/A2A/a554aedbb5be85345ffd838e749e179a3e65ba8b/CHANGELOG.md
  answers:: 0.3.0（2025-07-30）以 ⚠ BREAKING CHANGES 将 URI 由 `agent.json` 改为 `agent-card.json`（#841）；IANA <https://www.iana.org/assignments/well-known-uris/well-known-uris.txt> 确认 `agent-card.json` 为 permanent、Reference 指向 A2A 规范、Change Controller 为 Linux Foundation、登记日 2025-08-01
  authority:: 高
  verified:: 2026-09-13

- 来源:: A2A v1.0 变更说明（what's new）
  use_when:: 写 A2A 调用前核对操作名大小写与 Agent Card 字段结构
  url:: https://a2a-protocol.org/latest/whats-new-v1/
  answers:: v1.0 操作名全部 PascalCase；`tasks/cancel`→`CancelTask`、`tasks/resubscribe`→`SubscribeToTask`；Agent Card 支持 JWS 签名、规范化用 RFC 8785、`protocolVersion` 从顶层下移到各 `AgentInterface`、`preferredTransport`/`additionalInterfaces` 合并为 `supportedInterfaces`、按 `A2A-Version` 头协商
  authority:: 高
  verified:: 2026-09-13

- 来源:: A2A 官方 proto 定义
  use_when:: 需要 A2A RPC 方法或 TaskState 枚举的逐字清单时（不要凭教程记忆）
  url:: https://raw.githubusercontent.com/a2aproject/A2A/main/specification/a2a.proto
  answers:: `package lf.a2a.v1`；`service A2AService` = SendMessage（POST /message:send）/ SendStreamingMessage（POST /message:stream）/ GetTask（GET /tasks/{id}）/ ListTasks / GetExtendedAgentCard / TaskPushNotificationConfig 系列；TaskState 共 9 值（UNSPECIFIED=0 … AUTH_REQUIRED=8）
  authority:: 高
  verified:: 2026-09-13

- 来源:: A2A 官方 Streaming & Asynchronous 主题页
  use_when:: 长任务（分钟～小时级）怎么回传进度、要不要自己造轮询
  url:: https://a2a-protocol.org/latest/topics/streaming-and-async/
  answers:: Push Notification 定位为异步更新通道；配置对象 `TaskPushNotificationConfig`，配套 RPC `CreateTaskPushNotificationConfig`；服务端向客户端 webhook 发 HTTP POST
  authority:: 高
  verified:: 2026-09-13

- 来源:: AAIF — A2A v1.0 Builder's Guide Part 2（迁移、安全与生产化）
  use_when:: 给 A2A 上生产时查推送安全、存储与执行中授权
  url:: https://aaif.io/blog/a2a-v1-0-a-builder-s-guide-part-2-migration-security-and-production
  answers:: In-Task Authorization（`auth-required` 可在执行中打断）；推送要求**至少投递一次**并允许重复 → 接收端必须幂等，token 轮换、常量时间校验、JWT+JWKS 校验 `iss`/`aud`/`iat`/`exp`/`jti` 与 `kid`；默认 TaskStore 为内存实现，改用 `a2a-sdk[postgresql]`（或 `[mysql]`/`[sqlite]`/`[sql]`）+ `DatabaseTaskStore(engine=...)` 并配对 `DatabasePushNotificationConfigStore`
  authority:: 中
  verified:: 2026-09-13

- 来源:: a2a-sdk PyPI JSON 元数据 + 官方 SDK API 文档
  use_when:: 核对 a2a-sdk 最新版本号，或确认 v1 的 client 模块拆分
  url:: https://pypi.org/pypi/a2a-sdk/json
  answers:: 最新发行版 **1.1.2**（2026-07-22T13:40 上传），故笔记里的「1.1.0」既非最新也非精确；v1 client 模块拆为 `a2a.client.client` / `client_factory` / `transports.{jsonrpc,grpc,rest}`，见 <https://a2a-protocol.org/latest/sdk/python/api/a2a.server.agent_execution.agent_executor.html>
  authority:: 高
  verified:: 2026-09-13

- 来源:: langchain-mcp-adapters README + 迁移指南
  use_when:: 判断 LangChain 接 MCP 该用哪个包、`load_mcp_tools(client.session)` 还能不能抄
  url:: https://raw.githubusercontent.com/langchain-ai/langchain-mcp-adapters/main/README.md
  answers:: 横幅逐字「This repository is no longer actively maintained」「MCP support has moved into LangChain under the `langchain.mcp` namespace. Please migrate to `langchain[mcp]`」；现行写法 `tools = await client.get_tools()`，用户侧不再访问 `client.session`；迁移指南 <https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters>
  authority:: 高
  verified:: 2026-09-13

- 来源:: LangChain v1 迁移指南 + v1 Agents 文档
  use_when:: 抄到 `create_tool_calling_agent` / `AgentExecutor` 时判断它还在不在主包
  url:: https://docs.langchain.com/oss/python/migrate/langchain-v1
  answers:: Package namespace reduction——legacy chains / retrievers / indexing / hub 移入 `langchain-classic`（需 `pip install langchain-classic`，改用 `langchain_classic.*`），主包聚焦 agents / messages / tools / chat models / embeddings；v1 唯一 Agent 入口 `from langchain.agents import create_agent`（<https://docs.langchain.com/oss/python/langchain/agents.md>）；`langchain_classic` 下有 `AGENT_DEPRECATION_WARNING`（<https://reference.langchain.com/python/langchain-classic/agents>）。措辞注意：旧导入是「已迁出主包（ImportError 风险）」，非「必然报错」
  authority:: 高
  verified:: 2026-09-13

- 来源:: langgraph-supervisor 迁移指南
  use_when:: 写 Supervisor 多代理前决定「手写 StateGraph 还是用官方预置库」
  url:: https://docs.langchain.com/oss/python/migrate/langgraph-supervisor
  answers:: 官方设有独立迁移指南页（标题 Migrate from langgraph-supervisor），LangChain v1 迁移指南导航把它与 `langchain-mcp-adapters` 并列归入「需迁移的旧方案」；手写 Supervisor 才是当前推荐做法
  authority:: 高
  verified:: 2026-09-13

- 来源:: Ragas 官方指标目录（stable）
  use_when:: 核对 Ragas 指标现行命名，或判断 `ragas.metrics` 导入写法属哪一代
  url:: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
  answers:: `answer_relevancy` 现名为 **Response Relevancy**；指标按 Retrieval Augmented Generation / Nvidia Metrics / Agents 等类别分组，Faithfulness、Context Precision 并列；文档站已有 From v0.1 to v0.2 与 From v0.3 to v0.4 两份迁移指南，v0.1.21 锚点属过期（本轮**未**能确认 `ragas.metrics.collections` 下的小写指标对象写法，勿照抄）
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepSeek 官方计费页 + API 更新日志
  use_when:: 核对 DeepSeek 现役模型名，或判断 `deepseek-chat` / `deepseek-reasoner` 何时停用
  url:: https://api-docs.deepseek.com/quick_start/pricing
  answers:: 计费页现只列两行——`deepseek-flash`（MODEL VERSION `DeepSeek-V4.1-Flash`）与 `deepseek-v4-pro`（`DeepSeek-V4-Pro-0813`），并注明「Use `deepseek-flash` as the model name」，旧名 `deepseek-v4-flash` 对应模型已退役；V4 于 **2026-04-24** 上线、`deepseek-chat`/`deepseek-reasoner` 于 **2026-07-24** 停用（<https://api-docs.deepseek.com/updates>）；`deepseek-flash`（V4.1）发布于 2026-09-10
  authority:: 高
  verified:: 2026-09-13

- 来源:: ReAct 项目主页 + 论文元数据
  use_when:: 引用 ReAct 的提示词结构、原始动作集，或它的失效模式（幻觉 / 错误传播）
  url:: https://react-lm.github.io/
  answers:: ReAct: Synergizing Reasoning and Acting in Language Models（Shunyu Yao 等，2022）；「A ReAct prompt consists of few-shot task-solving trajectories, with human-written text reasoning traces and actions, as well as environment observations」；reason-only 基线「suffers from misinformation as it is not grounded to external environments」；元数据走 Semantic Scholar <https://api.semanticscholar.org/graph/v1/paper/arXiv:2210.03629?fields=title,abstract,year,authors>（arxiv.org 在复核环境不可达）
  authority:: 高
  verified:: 2026-09-13

## A2 复核新增（2026-09-13）：上游 Agent 工具与 AI SDK

> 本次回写实际打开并核对的上游来源（课程页 / 官方文档 / npm registry / GitHub API）；`use_when` 写「什么时候要回查」。

- 来源:: Vercel Academy — Build Your Own AI Coding Agent Harness
  use_when:: 核对课程模块大纲、开篇五痛点原文、技术栈表与 Capstone 口径；或取单课判据
  url:: https://vercel.com/academy/build-ai-agent-harness
  answers:: 11 模块大纲；Tech Stack 逐字（Zod v3 / AI Gateway / Vercel Sandbox / just-bash / Vercel Workflow）；单课页 `/pruning-old-results` 含 Done-When 判据清单与 `npx tsc --noEmit` 门
  authority:: 高
  verified:: 2026-09-13

- 来源:: AI SDK v6 → v7 迁移指南与 npm 版本
  use_when:: 照抄 AI SDK v6 时期教程前，确认破坏性改名与当前版本
  url:: https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0
  answers:: onFinish→onEnd、onStepFinish→onStepEnd、fullStream→stream、experimental_telemetry→telemetry 等 codemod；npm `ai` latest=7.0.99（2026-09-12）见 https://registry.npmjs.org/ai ；`pruneMessages` 参考页在 v7 文档树内 https://ai-sdk.dev/docs/reference/ai-sdk-ui/prune-messages
  authority:: 高
  verified:: 2026-09-13

- 来源:: OpenCode 官方文档（agents / policies / server / cli）
  use_when:: 核对 OpenCode 内置 agent 名册、策略引擎、HTTP 能力面与 CLI 子命令
  url:: https://opencode.ai/docs/agents
  answers:: 内置 8 个（5 可用：build/plan/general/explore/scout；3 隐藏系统 agent：compaction/title/summary）；`experimental.policies` 语义见 https://opencode.ai/docs/policies/ ；`GET /doc` 返回 HTML 页、SSE 首帧 `server.connected` 见 https://opencode.ai/docs/server/ ；CLI 子命令见 https://opencode.ai/docs/cli/
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm `@opencode-ai/sdk` / `@opencode-ai/plugin` 版本线
  use_when:: 对齐 OpenCode 包版本（库内调研报告的版本快照落后时）
  url:: https://registry.npmjs.org/@opencode-ai/sdk
  answers:: latest = 1.18.30，registry time 2026-09-09T03:36:39Z；1.18.23 → 1.18.30 为 7 个 patch
  authority:: 高
  verified:: 2026-09-13

- 来源:: GitHub API — 仓库归属与旧路径重定向
  use_when:: 判定「org 到底是谁的」「旧路径是否只是重定向」这类归属问题，直接用 API 而非二手报道
  url:: https://api.github.com/repos/sst/opencode
  answers:: 301 后 full_name=anomalyco/opencode（repo id 975734319、MIT、default_branch=dev、stars 207,008 @2026-09-13）；https://api.github.com/repos/badlogic/pi-mono 同样 301 到 earendil-works/pi（repo id 1035029907）；https://api.github.com/repos/earendil-works/pi stars 104,522
  authority:: 高
  verified:: 2026-09-13

- 来源:: Pi 官方 SDK 文档与 npm 分发物
  use_when:: 核对进程内嵌入 vs RPC 的取舍、工具 schema 契约（TypeBox）与版本线
  url:: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/sdk.md
  answers:: SDK preferred（type safety / same Node.js process / direct access to agent state）vs RPC preferred（另一语言 / **process isolation** / language-agnostic client）；`defineTool<TParams extends TSchema>` 与 `dist/core/extensions/types.d.ts` 的 `import ... from "typebox"`（https://cdn.jsdelivr.net/npm/@earendil-works/pi-coding-agent@0.85.1/dist/core/extensions/types.d.ts ）；npm latest=0.85.1（2026-09-05T12:17:19Z）见 https://registry.npmjs.org/@earendil-works/pi-coding-agent ，旧作用域停在 0.73.1 / 2026-05-07
  authority:: 高
  verified:: 2026-09-13

- 来源:: Open-Magiviz 仓库 README 与 package.json
  use_when:: 核对该平台的实际模型承接方（Kie.ai / ZenMux / FAL）与依赖清单
  url:: https://raw.githubusercontent.com/ItusiAI/Open-Magiviz/main/README.md
  answers:: 「AI 服务」段：Kie.ai（KIE_API_KEY / KIE_VEO_WEBHOOK_URL / KIE_VIDEO_WEBHOOK_URL）、ZenMux（ZENMUX_API_KEY）；视频模型表 14 个别名（wan30/wan30Prime 取代 wan27）；依赖 `@fal-ai/client@^1.8.4` 等见 https://raw.githubusercontent.com/ItusiAI/Open-Magiviz/main/package.json
  authority:: 高
  verified:: 2026-09-13

## B7 复核新增（2026-09-13）：Skills 体系

> 本次回写（Skill 规模化管理 / Anthropic Skill 系统深度分析 / 实用 Skills 参考 / Agent 驱动 Skill 迁移设计 四篇）实际打开并逐条核对的**官方文档与上游主源**；`use_when` 写「什么时候要回查」。

- 来源:: Claude Code 官方文档 · Skills
  use_when:: 写或改 SKILL.md frontmatter、判断某字段是否官方支持、解释「技能为什么占 context」时回查
  url:: https://code.claude.com/docs/en/skills
  answers:: 字段表（`paths` / `when_to_use` / `argument-hint` / `disable-model-invocation` / `user-invocable` / `disallowed-tools` / `model` / `effort` / `context: fork` / `agent` / `background` / `hooks` / `shell`）；`description`+`when_to_use` 在技能列表中截断于 1,536 字符；`/skill-doctor`（需 v2.1.252+，`-p` 模式打印文本）与 `skillOverrides`（插件技能除外）；`.claude/skills/` 子目录技能不在启动时加载（需 v2.1.257+）；`commands/*.md` 与 `skills/<name>/SKILL.md` 等价；技能加载后 stays in context across turns
  authority:: 高
  verified:: 2026-09-13

- 来源:: Agent Skills 规范（agentskills.io）
  use_when:: 判断某个 frontmatter 键能不能写进顶层、确认 name/description/compatibility 的长度上限
  url:: https://agentskills.io/specification
  answers:: 只有六个键：`name`（≤64 字符，小写/数字/连字符，不得以连字符开头或结尾）、`description`（≤1024 字符）、`license`、`compatibility`（≤500 字符）、`metadata`（string→string map）、`allowed-tools`（Experimental）；claude.ai 上传 / Skills API / `package_skill.py` 只接受这六个
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 · Memory
  use_when:: 核对 CLAUDE.md 到底有几层、`@import` 是启动展开还是按需级联、auto memory 的定位
  url:: https://code.claude.com/docs/en/memory
  answers:: 四层作用域（Managed policy / User / Project / Local）与各平台路径；「Claude Code has two complementary memory systems」（auto memory 与 CLAUDE.md 并列，不是层级）；`@import` 为 launch 时展开、不省 context；递归导入上限 four hops；跨工作目录导入的一次性批准弹窗
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 · Plugins
  use_when:: 确认插件技能的调用形式、命名空间与 `skillOverrides` 的适用范围
  url:: https://code.claude.com/docs/en/plugins
  answers:: 插件技能调用形如 `/plugin-name:skill-name`（天然命名空间）；`Plugin skills are not affected by skillOverrides`；`claude plugin eval` 的隔离会话评测格式
  authority:: 高
  verified:: 2026-09-13

- 来源:: Agent Skills · 描述优化指南
  use_when:: 建技能触发测试集、解释「为什么必须新会话 / 为什么要近失负样本」
  url:: https://agentskills.io/skill-creation/optimizing-descriptions
  answers:: should-trigger / should-not-trigger 查询集；「The most valuable negative test cases are near-misses」；无关键词重叠的负例 too easy；每查询多跑取触发率；「Seeing a skill trigger tells you Claude found it, not that it did what you intended」
  authority:: 高
  verified:: 2026-09-13

- 来源:: Agent Skills · 技能评测指南
  use_when:: 设计「技能可用 vs 禁用」的效果基线与验收清单
  url:: https://agentskills.io/skill-creation/evaluating-skills
  answers:: with/without 对比需新会话；触发与效果分开度量
  authority:: 高
  verified:: 2026-09-13

- 来源:: Anthropic 官方博文 · Improving skill-creator
  use_when:: 追 skill-creator 的评测能力演进与官方测试口径
  url:: https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills
  answers:: skill-creator 的 Test / measure / refine 流程定位
  authority:: 高
  verified:: 2026-09-13

- 来源:: anthropics/skills · marketplace.json 与 skill-creator SKILL.md
  use_when:: 写官方技能的安装命令、确认某技能属于哪个插件
  url:: https://raw.githubusercontent.com/anthropics/skills/main/.claude-plugin/marketplace.json
  answers:: marketplace `name` = anthropic-agent-skills，共 5 插件：document-skills（xlsx/docx/pptx/pdf）、example-skills（12 项）、claude-api、academy-guide、discernment-nudge；skill-creator 安装 `/plugin install skill-creator@claude-plugins-official`、排错先 `/plugin marketplace add anthropics/claude-plugins-official`，另见 https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md
  authority:: 高
  verified:: 2026-09-13

- 来源:: obra/superpowers README 与 requesting-code-review SKILL.md
  use_when:: 写 Superpowers 的技能名/安装路径，或排查「技能突然集体不触发」
  url:: https://raw.githubusercontent.com/obra/superpowers/main/README.md
  answers:: 技能实名（`requesting-code-review` 而非 `code-review`、`receiving-code-review`、`finishing-a-development-branch` 等）；官方 marketplace 为首选安装路径；post-compaction hook 导致超长会话丢失 bootstrap（处置=新开会话）；Visual companion 遥测与 `SUPERPOWERS_DISABLE_TELEMETRY`；SKILL.md 见 https://raw.githubusercontent.com/obra/superpowers/main/skills/requesting-code-review/SKILL.md
  authority:: 高
  verified:: 2026-09-13

- 来源:: UI UX Pro Max README（nextlevelbuilder）
  use_when:: 引用该技能的知识库计数（易漂移）或处置安装/搜索失败
  url:: https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/main/README.md
  answers:: 79 searchable UI styles（50 active）/192 color palettes（与 192 product types 1:1）/74 font pairings/119 UX guidelines/22 frameworks/34 landing patterns/1,934 Google Fonts；Troubleshooting：symlink 报错改用 `npx ui-ux-pro-max-cli init --ai claude`、Python 需自行安装、长字段截断 300 字符改用 `search.py --json`
  authority:: 高
  verified:: 2026-09-13

- 来源:: Web Access README（eze-is）与仓库元数据
  use_when:: 安装 Web Access、确认支持的浏览器与使用风险
  url:: https://raw.githubusercontent.com/eze-is/web-access/main/README.md
  answers:: 推荐安装 `npx skills add eze-is/web-access`（git clone 是方式三）；CDP 不再绑定 Chrome，支持 Edge（`edge://inspect/#remote-debugging`）与 `WEB_ACCESS_BROWSER`；Node.js 22+；社交平台自动化有账号限流/封禁风险，建议小号；仓库元数据 https://api.github.com/repos/eze-is/web-access（created 2026-03-18、stars 8,922、forks 638 @2026-09-13）
  authority:: 高
  verified:: 2026-09-13

- 来源:: GitHub API — Skills 系仓库元数据
  use_when:: 引用 star 数前核对（此类数字持续漂移，须带日期）
  url:: https://api.github.com/repos/anthropics/skills
  answers:: anthropics/skills：stargazers 176,041、forks 20,833、created 2025-09-22、pushed 2026-09-10、description「Public repository for Agent Skills」；https://api.github.com/repos/affaan-m/ECC ：full_name affaan-m/ECC、stargazers 257,373、homepage ecc.tools、created 2026-01-18
  authority:: 高
  verified:: 2026-09-13

- 来源:: monap.cn（Anthropic 内部 Skills 方法论转录）
  use_when:: 引用「9 大分类 / 9 条技巧」时回到转录方原文，确认哪句是 Anthropic 口径、哪句是编者加注
  url:: http://monap.cn/AI/Skills/04-Anthropic%E5%86%85%E9%83%A8Skills%E6%96%B9%E6%B3%95%E8%AE%BA.html
  answers:: 九类名称与顺序；Product Verification 优先级最高；类型 6 的 testing-practices → adversarial-review 流水线；类型 9 护栏写法（disable-model-invocation + allowed-tools）；「技巧 8」的 `/careful` 明确标注为社区/gstack 实践、非 Anthropic 博客原文
  authority:: 中
  verified:: 2026-09-13

- 来源:: skills.sh — /careful 技能归属
  use_when:: 澄清 `/careful` 是不是 Anthropic 官方示例
  url:: https://www.skills.sh/kunchenguid/programbench-bench/careful
  answers:: 归属 kunchenguid/programbench-bench，First Seen 2026-08-07，安装 `npx skills add https://github.com/kunchenguid/programbench-bench --skill careful`；含 Claude hooks 与 Snyk Warn 结论
  authority:: 中
  verified:: 2026-09-13

## C2 复核新增（2026-09-13）：cs-base 基础学科（算法 / 深度学习 / MongoDB / Kafka / 向量检索）

> 本簇（数据结构与算法 / 深度学习算法基础 / MongoDB / Kafka / 向量数据库与检索）回写时逐条核对的一手来源；`use_when` 写「什么时候要回查」。

- 来源:: libstdc++ `stl_queue.h`（priority_queue 实现）
  use_when:: 确认「取堆顶」是 O(1) 而不是 O(logn)
  url:: https://raw.githubusercontent.com/gcc-mirror/gcc/master/libstdc++-v3/include/bits/stl_queue.h
  answers:: `priority_queue::top()` 直接 `return c.front()`；底层容器默认 vector
  authority:: 高
  verified:: 2026-09-13

- 来源:: libstdc++ `hashtable_policy.h`（哈希表策略）
  use_when:: 核对 `std::unordered_map` 的桶策略与默认负载因子（素数桶 vs 2 的幂）
  url:: https://raw.githubusercontent.com/gcc-mirror/gcc/master/libstdc++-v3/include/bits/hashtable_policy.h
  answers:: `_Prime_rehash_policy(float __z = 1.0)`，注释 "smallest prime that keeps the load factor small enough"
  authority:: 高
  verified:: 2026-09-13

- 来源:: libc++ `__hash_table`
  use_when:: 对照 libc++ 的 `unordered_map` 实现（素数桶 + 单链表）
  url:: https://raw.githubusercontent.com/llvm/llvm-project/main/libcxx/include/__hash_table
  answers:: `__next_prime`、`__max_load_factor_` 存在
  authority:: 高
  verified:: 2026-09-13

- 来源:: libstdc++ `stl_vector.h`
  use_when:: 核对 `vector` 扩容因子（libstdc++ ≈2×）
  url:: https://raw.githubusercontent.com/gcc-mirror/gcc/master/libstdc++-v3/include/bits/stl_vector.h
  answers:: `_M_check_len` 注释 "Grow by (at least) doubling"
  authority:: 高
  verified:: 2026-09-13

- 来源:: libc++ `vector.h`
  use_when:: 核对 libc++ 的扩容策略 `max(2×cap, new_size)`
  url:: https://raw.githubusercontent.com/llvm/llvm-project/main/libcxx/include/__vector/vector.h
  answers:: `__recommend` 返回 `std::max<size_type>(2 * __cap, __new_size)`
  authority:: 高
  verified:: 2026-09-13

- 来源:: MSVC STL `vector`
  use_when:: 核对 MSVC 几何增长 1.5×
  url:: https://raw.githubusercontent.com/microsoft/STL/main/stl/inc/vector
  answers:: `_Calculate_growth` 的实现（1.5× 增长）
  authority:: 高
  verified:: 2026-09-13

- 来源:: stas00/ml-engineering — 训练性能手册
  use_when:: 核对 FFN/SwiGLU 隐层维度与「参数量持平」的 8/3·d 口径
  url:: https://raw.githubusercontent.com/stas00/ml-engineering/master/training/performance/README.md
  answers:: SwiGLU 用 3 个矩阵替代 2 个；保持参数量时取 8/3·d（8/3*4096=10922）与 11008 的实测讨论
  authority:: 中
  verified:: 2026-09-13

- 来源:: YaRN README（RoPE 上下文扩展）
  use_when:: 说明 RoPE 超出训练长度必须做位置缩放，不能称「外推友好」
  url:: https://raw.githubusercontent.com/jquesnelle/yarn/master/README.md
  answers:: 32K/64K/128K 扩展方式与 Llama-2 变体清单（仓库默认分支为 master，`/main/` 路径 404）
  authority:: 高
  verified:: 2026-09-13

- 来源:: OpenAlex API — ALiBi 论文检索
  use_when:: 需要一条可复核的 ALiBi（Attention with Linear Biases）收录记录
  url:: https://api.openalex.org/works?filter=title.search:attention%20with%20linear%20biases&per-page=2
  answers:: 命中 ALiBi 论文，keywords 含 Extrapolation——支撑「ALiBi 为长度外推设计」
  authority:: 中
  verified:: 2026-09-13

- 来源:: MongoDB 官方文档 `journaling.txt`
  use_when:: 核查 WiredTiger journal/checkpoint 的恢复流程与容量规划
  url:: https://raw.githubusercontent.com/mongodb/docs/master/source/core/journaling.txt
  answers:: 恢复三步（定位最后 checkpoint → 匹配标识 → 重放其后操作）、journal 约 100MB、checkpoint 默认上限 2GB、"the MongoDB server will crash"、默认 snappy
  authority:: 高
  verified:: 2026-09-13

- 来源:: MongoDB 官方文档 `fact-agg-memory-limit.rst`
  use_when:: 回答「聚合 100MB 上限要不要手动开 allowDiskUse」
  url:: https://raw.githubusercontent.com/mongodb/docs/master/source/includes/fact-agg-memory-limit.rst
  answers:: 6.0 起 `allowDiskUseByDefault` 默认 true、超 100MB 的阶段自动落临时文件；`$search` 在独立进程不受限
  authority:: 高
  verified:: 2026-09-13

- 来源:: endoflife.date — MongoDB 版本支持期
  use_when:: 核对 LTS/Rapid 版本线与 EOL 日期
  url:: https://endoflife.date/api/mongodb.json
  answers:: 8.0（2024-10-31 发布，eol 2029-10-31）、8.1/8.2/8.3 日期、6.0 eol 2025-07-31、7.0 eol 2027-08-31
  authority:: 中
  verified:: 2026-09-13

- 来源:: MongoDB 8.0 release notes
  use_when:: 确认 8.0 是 LTS 且合并了 7.1/7.2/7.3 的变更
  url:: https://raw.githubusercontent.com/mongodb/docs/master/source/release-notes/8.0.txt
  answers:: "MongoDB 8.0 is a LTS Release... includes changes introduced in MongoDB Rapid Releases 7.1, 7.2, and 7.3"；补丁记录到 8.0.9
  authority:: 高
  verified:: 2026-09-13

- 来源:: MongoDB 官方文档 `retryable-writes.txt`
  use_when:: 写「重试会不会把同一笔写做两遍」类结论前核对官方边界
  url:: https://raw.githubusercontent.com/mongodb/docs/master/source/core/retryable-writes.txt
  answers:: 官方驱动默认开启、**只重试一次**、不支持 standalone、写 local 库报写错误、存在重复应用窗口
  authority:: 高
  verified:: 2026-09-13

- 来源:: MongoDB 官方文档 `transactions-production-consideration.txt`
  use_when:: 给多文档事务定可验收边界（寿命 / 锁等待 / oplog 体积 / standalone）
  url:: https://raw.githubusercontent.com/mongodb/docs/master/source/core/transactions-production-consideration.txt
  answers:: standalone 不支持事务；`transactionLifetimeLimitSeconds`；`maxTransactionLockRequestTimeoutMillis`；事务总量上限取消但单条 oplog 仍 ≤16MB
  authority:: 高
  verified:: 2026-09-13

- 来源:: MongoDB 官方文档 `transactions.txt`
  use_when:: 核对事务的最低版本门槛
  url:: https://raw.githubusercontent.com/mongodb/docs/master/source/core/transactions.txt
  answers:: 副本集 FCV ≥4.0、分片 ≥4.2 的最低版本表
  authority:: 高
  verified:: 2026-09-13

- 来源:: Apache Kafka 4.0.0 RELEASE_NOTES
  use_when:: 确认 4.0 移除 ZooKeeper（KIP-500）与相关 JIRA 条目
  url:: https://archive.apache.org/dist/kafka/4.0.0/RELEASE_NOTES.html
  answers:: KAFKA-17613 Remove ZK migration code；KAFKA-17616 Remove KafkaServer；KAFKA-17128 node.id immutable
  authority:: 高
  verified:: 2026-09-13

- 来源:: endoflife.date — Kafka 版本线
  use_when:: 核对 4.x 各版本发布日期（文档写「截至 2026-09」时）
  url:: https://endoflife.date/api/kafka.json
  answers:: 4.0 2025-03-18；4.1 2025-09-02；4.2 2026-02-17；4.3 2026-05-20
  authority:: 中
  verified:: 2026-09-13

- 来源:: KIP-848（下一代消费者再平衡协议）
  use_when:: 判断服务端分配器是否可用、要不要显式开 `group.protocol=consumer`
  url:: https://cwiki.apache.org/confluence/display/KAFKA/KIP-848%3A+The+Next+Generation+of+the+Consumer+Rebalance+Protocol
  answers:: "The consumer rebalance protocol with server side assignors is GA in Apache Kafka 4.0."；成员逐个增量迁移、不整组停摆
  authority:: 高
  verified:: 2026-09-13

- 来源:: Kafka 4.0 `ConsumerConfig.java`
  use_when:: 核对默认 `group.protocol` 与默认 `partition.assignment.strategy`
  url:: https://raw.githubusercontent.com/apache/kafka/4.0/clients/src/main/java/org/apache/kafka/clients/consumer/ConsumerConfig.java
  answers:: `DEFAULT_GROUP_PROTOCOL = GroupProtocol.CLASSIC`；默认 `List.of(RangeAssignor.class, CooperativeStickyAssignor.class)`
  authority:: 高
  verified:: 2026-09-13

- 来源:: KIP-405（Kafka Tiered Storage）
  use_when:: 回答 tiered storage 在 Apache Kafka 侧的成熟度
  url:: https://cwiki.apache.org/confluence/display/KAFKA/KIP-405%3A+Kafka+Tiered+Storage
  answers:: "This KIP has been merged and marked production-ready since Kafka 3.9."
  authority:: 高
  verified:: 2026-09-13

- 来源:: Kafka 4.0 `BuiltInPartitioner.java`
  use_when:: 证明「key→分区只由分区数决定」（改分区数才重映射，纯 reassign 不影响）
  url:: https://raw.githubusercontent.com/apache/kafka/4.0/clients/src/main/java/org/apache/kafka/clients/producer/internals/BuiltInPartitioner.java
  answers:: `partitionForKey = toPositive(murmur2(key)) % numPartitions`
  authority:: 高
  verified:: 2026-09-13

- 来源:: KIP-320（follower 检测与处理日志截断）
  use_when:: 解释 HW 以上数据为何可能被截断、FENCED_REPLICA 从哪来
  url:: https://cwiki.apache.org/confluence/display/KAFKA/KIP-320%3A+Allow+fetchers+to+detect+and+handle+log+truncation
  answers:: 前提「HW 以下数据永不丢失」；`OffsetsForLeaderEpoch` 定位截断点；Fetch 带 leader epoch，不符返回 FENCED_REPLICA
  authority:: 高
  verified:: 2026-09-13

- 来源:: Kafka 4.0 `TopicConfig.java`
  use_when:: 核对 topic 级配置键名（如 `unclean.leader.election.enable`）
  url:: https://raw.githubusercontent.com/apache/kafka/4.0/clients/src/main/java/org/apache/kafka/common/config/TopicConfig.java
  answers:: `UNCLEAN_LEADER_ELECTION_ENABLE_CONFIG = "unclean.leader.election.enable"`
  authority:: 高
  verified:: 2026-09-13

- 来源:: hnswlib `hnswalg.h`
  use_when:: 核对 HNSW 构建期搜索宽度用 efConstruction（不是 M）及其钳位规则
  url:: https://raw.githubusercontent.com/nmslib/hnswlib/master/hnswlib/hnswalg.h
  answers:: `ef_construction_ = std::max(ef_construction, M_)`
  authority:: 高
  verified:: 2026-09-13

- 来源:: hnswlib README
  use_when:: 解释 M / ef_construction / efSearch 各自管什么
  url:: https://raw.githubusercontent.com/nmslib/hnswlib/master/README.md
  answers:: ef_construction 是构建期时间/精度权衡；M 为最大出边数；ef 越大召回越好但越慢（对具体倍率沉默）
  authority:: 高
  verified:: 2026-09-13

- 来源:: pgvector README
  use_when:: 给 pgvector 定选型边界、二值量化与重排口径
  url:: https://raw.githubusercontent.com/pgvector/pgvector/master/README.md
  answers:: Scaling 一节：halfvec、二值量化 "with re-ranking for search"、Citus/PgDog 分片；Monitoring 建议用 exact search 对比测 recall
  authority:: 高
  verified:: 2026-09-13

> [!tip] 为什么不批量登记本主题的 URL
> 脚本实测（`scripts/url-registry-mine.py`，2026-09-13 默认口径）全库 **736 个唯一 URL**（加 `--include-archive` 为 742），其中绝大多数属学习类噪声（博客、镜像、一次性引用）；滤除的占位/伪 URL 为 49 条（加 `--include-archive` 为 50）。
> 更正（2026-09-13）：本行原写「526 个唯一 URL」（原表述），且与 [[URL-REGISTRY]] 的「572 个唯一 URL / 733 次出现」同日互相矛盾——三个数字均为过期口径，复核重跑得唯一 URL **736**；「出现 1073 次」这一说法无法复算（该脚本只统计唯一 URL，没有出现次数计数器），已弃用。数字只在一处（[[URL-REGISTRY]]）维护，并固定「脚本 + 命令 + 口径 + 日期」。
> 本库已有 [[Articles-Index]] 与 [[AI-Links-KB-Home]] 承载「有学习价值」的部分，
> 本页只登记**会反复回查**的索引入口与官方文档。

## C1 复核新增（2026-09-13）：cs-base 语言与工具链

> 本簇（CPP-核心知识 / LibC运行时排查 / LLVM使用调优 / CPO与std-execution / COM组件框架 / Python高级核心 / 音视频流媒体 / 设计模式实战 / 架构设计与方案选型）回写时实际引用并逐条核对的一手来源；`use_when` 写「什么时候要回查」。

- 来源:: cppreference「C++26」
  use_when:: 判断 C++26 收录了哪些库件、各编译器落到哪一档（反射/契约/execution 的采用决策）
  url:: https://en.cppreference.com/w/cpp/26
  answers:: C++26 库头文件清单（meta / execution / contracts / hive / inplace_vector / linalg / rcu / simd / text_encoding / stdbit.h / stdckdint.h）；页内逐编译器支持表（含 partial 标记）可作落地判据
  authority:: 高
  verified:: 2026-09-13

- 来源:: C++ 现行标准草案在线版（eel.is/c++draft）
  use_when:: 核对某条 C++ 规则的现行措辞与枚举值（注意草案段号会随版本变动）
  url:: https://eel.is/c++draft/atomics.order
  answers:: [atomics.order] memory_order 只有 5 值（无 consume）；[futures.async]/5 async future 析构可阻塞；[exec.connect]/6 成员 connect；[exec.adapt] 现行适配器集合（无 ensure_started / split）；[exec.sync.wait] sync_wait 三态；[exec.get.fwd.progress] weakly_parallel；[exec.snd] 域分层；[stmt.dcl] 现行段号 /3
  authority:: 高
  verified:: 2026-09-13

- 来源:: WG21 P3109R0（std::execution 设计修改汇总）
  use_when:: 确认 tag_invoke 是否仍是 execution 的定制机制、被哪些提案改掉
  url:: https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2024/p3109r0.html
  answers:: P2855 Member-function-based customization（Remove the tag_invoke ADL-based CPs）；P2999 改为基于 domain 的成员函数定制；Remove ensure_started()（P2519）；原文「no more ADL-based customization points left in the design」
  authority:: 高
  verified:: 2026-09-13

- 来源:: glibc 上游源码与 NEWS
  use_when:: 核对 glibc 的常量上限、ld.so 调试开关、以及被移除的工具
  url:: https://sourceware.org/git/?p=glibc.git;a=blob_plain;f=sysdeps/unix/sysv/linux/bits/local_lim.h;hb=HEAD
  answers:: PTHREAD_KEYS_MAX=1024、_POSIX_THREAD_KEYS_MAX=128、PTHREAD_DESTRUCTOR_ITERATIONS=4；catchsegv/libSegFault.so 自 2.35 移除（同仓 NEWS）；LD_DEBUG 选项表含 tls（elf/rtld.c）
  authority:: 高
  verified:: 2026-09-13

- 来源:: musl libc 源码（include/limits.h）
  use_when:: 核对 musl 与 glibc 的常量差异（pthread key 上限、析构迭代次数）
  url:: https://git.musl-libc.org/cgit/musl/plain/include/limits.h
  answers:: PTHREAD_KEYS_MAX=128（等于 POSIX 下限）、PTHREAD_DESTRUCTOR_ITERATIONS=4
  authority:: 高
  verified:: 2026-09-13

- 来源:: man7 / Debian manpages（pthread rwlock、ld.lld）
  use_when:: 查 rwlock 写者饥饿的可执行旋钮、lld 的 --icf 档位与不安全优化开关归属
  url:: https://man7.org/linux/man-pages/man3/pthread_rwlockattr_setkind_np.3.html
  answers:: PREFER_READER_NP 是默认 kind、PREFER_WRITER_NP 被 glibc 忽略、可用的是 PREFER_WRITER_NONRECURSIVE_NP 及特性宏；lld 侧 https://manpages.debian.org/unstable/lld-19/ld.lld-19.1.en.html （--icf=none/safe/all、--keep-unique、--ignore-function-address-equality 与 --ignore-data-address-equality 的区别）
  authority:: 高
  verified:: 2026-09-13

- 来源:: LLVM BOLT README（llvm-project 主源）
  use_when:: 上 BOLT 前核对支持平台与输入约束
  url:: https://api.github.com/repos/llvm/llvm-project/contents/bolt/README.md
  answers:: 支持 X86-64 与 AArch64 ELF；采样 x86 LBR / AArch64 BRBE；输入须未剥离符号表、建议带重定位（--emit-relocs/-q）；与 -freorder-blocks-and-partition 不兼容；stale profile 需刷新 .fdata
  authority:: 高
  verified:: 2026-09-13

- 来源:: Microsoft Learn（COM / WMI 官方文档）
  use_when:: 核对 COM 线程模型初始化、免注册激活清单生成、WMI 事件订阅写法
  url:: https://learn.microsoft.com/en-us/windows/win32/com/choosing-the-threading-model
  answers:: ThreadingModel 取值 Apartment/Free/Both/Neutral（Neutral = COM+ only）；CoInitializeEx 只能 APARTMENTTHREADED/MULTITHREADED、COINIT_DISABLE_OLE1DDE 仅关 OLE1 DDE（api/objbase/ne-objbase-coinit）；reg-free 清单由 GenerateApplicationManifest.IsolatedComReferences 生成（dotnet/api/…isolatedcomreferences）；WMI 事件示例 ExecNotificationQueryAsync + IWbemObjectSink + CancelAsyncCall（windows/win32/wmisdk/example--receiving-event-notifications-through-wmi-）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Python 官方文档与 PEP（3.14 / free-threading / 子解释器）
  use_when:: 核对 CPython 版本口径与库行为（free-threaded 状态、子解释器、asyncio、GC、bisect）
  url:: https://docs.python.org/3/whatsnew/3.14.html
  answers:: free-threaded 为官方支持构建（PEP 779 Final，peps.python.org/pep-0779/）；PEP 734 多解释器进标准库（peps.python.org/pep-0734/）；增量 GC；asyncio TaskGroup/timeout（docs.python.org/3/library/asyncio-task.html）；bisect left/right 与性能说明（docs.python.org/3/library/bisect.html）
  authority:: 高
  verified:: 2026-09-13

- 来源:: FFmpeg 官方（ffplay doxygen 源页 / Encode wiki / 相关 RFC）
  use_when:: 对照 ffplay 线程与函数结构、编码器码率控制参数、WebRTC 抗弱网恢复件
  url:: https://ffmpeg.org/doxygen/trunk/ffplay_8c.html
  answers:: ffplay 结构（read_thread + audio/video/subtitle_thread + sdl_audio_callback，video_refresh 是主循环函数）；码率控制 CRF/Two-Pass 与 -maxrate/-bufsize（trac.ffmpeg.org/wiki/Encode/H.264）；PLI/FIR（RFC 5104，rfc-editor.org/rfc/rfc5104.html）；RTX 独立重传流（RFC 4588，rfc-editor.org/rfc/rfc4588.html）
  authority:: 高
  verified:: 2026-09-13

- 来源:: cppreference 中文镜像（三/五/零法则）
  use_when:: 复核 RAII 句柄类该不该声明特殊成员函数、拷贝/移动语义怎么定
  url:: https://cppreference.cn/w/cpp/language/rule_of_three
  answers:: 管理资源句柄的类不应使用隐式定义的特殊成员函数；五法则要求声明全部五个；缺移动构造通常只是「错失的优化机会」
  authority:: 中
  verified:: 2026-09-13

- 来源:: N3337（C++11 草案定稿文本）与 GCC 文档
  use_when:: 判断历史版本的条款段号引用是否正确、以及哪些保证可被编译开关关掉
  url:: https://timsong-cpp.github.io/cppwp/n3337/stmt.dcl
  answers:: C++11 中 [stmt.dcl]/4 才是魔法静态条款（现行草案为 /3，段号变动不改写历史引用）；GCC -fno-threadsafe-statics 会关掉线程安全初始化（gcc.gnu.org/onlinedocs/gcc/C_002b_002b-Dialect-Options.html）
  authority:: 高
  verified:: 2026-09-13

- 来源:: SQLite WAL 文档
  use_when:: 判断 WAL 模式的写并发上限与「方案自身失效」的重估触发线
  url:: https://www.sqlite.org/wal.html
  answers:: 只有一个 WAL 文件 → 同时只能有一个写者（§2.2）；§6 Avoiding Excessively Large WAL Files；§9 WAL 模式下的 SQLITE_BUSY（另见 A4 已登记的 sqlite.org/wal.html §11 WAL-Reset Bug 条目）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Evolutionary Architecture（适应度函数）
  use_when:: 设计适应度函数清单与职责边界（失败回 ADR，而不是改阈值）
  url:: https://evolutionaryarchitecture.com/
  answers:: Fitness Functions 概念（把「什么叫 fit」显式化并尽量自动化）与 Katas 练习入口
  authority:: 高
  verified:: 2026-09-13

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 「Obsidian 帮助文档」url 为 `https://help.obsidian.md/`——上游迁移型失效，且巡检跟随重定向、不会报出 | 改为 `https://obsidian.md/help/`（2026-09-13 实测 200，标题 Home - Obsidian Help）；原 url 与失效成因保留在 `answers` 的「更正」句内；`verified` 更新为 2026-09-13 |
| 纠错 | 「脚本实测全库 526 个唯一 URL」与 [[URL-REGISTRY]] 的 572 / 733 同日互相矛盾 | 统一为本轮复算值 **736**（`--include-archive` 742；滤除占位 49 / 50），写明「脚本 + 命令 + 口径 + 日期」；并注明「出现 1073 次」无法由该脚本复算、已弃用；原表述保留在更正行内 |
| 纠错 | [[Articles-Index]] 登记为「14 篇」 | 改为 **15 篇**（`ai-links/articles/` 实测 16 个 `.md`（含索引页自身）= 15 篇，索引页统计行自写「文章总数 15」）；出处可追溯至 `_archive/SESSION-ARCHIVE-2026-08-18.md` 的「14 篇远程文章」 |
| 加厚 | 外部学习资源只登记首页（arXiv / Obsidian / Dataview） | 补 Dataview 内联字段页（实测 200，含「字段名可用任意 UTF-8 字符」与内建隐式字段，正是 `字段:: 值` 语法的依据）与 Dataview Release API 条目（latest 0.5.70 / 本机 0.5.68，配合 [[URL-Lookup]] 版本策略）；arXiv 因复核环境不可达，未补具体检索入口 |
| 加厚 | 图表规范的入图来源未登记（Transformer 论文口径 / Excalidraw 绑定字段类型 / 插件版本） | 新增下方「C9 复核新增」节 3 条（Annotated Transformer、Excalidraw `types.ts`、obsidian-excalidraw-plugin 2.25.3，2026-09-13 实测均 HTTP 200） |

见 [[CORRECTIONS]]、[[AGENTS]]。

## C9 复核新增（2026-09-13）：图表规范与 Excalidraw 绑定

> 本簇（`diagrams/` 与 [[AGENTS]] 第十一节图表规范）回写时逐条核对的一手来源；`use_when` 写「什么时候要回查」。

- 来源:: The Annotated Transformer（Harvard NLP）
  use_when:: 核对 Transformer 架构图是否漏画残差 / LayerNorm、位置编码相加、层数 N 时，回到论文配套实现原文
  url:: https://nlp.seas.harvard.edu/2018/04/03/attention.html
  answers:: `The encoder is composed of a stack of N=6 identical layers.`（解码器同为 N=6）；`We employ a residual connection around each of the two sub-layers, followed by layer normalization` 与输出 `LayerNorm(x + Sublayer(x))`；位置编码与嵌入相加 `x = x + Variable(self.pe[:, :x.size(1)], ...)`；decoder 子层除 masked self-attn 外还有 src-attn，其 K/V 取自 encoder（2026-09-13 实测 HTTP 200）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Excalidraw 元素类型定义（`BindMode` / `FixedPointBinding`）
  use_when:: 判箭头绑定字段是否合规（该按 `focus`/`gap` 还是 `fixedPoint`/`mode` 核对）时读实际类型定义
  url:: https://cdn.jsdelivr.net/gh/excalidraw/excalidraw@master/packages/element/src/types.ts
  answers:: `export type BindMode = "inside" | "orbit" | "skip";`；`FixedPointBinding = { elementId; fixedPoint: [number, number] /* 0.0-1.0 比例 */; mode: BindMode }`；上游同文件 https://raw.githubusercontent.com/excalidraw/excalidraw/master/packages/element/src/types.ts（2026-09-13 两个地址均实测 HTTP 200）
  authority:: 高
  verified:: 2026-09-13

- 来源:: obsidian-excalidraw-plugin 2.25.3 release
  use_when:: 确认库内图像的 `compressed-json` 由哪个插件版本写出、绑定字段以哪一版口径为准
  url:: https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.25.3
  answers:: Release 2.25.3 存在（页面标题即该 tag；2026-09-13 实测 HTTP 200）；`diagrams/Transformer-Architecture.excalidraw.md` 的 `source` 字段即该 tag；实测 `diagrams/` 22 张图中 13 张为 `compressed-json`、9 张仍为未压缩 json；该批图中的箭头绑定全库仍有 108 处 legacy `focus`/`gap`（7 张图）
  authority:: 高
  verified:: 2026-09-13

## C4 复核新增（2026-09-13）：Claude Code 官方设置与版本元数据

> 本簇（claude-ops 事故复盘）回写时实际引用的一手来源；`use_when` 写「什么时候要回查」。

- 来源:: Claude Code 官方文档 · Settings（配置优先级）
  use_when:: 决定「锁定 CC 版本 / 关自动更新」这类值该写在哪一层，或排查「为什么我的设置没生效」
  url:: https://code.claude.com/docs/en/settings.md
  answers:: 优先级链：managed settings > command line（`claude --settings`）> project local（`.claude/settings.local.json`）> shared project（`.claude/settings.json`）> user（`~/.claude/settings.json`）——[[claude-cache-incident-postmortem]] §六 措施 4「CC 版本锁定」的落位依据
  authority:: 高
  verified:: 2026-09-13

## C5 复核新增（2026-09-13）：Claude Code CLI / 权限 / Actions 与会话

> 本簇（claude-ops 方案与设计 / hermes 回写，21 篇）实际打开并逐条核对的官方文档与上游清单；`use_when` 写「什么时候要回查」。

- 来源:: Claude Code 官方文档 · CLI reference
  use_when:: 照抄 systemd / 调度示例前确认子命令是否真实存在；查 `--permission-mode` 合法取值、版本安装与 headless 续接 flag
  url:: https://code.claude.com/docs/en/cli-reference.md
  answers:: daemon 子命令只有 `claude daemon status`（未运行退出码 1）与 `claude daemon stop --any [--keep-workers]`，**无 `daemon start` / `daemon restart`**（v2.1.199+ 需 `--dangerously-skip-permissions` 才跑 daemon 子命令）；版本安装走 `claude install [version]`（版本号或 stable/latest）与 `claude update`；`--permission-mode` 取 default | acceptEdits | plan | auto | dontAsk | bypassPermissions（manual = default 别名）；`--session-id` 须合法 UUID；`--continue` 跳过 `claude -p` / Agent SDK 会话，而 `claude -p --continue` 包含之；常驻后台会话用 `--bg` / `attach` / `respawn` / `agents`
  authority:: 高
  verified:: 2026-09-13

- 来源:: anthropics/claude-code-action v1.0 · action.yml
  use_when:: 写或审 GitHub Actions 里的 claude-code-action 步骤时，核对输入名是否真实存在（照抄旧例会让密钥静默为空、权限模式静默失效）
  url:: https://cdn.jsdelivr.net/gh/anthropics/claude-code-action@main/action.yml
  answers:: v1.0 inputs 含 `anthropic_api_key`、`claude_code_oauth_token`、`claude_args`、`prompt`、`settings`、`track_progress` 等；**无 `anthropic-api-key`、无 `permission-mode`**——权限类参数统一写进 `claude_args: "--permission-mode bypassPermissions"`
  authority:: 高
  verified:: 2026-09-13

- 来源:: claude-code-action 迁移指南（v0.x → v1.0）
  use_when:: 从旧版 action 迁移，或排查「输入写了却静默失效」
  url:: https://raw.githubusercontent.com/anthropics/claude-code-action/main/docs/migration-guide.md
  answers:: `mode` → 自动检测、`direct_prompt`/`override_prompt` → `prompt`、`custom_instructions` → `claude_args: --append-system-prompt`、`max_turns`/`model`/`allowed_tools`/`disallowed_tools`/`mcp_config` → `claude_args`、`claude_env` → `settings`、`timeout_minutes` → job 级 `timeout-minutes`
  authority:: 高
  verified:: 2026-09-13

- 来源:: 本库上游仓库 `L-ingqin12/agent-knowledge-base`
  use_when:: 引用本库地址，或判断旧仓库名是否已失效时
  url:: https://github.com/L-ingqin12/agent-knowledge-base
  answers:: 本库现名为 agent-knowledge-base（HTTP 200）；旧名 `claude-code-knowledge` 仍在但返回 **HTTP 301 → 本仓库**（README 的 clone 命令即新名），故旧链接并非死链
  authority:: 高
  verified:: 2026-09-13

- 来源:: Hermes Agent issue #91958 / PR #91971（Kanban dispatcher 与 delegated-child 守卫）
  use_when:: 讨论 Kanban dispatcher「每 60s 轮询」「并发上限」时，区分上游缺陷与配置上限，避免把缺陷读成能力
  url:: https://github.com/NousResearch/hermes-agent/issues/91958
  answers:: dispatcher tick 误触 delegated-child 守卫导致 gateway crash-loop；修复 PR 见 https://github.com/NousResearch/hermes-agent/pull/91971（keep Kanban dispatch running after delegated tasks）——证明的是缺陷，不是「并发无上限」
  authority:: 中
  verified:: 2026-09-13

## C7 复核新增（2026-09-13）：ai-links 旧文档与 articles 收藏

> C7 簇回写实际打开并核对的上游来源（发布记录页 / 仓库 README / 媒体与第三方报道 / 官方论文页）。官方站点不可达的条目已在 `answers` 里写明「本轮未复核」的边界。

- 来源:: sickn33/agentic-awesome-skills 发布记录与创作者页（仓库改名证据）
  use_when:: 核对 agentic-awesome-skills（原 antigravity-awesome-skills）的当前仓库名、版本线与 star 量级
  url:: https://newreleases.io/project/github/sickn33/agentic-awesome-skills/release/v9.5.0
  answers:: 对旧 slug 的 v7.0.0 请求被规范化到 agentic-awesome-skills 并返回「sickn33/agentic-awesome-skills v7.0.0」；v9.5.0 发布说明头部「## [9.5.0] - 2026-04-03 - "Selective Installs and 30K Stars"」，正文 PR 链接仍写旧名（说明改名发生在 2026-04 之后）；创作者页 https://skillsmp.com/de/creators/sickn33/agentic-awesome-skills 以新名收录并外链新 slug，显示 45,632 stars。github.com 本轮不可达，重定向状态未用 API 独立复核
  authority:: 中
  verified:: 2026-09-13

- 来源:: diagram-design 仓库 README（图表类型数与兼容宿主）
  use_when:: 核对 diagram-design 的图表类型数量、兼容宿主与新增布局语法（引用「29 种」前先回查）
  url:: https://raw.githubusercontent.com/cathrynlavery/diagram-design/main/README.md
  answers:: 「39 editorial diagram types for Claude Code, Codex, Factory Droid, Pi, and Agent Skills-compatible hosts. Self-contained HTML + SVG. No shadows. No Mermaid slop.」；2.5.10 新增十种布局语法（Sankey / fishbone / Wardley map / kanban / user journey / deployment / dependency graph / UML class / story map / database schema），29 + 10 = 39；star 数本轮未复核
  authority:: 高
  verified:: 2026-09-13

- 来源:: 智源论文解读页 —《Prime Agent: A Self-Improving RLM Harness》
  use_when:: 核对 Prime Agent 的 ARC-AGI-3 成绩口径、作者与发布日期（避免把单项指标读成基准总成绩）
  url:: https://hub-assets-cache.baai.ac.cn/paper/18a79369-4af0-40b4-8961-aec9c15fda41
  answers:: 2026-08-24 发布；作者 11 人（Seth Karten, Alex L. Zhang, Kevin Thomas, Sebastian Müller, Elie Bakouch, Daniel Auras, Mika Senghaas, Fares Obeid, Konstantin Dunas, Johannes Hagemann, Sami Jaghouar）；「在 ARC-AGI-3 RHAE 基准上 Best@1 准确率从 30% 跃升至 95.5%」；所有代码、基准、prompt 规范开源；**页面不含「超人类专家基线」**，也没有「评测不透明 / 代码膨胀」类批评
  authority:: 中
  verified:: 2026-09-13

- 来源:: watermarks-remover 的媒体报道（star 数与「拒绝安装」）
  use_when:: 核对该工具「一天涨 2.6K stars」「11K stars」「会被拒绝安装」的数字出处
  url:: https://hub.baai.ac.cn/view/57185
  answers:: 2026-08-17 报道《Claude隐形水印被光速破解，GitHub一天狂揽2.6k星》，正文「上线仅一天……GitHub狂揽2.6k stars」；投资界 https://m.pedaily.cn/news/567749 《Claude水印已被破解，斩获11k Star，但会被拒绝安装》；两份报道均未说明拦截发生在哪一层（GitHub 仓库警告 / 包管理器拦截）
  authority:: 低
  verified:: 2026-09-13

- 来源:: learn-from-claudecode —「07. Retry & Resilience」（Claude Code withRetry.ts 分析）
  use_when:: 核对重试/降级阈值：529-only 回退、Fast mode 20s/10min、persistent retry 6h/30s、budget guard
  url:: https://raw.githubusercontent.com/nathanyjleeprojects/learn-from-claudecode/refs/heads/main/claude_code_07_retry_resilience.md
  answers:: 文件头注明 source = github.com/nirholas/claude-code，正文为 withRetry.ts (824 lines) 分析；「Model fallback chain…단, 529 overload에서만 트리거」；Fast mode ≤20s 维持（保 prompt cache）/ >20s 切 standard 且 ≥10 分钟 cooldown；persistent retry 6 小时 cap + 30 秒 heartbeat；`x-should-retry` 尊重但不盲信；budget guard（长 context 反复重传会成本爆炸）
  authority:: 中
  verified:: 2026-09-13

- 来源:: 张汉东《驾驭工程》第 6b 章 — API 通信层（重试、流式与降级工程）
  use_when:: 交叉印证 Claude Code 通信层的重试/流式/降级公开分析
  url:: https://zhanghandong.github.io/harness-engineering-from-cc-to-ai-coding/part2/ch06b.html
  answers:: 页面存在且章节标题与目录一致（《API 通信层 — 重试、流式与降级工程》），与 learn-from-claudecode 的分析同主题；注意这是**内容对应的公开上游分析**，不是微信转载文的原文
  authority:: 中
  verified:: 2026-09-13

- 来源:: Claude 定价与 prompt cache 换算（第三方）
  use_when:: 核对 Opus/Sonnet 现行单价与缓存换算（写 1.25× / 读 0.1×），判断旧价目表是否过期
  url:: https://wavespeed.ai/llm/anthropic/claude-opus-4.6
  answers:: FAQ 原文「$5.00 per million input tokens and $25.00 per million output tokens」；https://raw.githubusercontent.com/barmoshe/claude-creative-stack/refs/heads/main/knowledge/01-claude-ecosystem.md 列 Opus 4.5/4.6/4.7 同为 $5/$25、1M context、128k max output，5m cache write = 1.25× 输入 → $6.25、cache read = 0.1× 输入 → $0.50；查不到「Opus Fast Mode $30/$150」对应项
  authority:: 低
  verified:: 2026-09-13

- 来源:: 6551Team — Claude Code 设计指南（error recovery）
  use_when:: 核对错误恢复的边界条件：输出恢复上限、reactive compact 频次、模型回退后的状态清理
  url:: https://raw.githubusercontent.com/6551Team/claude-code-design-guide/refs/heads/main/architecture/17-%E9%94%99%E8%AF%AF%E6%81%A2%E5%A4%8D/error-recovery-en.md
  answers:: 「max_output_tokens recovery at most 3 times | query.ts:164 defines MAX_OUTPUT_TOKENS_RECOVERY_LIMIT = 3」；「reactive compact only once per loop iteration | hasAttemptedReactiveCompact flag」；「State cleanup after model fallback | Fallback requires clearing StreamingToolExecutor and stripping thinking signatures」；全文**没有**「3 次续跑 / 每次 <500 token 的收益递减检测」，也没有 70%/85%/100% 三级预警
  authority:: 中
  verified:: 2026-09-13

- 来源:: Claude Code 源码社区文档站 — analytics/telemetry
  use_when:: 核对诊断日志的用户可控开关（本地存储、显式上报、PII 剥离、隐私设置、禁用开关）
  url:: https://mintlify.wiki/saurav-shakya/Claude_Code-_Source_Code/reference/analytics-telemetry
  answers:: 「Diagnostic logs are stored locally. They are only transmitted when you explicitly trigger a report — for example by running /doctor or submitting feedback. No diagnostic data is sent in the background.」；PII 标记值用 `_PROTO_` 前缀的 payload key，在到达通用后端（如 Datadog）前剥离，只有一方事件记录导出器可见；`/privacy-settings`；`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`。**注意：这是社区源码文档站（对应 GitHub 仓库 saurav-shakya/Claude_Code-_Source_Code），不是 Anthropic 官方页**
  authority:: 低
  verified:: 2026-09-13

- 来源:: Claude Code 官方 costs 文档页
  use_when:: 需要成本/速率限制的官方口径时（本页可打开但正文本轮未取到，只能证明页面在线）
  url:: https://code.claude.com/docs/en/costs
  answers:: 页面标题 Manage costs effectively、HTTP 可打开；正文未取到，故「70%/85%/100% 三级预警」与「连续 3 次续跑 / 每次 <500 token」两组数字**无法据此证真**
  authority:: 高
  verified:: 2026-09-13

- 来源:: lhl/agentic-memory — Claude Code 记忆机制独立源码分析
  use_when:: 核对自动记忆系统的 Absence 类证据、Team 同步、写入侧门禁与 top-5 上限的真实位置
  url:: https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md
  answers:: 「No vector search, embeddings, or knowledge graph | Full source review of src/memdir/ | 0.95 | Confirmed absent」；「MEMORY.md truncation at 200 lines / 25KB | MAX_ENTRYPOINT_LINES, MAX_ENTRYPOINT_BYTES | 0.95 | Dual-cap with clear warning message」；「Sonnet selector picks up to 5 relevant memories per query (findRelevantMemories.ts, max_tokens: 256) | Limit is in the prompt, not hard-coded in parsing」；Team memory 服务端同步 + OAuth delta + teamMemSecretGuard.ts (0.85)；#2 主/后台 agent 每轮互斥 hasMemoryWritesSince；#9 无写入侧内容门禁；#10 覆盖式写入、无更正/版本语义
  authority:: 中
  verified:: 2026-09-13

- 来源:: 小林coding — Claude Code 记忆机制图解（《Claude-Code记忆机制源码拆解》的 canonical 原文）
  use_when:: 回查该文原文出处（微信链接为分发渠道、实测跳验证码）
  url:: https://xiaolinnote.com/claudecode/source/cc_memory.html
  answers:: 两层架构（CLAUDE.md 六层级 + 自动记忆系统）；四类型 user/feedback/project/reference；索引常驻、内容按需；Sonnet 当选择器选 top-5、过滤已露脸与工具文档；老化警告「2 天前的记忆主动加 stale 提醒」；站内另有同系列 cc_grep.html、cc_multi_agent.html
  authority:: 中
  verified:: 2026-09-13

- 来源:: Gemma Scope 2 报道（官方博文不可达时的替代证据）
  use_when:: 核对 Gemma Scope 2 的发布时间与覆盖范围（Gemma 3、SAE + transcoder、Matryoshka 训练）
  url:: https://www.opensourceforu.com/2025/12/google-deepmind-open-sources-gemma-scope-2/
  answers:: 标题《Google DeepMind Open Sources Gemma Scope 2》，URL 路径为 /2025/12/；AIbase https://www.aibase.com/zh/news/23944 给出覆盖整个 Gemma 3 系列（最大 270 亿参数）、含训练于每一层的 SAE 与 transcoder、chat 版专用可解释性工具。deepmind.google 直连失败，故「2025-12-19」这一具体日期本轮**未能独立复核**
  authority:: 中
  verified:: 2026-09-13

- 来源:: TransformerLens 文档站（Getting Started）
  use_when:: 找 TransformerLens 的系统教程入口（本库脚本之外唯一有完整教程的站）
  url:: https://transformerlensorg.github.io/TransformerLens/content/getting_started.html
  answers:: Getting Started / Getting Started in Mechanistic Interpretability / Gallery / TransformerLens 3.0 与 2.0 发布说明均在线；github.com 仓库页本轮不可达，存活状态未独立复核
  authority:: 高
  verified:: 2026-09-13

- 来源:: SAE-for-VLM（Pach et al., NeurIPS 2025）官方定位页
  use_when:: 核对「SAE 视觉特征单义性」论文的作者、会议与官方摘要口径（判断 MTurk 数字能否引用）
  url:: https://www.eml-munich.de/publication/sae-for-vlm
  answers:: 标题与 5 位作者序列（Mateusz Pach, Shyamgopal Karthik, Quentin Bouniot, Serge Belongie, Zeynep Akata）；NeurIPS 2025；摘要「with sparsity and wide latents being the most influential factors」；NeurIPS poster 页 https://neurips.cc/virtual/2025/loc/san-diego/poster/119210（San Diego 会场，另有 Mexico City；摘要末给 code 链接 github.com/ExplainableML/sae-for-vlm，页内有 OpenReview id DaNnkQJSQf）；**官方摘要含「a large-scale user study」但不给人数/次数/一致率**，故 71 人 / 1000 次 / 82.8% / 56.6% / 100% 无法据此核验
  authority:: 高
  verified:: 2026-09-13

- 来源:: ICLR 2025 官方 proceedings — PatchSAE
  use_when:: 核对 PatchSAE 的标题、4 位作者、会议归属与官方摘要口径
  url:: https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d5b603d631d595f56bc36b373458b27-Abstract-Conference.html
  answers:: 《Sparse autoencoders reveal selective remapping of visual concepts during adaptation》；Hyesu Lim, Jinho Choi, Jaegul Choo, Steffen Schneider；ICLR 2025，含官方 Paper-Conference.pdf；摘要可确证的只有「训在 CLIP ViT 上 / 数据来自 ImageNet / 下游图像分类 + prompt-based adaptation」，**未给「BatchTopK 比 L1 好」也未列 code 链接**；domain-shifted 数据集与评估协议需回原文
  authority:: 高
  verified:: 2026-09-13

- 来源:: DeepStack 项目页
  use_when:: 核对 DeepStack 的规范引用（标题、作者、会议、arXiv 号），替换「203 期引用」这类无效出处
  url:: https://deepstack-vl.github.io/
  answers:: 《DeepStack: Deeply Stacking Visual Tokens is Surprisingly Simple and Effective for LMMs》，Lingchen Meng 等，NeurIPS 2024，arXiv:2406.04334（BibTeX booktitle={NeurIPS}, year={2024}）；页面图示含「DeepStack for ViTs」的跨层视觉 token 注入
  authority:: 高
  verified:: 2026-09-13

- 来源:: CaFE 行证据（两条均不可用，登记待回查）
  use_when:: 复核「CaFE (arXiv:2509.00749)」这一编号是否成立
  url:: https://excv-workshop.github.io/publication/causal-interpretation-of-sparse-autoencoder-features-in-vision/poster.pdf
  answers:: 该 URL 返回 **404**（站点在线，accepted papers 列表中无此条）；https://ieeexplore.ieee.org/document/11498646/ 返回 HTTP 202 空响应；arxiv.org 直连失败 → 「arXiv:2509.00749 = CaFE」既不能证实也不能证伪，引用前需用 OpenAlex / Semantic Scholar API 复核题名
  authority:: 低
  verified:: 2026-09-13

- 来源:: agentpatterns-ai — Lost in the Middle（位置偏差的结构性归因与两条限定）
  use_when:: 核对位置偏差的成因与适用边界（几百 token 无中间区、长上下文微调模型退化更小）
  url:: https://raw.githubusercontent.com/agentpatterns-ai/website/refs/heads/main/context-engineering/lost-in-the-middle.md
  answers:: 引 Liu et al., 2023 (arXiv:2307.03172) 与 Hsieh et al., 2024 (arXiv:2406.16008)；把位置偏差追溯到 causal masking 与 RoPE 等结构性因素（"This is a structural property…not a quirk of any particular model"）；「When the whole input fits in a few hundred tokens, there is no meaningful middle zone」；「Models trained with long-context fine-tuning or instruction-following reinforcement show less middle-degradation; treat placement as a default safeguard, not a guarantee」
  authority:: 中
  verified:: 2026-09-13

- 来源:: 澎湃号·湃客 — Context Rot 术语出处的中文转述
  use_when:: 核对 Context Rot 的报告出处、作者与核心命题（引用该术语时给出处）
  url:: https://m.thepaper.cn/newsDetail_forward_31500760
  answers:: 2025-08-29 发布《上下文腐烂：当百万token成为AI模型的阿喀琉斯之踵》；「2025年7月，向量数据库公司 Chroma 发布了一份技术报告《Context Rot: How Increasing Input Tokens Impacts LLM Performance》」，作者 Kelly Hong、Anton Troynikov、Jeff Huber，评估 18 款主流 LLM；核心命题「输入长度增加本身就会导致性能下降，与任务复杂度无关」
  authority:: 低
  verified:: 2026-09-13

- 来源:: Liu et al.《Lost in the Middle》与 RULER 编号
  use_when:: 需要长上下文位置效应与长上下文评测基准的正式文献编号时
  url:: https://arxiv.org/abs/2307.03172
  answers:: Lost in the Middle: How Language Models Use Long Contexts（U 形位置效应的公认出处）；RULER = Hsieh et al., 2024, arXiv:2406.16008（编号由 agentpatterns-ai 证据页给出）。本轮 arxiv.org 直连不可达，未逐字复核页面，引用前请回原文
  authority:: 高
  verified:: 2026-09-13

## C6 复核新增（2026-09-13）：Hook 语义 / 子智能体 / OpenCode 原生 / Pi 与 Python 官方口径

> C6 簇（claude-ops / 架构模式 / 日志分析）复核时发现库内多处「把现象当结论」：hook 被当成 advisory、子智能体根本没有上限记载、Pi 被当成可以"Python SDK 同步调用"、FastAPI 被当成依赖 Gunicorn。以下 21 条是当轮取证依据，逐条 2026-09-13 实测。

- 来源:: Claude Code 官方文档 · Hooks（超时与 exit code 语义）
  use_when:: 判断「hook 超时 / 失败会不会阻断工具执行」，或设计自建门禁时
  url:: https://code.claude.com/docs/en/hooks
  answers:: PreToolUse「Claude Code sends the tool input as **JSON on stdin** to the hook」（示例脚本用 `jq -r '.tool_input.command'`）⇒ **hook 能读到 Bash 命令行**；官方表「| PreToolUse | Yes | **Blocks the tool call** |」⇒ **exit 2 阻断**（「Exit 2 means a blocking error… even a JSON permissionDecision of allow can't override it」），exit 1 等为 non-blocking；Timeouts 节逐字「A timed-out command, http, or mcp_tool hook **doesn't block** the tool call… don't count on a stalled hook to act as a gate」；路径写错（127）会静默失效（「a mistyped path in settings.json leaves the gate silently disabled」）；`command`/`http`/`mcp_tool` 默认 timeout = **600s**（30s 仅 `prompt` 类型及少数被下调事件）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 · Hooks guide（hook 能读什么、matcher 作用范围）
  use_when:: 澄清「matcher 是否限制 hook 能读到的字段」
  url:: https://code.claude.com/docs/en/hooks-guide
  answers:: matcher 只是 settings.json 里的**过滤字段**（纯工具名走精确匹配，含其它字符走 JS 非锚定正则），限制的是「**何时触发**」而非「hook 能读到什么」；本轮在官方页检索「matcher 限制 stdin 字段」为 NOT FOUND
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 · Tools reference（前后台子智能体 vs Bash 的 run_in_background）
  use_when:: 区分「Agent 工具的前后台」与「Bash 工具的 run_in_background」，避免把两个开关混写
  url:: https://code.claude.com/docs/en/tools-reference
  answers:: Agent 工具支持前台 / 后台子智能体（前后台由 fork 模式决定）；`run_in_background` 是 **Bash 工具**的参数而非 Agent 工具的
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 仓库 issue #17208（子智能体返回值截断，社区证据）
  use_when:: 判断「后台子智能体的返回值会不会被截断、能不能默认当完整结果用」
  url:: https://github.com/anthropics/claude-code/issues/17208
  answers:: `closed / not_planned`；正文逐字「With run_in_background: true, output is truncated to 30K chars」，并转引变更记录「v2.1.2: Fixed API context overflow...truncating to 30K chars」。**注意口径**：30K 来自 issue 正文对变更记录的转引，**现行官方文档没有子智能体返回值上限条款**（官方只有 maxTurns 触发的 partial output 与 Bash 工具约 30,000 字符内联上限），故只能写作「社区证据 / 变更记录显示」
  authority:: 中
  verified:: 2026-09-13

- 来源:: Claude Code 仓库 issue #27483（请求给 Task 工具加 max_return_size）
  use_when:: 佐证「返回值截断是已知问题且尚无参数可调」
  url:: https://github.com/anthropics/claude-code/issues/27483
  answers:: `closed / duplicate`（目标 #27482）；标题即「Add max_return_size parameter to Task tool for task-notification truncation」⇒ 反向证明**当时没有**可配置的返回长度上限
  authority:: 中
  verified:: 2026-09-13

- 来源:: OpenCode 官方文档 · Agents（原生 subagent 与并行调度）
  use_when:: 判断「OpenCode 是否必须依赖插件生态才能并行子智能体」
  url:: https://opencode.ai/docs/agents/
  answers:: 官方**内置三个 subagent：General、Explore、Scout**；General 描述逐字「A general-purpose agent… Has full tool access (except todo)… Use this to run multiple units of work in parallel.」；另有 `Task` 工具、`permission.task` 权限项、子会话导航 `session_child_first` / `child_cycle` / `parent`、agent steps 上限 ⇒ 「OpenCode 依赖插件生态」的旧表述已过时，第三方方案属**补充控制通道**
  authority:: 高
  verified:: 2026-09-13

- 来源:: opencode issue #19999（Ephemeral Sub-Agent Teams，已 not planned）
  use_when:: 判断「要不要等上游的原生 team() / Ephemeral Team API」
  url:: https://api.github.com/repos/anomalyco/opencode/issues/19999
  answers:: title「[FEATURE]: Ephemeral Sub-Agent Teams (parallel multi-agent orchestration)」，`state=closed`、`state_reason=not_planned`、`closed_by=github-actions[bot]` ⇒ **不要再等**，把「等待原生 Ephemeral Team API」的路径划掉
  authority:: 高
  verified:: 2026-09-13

- 来源:: opencode PR #20152（experimental team tool，未合并）
  use_when:: 与 issue #19999 配合，确认该能力没有落地实现
  url:: https://github.com/anomalyco/opencode/pull/20152
  answers:: 「feat(tool): add experimental team tool for parallel subagents」，`state=closed`、`merged=false`、`merged_at=null`
  authority:: 高
  verified:: 2026-09-13

- 来源:: GitHub 仓库 · feanor5555/opencode-agent-intercom
  use_when:: 核对「opencode-agent-intercom」这一第三方方案的仓库归属与能力描述
  url:: https://github.com/feanor5555/opencode-agent-intercom
  answers:: 官方 description 逐字「opencode plugin: bidirectional control channel from the primary agent to running subagents — async spawn, message injection, live status, abort」（库内引用少了「opencode plugin: 」前缀）；**版本 / commit 未锁**，引用前需固定 commit 并补「并行上限」的测法与原始输出
  authority:: 中
  verified:: 2026-09-13

- 来源:: Python 官方文档 · concurrent.futures（线程池默认值与长任务取舍）
  use_when:: 给 ThreadPoolExecutor 的 `max_workers` 找官方默认值，或判断「线程池适不适合跑 50–60s 长任务」
  url:: https://docs.python.org/3/library/concurrent.futures.html
  answers:: 默认值 = `min(32, os.cpu_count() + 4)`（3.13 起 `min(32, (os.process_cpu_count() or 1) + 4)`）——**没有「CPU 核数 ×2」这种官方口径**；3.8 变更条逐字「It utilizes at most 32 CPU cores for CPU bound tasks **which release the GIL**」⇒ 线程池收益来自会释放 GIL 的任务；同节逐字「**it is recommended that ThreadPoolExecutor not be used for long-running tasks**」（退出时所有线程会被 join，且该退出处理器在 `atexit` 之前执行）；提交队列容量在官方页检索为 NOT FOUND
  authority:: 高
  verified:: 2026-09-13

- 来源:: Tornado 官方文档 · IOLoop（线程安全与信号处理器）
  use_when:: 判断「能不能在 signal handler 里直接调 IOLoop.stop()」
  url:: https://www.tornadoweb.org/en/stable/ioloop.html
  answers:: 逐字「this is the only method in IOLoop that makes this thread-safety guarantee; all other interaction with the IOLoop must be done from that IOLoop's thread」；`add_callback` 明确「except from a signal handler」；官方另提供 `add_callback_from_signal`（6.4 起 deprecated，并注明「suspected to have been broken since Tornado 5.0」）⇒ 在信号处理器里直接 reschedule 不在保证范围内
  authority:: 高
  verified:: 2026-09-13

- 来源:: FastAPI 官方文档 · 手动部署（默认 ASGI server 是 Uvicorn）
  use_when:: 判断「FastAPI 是否依赖 Gunicorn」，或给选型理由找依据
  url:: https://fastapi.tiangolo.com/deployment/manually/
  answers:: 逐字「…an ASGI server program like **Uvicorn**, this is the one that comes by default in the `fastapi` command」「When you add FastAPI with something like `uv add fastapi[standard]` you already get `uvicorn[standard]` as well」⇒ **Gunicorn 的 UNIX-only 不构成排除 FastAPI 的理由**
  authority:: 高
  verified:: 2026-09-13

- 来源:: gunicorn.org（自述定位）
  use_when:: 需要说明 Gunicorn 是 WSGI / UNIX 定位时（**不要**拿它当「不支持 Windows」的硬证据）
  url:: https://gunicorn.org/
  answers:: 自述「Python WSGI HTTP Server for UNIX」；首页 / FAQ / install 三页**都没有**「不支持 Windows」的明文声明
  authority:: 中
  verified:: 2026-09-13

- 来源:: opencode-multi-agent-system 上游仓库（GitHub API）
  use_when:: 确认「上游仓库是否可达、是否归档」，纠正「不可达 / 待原作者确认」一类过期勘误
  url:: https://api.github.com/repos/L-ingqin12/opencode-multi-agent-system
  answers:: `private=false`、`archived=false`、`default_branch=master`、`created_at=2026-07-04T07:02:53Z`、`pushed_at=2026-07-04T12:33:50Z`，description「OpenCode多智能体协作系统: 1主Orchestrator+6专业子智能体」⇒ 仓库**公开可达**
  authority:: 高
  verified:: 2026-09-13

- 来源:: opencode-multi-agent-system · `.opencode/agent/orchestrator.md`（原文）
  use_when:: 核对状态机状态名、质量门数量、重试/升级硬约束
  url:: https://raw.githubusercontent.com/L-ingqin12/opencode-multi-agent-system/master/.opencode/agent/orchestrator.md
  answers:: 状态机总览逐字 `START → ANALYZE → DELEGATE → VERIFY → INTEGRATE → DONE` + **RETRY** + **ESCALATE**（retry ≥ 3 终态）；VERIFY 节分两张清单——代码生成类 `syntax`/`completeness`/`consistency`/`no_hallucination`、分析类 `specificity`/`actionable`/**`file_check`**（去重共 **7 个门**，`GATE:file_check` = 「引用的文件路径是否真实存在？」）；硬约束 `maxRetries = 3`、`maxTotalRounds = 10`、`sameFailureThreshold = 2` → 强制 ESCALATE
  authority:: 高
  verified:: 2026-09-13

- 来源:: Pi 官方文档站（入口）
  use_when:: 需要 Pi Agent 的一手文档时（替代 DeepWiki 一类 AI 生成页）
  url:: https://pi.dev/docs/latest
  answers:: 站点存在，导航覆盖 Overview / Quickstart / Providers / Security / Containerization / Settings / Sessions / Compaction / Extensions / Skills / Packages / Models / SDK / RPC / JSON / **Windows** / Termux；Windows 场景应引 `/docs/latest/windows` 而非「Web 搜索」
  authority:: 高
  verified:: 2026-09-13

- 来源:: Pi 官方文档 · SDK（内置工具名 / RPC / JSON 事件流）
  use_when:: 核对 Pi 的内置工具白名单，或判断「Pi 能不能跨进程集成、要不要自建 HTTP」
  url:: https://pi.dev/docs/latest/sdk
  answers:: 逐字「Built-in tool names: **read, bash, powershell, edit, write, grep, find, ls**」= **8 个**（**不含** `edit-diff`，整页与仓库 `docs/sdk.md` 检索 `edit-diff` 均 0 命中），同页另写「Default built-ins: read, bash, edit, write」；导航含 [RPC Mode](/docs/latest/rpc) 与 [JSON Event Stream Mode](/docs/latest/json)、`runRpcMode`、RPC Mode Alternative ⇒ 跨进程集成是官方路径。注：检索 `toolExecution` 为 0 命中（该页在 Extensions 节被截断，属「未能确证」）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Pi 仓库 README（All Packages 表）
  use_when:: 核对 Pi 现行 npm 作用域与包清单
  url:: https://raw.githubusercontent.com/earendil-works/pi/main/README.md
  answers:: All Packages 表逐字含 `@earendil-works/chord` 与 `@earendil-works/pi-telemetry` ⇒ 现行作用域是 `@earendil-works/*`，不是 `@mariozechner/*`
  authority:: 高
  verified:: 2026-09-13

- 来源:: badlogic/pi-mono（旧仓库名，已重定向）
  use_when:: 判断库内旧链接是否需要换成 canonical 仓库
  url:: https://api.github.com/repos/badlogic/pi-mono
  answers:: 跟随重定向后落到 `https://api.github.com/repositories/1035029907`，`full_name` = **earendil-works/pi**（`private=false`、`archived=false`，description「AI agent toolkit: unified LLM API, agent loop, TUI, coding agent CLI」，另有原始 301 + Location 头实测）⇒ 旧链接靠重定向才能打开，应换 canonical
  authority:: 高
  verified:: 2026-09-13

- 来源:: earendil-works/pi（canonical 仓库）
  use_when:: 引用 Pi 的仓库地址时用这个，而不是 badlogic/pi-mono
  url:: https://github.com/earendil-works/pi
  answers:: 现行仓库首页（与 `api.github.com/repos/badlogic/pi-mono` 重定向目标一致）
  authority:: 高
  verified:: 2026-09-13

- 来源:: GNU xargs 手册（`--no-run-if-empty` 语义）
  use_when:: 写 `xargs` 管道时判断「没有输入时命令会不会仍被执行一次」
  url:: https://man7.org/linux/man-pages/man1/xargs.1.html
  answers:: 逐字「`-r, --no-run-if-empty`: If the standard input does not contain any nonblanks, do not run the command. **Normally, the command is run once even if there is no input.**」⇒ `git diff --cached --name-only | xargs grep …` 在无暂存文件时仍会执行 grep 且不带文件参数（读 stdin，表现为卡住）；`--name-only` 还按空白切分会拆坏含空格的文件名
  authority:: 高
  verified:: 2026-09-13

见 [[CORRECTIONS]]、[[AGENTS]]。
