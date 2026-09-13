---
title: SESSION-ARCHIVE-2026-08-25
aliases: [2026-08-25 会话归档]
tags: [meta]
created: 2026-08-25
updated: 2026-09-13
status: review
---

# 会话归档 — 2026-08-25 全库审计与 AI 大模型专题建设

> 本会话完成三件事：①[[AI大模型开发]] 主文件补全与勘误；②按西瓜老师课程大纲新建 `ai-dev/` 子库（13 篇实战文档 + MOC + 9 张 Excalidraw 图）；③五路子库审计修复（ai-links / network / claude-ops×3 / 根目录）。规范变更见 [[AGENTS]]。

## 一、主文件：AI大模型开发.md

| 类别 | 内容 |
|---|---|
| 勘误 | GPT 表格版本对应关系、Causal Decoder 拼写、标题层级；√d_k 方差论证标注；Multi-Head 各头独立 Wq/Wk/Wv 展开 |
| 补全 | Word2Vec+梯度下降完整 PyTorch Demo；Completion vs Chat API 完整章节（roles/base_url/curl/参数表/流式/陷阱）；`## 课程知识地图`（38 讲课程 → 文档映射） |
| 图表 | 过时 mermaid 引用替换为 Excalidraw 指针；删除重复空标题 |
| 入口 | `> 入口 MOC: [[AI-Dev-KB-Home]]` |

## 二、ai-dev/ 子库新建（13 篇 + MOC）

全部文档：frontmatter 规范、零 mermaid、≥3 出链（必含 [[AI大模型开发]] 与 [[AI-Dev-KB-Home]]）、参考资料 URL 节、web_search 交叉验证。

| 文档 | 要点 | 配图 |
|---|---|---|
| [[Prompt-Engineering入门与Demo]] | CoT/Few-shot/LtM，9 轮检索验证 | Prompt-Engineering-LtM-Flow |
| [[Function-Calling工具调用实战]] | tools schema/tool_calls/执行器循环 | Function-Calling-Sequence |
| [[RAG检索增强生成实战]] | Naive→Advanced 演进 + FAISS Demo | RAG-Pipeline |
| [[GraphRAG知识图谱增强实战]] | Leiden 社区/Local vs Global Search | GraphRAG-Flow |
| [[LLM-Agent开发基础]] | 手写 ReAct 循环 + 失效模式表 | ReAct-Agent-Loop |
| [[MCP协议开发实战]] | FastMCP Server/Client 双向 Demo | MCP-Architecture |
| [[A2A多智能体协作协议]] | Agent Card/Task 生命周期 | — |
| [[LangChain-LangGraph框架实战]] | LCEL/LangGraph State·Checkpointer·Supervisor | Multi-Agent-Supervisor |
| [[LLM推理部署与量化]] | Ollama/vLLM/Ray 三路线，16 次检索验证（QLoRA 65B 勘误） | Training-vs-Inference（复用） |
| [[LoRA参数高效微调实战]] | 低秩旁路原理 + Llama-Factory 实操 | LoRA-Principle |
| [[强化学习对齐-RLHF到GRPO]] | PPO/DPO/GRPO 谱系 | RLHF-GRPO-Pipeline |
| [[微调数据工程与模型蒸馏]] | SFT/COT/偏好数据 + R1 式蒸馏 | Training-vs-Inference（复用） |
| [[Agent-Skills技能开发实战]] | 课程第13章补齐：SKILL.md 规范/渐进式披露/最小技能 Demo | — |
| [[多模态Agent平台实战]] | 课程第21章补齐：四层架构/延迟预算/TEN·Dify 选型/VLM Demo | — |

入口：[[AI-Dev-KB-Home]]（文档地图/学习路径/项目地图/图表索引/标签索引）。

## 三、diagrams/ 新增 9 张 Excalidraw

`Function-Calling-Sequence`(21el)、`ReAct-Agent-Loop`(18)、`Prompt-Engineering-LtM-Flow`(23)、`RAG-Pipeline`(44)、`GraphRAG-Flow`(36)、`MCP-Architecture`(22)、`Multi-Agent-Supervisor`(28)、`LoRA-Principle`(30)、`RLHF-GRPO-Pipeline`(20)。
验证方式：pwsh 提取 ```json 块 ConvertFrom-Json 全部通过；箭头 start/endBinding 与矩形 boundElements 双向互引核对。格式遵循 [[ARROW-CHECKLIST]] 与 [[AGENTS]] 第十一节。

## 四、审计与修复（五路执行代理）

| 子库 | 执行摘要 | 修改点 |
|---|---|---|
| ai-links/ | source_url→source_urls 批量、PatchSAE 577→576+1、Kimi-K3 数字、幽灵链接清理、自链修正 | 20 文件 / 53 处 |
| network/ | 延迟基准统一 541→113(-79%)、TX Power 14vs18 勘误、8 处脚本路径补 scripts\、Mux 致障勘误 callout、uci 不可用警告、信号 82/86/88 口径注、MOC 地图补 2 行 | 14 文件 / 73 处 |
| 根目录 参考-* | VPN 三组数字矛盾统一、Ark「重度3天」首日超限修正、小米 login 移出 stok 表、树莓派复盘 ping 口径/danger 备份注、See also 全部移至 H1 后、SESSION-ARCHIVE-2026-08-18 出入链修复 | 14 文件 / 约 70 处 |
| claude-ops/事故复盘+Agent-架构模式 | hermes 80min→~110min 时间线、ping 口径澄清、opencode Python→TypeScript(+Go TUI)、nginx select 1024/单 worker、逃生通道级别统一、状态机补 ESCALATE 终态（附待确认 callout）、cron hosts 追加缺陷修正、HTTP/2 根因叙述纠正、死链按 MEMORY-INDEX 重定向修复 | 11 文件 / 28 处 |
| claude-ops/运维方案与设计 | 锚点工具 9/10 统一、sysctl PRoot 不可用 warning、fail-open 超时语义、claude-haiku-4-5→deepseek-chat 映射注、reusePort 正确实现、cache-proxy-evaluation 转 deprecated | 19 文件 / 76 处 |

死链专项：Plans 内 `hermes-parallel-task-communication` 等历史死链全部改为真实文件名或加失效注记。

## 五、规范演进（AGENTS.md）

- ⛔ **全局铁律**：一切委派必须使用 ox-alpha 模型，禁止路由 deepseek 系列其他模型（文首 danger 块 + 行为约束第 9 条）
- **Python 环境**：全局解释器固定 `D:\ProgramData\miniconda3\python.exe`（行为约束第 10 条）
- Mermaid 矛盾澄清（"禁止"为准，MOC 关系图用文字树/表格）；目录树重写；统计口径 170+/500+；注册 #ai/tools、#network/moc 等

## 六、终检结果

| 检查项 | 结果 |
|---|---|
| 全库 wikilink 解析（含 .excalidraw 嵌入） | ✅ 0 死链 |
| 全库 ```mermaid 代码块 | ✅ 0 处 |
| 新建文档 frontmatter（title/tags/created/updated/status） | ✅ 全合规 |
| Excalidraw JSON 解析 | ✅ 9/9 通过 |
| Python Demo 语法（py_compile 批量） | ✅ 45/45 通过 |

## 七、遗留事项（未解决）

1. **Demo 运行级验证未做**：全局 miniconda 未装 torch/faiss/networkx/sentence-transformers；语法已验证（45/45），装依赖后建议跑一遍（解释器路径见 [[AGENTS]] 行为约束第 10 条）
2. ~~vllm bench serve 版本、ZeRO 倍数~~ ✅ 已按公开资料核实补充（PR #13993/#18566；ZeRO 论文 400B 实测口径）
   > [!note] 2026-09-13 复核回标：PR #13993 经 GitHub API 实测为「[Feature] Add `vllm bench` CLI」（作者 randyjhc，state closed、merged=true，changed_files=8 / additions=1274），与本项核对动作逐项对得上；PR #18566 本次未复核（复核时遇 403 限流），保留编号时建议同时附 PR 标题以便人工核对。
   > 来源：https://api.github.com/repos/vllm-project/vllm/pulls/13993
3. ~~CVE-2020-14100 待核~~ ✅ NVD 描述确认 <1.0.66 受影响，修复版本即 1.0.66
   > [!note] 2026-09-13 复核回标：结论成立——第三方库 #VU46722（cybersecurity-help）实测 200，记为小米路由器 R3600 `set_WAN6` 命令注入（CWE-77）、缓解措施「update to 1.0.66」，与库内 [[参考-小米路由器API认证与利用]] 同口径（影响 < 1.0.66、修复 1.0.66）。附注：该编号在 OSV API 实测 404，这类 CNA 直发编号只能回 NVD / 第三方库 / 厂商公告核对。
   > 来源：https://www.cybersecurity-help.cz/vdb/vulns/46722/
4. **课 29 Janus 统一多模态** ✅ 已补全独立章节（解耦视觉编码 + GenEval/MMBench 成绩）
5. 主文件 `> 入口 MOC:` 与 `## Related` 间约 10 个空行（Obsidian 渲染无影响）
6. 沙箱限制备忘：pwsh 无法修改既有库文件（Access Denied），一律用 read/edit 工具；新文件创建可用 pwsh
   > [!note] 2026-09-13 复核回标：该条是**会话级环境备忘而非库属性**——复核会话的文件策略为 danger-full-access，复核员已用 pwsh 在库内 `_out/` 完成写入与删除探测，限制不成立。后续会话执行前请先用一条无害读写探测确认当前策略，勿把本条当现行约束。
7. 仍待验证（课程专属/需实机，公开资料无法覆盖）：labeler 与 llamabooster 产品形态、中文 token 压缩比官方口径、TYPORA 全新机器端到端
8. **推送待执行**：本地已领先 origin/main 三个提交（4edd7ef / ce7c593 / 本归档提交），沙箱内凭据管理器被拦无法认证。请在你的终端执行：
   ```powershell
   cd D:\Document\local\knowledge
   git -c http.proxy=http://127.0.0.1:10808 push origin main
   ```
   （直连可达时可省 proxy 参数）
   > [!note] 2026-09-13 复核回标：`4edd7ef` / `ce7c593` 在当前仓库（94 个提交，2026-09-12 从公开远端克隆）实测均不存在；该遗留项已由 [[SESSION-ARCHIVE-2026-08-26]] §六闭环——v4 `a518edf..fadb1f4` 与 v5/v6 推送完成。原历史判断保留，仅追加此回标。

## 十、同日追加会话：OpenCode/Pi 基座研究与日志分析多Agent架构设计

> 第二会话（同日晚）。主题：OpenCode 扩展机制知识补全、主↔子 agent 实时交互方案、基座开发七维度选型、日志网络根因分析多Agent架构。

### 产出（6 新文档）

| 文档 | 要点 |
|---|---|
| [[参考-OpenCode-技术调研报告]] | Agent双mode/task委派与四大缺口(异步#5887/嵌套#9280/并行#29638/resume#6584)、plugin五hook+event Bus、自定义tool(zod)、SKILL渐进披露、MCP local/remote、opencode.json permission last-match、**serve REST+/event SSE+abort**（GitLab orbit/Onyx 生产佐证）、v1.18.23/MIT |
| [[参考-Pi-Agent-技术调研报告]] | badlogic→Earendil 迁移史、库优先 createAgentSession 三层API、**steer()/followUp() 双队列**、AbortSignal/interrupt、树状JSONL、无内核MCP、默认无权限、Windows坑、0.x破坏性变更+npm作用域迁移风险 |
| [[main-subagent-realtime-interaction]] | 实时交互四原语（感知/邮箱/打断/恢复）、四层活性金字塔与判定矩阵、T0..T3升级阶梯（Pi steer=T1.5当轮注入）、mailbox协议、checkpoint模板 |
| [[opencode-pi-base-development-analysis]] | 双层基座推荐（OpenCode交互基座+Sidecar外挂，Pi嵌入备选）；manifest入上下文+secure_read明文治理；关键字短路两级；会话池/cache亲和/背压；跨平台矩阵；Phase 0-4路线图；ADR D1-D6 |
| [[lognet-rootcause-multiagent-architecture]] | LogNet图模型(SQLite+FTS5)+时钟域对齐；从问题节点frontier评分渐进展开；符号化工具链(addr2line/llvm-symbolizer批处理+build-id匹配+**artget适配器**)；多包并发流水线；容量估算与PoC假设清单；M0-M4路线 |
| [[agent-memory-context-knowledge-design]] | 记忆三级模型(L1窗口/L2checkpoint/L3知识库)；上下文五源装配+前缀稳定排序(缓存亲和)；外部知识库化四形态(规则/事实/方法论/案例)+写入三闸门与混合检索；直接复用本库 AGENTS 协议为产品内知识库规范 |

### 关联修改

- MOC 挂载：[[AI-Links-KB-Home]] 文档地图 +2 调研报告行；[[Claude-Ops-KB-Home]] ARCH 表 +4 行（review ×4）；[[MEMORY-INDEX]] 新增节 4 条
- 反向链接补齐：opencode-multi-agent-architecture / fan-out-subagent-pattern / state-machine-quality-gate-loop / pi-agent-framework-knowledge / log-analysis-agent-windows-architecture 的 See also
- 调研方式：两路后台子代理多轮 web_search 交叉验证（ox-alpha 继承，未传 model 覆盖）

### 本会话遗留

1. 两份调研报告各含 6-8 处「待确认」（org 归属、explore agent、MCP 分隔符、allowed-tools 执行、zod 细节等），后续可实机核验
2. artget 为内部工具，接入设计按"制品拉取"口径完成（用户确认），实际 CLI 参数待对齐
3. Doc C/D 的 Phase/M 路线图为设计稿，未启动实施

> [!success] 残余复核（2026-09-13）：**遗留 1「两份调研报告各含 6-8 处待确认，后续可实机核验」已闭环** —— 实机核验当时已完成（见 [[SESSION-ARCHIVE-2026-08-26]] §一：npm 包 `.d.ts` 逐条比对 + 平台二进制字符串取证），本轮再补开放网络复核，逐项定论如下。
> - [[参考-OpenCode-技术调研报告]]：① org 归属 = `anomalyco/opencode`（`sst/opencode` 为 301 重定向）✅；② 内置 `explore` agent ✅；③ `top_p` 支持 ✅；⑤ MCP timeout ✅；⑥ 无 `linter` 键、`doom` 实为 `doom_loop` ✅。
>   - **④ skill 的 `allowed-tools` 是否被执行 → 源码级定论：不被解析、不被执行。** 依据（`dev` 分支）：`packages/schema/src/skill.ts` 的 `SkillV2.Info` 只有 `name/description/slash/location/content`；`packages/opencode/src/skill/discovery.ts`、`packages/core/src/skill/discovery.ts`、`packages/opencode/src/skill/index.ts`、`packages/core/src/skill.ts` **均无 `allowed` 字段与工具白名单逻辑** ⇒ 该字段即使写进 frontmatter 也进不了运行时，与「二进制未见执行逻辑」的取证一致。该键名只是沿用 Anthropic Agent Skills 规范的写法，**OpenCode 侧忽略它**。
>   - **⑤ 的 MCP 分隔符源码级确认 → 已定论：单下划线 `<server>_<tool>`。** 依据：`packages/opencode/src/mcp/catalog.ts` L119 `toolName = (clientName, name) => sanitize(clientName) + "_" + sanitize(name)`，且 `sanitize = v => v.replace(/[^a-zA-Z0-9_-]/g, "_")`；`mcp__` 双下划线形态**不存在**于该实现。此写法亦解释了上游 `sverklo_sverklo_*` 双重前缀缺陷（服务器名自带前缀时重复）。
> - [[参考-Pi-Agent-技术调研报告]]：② TypeBox ✅；⑤ 九件套工具 ✅；⑥ MIT ✅；⑦ star 数约 104,522（2026-09-13）✅。
>   - **③ web-ui/slack/pods 存续 → 已解决：均不存在。** `main` 分支 `packages/` 现为 11 个包（agent/ai/chord/client/coding-agent/evals/protocol/server/session-backends/telemetry/tui），无 `web-ui`/`slack`/`pods`。
>   - **④ 四种运行形态官方命名 → 已解决。** `packages/coding-agent/src/modes/index.ts` 是权威清单：`InteractiveMode` / `runPrintMode` / `runRpcMode`（另导出 `json-event` 事件流类型）⇒ **interactive / print / rpc + JSON 事件流**，与「四种使用姿势」一一对应。
>   - **⑧ MCP 是否官方一等支持 → 已解决：无。** `main` 分支全仓库 **1713 个 blob 中路径含 `mcp` 的为 0**，即连 MCP 相关包/目录都不存在（社区扩展路线不变）。
> - **① 产品名 "LiblibPi" → 本轮已定论：该名称不存在，全库统一用 "pi / Pi coding agent"。** 依据（2026-09-13 取回）：GitHub 仓库检索 `LiblibPi` **total_count = 0**；npm registry `https://registry.npmjs.org/liblibpi` **HTTP 404**；公开检索亦无该名（命中项全是 libGDX 作者 Mario Zechner 的 Pi）。「LiblibPi」最可能是 libGDX 与 Pi 的记忆混淆（此句为推断，非取证结论）。取回：<https://api.github.com/search/repositories?q=LiblibPi>、<https://registry.npmjs.org/liblibpi>。
> - 范围说明：以上取自上游 `dev`/`main` 分支与 npm registry 的**当日快照**；报告正文内的「待确认」标记属其归属复核范围，本条只记结论与依据、不改报告正文。
> 来源：<https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/mcp/catalog.ts>、<https://github.com/anomalyco/opencode/blob/dev/packages/schema/src/skill.ts>、<https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/modes/index.ts>

> 相关：[[Network-KB-Home]] · [[Claude-Ops-KB-Home]] · [[AI-Links-KB-Home]] · [[TYPORA-KB-Home]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 加厚 | 遗留项 2 只留 PR 编号（#13993 / #18566），无标题与状态 | 复核 PR #13993 实测为「[Feature] Add `vllm bench` CLI」（randyjhc，merged=true，8 文件 +1274 行），与本项核对动作对得上；#18566 本次未复核（403 限流），保留编号时附标题 |
| 加厚 | 遗留项 3 只写「NVD 描述确认」，无外部锚点 | 第三方库 #VU46722 与库内 [[参考-小米路由器API认证与利用]] 同口径（R3600 `set_WAN6` 命令注入，修复 1.0.66）均成立；附注该编号 OSV API 实测 404，CNA 直发编号须回 NVD / 第三方库 / 厂商公告 |
| 纠错 | 遗留项 6「沙箱限制备忘」被后续会话当作现行约束 | 该条属会话级环境备忘：复核会话策略为 danger-full-access，已用 pwsh 在库内 `_out/` 完成写入与删除探测；执行前先用无害读写探测 |
| 纠错 | 遗留项 8「本地已领先 origin/main 三个提交（4edd7ef / ce7c593）」 | 两个哈希在当前仓库（94 个提交，2026-09-12 克隆）实测不存在；已由 [[SESSION-ARCHIVE-2026-08-26]] §六闭环（v4 `a518edf..fadb1f4` 与 v5/v6 推送完成） |
| 排除 | §十.本会话遗留 1「两份调研报告各含 6-8 处待确认，后续可实机核验」 | 核验已完成（[[SESSION-ARCHIVE-2026-08-26]] §一）+ 本轮补充网络复核：OpenCode ④ `allowed-tools` **不被解析/执行**（skill schema 与 4 处 loader 均无该字段）、⑤ MCP 分隔符 = `sanitize(server) + "_" + sanitize(tool)`（`mcp/catalog.ts` L119）；Pi ③ `web-ui`/`slack`/`pods` 不存在、④ 模式命名 = interactive/print/rpc(+JSON 事件流)、⑧ 全仓 0 个 mcp 路径。Pi「LiblibPi」名称经 GitHub 仓库检索（total_count=0）+ npm registry（404）确证不存在，全库统一用 pi / Pi coding agent 口径 |

相关：[[CORRECTIONS]]
