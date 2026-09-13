---
title: 推送门禁与 CI 说明
aliases: [推送门禁, CI 说明, kb-gates, prepush-gates]
tags: [meta, ai/ops]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 推送门禁与 CI 说明

See also: [[AGENTS]] | [[CORRECTIONS]] | [[HOME]] | [[repo-merge-2026-09-12]]

> [!abstract] 本文解决什么
> 本仓库是**公开**的，且历史上出过凭据泄露。本页说明现有的**两道本地闸 + 三道 CI 闸**、
> 各自的职责边界、以及维护它们时必须知道的几个坑。
>
> 背景：2026-09-12 的合并工作中，「把敏感字面量写进自己产出的文档」**同日复发四次**。
> 结论是不能靠人记得检查——**必须落成机器约束**（[[CORRECTIONS]] C-013）。

---

## 一、门禁全景

| 位置 | 名称 | 类型 | 作用 |
|---|---|---|---|
| 本地 | `scripts/prepush-selfscan.sh` | **阻断** | 敏感内容扫描（密钥/私钥/订阅 token/明文口令） |
| 本地 | `scripts/validate-kb.py` | **阻断**（仅 ERROR） | frontmatter / 嵌套标签 / 双链 / 禁 Mermaid |
| 本地 | `.git/hooks/pre-push` | 串联上述两者 | 由 `scripts/install-hooks.sh` 安装 |
| CI | `security-scan.yml` | **阻断** | 工作树扫描 + **全历史**扫描 + 断言本地副本未入库 |
| CI | `markdown-validation.yml` | **阻断** | 与本地同一份 `validate-kb.py`，避免逻辑分叉 |
| CI | `link-check.yml` | 仅报告 | 每周巡检外链，写入 Job Summary |

> [!important] 为什么本地与 CI 都要有
> 本地闸**快**（9 秒）且能在 `git push` 前拦住；CI 闸**无法被绕过**——
> 网页端编辑、`git push --no-verify`、其他机器克隆后推送，都逃不过 CI。
> 二者是纵深防御，不是重复。

---

## 二、设计原则（都来自踩过的坑）

### 1. 只报「真凭据」，不报「已受管的内容」

本地工作副本含明文路径（`C:\Users\<name>\…`）与已脱敏占位符（`[已脱敏]` / `%USERPROFILE%`），
**这些不是扫描目标**——前者由推送时脱敏规则处理（`.git/kb-push-redactions`），后者本就是目标形态。
首版扫描器把它们都报出来，一次产生 **39 处误报**。

### 2. ERROR 与 WARN 必须分级

`validate-kb.py` 只把 **死链** 与 **Mermaid** 当 ERROR；缺键、少链接、扁平标签属**既有约定差异**，仅记录。
若把历史遗留差异也算失败，门禁会长期飘红 → 被习惯性忽略 → 门禁失效。
见 [[CORRECTIONS]] C-014：**门禁的价值等于其信噪比，而非覆盖度**。

### 3. 豁免必须显式、可见、可审计

文档需要举例，但举例不应触发告警。同一行加 `<!-- scan-ignore: 理由 -->` 即豁免：
行内可见，可被审阅，而不是靠模糊正则去「猜」哪些是示例。
**不允许**用宽泛排除规则——真凭据也会被猜成示例而漏掉。

> [!bug] 规则与文档会互相命中（本页即例证）
> 本页原先逐字写出了「某个命令 + `-p` + 引号串」的示例，结果**被自己的规则拦下**。
> 处置优先级：**① 改措辞（用类别描述）→ ② 换行拆开关键字 → ③ 加 `scan-ignore` 显式豁免**。
> 本例选了 ①——因为要表达的是「`-p` 是通用参数」，本来就不需要写出具体命令。

### 4. 检查的判据必须与缺陷同形，匹配范围要窄

- 引号参数 `-p` **不是** 某类命令专属：交互式 CLI 传 prompt、测试框架传文件模式都用它
  ⇒ 规则必须限定在确切的命令上下文里，且**词边界要严**（宽松写法曾误报）
- 「长 hex 路径」**不能**判定订阅 URL：GitHub `/commit/<40hex>`、NeurIPS 论文 `/hash/<32hex>` 全都满足
  ⇒ 改用**有语义**的判据（订阅语义域名 + 已知服务域名）
- 检查规则会被**自己的解释性注释**误报（`grep -E` 下 `(?!…)` 前瞻还会**静默失配**）

---

## 三、维护本仓库的门禁时必须知道的坑

> [!danger] 坑 1：推送 `.github/workflows/*` 需要 `workflow` scope
> `gh` 的 OAuth token（`gho_`）scope 为 `admin:public_key, gist, read:org, repo`，**不含 `workflow`**。
> 用 HTTPS + 该 token 推送会被拒：
> ```
> ! [remote rejected] refusing to allow an OAuth App to create or update workflow
>   `.github/workflows/xxx.yml` without `workflow` scope
> ```
> **解法（已验证可用）**：改用 **SSH 推送**，不受该限制
> ```bash
> git push git@github.com:L-ingqin12/agent-knowledge-base.git main
> ```
> 另注：Contents API 同样无法创建 workflow（同一 scope 限制）。
>
> **更正（2026-09-13）**：解法不应**只有** SSH，首选是补齐 scope。官方 scopes 文档确认 `workflow` scope *Grants the ability to add and update GitHub Actions workflow files*，并给出**唯一例外**（同一文件、同一路径、同一内容已存在于其他分支时可无该 scope 提交）。因此：
> 1. **首选**：给 token 补 scope —— `gh auth refresh -s workflow`，或换用带该 scope 的 token；
> 2. **SSH 只是绕过**：后续若改用 HTTPS + 同一 token 做自动化，会再撞同一堵墙；
> 3. 上一条「Contents API 同样无法创建 workflow」应改写为「**缺 `workflow` scope 时**该 API 无法写入 `.github/workflows/*`；补齐 scope 后可写入」。
>
> 来源：<https://raw.githubusercontent.com/github/docs/main/content/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps.md>

> [!danger] 坑 2：`kb-push.sh` 不推送 `.github/`
> 它的变更集只含显式指定的文件，且默认流程不覆盖 `.github/`。
> 因此 CI 工作流的增改**必须**用 SSH 直推，或先 `git add .github && git commit` 再推。

> [!warning] 坑 3：Git Bash 下的 `python` 会命中 Windows Store 存根
> `command -v python` 返回 `…/WindowsApps/python`，它**不执行任何脚本**，实测返回 **exit 49**。
> `scripts/install-hooks.sh` 因此按「显式可用」顺序解析解释器：
> `$KB_PYTHON` → `/d/ProgramData/miniconda3/python.exe` → PATH 上的 python3/python，
> 且每个候选都要通过 `-c 'import sys'` 探测。

> [!warning] 坑 4：`/tmp` 在 Git Bash 与 Windows 程序间不一致
> Git Bash 的 `/tmp` 映射到 Windows TEMP，而 `gh.exe` / `python.exe` 按 Windows 语义解析，
> 传路径给它们会「找不到文件」。**中间文件放仓库内 `.git/` 下**（该目录永不推送）。

> [!warning] 坑 5：GitHub Git Data API 的 tree 端点在完整 payload 上会 404
> blob 上传全部成功、小 payload（1–2 条目）的 tree 创建也成功，但 18 条目的 payload 持续 404。
> 现象稳定、原因未定。**可靠替代是 Contents API 逐文件 PUT**（自动建目录，代价是多次提交）。
> 另：**不要复用上一次会话创建的 blob SHA**——未被引用的对象会被回收，引用它会 404。
>
> **更正 / 补疏漏（2026-09-13）**：本坑属**不可外部核验的本机观察**（已尝试对照官方 REST 文档，本环境只返回导航壳、读不到正文，故「官方未规定条目数上限」这半句标为**未复核**）。「现象稳定」这种暗示普遍性的措辞应收窄为「在本机该 payload 形状上可重复复现」。可补的排查动作：
> 1. 打印被拒请求的**完整 body 与响应体原文**——404 的 `message` 通常直接指出缺失的 `base_tree` 或无效 sha；
> 2. 核对每个条目的 sha 是否来自**同一仓库且未被回收**（与上句同一线索）；
> 3. 对照上文提到的 Contents API 逐文件 PUT——并明确**这是 workaround，不是修复**。
>
> 来源：<https://docs.github.com/en/rest/git/trees>（正文未取到，仅登记）

---

## 四、日常用法

```bash
# 安装/更新钩子（克隆后做一次）
bash scripts/install-hooks.sh

# 手动跑两道闸
bash scripts/prepush-selfscan.sh --self-test      # 敏感内容（--self-test 自证脚本自身无凭据）
python scripts/validate-kb.py                     # 格式校验

# 只扫改动
bash scripts/prepush-selfscan.sh --staged
bash scripts/prepush-selfscan.sh --files a.md b.md

# 明确知情要绕过（仅限紧急）
git push --no-verify
```

**退出码**：`prepush-selfscan.sh` 0=通过 1=命中；`validate-kb.py` 0=通过 1=有 ERROR。

> [!warning] 补疏漏（2026-09-13）：两道本地闸的运行依赖，以及「依赖缺失即放行」
> §一 把本地闸标为**阻断**，但读实现（`scripts/install-hooks.sh`、`scripts/validate-kb.py`）可见落差：
> - `validate-kb.py` **只用标准库**（`argparse`/`json`/`os`/`re`/`pathlib`），不存在 pip 依赖；
> - 真正的依赖是**解释器**：`$KB_PYTHON` → `/d/ProgramData/miniconda3/python.exe` → PATH 上的 `python3`/`python`，每个候选都要通过 `-c 'import sys'` 探测（与上文坑 3 一致）；
> - **失败方向是 fail-open**：生成的 pre-push 钩子在找不到可用 Python 时**只打印一行**「未找到可用 Python，跳过格式校验（可设 `KB_PYTHON` 指定）」并继续 ⇒ 会出现「以为有闸、其实没闸」。
>
> 建议（本次未改代码，仅登记）：① 钩子改 **fail-closed**（异常或缺解释器一律阻断）；② 端到端验收——故意引入死链与假密码，断言两次 push 分别被拦下并贴出退出码；③ 依赖自检：`python scripts/validate-kb.py && bash scripts/prepush-selfscan.sh --self-test`。
>
> 来源：仓库内实现（`scripts/install-hooks.sh`、`scripts/validate-kb.py`）

---

## 五、已知残余风险

| 项 | 说明 |
|---|---|
| 订阅 URL 的语义判据有漏报面 | 「域名无订阅特征 + 纯 hex 路径」的真实订阅源不会被抓；由提交前人工过一眼新增外链补 |
| `link-check.yml` 不阻断 | 外链会限流/宕机/地域不可达，硬门禁会被噪声淹没；改为每周巡检 + 报告 |
| 历史扫描只看 tip+全历史模式 | 不做相似度检测，变形/编码后的凭据可能漏过 |
| 本地未脱敏副本 | `*.local-unredacted-*` 由 `.gitignore` 排除，CI 有一条断言防误入库；但仍靠 gitignore 生效 |
| 定时工作流可能被自动禁用 / 丢跑 | 公开仓库**60 天无活动**时 scheduled workflow 会被 GitHub **自动禁用**，且高峰期定时任务会延迟 ⇒ 「每周巡检」可能根本没跑 |

> [!warning] 补疏漏（2026-09-13）：「不阻断」与「不运行」是两件事
> §一 把 `link-check.yml` 定为「仅报告：每周巡检」，§五 的理由（外链会限流/宕机/地域不可达，硬门禁会被噪声淹没）成立，但漏了 **scheduled workflow 的制度性风险**：官方原文——*In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days*，且该节带 schedule-delay 提示（高峰期会延迟）。本库 `.github/workflows/link-check.yml` 正是 `cron '0 2 * * 1'` 的 scheduled workflow、仓库公开 ⇒ 这条闸**可能静默停止**，而本页的设计前提恰是「不能靠人记得检查」。
> 可验证自检（建议补进仓库）：① 每次成功运行把**时间戳**写入 artifact 或分支；② 超过 N 天（建议 10 天）无新时间戳即视为失效并告警；③ 把「不阻断」与「不运行」分成两种状态分别上报。
>
> 来源：<https://raw.githubusercontent.com/github/docs/main/content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md>

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 坑 1 把「SSH 推送」当作唯一解，未给补 `workflow` scope 的官方正解 | 保留原解法并补：`gh auth refresh -s workflow` 为首选、SSH 只是绕过、Contents API 的表述改为「缺 scope 时不可写入」（GitHub scopes 官方文档） |
| 补疏漏 | §一/§五 只说 link-check「仅报告」，未考虑 scheduled workflow 会被静默禁用 | 补 §五 风险行与自检方案（时间戳回写 + 超期告警），并区分「不阻断」与「不运行」（GitHub Actions 触发事件官方文档） |
| 纠错 | 坑 5 的「现象稳定」暗示普遍性，且未给排查动作 | 收窄为「本机该 payload 形状可重复复现」，标注官方 REST 页未取到正文（未复核），补三条排查动作并明确 Contents API 是 workaround |
| 加厚 | §四 未写两道闸的运行依赖，也未说明依赖缺失时的失败方向 | 补依赖清单（仅标准库 + 解释器探测链）与 **fail-open 实测行为**，给出 fail-closed 与端到端验收建议（仓库内实现为据） |

回链：本文 See also 已含 [[CORRECTIONS]] 与 [[AGENTS]]，未重复添加。
