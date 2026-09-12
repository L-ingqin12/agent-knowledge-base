---
title: README — 仓库总览
aliases: [README, repo-readme, 知识库总览]
tags: [meta, moc]
created: 2026-09-12
updated: 2026-09-12
status: stable
---

# agent-knowledge-base

> [!abstract] 这是什么
> 一个**版本化的个人技术知识库**，以 Obsidian Vault 形式组织，覆盖 AI Agent 工程、无人值守运维、网络设备与计算机基础。
> 全库使用 `[[Wikilink]]` 双链导航，每篇文档含 YAML frontmatter。
>
> **本仓库是「脱敏发布线」**——本地工作副本含真实 IP / 口令 / 端口，推送前经脱敏规则替换为占位符（`[已脱敏]`、`[IP已脱敏]`、`%USERPROFILE%`）。

---

## 快速开始

```bash
git clone https://github.com/L-ingqin12/agent-knowledge-base.git
# 用 Obsidian 打开该目录即可（已含 .obsidian 配置与 Dataview 插件）
```

推荐在 Obsidian 中从 **[[HOME]]** 进入——它是全库导航入口，列出所有子目录及其 MOC。

---

## 目录结构

| 目录 | 主题 | 入口 |
|---|---|---|
| `claude-ops/` | Claude Code 无人值守运维：方案设计 / 事故复盘 / Agent 架构模式 | [[Claude-Ops-KB-Home]] |
| `ai-dev/` | LLM 应用开发实战：Prompt / RAG / Agent / MCP / 微调 | [[AI-Dev-KB-Home]] |
| `ai-links/` | AI 链接收藏与调研综述；DSH 源码分析 | [[AI-Links-KB-Home]] |
| `network/` | 家庭网络：WiFi / 小米路由器 / 代理 / 排障复盘 | [[Network-KB-Home]] |
| `cs-base/` | 计算机基础：语言 / 算法 / 系统 / 数据库 / 工具链 | [[CS-KB-Home]] |
| `typora/` | Typora 复盘与可复用流程 | [[TYPORA-KB-Home]] |
| `sources/` | 外部来源登记（供 [[URL-Lookup]] 按场景检索） | `sources/README.md` |
| `scripts/` | 跨库脚本：部署框架 / 中继 / 日志分析 PoC | `scripts/claude-ops-deployments/README.md` |
| `diagrams/` | Excalidraw 图表库（绘图规范） | [[ARROW-CHECKLIST]] |
| `_archive/` | 会话归档（SESSION-ARCHIVE-*.md） | — |

**根目录关键文件**

| 文件 | 作用 |
|---|---|
| [[HOME]] | 全局导航入口 |
| [[AGENTS]] | AI 协作规范（**含错误记忆协议**：出结论前先回查 [[CORRECTIONS]]） |
| [[CORRECTIONS]] | 方法论错误记忆库——记录判断错过的结论与可复用判定规则 |
| [[URL-REGISTRY]] | URL 登记册（按「何时使用」组织的外部来源索引） |
| [[URL-Lookup]] | URL 速查台（Dataview 动态检索端） |

---

## 组织约定

- **一文档一问题**：跨主题内容拆分，用 Wikilink 关联；每篇至少 3 条有效双链
- **frontmatter 必填**：`title` / `aliases` / `tags` / `created` / `updated` / `status`
- **标签嵌套**：`category/sub`（如 `ai/agent`、`network/proxy`、`cs/toolchain`）
- **禁止 Mermaid**：图表统一用 Excalidraw（见 [[AGENTS]] 第十一节）
- **功能配置不套知识文档格式**：`SKILL.md`、`.opencode/` 下的 agent/command 定义属**可执行配置**，加 Obsidian frontmatter 会破坏其加载

---

## 脱敏与安全

> [!danger] 本仓库是公开的，推送前必须脱敏
> 本地工作副本与发布线**内容不同**：本地保留真实值便于直接使用，推送时由规则替换。

脱敏规则位于 `.git/kb-push-redactions`（在 `.git/` 下，**永不推送**，因此可安全写入被脱敏的字面量）。当前覆盖：

| 类别 | 替换为 |
|---|---|
| 本机用户名（路径形态） | `%USERPROFILE%` |
| 内网 IP | `[IP已脱敏]` |
| SSH 口令（`-p "…"` / `--password=` / `SSHPASS=`） | `[已脱敏]` |
| API 密钥前缀与截断引用（`sk-` 前缀与截断引用（`A...B` 形式）） | `<REDACTED>` |
| 代理订阅 URL（含长 hex 路径 token） | `<SUB_URL_REDACTED>` |

> [!warning] 三条踩过的坑（详见 [[CORRECTIONS]]）
> 1. **脱敏正则要按「实际观测到的形态」写**——`sk-<前缀>[A-Za-z0-9]{3,}` 匹配不到 `sk-<前缀>*******`，星号不在字符类里
> 2. **注意截断引用** `sk-xxxx...yyyy`——它同时泄露首尾两段，只匹配长串会漏
> 3. **脱敏范围包含「自己写的文档」**——记录/复盘类文档里引用被清理的值，会把它们重新带回来

**本仓库历史经过一次全量改写**（2026-09-12），用于清除早期提交中的明文凭据。因此 2026-09-12 之前的提交哈希与任何 fork 已不兼容。

---

## 相关仓库

| 仓库 | 状态 |
|---|---|
| `L-ingqin12/hermes-ops` | **已转为重定向引用**——内容已并入本库 `claude-ops/hermes-ops/`，该仓库 README 保留迁移映射，供树莓派侧 Hermes Agent 定位新库 |

---

## 许可与使用

个人技术笔记集合，含少量第三方资料的整理与引用（已在文档内标注来源）。如需引用请注明出处。
