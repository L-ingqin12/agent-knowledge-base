---
title: URL 速查台 — 按场景动态检索
aliases: [URL-Lookup, 网址速查台, 场景速查, URL Lookup Board]
tags: [moc, meta, reference]
created: 2026-09-12
updated: 2026-09-12
status: draft
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

> [!warning] 为什么必须是列表项
> Dataview **无法查询 Markdown 表格的行**（表格内容不是可枚举对象）。
> 因此「检索版」用列表项，「可读版」用表格——两者并存，见 [[URL-REGISTRY]]。

---

## 二、按场景检索

### 我现在要判断一个依赖有没有 CVE

```dataview
TABLE WITHOUT ID
  link(file.path, source) AS 来源,
  answers AS 能回答什么,
  authority AS 权威度,
  verified AS 核实日期
FROM "sources"
WHERE contains(use_when, "CVE") OR contains(use_when, "依赖") OR contains(use_when, "漏洞")
SORT authority ASC, verified DESC
```

### 我现在要改模型路由 / provider

```dataview
TABLE WITHOUT ID
  link(file.path, source) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE contains(use_when, "路由") OR contains(use_when, "模型") OR contains(use_when, "provider")
SORT verified DESC
```

### 我现在要排查代理 / 中继

```dataview
TABLE WITHOUT ID
  link(file.path, source) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE contains(use_when, "代理") OR contains(use_when, "中继") OR contains(use_when, "8899") OR contains(use_when, "8790")
SORT verified DESC
```

### 我现在要查路由器 / 家庭网络

```dataview
TABLE WITHOUT ID
  link(file.path, source) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE contains(use_when, "路由器") OR contains(use_when, "网络") OR contains(use_when, "WiFi") OR contains(use_when, "SSH")
SORT verified DESC
```

### 我要复核安全审计

```dataview
TABLE WITHOUT ID
  link(file.path, source) AS 来源,
  answers AS 能回答什么,
  verified AS 核实日期
FROM "sources"
WHERE contains(use_when, "审计") OR contains(use_when, "安全") OR contains(use_when, "ACL") OR contains(use_when, "密钥")
SORT verified DESC
```

### 全部条目（兜底，按核实日期排序）

```dataview
TABLE WITHOUT ID
  link(file.path, source) AS 来源,
  use_when AS 何时用,
  authority AS 权威度,
  verified AS 核实日期
FROM "sources"
SORT verified DESC
```

### 过期复核 —— 核实日期超过 180 天的条目

```dataview
TABLE WITHOUT ID
  link(file.path, source) AS 来源,
  verified AS 核实日期,
  (date(today) - date(verified)).days AS 已过天数
FROM "sources"
WHERE verified AND (date(today) - date(verified)).days > 180
SORT verified ASC
```

### 低权威度条目（应尽量替换为官方来源）

```dataview
TABLE WITHOUT ID
  link(file.path, source) AS 来源,
  authority AS 权威度,
  answers AS 能回答什么
FROM "sources"
WHERE authority = "低"
```

---

## 三、临时一次性查询

不想新增主题笔记时，可在任意位置直接写：

````markdown
```dataview
TABLE WITHOUT ID source AS 来源, url AS 链接, answers AS 能回答什么
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
