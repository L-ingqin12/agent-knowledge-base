# /review — 代码审查快捷命令

通过 slash command 快速触发代码审查。

## 用法

```
/review <文件路径>
/review <文件路径> --focus=<安全|性能|可维护性>
/review --diff  # 审查当前未提交的变更
```

## 实现

触发 Orchestrator 委托 `code-reviewer` 子智能体：

```
主控收到 /review 命令
  → 解析目标文件和焦点
  → 委托 Task(code-reviewer, "审查 {file}，聚焦 {focus}")
  → 验证结果
  → 输出审查报告
```

## 示例

```
👤 /review src/auth.js --focus=安全

🧠 委托 code-reviewer 审查 src/auth.js，聚焦安全问题
🔍 发现 JWT 密钥硬编码 + 密码未哈希存储
→ 输出安全审查报告
```
