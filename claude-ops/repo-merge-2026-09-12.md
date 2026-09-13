---
title: 多仓库合并入库记录（2026-09-12）
aliases: [仓库合并记录, repo-merge-2026-09-12, 子库合并入库]
tags: [meta, ai/ops, incident]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 多仓库合并入库记录（2026-09-12）

See also: [[HOME]] | [[AGENTS]] | [[CORRECTIONS]] | [[Claude-Ops-KB-Home]] | [[URL-REGISTRY]]

> [!abstract] 本文记录什么
> 把账号下**描述同类任务**的 7 个独立仓库合并进本知识库的一次性操作：映射关系、脱敏拦截、格式规范化、以及过程中的方法教训。
> 合并后本库 `.md` 从 261 篇增至 **370+** 篇（含 sources/ 与新增子库）。

> [!note] 计数口径（2026-09-13 补）
> 本文三个数字的分母不同，**不可直接相减**——原记录未写明口径，故补此表：

| 数字 | 出现位置 | 分母 / 含义 | 复核方式 |
|---|---|---|---|
| 261 → 370+ | 本节 | 合并前后**全库** `.md` 总数（含 `sources/` 与新增子库），合并当日口径 | `git ls-files "*.md" \| wc -l` |
| 109 | §三 | 本批次**纳入格式规范化的候选 .md**（7 个源仓库内的知识文档） | `git show --stat afe4b7b` |
| 98 | §三 | 其中**实际写入 frontmatter** 的篇数 = 109 − 11 | 同上 |
| 86 文件 / 1130 行 | §五 `afe4b7b` | 该次提交的 **diffstat**（被改动文件数 / 行数），**不是篇数** | 同上 |

> **差额说明**：109 → 98 的 11 篇即 §三 的「刻意跳过」清单（该清单恰 11 条，自洽）。**98 → 86 的差额本记录未留逐项对应**，可能来自同一次提交中已含 frontmatter 文档的补充改动与非 `.md` 文件；三个数字的**统计时刻亦未记录**，如需精确对账应在原仓库跑 `git show --stat afe4b7b` 后逐文件比对。

---

## 一、合并映射

| 原仓库 | 目标位置 | 可见性变化 |
|---|---|---|
| `hermes-ops` | `claude-ops/hermes-ops/` | **私有 → 公开**（已脱敏） |
| `agent-resilience-tooling` | `claude-ops/agent-resilience-tooling/` | 公开 → 公开 |
| `opencode-unattended-guide` | `claude-ops/opencode-unattended-guide/` | 公开 → 公开 |
| `opencode-multi-agent-system` | `claude-ops/opencode-multi-agent-system/` | 公开 → 公开 |
| `agent-learn` | `ai-dev/agent-learn/` | 公开 → 公开 |
| `mcp-learn` | `ai-dev/mcp-learn/` | 公开 → 公开 |
| `lsp-learn` | `cs-base/lsp-learn/` | 公开 → 公开 |

**`hermes-ops` 特殊处理**：按用户要求**保留原仓库作为远程重定向引用**，供树莓派侧 Hermes Agent 定位新库。其 README 已改写为迁移指引（含映射表与「请勿在此新增内容」警告），推送于 `8d77749..b9c001d`。

**未合并（刻意保留独立）**：`aeon`（有 skill/hook 实现）、`my-agent`（独立框架）、`codebase-memory`（MCP server 实现）、`log_analysis_agent_system`（独立系统）。

---

## 二、脱敏拦截（本次最重要的部分）

> [!danger] 拦截到一处未发布的真实凭据
> `hermes-ops/pi/guardian/proxy-guardian.sh:26` 含 **xray/V2Ray 订阅地址**（host + 32 位路径 token），
> **等同 bearer 凭据**——可换取实时节点列表并消耗付费代理额度。
>
> 该仓库**原为私有**，内容从未公开。由子代理在合并前独立扫描发现，**推送前已拦截**。
> 处置：改为从 `SUB_URL` 环境变量或 `~/.config/proxy-guardian/sub_url` 读取，缺失即 `exit 2`。

> [!important] 私有 → 公开的门禁清单（2026-09-13 补）
> **公开前必须全部通过**：① 逐文件取全文扫描（不用 `git grep`，理由见 §四）② 四类形态各扫一遍——真实密钥前缀、订阅地址、内网 IP、本机用户名路径 ③ 命中项就地改为 env 变量或占位符 ④ 由**另一执行者独立复扫**一遍 ⑤ 命中矩阵写入本文件。
>
> **本次已执行的确认记录**：①–③ 在合并前完成；④ 由子代理独立扫描，发现上述订阅地址；⑤ 于**推送前拦截**，命中矩阵见下节。可见性变更落在 §一 映射表 `hermes-ops` 行（该动作不可逆）。
>
> **公开后仍生效的防护**：实体为 `claude-ops/hermes-ops/git-secrets-scan.sh`、`claude-ops/hermes-ops/git-pre-commit-hook.sh` 与主库侧 `scripts/claude-ops-deployments/.githooks/pre-commit`。**该钩子是否已在 hermes-ops 侧通过 `core.hooksPath` 装上，本记录未留证**——需现场 `git config --get core.hooksPath` 核对后，才可宣称「防护生效」。

**同时清除的真实密钥前缀**（事故复盘类文档大量引用，可与别处拼接还原）：

| 前缀 | 位置 |
|---|---|
| 一个 `sk-` 形态（4 位前缀，**不录于此**） | `hermes-ops/pi/architecture/` 三个文档，共 11 处 |
| 一个 `sk-` 形态（含截断引用写法） | 同上，含截断形态 `sk-<前缀>...<后缀>` |
| 一个 `sk-` 形态（已失效的旧网关密钥） | `ds2ox-proxy-retirement.md`（tokenra 旧密钥） |
| 两个 `ark-` 形态（事故复盘中的误用密钥） | 密钥泄漏事故复盘、调试复盘 |

**验证方法**：合并后**逐文件遍历远程全部 617 个文件**核对（不用 `git grep`，理由见第四节）。

> [!note] 扫描口径与命中数（2026-09-13 补）
> **617 的口径**：7 个源仓库的**远程文件总数**（扫描分母，含最终未合并的文件）；实际合并入库 **213 文件 / 45702 行**（§五 `4514e3e`）。逐仓库的 617 明细与扫描脚本本身**未随本记录入库**，如需复核对账应在各源仓库重跑同一正则集合。

| 敏感形态 | 命中数 | 处置 |
|---|---|---|
| xray/V2Ray 订阅地址（host + 32 位路径 token） | **1 处** | `pi/guardian/proxy-guardian.sh:26`，推送前拦截 → 改 `SUB_URL` 环境变量 |
| `sk-` 形态（4 位前缀） | **11 处** | `pi/architecture/` 三个文档，已清除 |
| `sk-` 形态（截断引用 `sk-<前缀>...<后缀>`） | 逐条见上方「同时清除的真实密钥前缀」表 | 该形态同时泄露首尾两段（§四·教训二） |
| `sk-` 形态（已失效旧网关密钥） | 逐条见上方「同时清除的真实密钥前缀」表 | `ds2ox-proxy-retirement.md`（tokenra 旧密钥） |
| `ark-` 形态（事故复盘中的误用密钥） | 2 类 | 密钥泄漏事故复盘、调试复盘 |
| `Users[\\/]<用户名>` / `ark-[0-9a-f]{8}-` / `sk-or-<版本>`（`git grep` 误报） | **均为 0** | 逐文件遍历复核，见 §四·教训三 |

> 正则集合按「**实际观测形态**」写（如 `sk-<前缀>*******` 里的星号不属于字符类），而非「密钥应该长什么样」——见 §四·教训一；宣布「0 残留」前必须先跑正向控制——见 §四·教训三。

---

## 三、格式规范化

按本库 [[AGENTS]] 规范处理，共 **98/109** 篇 .md 获得 frontmatter、双链与嵌套标签：

| 方式 | 内容 |
|---|---|
| frontmatter | 6 键（title/aliases/tags/created/updated/status），`created` 取文件内真实日期，无据可依时用合并日而非臆造 |
| 标签 | 一律嵌套 `category/sub`（`ai/ops`、`ai/agent`、`ai/skills`、`ai/tools`、`ai/learning`、`cs/toolchain`、`network/proxy`） |
| 双链 | 每篇 ≥3 条，**目标逐一用 glob 核验存在**；不添加指向不存在文档的链接 |
| Mermaid | 0 处（三组独立扫描均确认），无需迁移 |

**刻意跳过的 11 篇**（加 frontmatter 会**破坏功能**，不是遗漏）：

```
claude-ops/opencode-multi-agent-system/AGENTS.md          ← OpenCode 项目指令文件
claude-ops/opencode-multi-agent-system/slash-commands/*.md ← 斜杠命令定义（4 篇）
claude-ops/agent-resilience-tooling/implementations/skills/SKILL.md、safe-file-ops.md
claude-ops/hermes-ops/README.md                            ← 7 行目录图，非知识文档
ai-dev/agent-learn/MODULE_README.md、ai-dev/mcp-learn/examples/README.md、cs-base/lsp-learn/demo/README.md
```

> [!warning] 更正（2026-09-13）：清单中的 `claude-ops/hermes-ops/README.md` **已提升为正式子库首页**（带 6 键 frontmatter、`status: review`），不再是跳过对象，此行保留为合并当时的原始记录；另该文件实测 **22 行**并含 6 键 frontmatter，并非「7 行目录图」，跳过理由与实际不符（原表述为「claude-ops/hermes-ops/README.md                            ← 7 行目录图，非知识文档」）。**其余 10 篇仍按原样跳过**，判定原则不变。

> [!important] 判定原则
> `.opencode/agent/*.md` 与 `.opencode/command/*.md` 已自带**功能性 frontmatter**（`description`/`mode`/`tools`），
> 套用知识库字段会**覆盖这些键并污染使用者项目的上下文**。**功能配置文件不是知识文档。**

### 修复的 7 处悬空双链

合并文档引用了本库不存在的 HN 篇目，全部来自原 hermes-ops：

| 原链接 | 处置 |
|---|---|
| `[[claude-interruption-resilience]]` | → `[[claude-interruption-resilience-guide]]` |
| `[[claude-socket-error-elimination]]` | → `[[claude-socket-error-elimination-guide]]` |
| `[[claude-code-environment-architecture]]` | → `[[pi-vs-termux-guide]]`（[[MEMORY-INDEX]] 记载的最接近等价文档） |
| `[[occams-razor-principle]]`（2 处） | 去链接，改为「奥卡姆剃刀原则（本库暂无专文）」 |
| `[[claude-code-preflight-checklist]]`（2 处） | 去链接，改为「操作前强制检查清单（本库暂无专文）」 |

---

## 四、方法教训（已同步至 [[CORRECTIONS]] 的同类问题）

> [!warning] 教训一：脱敏正则要按「实际观测形态」写
> 初版用 `sk-<前缀>[A-Za-z0-9]{3,}` 匹配，**实测完全不生效**——文中写作 `sk-<前缀>*******`，
> **星号不属于该字符类**。
> **不能按「密钥应该长什么样」写正则，要按「它实际长什么样」写。**

> [!warning] 教训二：注意「截断引用」形态
> `sk-<前缀>...<后缀>`（前几位 + 省略号 + 后几位）只匹配长串会漏掉，
> 而它**同时泄露首尾两段**，比纯前缀更危险。

> [!warning] 教训三：`git grep` 与 PowerShell 正则方言不同，会误报
> 本轮**三次**被它误导（`Users[\\/]<用户名>`、`ark-[0-9a-f]{8}-`、`sk-or-<版本>`），
> 每次都说「远程有残留」，逐文件遍历后**均为 0**。
> **判定敏感内容必须用「逐文件取全文再匹配」，不能只信 `git grep`。**
> **且「0」本身也要受限**：宣布「0 残留」前先做**正向控制（positive control）**——在扫描范围内故意放一个已知能被命中的测试串，
> 跑完确认它**确实被匹配到**，再据以宣布干净；否则无法区分「真的干净」与「扫描器看不见目标」（[[AGENTS]] 六·五 第 3 条）。

> [!warning] 教训四：清单文件的 CRLF 会让循环静默全败
> `kb-push` 后自写的复制脚本读 CRLF 清单时，`read -r f` 保留的 `\r` 成为路径一部分，
> `cp` 全部失败而报 `copied=0`，脚本却以 `NOCHANGE` 静默退出。
> **跨 Windows/bash 传文件清单必须 `tr -d '\r'`。**

> [!note] 教训五：`Select-Object -Last N` 会缓冲输出，看起来像「命令卡死」
> 后台作业实际已完成，但输出被缓冲到最后才吐出，且**输出为空时会被误读为「没执行」**。
> 长任务应写**进度文件**，而非依赖管道输出。

---

## 五、本次提交序列

| commit | 内容 |
|---|---|
| `b9fd868` | ds2ox 脱敏归档 + URL 登记册三层结构 |
| `1ec5f7b` | CORRECTIONS 错误记忆库 + IP 脱敏补全 |
| `9506025` | 对齐历史复盘文件既有脱敏版 + 忽略本地未脱敏副本 |
| `c252eb7` | 对齐 network-analysis + 清除残留明文口令 |
| `3a7a36c` | router_ssh.sh 移除内嵌口令，改环境变量 |
| `0e0e8df` | 对齐 7 个分叉文件至既有脱敏版本 |
| `4514e3e` | **合并 7 个同类仓库入库**（213 文件 / 45702 行） |
| `f2cf872` | 补全远程残留脱敏（用户名路径 + 密钥前缀） |
| `9dda555` | 清除 dump_strpool.py 中的本机用户名路径 |
| `afe4b7b` | **格式规范化**（86 文件 / 1130 行） |

**hermes-ops 仓库**：`8d77749..b9c001d`（转为重定向引用 + 同步脱敏 ARK 密钥）

---

## 六、遗留待办

| # | 项 | 说明 |
|---|---|---|
| 1 | `router_ssh.sh` 口令的历史改写 | 口令**保留不轮换**，故 git 历史中该口令仍有效，需 `git filter-repo` 清除 29 个可达提交中的值（工具已装 `git-filter-repo` 2.47.0，机制已在副本验证） |
| 2 | 三篇 hermes 文档的独有细节 | 库内版更完整故未覆盖，但仓库版含 `WiFi 省电休眠` 根因、conntrack monitor 工作代码、路由器加固项等**库内缺失信息**，待人工并入 |
| 3 | 内容不一致 | `external-resources.md` / `verification-checklist.md` 与 `error-classification-system.md` 对 EEXIST/ENOENT/ENOMEM/EIO 的 layer/retryable 取值互相矛盾，两份滞后 |
| 4 | `agent-resilience-tooling/README.md` | 目录树尾部重复、两处冲突的文件计数（24/19） |
| 5 | 重复脚本 | `hermes-guardian.sh` 有两份，`pi/guardian/` 版第 628 行有多余 `exit 0` 使 L2–L5 恢复动作**不可达**；根目录版正确 |
| 6 | 14 字节占位文件 | `hermes-ops/pi/monitoring/api-usage-monitor.sh` 内容为 `404: Not Found`（下载失败的残留） |
| 7 | 未闭合代码块 | `opencode-remote-dispatch-design.md` ~394–401 孤立 systemd 片段 + 围栏不平衡 |
| 8 | `main-monitor/SKILL.md` | `description` 含未加引号的 `Triggers on: `，非严格合法 YAML，可能破坏严格加载器；且 `name` 与兄弟技能重复 |

**待办 1 的执行要素（2026-09-13 补）**：两条路线的取舍**尚未定**——**轮换口令**（低成本、立即消除风险，但需同步所有引用方与 `router_ssh.sh` 的读取来源）vs **改写历史**（彻底，但需 force-push、所有克隆方重新克隆）。若走改写：**时间盒 ≤1 个工作日**、执行人＝仓库所有者、完成判据为 `git log --all -S'<口令片段>' --oneline` **输出为空**；工具 `git-filter-repo` 2.47.0 已装且机制已在副本验证，故可先副本演练再对远端执行。**执行前该口令仍视为有效**，不得导出或复用。

**待办 5 的锚点更正（2026-09-13）**：结论成立，但应按**内容**锚定而非行号——缺陷是「**紧跟在 `SCORE` 日志（`:625`）与其后 `# 如果全部健康` 注释（`:627`）之后的那行无条件 `exit 0`（`:628`）**」，它使 `:629` 起 `if [ "$ESCALATION_LEVEL" -eq 0 ]` 与 L2–L5 的 `case` 分支**全部不可达**（原表述为「`hermes-guardian.sh` 有两份，`pi/guardian/` 版第 628 行有多余 `exit 0` 使 L2–L5 恢复动作**不可达**；根目录版正确」）。**行号并未漂移**：实测该副本仍为 665 行且 `:628` 正是该 `exit 0`；根目录版 655 行、`:628` 是 `if` 语句，唯一无条件 `exit 0` 在 `:595`（维护模式）。

> 顺带记录（2026-09-13）：pi 版的 `trigger_proxy_update()` 定义在 `:660`，位于 `main "$@"`（`:657`）调用**之后**且全文无引用，属死代码。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 三处文件计数口径不一（261→370+ / 98-109 / 86 文件·1130 行），未写明分母与统计时刻 | 补「计数口径」表分清分母与复核命令，说明 109→98 的差额＝11 篇跳过清单；98→86 本记录无逐项对应，标注需 `git show --stat afe4b7b` 对账 |
| 纠错 | §三 跳过清单把 `hermes-ops/README.md` 记为「7 行目录图，非知识文档」，与实际不符 | 保留原清单并就地更正：该文件实测 22 行、含 6 键 frontmatter，本次已提升为正式子库首页（`status: review`），其余 10 篇仍跳过 |
| 纠错 | §六 待办 5 以行号锚定 `hermes-guardian.sh` 的 `exit 0` 缺陷 | 改为按内容锚定（紧跟在 `SCORE` 日志之后的那行无条件 `exit 0`），并记下行号未漂移、根目录版对照与 `trigger_proxy_update()` 死代码 |
| 补疏漏 | §二 只记录「推送前已拦截」，未给私有→公开的门禁清单、已执行确认记录与公开后防护是否生效 | 补门禁清单（5 步）与本次已执行记录，并明确 pre-commit 钩子是否在 hermes-ops 侧生效**尚未留证**，不得据此宣称防护生效 |
| 补疏漏 | §二「617 个文件」无构成拆解、扫描脚本与各类形态命中数 | 补 617 口径（7 个源仓库远程文件总数，对照入库 213 文件）与逐形态命中矩阵（含误报项的 0），并标注扫描脚本未随记录入库 |
| 补疏漏 | §六 待办 1（口令历史改写）无优先级、执行人、完成判据 | 补时间盒（≤1 工作日）、执行人、完成判据 `git log --all -S'<口令片段>' --oneline` 为空；写明「轮换口令 vs 改写历史」取舍未定 |
| 加厚 | §四 教训三只给操作建议，「0 残留」结论本身缺约束 | 补正向控制（positive control）：扫描范围内预置已知测试串，确认能被命中后再宣布 0（[[AGENTS]] 六·五 第 3 条） |
