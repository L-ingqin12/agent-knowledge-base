---
title: AI 链接收藏库 MOC
aliases: [AI Links KB, AI链接收藏库, AI-Links MOC]
tags: [moc, ai/links]
created: 2026-08-16
updated: 2026-09-12
status: review
---

# AI 链接收藏库 — MOC

See also: [[AGENTS]] | [[AI大模型开发]] | [[TYPORA-KB-Home]] | [[2026-08-16-AI链接综述与归档]]

## 概述

收藏人「相·易」于 2026/05/05 与 2026/08/16 两批收藏的 18 条（2026-08-16 收藏 16 + 08-18 追加 2）AI 相关链接的调研综述库。子领域定位：**Agent 技能、编码 Agent 解剖、LLM 推理工程、系统设计与 AI 安全**。所有链接逐条给出内容、方向与学习价值评级，并按主题聚类综述。

> [!success] 状态
> 调研已全部完成（16/16 有效）；部分 star 数/版本为快照数据，待作者回访原链接复核 → `review`。

## 文档地图

| 文档 | 内容 |
|---|---|
| [[2026-08-16-AI链接综述与归档]] | ★ 主文档：全景表 + 9 类逐条分析 + 七条主线综述 + 学习价值矩阵 + 四阶段学习路线 |
| [[DSH跨框架Skills与MCP加载]] | DSH 加载外部生态 Skills/MCP 的三条路径（原生发现 / mcp-client / dsh-bridges） |
| [[DSH-TUI插件使用手册]] | 本机 @dsh-tui/dsh-tui 终端界面：安装、运行、快捷键、端点配置 |
| [[DSH插件与Hook开发最佳实践]] | Cordis 插件体系、工具/hooks 开发、发布与最佳实践清单 |
| [[DSH提效与Token插件调研]] | 官方 token-meter + 社区 Token/提效插件清单与推荐组合（2026-08-18） |
| [[DSH会话脱敏项目方法论复盘]] | ★ 方法论：绿测试陷阱、被测量推翻的假设、可证伪守卫与跨平台验证（2026-09-12 新增） |
| [[DSH会话脱敏插件缺陷档案]] | 插件缺陷档案 **22 条**（数据丢失 / 杀进程 / 界面锁死 / 输出误导 / 分页识别 / 工程卫生 / 可移植性）（2026-09-12 新增） |
| [[DSH插件组合与启动中止语义]] | 组合与启动中止：单行挂不上 = 整个 profile 起不来（2026-09-12 新增） |
| [[DSH会话日志格式与读取端约束]] | 会话日志格式与读取端合法性：帧、`seq` 密集、引用字段（2026-09-12 新增） |
| [[DSH会话持久化与活跃改写安全]] | 写入侧：append、崩溃尾截断与重放、活跃改写窗口（2026-09-12 新增） |
| [[DSH工具结果管线与meta陷阱]] | 工具结果管线与 `meta` 落盘陷阱（2026-09-12 新增） |
| [[DSH-TUI内部机制与键盘卡死陷阱]] | TUI 内部机制：键盘让出、面板挂载点优先级、200 格渲染（2026-09-12 新增） |
| [[Articles-Index]] | 远程文章库索引（可解释性/上下文工程/Skill/机制拆解/训练实录 14 篇） |
| [[Open-Magiviz-AI视频创作平台]] | 开源 AI 视频创作 SaaS 参考（追加 2026-08-18） |
| [[Vercel-AI编码Agent-Harness课程]] | Vercel 手写 Agent Harness 课程（11 模块 + Capstone，追加 2026-08-18） |
| [[参考-OpenCode-技术调研报告]] | OpenCode 全机制调研：Agent/Plugin-Hook/自定义工具/Skills/MCP/Server-SDK/社区生态（2026-08-25） |
| [[参考-Pi-Agent-技术调研报告]] | Pi (badlogic→Earendil) 调研：SDK 嵌入/steer-followUp 队列/扩展系统/权限与风险（2026-08-25） |

## 文档关系图

    AI-Links-KB-Home
    ├─ 2026-08-16-AI链接综述与归档 (MAIN)
    │   ├─ Agent Skills: 4 链接
    │   ├─ 编码 Agent 解剖: 3 链接
    │   ├─ 入门教程: 2 链接
    │   ├─ DeepSeek Harness 生态: 2 链接
    │   ├─ 推理与成本工程: 2 链接
    │   ├─ 系统设计/虚拟化: 2 链接
    │   ├─ AI 安全: 1 链接
    │   ├─ AI大模型开发
    │   ├─ TYPORA-KB-Home
    │   └─ 参考-Ark-Agent-Plan计费与配置
    ├─ DSH跨框架Skills与MCP加载 (BRIDGE)
    │   ├─ DSH-TUI插件使用手册 (TUI)
    │   └─ DSH插件与Hook开发最佳实践 (DEVBEST)
    ├─ DSH提效与Token插件调研 (PLUGINS)
    ├─ DSH会话脱敏项目方法论复盘 (REDACT-METHOD, 2026-09-12)
    │   ├─ DSH会话脱敏插件缺陷档案 (REDACT-DEFECTS, 22 条)
    │   ├─ DSH插件组合与启动中止语义 (BOOT)
    │   ├─ DSH会话日志格式与读取端约束 (LOGFMT)
    │   ├─ DSH会话持久化与活跃改写安全 (PERSIST)
    │   ├─ DSH工具结果管线与meta陷阱 (PIPELINE)
    │   └─ DSH-TUI内部机制与键盘卡死陷阱 (TUI-INTERNALS)
    ├─ Articles-Index (ARTICLES)
    ├─ Open-Magiviz-AI视频创作平台 (MAGIVIZ)
    ├─ Vercel-AI编码Agent-Harness课程 (VERCEL)
    └─ AGENTS

## 标签索引

- `#ai/links` — 本子库（链接收藏/综述）
- `#ai/skills` — 技能开发（antigravity/i-have-adhd/pretty-mermaid/diagram-design）
- `#ai/agent` — 编码 Agent（Pi 书/pi-from-scratch/prime-agent/Harness 生态）
- `#ai/learning` — 教程与路线图（copilot-cli/exploreclaudecode/TTFT/system-design）+ 文章库学习类（[[Articles-Index]]：论文精读/上下文工程/Skill/机制拆解 14 篇）
- `#ai/tools` — DSH 插件/Hook 实践与实测（[[DSH会话脱敏插件缺陷档案]]、[[DSH-TUI插件使用手册]]、[[DSH提效与Token插件调研]]）
- `#incident` — 事故与缺陷复盘（[[DSH会话脱敏插件缺陷档案]]、[[CORRECTIONS]] 同源条目）
- `#moc` — 本页

## 关键数据

| 项 | 值 |
|---|---|
| 链接总数 | 18（2026/05/05 × 3，2026/08/16 × 13，2026/08/18 追加 Open-Magiviz、Vercel 课程 × 2） |
| 平均评级 | ★★★★（5★×5，4★×10，3★×3） |
| 调研方式 | flash 式 4 代理并行 web 检索 |
| 归档状态 | `review`（快照数据待作者复核） |

## 脚本清单

无（纯知识归档，本次会话无脚本产出）。

## 另见

- [[2026-08-16-AI链接综述与归档]] — 主文档（本页入口）
- [[Articles-Index]] — 文章库子 MOC：可解释性/上下文工程/Skill/机制拆解 14 篇文章（2026-08-17 迁移）
- [[SESSION-ARCHIVE-2026-08-18]] — 本子库创建会话归档（16 链接调研 + DSH 4 篇落盘 + 远程合并推送）
- [[SESSION-ARCHIVE-2026-08-30]] — dsh/dsh-tui 升级 + 思考强度控制 + Token 优化归档（DSH-TUI 手册与 Token 调研同步更新）
- [[SESSION-ARCHIVE-2026-09-12]] — DSH 会话日志脱敏（预防 + 修复两个插件）与平台研究：7 篇 DSH 实测笔记的产出会话，含首次推送 CI 37 秒红的记录
- 本 vault 其他复盘：[[v2rayn-balancer-复盘-2026-08-09]]、[[2026-07-21-树莓派网络故障与路由器破解完整复盘]]
