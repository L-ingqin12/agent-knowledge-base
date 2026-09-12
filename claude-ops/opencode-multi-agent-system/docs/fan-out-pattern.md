# Fan-Out 子智能体分发模式

## 什么是 Fan-Out

Fan-Out（扇出）是主智能体将复杂任务分解为 N 个子任务后，**一次性并行分发给多个子智能体**，然后汇总结果的模式。

```
                      ┌─────────────────┐
                      │  🧠 Orchestrator │
                      │  (任务分解+汇总)  │
                      └───────┬─────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐
    │ Subagent 1│      │ Subagent 2│      │ Subagent 3│
    │ (独立执行) │      │ (独立执行) │      │ (独立执行) │
    └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                      ┌───────▼─────────┐
                      │  📊 汇总结果     │
                      │  (交叉验证+排序) │
                      └─────────────────┘
```

## Fan-Out vs 串行 vs 单智能体

| 模式 | 延迟 | 吞吐 | 适用场景 |
|------|------|------|---------|
| **Fan-Out 并行** | 等于最慢子任务 | 高 | 独立子任务（审查+安全+文档） |
| **串行链** | 所有子任务之和 | 低 | 有依赖的子任务（debug→refactor→test） |
| **单智能体** | 无调度开销 | 中 | 简单操作，不需要多专家 |

## OpenCode 生态中的 Fan-Out 实现

OpenCode 目前**原生不支持** Fan-Out（`task` 工具一次只能调用一个子智能体）。
但社区已构建了多种 Fan-Out 方案：

### 方案对比

| 方案 | 机制 | 最大并行数 | 非阻塞 | 依赖管理 |
|------|------|:--------:|:------:|:------:|
| **opencode-agent-intercom** | `spawn()` 非阻塞创建 | 可配置 | ✅ 200ms 返回 | ❌ |
| **Ouroboros Bridge** | MCP 工具钩子 | 10 | ✅ | ❌ |
| **swarm-control** | `/swarm_spawn` 文件分解 | 4 | ✅ | ✅ 文件锁 |
| **Ephemeral Team (提案中)** | `team()` 原生 API | 可配置 | ✅ | ✅ DAG |
| **subtask2** | `parallel` 命令数组 | N | ✅ | ✅ return 链 |
| **本系统 (Orchestrator 模拟)** | 多次 Task 调用 | 3-5 | ❌ 顺序发起 | ✅ 人工判断 |

### 推荐方案: opencode-agent-intercom

这是目前最成熟的 Fan-Out 方案：

```bash
npm install opencode-agent-intercom
```

```json
// opencode.json
{
  "plugins": ["opencode-agent-intercom"]
}
```

配置后，Orchestrator 可以这样 Fan-Out：

```
Orchestrator 收到用户请求: "审查所有代码、做安全审计、更新文档"

Orchestrator:
  spawn(code-reviewer, "审查 src/ 全部代码")
  spawn(security-auditor, "安全审计 src/")
  spawn(doc-writer, "更新 API 文档")

  → 三个 spawn() 都在 200ms 内返回
  → 三个子智能体并行工作
  → Orchestrator 继续响应用户（不阻塞）
  → 每个子智能体完成后自动通知 Orchestrator
  → Orchestrator 汇总结果
```

### 本系统的 Fan-Out 策略

即使不安装插件，Orchestrator 的设计也支持 Fan-Out 模式：

```
🧠 Orchestrator 自规划 Fan-Out 流程:

1. 收到用户请求
2. 意图分析 → 识别 3 个独立子任务
3. 检查子任务是否操作不同文件/维度 → 确认可并行
4. 并行调用子智能体:
   code-reviewer, 审查 src/ 全部代码
   security-auditor, 安全审计 src/
   doc-writer, 更新 README
5. 等待所有子智能体返回
6. 交叉验证结果（同一问题被多个子智能体发现 → 提升优先级）
7. 按优先级排序 → 汇报用户
```

## Fan-Out 适用条件判断

Orchestrator 在决策时使用以下判断逻辑：

```
可以 Fan-Out (并行):
  ✅ 子任务操作不同文件
  ✅ 子任务操作同一文件但不同维度 (审查 vs 测试)
  ✅ 子任务都是只读操作 (审查 + 安全审计)
  ✅ 子任务无状态依赖

不能 Fan-Out (必须串行):
  ❌ 子任务操作同一文件且都有写权限 (冲突风险)
  ❌ 子任务 B 依赖子任务 A 的输出 (debug → refactor)
  ❌ 子任务 C 需要子任务 B 完成后才能确定范围
```

## Fan-Out 防冲突机制

```
规则 1: 有写权限的子智能体永不并行操作同一文件
规则 2: 只读子智能体可以任意并行
规则 3: 写 + 只读可以并行（只读访问的是操作前的快照）
规则 4: 并行上限: 5 个子智能体
规则 5: 汇总阶段做交叉验证
```

## Fan-Out 实战示例

### 场景: 上线前全面检查

```
👤 用户: "准备上线 v2.0.0，做全面检查"

🧠 Orchestrator 自规划:
  [意图分析] review + security + docs → 3 个独立任务
  [冲突检查] 
    - code-reviewer: 只读 ✓
    - security-auditor: 只读 ✓
    - doc-writer: 写 docs/ 不碰 src/ ✓
  [决策] Fan-Out 并行！

⚡ 并行调用:
  code-reviewer, 审查 src/ 全部代码 (预计 2 分钟)
  security-auditor, 扫描 OWASP Top 10 + 依赖 CVE (预计 3 分钟)
  doc-writer, 更新 README 和 CHANGELOG (预计 1 分钟)

📊 汇总 (等待最慢的 security-auditor, 约 3 分钟):

  交叉验证发现:
    - CSRF 缺失: code-reviewer ✅ + security-auditor ✅ → 双确认 → 优先级提升
    - 硬编码密钥: security-auditor 发现, code-reviewer 未提及 → 补充审查

  优先级排序:
    🔴 阻塞: CSRF 缺失 (双确认), 硬编码密钥
    🟡 改进: 错误处理中的堆栈泄漏, 未使用参数
    🟢 完成: README 已更新

  → 总耗时: ~3 分钟 (vs 串行 6 分钟)
```

## 与 Claude Code 的对比

| 特性 | OpenCode + 插件 | Claude Code |
|------|:---:|:---:|
| 原生 Agent 工具 | ❌ (需插件) | ✅ `Agent` 工具 |
| Fan-Out 并行 | ✅ 通过 intercom | ✅ `background: true` |
| Task DAG | ✅ Ephemeral Team (提案) | ✅ Workflow |
| 会话隔离 | ✅ 每个子智能体独立 | ✅ isolation: worktree |
| 远程执行 | ❌ | ✅ isolation: remote |

## 参考资料

- [Ephemeral Sub-Agent Teams (Issue #19999)](https://github.com/anomalyco/opencode/issues/19999) — 原生 team() 提案
- [opencode-agent-intercom](https://www.npmjs.com/package/opencode-agent-intercom) — 最成熟的 Fan-Out 插件
- [Ouroboros Bridge](https://github.com/Q00/ouroboros) — MCP 钩子 Fan-Out
- [swarm-control](https://www.npmjs.com/package/swarm-control) — 文件级并行调度
- [Subagent task delegation (Issue #1293)](https://github.com/anomalyco/opencode/issues/1293) — 子智能体机制起源
