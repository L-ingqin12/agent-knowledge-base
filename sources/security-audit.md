---
title: 来源登记 — 安全审计
aliases: [sources-security-audit, 安全审计来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-12
status: draft
---

# 来源登记 — 安全审计

> [!abstract] 本页用途
> 存放「安全审计」主题的来源条目，供 [[URL-Lookup]] 检索。
> 可读版见 [[URL-REGISTRY#5-安全审计与漏洞复核]]。

## 本次审计产出（2026-09-12）

- 来源:: 本机系统漏洞分析报告
  use_when:: 复核本机整体暴露面与修复优先级
  url:: file:///C:/%USERPROFILE%/dsh-vulnerability-analysis.md
  answers:: 6 严重 / 4 高危 / 7 中危；证据、影响边界、修复顺序、未确认项清单
  authority:: 高
  verified:: 2026-09-12

- 来源:: 依赖漏洞专项审计
  use_when:: 复核依赖树版本、install hook、junction 农场结构
  url:: file:///C:/%USERPROFILE%/dsh-dep-vuln-audit.md
  answers:: 18 包版本表、8 个 install hook、23 个确认不存在的包
  authority:: 高
  verified:: 2026-09-12

- 来源:: ds2ox-proxy 退役归档
  use_when:: 复核本地路由代理的安全缺陷与凭据处置
  url:: wikilink://ds2ox-proxy-retirement
  answers:: D1 无鉴权 / D2 无 Host 校验 / D3 抢占即劫持；残留复活路径
  authority:: 高
  verified:: 2026-09-12

## 既有审计与优化

- 来源:: 网络优化审计
  use_when:: 查历史优化/审计结论
  url:: wikilink://OPTIMIZATION-AUDIT
  answers:: 既有优化审计记录
  authority:: 中
  verified:: 2026-09-12

- 来源:: 权限与资源协议
  use_when:: 查权限/资源约束的既有约定
  url:: wikilink://claude-resource-protocol
  answers:: 资源与权限约束约定
  authority:: 中
  verified:: 2026-09-12

## 标准与知识库（外部）

- 来源:: OWASP
  use_when:: 需要 Web 安全分类与加固基线
  url:: https://owasp.org/
  answers:: Top 10、加固指南、测试指南
  authority:: 高
  verified:: 2026-09-12

- 来源:: MITRE CWE
  use_when:: 要给某缺陷定位弱点编号（CWE）
  url:: https://cwe.mitre.org/
  answers:: 弱点分类与定义
  authority:: 高
  verified:: 2026-09-12

- 来源:: MITRE ATT&CK
  use_when:: 要做攻击技战术映射（事件响应/威胁建模）
  url:: https://attack.mitre.org/
  answers:: 技战术矩阵与缓解措施
  authority:: 高
  verified:: 2026-09-12

- 来源:: NVD
  use_when:: 查 CVE 的官方 CVSS 与受影响产品
  url:: https://nvd.nist.gov/
  answers:: CVSS 评分、CPE 匹配、参考链接
  authority:: 高
  verified:: 2026-09-12

## 本机审计可复用方法

- 来源:: ACL 判定方法
  use_when:: 判断某目录/文件是否真的「仅所有者可读」
  url:: wikilink://URL-REGISTRY
  answers:: `icacls` 用法；**不要假设用户目录默认安全**——本机 C: 收紧而 D: 为 `Authenticated Users:(M)`+`Users:(RX)`
  authority:: 高
  verified:: 2026-09-12

- 来源:: git 历史密钥泄露检查
  use_when:: 确认某密钥是否已进入提交历史
  url:: wikilink://URL-REGISTRY
  answers:: `git log --all -S "<完整密钥串>"`，命中即说明已进历史
  authority:: 高
  verified:: 2026-09-12

- 来源:: 依赖扫描盲区判定
  use_when:: 对 `~/.dsh/profiles` 做扫描前
  url:: wikilink://URL-REGISTRY
  answers:: 该路径是 256 个 junction 的农场，`-Recurse` 返回 0 会被误读为「干净」
  authority:: 高
  verified:: 2026-09-12

> [!danger] 审计自身的两条纪律
> 1. **区分「结构性缺陷」与「当前可利用性」**——本机 D: 盘 ACL 松散是结构性缺陷，但本机仅一个启用账户，故当前不可利用。二者不可混为一谈。
> 2. **结论标注边界**——未做的验证（如令牌是否仍有效）必须写进「未确认项」，不得缺省为「安全」。

## 相关

- [[URL-REGISTRY]]
