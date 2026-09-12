---
title: 来源登记索引（sources/）
aliases: [sources-README, 来源登记索引, Sources Index]
tags: [moc, meta, reference, source]
created: 2026-09-12
updated: 2026-09-12
status: draft
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
| [[sources/dep-cve\|dep-cve]] | 依赖与 CVE：发行版 tracker、官方公告、包元数据 | 12 |
| [[sources/dsh-routing\|dsh-routing]] | DSH 与模型路由：上游 API 文档、本机配置、模型切换调研 | 12 |
| [[sources/proxy-relay\|proxy-relay]] | 代理与中继：现役/退役资产、事故复盘 | 11 |
| [[sources/network-device\|network-device]] | 网络与设备：路由器、代理分层、复盘 | 13 |
| [[sources/security-audit\|security-audit]] | 安全审计：本次产出、标准、可复用方法 | 12 |
| [[sources/learning-notes\|learning-notes]] | 学习与调研：已有索引入口 + 官方文档 | 11 |

**合计 71 条**（链路已校验：每条 `url` / `use_when` / `answers` / `verified` 四字段齐全）

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
