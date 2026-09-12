---
title: "示例 2: 并行委托 — 多个子智能体同时工作"
aliases: [并行委托示例, 多子智能体并行, 交叉验证与优先级排序]
tags: [ai/agent, ai/learning]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# 示例 2: 并行委托 — 多个子智能体同时工作

## 场景
用户准备上线，要求对项目做全面检查：代码审查 + 安全审计 + 文档更新。

## OpenCode 会话

```
👤 用户: "准备上线了，做全面检查"

🧠 Orchestrator 思考:
  [意图分析]
    - review (代码质量)
    - security (安全漏洞)
    - documentation (文档更新)
  [依赖分析]
    - code-reviewer: 独立，无依赖
    - security-auditor: 独立，无依赖
    - doc-writer: 独立，无依赖
  [策略] 三个任务完全独立 → 并行委托，同时执行

🧠 Orchestrator 并行调用:
  ┌─────────────────────────────────────────────┐
  │ Task(code-reviewer, "审查 src/ 全部代码",    │
  │   "...检查错误处理和边界条件...")             │
  │                                              │
  │ Task(security-auditor, "安全审计 src/",       │
  │   "...扫描 OWASP Top 10 和 CWE 漏洞...")      │
  │                                              │
  │ Task(doc-writer, "更新 README 和 API 文档",   │
  │   "...检查 API 签名变更并同步更新文档...")     │
  └─────────────────────────────────────────────┘
        │              │                │
        ▼              ▼                ▼
    并行执行 — 三个子智能体同时工作，互不阻塞
  
  ... (等待全部完成) ...

  🔍 Code Reviewer 返回:  1 严重 + 3 改进
  🛡️ Security Auditor 返回: 2 高危(CSRF + CORS配置错误)
  📝 Doc Writer 返回: README 已更新 + 3 个新 API 端点已文档化

🧠 Orchestrator 整合:
  [交叉验证] code-reviewer 也发现了 CSRF 问题 → 置信度高
  [优先级排序]
    🔴 立即修复(阻塞上线):
      - CSRF Token 缺失 (security-auditor + code-reviewer 双确认)
      - CORS 配置允许任意来源 (security-auditor)
    🟡 上线后修复:
      - 3 项代码改进 (code-reviewer)
    🟢 已完成:
      - 文档已更新 (doc-writer)

🧠 Orchestrator 回复用户:
  "全面检查完成。阻塞上线的问题有 2 个：
   
   🚨 阻塞上线:
   1. CSRF 保护缺失 — 安全审计和代码审查双重确认
   2. CORS 配置过于宽松 — 允许了任意 Origin
   
   📋 上线后尽快修复:
   3. 错误处理中暴露了堆栈信息（3 处）
   
   ✅ 已完成:
   - README 更新了 3 个新 API 端点说明
   - 架构文档同步更新
   
   是否需要我委托 debugger 修复那 2 个阻塞问题？"
```

## 关键要点

1. **并行条件** — 三个子任务操作不同文件/不同维度
2. **交叉验证** — 一个问题被多个子智能体发现 → 提高优先级
3. **结果分层** — 按阻塞/非阻塞分类汇报
4. **决策留给人** — 主控不自动修复上线阻塞问题，询问用户

## 并行 vs 串行决策表

| 场景 | 并行 | 串行 |
|------|:--:|:--:|
| 审查 + 安全审计 | ✅ | |
| 审查 + 测试 | | ✅ (测试可针对审查发现优化) |
| 安全审计 + 文档 | ✅ | |
| Debug + 重构 | | ✅ (先修再重构) |
| 重构 + 测试 | | ✅ (测试验证重构不破坏) |
| 审查 + 安全 + 文档 | ✅ | |

> 🔗 相关文档：[[basic-delegation]] · [[fan-out-demo]] · [[fan-out-pattern]]
