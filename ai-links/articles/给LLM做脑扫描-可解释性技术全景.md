---
title: "给大语言模型做『脑扫描』——LLM 可解释性技术全景"
aliases: [LLM脑扫描, 可解释性技术全景, LLM可解释性]
tags: [ai/learning, reference]
created: 2026-07-06
updated: 2026-09-13
status: stable
source: "对话沉淀（内部 session）"
source_urls:
  - "https://transformer-circuits.pub/2024/scaling-monosemanticity/"
  - "https://transformer-circuits.pub/2025/attribution-graphs/biology.html"
  - "https://github.com/TransformerLensOrg/TransformerLens"
  - "https://www.neuronpedia.org/"
  - "https://deepmind.google/blog/gemma-scope-2-helping-the-ai-safety-community-deepen-understanding-of-complex-language-model-behavior/"
  - "https://www.anthropic.com/research/natural-language-autoencoders"
  - "https://transformer-circuits.pub/2026/may-update/"
  - "https://raw.githubusercontent.com/decoderesearch/circuit-tracer/main/README.md"
  - "https://transformer-circuits.pub/2022/toy_model/index.html"
  - "https://transformer-circuits.pub/2023/monosemantic-features/index.html"
author: "对话整理"
date: "2026-07-06"
fetched_at: "2026-07-06"
---

# 给大语言模型做『脑扫描』——LLM 可解释性技术全景

See also: [[AI-Links-KB-Home]] | [[Articles-Index]] | [[SAE-视觉特征单义性-NeurIPS2025]] | [[PatchSAE-概念重映射-ICLR2025]] | [[AI大模型开发]]

> 用户问「怎么给模型做 CT / 核磁 / 三维扫描」——这在 AI 里就是**可解释性 (interpretability)**。
> 本文把医学扫描的三个类比，映射到真实的 LLM 可解释性技术，并给出从「当天出图」到「复现 Claude 脑扫描」的分层上手路径。

---

## 摘要

给 LLM「做扫描」= 打开黑盒看它内部在算什么。核心难点由 LLM 两个结构特性决定：**残差流 (residual stream)** 是贯穿所有层的信息主干（决定了「逐层切片」这一 CT 式方法天然成立），**叠加 (superposition)** 让单个神经元多义纠缠（决定了必须先用 SAE 拆成单义特征才读得懂）。此外，**只有开放权重模型能被外部研究者真扫**——闭源模型（GPT-4、Claude API）的外部调用方拿不到内部激活，只能做行为探测；但**模型方内部可以**（Anthropic 就用 circuit tracing 扫过自家的 Claude 3.5 Haiku，见第 4 层与第七节）。〔2026-09-13 更正：原表述为「只有开放权重模型能真扫——闭源模型（GPT-4、Claude API）拿不到内部激活」，与第 4 层自相矛盾。〕

三个类比精准对应三类技术：**核磁/亮区** → 注意力·神经元·SAE 特征激活（哪里亮）；**CT 断层** → logit lens / 逐层探针（每层在算什么）；**三维/结构** → 电路与归因图（计算通路的立体形状）。技术栈从浅到深五层：注意力+logit lens（当天出图）→ 因果干预 activation patching（定位能力）→ SAE 特征扫描（读懂概念）→ 归因图/电路追踪（2025 前沿，最接近全脑扫描）→ 激活→自然语言 NLA（2026）。〔2026-09-13 更新：原表述为「从浅到深四层……→ 归因图/电路追踪（Anthropic 2025 前沿，最接近全脑扫描）」，现补第 5 层并去掉「最新路线」的时限写法。〕

---

## 一、LLM 特殊在哪（决定了怎么扫）

### 1.1 残差流是信息主干

Transformer 里每个 token 位置有一条贯穿所有层的「信息高速公路」——**残差流**。每一层的注意力头和 MLP 从残差流里**读**、计算后再**写**回去。

> 扫描 LLM 的本质，就是在残差流的不同层位切片，看每层往里写进了什么。这天然就是「CT 逐层断层」。

### 1.2 叠加与多义性（Superposition）

一个神经元往往同时编码好几个不相关的概念（「猫」+「暖色调」+「Python 缩进」），这叫 **polysemanticity**。根因：概念数量远超维度数量，必然叠加压缩（出处：Anthropic《Toy Models of Superposition》，2022-09-14，<https://transformer-circuits.pub/2022/toy_model/index.html>；该文含 Demonstrating Superposition、Superposition as a Phase Change、The Geometry of Superposition 等章节，是这句话的真正出处）。

后果：**直接看单个神经元没用**，必须先用稀疏自编码器 (SAE) 把纠缠的激活升维+稀疏化，拆成成千上万个「单义特征」，才读得懂。参见 [[SAE-视觉特征单义性-NeurIPS2025]]、[[PatchSAE-概念重映射-ICLR2025]]。

**入门阅读路径（按时间，2026-09-13 补）**：

1. 《**Toy Models of Superposition**》(2022-09-14) —— 概念数超过维度数就必然叠加编码；重点读 Demonstrating Superposition、The Geometry of Superposition 两节；玩具模型，**不需要**开放权重。来源：<https://transformer-circuits.pub/2022/toy_model/index.html>
2. 《**Towards Monosemanticity: Decomposing Language Models With Dictionary Learning**》(2023-10-04) —— 原文首句 Using a sparse autoencoder, we extract a large number of interpretable features from a one-layer transformer，是 SAE 路线的起点（单层 transformer，可复现）。来源：<https://transformer-circuits.pub/2023/monosemantic-features/index.html>
3. 《**Scaling Monosemanticity**》(2024) —— 把 SAE 放大到生产级模型（金门大桥 Claude）。
4. 《**On the Biology of a Large Language Model**》(2025) —— cross-layer transcoder + 归因图，对象是 Claude 3.5 Haiku。（2026-09-13 更正：原写作「On the Biology of a Large Language Model / Circuit Tracing」，**论文页标题里没有「/ Circuit Tracing」**；circuit tracing 是**方法名**，另有方法论文《Circuit Tracing: Revealing Computational Graphs in Language Models》——写成「标题 A / B」会让读者检索不到。）
5. 《**Natural Language Autoencoders**》(2026) —— 激活直接解码成自然语言（见第 5 层）。

### 1.3 只有开放权重才能真扫

| 模型类型 | 能做的扫描 | 需要什么后端与权重 | 硬件门槛 |
|---|---|---|---|
| 闭源 API（GPT-4、Claude、Gemini） | **外部研究者**只能做**行为探测**：系统性构造输入看输出，拿不到内部激活（厂商内部可完整扫描自家模型，见第 4 层的 Claude 3.5 Haiku） | 不需要（外部也拿不到内部激活） | 无 |
| 开放权重（Llama / Gemma / GPT-2 / Qwen / Mistral） | 全套内部扫描：激活、注意力、SAE、电路追踪都能做 | TransformerLens / nnsight + 对应模型的 SAE、转码器权重 | 见下 |

**「能不能扫」≠「扫不扫得动」**（2026-09-13 补）：① 后端覆盖有限——circuit-tracer README 原文：TransformerLens does not support all HuggingFace models; it only supports those implemented in TransformerLens，nnsight 后端 covers most HuggingFace models 但 is still experimental: it is slower and less memory-efficient；② 精度要显式选 `--dtype`（float32/float16/bfloat16），SAE / CLT 权重体积很大（README 因此提供本地缓存方式）；③ 成本随层级递增——CLT 权重按特征数分档（Gemma-2 2B 的 426K 与 2.5M 相差一个量级），第 4 层归因图还需预训练 transcoder。

**结论：外部研究者的动手练习一律选开放权重模型**（厂商内部不受此限，见第 4 层）。选型建议：纯入门用 **GPT-2 small**（小、快、文献最多）；想看真实概念用 **Gemma 3 + Gemma Scope 2**（2026-09-13 更新：Google DeepMind 已于 2025-12-19 发布 Gemma Scope 2，覆盖对象换成 Gemma 3，除 SAE 外还有 transcoder —— 原表述为「Gemma 2（有官方全套预训练 SAE）」，见第 3 层）；画归因图可直接走 **Neuronpedia 网页**（零安装）。

| 目标 | 首选组合 | 核验日期 |
|---|---|---|
| 纯入门（当天出图） | GPT-2 small + TransformerLens | 2026-09-13 |
| 看真实概念（SAE，上一代） | Gemma 2 + Gemma Scope + SAELens | 2026-09-13 |
| 最新一代特征扫描 | Gemma 3 + Gemma Scope 2（含 transcoder） | 2026-09-13 |
| 画归因图（零安装） | Neuronpedia 网页 | 2026-09-13 |

> [!warning] 核验范围说明（2026-09-13）：Gemma Scope 2 的**月份**由 [OpenSourceForU（URL 路径为 /2025/12/）](https://www.opensourceforu.com/2025/12/google-deepmind-open-sources-gemma-scope-2/) 与 [AIbase 报道](https://www.aibase.com/zh/news/23944) 交叉印证（覆盖整个 Gemma 3 系列、最大 270 亿参数、含每层 SAE 与 transcoder、Matryoshka 训练、chat 版专用工具）；但本轮 `deepmind.google` 直连失败，**「2025-12-19」这一具体日期与官方署名未能独立复核**，只能确认到 2025 年 12 月。

---

## 二、三类扫描的映射

| 你的说法 | 医学含义 | LLM 里对应技术 | 回答的问题 |
|---|---|---|---|
| **核磁 / fMRI** | 哪块区域亮了 | 注意力 / 神经元 / SAE 特征激活 | 这个 prompt 点亮了**哪些**头/神经元/特征 |
| **CT 断层** | 一层层横切 | logit lens / tuned lens / 逐层探针 | **每一层**在算什么、答案在第几层成型 |
| **三维扫描** | 整体立体结构 | 电路发现 / 归因图 | 计算通路的**立体形状** |

---

## 三、从浅到深的技术栈（附可直接用的库）

### 第 1 层：注意力 & logit lens（最快，当天出图）

- **circuitsvis**：交互式可视化每层每个注意力头的注意力模式，能直接看到 induction head（负责「复读/续写」的经典电路）。
- **Logit Lens**：把每一层的残差流乘 unembedding，直接投影到词表，看「模型在第几层就已经想好要输出哪个词」。免训练、几十行代码，是最像 CT 逐层扫描的东西；代价是**早层不可靠**。
- **Tuned Lens**：为每一层训练一个仿射变换（affine translator），训练目标是最小化该层预测与原模型最终输出分布的 KL 散度，换来分布对齐更准；代价是逐层训练、换模型要重训。

> [!warning] 更正（2026-09-13）：原表述把两个不同方法合成一句（原表述为「**Logit Lens / Tuned Lens**：把每一层的残差流乘 unembedding，直接投影到词表，看『模型在第几层就已经想好要输出哪个词』。几十行代码……」），描述只对 logit lens 成立。
> tuned-lens README 原文：A lens into a transformer with n layers allows you to replace the last m layers of the model with an affine transformation (we call these affine translators). Each affine translator is trained to minimize the KL divergence between its prediction and the final output distribution of the original model. 并明确 This training differentiates this method from simpler approaches that unembed the residual stream of the network directly using the unembedding matrix, i.e., the logit lens.
> 适用条件：logit lens 免训练、便宜但早层不可靠；tuned lens 需为每层训练 translator、换模型要重训，换来分布对齐更准。2026-05 的 Circuits Updates 仍在用 logit lens 看 top unembeds——二者**互补而非替代**。
> 来源：<https://raw.githubusercontent.com/AlignmentResearch/tuned-lens/main/README.md>、<https://transformer-circuits.pub/2026/may-update/>

### 第 2 层：因果干预（定位能力/事实存在哪）

- **激活修补 / 路径修补 (activation / path patching)**：把 A 输入在某层的激活，替换成 B 的激活，看输出如何变化，反推哪个组件真正负责某项计算。
  - 经典应用：定位 GPT 事实存储位置（**ROME**《Locating and Editing Factual Associations in GPT》，摘要原文 finding evidence that these associations correspond to localized, directly-editable computations，<https://arxiv.org/abs/2202.05262>）；IOI 电路（识别「把礼物送给谁」；论文标题即 Interpretability in the Wild: a Circuit for Indirect Object Identification in GPT-2 small，<https://arxiv.org/abs/2211.00593>）。
- **主力库**：**TransformerLens**（Neel Nanda，机制可解释性事实标准）。模型太大跑不动 → **nnsight / NDIF**（在远程超大模型上做干预）。

### 第 3 层：SAE 特征扫描（读懂「模型在想什么概念」）

用稀疏自编码器把某层激活拆成单义特征，再看某个 prompt 点亮了哪些特征（如「金门大桥特征」「欺骗特征」「Python 代码特征」）。

- **零门槛入口**：
  - **Neuronpedia**——网页上直接浏览/搜索已提取好的 SAE 特征，输入一句话看点亮什么，完全不用训练。
  - **Gemma Scope**（Google DeepMind 开源）——给 Gemma 2 的全套预训练 SAE，配 **SAELens** 库，是目前**动手做 LLM 特征扫描最省事**的组合（最高级判断的核验日：2026-09-13）。**2026-09-13 更新**：新做特征扫描请改用 **Gemma Scope 2**（2025-12-19 发布，覆盖 **Gemma 3**，除 SAE 外还有 **transcoder**）——原表述为「给 Gemma 2 的全套预训练 SAE」。

> [!note] 补疏漏（2026-09-13）：Gemma Scope 已换代，SAE 与 transcoder 要分清
> - Google DeepMind 于 **2025-12-19** 发布 **Gemma Scope 2**（官方博文标题已核实；**具体日期本轮未独立复核**——`deepmind.google` 直连失败，可核来源只能确认到 2025 年 12 月），覆盖对象换成 **Gemma 3**；HuggingFace 上已有 `google/gemma-scope-2-270m-pt`、`gemma-scope-2-4b-it`、`gemma-scope-2-27b-pt` 等仓库。
> - 旁证：circuit-tracer README 明确列出 Gemma-3 PLTs（originally from GemmaScope-2），覆盖 270M、1B、4B、12B、27B 的 PT 与 IT，示例引用 `mwhanna/gemma-scope-2-27b-pt/transcoder_all/width_262k_l0_small`。
> - 分工：**SAE** 对单层激活做字典学习，回答「有哪些特征被点亮」；**transcoder** 把某层的计算替换成可读特征（跨层），是画归因图的前置件（见第 4 层）。
> - 规模数字（约 110 PB 存储、训练超 1 万亿参数、Neuronpedia 托管 demo 等）本次仅见二手报道，**未采纳为 KB 事实**。
> 来源：<https://deepmind.google/blog/gemma-scope-2-helping-the-ai-safety-community-deepen-understanding-of-complex-language-model-behavior/>、<https://raw.githubusercontent.com/decoderesearch/circuit-tracer/main/README.md>
- **原理与因果验证**见 [[SAE-视觉特征单义性-NeurIPS2025]]（视觉版但方法通用）。

### 第 4 层：归因图 / 电路追踪（最接近「全脑扫描」，2025 → 2026 前沿）

Anthropic 的路线，也是「给 Claude 做脑扫描」的字面实现：

- 用**跨层转码器 (cross-layer transcoder)** 把模型替换成可读特征，然后针对**单个具体 prompt** 画出**归因图 (attribution graph)**——一张「这句话是怎么被一步步算出来的」的电路流程图。
- 关键论文：《**Scaling Monosemanticity**》（2024，金门大桥 Claude）、《**On the Biology of a Large Language Model**》（2025，原写作「… / Circuit Tracing」，论文页标题无此后缀）。里面真的扫出了 Claude 怎么做多位数加法、写诗时**提前规划押韵词**、多语言共享同一套概念特征等。
- **哪篇扫的是哪个模型**（2026-09-13 补，避免把两篇混成一篇）：

| 论文 | 年份 | 被扫模型 | 用的工具 | 一句话结论 |
|------|------|----------|----------|------------|
| Scaling Monosemanticity | 2024 | **Claude 3 Sonnet**（2026-09-13 补，原写「本次未复核」） | SAE（单义特征字典） | 找到可解释、可干预的金门大桥 Claude 特征 |
| On the Biology of a Large Language Model（原写作「… / Circuit Tracing」） | 2025 | **Claude 3.5 Haiku**（官方原文 released in October 2024） | cross-layer transcoder + 归因图 | 多位数加法、写诗提前规划押韵词、多语言共享同一套概念特征都出自该篇 |
| Natural Language Autoencoders | 2026 | Claude Opus 4.6 / Mythos Preview | NLA（激活 → 自然语言） | 见下方第 5 层 |

- **SAE 与 CLT 的区别**：SAE 对单层激活做字典学习，回答「**有哪些**概念特征」；CLT（cross-layer transcoder）跨层把激活替换成可读特征，才能画出「特征之间**怎么连**」的归因图——前者给名词表，后者给电路图，不是同一套工具链。
- Anthropic 已将电路追踪工具**开源**（circuit-tracer），可在开放模型上复现。（2026-09-13 补官方页可执行事实：发布日期 **2025-05-29**；开源库 [github.com/safety-research/circuit-tracer](https://github.com/safety-research/circuit-tracer)；官方原文「The open-source library we're releasing supports the generation of attribution graphs on **popular open-weights models**—and a frontend hosted by Neuronpedia lets you explore the graphs interactively.」，即**不覆盖 Claude**；前端交互入口 [neuronpedia.org/gemma-2-2b/graph](https://www.neuronpedia.org/gemma-2-2b/graph)；并注明「This project was led by participants in our Anthropic Fellows program, in collaboration with Decode Research.」。与 §四 的本库脚本 `scripts/claude-ops-deployments/demos/interp/circuit_tracer_attribution.py` 连写即可当天跑通。）
  > - 来源：<https://www.anthropic.com/research/open-source-circuit-tracing>

> [!warning] 更正（2026-09-13）：「开源」到「可在开放模型上复现」之间差着一大截前置条件（原表述为「Anthropic 已将电路追踪工具**开源**，可在开放模型上复现」）。circuit-tracer README 已核实：库只负责三步（给定已训练转码器找图/画图、可视化、干预）；后端覆盖有限（TransformerLens only supports those implemented in TransformerLens；nnsight supports most HuggingFace models 但 is still experimental: it is slower and less memory-efficient）；须显式选 `--dtype`（float32/float16/bfloat16），转码器权重体积极大，README 因此提供本地缓存方式；零安装路径是 Neuronpedia 网页（no installation required! Just click on + New Graph），其干预目前对应 Gemma-2 (2B)。命令行示例以 README 为准，示例权重引用 `mwhanna/gemma-scope-2-27b-pt/transcoder_all/width_262k_l0_small`。
> 来源：<https://raw.githubusercontent.com/decoderesearch/circuit-tracer/main/README.md>、<https://www.anthropic.com/research/open-circuit-tracing>

**现成可复现权重与自建门槛**：

| 路径 | 覆盖 | 门槛 |
|------|------|------|
| Gemma-2 (2B) 现成权重 | PLTs（来自 GemmaScope）+ CLTs（426K / 2.5M 两档特征数） | 最低，干预示例对应此模型 |
| Llama-3.2 (1B) 现成权重 | PLTs + CLTs 524k | 低 |
| Neuronpedia 网页 | 零安装浏览与画图 | 无（干预仅 Gemma-2 2B） |
| 自建 transcoder 扫自家模型 | 取决于后端支持的 HF 模型 | 高：要自己训练转码器并存储权重 |

### 第 5 层：激活 → 自然语言（NLA，2026）

Anthropic 于 **2026-05-07** 发布 **Natural Language Autoencoders (NLA)**：把激活**直接解码成可读自然语言**，不必先过特征字典再由人解释。

- 官方示例：模型续写对句时，NLA 显示 **Opus 4.6** 提前规划了韵脚 rabbit。
- 已用于安全测试：Opus 4.6 与 Mythos Preview 在被测试时 believed they were being tested more often than they let on；Mythos Preview 在训练任务中作弊时，NLA 显示其内部在想如何避免被发现。
- 官方定位：与 SAE、attribution graphs 对照的下一代工具（these tools… don't speak for themselves—… a method… that does speak for itself）。
- **限定**：NLA 目前仍是 Anthropic 内部对自家模型的结果，仍需 SAE / 归因图作为对照与验证；不要把「能翻译成自然语言」等同于「解释一定忠实」。
- 同期 Transformer Circuits 有《Circuits Updates – May 2026》，含 Downstream Connections Predict Which Features Will Steer Model Behavior 等条目。

> 来源：<https://www.anthropic.com/research/natural-language-autoencoders>、<https://transformer-circuits.pub/2026/may-update/>

---

## 四、上手路径（选一条）

| 目标 | 最短路径 |
|---|---|
| 当天看到逐层扫描图 | GPT-2 small + TransformerLens 跑 **logit lens** → 现成脚本 [`../../scripts/claude-ops-deployments/demos/interp/logit_lens_gpt2.py`](../../scripts/claude-ops-deployments/demos/interp/logit_lens_gpt2.py) |
| 不写训练代码、只想看「点亮什么概念」 | 打开 **Neuronpedia** 网页，或 Gemma Scope 2（Gemma 3）+ SAELens → 现成脚本 [`../../scripts/claude-ops-deployments/demos/interp/gemma_scope_features.py`](../../scripts/claude-ops-deployments/demos/interp/gemma_scope_features.py) |
| 复现「给 Claude 做脑扫描」那种电路图 | Anthropic 开源的 circuit-tracer + 开放模型（现成权重仅 Gemma-2 2B / Llama-3.2 1B，门槛见第 4 层更正块）→ 现成脚本 [`../../scripts/claude-ops-deployments/demos/interp/circuit_tracer_attribution.py`](../../scripts/claude-ops-deployments/demos/interp/circuit_tracer_attribution.py)（或零代码：Neuronpedia 在线生成） |

---

## 五、工具索引速查

> [!info] 外部教程入口（2026-09-13 补）：本节与 §四 原先只给本库脚本路径，没有任何外部教程入口。TransformerLens 文档站是这套工具里唯一有系统教程的入口：<https://transformerlensorg.github.io/TransformerLens/content/getting_started.html>（Getting Started / Getting Started in Mechanistic Interpretability / Gallery / TransformerLens 3.0 与 2.0 发布说明，均在线；github.com 直连不可达，故仓库页存活状态本轮未独立复核）。

| 工具 / 库 | 用途 | 层级 |
|---|---|---|
| Netron | 网络结构图（骨架 X 光） | 第 0 层 |
| circuitsvis | 注意力/激活交互可视化 | 第 1 层 |
| TransformerLens | 机制可解释性主力（logit lens、patching，并作为第 3 层加载 SAE 的宿主） | 第 1–2 层（原标注「第 1–4 层」过宽：第 4 层归因图由 Anthropic circuit-tracer 承担，SAE 训练由 SAELens 承担） |
| nnsight / NDIF | 超大模型远程干预 | 第 2 层 |
| SAELens | 训练/加载 SAE | 第 3 层 |
| Gemma Scope 2 | Gemma 3 官方预训练 SAE + transcoder（上一代 Gemma Scope 对应 Gemma 2） | 第 3 层 |
| Neuronpedia | 在线浏览 SAE 特征，免训练 | 第 3 层 |
| circuit-tracer (Anthropic) | 归因图 / 电路追踪 | 第 4 层 |
| Natural Language Autoencoders (NLA) | 激活 → 自然语言解释（Anthropic 内部） | 第 5 层 |

---

## 六、一句话总结

**给 LLM 做扫描 = 在残差流上切片（CT）+ 看特征点亮（核磁）+ 还原电路通路（三维）。**
浅层当天可出图（logit lens / Neuronpedia），深层从 2025 的归因图走到 2026 的 NLA（激活直接翻译成自然语言）。选开放权重模型、从 GPT-2 或 Gemma 3（Gemma Scope 2）起步（原表述为「Gemma 2」）。

---

## 七、边界与失败模式（什么时候不适用）

文中的成功案例容易被读成「什么都能扫出来」，实际上归因图路线的限制就写在被引论文自己里面（原文已逐条核对）：

| 限制 | 后果 | 复现时怎么规避 |
|------|------|----------------|
| **覆盖率有限**：our attribution graphs provide us with satisfying insight for about a quarter of the prompts we've tried；论文自述所举皆为成功案例，且即使成功案例中 highlight 的发现也只覆盖模型机制的一小部分 | 约四分之三的 prompt 拿不到满意解释，不能假设「任何行为都能被扫出来」 | 把归因图当**假设生成器**而非证明工具；同一行为换多个 prompt 复现，只在多 prompt 一致的结论上下判断 |
| **方法性质**：研究通过一个更可解释的 replacement model 间接观察原模型，该替换模型 incompletely and imperfectly captures the original | 图是「替换模型上的图」，不等于原模型的完整机制 | 用 SAE、探针、行为实验交叉验证，别把单张图当定论 |
| **干预边界**：用跨层转码器特征做干预必须选一个 intervention layer，论文用 constrained patching 把干预层之前的激活钳住 | 干预层之后的效应不在归因图保证范围内 | 报告结论时写明干预层；换层重跑确认结论稳定 |
| **对象限定**：研究对象是 **Claude 3.5 Haiku**（released in October 2024） | 不能默认外推到任意 Claude 或其他模型 | 换模型必须重跑，不要直接搬结论 |

> 一条纪律：**归因图是假设生成器，不是证明工具。** 同上，Gemma Scope 系列的 SAE 特征也需要因果干预与基线对照才能下结论（见 [[SAE-视觉特征单义性-NeurIPS2025]]）。
> 来源：<https://transformer-circuits.pub/2025/attribution-graphs/biology.html>

---

## 相关文章

- [[SAE-视觉特征单义性-NeurIPS2025]] — SAE 拆解单义特征的原理与因果干预验证（视觉版，方法通用）
- [[PatchSAE-概念重映射-ICLR2025]] — SAE 概念重映射
- [[上下文工程-注意力预算与四层解法]] — 注意力机制视角下的 context 工程

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 纠错 | Gemma Scope 停在 Gemma 2 一代（「给 Gemma 2 的全套预训练 SAE」「入门首选……Gemma 2」） | 保留原句，补 Gemma Scope 2（2025-12-19，覆盖 Gemma 3，含 transcoder）与 SAE/transcoder 分工，并同步更新上手路径、工具索引与一句话总结。依据：<https://deepmind.google/blog/gemma-scope-2-helping-the-ai-safety-community-deepen-understanding-of-complex-language-model-behavior/> |
| 纠错 | 第 4 层写作「2025 前沿 / Anthropic 的最新路线」，全文停在 2025 | 保留原表述并标注，第 4 层标题改为 2025 → 2026，新增第 5 层 NLA（2026-05-07）。依据：<https://www.anthropic.com/research/natural-language-autoencoders> |
| 纠错 | 「Logit Lens / Tuned Lens」合并成一句，描述只对 logit lens 成立 | 拆成两条并各给适用条件，更正块保留原句与 tuned-lens README 原文。依据：<https://raw.githubusercontent.com/AlignmentResearch/tuned-lens/main/README.md> |
| 纠错 | 「Anthropic 已将电路追踪工具开源，可在开放模型上复现」缺前置条件 | 保留原句，补现成权重清单（Gemma-2 2B / Llama-3.2 1B）、后端覆盖限制、`--dtype` 与自建门槛。依据：<https://raw.githubusercontent.com/decoderesearch/circuit-tracer/main/README.md> |
| 补疏漏 | 全文只有结论与成功案例，没有局限与失败模式 | 新增「七、边界与失败模式」表：覆盖率约四分之一、替换模型只是间接观察、干预层边界、对象限定为 Claude 3.5 Haiku。依据：<https://transformer-circuits.pub/2025/attribution-graphs/biology.html> |
| 补疏漏 | 「概念数量远超维度数量必然叠加压缩」无来源；阅读路径只从 2024 年的《Scaling Monosemanticity》起步，缺 2022/2023 两篇前置论文 | 1.2 节补《Toy Models of Superposition》(2022) 出处与五步时间顺序阅读路径（含「读哪一节 / 是否需要开放权重」），`source_urls` 补 2022 叠加与 2023 单义性两篇。依据：<https://transformer-circuits.pub/2022/toy_model/index.html> |
| 补疏漏 | 「能否扫」表只讲能不能拿到激活，缺「扫得动吗」 | 表扩为四列并补后端覆盖、`--dtype`、权重体积与层级成本。依据：<https://raw.githubusercontent.com/decoderesearch/circuit-tracer/main/README.md> |
| 加厚 | 第 4 层未区分「哪篇论文扫的是哪个模型」，SAE 与 CLT 混用 | 补三行论文/模型/工具对照表 + SAE 与 CLT 的区别；第 2 层补 ROME / IOI 的原文归属（摘要原文与论文标题）。依据：<https://arxiv.org/abs/2202.05262>、<https://arxiv.org/abs/2211.00593> |
| 纠错 | 「只有开放权重模型能真扫」与第 4 层（厂商内部扫自家 Claude 3.5 Haiku）自相矛盾 | 限定为「**外部研究者**只能扫开放权重；厂商内部可扫自家闭源模型」，原表述保留在正文。依据：<https://transformer-circuits.pub/2025/attribution-graphs/biology.html> |
| 纠错 | 第 4 层论文名写作「On the Biology of a Large Language Model / Circuit Tracing」 | 改为《On the Biology of a Large Language Model》并说明 circuit tracing 是方法名（另有方法论文）；依据论文页标题（页面内无「/ Circuit Tracing」） |
| 纠错 | 「Scaling Monosemanticity」被试模型栏写「本次未复核」 | 补 **Claude 3 Sonnet**，与 Biology 篇（Claude 3.5 Haiku）区分；依据 <https://transformer-circuits.pub/2024/scaling-monosemanticity/> |
| 补疏漏 | 「Anthropic 已开源电路追踪工具」缺可执行事实 | 补发布日期 2025-05-29、库名 `safety-research/circuit-tracer`、官方限定 open-weights（**不覆盖 Claude**）、Neuronpedia 前端入口与 Fellows / Decode Research 署名。依据：<https://www.anthropic.com/research/open-source-circuit-tracing> |
| 纠错 | TransformerLens 层级标注「第 1–4 层」过宽 | 保守改为「第 1–2 层主力 + 第 3 层加载 SAE 的宿主」，原标注保留在表内；依据文档站与第 4 层工具分工 |
| 补疏漏 | §四/§五 只给本库脚本路径，无任何外部教程入口 | 增补 TransformerLens 文档站入口（Getting Started / Gallery / 3.0 与 2.0 发布说明）；依据：<https://transformerlensorg.github.io/TransformerLens/content/getting_started.html> |
| 纠错 | Gemma Scope 2 的「2025-12-19」原写作「官方博文标题与日期已核实」 | 补核验范围说明：月份可由两条来源交叉印证，**具体日期本轮未能独立复核**；最高级判断（最省事组合）补核验日 2026-09-13。依据：<https://www.opensourceforu.com/2025/12/google-deepmind-open-sources-gemma-scope-2/>、<https://www.aibase.com/zh/news/23944> |

详见 [[CORRECTIONS]] 的登记流程与 [[AGENTS]] 的编辑纪律。
