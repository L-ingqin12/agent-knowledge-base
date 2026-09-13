---
title: 来源登记 — 安全审计
aliases: [sources-security-audit, 安全审计来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 来源登记 — 安全审计

> [!abstract] 本页用途
> 存放「安全审计」主题的来源条目，供 [[URL-Lookup]] 检索。
> 可读版见 [[URL-REGISTRY#5-安全审计与漏洞复核]]。

## 本次审计产出（2026-09-12）

- 来源:: 本机系统漏洞分析报告
  use_when:: 复核本机整体暴露面与修复优先级
  url:: file:///%USERPROFILE%/dsh-vulnerability-analysis.md
  answers:: 6 严重 / 4 高危 / 7 中危；证据、影响边界、修复顺序、未确认项清单。更正（2026-09-13）：本条原 url 为 `file:///C:/%USERPROFILE%/dsh-vulnerability-analysis.md`（原表述）——`file://` URI 里的 `%USERPROFILE%` 不会被展开、点不开；两份报告实测均在 `%USERPROFILE%\` 下（Test-Path 为 True）
  authority:: 高
  verified:: 2026-09-12

- 来源:: 依赖漏洞专项审计
  use_when:: 复核依赖树版本、install hook、junction 农场结构
  url:: file:///%USERPROFILE%/dsh-dep-vuln-audit.md
  answers:: 18 包版本表、8 个 install hook、23 个确认不存在的包（同上更正：原写 `file:///C:/%USERPROFILE%/…`）
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

- 来源:: OWASP LLM01:2025 Prompt Injection
  use_when:: 设计 RAG / Agent 的检索内容防注入时；判定「RAG 是否已消除提示词注入」
  url:: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
  answers:: RAG 与微调**不能完全**缓解提示词注入（原文：they do not fully mitigate prompt injection vulnerabilities）；间接注入示例（篡改 RAG 所用文档）；原文另见 https://raw.githubusercontent.com/OWASP/www-project-top-10-for-large-language-model-applications/main/2_0_vulns/LLM01_PromptInjection.md
  authority:: 高
  verified:: 2026-09-13

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
  use_when:: 查 CVE 的官方 CVSS 与受影响产品（引用具体 CVE 时用 `/vuln/detail/<CVE-ID>` 具体路径）
  url:: https://nvd.nist.gov/
  answers:: CVSS 评分、CPE 匹配、参考链接。**可达性更正（2026-09-13）**：本复核环境实测 `https://nvd.nist.gov/vuln/detail/CVE-2020-14100` 返回 HTTP 200（页面为 JS 壳、正文需渲染），故「本审计环境不可达」属环境相关结论、不是站点属性——抓取失败时应标注**需人工确认**，不要默认不可用。同批四条入口（OWASP / CWE / ATT&CK / NVD）首页均可用
  authority:: 高
  verified:: 2026-09-12

- 来源:: Node.js inspector 文档（调试端口）
  use_when:: 评估本机**常开调试端口**的暴露面（例：Typora hook 常开 9229、Node 进程 `--inspect`）
  url:: https://nodejs.org/api/inspector.html
  answers:: inspector 调试端口**无鉴权**，连上即可 `Runtime.evaluate` 执行任意代码（等效取得该进程的 fs / child_process 能力）；结论：只应在排障期开启、验证完即关，并限制在本机回环地址
  authority:: 高
  verified:: 2026-09-13

## 本机审计可复用方法

- 来源:: ACL 判定方法
  use_when:: 判断某目录/文件是否真的「仅所有者可读」
  url:: wikilink://URL-REGISTRY
  answers:: **命令**：`icacls C:\`、`icacls D:\`；**典型输出**：C:\ 为 `BUILTIN\Users:(OI)(CI)(RX)` + `NT AUTHORITY\Authenticated Users:(OI)(CI)(IO)(M)`，D:\ 另有 `Authenticated Users:(M)`（直接赋权、**无 `IO`**）与 `Users:(OI)(CI)(IO)(GR,GE)`；**结论**：**不要假设用户目录默认安全**——两卷都给了 Users 读/执行、给了 Authenticated Users 修改权，差异不止继承标志：D:\ **根对象本身**就直接对 Authenticated Users 开写，C:\ 根对象只有继承型 `(IO)`。出处更正（2026-09-13）：本条原写「本机 C: 收紧而 D: 为 `Authenticated Users:(M)`+`Users:(RX)`」（原表述），而「**两卷相反**」四字实际在 [[URL-REGISTRY]]、不在本页，且该说法不成立。本结论属**本机配置类论断**，以现场 `icacls` 输出为准
  authority:: 高
  verified:: 2026-09-13

- 来源:: git 历史密钥泄露检查
  use_when:: 确认某密钥是否已进入提交历史
  url:: wikilink://URL-REGISTRY
  answers:: **命令**：`git log --all -S "<完整密钥串>" --oneline`（`-S` 按内容增减匹配，须给完整串）；**典型输出**：列出命中提交（无输出 = 未进历史）；**结论**：命中即已进历史、必须按泄露处置（**rotate 优先**）；`git filter-repo` / BFG 改写历史会影响协作者与既有克隆，需先公告，不能当默认动作
  authority:: 高
  verified:: 2026-09-13

- 来源:: 依赖扫描盲区判定
  use_when:: 对 `~/.dsh/profiles` 做扫描前
  url:: wikilink://URL-REGISTRY
  answers:: **命令**：先 `Get-Item <目录> | Select-Object LinkType,Target` 确认是否 junction，再扫主安装树或显式解析 Target；**典型输出**：该路径是 256 个 junction 的农场，`-Recurse` 返回 0；**结论**：**不得把 `-Recurse` 的 0 结果当「干净」**——0 是重解析点未被跟随的表现，必须换扫描策略后重跑
  authority:: 高
  verified:: 2026-09-13

> [!danger] 审计自身的两条纪律
> 1. **区分「结构性缺陷」与「当前可利用性」**——本机 D: 盘 ACL 松散是结构性缺陷，但本机仅一个启用账户，故当前不可利用。二者不可混为一谈。
> 2. **结论标注边界**——未做的验证（如令牌是否仍有效）必须写进「未确认项」，不得缺省为「安全」。

## A3 复核新增（2026-09-13）：CI 门禁与仓库权限

- 来源:: GitHub OAuth App scopes（`workflow` scope）
  use_when:: 推送 `.github/workflows/*` 被拒、要确认该用补 scope 还是绕道 SSH
  url:: https://raw.githubusercontent.com/github/docs/main/content/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps.md
  answers:: `workflow` scope *Grants the ability to add and update GitHub Actions workflow files*；**唯一例外**——同一文件、同一路径、同一内容已存在于其他分支时可无该 scope 提交
  authority:: 高
  verified:: 2026-09-13

- 来源:: GitHub Actions 触发事件参考（schedule）
  use_when:: 判断某条定时闸是否会**静默失效**（不是失败，而是根本没跑）
  url:: https://raw.githubusercontent.com/github/docs/main/content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md
  answers:: *In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days*；schedule 一节另有延迟提示（高峰期会晚跑）
  authority:: 高
  verified:: 2026-09-13

- 来源:: GitHub REST — Git Data API（trees 端点）
  use_when:: 排查 `POST /git/trees` 返回 404（本库坑 5）或被拒 payload 的原文归因
  url:: https://docs.github.com/en/rest/git/trees
  answers:: 待补——本环境该页**只返回导航壳、读不到正文**，故「官方未规定条目数上限」一类结论**未复核**（登记以备可访问时回查）
  authority:: 高
  verified:: 2026-09-13

## A4 复核新增（2026-09-13）：内核侧缓存缓解

> cs-base 簇（组成原理）回写时逐字核对的官方来源；`use_when` 写「什么时候要回查」。
> 二进制加固开关（PIE / 静态 PIE，GCC Link Options）登记在 [[sources/learning-notes|learning-notes]] 的主题页，此处不重复。

- 来源:: Linux 内核 PTI（页表隔离）文档
  use_when:: 论证 Meltdown/KPTI 类缓解的机制与代价，或在排查 TLB/PCID 相关性能问题时给出官方口径
  url:: https://docs.kernel.org/arch/x86/pti.html
  answers:: PCID 允许换页表时跳过整表 TLB 刷新；INVPCID 只失效非当前 PCID 的条目，不支持的机器只能失效当前 PCID；global page 被禁用的 TLB miss 增加量级「never exceeding 1%」；entry_64.S 中页表切换与 PCID 配合、以及「invalidated the wrong PCID」这类 bug 症状；引用 KAISER 与 meltdownattack 论文
  authority:: 高
  verified:: 2026-09-13

## 相关

- [[URL-REGISTRY]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 两条内部报告 url 写成 `file:///C:/%USERPROFILE%/…`——`file://` URI 不展开变量，点不开 | 改为绝对路径 `file:///%USERPROFILE%/dsh-vulnerability-analysis.md` 与 `…/dsh-dep-vuln-audit.md`（两份文件 Test-Path 为 True）；原写法保留在条目内的「更正」句 |
| 纠错 | ACL 条目把「两卷相反」当作本页结论，且与实测不符 | 保留原表述并标注更正：两卷都给 Users 读/执行、给 Authenticated Users 修改权，差异在继承标志（D:\ 根对象直接赋权 `(M)`、C:\ 根对象只有继承型 `(IO)`）；出处更正为 [[URL-REGISTRY]]；并标注属本机配置类论断（以现场 `icacls` 输出为准） |
| 补疏漏 | 「本机审计可复用方法」三条各只有一句话 | 各补三段式（命令 / 典型输出 / 结论）：`icacls` 判读直接赋权 vs 仅继承；`git log --all -S` 命中即需 rotate、`filter-repo`/BFG 需先公告；junction 农场不得拿 `-Recurse` 的 0 当结论 |
| 加厚 | NVD 的可用性口径、常开调试端口的暴露面均未登记 | NVD 条目补「本复核环境实测 200、抓取失败须标注需人工确认、引用具体 CVE 用具体路径」；新增 Node.js inspector 文档条目（调试端口无鉴权），供 Typora hook 类暴露面回查 |
| —（复核成立） | OWASP / CWE / ATT&CK / NVD 四条入口可用性 | 复核确认四条首页均可用，条目未删改 |

## C6 复核新增（2026-09-13）：密钥泄漏后的「清除」边界（历史重写 ≠ 已清除）

> C6 簇核 `pi-audit-plan` 的「GitHub Key 泄漏 — 已确认并清除」时发现：该结论只覆盖「分支可及历史已重写」，**不含 GitHub 缓存视图与他人 clone / fork**，属过度断言。

- 来源:: GitHub 官方文档 · 从仓库中移除敏感数据
  use_when:: 判断「force push 之后密钥算不算清干净」，或给泄漏响应写处置步骤与验收判据时
  url:: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
  answers:: 逐字「If you only rewrite your history and force push it, the commits with sensitive data **may still be accessible elsewhere**: In any clones or forks of your repository / Directly via their SHA-1 hashes in **cached views** on GitHub / Through any pull request that references them」⇒ 缓存视图需联系 Support 才能永久清除，且官方仅在「风险无法通过轮换凭据缓解」时协助；另给出响应**第一步**：「as a first step you need to revoke and/or rotate that secret… that may be sufficient to solve your problem. Going through the extra steps to rewrite the history and remove the secret **may not be warranted**」；推荐工具为 `git-filter-repo`（≥2.47 的 `--sensitive-data-removal`）
  authority:: 高
  verified:: 2026-09-13

- 来源:: git-filter-branch 手册（官方自述不推荐）
  use_when:: 历史重写选型时说明「为什么不该用 filter-branch」
  url:: https://man7.org/linux/man-pages/man1/git-filter-branch.1.html
  answers:: 开篇逐字警告「…has a plethora of pitfalls… **its use is not recommended**」⇒ 库内 `pi-audit-plan` 用 filter-branch 实施的历史重写属高风险路径，应改用 `git-filter-repo`
  authority:: 高
  verified:: 2026-09-13

见 [[CORRECTIONS]]、[[AGENTS]]。
