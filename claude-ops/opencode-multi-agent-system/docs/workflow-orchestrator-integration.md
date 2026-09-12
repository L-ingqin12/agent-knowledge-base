---
title: Workflow 与 Orchestrator 协作机制
aliases: [Workflow 与主 Agent 协作, Orchestrator 剧本库, 关键词触发工作流]
tags: [ai/agent, ai/ops]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# Workflow 与 Orchestrator 协作机制

## 谁是主 Agent

**只有一个主 Agent: `orchestrator`** (mode: primary)

```
用户交互层
    │
    ▼
┌─────────────────────────────────────────────┐
│  🧠 Orchestrator (唯一入口, mode: primary)    │
│                                              │
│  ANALYZE → 匹配 Workflow → DELEGATE → DONE  │
│                                              │
│  内置剧本库:                                  │
│  ├─ full-review:     审查+安全+文档 (并行)    │
│  ├─ feature-impl:    实现→测试→审查 (串行)    │
│  └─ bug-fix:         debug→修复→回归 (串行)   │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
code-reviewer  test-writer   security-auditor  ...
(subagent)     (subagent)    (subagent)
```

**其他 primary agent (build, plan, summary, title) 是 OpenCode 内置的，不是我们的。**

## Workflow 如何被触发

### 方式 1: 关键词自动匹配（Orchestrator 内置）

用户说"上线前检查" → Orchestrator 的 ANALYZE 阶段匹配到 `full-review` workflow。

### 方式 2: 用户显式指定

用户说"用 bug-fix workflow 处理" → Orchestrator 直接加载对应剧本。

### 方式 3: Slash Command（OpenCode 命令）

用户输入 `/review` → OpenCode 执行对应的 slash command → 触发 Orchestrator + 对应 workflow。

## 协作流程详解

```
                         Orchestrator (主 Agent)
                                │
    ┌───────────────────────────┼───────────────────────────┐
    │                           │                           │
    ▼                           ▼                           ▼
[ANALYZE]                  [DELEGATE]                  [VERIFY]
    │                           │                           │
    │ 读取用户请求               │ 按 workflow 步骤          │ 质量门控
    │ 匹配关键词                 │ 逐个调用 subagent         │ 不通过→RETRY
    │ 选择 workflow              │                           │
    │                           │                           │
    │  ┌──────────────────┐     │                           │
    │  │ Workflow 剧本库   │     │                           │
    │  │                  │     │                           │
    │  │ full-review:     │     │                           │
    │  │  parallel:       │     │                           │
    │  │   - reviewer     │────▶│ 并行调用三个 subagent      │
    │  │   - auditor      │     │                           │
    │  │   - doc-writer   │     │                           │
    │  │                  │     │                           │
    │  │ bug-fix:         │     │                           │
    │  │  serial:         │     │                           │
    │  │   - debugger     │────▶│ 串行: debug→verify→refactor│
    │  │   - refactor     │     │                           │
    │  └──────────────────┘     │                           │
    └───────────────────────────┴───────────────────────────┘
```

## 实现：将 Workflow 嵌入 Orchestrator

Workflow YAML 文件是给人看的参考。真正执行靠 Orchestrator system prompt 中的剧本指令。

Orchestrator 的 ANALYZE 阶段原文：
```
匹配到 "上线" / "发布" / "release" / "full check" → full-review workflow
匹配到 "新功能" / "feature" / "实现" → feature-implementation workflow
匹配到 "修" / "bug" / "fix" / "报错" → bug-fix workflow
```

## 可运行的演示

以下脚本模拟 Orchestrator 加载并执行一个 workflow：

```javascript
// 模拟 Orchestrator 执行 full-review workflow
const workflow = {
  name: 'full-review',
  mode: 'parallel',
  steps: [
    { agent: 'code-reviewer', prompt: '审查 src/ 全部代码' },
    { agent: 'security-auditor', prompt: '安全审计 src/' },
    { agent: 'doc-writer', prompt: '更新 README' }
  ]
};

async function executeWorkflow(workflow, context) {
  console.log(`[Orchestrator] 匹配到 workflow: ${workflow.name}`);

  if (workflow.mode === 'parallel') {
    // Fan-Out: 并行委托所有子任务
    console.log(`[Orchestrator] Fan-Out → ${workflow.steps.length} 个子任务并行`);
    const results = await Promise.all(
      workflow.steps.map(step => delegateSubagent(step.agent, step.prompt))
    );
    return integrateResults(results, workflow.steps);

  } else if (workflow.mode === 'serial') {
    // 串行: 逐个委托
    const results = [];
    for (const step of workflow.steps) {
      const output = await delegateSubagent(step.agent, step.prompt);
      const verify = runQualityGates(step.agent, output);
      if (!verify.pass) {
        // 进入 RETRY 回环...
      }
      results.push(output);
    }
    return integrateResults(results, workflow.steps);
  }
}
```

## 完整调用链

```
1. 用户输入:  "上线前做全面检查"
       │
2. Orchestrator.ANALYZE:
       │  关键词 "上线" + "检查" → full-review workflow
       │  依赖分析: 三个子任务独立 → 并行模式
       │
3. Orchestrator.DELEGATE (Fan-Out):
       │  ┌─ code-reviewer, "审查 src/ 全部代码"      ─┐
       │  ├─ security-auditor, "安全审计 src/"         ─┤ 并行
       │  └─ doc-writer, "更新 README"                ─┘
       │
4. Orchestrator.VERIFY (每个子任务独立):
       │  code-reviewer:     PASS ✓
       │  security-auditor:  PASS ✓
       │  doc-writer:        FAIL (输出过短) → RETRY → PASS ✓
       │
5. Orchestrator.INTEGRATE:
       │  交叉验证 → 发现 CSRF 被两个子智能体同时报告 → 升级为严重
       │
6. Orchestrator.DONE:
       │  "上线检查完成: 2 个阻塞问题, 3 个改进建议"
```

## 关键点

| 问题 | 答案 |
|------|------|
| 谁是主 Agent？ | **orchestrator** (唯一的 mode:primary，用户入口) |
| Workflow 是 Agent 吗？ | **不是**。它是 Orchestrator 执行任务的**剧本** |
| Workflow 怎么触发？ | ANALYZE 阶段关键词匹配 / 用户显式指定 / slash command |
| 谁执行 Workflow？ | Orchestrator 读取剧本，按步骤委托 subagent |
| Workflow 文件的作用？ | 给人看的参考 + 给 Orchestrator 的指令模板 |

> 🔗 相关文档：[[fan-out-pattern]] · [[state-machine-control]] · [[opencode-multi-agent-architecture]]
