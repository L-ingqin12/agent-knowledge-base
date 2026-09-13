---
title: "Skill 规模化管理——从渐进式披露到检索式发现"
aliases: [Skill规模化管理, 检索式发现, Skill Discovery]
tags: [ai/skills, ai/learning]
created: 2026-06-22
updated: 2026-09-13
status: review
source: "基于 Claude Code Skills 体系推演"
date: "2026-06-22"
fetched_at: "2026-06-22"
---

# Skill 规模化管理——从渐进式披露到检索式发现

See also: [[AI-Links-KB-Home]] | [[Articles-Index]] | [[Agent驱动Skill迁移设计]] | [[日志检索分析系统-Skill管理Demo设计]] | [[Claude-Code记忆机制源码拆解]] | [[上下文工程落地实践-从理论到Claude-Code实现]]

## 摘要

当 Skill 从 10 个增长到 1000 个，渐进式披露的 Level 1（元信息始终在 system prompt）本身就成为瓶颈——1000 个 skill × 30 token/行 = 30000 token，还没加载任何内容就把 system prompt 吃掉了。

> [!warning] 更正（2026-09-13）：`30 token/行` 是本文自造的换算系数，官方文档中没有这个口径，「1000 skill = 30000 token」由它推出，**不应作为量化基石**（原表述为「1000 个 skill × 30 token/行 = 30000 token，还没加载任何内容就把 system prompt 吃掉了」）。可核对的上界只有两条：Agent Skills 规范规定 `description` ≤ 1024 字符、`name` ≤ 64 字符；Claude Code 把 `description` 与 `when_to_use` 合并后在技能列表中**截断于 1,536 字符**（官方原文：the combined description and when_to_use text is truncated at 1,536 characters in the skill listing to reduce context usage）。1,536 字符是**截断上限而非典型占用**，真实开销取决于各技能 description 的实际长度，必须以 `/skill-doctor` 实测为准，不得引用任何未经实测的换算值。本文第一、二、五、六节沿用的全部数字（300/1500/3000/9000/15000/30000、150、12000 等）都是同一自造系数的推导结果，请按「方向性示意」而非实测值阅读。低成本治理手段见第九节，检索式发现自身的代价见第十节。
> 来源：https://code.claude.com/docs/en/skills ；https://agentskills.io/specification

解法：把上下文工程的四层解法**递归应用到 Skill 管理自身**。Skill 元信息不再是常驻列表，而是一个可检索、可发现、按时效性分层的动态目录。核心转变：**从「渐进式披露」（先列目录再展开）到「检索式发现」（先搜再列）。**

---

## 一、问题的缩放曲线

```
Skill 数量        渐进式披露开销          瓶颈在哪
──────────────────────────────────────────────────
10-50            300-1500 token        ✅ 完全可接受
100-300          3000-9000 token       ⚠️ 开始挤压其他元信息
500-1000         15000-30000 token     ❌ system prompt 被淹没
5000+            不可行                  ❌❌ 模型根本看不全
```

当前阶段（10-50 个 skill）渐进式披露完全够用。但问题出在**信息密度**：30 token 的一行 Skill 元信息，它的「信息密度」远低于一条 30 token 的记忆 description。因为记忆是对话中长出来的、高度个性化的，而 Skill 是通用的——「这个 skill 是干什么的」对当前任务而言，大部分时候是噪声。

Skill 数量和当前任务的**相关性比例**，决定了瓶颈到来的速度：

| 场景 | Skill 总数 | 与当前任务相关的 | 相关性比例 | 浪费的元信息 token |
|------|-----------|----------------|-----------|------------------|
| 单人全栈 | 20 | 8-12 | 40-60% | 可接受 |
| 团队多项目 | 200 | 10-20 | 5-10% | 90% 是噪声 |
| 公司级市场 | 2000 | 5-10 | < 1% | 99% 是噪声 |

规模越大，**相关性比例越低，渐进式披露的浪费越严重**。

> 本节表格中的 token 数字与摘要同源（自造系数），只表达趋势；在讨论「要不要上检索式发现」之前，请先看第九节的量测手段与显隐旋钮。

---

## 二、解法：检索式发现——把四层递归应用到自己身上

核心思路：不是因为 Skill 多了就「不要渐进式披露了」，而是**在渐进式披露的前面再加一层——Skill 发现层**。

```
渐进式披露（当前）
  system prompt: [skill_a, skill_b, skill_c, ... skill_z] ← 全部列出
  model 自己判断用哪个

检索式发现（规模化后）
  system prompt: search_skills(query) ← 一个工具，一句说明（30 token）
  model 调用 search_skills("current task description") → 返回 top-5 匹配
  system prompt 只注入这 5 个的元信息
```

### 2.1 四层递归对照

| 上下文工程四层 | 应用于 Context | 递归应用于 Skill 管理 |
|--------------|---------------|---------------------|
| **检索** | 从文档库检索相关片段 | 从 Skill 注册中心检索相关 Skill |
| **压缩** | 压缩长对话历史 | 压缩 Skill 元信息（description → 一行摘要 → 嵌入向量） |
| **子 Agent 隔离** | 独立 context 执行子任务 | Skill 独立 context 执行，不污染主 prompt |
| **渐进式披露** | 指令按需加载 | Skill 按三层加载：搜索结果 → 元信息 → 完整 SKILL.md |

### 2.2 三层架构

```
Layer 0 — Skill 发现（检索式，替代常驻列表）
  ├── model 调用 search_skills(task_description) 
  ├── 返回 top-5 候选 skill 的 name + description
  └── 开销：5 × 30 = 150 token（vs 1000 × 30 = 30000 token）

Layer 1 — Skill 元信息（渐进式披露 Level 1）
  ├── 只加载 Layer 0 返回的 top-5 的元信息
  └── 与当前渐进式披露完全兼容

Layer 2 — Skill 完整内容（渐进式披露 Level 2 & 3）
  ├── model 判断要用了 → 加载完整 SKILL.md
  └── 需要具体文件 → 按需读取
```

> 检索式发现不是纯收益解法：它的漏召回风险、描述截断损失与触发率验收方式见第十节。

---

## 三、Layer 0 的实现方案

### 3.1 方案 A：小模型选择器（候选 < 500）

和记忆系统的 Sonnet 选择器完全一致：

```python
def search_skills(query: str, all_skills: list, top_k: int = 5) -> list:
    """用小模型从所有 skill 中选 top-k"""
    candidates = [
        {"name": s.name, "description": s.description, "namespace": s.namespace}
        for s in all_skills
    ]
    prompt = f"""
    Task: {query}
    Available skills (only name + description):
    {json.dumps(candidates, ensure_ascii=False)}

    Select the {top_k} most relevant skills. Be selective — 
    if uncertain, do NOT include. Return only the skill names.
    """
    result = small_llm(prompt, schema=TopKSchema)
    return [s for s in all_skills if s.name in result.names]
```

优点：简单、和记忆系统统一、可解释。  
局限：候选超过 500 时，candidates 字符串本身可能超过小模型 context。

### 3.2 方案 B：两阶段检索（候选 > 500）

当 skill 数量超过小模型一次性处理的阈值时，加一层粗筛：

```python
def search_skills_large(query: str, index, top_k: int = 5) -> list:
    # Stage 1: 向量粗筛（embedding → top-50）
    query_vec = embed(query)
    coarse = index.search(query_vec, k=50)
    
    # Stage 2: LLM 精排（50 个候选 → top-5）
    return small_llm_selector(query, coarse, top_k=5)
```

这里用了向量检索，但和记忆系统的区别在于：**向量只做粗筛，不做最终决策**。最终选择仍是 LLM——避免「0.87 相似度但实际不相关」的向量检索老问题。

### 3.3 方案 C：命名空间 + 触发条件前置过滤

在任何检索发生之前，先用规则砍掉不相关的 skill：

```yaml
# 每个 skill 的 frontmatter 声明
---
name: react-hooks-guide
namespace: frontend/react
paths: ["**/*.tsx", "**/*.jsx"]
tasks: ["ui-development", "code-review"]
requires: ["node", "npm"]
conflicts: ["vue-best-practices"]
---

# Skill 内容...
```

```python
def pre_filter(skills, context):
    """规则前置过滤——不花 token，纯逻辑匹配"""
    filtered = []
    for s in skills:
        if s.namespace and context.project_type not in s.namespace:
            continue  # 前端项目不加载 backend skill
        if s.paths and not glob_match(s.paths, context.current_files):
            continue  # 编辑 .go 不加载 React skill
        if s.conflicts and any(c in context.active_skills for c in s.conflicts):
            continue  # vue 和 react skill 互斥，只加载一个
        filtered.append(s)
    return filtered
```

这个过滤是**零 token 开销**的——在候选技能进入 LLM 视野之前，先砍掉确定不相关的。

> [!warning] 更正（2026-09-13）：方案 C 里的 `paths` 前置过滤与「命名空间」**已由 Claude Code 原生提供**，不应再当作待自建扩展（原表述为把 namespace / paths / conflicts 整体列为方案 C 的自研内容，第八节 Phase 2 亦称「给 skill 补 namespace/paths/includes frontmatter」）。`paths` 已是 SKILL.md frontmatter 的一等字段（官方原文：Glob patterns that limit when this skill is activated. Accepts a comma-separated string or a YAML list. When set, Claude loads the skill automatically only when working with files matching the patterns. Uses the same format as path-specific rules），`.claude/rules/` 同样支持 `paths` 路径限定（Rules without a paths field are loaded unconditionally；Path-scoped rules trigger when Claude reads files matching the pattern, not on every tool use）；插件技能天然带命名空间，调用形式为 `/plugin-name:skill-name`。真正需要自建的只剩 namespace 语义分组、includes/optional_includes 依赖声明与检索式发现三块。
> 来源：https://code.claude.com/docs/en/skills ；https://code.claude.com/docs/en/plugins

---

## 四、时效性分层——Skill 的「stale 管理」

记忆系统有 2 天 stale 警告。Skill 同样有时效性问题：某个 Skill 对应的工具升级了、API 变了、团队规范改了，旧的 SKILL.md 就成了「权威的错误」。

### 4.1 三层时效

| 层级 | 内容 | 时效性 | 检查方式 |
|------|------|--------|---------|
| 官方 Skills | Anthropic 维护的 doc-coauthoring、mcp-builder 等 | 跟随上游仓库更新 | `git pull` 检查 |
| 团队 Skills | 团队沉淀的规范和流程 | 随项目演进更新 | 与 CLAUDE.md 同步 review |
| 个人 Skills | 个人偏好和快捷指令 | 自己维护 | 使用频率统计 + 废弃提示 |

### 4.2 时效性元信息

```yaml
---
name: api-gateway-deploy
namespace: team/backend
last_verified: "2026-06-15"
stale_after_days: 30
source_repo: "https://github.com/team/backend-skills"
---

skill 内容...
```

类似记忆系统的 `<system-reminder>This memory was saved N days ago</system-reminder>`，超过 `stale_after_days` 的 Skill 在加载时自动附带提示。

> [!warning] 更正（2026-09-13）：上面这套字段**在当前机制下不会生效**。
> 1. **位置错了**——Agent Skills 规范只允许六个键：`name`（≤64 字符，不得以连字符开头或结尾）、`description`（≤1024 字符）、`license`、`compatibility`（≤500 字符）、`metadata`（string→string map）、`allowed-tools`（Experimental）。`last_verified` / `stale_after_days` / `source_repo` 属规范外键，只能落进 `metadata` map。
> 2. **承诺不成立**——官方对 `metadata` 的态度是「Free-form YAML map for your own key-value data, such as entitlement or catalog fields, read by your own tooling from SKILL.md. Claude Code doesn't act on its contents, and drops a value that isn't a map. Don't reuse frontmatter field names such as paths as keys」，即写了也不会自动提示，必须由自己的 hook/脚本读取 `metadata` 后注入（原表述为「超过 `stale_after_days` 的 Skill 在加载时自动附带提示」）。
> 3. **验收应落成三步清单**：①日期判定 stale → ②重跑触发评测（should-trigger 集复测）→ ③改名或下线。注意 **stale ≠ 废弃**：工具升级导致的失效要靠触发集复测暴露，不是靠日期。官方已有的近似能力是 `/skill-doctor`，它会列出从未被调用的技能并指出可关闭的位置，可直接作为「废弃检测」的第一版实现，不必自建使用频率统计。
> 来源：https://agentskills.io/specification ；https://code.claude.com/docs/en/skills

---

## 五、依赖式引入：`@include` 级联加载——编程式的按需关联

检索式发现解决的是「模型不知道有哪些 Skill 时如何发现」。但还有另一条路径：**Skill 之间本就有明确的组合/依赖关系，不需要「搜索」，只需要「声明」。**

这和 C 语言的 `#include`、Python 的 `import` 完全同构——父 Skill 声明依赖，依赖只在父 Skill 被激活时才级联加载。

### 5.1 现有基础：CLAUDE.md 的 `@include`

CLAUDE.md 中已经实现了这个机制：

```
@~/company/security-rules.md
```

加载时自动读取目标文件内容拼入，同时有防循环引用和防路径遍历的工程保护。Skills 可以直接复用同一套语法和实现。

> [!warning] 更正（2026-09-13）：本节的**方向反了**，而且反转依据就在同一份官方文档里。
> 1. `@path` 导入是**启动时急切展开**，不是按需级联——官方原话「Imported files are expanded and loaded into context at launch alongside the CLAUDE.md that references them」与「Splitting into @path imports helps organization but doesn't reduce context, since imported files load at launch」。越 import 越占 context，**不可能**产生 5.2–5.4 节承诺的「子 Skill 隐形、开销 0 token」。真正的按需加载要靠 Skill 目录本身（SKILL.md 正文触发时才加载，加载后 stays in context across turns）与 `references/` 的按需读取。（原表述为「加载时自动读取目标文件内容拼入……Skills 可以直接复用同一套语法和实现」，并据此推出子 Skill 的 token 节省结论）
> 2. 导入深度上限是**四跳**：官方原文「Imported files can recursively import other files, with a maximum depth of four hops」。
> 3. 跨工作目录的导入会触发**一次性批准弹窗**：官方原文「The first time Claude Code encounters external imports in a project, it shows an approval dialog listing the files. If you decline, the imports stay disabled and the dialog doesn't appear again」——须限定为「项目级记忆文件引入工作目录之外的文件时」，不是无条件可用，也不是所有导入都需要批准。
> 4. 原文所称的「防循环引用和防路径遍历」两项工程保护在该官方文档中**未见对应表述**，按本库规则不应作为官方机制引用。
> 来源：https://code.claude.com/docs/en/memory

### 5.2 Skill 依赖声明

```yaml
# skills/data-pipeline-deploy/SKILL.md
---
name: data-pipeline-deploy
description: 数据管道部署流程
includes:
  - @skills/shared/docker-build       # 必选依赖
  - @skills/shared/k8s-apply          # 必选依赖
  - @skills/team/secret-management    # 必选依赖
optional_includes:
  - @skills/team/slack-notify         # 可选：有就加载，没有也不报错
---
```

**效果**：

```
System prompt（始终加载，30 token）：
  "data-pipeline-deploy — 数据管道部署流程"

模型选中 data-pipeline-deploy 后（级联自动展开）：
  Level 1: data-pipeline-deploy 元信息
  Level 2: 检测 includes → 自动加载 docker-build + k8s-apply + secret-management
  Level 3: 需要具体文件时按需读取
```

模型只需要知道父 Skill 的存在（30 token），三个子 Skill 的元信息根本不在 system prompt 里——只在被需要时才出现。

> 更正（2026-09-13）：本段结论不成立——`@import` 是启动时急切展开，「子 Skill 隐形」不成立；原因与官方原文见 5.1 节末的更正块。

### 5.3 与检索式发现的对比

| 维度 | 检索式发现 | 依赖式引入 |
|------|-----------|-----------|
| 触发方式 | 模型调用 search_skills(query) | Skill 声明 includes 字段 |
| 关系类型 | 语义相似（动态） | 组合/依赖（静态，声明时确定） |
| 适合场景 | 「这个任务大概需要哪些 Skill」 | 「Skill A 的执行一定需要 Skill B/C」 |
| 模型开销 | 一次 LLM 调用做选择题 | 零——纯规则级联 |
| 典型例子 | 模型自己判断部署任务需要 docker-build | data-pipeline-deploy 声明依赖 docker-build |

两者互补，不是互斥：

```
1000 个 Skill
  │
  ├── 有明确依赖关系的（~60%）
  │     → 依赖式引入，父 Skill 激活时级联加载
  │     → system prompt 只列父 Skill，子 Skill 隐形
  │
  └── 独立/无预设关系的（~40%）
        → 检索式发现，按需搜索
        → search_skills(query) 返回 top-5
```

### 5.4 依赖树的 token 节省计算

假设 1000 个 Skill 中有 600 个是子 Skill（被其他 Skill 依赖），只有 400 个是顶层入口：

```
全部列出：1000 × 30 = 30000 token
只列顶层：400 × 30 = 12000 token
  → 省 18000 token（60%）
```

而 12000 token 仍然偏多——再加上检索式发现（search_skills），只返回 top-5，就只有 150 token。

**两条路径叠加后的效果**：

```
System prompt 中 Skill 相关开销：
  search_skills 工具声明：30 token
  + depends_on/include 依赖解析引擎：0 token（纯规则引擎）
  = 30 token（vs 原始方案的 30000 token）
```

### 5.5 自建 Agent 实现

```python
class SkillLoader:
    def __init__(self, registry):
        self.registry = registry  # 所有 skill 的索引
        self.loaded = set()       # 已加载的 skill（防循环）

    def load(self, skill_name: str, depth: int = 0) -> list:
        """加载一个 skill 及其依赖链"""
        if depth > 5:
            raise CircularDependencyError(f"Max depth exceeded at {skill_name}")
        if skill_name in self.loaded:
            return []  # 已加载，跳过（防循环）

        skill = self.registry.get(skill_name)
        if not skill:
            return []

        self.loaded.add(skill_name)
        loaded = [skill.content]

        # 级联加载依赖
        for dep in skill.includes or []:
            loaded.extend(self.load(dep, depth + 1))

        # 可选依赖：有就加载，没有跳过
        for opt_dep in skill.optional_includes or []:
            try:
                loaded.extend(self.load(opt_dep, depth + 1))
            except SkillNotFound:
                pass

        return loaded
```

> [!note] 补疏漏（2026-09-13）：上面 `depth > 5` 是自建加载器的深度上限，官方 `@import` 体系的硬上限是**四跳**（memory 文档原文：Imported files can recursively import other files, with a maximum depth of four hops）。自建解析器若沿用 5 而不写明理由，会出现「本机可解析、上游展开失败」的落差，建议在对齐官方语义时改为四跳；库内 `scripts/claude-ops-deployments/demos/skill-registry.py` 的 `resolve_dependencies(..., max_depth=5)` 同理。
> 来源：https://code.claude.com/docs/en/memory

---

## 六、完整架构（双路径：依赖声明 + 检索发现）

```
┌─────────────────────────────────────────────────┐
│              Skill Registry（注册中心）              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ frontend│  │ backend │  │ shared  │  ← 命名空间 │
│  │  ·react │  │  ·go    │  │  ·docker│           │
│  │  ·vue   │  │  ·db    │  │  ·k8s   │           │
│  │  ·css   │  │  ·api   │  │  ·secret│           │
│  └─────────┘  └─────────┘  └─────────┘           │
│                                                   │
│  每条 skill 声明 includes / optional_includes     │
└──────────────────┬──────────────────────────────┘
                   │
          ┌────────▼────────┐
          │  两条路径并行     │
          └────────┬────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
    ▼                             ▼
┌───────────────┐          ┌───────────────┐
│ 路径 A: 依赖   │          │ 路径 B: 检索   │
│ @include 级联  │          │ search_skills │
│               │          │               │
│ 父 Skill 激活  │          │ Stage 0:      │
│ → 依赖链自动   │          │ 规则前置过滤   │
│   级联加载     │          │ (零 token)    │
│               │          │      ↓        │
│ 开销：0 token │          │ Stage 1:      │
│ (纯规则引擎)   │          │ 检索          │
│               │          │ (token 可控)  │
│ 适合：明确组合 │          │      ↓        │
│ 关系的 skill   │          │ 适合：独立/无  │
│               │          │ 预设关系      │
└───────┬───────┘          └───────┬───────┘
        │                          │
        └──────────┬───────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│     Stage 2: 渐进式披露（只有命中的进入 context）     │
│  · Level 1: name + description（每人一行）         │
│  · Level 2: 选中后才加载完整 SKILL.md             │
│  · Level 3: @include 的具体文件按需读取            │
│  · 防循环引用、防路径遍历                          │
└─────────────────────────────────────────────────┘
```

### 两条路径的 token 效果

| 阶段 | 全部列出 | 只列顶层 + 检索 | 顶层 + 检索 + 依赖链 |
|------|---------|---------------|-------------------|
| 100 Skill | 3000 | 150（top-5 结果） | 30（search_skills 工具声明） |
| 1000 Skill | 30000 | 150（top-5 结果） | 30 + 子 Skill 自动级联 |
| 瓶颈 | system prompt 被淹没 | LLM 选择器候选池 | 无——规模完全解耦 |

---

## 七、与现有 Claude Code 机制的对应

| 框架组件 | Claude Code 已有实现 |
|---------|-------------------|
| 命名空间隔离 | CLAUDE.md 四层级（Managed policy / User / Project / Local）；auto memory 是与之并列的另一套机制，不是层 |
| 依赖链级联加载 | `@import` 指令——但它是**启动时急切展开**，不是按需级联；深度上限四跳 |
| 条件匹配 | `.claude/rules/` 与 SKILL.md frontmatter 的 `paths` glob 匹配 |
| 小模型选择 | ⚠️ 待证：Sonnet 从 MEMORY.md 索引选 top-5 记忆 |
| Stale 管理 | ⚠️ 待证：`<system-reminder>` 2 天 stale 警告 |
| 去重过滤 | ⚠️ 待证：`alreadySurfaced` + `recentTools` 过滤 |
| 渐进式披露 | Skills 三级加载（元信息 → SKILL.md → 具体文件） |

**核对结果：skills 侧的机制有官方依据，记忆侧的三项待证。**

> [!warning] 更正（2026-09-13）：
> 1. **CLAUDE.md 层级是四层不是六层**——官方作用域表按加载顺序为 Managed policy（macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`、Linux 与 WSL `/etc/claude-code/CLAUDE.md`、Windows `C:\Program Files\ClaudeCode\CLAUDE.md`）→ User instructions（`~/.claude/CLAUDE.md`）→ Project instructions（`./CLAUDE.md` 或 `./.claude/CLAUDE.md`）→ Local instructions（`./CLAUDE.local.md`）。官方原文「Claude Code has two complementary memory systems」确认 **auto memory 不是 CLAUDE.md 的层级**，而是与 CLAUDE.md 并列的另一套机制；「Team」只是 Project instructions 的共享对象（Team members via source control），不是第五/第六层。（原表述为「CLAUDE.md 六层级（Managed/User/Project/Local/Auto/Team）」）
> 2. **`@include` 是启动时急切展开而非「级联加载」**——官方原话「Imported files are expanded and loaded into context at launch alongside the CLAUDE.md that references them」「Splitting into @path imports helps organization but doesn't reduce context, since imported files load at launch」；原文承诺的「防循环引用 + 防路径遍历」在该官方文档中未见对应表述。（原表述为「`@include` 指令（防循环引用 + 防路径遍历）」）
> 3. **结尾断言降级**：七项里只有四项能找到公开官方依据，其中两项口径本身还需订正（见上）；「Sonnet 从 MEMORY.md 索引选 top-5 记忆」「2 天 stale 警告」「alreadySurfaced + recentTools 过滤」三项在 `code.claude.com/docs/en/memory` 与 `code.claude.com/docs/en/skills` 两份官方文档中均无对应描述，目前只有本库自证的页面（如 [[Claude-Code记忆机制源码拆解]]）支撑，按本库规则应标 `unverifiable`——要么补上可公开核验的一手证据，要么改写为「本库源码观察所得，未经官方文档确认」。（原表述为「**七个机制，每一个都已在 Claude Code 中运行。**」）
> 来源：https://code.claude.com/docs/en/memory ；https://code.claude.com/docs/en/skills 当前 Skill 数量还小，这些机制主要用在记忆系统和 CLAUDE.md 上——当 Skill 数量增长时，同样的模式可以直接平移。

> [!success] 残余复核（2026-09-13）：表内三项「⚠️ 待证」**已用可公开核验的独立源码分析结案**，不再只依赖本库自证页——[lhl/agentic-memory — ANALYSIS-claude-code-memory.md](https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md)（本次经代理直取 HTTP 200，逐条比对）：
> - **小模型选择（Sonnet 选 top-5）→ 确认**：该文记「Sonnet selector picks up to 5 relevant memories per query | Mechanism | Source code (`findRelevantMemories.ts`, `max_tokens: 256`) | 0.95 | Limit is in the prompt, not hard-coded in parsing」；检索管线四步为 `scanMemoryFiles`（读全部 .md 前 30 行 frontmatter，上限 200 个文件）→ `formatMemoryManifest` → `sideQuery` 到 Sonnet → 输出 JSON `selected_memories`（max 5）。**注意上限写在选择 prompt 里，不是解析代码里的常量**（同 [[Claude-Code记忆机制源码拆解]] 的精确化）。
> - **Stale 管理（2 天警告）→ 阈值确认，包裹形态未确认**：该文记 `memoryAge(mtimeMs)` 返回 "today / yesterday / N days ago"，`memoryFreshnessText()` 对**超过 1 天**的记忆注入 "This memory is N days old. Memories are point-in-time observations… Verify against current code before asserting as fact."——与「今天/昨天不警告、第 2 天起警告」**一致**（age 为整天数，>1 天即 ≥2 天）。但该文只写「注入到 user context」，**未见 `<system-reminder>` 这一具体包裹形态**；该标签仍属原文表述，引用时宜写成「以提醒文本随记忆注入」。
> - **去重过滤（`alreadySurfaced` + `recentTools`）→ 机制确认，标识符部分确认**：该文管线第 4-6 步逐字为「Filter: exclude memories already surfaced in prior turns (`alreadySurfaced` set)」「Filter: exclude reference docs for currently-active tools (tool-aware filtering)」「Include warnings/gotchas about active tools (active use = when those matter)」——`alreadySurfaced` 标识符对上；`recentTools` 这个**变量名**只在原文出现，该文用「tool-aware filtering / recently-used tools」描述同一机制（选择器输入里含 "recently-used tools"）。
> **结论更新**：第七节表内三项由 `unverifiable` 升为「**有独立源码分析印证**」（唯 `<system-reminder>` 包裹形态与 `recentTools` 变量名两点仍属原文单一来源）。此处仍非官方文档口径——官方 memory 文档未公开这些机制，引用时请标明证据等级为「两路独立源码分析」。
> 来源：https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md

---

## 八、迁移路径：从 10 到 5000

```
Phase 1（当前：10-50 个 skill）
  → 渐进式披露完全够用，所有 skill 元信息一行一个
  → 任务：无

Phase 2（增长到 100-300 个 skill）
  → 加命名空间 + 条件过滤 + @include 依赖声明
  → 把共享 skill 抽成依赖，顶层 skill 声明 includes
  → system prompt 只列顶层入口，子 Skill 隐形
  → 任务：给 skill 补 includes 依赖声明（namespace 由目录/插件分组承担；paths 已是官方原生字段，直接用、不必自建——见 3.3 节更正）

Phase 3（增长到 500-1000 个 skill）
  → 加检索式发现（search_skills 工具）
  → system prompt 中不列 skill 列表，只给搜索工具 + 依赖解析引擎
  → 任务：实现 search_skills + 小模型选择器

Phase 4（增长到 5000+ 个 skill）
  → 两阶段检索（向量粗筛 + LLM 精排）
  → 加 stale 管理和废弃检测
  → 任务：建向量索引 + 时效性检查
```

核心原则不变：**任何时刻 context 里只放当前这一步真正用得上的部分。** 对文档成立、对记忆成立、对 Skill 成立——依赖声明和检索发现是这条原则在 Skill 管理上的两种互补实现。

---

## 九、先量测、再改架构（2026-09-13 补）

原文通篇默认「Skill 元信息常驻 system prompt」是唯一机制，没有提到 Claude Code 已经提供的技能成本度量与显隐治理手段。这三条正是「要不要上检索式发现」的判据，也是最有可能让整套架构升级变得不必要的低成本替代方案。

| 手段 | 作用 | 关键约束 |
|------|------|---------|
| `/skill-doctor` | 直接报告每个技能占用的 context 成本与调用频次；交互式会话开在 `/plugin` 管理器的 Stats 标签，`-p` 非交互模式打印为文本 | 需 v2.1.252+；在跳过 feature-flag fetching 的会话中不可用 |
| `skillOverrides` | 把单个技能改为 `name-only` 或 `off`，人工可读示例 `"legacy-context": "name-only"` | **插件技能不受 `skillOverrides` 影响**——官方原文「Plugin skills are not affected by skillOverrides. Manage those through /plugin instead.」 |
| `disable-model-invocation: true` | 阻止模型自动加载，只允许人工 `/name` 调用 | 反向旋钮 `user-invocable: false`；`skillOverrides` 的 `"user-invocable-only"` 是等价档位 |

官方把这件事说得很直白：「Every skill in the skill listing adds to your context on every turn, whether or not Claude ever uses it. Run /skill-doctor to see what each of your skills costs and how often it gets used, so you can decide which ones to turn off」。

> 来源：https://code.claude.com/docs/en/skills

---

## 十、取舍对照：检索式发现的失败模式与代价（2026-09-13 补）

原文第二节只对比 token 开销（30 token vs 30000 token）就把检索式发现当作纯收益解法。实际上两种机制的风险类型不同：**常驻列表永不漏召回、只多花 token；检索式发现错在不可见**——一旦漏召回，模型不会知道该技能存在。

| 代价 | 具体表现 | 对策 |
|------|---------|------|
| 召回有损 | 原文提出「返回 top-5 匹配」并以「Be selective — if uncertain, do NOT include」作为提示词；漏召回时模型无从察觉 | 按触发率而非主观感受验收，对漏召回设回归集 |
| 描述被截断 | `description` + `when_to_use` 合计截断于 1,536 字符；把路由信息压进检索查询会进一步放大截断损失 | 路由信息写进 `description` 前先确认长度预算 |
| 触发质量不可自证 | 官方原文「Seeing a skill trigger tells you Claude found it, not that it did what you intended.」 | 建 should-trigger / should-not-trigger 查询集，每条查询多次运行取触发率 |

触发集的建法（agentskills.io 官方口径）：最有价值的负样本是**近失（near-miss）**——原文「The most valuable negative test cases are near-misses」，同时提醒无关键词重叠的负样本太容易（too easy），测不出东西；每条查询至少跑 3 次取触发率，阈值 0.5。

结论：**检索式发现必须带上同等强度的触发率回归测试**，否则无法证明它比常驻列表更好——只比 token 开销是不完整的对照。

> 来源：https://agentskills.io/skill-creation/optimizing-descriptions ；https://code.claude.com/docs/en/skills

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 以自造系数「30 token/行」推出 30000/150/12000 全套数字，作为全文量化基石 | 摘要处加更正块：官方只有 `description` ≤ 1024 字符与 `description`+`when_to_use` 截断于 1,536 字符两条上界，实测交给 `/skill-doctor`；来源 code.claude.com/docs/en/skills、agentskills.io/specification |
| 纠错 | 第七节称 CLAUDE.md 为「六层级」（含 Auto/Team） | 改为官方四层级（Managed policy/User/Project/Local），auto memory 单列为并列机制；原表述保留在更正块内（来源 code.claude.com/docs/en/memory） |
| 纠错 | 称 `@include` 是「级联加载」且有防循环引用/防路径遍历保护，并据此推出子 Skill 隐形结论 | 更正为启动时急切展开（越 import 越占 context）、深度上限四跳、跨工作目录导入需一次性批准；5.2 节结论一并标注失效 |
| 纠错 | 第七节断言「七个机制，每一个都已在 Claude Code 中运行」 | 降级为「skills 侧有官方依据，记忆侧三项待证」，三项标 `unverifiable` 并指向本库自证页面 |
| 补疏漏 | 3.3 方案 C 把 namespace / paths 当作待自建扩展；Phase 2 要「补 namespace/paths frontmatter」 | 标注 `paths` 与插件命名空间已原生存在，真正待自建的只剩 namespace 语义分组、includes 与检索式发现（来源 code.claude.com/docs/en/skills、/docs/en/plugins） |
| 补疏漏 | 4.2 时效性字段位置错误，且「加载时自动附带提示」不成立 | 标注规范只允许六个键、私有字段须落 `metadata`，Claude Code 不解读 `metadata`，需自建 hook 注入；补「stale 判定 → 重跑触发评测 → 改名/下线」三步验收清单（来源 agentskills.io/specification） |
| 补疏漏 | 通篇未提技能成本度量与显隐治理手段 | 新增第九节：`/skill-doctor`、`skillOverrides`、`disable-model-invocation`；含版本与插件技能例外两条约束 |
| 加厚 | 第二节把检索式发现当作纯收益解法 | 新增第十节：召回有损、描述截断、触发质量不可自证，与近失负样本 + 多次运行取触发率的验收口径 |
| 加厚 | 5.5 节 `SkillLoader` 深度上限无出处 | 补注官方 `@import` 四跳上限，说明自建解析器（`depth > 5`、`max_depth=5`）与上游语义的落差 |
| 残余复核 | 第七节三项「⚠️ 待证」（Sonnet 选 top-5 / 2 天 stale 警告 / `alreadySurfaced`+`recentTools` 过滤） | **已结（升为有独立源码分析印证）**：lhl/agentic-memory 独立源码分析（本次直取 200）逐条对上——`findRelevantMemories.ts` + max 5；`memoryAge` today/yesterday/N days ago 与 `memoryFreshnessText()` 对 >1 天记忆注入验证提示（= 2 天起警告）；`alreadySurfaced` set 与 tool-aware filtering（含 active tools 的 warnings/gotchas）。残留两点属原文单一来源：`<system-reminder>` 包裹形态、`recentTools` 变量名 |

来源登记：[[sources/learning-notes]]（B7 复核新增一节）
回链：[[CORRECTIONS]] | [[AGENTS]]
