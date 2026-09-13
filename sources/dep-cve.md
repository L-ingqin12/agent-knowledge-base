---
title: 来源登记 — 依赖与 CVE
aliases: [sources-dep-cve, 依赖来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 来源登记 — 依赖与 CVE

> [!abstract] 本页用途
> 存放「依赖与 CVE」主题的来源条目，供 [[URL-Lookup]] 的 Dataview 查询检索。
> 条目协议见 [[URL-Lookup#一、条目从哪来]]；可读版见 [[URL-REGISTRY#1-依赖与-cve]]。

## 官方 / 发行版追踪（判定受影响版本）

- 来源:: Debian 漏洞追踪
  use_when:: 判断某 Debian/Node 包版本是否受某 CVE 影响，并找修复 commit
  url:: https://security-tracker.debian.org/tracker/
  answers:: 受影响版本、修复版本、修复 commit 链接、发行版状态
  authority:: 高
  verified:: 2026-09-12

- 来源:: Ubuntu 安全追踪
  use_when:: 需要 CVE 的披露日期与 CVSS 向量（把 `<CVE-ID>` 换成真实编号，如 `CVE-2026-4923`）
  url:: https://ubuntu.com/security/CVE-2026-4923
  answers:: 披露日期、最近更新日期、CVSS 3 向量、优先级；2026-09-13 实测该真实链接 HTTP 200（Medium，发布 2026-03-26）。路径模板 `https://ubuntu.com/security/<CVE-ID>`（原登记为字面量 `CVE-XXXX-YYYY`，实测 404，已换真实示例）
  authority:: 高
  verified:: 2026-09-12

- 来源:: Alpine 安全追踪
  use_when:: 需要「完整版本区间匹配表」来判断已装版本是否落在范围内（把 `<CVE-ID>` 换成真实编号）
  url:: https://security.alpinelinux.org/vuln/CVE-2026-4923
  answers:: 各分支的 min/max 版本区间、CPE、补丁 commit；2026-09-13 实测该真实链接 HTTP 200（CVE-2026-4923 给出 Match rules `>= 8.0.0 < 8.4.0`）。模板 `https://security.alpinelinux.org/vuln/<CVE-ID>`（原登记为字面量 `CVE-XXXX-YYYY`，已换真实示例）
  authority:: 高
  verified:: 2026-09-12

- 来源:: GitHub Advisory Database
  use_when:: 查 GHSA 原始公告，确认受影响范围与修复版本
  url:: https://github.com/advisories
  answers:: GHSA 公告全文、CVSS、受影响包与版本范围
  authority:: 高
  verified:: 2026-09-12

- 来源:: OSV.dev（API：`https://api.osv.dev/v1/vulns/<CVE-ID>`）
  use_when:: 按包名跨生态查询漏洞；也用于按编号取结构化记录（受影响区间 + fixed 版本）
  url:: https://osv.dev/
  answers:: 多生态漏洞记录、受影响 commit 范围。**覆盖边界（2026-09-13 补）**：OSV 查不到 ≠ 不存在——CNA 直发编号可能缺失（`CVE-2020-14100` 在 OSV API 实测 404），须回 NVD / 厂商公告 / 第三方库复核，本库已实例化于 `sources/network-device.md` 的小米 R3600 条目。本轮经它复核：CVE-2026-4923（path-to-regexp `< 8.4.0` 修复）、CVE-2026-48779（ws `< 8.21.0` 修复）
  authority:: 高
  verified:: 2026-09-13

- 来源:: deps.dev 版本与公告接口（Google Open Source Insights）
  use_when:: 直接判定「某个**已装版本**是否带已知公告」——按包名+版本读 advisoryKeys，省去读区间
  url:: https://api.deps.dev/v3alpha/systems/npm/packages/path-to-regexp/versions/8.4.2
  answers:: 该版本的 advisoryKeys（空 = 无公告）；2026-09-13 实测 path-to-regexp 8.4.2 与 ws 8.21.3 均为空，与 [[URL-REGISTRY]] §1 两行结论一致。换包/版本：`https://api.deps.dev/v3alpha/systems/npm/packages/<package>/versions/<version>`
  authority:: 高
  verified:: 2026-09-13

## 上游包元数据

- 来源:: npm registry 镜像
  use_when:: 判断某包「是否还有更高版本可升」——决定漏洞能否靠升级解决（把 `<package>` 换成真实包名，如 `express`）
  url:: https://registry.npmmirror.com/express
  answers:: dist-tags.latest、全部已发布版本列表；2026-09-13 实测该真实链接返回 registry JSON、dist-tags.latest=5.2.1。模板 `https://registry.npmmirror.com/<package>`（字面量占位实测 404，勿当可点链接）
  authority:: 高
  verified:: 2026-09-12

- 来源:: Express 官方安全更新（逐版本修复页）
  use_when:: 查 Express 生态（含 path-to-regexp）的安全发布与逐版本修复说明
  url:: https://expressjs.com/en/advanced/security-updates/
  answers:: 受影响范围 + 修复版本 + GHSA 链接；2026-09-13 实测 200，明确列出「4.21.2 — dependency path-to-regexp 已更新以修复漏洞」。（更正 2026-09-13：本条原 url 为 https://expressjs.com/blog/ ，实测 301 → `/en/blog`，是博客首页而非安全公告索引；原 answers 记「三条 CVE 同批披露」）
  authority:: 高
  verified:: 2026-09-13

- 来源:: OpenJS CNA 安全公告
  use_when:: 查 Express / Node 生态的 CNA 原始公告（GHSA 之外的官方发布渠道）
  url:: https://cna.openjsf.org/security-advisories.html
  answers:: 2026-09-11 一批 compression（CVE-2026-87776）/ hbs（CVE-2026-87123）/ morgan（CVE-2026-87859）等；2026-09-13 实测 200
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm registry 包元数据（单包 latest）
  use_when:: 核实某个 DSH 生态包的真实版本、repository 与自述——判断文档里的包名/版本是否还在维护
  url:: https://registry.npmjs.org/<package>/latest
  answers:: version、repository、description、engines；本轮用于 dsh-plugin@1.4.3 / @dsh-tui/dsh-tui@0.1.2 / @deepseek-harness-tui/dsh-tui@0.10.1 / dsh-tui@0.2.19 / dsh-bridges@0.2.4 / @deepseek-ai/dsh-mcp-client@0.0.1-rc.1 / @deepseek-ai/dsh-token-meter
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm dist-tags（@deepseek-ai/dsh）
  use_when:: 判断本机该装 `latest` 还是 `next`，或核对文档里的 CLI 版本号是否过期
  url:: https://registry.npmjs.org/@deepseek-ai/dsh
  answers:: latest=0.1.5-rc.1 / next=0.1.5-rc.2 / alpha=0.1.5-alpha.2（2026-09-13）
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm 受限包查询（dsh-session-persistence-jsonl）
  use_when:: 确认随 CLI 发布的内部包版本，解释为何 registry 上取不到同版本 tarball
  url:: https://registry.npmjs.org/@deepseek-ai/dsh-session-persistence-jsonl/latest
  answers:: 公开 latest=0.0.1-rc.1（publishConfig.access=restricted）⇒ 0.1.5-rc.2 只能随 @deepseek-ai/dsh 一起装
  authority:: 高
  verified:: 2026-09-13

- 来源:: GitHub 仓库搜索 API
  use_when:: 核实 star 数、pushed_at、默认分支，或判断某仓库是否改名/根本不存在
  url:: https://api.github.com/search/repositories?q=topic:dsh-plugin&per_page=1
  answers:: topic:dsh-plugin 命中 14626 个仓库；按 `user:` / `repo:` 可复核单个插件仓库现状（含 404/422 反证）
  authority:: 高
  verified:: 2026-09-13

- 来源:: awesome-dsh-plugin 目录计数
  use_when:: 需要「已核实插件数」而不是 topic 命中数时
  url:: https://awesome-dsh-plugin.com/count.json
  answers:: 3632 个已核实插件（对照 topic 命中 14626）
  authority:: 中
  verified:: 2026-09-13

- 来源:: bruc3van/awesome-dsh-plugin 收录标准
  use_when:: 判断某仓库为何没被目录站收录（topic 命中 ≠ 被收录）
  url:: https://raw.githubusercontent.com/bruc3van/awesome-dsh-plugin/main/CONTRIBUTING.md
  answers:: 四条剔除规则：必须公开且带 `dsh-plugin` topic、必须有 description、必须是可安装插件、不得是别的目录站或无关项目
  authority:: 中
  verified:: 2026-09-13

- 来源:: npm search 语义（官方 CLI 文档）
  use_when:: 解释「为什么 `dsh plugin search` 搜不到刚发布的包」
  url:: https://docs.npmjs.com/cli/v11/commands/npm-search
  answers:: npm search 走搜索结果索引；与 `npm view` 直读 registry 元数据是两条不同路径
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm keyword 检索入口
  use_when:: 按 keyword 找 DSH 插件（与 GitHub topic 是两条独立通道）
  url:: https://www.npmjs.com/search?q=keywords:dsh-plugin
  answers:: keyword=dsh-plugin 的全部包（网页入口）
  authority:: 高
  verified:: 2026-09-13

- 来源:: PyPI 包元数据（JSON 接口）
  use_when:: 判断某个 Python 包的最新版、Python 版本要求与是否该在依赖里加上界
  url:: https://pypi.org/pypi/<package>/json
  answers:: latest 版本、requires_python、包描述与作者；`mcp` 实测 latest 2.2.0，包描述自述「keep a `<2` upper bound on your requirement」（本库 mcp-learn 示例仍用 v1 `FastMCP`，详见 `sources/learning-notes.md` 的 B6 节）
  authority:: 高
  verified:: 2026-09-13

## 聚合站（权威度较低，仅作交叉验证）

- 来源:: vuldb
  use_when:: 官方 tracker 未收录时的**人工**补充检索（站点对自动化访问返回 403，别指望脚本抓）
  url:: https://vuldb.com/
  answers:: CVE 概要（**常返回 403 或无正文，勿单独依赖**）；2026-09-13 实测根域返回 403「VulDB | Security Check」，且是全库非 200 列表中唯一来自 `sources/` 的一条。具体 CVE 详情路径未核，保留首页入口
  authority:: 中
  verified:: 2026-09-12

- 来源:: Mend 漏洞库
  use_when:: 补充 CVSS 与受影响版本描述
  url:: https://www.mend.io/vulnerability-database/
  answers:: CVE 描述与严重度（正文有时缺失）
  authority:: 中
  verified:: 2026-09-12

## 内部结论（免重复查）

- 来源:: 本机漏洞分析报告
  use_when:: 复核本机依赖 CVE 结论，避免重复劳动
  url:: file:///%USERPROFILE%/dsh-vulnerability-analysis.md
  answers:: 已核实的 4 条公告判定（path-to-regexp / ws 均不受影响）
  authority:: 高
  verified:: 2026-09-12

- 来源:: 依赖漏洞专项审计
  use_when:: 复核依赖树结构与 junction 农场扫描盲区
  url:: file:///%USERPROFILE%/dsh-dep-vuln-audit.md
  answers:: 18 个包版本表、install hook 清单、junction 结构
  authority:: 高
  verified:: 2026-09-12

- 来源:: 登记册·依赖与 CVE 节
  use_when:: 查看「公告必须成对读取」与 junction 盲区的完整说明
  url:: wikilink://URL-REGISTRY
  answers:: 判定规则、扫描盲区警示、已核实结论表
  authority:: 高
  verified:: 2026-09-12

> [!danger] 本主题的两条硬规则
> 1. **判定必须成对读取**「受影响范围」与「修复版本」——只读前者会得出相反结论（2026-09-12 实际踩过）
> 2. **扫描前先判定是否 junction 农场**——否则 `-Recurse` 返回 0 会被误读为「干净」

## C5 复核新增（2026-09-13）：运行时与标准库行为参考

> 本簇（claude-ops 方案与设计 / hermes 回写）用于判定「某开关或语义是否还存在」的运行时官方文档；通用文档只能证明语言层语义，**不能**佐证 PRoot/Termux 等特定环境行为。

- 来源:: Node.js 官方 CLI 文档
  use_when:: 照抄 `NODE_OPTIONS` / CLI 开关（尤其解析器、线程池类）前，确认它是否仍存在
  url:: https://nodejs.org/api/cli.html
  answers:: 现行 CLI 只有 `--insecure-http-parser`，**没有 `--http-parser` / `--http-parser=legacy`**（已移除；经 `NODE_OPTIONS` 传入会被忽略，既不切换解析器也不强制 HTTP/1.1）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Python 标准库 · `select`
  use_when:: 判断「把连接放进 select 的 write 集合」能否当作保活/判活手段时
  url:: https://docs.python.org/3/library/select.html
  answers:: write 集合只反映**本地发送缓冲可写性**——不发送数据、也不代表对端存活，不能当心跳
  authority:: 高
  verified:: 2026-09-13

- 来源:: Python 标准库 · `socketserver`
  use_when:: 核对 `allow_reuse_address` / `SO_REUSEADDR` 的语义边界时（**通用文档不能佐证 PRoot/Termux 的端口占用行为**）
  url:: https://docs.python.org/3/library/socketserver.html
  answers:: `allow_reuse_address` 控制 `SO_REUSEADDR` 的设置；文档只给通用语义，不含 PRoot/Termux 行为
  authority:: 高
  verified:: 2026-09-13

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 3 条占位模板 URL 被登记成可点链接（ubuntu / alpine 的 `CVE-XXXX-YYYY`、npmmirror 的 `<package>`） | 换为真实示例：两个 tracker 的 `CVE-2026-4923` 实测 200，`registry.npmmirror.com/express` 实测返回 registry JSON（dist-tags.latest=5.2.1）；模板形式移入 `use_when` / `answers` 并注明「勿当可点链接」 |
| 纠错 | Express 安全公告 url 指向博客首页 `https://expressjs.com/blog/`（实测 301 → `/en/blog`） | 换为逐版本修复页 `https://expressjs.com/en/advanced/security-updates/`（实测 200，明确列出「4.21.2 — dependency path-to-regexp 已更新以修复漏洞」）；原 url 与说法保留在 `answers` 的「更正」句中 |
| 纠错 | 两条内部报告 url 写成 `file:///C:/%USERPROFILE%/…`——`file://` URI 不展开变量，点不开 | 改为绝对路径 `file:///%USERPROFILE%/dsh-vulnerability-analysis.md` 与 `…/dsh-dep-vuln-audit.md`（两份文件 Test-Path 均为 True） |
| 补疏漏 | OSV.dev 被登记为默认入口，但无覆盖边界说明 | `answers` 补「OSV 查不到 ≠ 不存在」：`CVE-2020-14100` 在 OSV API 实测 404，须回 NVD / 厂商公告 / 第三方库；并补 API 路径与两个已复核 CVE 的修复版本 |
| 加厚 | 已核实结论缺「下次复核入口」；vuldb 的 403 风险未量化 | 新增 deps.dev 版本公告接口条目（8.4.2 / 8.21.3 的 advisoryKeys 实测为空，与 [[URL-REGISTRY]] §1 一致）与 OpenJS CNA 公告条目（2026-09-11 批次实测 200）；vuldb 条目注明实测 403 与「人工检索」定位，并保留首页入口（具体 CVE 路径未核） |

`path-to-regexp 8.4.2 / ws 8.21.3 均不受影响` 一条经复核独立重抓四个 API 成立，结论与「修复版本」列均无需修改。见 [[CORRECTIONS]]、[[AGENTS]]。

## C4 复核新增（2026-09-13）：工具手册与上游包元数据

- 来源:: `patch(1)` 手册（GNU/BSD 通用语义）
  use_when:: 判断 `.orig` / `-b` 备份到底指哪一份，或设计「补丁版 vs 干净基线」的命名时
  url:: https://man7.org/linux/man-pages/man1/patch.1.html
  answers:: `-b` / `--backup` = *rename or copy the original instead of removing it*；未给 `-B` / `-Y` / `-z` 时后缀取 `SIMPLE_BACKUP_SUFFIX`，默认 `.orig`——即 `.orig` 的约定含义是「**未被改动的原版**」
  authority:: 高
  verified:: 2026-09-13

- 来源:: Python 标准库 · `py_compile`（`.pyc` 失效模式）
  use_when:: 判断「改了 `.py` 却继续跑旧字节码」是否可能，或给部署脚本写缓存判据时
  url:: https://docs.python.org/3/library/py_compile.html
  answers:: TIMESTAMP 模式下 `.pyc` 记录源文件 timestamp + size，运行时比对后才决定是否重编译；只有 `UNCHECKED_HASH` 完全不校验（默认 TIMESTAMP，除非设置 `SOURCE_DATE_EPOCH`，此时默认 CHECKED_HASH）
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm per-version 元数据 · `@anthropic-ai/claude-code` 2.1.177
  use_when:: 核对 CC 某版本是否存在与何时发布（区分「版本发布」与「自动升级发生」）
  url:: https://registry.npmjs.org/@anthropic-ai/claude-code/2.1.177
  answers:: 版本在架；`_npmOperationalInternal.tmp` = 1781312661577 ms = **2026-06-13 01:03:58Z**（故 06-16 是升级发生时间，不是发布时间）
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm per-version 元数据 · `@anthropic-ai/claude-code` 2.1.174
  use_when:: 与 2.1.177 对照，确认回退目标版本的发布时间
  url:: https://registry.npmjs.org/@anthropic-ai/claude-code/2.1.174
  answers:: 版本在架；`_npmOperationalInternal.tmp` = 1781216871895 ms = 2026-06-11 22:27:52Z
  authority:: 高
  verified:: 2026-09-13

- 来源:: GitHub 仓库 API（重命名重定向证据）
  use_when:: 确认本库仓库现名与本地 clone 目录名，避免按旧名 clone 出第二份目录
  url:: https://api.github.com/repos/L-ingqin12/claude-code-knowledge
  answers:: 旧路径重定向到 `full_name = L-ingqin12/agent-knowledge-base`（id 1265645967，public，created_at 2026-06-11T00:53:55Z，pushed_at 2026-09-13T06:39:45Z）
  authority:: 高
  verified:: 2026-09-13

## C3 复核新增（2026-09-13）：CVE 评分的「同一编号两个分数」

> C3 簇在复核小米路由器 CVE 表时发现：同一 CVE 的 **NVD（primary）** 与 **厂商/CNA（secondary）** 会给出不同分值，表格混用会得出相反结论。以下两个结构化接口是判别依据（2026-09-13 实测）。

- 来源:: NVD CVE API 2.0（单条查询，含 primary/secondary 评分）
  use_when:: 判定某 CVE 的 CVSS 到底是谁给的、向量是否含 `PR:N`（即「是否需要认证」）
  url:: https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2023-26319
  answers:: 同一条记录内并列给出多个来源评分——`CVE-2023-26319`：NVD(primary) **7.2 HIGH**（AV:N/AC:L/**PR:H**）、厂商(secondary) **6.7 MEDIUM**（AV:L/AC:L/PR:H），`configurations` 指向 `cpe:2.3:o:mi:xiaomi_router_ax3200_firmware`（<2023.2），描述中**没有** `request_smartcontroller` / `mac`（库内表的注入点属二手整理）；`CVE-2023-26317`：厂商(secondary) **7.0 HIGH**（AV:N/AC:H/PR:N）、NVD(primary) **9.8 CRITICAL**（AV:N/AC:L/PR:N）；`CVE-2019-18370`：`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` = **9.8 CRITICAL**，描述只覆盖 *Xiaomi Mi WiFi **R3G** devices before 2.28.23-stable*，CPE `cpe:2.3:o:mi:millet_router_3g_firmware < 2.28.23`。模板 `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=<CVE-ID>`
  authority:: 高
  verified:: 2026-09-13

- 来源:: MITRE CVE Services API（CNA 原始记录）
  use_when:: 与 NVD 交叉验证描述与受影响范围（尤其判断「型号推广」是否为上游结论）
  url:: https://cveawg.mitre.org/api/cve/CVE-2023-26319
  answers:: CNA 侧记录（与 NVD 描述一致，均无库内补的注入点字段）；用于坐实「库内把 R3G 的 CVE 推广到多型号属页面推断」。模板 `https://cveawg.mitre.org/api/cve/<CVE-ID>`
  authority:: 高
  verified:: 2026-09-13

## C6 复核新增（2026-09-13）：运行时与包的版本锚点（npm latest 四处）

> C6 簇（claude-ops / 架构模式 / 日志分析）在核对库内版本数字时发现：写法普遍是「某版本源码核验」，但**不带复核命令与日期**，于是上游一发版就自动失效。以下四个 latest 端点是当时的核验依据。

- 来源:: npm registry · `@anthropic-ai/claude-code` latest
  use_when:: 核对库内写的 Claude Code 版本号是否已过期（MOC「版本核验矩阵」的锚点）
  url:: https://registry.npmjs.org/@anthropic-ai/claude-code/latest
  answers:: 2026-09-13 实测 `version` = **2.1.270**；库内 `Claude-Ops-KB-Home` 「环境上下文」的 v2.1.172 属原始运行环境的历史记录，不是待更新项。复核命令 `npm view @anthropic-ai/claude-code version`
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm registry · `@earendil-works/pi-coding-agent` latest
  use_when:: 核对 Pi Agent 现行包名与版本；判断库内 `0.84.3` / `0.73.1` 一类锚点是否仍有意义
  url:: https://registry.npmjs.org/@earendil-works/pi-coding-agent/latest
  answers:: 2026-09-13 实测 `version` = **0.85.1**、`engines` = `node>=22.19.0`、依赖 `@earendil-works/chord` / `pi-ai` / `pi-tui` / `pi-agent-core` `^0.85.1`；`exports` 含 `"./rpc-entry"`（即官方 RPC 集成路径）。复核命令 `npm view @earendil-works/pi-coding-agent version`
  authority:: 高
  verified:: 2026-09-13

- 来源:: npm registry · `@mariozechner/pi-coding-agent` latest（旧作用域）
  use_when:: 确认旧包名是否已废弃、还能不能装
  url:: https://registry.npmjs.org/@mariozechner/pi-coding-agent/latest
  answers:: 停在 **0.73.1** 且 `deprecated` 字段逐字「please use @earendil-works/pi-coding-agent instead going forward」；`engines` = `node>=20.6.0`，**无** `./rpc-entry` 导出 ⇒ 库内所有 `from "@mariozechner/..."` 都需替换
  authority:: 高
  verified:: 2026-09-13

- 来源:: Claude Code 官方文档 · sub-agents（子智能体并发与嵌套深度）
  use_when:: 设计 Fan-Out 扇出规模时查「默认能开几个子智能体、能嵌几层」
  url:: https://code.claude.com/docs/en/sub-agents
  answers:: 并发子智能体默认 **20**（超出即 Agent 工具失败并报 `Concurrent subagent limit reached`），可用 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` 调整、需 v2.1.217+、ultracode 会话豁免；嵌套深度 v2.1.172–2.1.216 默认 5（不可改）、v2.1.217–2.1.218 默认 1、v2.1.219 起默认 3（`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`）；非内置子智能体 `description` 合计超 15,000 token 时启动告警
  authority:: 高
  verified:: 2026-09-13

见 [[CORRECTIONS]]、[[AGENTS]]。
