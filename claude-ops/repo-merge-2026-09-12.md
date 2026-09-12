---
title: 多仓库合并入库记录（2026-09-12）
aliases: [仓库合并记录, repo-merge-2026-09-12, 子库合并入库]
tags: [meta, ai/ops, incident]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# 多仓库合并入库记录（2026-09-12）

See also: [[HOME]] | [[AGENTS]] | [[CORRECTIONS]] | [[Claude-Ops-KB-Home]] | [[URL-REGISTRY]]

> [!abstract] 本文记录什么
> 把账号下**描述同类任务**的 7 个独立仓库合并进本知识库的一次性操作：映射关系、脱敏拦截、格式规范化、以及过程中的方法教训。
> 合并后本库 `.md` 从 261 篇增至 **370+** 篇（含 sources/ 与新增子库）。

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

**同时清除的真实密钥前缀**（事故复盘类文档大量引用，可与别处拼接还原）：

| 前缀 | 位置 |
|---|---|
| 一个 `sk-` 形态（4 位前缀，**不录于此**） | `hermes-ops/pi/architecture/` 三个文档，共 11 处 |
| 一个 `sk-` 形态（含截断引用写法） | 同上，含截断形态 `sk-<前缀>...<后缀>` |
| 一个 `sk-` 形态（已失效的旧网关密钥） | `ds2ox-proxy-retirement.md`（tokenra 旧密钥） |
| 两个 `ark-` 形态（事故复盘中的误用密钥） | 密钥泄漏事故复盘、调试复盘 |

**验证方法**：合并后**逐文件遍历远程全部 617 个文件**核对（不用 `git grep`，理由见第四节）。

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
> 本轮**三次**被它误导（`Users[\\/]28064`、`ark-[0-9a-f]{8}-`、`sk-or-v1`），
> 每次都说「远程有残留」，逐文件遍历后**均为 0**。
> **判定敏感内容必须用「逐文件取全文再匹配」，不能只信 `git grep`。**

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
