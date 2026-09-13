---
title: "Agent 驱动 Skill 系统迁移设计"
aliases: [Skill迁移设计, Skill审计, Agent驱动迁移]
tags: [ai/skills, ai/learning]
created: 2026-06-22
updated: 2026-09-13
status: review
source: "系统设计"
date: "2026-06-22"
fetched_at: "2026-06-22"
---

# Agent 驱动 Skill 系统迁移设计

See also: [[AI-Links-KB-Home]] | [[Articles-Index]] | [[Skill规模化管理-从渐进式披露到检索式发现]] | [[日志检索分析系统-Skill管理Demo设计]] | [[Claude-Code记忆机制源码拆解]]

## 背景

当前技能体系是**扁平发现式**——所有 skill 元信息列在 system prompt，模型被动匹配。10-50 个 skill 时完全够用，但数量增长后面临三个瓶颈：

1. System prompt 被 skill 元信息淹没（1000 skill × 30 token = 30000 token）
2. Skill 之间隐含的依赖关系靠模型猜测，不可靠
3. 无审计痕迹——skill 的加载、选择、废弃全无记录

目标：设计一个 **Agent 自主完成迁移** 的方案，将旧系统（扁平 skill 列表）迁移到新系统（命名空间 + 依赖声明 + 条件匹配 + 检索式发现），全程可审计。

> [!warning] 更正（2026-09-13）：上面的前提**已部分失效**——四件套里至少两件已由 Claude Code 原生提供，迁移目标应收窄（原表述为「当前技能体系是扁平发现式——所有 skill 元信息列在 system prompt，模型被动匹配」，并把目标定为「命名空间 + 依赖声明 + 条件匹配 + 检索式发现」四件套）。
> 1. **条件匹配已有**：SKILL.md frontmatter 支持 `paths`（官方原文：Glob patterns that limit when this skill is activated…… Claude loads the skill automatically only when working with files matching the patterns），与本文方案 C 的前置过滤是同一机制——但注意官方版是**运行时门控**（Path-scoped rules trigger when Claude reads files matching the pattern, not on every tool use），不是在候选池上提前过滤。
> 2. **命名空间已有**：插件技能调用形式为 `/plugin-name:skill-name`，天然带命名空间前缀。
> 3. **「按需」也已有部分实现**：`.claude/skills/` 子目录下的技能不在启动时加载，而是首次读/编辑该目录文件时才加载。
> 4. **削减元信息已有旋钮**：`skillOverrides` 可把技能降级为 `name-only` 或 `off`，`disable-model-invocation: true` 可禁止自动加载。
> 另注：第 1 条瓶颈里的「1000 skill × 30 token = 30000 token」沿用了一个自造系数（见 [[Skill规模化管理-从渐进式披露到检索式发现]] 摘要处的更正），本设计据此做筛选可以，但**不要把 30000 当作实测预算**，成本以 `/skill-doctor` 为准。
> **迁移设计应改写为「在原生机制之上只补两块：includes 依赖声明 + 检索式发现」**，并说明为何原生 `paths` + `skillOverrides` 不足以解决规模问题。
> 来源：https://code.claude.com/docs/en/skills ；https://code.claude.com/docs/en/plugins

## 迁移 Agent 设计

### 核心原则

1. **Git 全程追踪**：每一步迁移一个 commit，可回滚、可审计
2. **决策透明**：Agent 的每一个分类/命名/依赖推断决定，都输出到 audit log
3. **人工闸门**：迁移分阶段，每阶段完成后生成 diff review report，人工确认后继续
4. **幂等可重入**：迁移脚本可以安全重跑，不会重复创建或覆盖已迁移的 skill

### 迁移五阶段

```
Phase 1: 发现（Discovery）
  Agent 扫描旧系统 → 输出 Inventory Report
  ├── 列出所有 skill 文件的位置、大小、frontmatter
  ├── 分析每个 skill 的内容语义（调 LLM 做摘要）
  ├── 检测 skill 之间的文本引用关系（反向索引 grep）
  ├── 提取 frontmatter 元信息（name/description/type）
  └── 输出：discovery-report.json + discovery-report.md

Phase 2: 分类（Classification）
  Agent 基于 Discovery 结果做分类决策
  ├── 推断 namespace：根据 skill 内容和名称推断所属领域
  │   - 关键词匹配（规则粗筛）
  │   - LLM 分类（小模型发 skill 摘要，选 namespace）
  │   - 置信度标记（HIGH/MEDIUM/LOW/ESCALATE）
  ├── 推断依赖关系：检测 skill A 的内容是否引用了 skill B 的能力
  │   - 文本引用（grep 交叉引用模式）
  │   - 语义推断（LLM 判断 A 的工作流是否隐含需要 B）
  ├── 生成 paths glob 候选（基于 skill 内容中的文件类型引用）
  ├── 标记冲突：两个 skill 覆盖同一功能但参数不同
  └── 输出：classification-report.json（含置信度）

Phase 3: 审核（Human Review）
  生成可读的 diff preview，人工确认
  ├── 高置信度决策 → 绿色，建议自动执行
  ├── 中置信度决策 → 黄色，建议人工确认
  ├── 低置信度决策 → 红色，必须人工决策
  ├── 极低置信度（<0.2）→ 升级，建议新建 namespace 或重审输入
  ├── 依赖感知：如果 skill B 被拒且 B 是 A 的 includes 依赖，A 自动标记为 blocked
  └── 用户对每项选择：approve / reject / modify

Phase 4: 执行（Migration）
  只执行已审批的迁移决策
  ├── 创建目标目录结构（按 namespace 分层）
  ├── 迁移每个 skill 文件到新位置
  ├── 补全 frontmatter（namespace, paths, includes, optional_includes）← 字段合法性见下节「字段合法性分层」，勿直接写进顶层
  ├── 更新交叉引用（旧路径→新路径）
  ├── 生成 MEMORY.md 风格的 Skill Registry 索引
  ├── 每次 commit 粒度：单个 namespace（~5-10 skills）
  └── 输出：migration-log.jsonl（每条一行，含 timestamp + action + decision + trace_id）

Phase 5: 验证（Verification）
  Agent 验证迁移正确性
  ├── 依赖链完整性检查（所有 includes 目标存在且可解析）
  ├── 循环依赖检测（拓扑排序验证依赖图无环）
  ├── 条件匹配覆盖检查（paths glob 是否覆盖了 skill 描述的目标文件类型）
  ├── Token 预算对比（旧系统 vs 新系统的 system prompt 开销）
  └── 输出：verification-report.md
```

> [!warning] Phase 5 缺可判定门槛（2026-09-13 补）：上面四项检查只写「检查什么」，没有任何「多少算通过」的验收判据，因此 **Phase 5 无法自动判定结束**，也支撑不了文中反复强调的「人工闸门 + 幂等可重入」。下表是「迁移完成」的唯一客观定义：

| 检查项 | 通过门槛（可判定） | 数据来源 |
|---|---|---|
| 依赖链完整性 | 断裂 edge 数 = **0** | `classification-report.json` 的 includes 图 |
| 循环依赖 | 拓扑排序成功，且环路径报告为空 | 循环依赖预检步骤的输出 |
| 条件匹配覆盖 | 每条 `paths` glob 至少命中 1 个目标文件类型（推荐对每个声明的扩展名各造一个假路径做断言，见「验证补强」第 4 条） | paths 断言脚本 |
| Token 预算对比 | 新系统 system prompt 开销 ≤ 旧系统的 **X%**（X 须实测标定，**不得沿用 30000 的经验系数**） | 迁移前后 system prompt 实测 |

## 字段合法性分层（2026-09-13 补）

Phase 4 与「复用现有组件」把迁移产物写成补全 `namespace` / `paths` / `includes` / `optional_includes` 四类 frontmatter，但没有区分哪些是官方规范字段、哪些是自建解析器的私有约定——这是本设计最大的可移植性缺口。

| 字段 | 身份 | 在本机（Claude Code） | 分发到 Claude Code 之外 |
|------|------|---------------------|----------------------|
| `name` / `description` / `license` / `compatibility` / `metadata` / `allowed-tools` | Agent Skills 规范六键 | 生效 | 生效（唯一被接受的一组） |
| `paths` | Claude Code 一等 frontmatter 字段（与 `metadata` 并列） | 生效 | **失效**（被忽略） |
| `namespace` / `includes` / `optional_includes` | 私有扩展键 | Claude Code **不解释**，须由自建解析器读取 | **失效** |

四点约束：

1. Agent Skills 规范只认六个键：`name`、`description`、`license`、`compatibility`、`metadata`、`allowed-tools`。
2. 私有扩展键放进 frontmatter 顶层既不会被规范接受，也不会被 Claude Code 解释；唯一规范的做法是塞进 `metadata` map。
3. 但 Claude Code 对 `metadata` 的态度是「Free-form YAML map for your own key-value data…… Claude Code doesn't act on its contents」——**必须由自建解析器读取**；官方还特意提醒 `metadata` 不要复用 `paths` 这类 frontmatter 字段名作为键。
4. 官方明确：claude.ai 上传、Skills API、以及 `anthropics/skills` 的 `package_skill.py` 打包三种路径，只能用规范六字段。

**因此 Phase 3 的 review report 必须为每个技能标注「本机生效 / 仅自建工具生效 / 分发后丢失」**，否则迁移完成后一旦技能被分发出去，`paths` 会失效、`metadata` 里的依赖声明只有本工具认——这是一次静默的行为变更。

> 来源：https://agentskills.io/specification ；https://code.claude.com/docs/en/skills

### Phase 5→2 反馈循环

验证发现问题时不直接 git revert 全量回滚：
- Phase 5 标记特定断裂的依赖 edge
- 只对该 edge 涉及的 skill 重跑 Phase 2 分类
- Phase 4 增量迁移只处理被修复的项

### 循环依赖预检

在 Phase 4 执行前增加独立步骤：对完整的 {已批准依赖图} 运行拓扑排序。有环则阻止迁移并报告具体环路径。

### 反馈循环与环报告的工程化（2026-09-13 补）

上面两节合计不足 8 行，缺三样可执行的东西：

1. **环报告要有可机读格式**——直接扩展本文已有的 `audit.jsonl` schema：其中第 130 行本就有 `verification` 字段，可在里面写
   ```json
   {"cycle": ["a", "b", "c", "a"], "edge_ids": ["..."], "suggested_break": "b->c"}
   ```
   并与触发它的 `trace_id` 关联。否则人工无法定位到具体决策条目，「报告环路径」只是一句口号。
2. **失败要可回滚到单条决策**——本文已声明「每次迁移一个 namespace 一个 commit（粒度 ~5-10 skills/commit）」，edge 级修复也应当独立 commit，否则 `git revert` 的粒度对不上。
3. **增量重跑的收敛判据缺失**——Phase 5→2 循环目前没有终止条件，会出现「修复 A 破坏 B」的往复；应约定「同一 edge 重跑不超过 N 次，超出则升级人工」，并在 `audit.jsonl` 里记录重跑次数。

> [!note] 关于深度校验：官方 `@import` 体系的硬上限是四跳（memory 文档原文：Imported files can recursively import other files, with a maximum depth of four hops），但**本文两节讨论的是环检测，不是深度校验**，全文也不含任何深度数字——若要在预检里加「深度 ≤ 4」，那是新增建议，需另行论证并挂到实现处（见 [[Skill规模化管理-从渐进式披露到检索式发现]] 5.5 节的 `SkillLoader` 补注）。
> 来源：https://code.claude.com/docs/en/memory

## 验证补强（2026-09-13 补）

Phase 5 现有的四项（依赖链完整性、循环依赖检测、条件匹配覆盖、Token 预算对比）**全是结构验证**，缺了迁移唯一真正重要的验收：迁移前后技能还能不能被正确触发、触发后输出是否等价。应补四项：

1. **触发准确率回归**——为每个技能准备 should-trigger 与 should-not-trigger（重点是 near-miss 近失）查询集，每查询多次运行取触发率，迁移前后对比。官方口径「Seeing a skill trigger tells you Claude found it, not that it did what you intended」——**结构正确不代表触发正确**。
2. **效果基线对比**——同一批真实 prompt 在「技能可用 vs 禁用」下分别跑，且官方强调**必须新会话**（写技能时的残留上下文会掩盖指令缺口）。
3. **自动化门禁**——插件形态可用 `claude plugin eval`（隔离会话 with/without，自定义 grader 打分，默认阈值 1.0，低于阈值非零退出，可直接卡 CI）；单技能迭代可用 skill-creator 的 `evals/evals.json`。官方明确两种格式 `aren't interchangeable` / `its case format is separate`，选定一种后不要指望互相转换（见 [[Anthropic-Skill系统深度分析]] 3.8 节）。
4. **`paths` 必须断言而不是目检**——Phase 4 补的 `paths` 若写错**不会报错、只会静默不加载**，所以第 3 项「条件匹配覆盖检查」要落成自动化断言：对每个技能声明的扩展名各造一个假路径做 glob 匹配，命中失败即 fail。

> 来源：https://code.claude.com/docs/en/skills ；https://agentskills.io/skill-creation/evaluating-skills

## 审计设计

### 审计 trace 粒度

单条决策一条 trace（不是按 phase 记录），每个 namespace 推断、每个依赖推断都独立记录。

### 审计数据结构

```json
{
  "trace_id": "mig-20260622-a3f8",
  "timestamp": "2026-06-22T12:00:00Z",
  "phase": "classification",
  "action": "namespace|dependency|conflict|dedup|paths|rename|content|reject",
  "target": "skill_name.md",
  "source_hash": "sha256:abc123...",
  "decision": {
    "field": "namespace|includes|paths|...",
    "inferred_value": "logs/queries",
    "confidence": 0.87,
    "reasoning": "Agent 的推理过程",
    "implicit_deps": ["old_ref_a", "old_ref_b"],
    "alternatives": ["logs/alerts"],
    "llm_used": "sonnet",
    "prompt_hash": "sha256:..."
  },
  "blocked_by": ["dependency_skill_name"],
  "approval": "pending|approved|rejected|modified",
  "rejection_reason": null,
  "human_override_value": null,
  "git_commit": null,
  "verification": null
}
```

### 审计文件结构

```
migration-session-{id}/
├── audit.jsonl                # 所有阶段决策（追加写入）
├── snapshots/
│   ├── phase-1-registry.json  # Discovery 完整快照
│   ├── phase-2-registry.json  # Classification 完整快照
│   ├── phase-3-decisions.json # 人工审批结果
│   └── phase-4-registry.json  # Migration 完成快照
├── reports/
│   ├── discovery-report.md
│   ├── classification-report.md
│   ├── review-report.md
│   └── verification-report.md
└── git-log.txt                # 每个 phase 的 commit SHA 列表
```

## 置信度阈值（按决策类型拆分）

| 决策类型 | HIGH（自动） | MEDIUM（人工确认） | LOW（必须人工） | ESCALATE（升级） |
|---------|-------------|------------------|---------------|----------------|
| namespace | > 0.9 | 0.7-0.9 | 0.2 – 0.7 | < 0.2 |
| dependency | > 0.8 | 0.5-0.8 | < 0.5 | < 0.2 |
| paths | — | — | 全部人工审核 | — |
| conflict | > 0.85 | 0.6-0.85 | < 0.6 | — |

> [!warning] 表内三处结构问题（2026-09-13 复核）：本表 4 行 × 4 列共 16 个阈值，逐格核对发现——
> 1. **边界重叠**：namespace 的 MEDIUM `0.7–0.9` 与 LOW `0.2–0.7` 在 **0.7** 处重叠，边界值归属未定义（应改成闭开区间，如 `[0.7, 0.9)` / `[0.2, 0.7)`）；
> 2. **死格不可达**：dependency 的 ESCALATE `< 0.2` 被 LOW `< 0.5` 完全包含，该档永远不会被触发（应删档，或改为 `< 0.2` 优先判定）；
> 3. **与 Phase 3 规则不一致**：conflict 行 ESCALATE 为空，但 Phase 3 写「极低置信度（<0.2）→ 升级」（见迁移五阶段），两处规则冲突。
> 另：16 个阈值均未说明标定样本数与指标，建议补「标定样本数 / 指标」列（校准方法见下节）。

### 阈值校准与代价分级（2026-09-13 补）

上面这张表没有来源、没有校准方法、也没有代价分析，直接拍 0.9 无法解释。至少补三样：

1. **校准步骤**——先人工标注 20–30 个决策样本，画出「置信度 → 实际正确率」的对应曲线，再取阈值；阈值应当是曲线上某个可辩护的点，而不是整数偏好。
2. **按代价而非按类型设阈值**——阈值的依据应是「判错的代价能否低成本回退」：
   - `paths` 设错只导致不触发、且可随时改，本可自动执行（原表却要求**全部人工**）；
   - `includes` 设错会让父技能加载错误的子技能，影响面更大，应**从严**；
   - 官方提供的低成本回退手段是 `skillOverrides` 与 `disable-model-invocation`，可让高风险批次先以「只读 / 仅手动触发」形态上线再观察。
3. **防止阈值本身过拟合**——官方 skill-creator 的公开流程是 60/40 分层分割、改进时对 test 结果设盲、最终按 held-out 分数选方案（该细节见于 [[Anthropic-Skill系统深度分析]] 3.5 节自述，本库外未复核）；迁移的阈值与 prompt 也应照此办理，否则 0.9 只是拟合了手头那几个样本。

> 来源：https://code.claude.com/docs/en/skills ；https://agentskills.io/skill-creation/optimizing-descriptions

## 规模分档

| 技能数量 | 命名空间策略 | 依赖关系策略 |
|---------|-------------|-------------|
| < 50 | 直接 LLM 分类（一次 prompt） | 文本 grep + LLM 验证（O(n)） |
| 50-200 | 规则预筛 + 按 namespace 分组 LLM | 按 namespace 分组推断（O(n×k)，k=每个 namespace 的 skill 数） |
| 200-1000 | embedding 聚类 + LLM 精排 | 向量粗筛 → LLM 精排 |

Phase 1 的跨文件引用检测始终使用反向索引而非 O(n²) grep。

> [!warning] 复杂度记号与算法对不上（2026-09-13 复核）：Phase 2 明确写依赖推断要做「文本引用（grep 交叉引用）+ 语义推断（LLM 判断 A 的工作流是否隐含需要 B）」，**成对语义推断本身就是 O(n²) 量级的候选**；反向索引只能把候选生成降到 O(总引用数)，随后每个候选仍要一次 LLM 调用。表中 `O(n)` / `O(n×k)` 既未定义 n、k（skill 数还是候选对数），也没有给出真正决定可行性的三个可测量。建议该列改为「**候选对数 / LLM 调用次数 / 预估 token**」，并在 200–1000 档补 embedding 聚类的成本估算。

## 回滚机制

- 每次迁移一个 namespace 一个 commit（粒度 ~5-10 skills/commit）
- git revert 只影响单个 namespace，其他已迁移的 namespace 不受影响
- 审计文件同步记录回滚 trace

### 失败模式与止损（2026-09-13 补）

上文只有成功路径。三条失败模式目前没有对应设计，每条给出可观测信号与止损动作：

| 失败模式 | 为什么现有设计挡不住 | 可观测信号 | 止损动作 |
|---|---|---|---|
| **错误传播半径 = 回滚单位** | 单 namespace 内一个 skill 误分类，会让同批 5–10 个 skill 一起进错目录；而 commit 粒度正是「单 namespace」，回滚只能整块回滚 | `review-report.md` 中同一 namespace 的红色项 ≥ 2 | 先 dry-run 生成 diff、逐个 approve 再落盘；把 commit 粒度压到「单 skill 的变更集」 |
| **幂等性自身没有验证方法** | 「可安全重跑」是声明，不是被测过的性质——重跑后是否重复追加 trace、是否产生空 commit、`snapshots/` 是否被半成品覆盖，均无检查项 | 重跑后 `audit.jsonl` 出现重复 `trace_id`；git 出现空 commit；快照被半成品覆盖 | 用输入哈希做幂等键；补一条「重跑两次产物字节一致」的自动化断言 |
| **审计体积无估算、无轮转** | 单条决策一条 trace + 四个 phase 快照，200–1000 skill 档位的 `audit.jsonl` 会持续膨胀 | `audit.jsonl` 行数或单会话目录体积超阈值 | 约定轮转策略（按会话切分 + 归档），并把 trace 的 `reasoning` 字段改为可外部引用的 digest |

## 复用现有组件

- **SkillRegistry 数据类**：import `skill-registry.py` 的 `Skill` dataclass 和 `SkillRegistry` 类
- **Phase 5 验证**：直接调用 `reg.resolve_dependencies()` 和 `reg.filter_by_context()`
- **顶层技能识别**：复用 `skill-dependency-viz.py` 中的 top-level 判定逻辑
- **Frontmatter 解析**：复用 `scripts/claude-ops-deployments/demos/migration/phase1_discover.py` 的 `parse_frontmatter()` 函数（定义于该文件第 30 行）

> [!warning] 更正（2026-09-13）：本节原写的 `analyze_skills.py` 是**悬空引用，库内不存在**（原表述为「复用 `analyze_skills.py` 的 `parse_frontmatter()` 函数」）。全库检索确认：`scripts/claude-ops-deployments/demos/` 下实际只有 `demo-e2e-test.py`、`demo-skills.json`、`fetch-wechat-article.sh`、`restructure-claude-md-demo.sh`、`skill-dependency-viz.py`、`skill-registry.py`，递归匹配 `*analyze_skill*` 与 `analyze*` 均为空。同名的 `parse_frontmatter()` 实际定义在 `scripts/claude-ops-deployments/demos/migration/phase1_discover.py:30`（另有一份独立实现在 `scripts/validate-kb.py:111`）——应说明复用哪一份，或抽成公共模块，否则后来者按图索骥必然落空。
> [[Anthropic-Skill系统深度分析]] 5.4 节同样称「`analyze_skills.py` 计算每对 skill 的歧义风险」，该**歧义评分算法（触发词重叠 40% / 领域重叠 30% / 结构相似 30%）缺少可核查的实现出处**，应标注为「设计稿，尚无实现」或补上脚本路径。
> 核对无误项：`skill-registry.py` 确含 `class Skill`（第 13 行）、`class SkillRegistry`（第 23 行）、`resolve_dependencies()`（第 32 行）、`filter_by_context()`（第 60 行）；`skill-dependency-viz.py` 存在——本节其余三处组件引用有效。
> 来源：本库文件实测（`scripts/claude-ops-deployments/demos/migration/phase1_discover.py`、`scripts/validate-kb.py`）

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 背景把系统写成「扁平发现式」，并把目标定为「命名空间 + 依赖声明 + 条件匹配 + 检索式发现」四件套 | 逐条标注 `paths` 条件匹配、插件命名空间、子目录技能延迟加载、`skillOverrides` 四项已原生存在，目标收窄为「只补 includes + 检索式发现」；并提示 30000 token 属自造系数（来源 code.claude.com/docs/en/skills、/docs/en/plugins） |
| 纠错 | 「复用现有组件」引用库内不存在的 `analyze_skills.py` | 改为真实路径 `demos/migration/phase1_discover.py:30`（另一份实现在 `scripts/validate-kb.py:111`），并标注歧义评分算法暂无实现出处 |
| 补疏漏 | Phase 4 未区分官方规范字段与自建私有键 | 新增「字段合法性分层」一节：规范六键 / `paths` / 私有扩展三档对照表 + 「本机生效 / 仅自建工具生效 / 分发后丢失」标注要求 |
| 补疏漏 | Phase 5 四项验证全是结构验证 | 新增「验证补强」一节：触发准确率回归、效果基线对比（须新会话）、`claude plugin eval` 门禁与两种 eval 格式不互通、`paths` 静默失败须落成自动化断言 |
| 加厚 | 置信度阈值表无来源、无校准方法、无代价分析 | 新增「阈值校准与代价分级」：20–30 样本校准曲线、按回退代价而非按决策类型设阈值、防止阈值过拟合 |
| 加厚 | Phase 5→2 反馈循环与循环依赖预检合计不足 8 行 | 补 `audit.jsonl` 的 `verification.cycle` 机读 schema、edge 级独立 commit、增量重跑收敛判据（重跑上限 + 升级人工）；并说明本文不含深度数字、「深度 ≤ 4」属新增建议而非订正 |
| 纠错 | 置信度阈值表 16 个阈值存在边界重叠、死格与规则冲突 | 逐格核对后标注三处：namespace 在 0.7 处重叠、dependency 的 ESCALATE `<0.2` 不可达、conflict 的 ESCALATE 与 Phase 3 的 `<0.2 → 升级` 不一致；建议改闭开区间并补标定样本数列 |
| 补疏漏 | Phase 5 四项检查没有「多少算通过」的判据 | 新增可判定门槛表（断裂 edge = 0 / 拓扑排序成功 / 每条 glob 至少命中 1 类 / Token 预算 ≤ 旧系统 X%，X 须实测）；依据本设计自身的验证目标 |
| 补疏漏 | 「幂等可重入」与回滚机制只有成功路径 | 新增「失败模式与止损」一节：错误传播半径 = 回滚单位、幂等性无验证方法、审计体积无轮转，各配可观测信号与止损动作 |
| 纠错 | 规模分档表的 `O(n)` / `O(n×k)` 与 Phase 2 的成对语义推断对不上 | 标注复杂度记号未定义 n/k，建议该列改为「候选对数 / LLM 调用次数 / 预估 token」；依据 Phase 2 的算法描述与反向索引的实际作用 |

来源登记：[[sources/learning-notes]]（B7 复核新增一节）
回链：[[CORRECTIONS]] | [[AGENTS]]
