---
title: 来源登记 — 依赖与 CVE
aliases: [sources-dep-cve, 依赖来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-12
status: draft
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
  use_when:: 需要 CVE 的披露日期与 CVSS 向量
  url:: https://ubuntu.com/security/CVE-XXXX-YYYY
  answers:: 披露日期、最近更新日期、CVSS 3 向量、优先级
  authority:: 高
  verified:: 2026-09-12

- 来源:: Alpine 安全追踪
  use_when:: 需要「完整版本区间匹配表」来判断已装版本是否落在范围内
  url:: https://security.alpinelinux.org/vuln/CVE-XXXX-YYYY
  answers:: 各分支的 min/max 版本区间、CPE、补丁 commit
  authority:: 高
  verified:: 2026-09-12

- 来源:: GitHub Advisory Database
  use_when:: 查 GHSA 原始公告，确认受影响范围与修复版本
  url:: https://github.com/advisories
  answers:: GHSA 公告全文、CVSS、受影响包与版本范围
  authority:: 高
  verified:: 2026-09-12

- 来源:: OSV.dev
  use_when:: 按包名跨生态查询漏洞
  url:: https://osv.dev/
  answers:: 多生态漏洞记录、受影响 commit 范围
  authority:: 高
  verified:: 2026-09-12

## 上游包元数据

- 来源:: npm registry 镜像
  use_when:: 判断某包「是否还有更高版本可升」——决定漏洞能否靠升级解决
  url:: https://registry.npmmirror.com/<package>
  answers:: dist-tags.latest、全部已发布版本列表
  authority:: 高
  verified:: 2026-09-12

- 来源:: Express 官方安全公告
  use_when:: 查 Express 生态（含 path-to-regexp）的安全发布说明
  url:: https://expressjs.com/blog/
  answers:: 受影响范围 + 修复版本 + GHSA 链接（三条 CVE 同批披露）
  authority:: 高
  verified:: 2026-09-12

## 聚合站（权威度较低，仅作交叉验证）

- 来源:: vuldb
  use_when:: 官方 tracker 未收录时的补充查询
  url:: https://vuldb.com/
  answers:: CVE 概要（**常返回 403 或无正文，勿单独依赖**）
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
  url:: file:///C:/%USERPROFILE%/dsh-vulnerability-analysis.md
  answers:: 已核实的 4 条公告判定（path-to-regexp / ws 均不受影响）
  authority:: 高
  verified:: 2026-09-12

- 来源:: 依赖漏洞专项审计
  use_when:: 复核依赖树结构与 junction 农场扫描盲区
  url:: file:///C:/%USERPROFILE%/dsh-dep-vuln-audit.md
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
