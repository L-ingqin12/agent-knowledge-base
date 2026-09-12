# 示例 1: 基础委托 — 单一子智能体调用

## 场景
用户想让 Orchestrator 审查 `src/auth.js` 的代码质量。

## OpenCode 会话

```
👤 用户: "审查 src/auth.js 的代码质量"

🧠 Orchestrator 思考:
  [意图分析] type=review, target=src/auth.js
  [决策] 单一原子任务 → 委托 code-reviewer
  [评估] 不需要写权限，审查结果由我验证后转达

🧠 Orchestrator 调用:
  Task(
    subagent_type: "code-reviewer",
    description: "审查 auth.js 代码",
    prompt: """
## 任务
审查 src/auth.js 的代码质量

## 范围
- 文件: src/auth.js
- 约束: 只分析不修改，输出结构化审查报告

## 预期输出
按 code-reviewer 标准格式输出：严重问题/改进建议/风格建议

## 关键上下文
- 项目语言: JavaScript
- 框架: Express.js + JWT 认证
- 该文件负责用户登录、Token 签发、会话管理
"""
  )

🔍 Code Reviewer 执行 → 返回:
  ## 审查总结
  - 严重问题: 2
  - 改进建议: 4
  - 风格建议: 3

  ## 🔴 严重问题
  ### [S-01] JWT secret 硬编码
  - 位置: src/auth.js:15
  - 修复: 改为 process.env.JWT_SECRET

  ### [S-02] 密码比较使用 == 而非 ===
  - 位置: src/auth.js:42
  - 修复: 改用 === 严格比较 + 使用 bcrypt.compare

  ...

🧠 Orchestrator 验证:
  [检查] S-01 确实存在，风险评估正确 ✓
  [检查] S-02 确实存在，影响面评估完整 ✓
  [整合] 审查报告完整可用，无遗漏

🧠 Orchestrator 回复用户:
  "src/auth.js 审查完成，发现 2 个严重问题：
   
   🔴 JWT secret 硬编码在第 15 行，应立即迁移到环境变量
   🔴 密码比较存在弱类型漏洞在第 42 行，应使用 bcrypt.compare
   
   还有 4 个改进建议涉及错误处理和 Token 刷新逻辑。是否需要我委托子智能体逐一修复？"
```

## 关键要点

1. **主控做意图分析** — 不直接执行，先判断类型
2. **委托 prompt 精简** — 只给最小必要上下文
3. **主控验证结果** — 不盲目信任子智能体
4. **主控整合输出** — 用自然语言向用户汇报
