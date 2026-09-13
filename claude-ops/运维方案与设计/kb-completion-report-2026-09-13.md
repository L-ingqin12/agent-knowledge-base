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

> [!success] 残余复核（2026-09-13）：本行三个数**可由落盘产物重算复现**，不是自述。对 `_out/kb-completion-2026-09-13/*-verified.json`（20 份）逐条统计 `status` 字段：`outdated` 164 / `omission` 186 / `too-brief` 172 / `confirmed` 161 / `unverifiable` 96，合计 **779**；164+186+172 = **522**，去重后涉及 **163** 篇文档；`rejected` 66、`downgraded` 58 亦逐份对上。依据：`D:\Document\local\knowledge\_out\kb-completion-2026-09-13\*-verified.json`（重算于 2026-09-13）。

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

> [!success] 残余复核（2026-09-13）：本表 `无法核实 unverifiable = 96` 与 `确认无误 confirmed = 161` 已按上条口径重算对上（见文首残余复核）；96 条另在 `_out/kb-completion-2026-09-13/_rows96.json` 有全量落盘，逐条含 `claim` / `rc`（原因分类）/ `cf`（复核说明）。原因分类分布：`unverified-claim` 62、`inference-not-observation` 17、`count-or-numeric` 6、`url-or-entity-gone` 6、`none` 3、`upstream-moved` 2；其中 8 条带 `file://` 本机证据（配置类，已在本机读过文件）。

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

> [!success] 残余复核（2026-09-13）：本节可**离线复跑复现**。①校验器重跑：`python scripts/validate-kb.py` → 仍 **0 ERROR**、退出码 0（现存 **377** 个 `.md` / 校验 280 篇，较报告时的 376/279 各 +1，属后续新增文档的正常漂移）；②外链巡检验尸：`_out/kb-completion-2026-09-13/linkcheck.txt` 表头即 **提取 1248 / 探测 1142 / 词法过滤 47 / 非 200 共 63**，与报告逐字一致；非 200 分层亦对上（403×27 + 401×10 + 429×1 = 38 属反爬/鉴权，404×17 含 API 基址）。依据：本机重跑 + 缓存报告（核验于 2026-09-13）。

> [!tip] 63 条非 200 要分层读，不能当成 63 条死链
> `403`×27 + `401`×10 + `429`×1 = **38 条是反爬/需鉴权**（页面活着，只是拒绝探测）；
> `404`×17 中又有一部分是 **API 基址**（`api.osv.dev/v1/vulns/`、`api.deps.dev/.../packages/`、`api.anthropic.com` 无资源路径本就 404）。
> 真死链里的 `deepseek-harness-official` 等已在回写中修正，巡检报告是修正前的快照。

## 七、未决与建议

1. **96 条 `unverifiable`**：找不到公开证据，需要在**本机实测**才能定性（如路由器固件行为、本机 profile 配置断言）。这批没有被写成结论。
2. **`AGENTS.md` 模型铁律失效**：建议把 `ox-alpha` 改为「继承会话默认模型，禁传 provider/model 覆盖」，并录入 [[CORRECTIONS]]。
3. **并发会话的 3 篇新文档**：`status: stable` 但仍是 untracked（未 git add），且 `cache-relay.mjs.pre-probe-20260913` 备份文件、`.obsidian/workspace.json` 也在工作区——由作者确认后提交或清理。
4. **`sources/` 条目数口径**：现为分期快照（C2 287 → C5 338 → C3 363 → C7 385 → C6 417），并发写入下会持续漂移，建议改为「以脚本重新清点为准」并由 `scripts/url-registry-mine.py` 定期刷新。

> [!success] 残余复核（2026-09-13）：本节 4 条**逐条定论**。
> **①96 条 `unverifiable`** —— 性质已澄清，**部分仍开放**。全量清单落盘在 `_out/kb-completion-2026-09-13/_rows96.json`（96 条，含 `claim`/`rc`/`cf`）与 `_unver_96.md`；原因分类 `unverified-claim` 62 / `inference-not-observation` 17 / `count-or-numeric` 6 / `url-or-entity-gone` 6 / `none` 3 / `upstream-moved` 2，其中 8 条带 `file://` 本机证据（配置类，**已在本机读过文件**，非未查）。真正「需本机实测或厂商确认」的是前者中的多数（如路由器固件行为、厂商未定义的语义），本库无法定论，判据即该 JSON 的 `cf` 字段里已写明的复跑命令或待确认项。
> **②`AGENTS.md` 模型铁律** —— **已解决**。`AGENTS.md` 文首 [!danger] 块已加 2026-09-13 订正（点名 `ox-alpha` 已于 2026-09-12 下架、该条不可执行），并把规则改为只约束「**不得覆盖**」、不再点名模型；§十一第 9 条同步改写为「一律继承会话默认模型」。注意 [[CORRECTIONS]] 侧**未新增专条**，只在该订正里做了同族交叉引用（C-010「把配置字段当作稳定值」）——若作者认为值得独立成条，属另行决定。
> **③并发会话的 3 篇新文档 / 备份文件 / `workspace.json`** —— **已解决**。`git status --porcelain --untracked-files=all` 现仅 1 行：` M .obsidian/workspace.json`（编辑器 UI 状态，属本机常态），**untracked 文件为 0**；3 篇新文档与 `scripts/claude-ops-deployments/cache-relay/cache-relay.mjs.pre-probe-20260913` 均已在 `673314c` 提交入库。依据：`git ls-files` 与 `git log -- <备份文件>`（核验于 2026-09-13）。
> **④`sources/` 口径** —— **已解决，并订正建议里的工具错配**。`sources/README.md` 已改为「以重新清点为准」的明确表述；独立重算六页列表项 `- 来源::` 得 37 / 29 / 263 / 37 / 31 / 20 = **417**，与 README 现值一致。但「由 `scripts/url-registry-mine.py` 定期刷新」**不成立**：该脚本的自我定位是「只产出**草稿**，不自动改写 `sources/`」，做的是从全库挖掘 URL 生成候选条目，**不做条目清点**。清点只需 `grep -c '^- 来源::' sources/*.md`。
> 依据：`_out/kb-completion-2026-09-13/_rows96.json`、`AGENTS.md`、`git ls-files`/`git log`、`sources/README.md`、`scripts/url-registry-mine.py` 文档串（核验于 2026-09-13）。

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
| 2026-09-13 | 残余复核（§七 4 条逐条定论）：①96 条 `unverifiable` 澄清归档位置与原因分类分布（62/17/6/6/3/2），需真机或厂商确认者仍开放；②`AGENTS.md` 模型铁律已改（只约束「不得覆盖」、不再点名模型），[[CORRECTIONS]] 侧仅同族交叉引用 C-010；③并发会话 3 篇文档与 `.pre-probe-20260913` 备份均已在 `673314c` 提交，untracked 为 0；④`sources/` 已改为「以重新清点为准」，独立重算 = 417 与 README 一致，并订正「用 `url-registry-mine.py` 刷新」的工具错配 |
| 2026-09-13 | 残余复核（可复现性）：文首 522/161/96 与 §三 计数由 20 份 `*-verified.json` 重算复现（779 = 164+186+172+161+96，去重 163 篇）；§六 验收离线复跑——`validate-kb.py` 仍 0 ERROR（现存 377 篇 / 校验 280），`linkcheck.txt` 缓存数 1248/1142/63 逐字对上 |
