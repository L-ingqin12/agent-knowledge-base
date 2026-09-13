---
title: hermes-ops — 子库目录说明
aliases: []
tags: [ai/ops, meta]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# Hermes AI Agent 运维管理

pi/architecture/         架构设计 + 事故复盘 + 排查方法
pi/guardian/             6探针守护进程
pi/monitoring/           API用量监控  
pi/proxy/                代理 + systemd 单元
local/git-hooks/         Git pre-commit 敏感检测

> [!warning] 更正（2026-09-13）：`local/git-hooks/` 目录在本库**不存在**，敏感检测实体实际在子库根目录与主库侧；`pi/` 下实际内容见下表（原表述为「local/git-hooks/         Git pre-commit 敏感检测」）。

| 目录 / 位置 | 实际内容 | 性质 |
|---|---|---|
| `pi/architecture/` | 6 篇 .md（见下方索引） | 架构设计 / 事故复盘 / 排查方法 |
| `pi/guardian/` | `hermes-guardian.sh`（6 探针，665 行）、`proxy-guardian.sh` | 守护脚本 |
| `pi/monitoring/` | `api-usage-monitor.sh`（**14 字节 `404: Not Found` 占位残留，待补实体**，见 [[repo-merge-2026-09-12]] 遗留待办 6） | API 用量监控脚本 |
| `pi/proxy/` | `claude-proxy.service`、`claude-resilience-proxy.js` | 代理 + systemd 单元 |
| 子库根目录 | `hermes-guardian.sh`、`api-usage-monitor.sh`、`deploy-monitoring.sh`、`git-pre-commit-hook.sh`、`git-secrets-scan.sh` | 5 个脚本 |
| 敏感检测钩子（原 `local/git-hooks/` 的实际位置） | `git-secrets-scan.sh` · `git-pre-commit-hook.sh`（本子库根目录）· `scripts/claude-ops-deployments/.githooks/pre-commit`（主库侧） | Git pre-commit 敏感检测 |

> [!success] 残余复核（2026-09-13）：**`pi/monitoring/api-usage-monitor.sh` 的「待补实体」已就地补全（上表与「脚本实体」两处原表述保留不改）**。
> - **占位来源已查明**：该文件恰 **14 字节、无换行**，内容即 `404: Not Found`；源仓库同一路径**只有一次提交**（`d971466 refactor: Pi/本地目录分离 + 统一入口架构归档`）——即它是**源仓库侧就提交进去的残留**，不是本次合并时的下载事故。
> - **实体并未丢失，也无需联网**：同一子库根目录的 `api-usage-monitor.sh` 就是真实体（**166 行 / 5051 字节**，LF）；且同目录 `deploy-monitoring.sh` 部署的正是**根目录这一份**（`scp api-usage-monitor.sh …:/home/pi/`），`pi/monitoring/` 从来不是部署来源。**已于 2026-09-13 从根目录同步覆盖**（`/usr/bin/cp -f`，`cmp` 校验逐字节相同），故上文「14 字节占位残留」的描述**自本次起已过期**，保留仅为记录原状。
> - **复跑判据**：`wc -c claude-ops/hermes-ops/pi/monitoring/api-usage-monitor.sh` 应为 5051（而非 14）；`cmp` 与根目录同名文件应无输出。同步动作已过 `bash scripts/prepush-selfscan.sh --files <该文件>`（通过）。
> 详见 [[repo-merge-2026-09-12]] §六 待办 6 的同名结论。

## 收录边界与维护约定

- **收录**：Hermes Agent 在树莓派侧的运维实体——架构设计、事故复盘、排查方法（`pi/architecture/`）与配套脚本（guardian / monitoring / proxy）。
- **不收录**：通用 Claude Code 运维方法仍归主库 [[Claude-Ops-KB-Home]]，本页只作入口，不承载正文（[[AGENTS]] 五·五「一文档一问题」）。
- **分工**：与 `claude-ops/agent-resilience-tooling/`、`opencode-*` 子库无内容重叠——那些是通用工具与方法，本子库绑定树莓派 Hermes 实例。
- **新增内容前必做**：跑 `claude-ops/hermes-ops/git-secrets-scan.sh`，并确认 pre-commit 钩子已在本子库通过 `core.hooksPath` 生效（**是否已装上本记录未留证**，需现场 `git config --get core.hooksPath` 核对后再宣称防护生效）。
- **红线**：本子库曾为私有仓库、后转公开（见 [[repo-merge-2026-09-12]]），**禁止回填任何真实凭据 / 内网 IP / 订阅地址**；`proxy-guardian.sh` 的 `SUB_URL` 只从环境变量或 `~/.config/proxy-guardian/sub_url` 读取，缺失即 `exit 2`。

## 相关文档

**架构与排查（`pi/architecture/`，6 篇）**

| 文档 | 类型 |
|---|---|
| [[unified-architecture]] | 架构设计（总览） |
| [[pi-audit-plan]] | 排查方法 / 审计计划 |
| [[api-key-leak-postmortem]] | 事故复盘（密钥泄漏） |
| [[final-postmortem]] | 事故复盘（收束总结） |
| [[claude-debug-postmortem]] | 事故复盘（调试过程） |
| [[network-storm-prevention]] | 预防方案 |

**脚本实体**

- `pi/guardian/hermes-guardian.sh` · `pi/guardian/proxy-guardian.sh`
- `pi/monitoring/api-usage-monitor.sh`（占位残留，待补实体）
- `pi/proxy/claude-resilience-proxy.js` · `pi/proxy/claude-proxy.service`

**主库入口**

- [[Claude-Ops-KB-Home]]
- [[HOME]]
- [[repo-merge-2026-09-12]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 目录说明把 `local/git-hooks/` 列为子库目录，与实际不符；本页自称 `status: stable`，却被 repo-merge 记为「非知识文档、刻意跳过」 | 保留原目录树并就地标注实际结构表；`status` 由 `stable` 改为 `review`，并同步订正 [[repo-merge-2026-09-12]] 的跳过清单 |
| 补疏漏 | 未说明收录边界与维护约定 | 补「收录边界与维护约定」：收录范围、与主库分工、新增前跑 `git-secrets-scan.sh` 与 pre-commit 钩子、禁止回填真实凭据/IP（本子库曾私有后转公开） |
| 补疏漏 | 「相关文档」仅 3 条，读者无法从入口页发现子库内已有的事故复盘 | 扩成按目录分组的索引，列出 `pi/architecture/` 全部 6 篇与 guardian / monitoring / proxy 脚本实体，并标注复盘 vs 方法论 |
| 残余复核 | `pi/monitoring/api-usage-monitor.sh`「14 字节 `404: Not Found` 占位残留，待补实体」 | **结案并就地补全**：占位系源仓库 `d971466` 一次提交带进来的残留（非合并事故）；真实体在同子库根目录（166 行 / 5051 字节），且 `deploy-monitoring.sh` 部署的正是那一份。2026-09-13 已 `cp -f` 同步并以 `cmp` 校验逐字节相同，过 `prepush-selfscan`；复跑判据 `wc -c` 应得 5051 |

回链：[[CORRECTIONS]] · [[AGENTS]]
