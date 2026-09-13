---
title: Explorer 100% CPU 空转事故复盘
aliases: [explorer cpu spin, 文件夹打开慢, ShellIconOverlayIdentifiers 空转, 壳扩展优化]
tags: [incident, windows/explorer]
created: 2026-08-28
updated: 2026-09-13
status: stable
---

# Explorer 100% CPU 空转事故复盘

See also: [[Claude-Ops-KB-Home]] · [[AGENTS]] · [[fan-out-subagent-pattern]] · [[SESSION-ARCHIVE-2026-08-28]]

> 日期: 2026-08-28 00:11 ~ 02:26 (主会话 `cc2a3123`，08-30~31 归档) | 影响: 文件夹打开卡顿，explorer 恒定 100% 单核空转 | 结果: 2% 稳态，根因修复

---

## 一、事故现象

- 用户反馈「文件夹打开加载过慢」，C:（NVMe SSD）与 D:（5400rpm HDD）均受影响
- 实测 explorer.exe 进程 **10690s CPU 时间 / 约 1.2 天**，即恒定 100% 单核空转

> [!warning] 更正（2026-09-13）：两个数字不能同时成立（原表述为「10690s CPU 时间 / 约 1.2 天」，即恒定 100% 单核空转）
> 算术自证：`10690 s ÷ 3600 = 2.97 h`；1.2 天 = 103680 s。若真按「恒定 100% 单核」跑了 1.2 天，CPU 时间应在 `1.0×10^5 s` 量级——`106900 s = 1.237 天`，与 1.2 天吻合。故极可能是**漏写一位数字**（10690 → 106900），而不是「1.2 天」写错。
> 采集口径应同时记录两个互不冲突的量：`(Get-Process explorer).CPU`（累计 CPU 秒）与 `(Get-Process explorer).StartTime`（进程运行时长），正文写成「explorer 累计 CPU 时间 N s（≈M 天单核满载）＋运行时长 T」。

- 重启 explorer 后症状消失，但 **30-45 秒后空转复现**（桌面图标/云盘根初始化触发）

## 二、完整时间线（2026-08-28，日志时间）

| 时间 | 事件 | 阶段 |
|------|------|------|
| 00:11:30 | `fix_admin.ps1` v1 启动，**挂死在 PS 注册表通配符路径**（`HKLM:\...\Classes\*\shellex`，`*` 被当通配符全量枚举） | 初诊 |
| 00:22:59 | `fix_admin2.ps1`（reg.exe 版重写）: duba_64bit CMH ×5、nsemenu HKLM ×16（8 键 × 2 视图）、overlay MEGA×3 + NutstoreExt×5 + IDM×1 → DISABLED_；AutoCAD Approved 3 项放行；D: defrag 分析 **0% 碎片**、SMART 双盘 Healthy | 分层禁用 v1 |
| 00:23:55 | `fix_user2.ps1`: HKCU "Open With qingshellext" ×4、HKCU CLSID ×2、`FolderContentsInfoTip=0`、清 iconcache/thumbcache、重启 explorer | 分层禁用 v1 |
| 00:35:29 | `fix_user3.ps1`: HKCU nsemenu ×8 → DISABLED_ | 分层禁用 v2 |
| 00:56:31 | phase1: HKLM NutstoreExt CMH ×2 + NutstoreShellCopyHook；定位 QB overlay CLSID | 补漏 |
| 01:49:42 | phase2: HKCU Nutstore 命名空间 CLSID ×3 删除（ns_/nsicon 两处） | 补漏 |
| 02:06:17 | phase3b（关键方法变更）: **先停 explorer 再改注册表**，8 个 HKLM CLSID body（AcSignIcon {36A21736} + Nutstore {5D652B62-67}×6 + {CA799F4D}）12 秒完成，消除 registry contention | 深度清理 |
| 02:13:45 | phase4: wpscloudsvr=Stopped/Manual 确认；phase4 脚本挂起 → 杀 PID 1064 | 排障 |
| 02:18:23 | phase4b: 删除 16 个 DISABLED_nsemenu + 5 个 DISABLED_duba + duba CLSID {DDEA5705} + qingnse CLSID ×12（6 键 × 2 视图）+ SyncRootManager Nutstore ×3 | 深度清理 |
| 02:23:32 | test1: `sc stop QPCore` → **FAILED 1052 (NOT_STOPPABLE)**，QQProtect 服务无法停止 | 对抗注入 |
| 02:23:34 | test1: IDMan CloseMainWindow + force-stop，重启 explorer | 对抗注入 |
| 02:25:29 | `gen_phase5.ps1`: 枚举到 **51 个 overlay 键**，47 个待清空（保留 EldosIconOverlay-cbfs6 / EnhancedStorageShell / Optane 系列） | 最终清空 |
| 02:25:53 | phase5: **47/47 条 overlay 键值清空**（`reg add ... /ve /d "" /f`），重启 explorer | 最终清空 |
| 02:26:16 | PHASE5_DONE；后续 monitor/check_now 验证 | 验证 |

## 三、根因分析

> [!bug] 直接根因
> **ShellIconOverlayIdentifiers（覆盖图标处理器）的宿主进程死亡后，explorer 内残留的轮询线程持续空转**：坚果云/QQ/IDM 等 overlay handler 的 DLL 被加载进 explorer 后，其宿主进程已退出或未运行，轮询"云盘状态"的循环永不退出 → 恒定 100% 单核。

> [!warning] 更正（2026-09-13）：上条应记为**未验证假设**，不是已确认的 bug（原表述以 `[!bug] 直接根因` 写死该机制）
> 全文没有任何线程级证据：没有 ETW/WPA 采样、没有 explorer 的线程栈或 WaitReason、没有指名哪个 DLL 的哪个线程在烧 CPU。现有证据只有 §四 的模块清单、30-45s 延迟曲线与「重启即消失」，即**相关性**，不足以定机制。
> 取证路径（取不到就只保留相关性结论）：`wpr -start cpu` → 复现后 `wpr -stop spin.etl` → WPA 看 explorer 的 CPU 归属模块；或 Process Explorer → explorer 属性 → Threads 按 CPU 排序，读线程栈与 WaitReason。

叠加因素（多层壳扩展同时加载）：

| 层 | 内容 | 来源 |
|----|------|------|
| 覆盖图标 | MEGA ×3、NutstoreExt ×5、IDM、OneDrive ×7、DingSync ×3、WorkspaceExt、AccExtIco、AutoCAD 签名图标、QBOverlayIcon 等共 47 项 | 云盘/下载器/办公套件 |
| 右键菜单 CMH | duba_64bit ×5（WPS 毒霸）、nsemenu ×16×2 视图（坚果云）、qingshellext ×4（QQ 浏览器） | WPS/坚果云/QQ |
| CopyHook | NutstoreShellCopyHook | 坚果云 |
| 命名空间 CLSID | Nutstore ns ×3 组 + qingnse ×12 + duba CLSID {DDEA5705} + AcSignIcon | 云盘/QQ/WPS |
| SyncRootManager | Nutstore 3 条（HKLM+HKCU 隐藏加载点） | 坚果云 |
| 运行时注入 | IDMan.exe 注入 IDMShellExt64/IDMNetMon64；QQProtect(QPCore) 注入 QBShellIcon1341ee | IDM/QQ 浏览器 |

> [!note] 补疏漏（2026-09-13）：真正生效的只有字母序前 15 个
> 微软官方博客（Youhana，Learn 存档）原文：*Windows allows a maximum of 15 icon overlays in the system … the shell respects the first 15 icon overlays in the system (sorted in alphabetical order)*；同文给出 TortoiseSVN 用 `1TortoiseNormal` / `2TortoiseModified` 数字前缀把自家图标挤进前列的同类做法。
> 因此「47 项 overlay 全部清空」**不是唯一解**：真正生效的只是按字母序排进前 15 的那一批。可复用判据是**实际生效清单**（字母序前 15），而不是**键总数**。复现：`Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellIconOverlayIdentifiers'` 后按名字排序取前 15。
> 来源：https://learn.microsoft.com/en-us/archive/blogs/youhana/why-am-i-not-seeing-the-icon-overlays-in-shell-extensions-tfs-power-tools

> [!note] 空转的 30-45 秒延迟特征
> 重启 explorer 后前 15 秒 CPU≈0%（桌面刚起），**t+45s 左右达到峰值 124% 核心**，随后衰减。这是云盘壳扩展的延迟初始化模式——桌面图标/云盘根枚举完成时才加载 handler 并开始轮询，是区分"壳扩展空转"与"开机瞬时负载"的特征信号。

## 四、排查方法论（可复用）

1. **CPU 采样基线**：`check_now.ps1`（10s 采样 CPU delta + suspect DLL 列表）量化空转，0.20s/10s = 2% 为最终验收标准
2. **时间线采样**：`monitor.ps1` 重启 explorer 后 t+15/45/90/150s 各采样 6s，捕捉延迟加载曲线（发现 30-45s 特征的关键手段）
3. **模块列表取证**：explorer 进程的 DLL 清单 → 识别全部第三方 shell 扩展 → 分层禁用（HKLM→HKCU→注入型）
4. **二分排除**：先停宿主进程（IDMan）验证注入 DLL 是否加载；对 NOT_STOPPABLE 的 QPCore 用改名 DLL 阻断注入
5. **D: 盘并行调查**：fan-out 子代理只读分析（defrag 0%、SMART Healthy）→ 排除机械盘碎片因素，锁定纯壳扩展问题（见 [[fan-out-subagent-pattern]]）

> [!warning] 补疏漏（2026-09-13）：2% 缺归一化口径，「文件夹打开恢复正常」缺判据
> - **归一化口径**：原文只给 `0.20s/10s = 2%`，未写是否除以逻辑核数。算式应写成 `Δ(Get-Process explorer).TotalProcessorTime ÷ 采样秒数 ÷ 逻辑核数`；文档必须写明 2% 是「占单核」还是「占全部逻辑核」，否则与「100% 单核恒定」不可比。
> - **「恢复正常」的判据**：打开含 1000 个小文件的目录，首屏 <1s，且地址栏与状态栏无「正在处理」停留。
> - **可核性**：`check_now.ps1` / `monitor.ps1` 目前只在 `D:\SoftWare\ExplorerOptimize\`（库内不可核），应把采样原始输出随文档归档。

## 五、修复过程（分层）

> [!danger] 操作约束
> 所有提权脚本必须：先 `Stop-Process explorer` 再改注册表（消除 registry contention，12s 完成 8 键 vs 挂死）；禁用一律用 **reg.exe**（PS 注册表 provider 的 `*` 通配符会全量枚举挂死）；命令文件预生成（非提权脚本生成 `phase5_commands.txt`，提权脚本只执行）。

| Phase | 内容 | 结果 |
|-------|------|------|
| 1-3 | CMH/CopyHook/CLSID 全部 DISABLED_ 重命名（reg copy+delete） | 部分生效，overlay 未清空仍空转 |
| 3b-4b | 深度清理：命名空间 CLSID、CLSID body、SyncRootManager、DISABLED_ 残留键 | 显著改善 |
| 5 | **overlay 47 键值全部清空**（DISABLED_ 改名无效 → 必须清 `(Default)` 值） | 空转终止 |

## 六、验证结果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| CPU 采样 | 100% 单核恒定（10690s/1.2天，数值口径见 §一 更正） | **0.20s/10s = 2%** |
| 残留模块 | 云盘/QQ/IDM/WPS 全家桶 | 仅 Stardock 5 个 DLL（Fences/DesktopDock，用户保留） |
| monitor 曲线 | t+45s 峰值后不回落 | t+150s 后降至 10% 以下，稳态 2% |
| D: 盘 | defrag 0%、SMART Healthy | 无需操作（瓶颈非磁盘） |

> [!success] 最终稳态
> 47/47 overlay 清空 + 分层禁用 + DLL 改名后，explorer 稳态 2% CPU，文件夹打开恢复正常。Stardock（Fences/DesktopDock）按用户意愿保留，其延迟加载峰值正常回落。

## 七、关键结论（可复用知识）

> [!tip] DISABLED_ 前缀重命名 **阻止不了加载**
> Explorer 按键值（CLSID）加载覆盖图标/CMH，**键名无关紧要**。`DISABLED_` 改名只是"看不见"，DLL 照样加载。真禁用 = **清空 `(Default)` 值**（`reg add ... /ve /d "" /f`）或删除键。

- **云盘 DLL 的隐藏加载点**：SyncRootManager（HKLM+HKCU 两条腿）、CLSID\DefaultIcon（64/32 位双视图 WOW6432Node）、命名空间 CLSID——查壳扩展不能只看 ShellIconOverlayIdentifiers
- **注入型 DLL 处理顺序**：先优雅关闭宿主（CloseMainWindow）→ force-stop → 仍加载则改名 DLL（AppData 可写，Program Files 需提权）
- **QPCore (QQProtect) NOT_STOPPABLE**：只能改 StartType + 重启，无法运行中停止；对抗注入的唯一手段 = 改名 QBShellIcon1341ee.dll
- **先停 explorer 再改注册表**：消除 registry contention，批操作从"挂死"变"12 秒完成"
- **PS 注册表 provider 的 `*` 通配符**：`HKLM:\...\Classes\*\shellex` 触发全库枚举挂死 → 用 reg.exe 或硬编码路径
- **MSYS bash 坑**：内联 PowerShell 的 `$_` 被吞（改用 .ps1 文件）；reg.exe 的 `/f` 被 MSYS 转成 `F:/`（`MSYS_NO_PATHCONV=1`）

> [!note] 补疏漏（2026-09-13）：1052 的官方名称与出处（结论不变）
> 微软系统错误码页逐字：`ERROR_INVALID_SERVICE_CONTROL`，**1052 (0x41C)**，*The requested control is not valid for this service.*。括号里的 `NOT_STOPPABLE` 是本文自己的注解，不是官方错误名。解释方向无需修正：QPCore 未注册 STOP 控制、SCM 拒绝停止请求，故「运行中无法停止，只能改 StartType + 重启」成立。
> 来源：https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1000-1299-

## 八、复发风险与排查顺序

> [!warning] 已知复发源（按概率排序）
> 1. **QQ 浏览器重建 QBShellIcon DLL**（QPCore 仍 RUNNING）——QQ 浏览器下次启动时可能重新释放；根治需禁 QPCore 服务 StartType 并重启
> 2. **IDM 重新运行** → 重新注入 IDMShellExt64/IDMNetMon64
> 3. **WPS 更新** → 重注册 duba_64bit/nsemenu
> 4. **坚果云重开** → 重注册 SyncRootManager/overlay

**复发排查顺序**：`check_now.ps1` 看 explorer 模块列表 → 按上表对症处理（清 overlay 键值 / 改名 DLL / DISABLED_ 清空）。

> [!warning] 补疏漏（2026-09-13）：§八 只给方向，无命令、无读回、无副作用评估
> - **禁用 + 读回**：`sc config QPCore start= disabled` → `sc qc QPCore`（`START_TYPE` 应为 `DISABLED`）→ 重启后 `sc query QPCore`（`STATE` 应为 `STOPPED`）。
> - **复发检测判据**：explorer 模块列表不再出现 `QBShellIcon1341ee` / `IDMShellExt64` / `IDMNetMon64`，且 `check_now.ps1` **连续 3 天 <2%**。
> - **副作用（需人工回归）**：禁用 QPCore 后 QQ 浏览器 / QQ 的哪些功能受影响需逐个回归；改名后的 `QBShellIcon1341ee.dll.bak` 是否被升级重新写成 `.dll`，用文件时间戳 + 模块列表两项检测。

## 九、回滚与恢复

- **全部原始值已备份**：`D:\SoftWare\ExplorerOptimize\backup-20260828\`（60+ 个 .reg 导出 + `overlay_values_before.txt` + 双日志）
- 回滚方式：双击对应 .reg 导入，或按 `overlay_values_before.txt` 恢复 47 条 overlay 值
- 已改名 DLL：`QBShellIcon1341ee.dll.bak`（改回 .dll 即恢复注入）
- 脚本与命令文件均在 `D:\SoftWare\ExplorerOptimize\`（可重跑 gen_phase5 + phase5_admin 复现清空流程）

> [!warning] 补疏漏（2026-09-13）：只声明备份存在，未做过恢复演练，且备份路径在库外
> 回滚判据应落在「**读回的值与备份文件一致**」，而不是「备份文件存在」。最小演练：挑 1 个已清空的 overlay 键 → `reg import` 对应 .reg → `Get-ItemProperty` 断言 `(Default)` 等于 `overlay_values_before.txt` 中的原值 → 再复位清空。`backup-20260828\` 位于库外本机，库内无法核验，演练结论需回写本文。

## 十、相关文件

| 位置 | 内容 |
|------|------|
| `D:\SoftWare\ExplorerOptimize\` | 全部修复脚本（fix_*/phase*/test1_*/monitor/check_now/verify/gen_phase5） |
| `D:\SoftWare\ExplorerOptimize\backup-20260828\` | .reg 备份 ×60+、overlay_values_before.txt、log_admin.txt、log_user.txt、DONE 标记 |
| `%USERPROFILE%\AppData\Local\Tencent\QQBrowser\User Data\QBShellIcon\` | QBShellIcon1341ee.dll → .bak |
| 本会话 | [[SESSION-ARCHIVE-2026-08-28]]（对话归档） |

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | §一/§六 同写「10690s CPU 时间 / 约 1.2 天」并断言恒定 100% 单核 | 保留原表述并加更正：10690 s = 2.97 h，1.2 天对应 106900 s，判为漏写一位数字；补 `(Get-Process explorer).CPU` + `StartTime` 双量采集口径 |
| 补疏漏 | 全篇无「覆盖图标 15 个上限 + 字母序截断」规则，却把「清空 47 项」当必要且充分 | 补微软 Learn 存档博客规则（前 15 个按字母序生效、TortoiseSVN 数字前缀做法）；判据改为「实际生效清单」而非键总数 |
| 纠错 | §三 以 `[!bug] 直接根因` 写死「残留轮询线程空转」 | 保留原文，标注为未验证假设（无线程级证据），补 `wpr`/WPA 与 Process Explorer Threads 取证路径 |
| 加厚 | §四 只给 `0.20s/10s = 2%`，「文件夹打开恢复正常」无判据 | 补归一化算式（÷ 采样秒数 ÷ 逻辑核数）与界面判据（1000 小文件目录首屏 <1s、无「正在处理」） |
| 补疏漏 | §五/§七 未写 1052 的官方名称（结论本身正确） | 补 `ERROR_INVALID_SERVICE_CONTROL` (1052/0x41C) 与微软错误码页出处，结论不改 |
| 加厚 | §八 复发处置只有一句方向 | 补 `sc config/qc/query` 读回、连续 3 天 <2% 复发判据、QPCore 副作用人工回归项 |
| 加厚 | §九 只声明备份存在、未演练 | 补读回式演练（reg import → Get-ItemProperty 断言 → 复位），注明备份在库外不可核 |

依据与索引：[[CORRECTIONS]]
