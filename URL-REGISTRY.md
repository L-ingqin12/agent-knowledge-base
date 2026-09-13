---
title: URL 登记册 — 按「何时使用」检索的外部来源索引
aliases: [URL-REGISTRY, URL登记册, 外部来源索引, 网址速查, Link Registry]
tags: [moc, meta, reference]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# URL 登记册 — 按「何时使用」检索

See also: [[HOME]] | [[AGENTS]] | [[AI-Links-KB-Home]] | [[Articles-Index]] | [[Network-KB-Home]]

> [!abstract] 这个文档解决什么问题
> 库内外积累了大量来源网址（当前 vault 内 markdown 已含 **736 个唯一 URL**——2026-09-13 用 `scripts/url-registry-mine.py` 默认口径复算，滤除占位/伪 URL 49 条，加 `--include-archive` 为 742 / 50），但按域名或按时间排列**无法回答「我现在这个问题该查哪个」**。
> 本册的唯一组织维度是 **「什么时候用」**：先找你的当前场景，再取对应来源。
>
> **设计前提**：本册**不依赖 Dataview**（纯 Markdown 表格，任何环境可读）；需要按「何时用」动态检索时见 [[URL-Lookup]]。
>
> 更正（2026-09-13）：本行原写「本 vault **未安装 Dataview**（已核实插件清单）」（原表述）——实测 `.obsidian/community-plugins.json` 含 `dataview`、`.obsidian/plugins/dataview/manifest.json` 的 `version = 0.5.68`，同日建立的 [[URL-Lookup]] 也写明已安装并写入插件清单。该前提与库内事实直接冲突，故改为上面的「不依赖」表述（本册仍只用纯 Markdown，保证任何环境可读）。
>
> 更正（2026-09-13）：本行原写「**572 个唯一 URL / 733 次出现**」（原表述）——复核重跑脚本得唯一 URL **736**、滤除 49；572 是过期口径，「733 次出现」不可由该脚本复算（脚本只统计唯一 URL，没有出现次数计数器），一并弃用。数字只在本册维护一处，并固定「脚本 + 命令 + 口径 + 日期」。

> [!tip] 用法：两步
> 1. 在下方《场景速查表》找到你现在的问题类型
> 2. 跳到对应分区取来源；每条都标注了「权威度」与「核实日期」

---

## 场景速查表（先看这里）

| 你现在的处境 | 去哪一节 | 关键来源 |
|---|---|---|
| 要判断一个 npm 包版本有没有 CVE | [§1 依赖与 CVE](#1-依赖与-cve) | Debian / Ubuntu / Alpine tracker、OSV、项目官方公告 |
| 不确定某公告的「影响范围」和「修复版本」 | [§1](#1-依赖与-cve) | **必须成对读取**——见该节警示 |
| 要改 DSH 的模型路由 / provider | [§2 DSH 与模型路由](#2-dsh-与模型路由) | 本机 `settings.yaml` 注释 + OpenRouter / DeepSeek API 文档 |
| 要查某个代理/中继的历史实现 | [§3 代理与中继](#3-代理与中继本库自有资产) | 本库 `scripts/claude-ops-deployments/` |
| 要查路由器 / 家庭网络配置 | [§4 网络设备](#4-网络与设备) | [[Network-KB-Home]] 子库 |
| 要复核安全事件、找审计方法 | [§5 安全审计](#5-安全审计与漏洞复核) | 本库复盘 + tracker |
| 想找「某个技术概念怎么理解」 | [§6 学习与调研](#6-学习与调研) | [[AI-Links-KB-Home]]、[[Articles-Index]] |
| 要新增一条来源 | [§7 维护规则](#7-维护规则) | 用该节的登记模板 |

---

## 1. 依赖与 CVE

**何时用**：需要确认某个 npm/Python 包版本是否受某 CVE 影响，或需要判断「该不该升级」。

| 来源 | 回答什么问题 | 权威度 | 核实日期 |
|---|---|---|---|
| <https://security-tracker.debian.org/tracker/CVE-2026-4923> | 受影响/修复版本的**发行版视角**；含修复 commit 链接（真实示例：Debian 记 forky/sid `8.4.2-1` fixed） | 高（发行版官方） | 2026-09-13 |
| <https://ubuntu.com/security/CVE-2026-4923> | **披露日期** + CVSS 向量 + 优先级（真实示例：实测 200，Medium，发布 2026-03-26） | 高（发行版官方） | 2026-09-13 |
| <https://security.alpinelinux.org/vuln/CVE-2026-4923> | **完整版本区间匹配表**（最适合判断「我装的是否在范围内」；真实示例给出 Match rules `>= 8.0.0 < 8.4.0`） | 高 | 2026-09-13 |
| <https://github.com/advisories?query=CVE-2026-4923> | GHSA 原始公告，通常含受影响范围与修复版本 | 高（CNA） | 2026-09-12 |
| <https://osv.dev/> | 跨生态漏洞库，可按包名查询；**API** `https://api.osv.dev/v1/vulns/<CVE-ID>`。注意覆盖边界：**OSV 查不到 ≠ 不存在**（CNA 直发编号可能缺失，如 `CVE-2020-14100` 实测 404），须回 NVD / 厂商公告复核 | 高 | 2026-09-13 |
| <https://registry.npmmirror.com/express>（或官方源） | 判断「是否还有更高版本可升」（真实示例：实测返回 registry JSON、`dist-tags.latest = 5.2.1`） | 高（官方源） | 2026-09-13 |
| <https://expressjs.com/en/advanced/security-updates/> | Express 生态（含 path-to-regexp）官方**逐版本修复页**（实测 200，明确列出「4.21.2 — dependency path-to-regexp 已更新以修复漏洞」） | 高（项目官方） | 2026-09-13 |
| <https://cna.openjsf.org/security-advisories.html> | OpenJS CNA 原始公告（2026-09-11 批次：compression / hbs / morgan 等） | 高（CNA） | 2026-09-13 |

> [!warning] 更正（2026-09-13）：本节原登记**字面不可用**的占位 URL（原表述）
> `https://security-tracker.debian.org/tracker/CVE-XXXX-YYYY`（实测 404「matched no results」）、`https://ubuntu.com/security/CVE-XXXX-YYYY`、`https://security.alpinelinux.org/vuln/CVE-XXXX-YYYY`，另有 `https://github.com/advisories?query=GHSA-xxxx` 与 `https://registry.npmjs.org/<pkg>` 同为占位形式——占位形态实测均 404，却被写成可点链接。已全部换成上面的真实示例；`https://expressjs.com/blog/` 也实测 301 → `/en/blog`（博客首页，非安全公告索引），已换为逐版本修复页。

模板（复制后把 `<...>` 换成真实编号，**不要当链接点**）：

```text
https://security-tracker.debian.org/tracker/<CVE-ID>
https://ubuntu.com/security/<CVE-ID>
https://security.alpinelinux.org/vuln/<CVE-ID>
https://github.com/advisories?query=<GHSA-ID 或 CVE-ID>
https://registry.npmjs.org/<package>
```

> [!danger] 血泪教训 —— 公告必须成对读取
> 2026-09-12 复核 `path-to-regexp` 时，曾因**只读了公告的「Affected versions」而漏读紧随其后的「Patched version」**，把一个**已修复**的漏洞误判为「无补丁可用」，并据此推翻了一次**正确**的结论。
>
> **规则：任何漏洞判定，必须同时取到「受影响范围」与「修复版本」两个值，缺一不可。**
> 判定受影响的完整条件：`已装版本 ∈ 受影响范围` **且** `已装版本 < 修复版本`。

> [!warning] 扫描盲区 —— junction 农场
> `~/.dsh/profiles/node_modules` **不是真实安装目录**，而是 **256 个 junction** 指向 `...\@deepseek-ai\dsh\node_modules`（191 项）与 `D:\Program Files\DSH Desktop\...\node_modules`（7 项）。
> `Get-ChildItem -Recurse` 与 `rg`/`grep` **都不跟随 junction**（实测 `-Recurse -File` 返回 **0** 个文件）。
> **后果：任何针对该路径的依赖/密钥扫描都会返回「0 命中」并被误读为「干净」。**
> 正确做法：扫描**主安装树**，或显式解析 junction 目标。

### 本项目已核实的结论（免重复查）

| 包 | 已装 | 结论 | 修复版本 |
|---|---|---|---|
| `path-to-regexp` | 8.4.2 | **不受影响**（CVE-2026-4923 / 4926 / 4867 均 < 8.4.0 或 > 范围） | 8.4.0 |
| `ws` | 8.21.3 | **不受影响**（CVE-2026-48779 影响 `>=8.0.0,<8.21.0`） | 8.21.0 |

> 详见本机报告 `%USERPROFILE%\dsh-vulnerability-analysis.md` 与 [[ds2ox-proxy-retirement]] 同批审计（原文写 `%USERPROFILE%\dsh-vulnerability-analysis.md`，`%USERPROFILE%` 作路径需人工替换、不是可点链接）。
>
> 下次复核入口（2026-09-13 补，两条结论经独立重抓 API 成立）：`https://api.deps.dev/v3alpha/systems/npm/packages/path-to-regexp/versions/8.4.2` 与 `…/ws/versions/8.21.3` 的 `advisoryKeys` 均为空；区间核对见 `https://api.osv.dev/v1/vulns/CVE-2026-4923`（`< 8.4.0` 修复）与 `https://api.osv.dev/v1/vulns/CVE-2026-48779`（`< 8.21.0` 修复）。

---

## 2. DSH 与模型路由

**何时用**：要改 provider、baseURL、模型、思考强度，或排查路由为何走了非预期模型。

| 来源 | 回答什么问题 | 位置 / 链接 |
|---|---|---|
| 本机 `~/.dsh/settings.yaml` 注释 | `llm-deepseek` / `llm-pi-ai` 段含义、**逐请求重读**行为、provider id 冲突原因 | 本机文件（含密钥，勿外传） |
| 本库 `ai-dev/参考-Ark-Agent-Plan计费与配置` | Ark Agent Plan 计费与配置（首列原文误写为 `参考-Rk-Agent-Plan计费与配置`，全库无此文件；右侧 wikilink 一直是对的） | [[参考-Ark-Agent-Plan计费与配置]] |
| [[claude-flash-primary-analysis]] | flash / ox-alpha 主模型切换 | 本库 |
| [[deepseek-cache-key-and-sep-experiments]] | 缓存键构成、扰动分离、模型切换记录 | 本库 |
| [[ds2ox-proxy-retirement]] | 已退役的本地路由代理（附 3 处设计缺陷） | 本库 |
| <https://openrouter.ai/docs> | OpenRouter 端点、模型命名（`z-ai/glm-5.x`） | 官方 |
| <https://api-docs.deepseek.com> | DeepSeek 官方端点 + anthropic 兼容路径 | 官方 |
| <https://openrouter.ai/models> | 确认某免费模型是否仍在上架（**路由失效首查**） | 官方 |

> [!note] 常见故障顺序
> 走错模型 → 先查 `settings.yaml` 的 `agent-default-model`，再查是否有残留 `baseURL` 指向本地代理端口，最后查上游模型是否已下架。

---

## 3. 代理与中继（本库自有资产）

**何时用**：要复用、排障或回滚本机的模型代理/中继。

| 来源 | 内容 | 状态 |
|---|---|---|
| `scripts/claude-ops-deployments/cache-relay/cache-relay.mjs` | 现役多源缓存对齐中继（:8790），**密钥不落地（透传头）**、含健康检查与回滚 | 现役 |
| [[claude-cache-relay-design]] | cache-relay 设计文档 | 现役 |
| `scripts/claude-ops-deployments/deployment-log.md` | 部署/逃生审计日志（原误用 [[claude-cache-relay-design]] 链接指代本条，点进去是设计文档） | 现役 |
| `scripts/claude-ops-deployments/ds2ox-proxy/` | 已退役路由代理（脱敏归档） | **已退役** |
| [[claude-proxy-deployment-postmortem]] | 代理部署事故复盘 | 复盘 |
| [[proxy-cancelretry-hook-incident]] | cancel/retry hook 事故 | 复盘 |
| [[claude-port-rebind-solution]] | 端口重绑定方案 | 参考 |

---

## 4. 网络与设备

**何时用**：路由器、WiFi、代理/分流、家庭网络排障。

| 来源 | 内容 |
|---|---|
| [[Network-KB-Home]] | 网络子库 MOC（入口） |
| [[ROUTER-FULL-CAPABILITY]] | 路由器完整能力手册（R4CM / [IP已脱敏] / SSH） |
| [[参考-小米路由器API认证与利用]] | 小米路由器 API 认证机制 |
| [[参考-网络路由与代理排障]] | 路由与代理排障 |
| [[参考-VPN代理诊断与优化]] | VPN/代理诊断 |
| [[ARCHITECTURE]] / [[GUIDE]] | 网络架构与日常操作 |

> [!warning] 关联安全项
> 本机 `~/.ssh/router_ssh.sh` 含**明文的设备口令**，且 `~/.ssh/router_root`、`id_rsa` 均为**未加密私钥**。路由器凭据应优先轮换，详见同批审计报告。

---

## 5. 安全审计与漏洞复核

**何时用**：复核本次审计结论、复用审计方法、或再次排查本机暴露面。

| 来源 | 内容 |
|---|---|
| `%USERPROFILE%\dsh-vulnerability-analysis.md` | 本机系统漏洞分析报告（6 严重 / 4 高危 / 7 中危）；原文写 `%USERPROFILE%\…`，该占位需人工替换、不是可点路径 |
| `%USERPROFILE%\dsh-dep-vuln-audit.md` | 依赖漏洞专项审计明细（含 junction 农场结构）；同上更正 |
| [[ds2ox-proxy-retirement]] | 本地路由代理的安全复核与退役 |
| [[OPTIMIZATION-AUDIT]] | 既有优化/审计文档 |
| <https://security-tracker.debian.org/> | 发行版漏洞追踪（判定受影响版本） |
| <https://osv.dev/> | 跨生态漏洞库 |

> [!tip] 本机审计的关键方法（可复用）
> - ACL 判定用 `icacls`，不要假设「用户目录默认安全」——本机 `C:\` 根对象为 `BUILTIN\Users:(OI)(CI)(RX)` + `NT AUTHORITY\Authenticated Users:(OI)(CI)(IO)(M)`，`D:\` 另有 `Authenticated Users:(M)`（直接赋权、**无 `IO`**）+ `Users:(OI)(CI)(IO)(GR,GE)`
>   - 更正（2026-09-13）：原文写「本机 `C:\` 收紧而 `D:\` 为 `Authenticated Users:(M)` + `Users:(RX)`，**两卷相反**」（原表述）——「两卷相反」不成立：两卷都给 Users 读/执行、给 Authenticated Users 修改权；差别是 `D:\` **根对象本身**就直接开写，`C:\` 根对象只有继承型 `(IO)`。此结论属**本机配置类论断**，以现场 `icacls` 输出为准
> - 依赖扫描前先判定是否 junction 农场（见 [§1 警示](#1-依赖与-cve)）
> - git 历史泄露检查用 `git log --all -S "<完整密钥串>"`，命中即说明密钥已进入历史（处置 rotate 优先）

---

## 6. 学习与调研

**何时用**：要理解某个技术概念，或找既有调研结论避免重复研究。

| 来源 | 内容 |
|---|---|
| [[AI-Links-KB-Home]] | AI 链接收藏库 MOC |
| [[Articles-Index]] | 文章库索引（可解释性 / 上下文工程 / Skill / 机制拆解） |
| [[2026-08-16-AI链接综述与归档]] | 链接调研综述主文档 |
| [[参考-OpenCode-技术调研报告]] | OpenCode 全机制调研 |
| [[参考-Pi-Agent-技术调研报告]] | Pi Agent 调研 |
| [[AI-Dev-KB-Home]] | LLM 应用开发实战子库 |
| [[CS-KB-Home]] | 计算机基础子库 |

---

## 7. 维护规则

> [!important] 收录标准（只收「会再用」的）
> 收录一条 URL 需满足至少一项：
> 1. **无它无法复核结论**（如漏洞 tracker、官方公告）
> 2. **易失效但重要**（如模型上下架页、API 文档）
> 3. **本库自有资产**（脚本、复盘、设计文档）
>
> **不收**：一次性搜索结果页、可通过本库文档替代的二手转载。

### 登记模板

复制以下行加入对应分区：

```markdown
| <URL> | 回答什么问题 | 权威度（高/中/低） | 核实日期 YYYY-MM-DD |
```

带「何时用」说明的完整块模板：

```markdown
### <主题>
**何时用**：<一句话场景>
| 来源 | 回答什么问题 | 权威度 | 核实日期 |
|---|---|---|---|
| <URL> | | | |
```

### 字段约定

| 字段 | 说明 |
|---|---|
| `权威度` | **高**=官方/原始来源；**中**=知名聚合（vuldb、Mend 等）；**低**=二手转载 |
| `核实日期` | **必填**。URL 会失效、结论会过期；无核实日期的条目一律视为不可信 |
| `状态` | 现役 / 已退役 / 复盘 —— 仅用于本库自有资产 |

> [!warning] 三条维护纪律
> 1. **第三方聚合站（vuldb / Mend / deps.dev）常返回无正文或 403**——遇到时不要猜，改用该节列出的发行版 tracker 交叉验证
> 2. **结论要带日期**——「不受影响」只在特定已装版本下成立；依赖升级后须复核
> 3. **本册与 §1 的「已核实结论」表保持同步**——若某条结论被推翻，两处都要改（参见 §1 血泪教训）

### 待补录

当前 vault 内 **736 个唯一 URL**（2026-09-13 用 `scripts/url-registry-mine.py` 默认口径复算）尚未全量登记。本册先建立**检索骨架 + 高频场景**，后续按「用到时才补」的方式增量登记——避免一次性搬运产生无人维护的死表。

| 分区 | 待补录规模（脚本分类计数，命令 + 日期） | 优先级 |
|---|---|---|
| §1 依赖与 CVE | 28 条唯一 URL（本批 12 条已分流） | 已覆盖**高频判定路径**，剩余约 16 条待人工分流 |
| §2 DSH 与模型路由 | 23 条 | 高 |
| §4 网络与设备 | 8 条 | 中 |
| §3 代理与中继 / §5 安全审计 | 5 条 / 4 条 | 低 |
| §6 学习与调研 | **136 条**（`ai-links/articles` 为主，已有 [[Articles-Index]] 承载） | 低（已有索引） |
| 未分类 | 532 条（待主题分流） | — |

> 更正（2026-09-13）：本表原写「§1 少量（本批已基本覆盖）｜**已覆盖**」「§2 中」「§4 中」「§6 **大**」（原表述），**无口径说明**。复核运行 `scripts/url-registry-mine.py`（2026-09-13）得各主题唯一 URL 数：学习与调研 136、依赖与 CVE 28、DSH 与模型路由 23、网络与设备 8、代理与中继 5、安全审计 4、未分类 532；而 §1 表格仅 8 行、`sources/dep-cve.md` 12 条，故「已覆盖」不成立——已改为「已覆盖高频判定路径 + 剩余条数待人工分流」，规模列改为「脚本分类数（命令 + 日期）」。

---

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-12 | 建册；登记 §1 依赖与 CVE、§2 DSH 路由、§3 代理资产的已核实来源；记录 junction 扫描盲区与公告成对读取教训 |
| 2026-09-13 | C8 簇回写：更正「未安装 Dataview」前提与 572/733 计数口径（统一为脚本复算 736）、§1 占位 URL 换真实示例并加不可点模板、§2 `参考-Rk-…` 字母错位、§3 deployment-log 误用 wikilink、§5 ACL「两卷相反」更正；§1 已核实结论补两条 API 复核入口；新增「补完记录」节 |

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 设计前提写「本 vault **未安装 Dataview**（已核实插件清单）」，与库内事实直接冲突 | 改为「本册**不依赖** Dataview（纯 Markdown，任何环境可读）；动态检索见 [[URL-Lookup]]」；依据：`.obsidian/community-plugins.json` 含 `dataview`、`manifest.json` 的 `version = 0.5.68`；原表述保留在更正块内 |
| 纠错 | 「572 个唯一 URL / 733 次出现」（§7 又重复一次 572） | 统一为脚本复算值 **736**（滤除 49；`--include-archive` 742/50），写明「脚本 + 命令 + 口径 + 日期」；733 与 1073 均不可由该脚本复算，已弃用；原表述保留在更正块内 |
| 纠错 | §1 表格把三条占位模板 URL（Debian / Ubuntu / Alpine 的 `CVE-XXXX-YYYY`）写成可点链接，另 `GHSA-xxxx`、`registry.npmjs.org/<pkg>` 同为占位 | 换为真实示例（`CVE-2026-4923` 三站实测 200）、`registry.npmmirror.com/express` 实测有 JSON；占位形式改为**不可点的代码块模板**；`expressjs.com/blog/`（301 → `/en/blog`）换为逐版本修复页并新增 OpenJS CNA 行 |
| 纠错 | §2 首列 `参考-Rk-Agent-Plan计费与配置` 字母错位（全库无 `参考-Rk-*` 文件） | 改为 `ai-dev/参考-Ark-Agent-Plan计费与配置`（右侧 wikilink 一直正确） |
| 纠错 | §3 复用 `[[claude-cache-relay-design]]` 链接指代 `deployment-log.md`（张冠李戴） | 改为直接给路径 `scripts/claude-ops-deployments/deployment-log.md`；既有 wikilink 未删改 |
| 纠错 | §5 关键方法写「`C:\` 收紧而 `D:\` …，**两卷相反**」 | 保留原表述并标注更正：两卷都给 Users 读/执行、给 Authenticated Users 修改权，差别是 `D:\` 根对象**直接赋权**、`C:\` 根对象只有继承型 `(IO)`；标注属本机配置类论断（以现场 `icacls` 为准） |
| 加厚 | §7 待补录表用「少量/中/大」+「已覆盖」等无口径判断 | 规模列改为「脚本分类计数（命令 + 日期）」：学习 136 / 依赖 28 / DSH 23 / 网络 8 / 代理 5 / 安全 4 / 未分类 532；「已覆盖」改为「已覆盖高频判定路径，剩余约 16 条待人工分流」 |
| 加厚 | §1「已核实结论」表缺下次复核入口 | 补两条结论的 API 复核入口（deps.dev 两个版本的 `advisoryKeys` 为空；OSV 两条 CVE 的修复区间） |
| 纠错 | §5 表格与本册其他处的 `%USERPROFILE%\...` 路径 | 改为绝对路径 `%USERPROFILE%\...` 并注明该占位不可点 |

见 [[CORRECTIONS]]、[[AGENTS]]。
