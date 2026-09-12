---
title: Fan-Out 扇出演示 — Orchestrator 并行分发任务
aliases: [Fan-Out 演示, 并行分发实测, 扇出性能对比]
tags: [ai/agent, ai/learning]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# Fan-Out 扇出演示 — Orchestrator 并行分发任务

## 场景

用户要求对 `src/auth.js` 同时做代码审查 + 安全审计 + 文档生成。这是典型的 Fan-Out 场景 — 三个独立任务可以并行执行。

## Orchestrator 内部决策过程

```
👤 用户: "审查 src/auth.js 代码质量，同时做安全审计，并补充文档"

🧠 Orchestrator 自规划:

  Step 1: 意图分析
    ├─ "审查" → code-reviewer
    ├─ "安全审计" → security-auditor
    └─ "文档" → doc-writer

  Step 2: 依赖判断
    ├─ code-reviewer: 只读 src/auth.js ✓
    ├─ security-auditor: 只读 src/auth.js ✓
    └─ doc-writer: 写 docs/ 不碰 src/ ✓
    → 三个任务操作不同维度/文件 → 可并行！

  Step 3: Fan-Out 执行
    ┌─────────────────────────────────────────────────────┐
    │ 并行调用（3 个子智能体同时工作）:                    │
    │                                                      │
    │  code-reviewer, 审查 src/auth.js 代码质量            │
    │  security-auditor, 安全审计 src/auth.js              │
    │  doc-writer, 为 src/auth.js 编写 API 文档           │
    │                                                      │
    │  预期耗时: max(2min, 3min, 1min) = 3min              │
    │  串行耗时: 2 + 3 + 1 = 6min                          │
    │  Fan-Out 加速: 2x                                    │
    └─────────────────────────────────────────────────────┘

  Step 4: 汇总
    收集三个子智能体结果 → 交叉验证 → 优先级排序 → 汇报用户
```

## 预期输出（汇总后）

```markdown
## Fan-Out 审查报告 — src/auth.js

### 🔴 阻塞问题 (双确认 — code-reviewer + security-auditor 共同发现)
1. **JWT 密钥硬编码** — src/auth.js:5
   - code-reviewer: "[S-01] 敏感信息硬编码，应迁移到环境变量"
   - security-auditor: "[CRIT-01] CWE-798: 硬编码凭据"

2. **密码明文存储** — src/auth.js:13
   - code-reviewer: "[S-02] 密码未哈希，应使用 bcrypt"
   - security-auditor: "[CRIT-02] CWE-312: 敏感数据明文存储"

### 🟡 单方面发现
3. **弱比较运算符** (code-reviewer) — src/auth.js:17
4. **错误信息泄漏用户存在性** (security-auditor) — src/auth.js:24
5. **缺少速率限制** (security-auditor) — src/auth.js:29

### ✅ 已完成
6. API 文档已生成: docs/auth-api.md (doc-writer)

### 统计
- 并行耗时: ~3 分钟 (vs 串行 6 分钟)
- 加速比: 2x
- 交叉验证发现: 2 个双确认问题
```

## 并行 vs 串行性能对比

```
Fan-Out 并行:
  code-reviewer    ████████████████ (2 min)
  security-auditor ██████████████████████ (3 min) ← 瓶颈
  doc-writer       ████████ (1 min)
  总耗时: 3 min

串行执行:
  code-reviewer → security-auditor → doc-writer
  ████████████████ ██████████████████████ ████████
  总耗时: 6 min
```

## 防冲突规则验证

```
场景 A: 两个只读 + 一个写（不冲突的文件）
  ✅ code-reviewer (只读 src/) + security-auditor (只读 src/) + doc-writer (写 docs/)
  → 可以并行

场景 B: 两个写（不同文件）
  ✅ test-writer (写 tests/) + doc-writer (写 docs/)
  → 可以并行

场景 C: 两个写（同一文件）
  ❌ refactor-specialist (写 src/auth.js) + debugger (写 src/auth.js)
  → 必须串行，防止冲突

场景 D: 写 + 只读（同一文件）
  ✅ debugger (写 src/auth.js) + code-reviewer (只读 src/auth.js)
  → 可以并行（但 code-reviewer 读到的可能是修改前的版本）
```

## 如何运行此测试

```bash
# 1. 进入测试项目
cd /root/test-opencode-project

# 2. 用 orchestrator + 可用的模型
opencode run \
  --agent orchestrator \
  --model <your-working-model> \
  "审查 src/auth.js 代码质量，同时做安全审计，并补充文档"

# 3. 观察输出
# - Orchestrator 应自动识别三个独立任务
# - 并行调用 code-reviewer, security-auditor, doc-writer
# - 汇总结果后输出 Fan-Out 审查报告
```

## 当前环境状态

| 检查项 | 状态 |
|--------|:--:|
| OpenCode v1.17.13 安装 | ✅ |
| 7 个智能体定义加载 | ✅ |
| 权限配置正确 | ✅ |
| Agent list 识别所有智能体 | ✅ |
| Debug config 解析正确 | ✅ |
| 免费模型 API 连接 | ❌ TLS 证书验证失败（环境限制） |

> 🔗 相关文档：[[fan-out-pattern]] · [[parallel-execution]] · [[fan-out-subagent-pattern]]
