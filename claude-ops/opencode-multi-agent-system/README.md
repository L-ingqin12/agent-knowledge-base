# OpenCode Multi-Agent Collaboration System

一个基于 OpenCode 的生产级多智能体协作系统。包含 1 个主 Orchestrator 和 6 个专业子智能体，覆盖软件开发生命周期中的核心环节。

## ✨ 特性

- 🧠 **智能路由**: 主智能体自动分析意图，将任务路由到最合适的子智能体
- 🔀 **并行调度**: 独立子任务自动并行执行，最大化效率
- 🔒 **权限隔离**: 审查/安全类子智能体只读，生成/修复类才有写权限
- 📋 **标准化输出**: 每个子智能体都有结构化的输出模板
- 🔌 **即插即用**: 复制 `.opencode/agent/` 到任何项目即可使用

## 📦 快速开始

```bash
# 1. 克隆
git clone https://github.com/L-ingqin12/opencode-multi-agent-system.git
cd opencode-multi-agent-system

# 2. 安装 OpenCode
curl -fsSL https://opencode.ai/install | bash

# 3. 在你的项目中使用
cp -r .opencode /path/to/your-project/
cp AGENTS.md /path/to/your-project/

# 4. 启动
cd /path/to/your-project
opencode
```

在 OpenCode 会话中直接描述任务，主智能体会自动调度子智能体。

## 🏗️ 架构

```
👤 用户请求
     │
🧠 Orchestrator (主智能体: 意图分析 → 任务分解 → 调度 → 验证)
     │
     ├── 🔍 Code Reviewer    → 代码审查 (只读)
     ├── 🧪 Test Writer       → 测试生成 (读写)
     ├── 📝 Doc Writer        → 文档生成 (读写)
     ├── 🛡️ Security Auditor → 安全审计 (只读)
     ├── ♻️  Refactor Spec    → 代码重构 (读写)
     └── 🐛 Debugger          → Bug 定位修复 (读写)
```

## 🤖 子智能体

| 智能体 | 触发词 | 权限 | 说明 |
|-------|--------|------|------|
| `code-reviewer` | review, 审查 | 只读 | 审查正确性/安全/性能/可维护性 |
| `test-writer` | test, 测试 | 读写 | 自动检测框架，生成单元/集成/E2E 测试 |
| `doc-writer` | doc, 文档 | 读写 | README/API/架构/变更日志 |
| `security-auditor` | security, 安全 | 只读 | OWASP Top 10 / CWE 扫描 |
| `refactor-specialist` | refactor, 重构 | 读写 | 消除代码味道，不改变外部行为 |
| `debugger` | debug, bug | 读写 | 根因定位 → 最小修复 → 回归建议 |

## 🎯 使用场景

```bash
# 单一任务
"审查 src/auth.js 的代码质量"

# 并行复合任务
"审查所有代码、做安全扫描、同时更新文档"

# 串行依赖任务
"找出登录超时的根因，修好后重构该模块"

# 上线检查
"准备上线，执行全面检查清单"
```

## 📁 项目结构

```
.
├── .opencode/agent/           # 智能体定义
│   ├── orchestrator.md        # 主智能体
│   ├── code-reviewer.md       # 代码审查
│   ├── test-writer.md         # 测试编写
│   ├── doc-writer.md          # 文档编写
│   ├── security-auditor.md    # 安全审计
│   ├── refactor-specialist.md # 代码重构
│   └── debugger.md            # 调试排错
├── AGENTS.md                  # OpenCode 系统文档
├── README.md                  # 本文件
├── examples/                  # 使用示例
├── workflows/                 # 预设工作流
└── slash-commands/            # 快捷命令
```

## 📄 License

MIT
