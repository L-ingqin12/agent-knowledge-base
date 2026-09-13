---
title: AI 链接收藏库 MOC
aliases: [AI Links KB, AI链接收藏库, AI-Links MOC]
tags: [moc, ai/links]
created: 2026-08-16
updated: 2026-09-13
status: review
---

# AI 链接收藏库 — MOC

See also: [[AGENTS]] | [[AI大模型开发]] | [[TYPORA-KB-Home]] | [[2026-08-16-AI链接综述与归档]]

## 概述

收藏人「相·易」于 2026/05/05 与 2026/08/16 两批收藏的 18 条（2026/05/05 × 3 + 2026/08/16 × 13 = 16，2026-08-18 追加 × 2，共 18）AI 相关链接的调研综述库。子领域定位：**Agent 技能、编码 Agent 解剖、LLM 推理工程、系统设计与 AI 安全** + 2026-08-18 追加的 **AI 应用层（Open-Magiviz）与 Agent Harness 课程（Vercel Academy）**。所有链接逐条给出内容、方向与学习价值评级，并按主题聚类综述。

> [!warning] 更正（2026-09-13）：原文写作「18 条（2026-08-16 收藏 16 + 08-18 追加 2）」，把 2026/05/05 的 3 条并入了 08/16 批次，与主文档 §一 及本页「关键数据」行不符（原表述保留于此）。正确拆分：05/05 × 3 + 08/16 × 13 = 16，08/18 追加 × 2 = 18。

> [!success] 状态
> 调研已全部完成（原表述为「16/16 有效」——该计数只覆盖首批 16 条，2026-08-18 追加的 #17/#18 从未纳入，现状应为 18 条）；部分 star 数/版本为快照数据，待作者回访原链接复核 → `review`。
>
> **待复核清单（2026-09-13 补，逐项可执行）**
> - ✅ **#18 Vercel Academy 课程模块数** —— 已核对：Introduction + 11 模块 + Capstone，与主文档 §I 一致，可关闭。
> - ⏳ **#1 仓库名** —— 2026-09-13 复核确认已改名 `antigravity-awesome-skills` → `agentic-awesome-skills`；重定向状态待用 api.github.com 独立复核。
> - ⏳ **#15 diagram-design 图表类型数与兼容宿主** —— 2026-09-13 按 README 更正为 39 种、Claude Code / Codex / Factory Droid / Pi / Agent Skills 五类宿主；star 数待复核。

## 文档地图

| 文档 | 内容 |
|---|---|
| [[2026-08-16-AI链接综述与归档]] | ★ 主文档：全景表 + 9 类逐条分析 + 七条主线综述 + 学习价值矩阵 + 四阶段学习路线 |
| [[DSH跨框架Skills与MCP加载]] | DSH 加载外部生态 Skills/MCP 的三条路径（原生发现 / mcp-client / dsh-bridges） |
| [[DSH-TUI插件使用手册]] | 本机 @dsh-tui/dsh-tui 终端界面：安装、运行、快捷键、端点配置 |
| [[DSH插件与Hook开发最佳实践]] | Cordis 插件体系、工具/hooks 开发、发布与最佳实践清单 |
| [[DSH插件发布与分发]] | ★ 发布/分发闭环：**官方没有市场**（`dsh plugin` 是 pnpm 薄包装）、topic/keyword 双信号、monorepo 收录坎、`files` 白名单与可证伪守卫、供应链核查（2026-09-13 新增） |
| [[DSH提效与Token插件调研]] | 官方 token-meter + 社区 Token/提效插件清单与推荐组合（2026-08-18） |
| [[DSH会话脱敏项目方法论复盘]] | ★ 方法论：绿测试陷阱、被测量推翻的假设、可证伪守卫与跨平台验证（2026-09-12 新增） |
| [[DSH会话脱敏插件缺陷档案]] | 插件缺陷档案 **22 条**（数据丢失 / 杀进程 / 界面锁死 / 输出误导 / 分页识别 / 工程卫生 / 可移植性）（2026-09-12 新增） |
| [[DSH插件组合与启动中止语义]] | 组合与启动中止：单行挂不上 = 整个 profile 起不来（2026-09-12 新增） |
| [[DSH会话日志格式与读取端约束]] | 会话日志格式与读取端合法性：帧、`seq` 密集、引用字段（2026-09-12 新增） |
| [[DSH会话持久化与活跃改写安全]] | 写入侧：append、崩溃尾截断与重放、活跃改写窗口（2026-09-12 新增） |
| [[DSH工具结果管线与meta陷阱]] | 工具结果管线与 `meta` 落盘陷阱（2026-09-12 新增） |
| [[DSH-TUI内部机制与键盘卡死陷阱]] | TUI 内部机制：键盘让出、面板挂载点优先级、200 格渲染（2026-09-12 新增） |
| [[Articles-Index]] | 远程文章库索引（可解释性/上下文工程/Skill/机制拆解/多智能体编排/训练实录 **15 篇**；篇数以 [[Articles-Index]] 为准，本页不复述计数） |
| `ai-links/articles/`（目录约定） | 文章库正文全部存放于此目录（15 篇 + 索引自身）；上表与「另见」中文章类条目的实际路径均为 `ai-links/articles/<名称>.md` |
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
    │       └─ DSH插件发布与分发 (PUBLISH, 2026-09-13)
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
    ├─ 参考-OpenCode-技术调研报告 (OPENCODE, 2026-08-25)
    ├─ 参考-Pi-Agent-技术调研报告 (PI, 2026-08-25)
    └─ AGENTS

## 标签索引

- `#ai/links` — 本子库（链接收藏/综述）
- `#ai/skills` — 技能开发（antigravity/i-have-adhd/pretty-mermaid/diagram-design）
- `#ai/agent` — 编码 Agent（Pi 书/pi-from-scratch/prime-agent/Harness 生态）
- `#ai/learning` — 教程与路线图（copilot-cli/exploreclaudecode/TTFT/system-design）+ 文章库学习类（[[Articles-Index]]：论文精读/上下文工程/Skill/机制拆解/多智能体编排 15 篇）
- `#ai/tools` — DSH 插件/Hook 实践与实测（[[DSH会话脱敏插件缺陷档案]]、[[DSH-TUI插件使用手册]]、[[DSH提效与Token插件调研]]、[[DSH插件发布与分发]]）
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
- [[Articles-Index]] — 文章库子 MOC：可解释性/上下文工程/Skill/机制拆解/多智能体编排 15 篇文章（2026-08-17 迁移；正文位于 `ai-links/articles/`）
- [[SESSION-ARCHIVE-2026-08-18]] — 本子库创建会话归档（16 链接调研 + DSH 4 篇落盘 + 远程合并推送）
- [[SESSION-ARCHIVE-2026-08-30]] — dsh/dsh-tui 升级 + 思考强度控制 + Token 优化归档（DSH-TUI 手册与 Token 调研同步更新）
- [[SESSION-ARCHIVE-2026-09-12]] — DSH 会话日志脱敏（预防 + 修复两个插件）与平台研究：7 篇 DSH 实测笔记的产出会话，含首次推送 CI 37 秒红的记录；**§七 是 2026-09-13 补记的发布与分发**（两包发布、两次版本迭代、守卫体系、收录信号）
- [[DSH插件发布与分发]] — §七 的展开笔记：官方无市场、topic/keyword 双信号、monorepo 收录坎、`files` 白名单、可证伪守卫与供应链核查（2026-09-13 新增）
- 本 vault 其他复盘：[[v2rayn-balancer-复盘-2026-08-09]]、[[2026-07-21-树莓派网络故障与路由器破解完整复盘]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 概述把 05/05 的 3 条并入 08/16 批次，写作「18 条（2026-08-16 收藏 16 + 08-18 追加 2）」 | 改为「05/05 × 3 + 08/16 × 13 = 16，08/18 × 2 = 18」，原表述保留在更正块；依据主文档 §一 与本页「关键数据」行 |
| 纠错 | 状态框「16/16 有效」与同页「链接总数 18」自相矛盾 | 保留原表述并注明计数口径；补三条可执行待复核项（#18 已核对关闭，#1 改名、#15 版本漂移 待 API / star 复核） |
| 纠错 | 文档地图与「另见」把 [[Articles-Index]] 写成 14 篇 | 更正为 15 篇并补第六组「多智能体编排」；篇数改为以 [[Articles-Index]] 单向定义，本页不再复述计数 |
| 补疏漏 | 文档地图只有 [[Articles-Index]] 一行，未登记 `articles/` 目录层 | 增补 `ai-links/articles/` 目录约定行，说明文章类条目的实际路径 |
| 补疏漏 | 子领域定位五项未随 2026-08-18 追加更新 | 补「AI 应用层（Open-Magiviz）与 Agent Harness 课程（Vercel Academy）」两项 |
| 补疏漏 | 「文档关系图」缩进文字树落后于同页「文档地图」：2026-08-25 登记的 `参考-OpenCode-技术调研报告`、`参考-Pi-Agent-技术调研报告` 未进树 | 已把 2 个节点补入文字树（节点名取库内真实 basename）；补入后树覆盖文档地图的全部 18 篇（地图另一行 `ai-links/articles/` 是目录约定，非文档），树另含地图未列的 `参考-Ark-Agent-Plan计费与配置` 与 `AGENTS` |
| 纠错 | 外部审计把「本簇没有 Excalidraw 关系图」记为缺覆盖 | 不成立：[[AGENTS]] 第十一节「文档关系图 \| 文字树/表格 (MOC 中)」本就是本簇的口径，且 `AI-Links-关系图.excalidraw.md` 在全库零引用；已按「不产出」在 [[ARROW-CHECKLIST]] §9 销项 |

> 回链：本页已在页首 See also 链出 [[AGENTS]]、在标签索引链出 [[CORRECTIONS]]，不重复添加。
