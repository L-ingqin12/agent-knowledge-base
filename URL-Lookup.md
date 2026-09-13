---
title: URL 速查台 — 按场景动态检索
aliases: [URL-Lookup, 网址速查台, 场景速查, URL Lookup Board]
tags: [moc, meta, reference]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# URL 速查台 — 按场景动态检索

See also: [[URL-REGISTRY]] | [[HOME]] | [[AGENTS]] | [[AI-Links-KB-Home]]

> [!abstract] 这是什么
> [[URL-REGISTRY]] 是**人工可读的登记册**（表格，按分区组织）；
> **本页是它的检索端**：用 Dataview 把散落各处、带内联字段的来源条目**按「何时使用」动态筛出来**。
>
> 分工：**登记册回答「有哪些」，速查台回答「我现在该看哪个」。**

> [!info] 前置条件（已就绪）
> 本页依赖 **Dataview v0.5.68** 社区插件，已在 2026-09-12 安装并写入 `community-plugins.json`。
> 首次在 Obsidian 打开时可能提示「第三方插件」需信任；信任后本页查询即生效。
> **若插件不可用**，本页不显示结果，但 [[URL-REGISTRY]] 的表格仍完全可用（纯 Markdown，不依赖插件）。

> [!info] 版本策略（2026-09-13 复核）
> 以**记录的安装版本 `v0.5.68`** 为基线，允许的最低版本同为 **≥ 0.5.68**（更早版本未验证 `字段:: 值` 内联字段与 `date(today)` 差值查询）。
> **核对方法**：读 `.obsidian/plugins/dataview/manifest.json` 的 `version` 字段；`.obsidian/community-plugins.json` 含 `"dataview"` 才代表已启用。
> **升级纪律**：升级前先在测试库跑一遍本页 10 条查询——`link(file.path, 来源)`（CJK 字段名取列）与 `(!status OR status != "retired")`（空值语义）最易随版本变化。

> [!warning] 更正（2026-09-13）：安装版本 `v0.5.68` 已非最新——官方最新 release 为 **0.5.70**（2025-04-07 发布，release body「Still attempting to fix #2557」）。（原表述为「本页依赖 **Dataview v0.5.68** 社区插件，已在 2026-09-12 安装并写入 `community-plugins.json`」——未写是否为最新版，也未给允许的最低版本。）
> 来源：https://api.github.com/repos/blacksmithgu/obsidian-dataview/releases/latest

---

## 一、条目从哪来

速查台不自己存数据，它查的是**带内联字段的条目**。条目使用 Obsidian 内联字段语法（`字段:: 值`），当前约定放在 `sources/` 目录下的主题笔记里：

```
knowledge/sources/
  dep-cve.md           依赖与 CVE
  dsh-routing.md       DSH 与模型路由
  proxy-relay.md       代理与中继
  network-device.md    网络与设备
  security-audit.md    安全审计
  learning-notes.md    学习与调研
```

**条目写法**（每行一个，必须是列表项，Dataview 才能识别）：

```markdown
- 来源:: Debian 漏洞追踪
  use_when:: 判断某 npm/Debian 包版本是否受某 CVE 影响
  url:: https://security-tracker.debian.org/tracker/
  answers:: 受影响版本、修复版本、修复 commit
  authority:: 高
  verified:: 2026-09-12
```

> [!warning] 更正（2026-09-13）：查询里的「来源」列原写作 `link(file.path, source)`，但 `sources/` 六页条目的首字段实际是 `来源::`（逐页统计：`来源::` 71 条、`source::` 0 条，frontmatter 亦无 `source` 键），而 `source` 不是 Dataview 的内建隐式字段——该列会整列取空（`use_when` / `answers` / `authority` / `verified` 照常工作）。本页查询已统一改为 `link(file.path, 来源) AS 来源`，与上面「条目写法」的首字段对齐。（原表述为 `link(file.path, source) AS 来源`。）

> [!warning] 为什么必须是列表项
> Dataview **无法查询 Markdown 表格的行**（表格内容不是可枚举对象）。
> 因此「检索版」用列表项，「可读版」用表格——两者并存，见 [[URL-REGISTRY]]。

---

## 二、按场景检索

> [!note] 2026-09-13 复核回标：本节原 8 条查询都不过滤 `status:: retired`，而 §四 维护表与 `sources/README.md` 都规定「停用来源：标注 `status:: retired`，不建议直接删除」——停用机制因此形同虚设。现已给每条 `FROM "sources"` 补上 `WHERE ... AND (!status OR status != "retired")`（`!status` 用于兼容未写 `status` 的老条目），并另设「已停用来源」查询兜住被排除的条目。（原查询无任何 `status` 过滤。）

### 我现在要判断一个依赖有没有 CVE

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  answers AS 能回答什么,
  authority AS 权威度,
  verified AS 核实日期
FROM "sources"
WHERE (contains(use_when, "CVE") OR contains(use_when, "依赖") OR contains(use_when, "漏洞")) AND (!status OR status != "retired")
SORT authority ASC, verified DESC
```

### 我现在要改模型路由 / provider

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE (contains(use_when, "路由") OR contains(use_when, "模型") OR contains(use_when, "provider")) AND (!status OR status != "retired")
SORT verified DESC
```

### 我现在要排查代理 / 中继

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE (contains(use_when, "代理") OR contains(use_when, "中继") OR contains(use_when, "8790")) AND (!status OR status != "retired")
SORT verified DESC
```

> [!note] 2026-09-13 复核回标：原查询含 `OR contains(use_when, "8899")` 分支，但 `sources/` 六页全文无 `8899` 字样（该端口只出现在历史复盘里），该分支恒不命中，已移除；`:8790` 分支有效（见 `sources/proxy-relay.md` 的 `use_when` 写作「（:8790）」）。若后续把 8899 补进条目数据，再恢复该分支。（原表述为 `... OR contains(use_when, "8899") OR contains(use_when, "8790")`。）

### 我现在要查路由器 / 家庭网络

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE (contains(use_when, "路由器") OR contains(use_when, "网络") OR contains(use_when, "WiFi") OR contains(use_when, "SSH")) AND (!status OR status != "retired")
SORT verified DESC
```

### 我要复核安全审计

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE (contains(use_when, "审计") OR contains(use_when, "安全") OR contains(use_when, "ACL") OR contains(use_when, "密钥")) AND (!status OR status != "retired")
SORT verified DESC
```

### 全部条目（兜底，按核实日期排序）

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  use_when AS 何时用,
  authority AS 权威度,
  verified AS 核实日期
FROM "sources"
WHERE (!status OR status != "retired")
SORT verified DESC
```

### 过期复核 —— 核实日期超过 180 天的条目

> [!note] 2026-09-13 复核回标：180 天阈值原先无依据说明，且 `sources/` 六页 71 条 `verified::` 全部为 2026-09-12，故该查询在 **2027-03-11** 之前恒返回空（首次可能命中的日期 = 2026-09-12 + 180 天）。
> **阈值分档（本页口径）**：① **外部 URL 类**（厂商公告 / CVE 库 / 官方文档）——以 **180 天** 为上限，链接与结论都易漂移，最紧；② **本机资产类**（`file:///` 与 `wikilink://` 指向库内脚本、部署日志）——**随状态变更复核**，部署 / 退役 / 改名即需重核，不单看日期；③ **结论类**（版本号、「不受影响」判定）——**随依赖升级复核**，上游发版或 CVE 库更新即重核。

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  verified AS 核实日期,
  (date(today) - date(verified)).days AS 已过天数
FROM "sources"
WHERE verified AND (date(today) - date(verified)).days > 180 AND (!status OR status != "retired")
SORT verified ASC
```

### 按权威度分档复核（提前预警：已过 90 天）

按上文三档口径排期：90 天为预警线，先按 `authority` 分档、再按已过天数排序，便于逐条决定「换官方源 / 重跑命令 / 重新核实」。

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  authority AS 权威度,
  verified AS 核实日期,
  (date(today) - date(verified)).days AS 已过天数
FROM "sources"
WHERE verified AND (date(today) - date(verified)).days > 90 AND (!status OR status != "retired")
SORT authority ASC, verified ASC
```

### 低权威度条目（应尽量替换为官方来源）

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  authority AS 权威度,
  answers AS 能回答什么
FROM "sources"
WHERE authority = "低" AND (!status OR status != "retired")
```

### 已停用来源（`status:: retired`，仅供追溯）

被上面各条查询排除的条目都收在这里——`sources/README.md` 规定停用来源标注 `status:: retired` 而不直接删除，故它们仍需可被检索到。

```dataview
TABLE WITHOUT ID
  link(file.path, 来源) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE status = "retired"
SORT verified DESC
```

---

## 三、临时一次性查询

不想新增主题笔记时，可在任意位置直接写：

````markdown
```dataview
TABLE WITHOUT ID 来源, url AS 链接, answers AS 能回答什么
FROM "sources"
WHERE contains(use_when, "你的关键词")
```
````

---

## 四、维护

| 动作 | 做法 |
|---|---|
| 新增来源 | 在 `sources/<主题>.md` 追加一个列表项（六个字段齐全） |
| 停用来源 | 加 `status:: retired`，或删除该行；不建议直接删主题笔记 |
| 更新结论 | 同步改 `verified::` 日期 **并**更新 [[URL-REGISTRY]] 的对应表格行 |
| 批量补录 | 用 `scripts/url-registry-mine.py` 扫描 vault 现有 URL 生成候选条目 |

> [!danger] 两条纪律（与 [[URL-REGISTRY]] 一致）
> 1. **`verified` 必填**——URL 会失效、结论会过期，无核实日期的条目视为不可信
> 2. **判定漏洞必须成对读取**「受影响范围」与「修复版本」——详见 [[URL-REGISTRY#1-依赖与-cve]]

---

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-12 | 建页；安装 Dataview v0.5.68 并启用；定义内联字段条目协议（source / use_when / url / answers / authority / verified）；内置 8 个场景查询与过期复核查询 |
| 2026-09-13 | 复核回标：来源列改用 `来源` 字段（原写 `source`）；各查询补 `status:: retired` 过滤，并新增「已停用来源」「按权威度分档复核（90 天预警）」两条查询；移除恒不命中的 8899 分支；补 Dataview 版本策略、核对方法与来源 URL；补完记录见文末 |

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 「来源」列写作 `link(file.path, source)`，而 `sources/` 条目首字段实际是 `来源::`（逐页统计 71 条 `来源::`、0 条 `source::`），`source` 非内建字段 → 该列整列取空 | 全部查询改为 `link(file.path, 来源) AS 来源`，§三 示例同步改；依据：六页 `sources/` 逐页 grep + Dataview 字段名规则（字段名即 `::` 前的键） |
| 纠错 | 「排查代理 / 中继」查询含 `OR contains(use_when, "8899")` 分支，但 `sources/` 六页无 `8899` 字样，该分支恒不命中 | 移除 8899 分支（保留有效的 `:8790` 分支）；依据：`sources/` 全量 grep 无 8899，其仅见于历史复盘 |
| 纠错 | 前置条件只写「已安装 v0.5.68」，未说明是否为最新版、未给允许的最低版本 | 补 [!warning] 更正 + 「版本策略」小节（基线 ≥ 0.5.68、核对 `manifest.json`、升级前先验证本页查询）；依据官方 release API：最新 0.5.70（2025-04-07，body「Still attempting to fix #2557」） |
| 补疏漏 | 8 条场景查询均不过滤 `status:: retired`，与 §四 维护表及 `sources/README.md` 的「停用不删行」约定冲突，停用机制形同虚设 | 每条 `FROM "sources"` 后补 `AND (!status OR status != "retired")`（兼容无 `status` 键的老条目），并新增「已停用来源」查询兜住被排除条目 |
| 加厚 | 「过期复核 180 天」无阈值依据、无分档说明、无首次生效日期（六页 71 条 `verified::` 全为 2026-09-12，此前恒空） | 补三档口径（外部 URL ≤180 天 / 本机资产随状态变更 / 结论类随依赖升级）与首次可命中日期 2027-03-11；新增「按权威度分档复核（90 天预警）」查询 |

> 回链：[[CORRECTIONS]]
