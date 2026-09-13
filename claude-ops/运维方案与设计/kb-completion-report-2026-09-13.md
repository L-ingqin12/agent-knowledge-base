---
title: 知识库补完报告 2026-09-13
aliases: [KB Completion Report, 补完报告 2026-09-13, kb-completion]
tags: [meta, ai/ops]
created: 2026-09-13
updated: 2026-09-13
status: review
---

# 知识库补完报告 — 2026-09-13

See also: [[AGENTS]] | [[HOME]] | [[CORRECTIONS]] | [[URL-REGISTRY]] | [[URL-Lookup]] | [[Claude-Ops-KB-Home]]

> [!abstract] 本次任务
> 用户要求：**读取知识库并对其中的内容进行调研补完**，随后扩展为「原有的知识归档也有部分存在问题或疏漏或内容描述过于简略，补完」，并要求 fan out subagents。
> 做法：先立校验基线 → 20 簇 fan-out 审计（联网核实）→ 独立复核证伪 → 20 簇并行回写（共享文件加锁）→ 校验器 + 外链巡检验收。
> 结论：**三类问题共处理 522 处**（纠错 164 / 补疏漏 186 / 加厚过简 172），另有 161 处经核验确认原本正确、96 处如实标为「无法核实」。

## 一、任务边界与基线

| 项 | 值 |
|---|---|
| 库根 | `D:\Document\local\knowledge`（Obsidian vault，git 版本化） |
| 初始规模 | 373 个 .md / 校验 276 篇 / **0 ERROR**（`scripts/validate-kb.py`） |
| 终态规模 | 376 个 .md / 校验 279 篇 / **0 ERROR** |
| 校验判据 | 库自带的 `validate-kb.py`（frontmatter 六键 / 嵌套标签 / 死链 / 禁 Mermaid / 连通性 ≥3） |

> [!success] 先立基线是刻意的
> 该库 [[CORRECTIONS]] C-003 与 C-015 都记着「未经校准的扫描器返回零命中被读成『干净』」。
> 因此先跑一次校验器确认它**看得见目标**（276 篇被检查、非 0），之后它报「通过」才算证据。

## 二、fan-out 编排（四轮，共 78 个 subagent）

| 轮次 | 规模 | 产出 |
|---|---|---|
| A 组审计 | 8 agents（4 簇 × 审计+复核） | 171 条结论 |
| B 组审计 | 16 agents（8 簇） | 234 条结论 |
| C 组审计 | 16 agents（8 簇） | 466 条结论 |
| **返回值截断事故** | — | 三组返回值**各被截在 50,105 字符**，272 万字符输出仅救回 89 条 |
| 重建审计（落盘版） | 38 agents（20 簇） | **796 条审计 → 683 条复核通过** |
| 补齐 A1/C7 复核 | 2 agents | +96 条 |
| 回写 | 20 agents | 217 篇文件 / 1237 处编辑 |

> [!danger] 第一轮三组 78 个 agent 的结论基本丢失（本条值得录入 [[CORRECTIONS]]）
> 工具的返回值在 50 KB 处硬截断，且 spill 落盘文件同样被截断（50104 字节即止，带 `… [truncated: N more characters]` 标记）。
> **「跑了 8 个 agent」不等于「871 条结论到手」**——我一度按返回值里的计数汇报，实际到手只有 89 条。
> 修法：第二轮改为**结论写磁盘、返回值只回紧凑摘要**（每报告 < 5 KB），才彻底绕开天花板。

## 三、三类改动（复核通过 779 条，去重涉及 163 篇文档）

| 类型 | 条数 | 含义 |
|---|---|---|
| 纠错 `outdated` | **164** | 与公开来源冲突：版本过期、上游迁移、URL 失效、算错的数值 |
| 补疏漏 `omission` | **186** | 该有却没有：关键机制、边界条件、失败模式、取舍对照 |
| 加厚 `too-brief` | **172** | 只有一两句带过、读者需要更多的地方 |
| 确认无误 `confirmed` | 161 | 经核验原本正确（**不改**，但留下出处） |
| 无法核实 `unverifiable` | 96 | 找不到公开证据，如实标注而非编造 |
| 复核驳回 | 66 | 审计员提出但复核员证伪，**未写入** |
| 类别下调 | 58 | 证据不足，降级处理 |

> [!note] 复核的作用是实打实的
> 124 条（66 驳回 + 58 降级）被拦在回写之前。若只跑审计不跑复核，这些会直接污染知识库。

## 四、最有价值的若干发现（附证据来源）

### 4.1 算错的数值：位置编码手算示例

`ai-dev/AI大模型开发.md` 的位置编码手算表**数值错误且频率方向标反**：原文写 `sin(3/1.04)=0.260`、`cos(3/1.04)=-0.966` 等，实为把分母取整成 1.04（正确 1.03663）。
独立复算（d_model=512, pos=3）：`dim0=+0.1411 dim1=-0.9900 dim2=+0.2451 dim3=-0.9695 dim4=+0.3428 dim5=-0.9394 dim6=+0.4336 dim7=-0.9011`。
同文另有 RoPE 表述、MoE 步数口径、温度采样概率等多处数值问题，均已按「保留原表述 + 更正块」处置。

### 4.2 官方文档的存在与否

`ai-links/DSH插件与Hook开发最佳实践.md` 的 `source_urls` 两条 slug（`deepseek-harness-official`、`deepseek-harness-desktop-src`）实测 **404 / 422**，真实仓库是 `deepseek-ai/deepseek-harness`（默认分支 **master**，非 main）；引用的 `docs/plugin-ecosystem.md`、`docs/plugin-development.md` 亦已 404。
同时「官方 docs 里没有插件分发章节」的判断**被推翻**：`docs/user/develop/basic/publish.zh.md` 确实存在。

### 4.3 幻影产物（写在规范里、实际不存在）

`AGENTS.md` §十一 的命名规范目录树把 `Proxy-Routing-Architecture.excalidraw.md`、`Router-Network-Topology.excalidraw.md` 与真实文件并列，二者**全库不存在**（`diagrams/` 实有 22 张，引用仅此一处）。已加更正块标明那是「命名示例」而非产物清单。

### 4.4 图表绑定字段已换代

该库多处（含 `AGENTS.md`）写的 `startBinding.focus/gap` 是**旧版字段**；实测现由 obsidian-excalidraw-plugin 2.25.3 写出的是 **FixedPointBinding**（`elementId` + `fixedPoint` + `mode`）。同一批还查出 `diagrams/` 22 张图中 **13 张为 `compressed-json`**（read/ripgrep 看不到元素字段），并补了回读解压流程。

### 4.5 缺失的文档被引用

- `cs-base/SQLite原理与实践.md`、`_archive/SESSION-ARCHIVE-2026-07-28.md`：被索引/正文引用但**不存在**。
- `sources/` 六页条目数：建目录时 71 条 → 本次清点 **418 条**（并发簇仍在追加，README 已改为分期快照口径）。

### 4.6 上游路由事实

`settings.yaml` 明确记录 **ox-alpha（tokenra `stealth/ox-alpha`）已于 2026-09-12 从上游下架**，而 [[AGENTS]] 文首的「全局铁律 — 模型路由」仍把 `ox-alpha` 写成**强制模型**（不可豁免）。该规范在当前环境下**无法执行**，属文档与现实冲突。

## 五、并发会话（重要）

本次执行期间，**同一 vault 上另有一个会话在并发工作**（cache-relay 诊断探针、dsh-tui CPU 空转复盘）：

| 产物 | mtime | 归属 |
|---|---|---|
| `CORRECTIONS.md` C-023 / C-024 / C-025 | 18:35 | 并发会话 |
| `claude-ops/事故复盘/dsh-tui-cpu-spin-postmortem-2026-09-13.md` 等 3 篇新文档 | 18:33–18:34 | 并发会话 |
| `scripts/claude-ops-deployments/cache-relay/cache-relay.mjs`（+255 行探针） | 18:27 | 并发会话 |
| `ai-dev/AI大模型开发.md`、`AGENTS.md` 等 166 篇 | 19:41–19:52 | **本次补完** |

两边都编辑过 `AGENTS.md` 与 `CORRECTIONS.md`，经核对**相容且互补，无互相覆盖**。
`dsh-tui-cpu-spin-postmortem-2026-09-13.md` 遗留 2 处悬空 wikilink（`dsh-tui-clock-idle-is-silent` 全库无此文档、`DRSH-TUI插件使用手册` 拼写错误），已做外科式修正并留更正块。

## 六、验收（判据落在工具上，不是 agent 自述）

| 检查 | 命令 | 结果 |
|---|---|---|
| 格式 / 死链 / Mermaid / 连通性 | `python scripts/validate-kb.py` | **0 ERROR**，退出码 0 |
| 外链巡检 | `python scripts/check-links.py --workers 24` | 提取 1248 条 / 探测 1142 条 / 非 200 共 63 条 |
| 残留锁文件 | 查 `_out/kb-completion-2026-09-13/*.lock` | 无 |

> [!tip] 63 条非 200 要分层读，不能当成 63 条死链
> `403`×27 + `401`×10 + `429`×1 = **38 条是反爬/需鉴权**（页面活着，只是拒绝探测）；
> `404`×17 中又有一部分是 **API 基址**（`api.osv.dev/v1/vulns/`、`api.deps.dev/.../packages/`、`api.anthropic.com` 无资源路径本就 404）。
> 真死链里的 `deepseek-harness-official` 等已在回写中修正，巡检报告是修正前的快照。

## 七、未决与建议

1. **96 条 `unverifiable`**：找不到公开证据，需要在**本机实测**才能定性（如路由器固件行为、本机 profile 配置断言）。这批没有被写成结论。
2. **`AGENTS.md` 模型铁律失效**：建议把 `ox-alpha` 改为「继承会话默认模型，禁传 provider/model 覆盖」，并录入 [[CORRECTIONS]]。
3. **并发会话的 3 篇新文档**：`status: stable` 但仍是 untracked（未 git add），且 `cache-relay.mjs.pre-probe-20260913` 备份文件、`.obsidian/workspace.json` 也在工作区——由作者确认后提交或清理。
4. **`sources/` 条目数口径**：现为分期快照（C2 287 → C5 338 → C3 363 → C7 385 → C6 417），并发写入下会持续漂移，建议改为「以脚本重新清点为准」并由 `scripts/url-registry-mine.py` 定期刷新。

## 八、证据归档位置

全部审计与复核原始结论（含每条的证据 URL）落盘在 `_out/kb-completion-2026-09-13/`（该目录由 `.gitignore` 排除，不入版本库）：

| 文件 | 内容 |
|---|---|
| `INDEX.json` | 全部簇的紧凑索引（每篇文档的计数与最重要一条） |
| `<簇>-audit.json` | 20 份审计原始结论（796 条） |
| `<簇>-verified.json` | 20 份复核后结论（779 条 + 驳回/降级记录） |
| `linkcheck.txt` | 外链巡检完整报告 |
| `BASENAMES.txt` | 712 个合法 wikilink 目标（回写时的防死链白名单） |
| `parse-spill.py` / `index-bundles.py` | 可复用的产物抢救与索引脚本 |

## 关联

| 关联对象 | 关系 |
|---|---|
| [[AGENTS]] | 本次全程遵守其协作规范（先读后写 / frontmatter / 禁 Mermaid / 连通性 ≥3） |
| [[CORRECTIONS]] | 本次踩到的「返回值截断当数据到手」应录入；另有 ox-alpha 铁律失效待录 |
| [[HOME]] | 全局索引，本次涉及的子库入口 |
| [[URL-REGISTRY]] | 外链权威性的三层结构之一 |
| [[Claude-Ops-KB-Home]] | 并发会话所属子库 |

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-13 | 建报告：记录 20 簇 fan-out 审计、779 条复核结论、三类改动 522 处、验收结果与未决项 |
