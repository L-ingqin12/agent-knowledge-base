---
title: AI 文章库索引（子 MOC）
aliases: [Articles Index, 文章索引, AI文章库, Articles-MOC]
tags: [moc, ai/learning]
created: 2026-08-17
updated: 2026-09-13
status: review
---

# AI 文章库索引 — 子 MOC

See also: [[AI-Links-KB-Home]] | [[2026-08-16-AI链接综述与归档]] | [[AI大模型开发]] | [[AGENTS]]

> [!abstract] 概述
> 2026-08-17 从远程仓库（`_install-tmp/akb-remote`）迁移来的技术文章合集：论文精读、源码拆解与系统设计。与 [[AI-Links-KB-Home]] 的「链接调研综述」互补——那边是 18 条收藏链接的调研（原写 16 条，2026-09-13 按主文档 §一 更正：05/05 × 3 + 08/16 × 13 + 08/18 追加 × 2），这里是「AI Agent / LLM 的原理与工程认知」深度文章。
> 每篇均可独立阅读，正文内用 `[[文件名]]` 交叉引用；frontmatter 已统一为 Obsidian 规范（title/aliases/tags/created/updated/status），原引用字段（source/source_urls/author/date/fetched_at）原样保留。

---

## 文档地图

### 🔬 可解释性 / SAE（3 篇）

打开模型黑盒，看它内部在算什么。

| 文档 | 回答的问题 | 日期（arXiv 首发） | 会议 | 规范标识 |
|------|-----------|------|------|------|
| [[给LLM做脑扫描-可解释性技术全景]] | 怎么给大模型做「CT/核磁/三维扫描」？四层技术栈与上手路径 | 2026-07-06（成文日） | —（本库综述） | 本库自撰，无外部 canonical |
| [[SAE-视觉特征单义性-NeurIPS2025]] | SAE 如何在视觉-语言模型里学到单义特征？因果干预怎么验证 | 2025-04-03 | NeurIPS 2025 | arXiv:2504.02821 · [NeurIPS poster 119210](https://neurips.cc/virtual/2025/loc/san-diego/poster/119210) · OpenReview `DaNnkQJSQf` · [EML Munich 出版页](https://www.eml-munich.de/publication/sae-for-vlm) |
| [[PatchSAE-概念重映射-ICLR2025]] | adaptation 期间视觉概念如何被选择性重映射？ | 2024-12-06 | ICLR 2025 | arXiv:2412.05276 · [ICLR proceedings（hash 3d5b603…）](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d5b603d631d595f56bc36b373458b27-Abstract-Conference.html) |

> [!info] 列名与规范标识（2026-09-13 补）
> 原表头只写「日期」，而这两列填的是 **arXiv 首发日**，会让 PatchSAE 的 2024-12-06 被误读成 ICLR 2024 的会议日期；故列名改为「日期（arXiv 首发）」并新增「会议」「规范标识」两列。规范标识用于在搜索结果里唯一锁定文献（会议届次 + 编号 + 可解析 id）。
> 索引层待补 canonical：[[Agent韧性架构分析-微信转载]] —— 微信原文（需验证码），其**内容对应的公开上游分析**见该文 frontmatter 与本文「canonical 登记」表。

### 🧠 上下文工程（2 篇）

有限注意力预算下如何经营 context。

| 文档 | 回答的问题 | 日期 |
|------|-----------|------|
| [[上下文工程-注意力预算与四层解法]] | 为什么窗口越大模型越蠢？注意力预算视角 + 四层解法 | 2026-06-10 |
| [[上下文工程落地实践-从理论到Claude-Code实现]] | 上述理论如何在 Claude Code 源码里落地？ | 2026-06-22 |

### 🧩 Skill 系统与管理（5 篇）

Skill 从「几个」长到「几百个」后的组织问题。

| 文档 | 回答的问题 | 日期 |
|------|-----------|------|
| [[Claude-Code实用Skills参考]] | 有哪些实用 Skills？开发流程中怎么用？ | 2026-06-17 |
| [[Skill规模化管理-从渐进式披露到检索式发现]] | Skill 多到装不下时，如何从渐进式披露转向检索式发现？ | 2026-06-22 |
| [[Agent驱动Skill迁移设计]] | 如何用 Agent 驱动 Skill 系统迁移？审计怎么做？ | 2026-06-22 |
| [[日志检索分析系统-Skill管理Demo设计]] | Skill 管理框架（命名空间/依赖声明）落地 Demo 长什么样？ | 2026-06-22 |
| [[Anthropic-Skill系统深度分析]] | Anthropic Skill 系统的设计方案与实现方法全貌？ | 2026-06-12 |

### ⚙️ 机制拆解（3 篇）

Agent 产品内部是怎么实现的。

| 文档 | 回答的问题 | 日期 |
|------|-----------|------|
| [[Claude-Code记忆机制源码拆解]] | CLAUDE.md / 记忆机制在源码层面如何工作？ | 2026-06-02 |
| [[Loop-Engineering-深度拆解-从产品功能集到方法论包装]] | Loop 从产品功能集是怎么被包装成方法论的？ | 2026-06-25 |
| [[Agent韧性架构分析-微信转载]] | Claude Code 的容错/成本/认证/观测四支柱怎么设计？ | 2026-06-13 |

### 🤝 多智能体编排（1 篇）

生产级 Orchestrator-Worker 模式的一手复盘，本库多代理协议的外部锚点。

| 文档 | 回答的问题 | 日期 |
|------|-----------|------|
| [[Anthropic多智能体研究系统拆解]] | 编排者-工作者模式为什么有效？委派工程/上下文经济学(15×)/评测三件套怎么做？ | 2026-08-26 |

### 🏋️ 训练/复刻实录（1 篇）

真正跑一次训练会踩什么坑。

| 文档 | 回答的问题 | 日期 |
|------|-----------|------|
| [[预训练迷你Kimi-K3实录-章节总结]] | $252 单卡复刻迷你 Kimi K3：实际训练了什么、钱花在哪（MFU 2.5%）？ | 2026-08-18 |

---

## 文档关系图

    AI-Links-KB-Home
    └─ Articles-Index
        ├─ 可解释性/SAE: 3 篇
        │   ├─ 给LLM做脑扫描-可解释性技术全景
        │   │   ├─ → SAE-视觉特征单义性-NeurIPS2025
        │   │   └─ → PatchSAE-概念重映射-ICLR2025
        │   ├─ SAE-视觉特征单义性-NeurIPS2025
        │   │   └─ ↔ PatchSAE-概念重映射-ICLR2025
        │   └─ PatchSAE-概念重映射-ICLR2025
        ├─ 上下文工程: 2 篇
        │   ├─ 上下文工程-注意力预算与四层解法
        │   │   └─ → 上下文工程落地实践-从理论到Claude-Code实现
        │   └─ 上下文工程落地实践-从理论到Claude-Code实现
        │       └─ → Claude-Code记忆机制源码拆解
        ├─ Skill 系统: 5 篇
        │   ├─ Claude-Code实用Skills参考
        │   ├─ Skill规模化管理-从渐进式披露到检索式发现
        │   │   ├─ → Agent驱动Skill迁移设计
        │   │   ├─ → 日志检索分析系统-Skill管理Demo设计
        │   │   └─ → Claude-Code记忆机制源码拆解
        │   ├─ Agent驱动Skill迁移设计
        │   │   └─ → 日志检索分析系统-Skill管理Demo设计
        │   ├─ 日志检索分析系统-Skill管理Demo设计
        │   └─ Anthropic-Skill系统深度分析
        │       └─ → Claude-Code实用Skills参考
        ├─ 机制拆解: 3 篇
        │   ├─ Claude-Code记忆机制源码拆解
        │   ├─ Loop-Engineering-深度拆解-从产品功能集到方法论包装
        │   └─ Agent韧性架构分析-微信转载
        ├─ 多智能体编排: 1 篇
        │   └─ Anthropic多智能体研究系统拆解
        │       ├─ → main-subagent-realtime-interaction
        │       └─ → fan-out-subagent-pattern
        ├─ 训练实录: 1 篇
        │   └─ 预训练迷你Kimi-K3实录-章节总结
        │       └─ → AI大模型开发
        ├─ → AI大模型开发
        └─ → 2026-08-16-AI链接综述与归档

### 跨文档复用清单（2026-09-13 补）

关系图只画引用关系，不画**代码级复用依赖**——这类依赖一旦断链影响不止一篇。

| 被复用文件 | 相对路径 | 复用者 |
|---|---|---|
| `skill-registry.py`（`Skill` / `SkillRegistry` 类、`resolve_dependencies()`、`filter_by_context()`） | `scripts/claude-ops-deployments/demos/skill-registry.py` | [[Agent驱动Skill迁移设计]]、[[日志检索分析系统-Skill管理Demo设计]] |
| `skill-dependency-viz.py`（`get_top_level_skills()` 顶层判定） | `scripts/claude-ops-deployments/demos/skill-dependency-viz.py` | [[Agent驱动Skill迁移设计]] |

注：[[Agent驱动Skill迁移设计]] 原文所称的 `analyze_skills.py` / `parse_frontmatter()` 经全库检索**不存在**（`analyze_skills*` 零命中），已在该文标注；Phase 1 的 frontmatter 解析需改用上表脚本或新写。

### canonical 登记（2026-09-13 补）

| 文档 | canonical / 规范标识 | 状态 |
|---|---|---|
| [[SAE-视觉特征单义性-NeurIPS2025]] | arXiv:2504.02821；NeurIPS 2025 poster 119210；OpenReview `DaNnkQJSQf` | 已核 |
| [[PatchSAE-概念重映射-ICLR2025]] | arXiv:2412.05276；ICLR 2025 proceedings hash `3d5b603d631d595f56bc36b373458b27` | 已核（code 仓库存在性待 api.github.com 复核） |
| [[Claude-Code记忆机制源码拆解]] | https://xiaolinnote.com/claudecode/source/cc_memory.html （小林coding；微信链接为分发渠道） | 已核 |
| [[Agent韧性架构分析-微信转载]] | 微信原文 `https://mp.weixin.qq.com/s/3RUJT5zKWpj9Aeqe3ubSHg`（实测跳验证码）；内容对应的公开上游分析两条（learn-from-claudecode「07. Retry & Resilience」、张汉东《驾驭工程》ch06b） | 上游分析已核，「原文」出处**待补 canonical** |
| [[上下文工程-注意力预算与四层解法]] | 微信原文 `https://mp.weixin.qq.com/s/AI378SJcvKSPk9saXpOXZg`（实测跳验证码）；可核锚点：Lost in the Middle（arXiv:2307.03172）、Chroma《Context Rot》报告 | 原文待核，锚点已核 |

---

## 标签索引

- `#ai/learning` — 学习与精读：可解释性 3 篇、上下文工程落地实践、Skill 系统 5 篇、机制拆解 2 篇、训练实录 1 篇（实际合计 12 篇；原表述拆项为「机制拆解 3 篇」，但该组中 [[Agent韧性架构分析-微信转载]] 的 tags 是 `[ai/links, reference, ai/agent]`，不带 ai/learning，凑满 12 的第 12 篇为 [[预训练迷你Kimi-K3实录-章节总结]]）
- `#ai/skills` — Skill 系统相关：实用 Skills 参考、规模化管理、迁移设计、日志 Demo、Anthropic 深度分析（5 篇）
- `#ai/agent` — Agent 机制：记忆机制源码拆解、Loop-Engineering、Agent 韧性架构、多智能体研究系统拆解（4 篇）
- `#ai/links` — 微信转载：上下文工程理论、Agent 韧性架构分析（2 篇）
- `#reference` — 引用型文档：论文精读/转载原文出处（7 篇，原表述为 8 篇；逐文件统计的 7 篇为 Agent韧性架构分析-微信转载、PatchSAE、SAE-视觉特征单义性、上下文工程两篇、给LLM做脑扫描、预训练迷你Kimi-K3）
- `#moc` — 本页

---

## 关键数据

| 项 | 值 |
|---|---|
| 文章总数 | 15（全部位于 `ai-links/articles/`；其中 [[预训练迷你Kimi-K3实录-章节总结]] 为 2026-08-18 新增。原表述为「articles/ 12 篇 + 仓库根目录 2 篇 + 新增 1 篇」——目录内已无「仓库根目录」篇目，属迁移前旧布局残留） |
| 分组 | 6 组：可解释性 3 / 上下文工程 2 / Skill 5 / 机制拆解 3 / **多智能体编排 1（2026-08-26 新增）** / 训练实录 1 |
| 迁移日期 | 2026-08-17（源：`_install-tmp/akb-remote`，只读源未改动） |
| status 分布 | stable 11 篇 / review 4 篇（原表述为 3 篇；逐文件核对 15 篇 frontmatter 后为 4 篇：Agent驱动Skill迁移设计、Anthropic多智能体研究系统拆解、Skill规模化管理-从渐进式披露到检索式发现、日志检索分析系统-Skill管理Demo设计；11 + 4 = 15 方与「文章总数」自洽） |
| 命名调整 | 2 篇改为主语义中文命名：`Agent韧性架构分析-微信转载.md`、`Anthropic-Skill系统深度分析.md` |

---

## 阅读线索

- **想搞懂模型内部** → 可解释性三篇：先 [[给LLM做脑扫描-可解释性技术全景]] 建立全景，再深入 [[SAE-视觉特征单义性-NeurIPS2025]]、[[PatchSAE-概念重映射-ICLR2025]]。
- **想把 Agent 做稳/做省** → 上下文工程两篇（理论 → 落地），辅以 [[Agent韧性架构分析-微信转载]]（容错/成本四支柱）。
- **想管理规模化 Skill** → [[Claude-Code实用Skills参考]]（有什么可用）→ [[Anthropic-Skill系统深度分析]]（设计原理）→ [[Skill规模化管理-从渐进式披露到检索式发现]]（规模化方案）→ [[Agent驱动Skill迁移设计]] + [[日志检索分析系统-Skill管理Demo设计]]（落地）。
- **想懂 Claude Code 内部** → [[Claude-Code记忆机制源码拆解]] → [[Loop-Engineering-深度拆解-从产品功能集到方法论包装]]。
- **想搭多代理系统** → [[Anthropic多智能体研究系统拆解]]（生产级编排者-工作者：委派工程/15× token 经济学/评测三件套），对照本库 [[main-subagent-realtime-interaction]] 协议与 [[fan-out-subagent-pattern]]。
- **想搞一次真实的预训练** → [[预训练迷你Kimi-K3实录-章节总结]]（先测量再优化：MFU 只有 2.5% 时钱花在哪）。

## 另见

- [[AI-Links-KB-Home]] — 父 MOC（本页入口）
- [[2026-08-16-AI链接综述与归档]] — 链接调研综述（文章库的姊妹文档）
- [[AI大模型开发]] — LLM 开发笔记（可解释性/注意力机制的姊妹主题）

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 「status 分布 = stable 11 / review 3」与同表「文章总数 15」对不上 | 更正为 review 4 篇并逐篇列名；依据 15 篇 frontmatter 逐文件核对（11 + 4 = 15） |
| 纠错 | 「文章总数」拆分写「articles/ 12 + 仓库根目录 2 + 新增 1」，目录内已无仓库根目录篇目 | 改为「15 篇全部位于 `ai-links/articles/`」，并注明 K3 章节总结为 08-18 新增；依据目录实际清点（16 个 .md = 15 正文 + 索引自身） |
| 纠错 | `#reference` 记 8 篇 | 更正为 7 篇并逐篇列名；依据 15 篇 tags 逐文件统计 |
| 纠错 | `#ai/learning` 拆项「机制拆解 3 篇」 | 更正为「机制拆解 2 篇 + 训练实录 1 篇」合计 12 篇，并说明第三篇带的是 `ai/links`；依据 tags 统计 |
| 纠错 | 可解释性表列名只写「日期」，实为 arXiv 首发日 | 列名改为「日期（arXiv 首发）」，新增「会议」列；依据 NeurIPS / ICLR 官方页 |
| 补疏漏 | 索引层无「规范标识」，读者无法唯一锁定文献 | 新增「规范标识」列与「canonical 登记」表（含 arXiv / 会议 / OpenReview / proceedings hash）；依据各官方页 |
| 补疏漏 | 关系图不画跨文档代码级复用依赖 | 新增「跨文档复用清单」表（被复用文件 / 相对路径 / 复用者）；依据脚本逐行核对 |

- 回链：[[CORRECTIONS]]
