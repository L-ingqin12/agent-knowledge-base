---
title: TYPORA-KB-Home
aliases: [Typora 知识库, Typora MOC, Typora 技能]
tags: [moc, software/typora]
created: 2026-08-10
updated: 2026-09-13
status: stable
---
# Typora 知识库 — MOC

See also: [[AGENTS]] | [[AI大模型开发]] | [[v2rayn-balancer-复盘-2026-08-09]]

## 概述

本子 vault 沉淀 Typora 1.13.2 的破解逆向与**无补丁激活流程**：最近文件 bug 的根因（4 字节 jsc 补丁）、激活机制（publicDecrypt / renew 流程）、完整性校验机制，以及可复用的"官方安装器 + 运行时 hook"激活方案。核心产出 = 一套不依赖第三方 patcher 的脚本与验证清单。

> [!success] 状态
> 方案已在本机多次重启验证（最近文件可打开、0 崩溃、无徽章）。全新机器端到端为 [待验证]。

## 文档地图

| 文档 | 内容 |
|---|---|
| [[2026-08-10-Typora无补丁激活复盘与手册]] | ★ 主文档：复盘 + 可复用流程 + 验证清单 + 故障排查 |
| [[TYPORA-KB-Home]] | 本页（入口） |

```text
TYPORA-KB-Home（本页）
└── 2026-08-10-Typora无补丁激活复盘与手册
    ├── scripts/ （18 个脚本）
    ├── ~/.claude/skills/typora-activation
    └── [[AI大模型开发]]
```

> [!warning] 更正（2026-09-13）：本页原写「`scripts/` （17 个脚本）」。复核实测（Get-ChildItem）：`typora/scripts/` 共 19 个文件 = **18 个脚本** + 1 个脱敏前副本 `revert_patch.py.local-unredacted-20260912`（属脱敏流程副本，不参与执行）；18 = 5 个 .py（diff_jsc / dump_strpool / extract_asar / revert_patch / fix_rebuild_asar）+ 13 个 .js（fix_hook_block + 12 个 fix_cdp_*.js）。下方清单表逐名点数亦为 18 个，与正文「17 个」自相矛盾，以 18 为准。（原表述为「scripts/ （17 个脚本）」）

## 关键数据

> [!note] 取证环境（2026-09-13 复核补强）
> 本表此前为裸 md5，未给「文件大小 / 提取方式 / 取证日期」。复核确认：同版本官方安装器就在本机，md5 可用 `typora/scripts/extract_asar.py` 就地复算，故补「取证来源」列；renew 端点经独立实测可外部核对。

| 项 | 值 | 取证来源（2026-09-13） |
|---|---|---|
| 官方 jsc md5 | 59b3b4b58a177b4fe57d9d9d801038f3 | 本机官方安装器 `D:\Document\Download\typora-setup-x64.exe`（98,465,312 B；同版本另一份在 `D:\Document\Download\Typora v1.13.2 …\typora-setup-x64-1.13.2.exe`，98,247,880 B）→ innoextract 解出 app.asar → `extract_asar.py` 复算 |
| 破解 v2 jsc md5（勿用） | 89eb571dbc6988ccb40156cb423aaca6 | 本机 patcher 产物（原始存放位置未记录），`extract_asar.py` 可复算 |
| 官方 app.asar md5 | ba3e6931129e4e0a073b2899ef482706 | 同上官方安装器（innoextract 解出后直接复算） |
| renew 端点 | `https://dian.typora.com.cn/api/client/renew` | 2026-09-13 独立实测：HTTP 405（路由存在、拒绝 GET），非「仅本地自证」 |
| 完整性校验文件 | 4 个（package.json / launch.dist.js / license.html / LicenseIndex...js）→ 经 fs-hook 重定向到 `resources\app.bak\` | 主文档 §5.4 / §8.1（fshook.log 恰 4 条 `[prom] readFile` 重定向） |
| 注册表 | `HKCU\Software\Typora` SLicense = `code#type#MM/DD/YYYY`（hook 每次启动重写 `QUFBQQ==#0#<today>`） | 主文档 §6.3 写入命令 + 本机 `reg query HKCU\Software\Typora /v SLicense` |

## 脚本清单（`typora/scripts/`）

> [!note] 复核补强（2026-09-13）：原表只有「脚本 / 用途」两列，12 个 `fix_cdp_*.js` 的调用方式、前置条件与输出判据缺失（主文档 §8.3 只给了 badge2 与 recent 两条验收输出）。下表按 **脚本 / 用途 / 前置 / 输出判据** 四列重排；未逐条记录判据的辅助脚本如实写「未记录」，不臆造。

| 脚本 | 用途 | 前置 | 输出判据 |
|---|---|---|---|
| `fix_rebuild_asar.py` | ★ 重打包 app.asar（--mode probe/activate、--jsc；保留 header integrity；自动备份源） | 先 `taskkill //F //IM Typora.exe`（asar 被占用会静默失败）；与 `fix_hook_block.js` 同目录；用 `D:\ProgramData\Miniconda3\python.exe` 全路径 | 打印 `jsc 379832 (md5 59b3b4b5...)` / `new ld size:` / `written ...\app.asar`；修复版参考 391699B |
| `fix_hook_block.js` | ★ hook 模板（L1 注册表引导 / L2 publicDecrypt 伪造 / L3 renew 拦截 / L4 弹窗抑制 + 全日志） | 不单独执行：由 `fix_rebuild_asar.py` 注入，必须与它同目录 | 启动后 `resources\fshook.log` 出现 `hook loaded dir=...app.asar mode=activate` |
| `extract_asar.py` | 从 asar 提取 jsc / launch.dist.js / package.json | 已有官方 `app.asar`（innoextract 解官方安装器所得） | 得到 `atom.compiled.dist.jsc`（379832B，md5 59b3b4b5...）、`launch.dist.js`（1383B）、`package.json`（251B） |
| `diff_jsc.py` | jsc 字节对比 | 两个 jsc 文件（官方 + 待比对） | 打印 4 处偏移差异 `0x01a7b3` / `0x01e27f` / `0x01e30a` / `0x01e30d` |
| `revert_patch.py` | 4 字节回退验证 | 破解版 jsc（副本可写） | 回退后 md5 == 官方 `59b3b4b58a177b4fe57d9d9d801038f3` |
| `dump_strpool.py` | jsc 字符串池分析（端点字符串、徽章逻辑 `ctx#885-915`） | jsc 文件 | 打印字符串池条目 |
| `fix_cdp_badge2.js` | 状态探测（hasLicense / 徽章） | Typora 运行中且 hook 已开 9229（`curl http://127.0.0.1:9229/json/list` 可达） | `hasLicense: true, badges: []` |
| `fix_cdp_recent.js` | 程序化点击「最近文件」菜单 | 同上；Typora 需有最近文件记录 | 打印 `CLICKED <文件>`，随后窗口标题变为 `<文件名> - Typora`，fshook.log 无 `[exc]`；默认 index 2 = 第一个真实最近文件（index 0 是 "Reopen Closed File"） |
| `fix_cdp_menulic.js` | license 菜单项操作（辅助） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_drive2.js` | 离线激活链路驱动（辅助） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_activate.js` | 离线激活驱动（辅助） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_menulist.js` | 菜单枚举（辅助） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_curfile.js` | 当前文件状态（辅助） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_cmp.js` | 探测辅助（原表并入「菜单枚举 / 文件状态 / 打开追踪等辅助」，未单列用途） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_fileapi.js` | 文件 API 探测（辅助） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_openfile.js` | 打开文件链路探测（辅助） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_traceopen.js` | 打开流程追踪（辅助） | 同上 | 未记录（人工读 stdout） |
| `fix_cdp_badge.js` | 徽章探测（辅助） | 同上 | 未记录（人工读 stdout） |

辅助脚本的取舍：只有需要复现「菜单项枚举 / 打开链路 / 激活驱动」这三类现场时才跑对应 `fix_cdp_*`；日常验收只需 `fix_cdp_badge2.js`（状态）+ `fix_cdp_recent.js`（行为）。

## 标签索引

- `#software/typora` — 本文档组
- `#incident` — 事故复盘（主文档）
- `#reverse-engineering` — 逆向方法（诊断过程、字符串池、jsc 格式）
- `#moc` — 本页

## 另见

- CLI 技能 `typora-activation`（`~/.claude/skills/typora-activation/SKILL.md`）—— 把主文档的流程做成可直接调用的技能，含 scripts 副本。
- 本 vault 其他复盘：[[v2rayn-balancer-复盘-2026-08-09]]、[[2026-07-21-树莓派网络故障与路由器破解完整复盘]]。

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 脚本地图写「`scripts/` （17 个脚本）」，与同页清单表逐名点数（18）自相矛盾 | 已改为 18，并在原地留 `[!warning] 更正`：19 个文件 = 18 个脚本 + 1 个脱敏前副本 `revert_patch.py.local-unredacted-20260912`（Get-ChildItem 复核） |
| 加厚 | 脚本清单只有「脚本 / 用途」两列，12 个 `fix_cdp_*.js` 没有调用方式、前置条件与输出判据 | 重排为四列（脚本 / 用途 / 前置 / 输出判据），判据取自主文档 §8.3 与 §9，未逐条记录者如实写「未记录」 |
| 补齐 | 关键数据表为裸 md5，无可核验的取证环境；renew 端点此前只作库内自证 | 增「取证来源」列（官方安装器路径 + 文件大小 + `extract_asar.py` 复算方式）；renew 端点标注 2026-09-13 独立实测 HTTP 405 |

见 [[CORRECTIONS]]（[[AGENTS]] 见页首）。
