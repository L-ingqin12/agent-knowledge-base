---
description: Feature实现流程 — 实现→测试→审查 (串行)
agent: orchestrator
---

执行 Feature 实现工作流。按以下顺序串行委托子智能体：

Step 1: 分析需求并规划实现方案
- 委托 refactor-specialist 子智能体实现代码

Step 2: 委托 test-writer 子智能体
- 为新功能编写单元测试和集成测试
- 覆盖 Happy Path + 边界条件 + 错误路径

Step 3: 委托 code-reviewer 子智能体
- 审查新实现代码的正确性/安全性/性能
- 检查是否遵循项目风格

约束: 每步最多重试3次, 测试必须先通过再进入审查
