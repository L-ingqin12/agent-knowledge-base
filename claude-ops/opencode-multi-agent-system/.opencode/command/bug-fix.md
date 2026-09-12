---
description: Bug修复流程 — debug→验证→重构→回归测试 (串行)
agent: orchestrator
---

执行 Bug 修复工作流。按以下顺序串行委托子智能体：

Step 1: 委托 debugger 子智能体
- 定位 bug 根因
- 范围: $ARGUMENTS 中指定的文件或模块
- 输出: 根因分析报告 + 修复 diff

Step 2: 主控验证修复方案
- 检查修复是否解决根因
- 检查是否引入新问题

Step 3: 委托 refactor-specialist 子智能体
- 基于修复后的代码消除代码味道
- 不改变外部行为

Step 4: 委托 test-writer 子智能体
- 为修复编写回归测试
- 测试复现原始 bug 验证修复有效

约束: 每步最多重试3次, 同一问题连续2次失败则暂停
