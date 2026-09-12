# 状态机式质量门控系统

## 核心问题

单次委托子智能体的缺陷：
- 子智能体可能输出不完整/不准确的结果
- 没有反馈机制让子智能体修正
- 质量问题在最终阶段才暴露

**解决方案**: 引入状态机控制流——每个子智能体输出经过验证门，不通过则携带反馈回环重试，直到满足质量标准。

## 状态机架构

```
                              ┌─────────────────────────────────────┐
                              │         STATE MACHINE               │
                              │                                     │
    ┌──────┐    ┌──────────┐  │  ┌──────────┐    ┌──────────┐      │
    │START │───→│ ANALYZE  │──┼─→│ DELEGATE │───→│ VERIFY   │──┐   │
    └──────┘    └──────────┘  │  └──────────┘    └──────────┘  │   │
                              │       ↑               │        │   │
                              │       │          ┌────┴────┐   │   │
                              │       │          │ pass?   │   │   │
                              │       │          └────┬────┘   │   │
                              │       │               │ no     │   │
                              │       │          ┌────▼────┐   │   │
                              │       │          │ RETRY   │───┘   │
                              │       │          │ (N<3,   │       │
                              │       │          │ +feedback)       │
                              │       │          └────┬────┘       │
                              │       │               │ N≥3        │
                              │       │          ┌────▼────┐       │
                              │       │          │ESCALATE │       │
                              │       │          └─────────┘       │
                              │       │               │ yes        │
                              │       │               ▼            │
                              │  ┌────┴────┐    ┌──────────┐      │
                              │  │ all done?│←───│INTEGRATE │      │
                              │  └────┬────┘    └──────────┘      │
                              │       │ no                         │
                              │       ▼                            │
                              │  ┌──────────┐                      │
                              │  │  DONE    │                      │
                              │  └──────────┘                      │
                              └─────────────────────────────────────┘
```

## 状态定义

| 状态 | 描述 | 触发条件 | 下一状态 |
|------|------|---------|---------|
| **ANALYZE** | 意图分析 + 任务分解 | 用户请求进入 | → DELEGATE |
| **DELEGATE** | 构造 prompt + 调用子智能体 | 有未分配的 (子) 任务 | → VERIFY |
| **VERIFY** | 质量检查子智能体输出 | 子智能体返回结果 | → INTEGRATE (通过) / RETRY (不通过) |
| **RETRY** | 携带反馈重新委托 | 验证不通过 + retry < 3 | → DELEGATE (同一任务 + 反馈) |
| **ESCALATE** | 超过最大重试，上报用户 | 验证不通过 + retry ≥ 3 | → 等待用户决策 |
| **INTEGRATE** | 整合已验证的结果 | VERIFY 通过 | → DONE (全部完成) / DELEGATE (还有任务) |
| **DONE** | 向用户汇报最终结果 | 所有任务 INTEGRATE 完成 | → 等待新请求 |

## 质量门控规则 (VERIFY 状态)

每个子智能体输出经过以下门控检查：

### 代码生成类 (test-writer, refactor-specialist, debugger, doc-writer)

```yaml
gates:
  - name: syntax
    rule: 代码语法必须正确
    check: 尝试静态解析或检查明显语法错误
    severity: BLOCKER
    
  - name: completeness
    rule: 输出必须包含预期字段（代码/测试/文档正文 + 运行说明）
    check: 检查是否只有描述没有实际产物
    severity: BLOCKER
    
  - name: consistency
    rule: 修改后的代码风格必须与项目一致
    check: 缩进/命名/引号风格是否匹配
    severity: WARNING
    
  - name: no_hallucination
    rule: 不能引用不存在的文件/API/函数
    check: 用 grep 验证引用的所有符号是否存在
    severity: BLOCKER
```

### 分析类 (code-reviewer, security-auditor)

```yaml
gates:
  - name: specificity
    rule: 每个发现必须引用具体行号
    check: 报告中是否包含 file:line 引用
    severity: BLOCKER
    
  - name: actionable
    rule: 每个问题必须有可操作的修复建议
    check: 是否有 "修复:" 块
    severity: WARNING
    
  - name: file_check
    rule: 引用的文件路径必须存在
    check: glob/read 验证
    severity: BLOCKER
```

## RETRY 状态的反馈机制

每次重试时，向子智能体传递上一轮的失败原因：

```
RETRY #N 时传递给子智能体的额外上下文:

## ⚠️ 上一轮未通过质量检查
### 阻塞问题 (必须修复):
- [GATE:syntax] {具体的语法错误位置和修复建议}
- [GATE:completeness] {缺少的部分}

### 改进建议:
- [GATE:consistency] {风格不匹配的具体位置}

### 本轮要求:
请基于以上反馈修正输出，确保所有阻塞问题已解决。
```

## 环控制算法（Orchestrator 系统指令中的伪代码）

```
function processRequest(userRequest):
    tasks = analyzeAndDecompose(userRequest)
    results = {}
    completed = false
    
    while not completed:
        for each task in tasks:
            if task.isComplete:
                continue
            
            // 进入 DELEGATE
            prompt = buildPrompt(task)
            if task.retryCount > 0:
                prompt += buildFeedback(task.previousFailures)
            
            output = delegate(task.subagent, prompt)
            task.retryCount++
            
            // 进入 VERIFY
            failures = runQualityGates(task.subagent, output)
            
            if failures.has(severity=BLOCKER):
                if task.retryCount >= MAX_RETRIES(3):
                    escalateToUser(task, failures)  // 进入 ESCALATE
                    return  // 等待用户
                else:
                    task.previousFailures = failures
                    // 回环到 DELEGATE (继续 for 循环)
                    continue
            
            // 通过 → 进入 INTEGRATE
            results[task.id] = output
            task.isComplete = true
        
        completed = all tasks are complete
    
    // 进入 DONE
    return integrateAndReport(results)
```

## 实战示例：Bug 修复环

```
用户: "修复 src/auth.js 中密码明文存储的问题"

═══════════════════════════════════════════
Round 1
═══════════════════════════════════════════

[ANALYZE] → 单一任务: debugger 定位 + 修复
[DELEGATE] → debugger, "定位并修复 src/auth.js 密码明文存储"
[VERIFY]   → 
  ✅ Gate:syntax — 代码语法正确
  ❌ Gate:completeness — 只加了 bcrypt.hash() 但没有导入 bcrypt 模块!
  ✅ Gate:consistency — 代码风格匹配

→ FAIL → RETRY Round 2

═══════════════════════════════════════════
Round 2 (携带反馈)
═══════════════════════════════════════════

[DELEGATE] → debugger, "
  修复 src/auth.js 密码明文存储
  
  ## ⚠️ 上一轮未通过:
  [GATE:completeness] 使用了 bcrypt.hash() 但缺少 `const bcrypt = require('bcrypt')` 
  导入语句。同时检查是否需要更新 package.json 添加 bcrypt 依赖。
"
[VERIFY]   → 
  ✅ Gate:syntax — 正确
  ✅ Gate:completeness — bcrypt 已导入 + package.json 已更新
  ✅ Gate:no_hallucination — bcrypt 是真实存在的 npm 包

→ PASS → INTEGRATE → DONE ✓
```

## 跨智能体验证环

当一个子智能体的输出被另一个子智能体质疑时，触发跨智能体回环：

```
场景: code-reviewer 和 security-auditor 并行审查

code-reviewer 输出: "[W-03] bcrypt saltRounds=10 不够安全"
security-auditor 输出: "未发现加密相关漏洞"

→ INTEGRATE 时发现冲突!
→ VERIFY (交叉): bcrypt saltRounds=10 是否是安全问题?
→ 查阅 OWASP 标准: saltRounds≥10 符合当前最佳实践
→ code-reviewer 的 W-03 降级为 false positive
→ 不需要回环，直接调整结果
```

## 死循环保护

```yaml
loop_protection:
  max_retries_per_subtask: 3
  max_total_rounds: 10
  same_failure_threshold: 2    # 同一问题连续失败 2 次 → 不再重试 → ESCALATE
  deadlock_detection: true     # 检测子任务间的循环依赖
```

## 状态转换日志格式

每次状态转换记录到日志，便于追踪决策链：

```
[ANALYZE] User request: "修复密码明文存储"
  → 分解: 1 task → debugger
[DELEGATE:debugger:R1] "定位并修复 src/auth.js..."
[VERIFY:debugger:R1] FAIL — completeness gate: missing import
[RETRY:debugger:R2] Added feedback: "缺少 bcrypt 导入..."
[DELEGATE:debugger:R2] "修正: 添加 bcrypt 导入..."
[VERIFY:debugger:R2] PASS — all gates clear
[INTEGRATE] Result validated and applied
[DONE] Reported to user
```

## 与 Fan-Out 的组合

Fan-Out 并行 + 每个子任务独立状态机：

```
                    ┌─────────────┐
                    │   ANALYZE   │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
       ┌────▼────┐   ┌─────▼────┐   ┌────▼────┐
       │Task A   │   │ Task B   │   │ Task C  │
       │State    │   │ State    │   │ State   │
       │Machine  │   │ Machine  │   │ Machine │
       │(DELEGATE│   │(DELEGATE│   │(DELEGATE│
       │→VERIFY  │   │→VERIFY  │   │→VERIFY  │
       │→RETRY)  │   │→PASS ✓) │   │→RETRY  │
       │  ...    │   │          │   │  ...    │
       └────┬────┘   └─────┬────┘   └────┬────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                    ┌──────▼──────┐
                    │  INTEGRATE  │
                    │  (交叉验证)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    DONE     │
                    └─────────────┘

注: Task A 和 Task C 各自在 RETRY 中循环，
    不影响 Task B (已通过) — 独立的环。
```

## 实现建议

### 方案 A: 纯 System Prompt (当前可行)

将状态机逻辑嵌入 Orchestrator 的 system prompt，让 LLM 自己管理状态转换。
**优点**: 无需代码改动，立即可用
**缺点**: 依赖 LLM 自律执行，可能遗漏检查

### 方案 B: Hook 插件 (推荐)

利用 OpenCode 的 hook 系统实现真正的状态机：
```json
// opencode.json
{
  "hooks": {
    "tool.execute.after": [".opencode/hooks/quality-gate.js"]
  }
}
```
**优点**: 强制执行，不会遗漏
**缺点**: 需要编写 hook 代码

### 方案 C: Workflow Engine (未来)

等待 Ephemeral Team API 原生支持 DAG + 回环。
