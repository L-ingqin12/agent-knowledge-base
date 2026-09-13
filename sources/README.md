---
title: 来源登记索引（sources/）
aliases: [sources-README, 来源登记索引, Sources Index]
tags: [moc, meta, reference, source]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 来源登记索引 — `sources/`

See also: [[URL-Lookup]] | [[URL-REGISTRY]] | [[HOME]] | [[AGENTS]]

> [!abstract] 本目录是什么
> 存放**带内联字段的来源条目**，供 [[URL-Lookup]] 的 Dataview 查询检索。
> 每页对应一个主题；条目必须是**列表项**（Dataview 无法查询表格行）。

## 三层结构

| 层 | 文件 | 角色 | 依赖插件 |
|---|---|---|---|
| 入口 | [[URL-REGISTRY]] | 人工可读的登记册（分区表格） | 不依赖 |
| 检索 | [[URL-Lookup]] | 按「何时使用」动态筛出条目 | Dataview |
| 数据 | `sources/*.md`（本目录） | 条目的实际存放处 | 不依赖 |

## 主题页

| 主题页 | 覆盖范围 | 条目数 |
|---|---|---|
| [[sources/dep-cve\|dep-cve]] | 依赖与 CVE：发行版 tracker、官方公告、包元数据 | 37 |
| [[sources/dsh-routing\|dsh-routing]] | DSH 与模型路由：上游 API 文档、本机配置、模型切换调研 | 29 |
| [[sources/proxy-relay\|proxy-relay]] | 代理与中继：现役/退役资产、事故复盘 | 31 |
| [[sources/network-device\|network-device]] | 网络与设备：路由器、代理分层、复盘 | 37 |
| [[sources/security-audit\|security-audit]] | 安全审计：本次产出、标准、可复用方法 | 20 |
| [[sources/learning-notes\|learning-notes]] | 学习与调研：已有索引入口 + 官方文档 | 263 |

**合计 417 条**（2026-09-13 按各页 `- 来源::` 实际清点的快照：37 / 29 / 31 / 37 / 20 / 263；并发簇仍在追加，后续以重新清点为准；字段齐备口径为**六字段**：`来源` / `use_when` / `url` / `answers` / `authority` / `verified`）

> [!warning] 更正（2026-09-13）：本行原写「链路已校验：每条 `url` / `use_when` / `answers` / `verified` **四字段**齐全」（原表述）——与下方「条目协议」的六字段、以及 [[URL-Lookup]] 的「六个字段齐全」自相矛盾，属笔误（复核逐页统计六页：来源/url/use_when/answers/authority/verified 各 12/12/11/13/12/11，71 条全部六字段齐备）。已改为六字段；同时把「链路已校验」的口径更正为**字段齐备**——本页与 `sources/*.md` 只保证字段存在，**不做 URL 可达性校验**（可达性由 `scripts/check-links.py` 巡检，它跟随重定向、只记最终状态码，故 help.obsidian.md 这类迁移型失效不会被报出）。

## 条目协议

```markdown
- 来源:: <名称>
  use_when:: <何时用 —— 这是检索主键>
  url:: <链接或 wikilink://名称>
  answers:: <能回答什么>
  authority:: 高 | 中 | 低
  verified:: YYYY-MM-DD
```

| 字段 | 约束 |
|---|---|
| `use_when` | **检索主键**。写「什么时候需要它」，不是「它是什么」 |
| `url` | 外部用真实 URL；本库内部文档用 `wikilink://文档名`；本机文件用 `file:///` |
| `authority` | 高=官方/原始来源；中=知名聚合；低=二手转载 |
| `verified` | **必填**。无核实日期的条目视为不可信（[[URL-Lookup]] 有过期复核查询） |

## 维护

| 动作 | 做法 |
|---|---|
| 新增来源 | 在对应主题页追加列表项，六字段齐全 |
| 批量补录 | 运行 `scripts/url-registry-mine.py --out-dir _out`，人工确认后并入 |
| 停用来源 | 标注 `status:: retired`，不建议直接删除 |
| 更新结论 | 同步改 `verified::` **并**更新 [[URL-REGISTRY]] 对应表格行 |

> [!warning] 两条纪律
> 1. **`verified` 必填**——URL 会失效、结论会过期
> 2. **漏洞判定必须成对读取**「受影响范围」与「修复版本」——详见 [[URL-REGISTRY#1-依赖与-cve]]

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-12 | 建目录；6 个主题页共 71 条条目；建立与 [[URL-REGISTRY]] / [[URL-Lookup]] 的三层结构 |
| 2026-09-13 | A1 簇（DSH 插件生态）回写：`dep-cve` +8（npm 包元数据 / dist-tags / 受限包查询 / GitHub 搜索 API / 目录站计数与收录标准 / npm search 语义 / keyword 入口）、`dsh-routing` +5（官方 README / 文档站 / session-format-status / capability-seams / apps-cli）；合计 84 |
| 2026-09-13 | B6 簇（agent-learn / mcp-learn）回写：`learning-notes` +11（新增「B6 复核新增」节：oh-my-openagent 上游 / oh-my-opencode npm 元数据 / jsDelivr 清单接口 / agent-learn 上游 / MCP 规范 2026-07-28 三条 / MCP 官方构建教程 / MCP SDK v2 更新与迁移 / Anthropic 多 Agent 博文）、`dep-cve` +1（PyPI 包元数据：`mcp` 2.x 与 `<2` 上界）；条目数一并按当日实际清点刷新（合计 121） |
| 2026-09-13 | B2 簇（Prompt / Function Calling / 上下文工程）回写：`learning-notes` +9（新增「B2 复核新增」节：Anthropic 上下文工程 / Chroma Context Rot / Simon Willison 失效模式 / Addy Osmani 两篇原文 / Claude Code CHANGELOG 与 Release API / Claude Code 官方 scheduled-tasks 与 goal / openai-python 类型规格 / 推理技法论文三篇 / 智谱 GLM 官方模型文档）；条目数按各页实际清点刷新（快照合计见上表） |
| 2026-09-13 | B1 簇（LLM 理论笔记与推理工程数值纠错）回写：`learning-notes` +11（新增「B1 复核新增」节：PyTorch SiLU / RMSNorm、torchtitan 与 zubnet 的 SwiGLU 8d/3、EleutherAI RoPE、vLLM Engine Arguments 与 Automatic Prefix Caching 现路径、vLLM config/parallel.py、vLLM 论坛 gpu_memory_utilization 帖、Ollama envconfig、vLLM 官方博客）；条目数按各页实际清点刷新（合计 173） |
| 2026-09-13 | A3 簇（claude-ops 架构模式与无人值守）回写：`learning-notes` +15（新增「A3 复核新增」节：Claude Code 官方文档 memory / hooks / skills / context-window / permissions / permission-modes / sessions / scheduled-tasks / commands / sub-agents / agent-view / agent-teams / cross-session-messaging / errors / changelog）、`dsh-routing` +1（DeepSeek 上下文硬盘缓存发布公告 news0802：64 token 存储单位与 best-effort 口径）、`security-audit` +3（GitHub OAuth scopes 的 workflow scope、Actions 触发事件的 scheduled workflow 60 天自动禁用、REST Git Data API trees 端点——该页正文未取到，登记待回查）；条目数按各页实际清点刷新（合计 221） |
| 2026-09-13 | C2 簇（cs-base 基础学科）回写：`learning-notes` +27（新增「C2 复核新增」节：libstdc++/libc++/MSVC 容器实现源码、ml-engineering 与 YaRN、ALiBi 检索、MongoDB journaling/聚合内存/版本线/重试写/事务生产考量、Kafka 4.0 release notes 与 KIP-848/405/320、TopicConfig/ConsumerConfig/BuiltInPartitioner、hnswlib 与 pgvector）；条目数按各页实际清点刷新（learning-notes 197、合计 287） |
| 2026-09-13 | C9 簇（`diagrams/` 与图表规范）回写：`learning-notes` +3（新增「C9 复核新增」节：Annotated Transformer / Excalidraw `types.ts` 绑定类型 / obsidian-excalidraw-plugin 2.25.3）；该簇同时回写 `diagrams/ARROW-CHECKLIST.md` 与 [[AGENTS]] 第十一节，未新增其他主题页条目 |
| 2026-09-13 | C4 簇（claude-ops 事故复盘）回写：`network-device` +6（微软存档博客的覆盖图标 15 上限 / Windows 错误码 1052 / nf_conntrack sysctl / ip-sysctl / man 7 tcp / systemd resolved.conf）、`proxy-relay` +5（undici `Client` / Python `http.server` / coreutils `timeout` / Node `http` 文档 / nodejs 提交 f2dc7c84d6）、`dsh-routing` +3（DeepSeek `kv_cache` 与 `anthropic_api`、Claude prompt caching）、`dep-cve` +5（`patch(1)` / `py_compile` / npm 2.1.177 与 2.1.174 元数据 / GitHub 仓库重命名重定向）、`learning-notes` +1（Claude Code settings 优先级）；本次 +20 条，合计待并发簇结束后统一清点 |
| 2026-09-13 | C5 簇（claude-ops 方案与设计 / hermes，21 篇）回写：`learning-notes` +5（新增「C5 复核新增」节：Claude Code CLI reference / claude-code-action v1.0 `action.yml` 与迁移指南 / 本库上游仓库现名 `agent-knowledge-base` / Hermes Agent Kanban dispatcher issue+PR）、`dep-cve` +3（新增「C5 复核新增」节：Node.js CLI 文档的 `--http-parser` 已移除、Python `select` 写集合语义、Python `socketserver` 的 `allow_reuse_address`）；条目数按各页实际清点刷新（快照合计 338） |
| 2026-09-13 | C3 簇（network 子库，16 篇）回写：`proxy-relay` +10（新增「C3 复核新增」节：Xray 路由文档 / Xray 出站文档的 Mux 定位与 `xudpProxyUDP443` / observatory 文档 / Xray-core `default.go` / 提交 `4f601530` / Xray-core Releases API（含预发布口径）/ v2rayN Releases API（版本配对）/ PR #8849 / `ConfigHandler.cs` / gfpcom 免费代理清单）、`network-device` +13（miuirom 固件页 / OpenWrt TOH / OpenWrt 无线文档 / ramips DTS / LKML mt7603 补丁 / qc-drivers 设备清单 / OpenSSH 8.8 / `ssh(1)` / `resolv.conf(5)` / frp Releases / 已 404 的 `netsh int tcp` / Windows TCP/IP 已知问题 / RFC 8325）、`dep-cve` +2（NVD CVE API 2.0 的 primary/secondary 双评分、MITRE CVE Services）；条目数按各页实际清点刷新（快照合计 363） |
| 2026-09-13 | C7 簇（ai-links 旧文档与 articles/ 文章收藏，10 篇）回写：`learning-notes` +21（新增「C7 复核新增」节：agentic-awesome-skills 改名证据 / diagram-design README / Prime Agent 论文解读页 / watermarks-remover 媒体出处 / learn-from-claudecode「07. Retry & Resilience」/ 张汉东《驾驭工程》ch06b / Claude 定价与缓存换算 / 6551Team error-recovery / Claude Code 源码社区文档站 telemetry / 官方 costs 页 / lhl agentic-memory 分析 / 小林coding cc_memory canonical / Gemma Scope 2 报道 / TransformerLens 文档站 / SAE-for-VLM 官方页 / ICLR PatchSAE proceedings / DeepStack 项目页 / CaFE 待回查证据 / agentpatterns Lost-in-the-Middle / 澎湃 Context Rot 转述 / Liu et al. 与 RULER 编号；另扩充既有「Anthropic 开源电路追踪工具公告」条目的 answers）；条目数按各页实际清点重算（33 / 28 / 29 / 35 / 18 / 242，快照合计 385） |
| 2026-09-13 | C6 簇（claude-ops 计划 / 架构模式 / 日志分析，17 篇）回写：`learning-notes` +21（新增「C6 复核新增」节：Claude Code hooks 与 hooks-guide、tools-reference、issue #17208 / #27483、OpenCode 官方 agents 文档与 issue #19999 / PR #20152、feanor5555/opencode-agent-intercom、Python concurrent.futures、Tornado IOLoop、FastAPI 手动部署、gunicorn.org、opencode-multi-agent-system 仓库 API 与 orchestrator.md、pi.dev 文档站与 SDK、Pi README、badlogic/pi-mono 重定向证据、earendil-works/pi canonical、GNU xargs 手册）、`dep-cve` +4（新增「C6 复核新增」节：`@anthropic-ai/claude-code` latest = 2.1.270、`@earendil-works/pi-coding-agent` latest = 0.85.1、旧作用域 `@mariozechner/pi-coding-agent` 0.73.1 deprecated、Claude Code sub-agents 的并发 20 / 嵌套深度 / 15,000 token 告警）、`proxy-relay` +2（nginx for Windows 文档、Maxim Dounin 的 poll/WSAPoll 邮件列表）、`network-device` +2（KB 929851 动态端口默认 49152-65535、TCP Chimney Offload 已废弃）、`security-audit` +2（GitHub 移除敏感数据官方文档、git-filter-branch 手册）、`dsh-routing` +1（DeepSeek 官方价目表：flash / v4-pro 的 hit-miss 与空闲-峰值）。条目数按各页实际清点刷新（37 / 29 / 31 / 37 / 20 / 263，快照合计 417） |

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 条目数快照行写「链路已校验：每条 `url` / `use_when` / `answers` / `verified` **四字段**齐全」，与同页「条目协议」（六字段）及 [[URL-Lookup]] 的「六个字段齐全」自相矛盾 | 已改为六字段（`来源` / `use_when` / `url` / `answers` / `authority` / `verified`）；复核逐页统计六页 71 条六字段全部齐备，确认「四字段」为笔误；原表述保留在 `[!warning] 更正` 内 |
| 纠错 | 「链路已校验」易被读成「链接都可用」 | 口径改为**字段齐备**：不做可达性校验，可达性由 `scripts/check-links.py` 巡检；并注明巡检跟随重定向、只记最终状态码，故 `help.obsidian.md` 这类上游迁移型失效不会被报出 |
| 加厚 | 图表规范（[[AGENTS]] 第十一节）此前没有任何外部来源条目 | 登记「C9 复核新增」3 条并在正文加引用块（Annotated Transformer / Excalidraw `types.ts` / obsidian-excalidraw-plugin 2.25.3）；依据 2026-09-13 实测 HTTP 200 |
| 加厚 | 条目数快照行停留在 C2 簇清点的 287，与并发回写后的实际条目数不符 | C5 簇回写后重新清点六页 `- 来源::`（31 / 28 / 19 / 22 / 17 / 221），快照合计刷新为 **338**（2026-09-13 19:58）；本页 `updated` 保持 2026-09-13 |
| 加厚 | C3 簇新增的 25 条上游来源未计入快照（表内为 C5 的 338） | 重新清点六页 `- 来源::`（33 / 28 / 29 / 35 / 17 / 221），快照合计刷新为 **363**（2026-09-13 20:0x，C3 清点）；并说明 `proxy-relay` 的 Xray-core Releases API 条目与 C8 节 `/releases/latest` 条目是**两个不同端点**，二者不矛盾（前者含预发布） |
| 加厚 | 快照 363 未包含 C7 簇新登记的 21 条，`security-audit` 亦已增至 18 | C7 簇回写后重新清点六页 `- 来源::`（33 / 28 / 29 / 35 / 18 / 242），快照合计刷新为 **385**（2026-09-13 20:1x）；`learning-notes` 的增量全部落在「C7 复核新增」节，格式为六字段条目 |
| 加厚 | 快照 385 未包含 C6 簇新登记的 32 条 | C6 簇回写后重新清点六页 `- 来源::`（37 / 29 / 31 / 37 / 20 / 263），快照合计刷新为 **417**（2026-09-13）；本簇增量全部落在各页「C6 复核新增」节，格式为六字段条目 |

条目数（当时快照合计 287）经复核独立重算成立，无需修改；C5 簇回写后已按最新清点刷新为 **338**（见表与变更记录）。见 [[CORRECTIONS]]（[[AGENTS]] 见页首）。C9 簇另在 `learning-notes` 追加 3 条（累计 +3），最终合计以本轮全部并发回写结束后重新清点为准。
