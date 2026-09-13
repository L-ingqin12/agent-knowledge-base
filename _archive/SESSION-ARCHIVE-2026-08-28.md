---
title: SESSION-ARCHIVE-2026-08-28
aliases: [会话归档20260828, Explorer优化归档]
tags: [meta, incident]
created: 2026-08-28
updated: 2026-09-13
status: stable
---

# SESSION-ARCHIVE-2026-08-28

> [!abstract] 会话 `fix-explorer-cpu`（`cc2a3123`，2026-08-28 开，08-30~31 归档续写）：**诊断并修复 Windows Explorer 100% 单核空转 → 文件夹打开卡顿**。完整复盘见 [[explorer-cpu-spin-postmortem-2026-08-28]]。期间用户永久放宽子代理 ox-alpha 确认规则（见 [[fan-out-subagent-pattern]]）。

## 一、任务

"协助优化 Windows explorer 的加载速度，文件夹打开加载过慢"。澄清：C: SSD + D: HDD 均慢；可禁壳扩展为 WPS/IDM/云盘/AutoCAD 钩子；范围=全量优化（UAC 提权）。

## 二、关键过程与坑

| 类别 | 内容 |
|------|------|
| 根因 | ShellIconOverlayIdentifiers 宿主进程死亡后轮询线程空转（坚果云/QQ/IDM）+ 云盘 CMH/命名空间/SyncRootManager 多路加载 |
| 关键反转 | **DISABLED_ 键名重命名阻止不了加载**——Explorer 按键值加载，真禁用=清空 (Default) 值；47/47 overlay 键清空后空转终止 |
| 方法改进 | 先停 explorer 再改注册表（消除 contention，12s 完成 8 键）；PS provider 通配符 `*` 挂死 → 全部改 reg.exe |
| 对抗注入 | QPCore NOT_STOPPABLE（FAILED 1052）→ 改名 QBShellIcon1341ee.dll；IDMan 优雅关闭 + force-stop |
| 工具坑 | MSYS bash 吞 `$_`（改用 .ps1）、`/f`→`F:/`（MSYS_NO_PATHCONV=1）、reg 搜索 `{` 报错（省略花括号） |

> [!note] 2026-09-13 复核回标（覆上表「关键反转」行，补证据链）：上文只给键名与「47/47 清空后终止」的结论，全文无完整注册表路径、也无清空前后的判定命令。补：
>
> | 项 | 内容 |
> |---|---|
> | 完整键路径 | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellIconOverlayIdentifiers`（32 位视图另查 `Wow6432Node\...` 同名路径；壳挂载点挂死记录另见 `HKLM\...\Classes\*\shellex`）——以现场 `reg query` 输出为准 |
> | 判定命令 | 改前 `reg query "<键路径>" > before.txt`；清空 `(Default)` 并重启 explorer 后再查一次，逐键比对 |
> | 最小反例 | 仅把键名改成 `DISABLED_xxx` 后重启：该 DLL 仍被加载（按键值加载）；把 `(Default)` 清空后重启：该 DLL 不再加载 |
> | 47 条清单 | 锚点在备份文件 `D:\SoftWare\ExplorerOptimize\backup-20260828\overlay_values_before.txt`（同目录 `check_now.ps1`、`gen_phase5`、`phase5_admin` 可重跑）；复盘 §八 是复发风险与排查顺序，47 条清单本身出自 §九 |

## 三、成果

- explorer CPU **100% 单核 → 2%**（0.20s/10s）；残留仅 Stardock（用户保留）
- 47 条 overlay 值清空、约 60 处 CMH/CLSID/SyncRootManager 禁用/清理，全部备份
- 产物：`D:\SoftWare\ExplorerOptimize\`（脚本+备份+双日志+命令文件）
- D: 盘并行调查（fan-out）：defrag 0%、SMART Healthy → 排除磁盘因素

> [!note] 2026-09-13 复核回标（对上面第 1 条，补测量口径）：「100% 单核 → 2%（0.20s/10s）」是结论，归档与复盘都没给测量命令，补：
>
> | 项 | 判据 / 命令 |
> |---|---|
> | 采样 | `Get-Process explorer` 取 CPU 秒差（间隔 10s 两次相减 ÷ 10 ≈ 单核占比），或 `typeperf "\Process(explorer)\% Processor Time" -sc 10` |
> | 观察窗口 | 空闲桌面静置 ≥10s；本次口径即 0.20s/10s ≈ 2% |
> | 判定阈值 | 单核占用 >50% 且持续 >10s 视为空转复发；<5% 视为已恢复 |
> | 复发信号 | 打开含云盘 / IDM / 坚果云同步目录时 CPU 尖峰，ShellIconOverlayIdentifiers 宿主进程被重新拉起 |

> [!note] 2026-09-13 复核回标（对上面第 3 条，正面对照项）：`D:\SoftWare\ExplorerOptimize\` 实测仍存在（Test-Path 为真），产物目录未丢失；复盘 §九 另给出子目录 `backup-20260828\` 与清空前原始值文件 `overlay_values_before.txt`，后续复查从这里取那 47 条。

## 四、归档链接

| 文档 | 说明 |
|------|------|
| [[explorer-cpu-spin-postmortem-2026-08-28]] | 完整事故复盘（根因/时间线/方法论/回滚） |
| [[Claude-Ops-KB-Home]] | MOC 事故复盘区新增条目 |
| [[fan-out-subagent-pattern]] | 本会话使用的并行调查模式 |

> [!warning] 遗留建议
> QPCore 服务仍 RUNNING（NOT_STOPPABLE）——建议禁用其 StartType 并重启以彻底阻断 QQ 浏览器注入复发；IDM 重开/WPS 更新/坚果云重开均为已知复发源（详见复盘第八节）。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 补疏漏 | 「DISABLED_ 重命名无效 / 47 条清空后终止」只有结论，无键路径与判定命令 | §二 回标：补完整键路径、清空前后 `reg query` 判定、重命名无效的最小反例；47 条清单锚定到 `D:\SoftWare\ExplorerOptimize\backup-20260828\overlay_values_before.txt`（复盘 §九） |
| 补疏漏 | 「explorer CPU 100% 单核 → 2%（0.20s/10s）」无计数器、采样窗口与复发信号 | §三 回标：补 `Get-Process` 秒差 / `typeperf` 采样命令、≥10s 观察窗口、>50% 复发阈值与尖峰信号 |
| 加厚 | 产物路径仅一行，未标子目录与备份锚点 | §三 回标：复核目录仍存在（Test-Path 为真），补 `backup-20260828\` 与清空前原始值文件 |

复核入口：[[CORRECTIONS]] | [[AGENTS]]
