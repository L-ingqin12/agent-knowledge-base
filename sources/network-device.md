---
title: 来源登记 — 网络与设备
aliases: [sources-network-device, 网络设备来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 来源登记 — 网络与设备

> [!abstract] 本页用途
> 存放「网络与设备」主题的来源条目，供 [[URL-Lookup]] 检索。
> 可读版见 [[URL-REGISTRY#4-网络与设备]]；子库入口 [[Network-KB-Home]]。

## 子库入口与手册

- 来源:: 网络子库 MOC
  use_when:: 不知道网络问题该看哪篇时的入口
  url:: wikilink://Network-KB-Home
  answers:: 网络子库全部文档地图
  authority:: 高
  verified:: 2026-09-12

- 来源:: 路由器完整能力手册
  use_when:: 查路由器型号/固件/SSH 接入方式
  url:: wikilink://ROUTER-FULL-CAPABILITY
  answers:: R4CM（内网 `192.168.x.x`，IP 已脱敏——`[IP已脱敏]` 是脱敏占位、不是字段名，原文把型号/IP/固件/账户挤成一行）fw 2.14.87、SSH 以 `root` 登录 22 端口、需放宽 legacy crypto。**复现要素（2026-09-13 补）**：① 账户 `root`、端口 `22`；② legacy 算法必须显式放宽，示例 `ssh -o KexAlgorithms=+diffie-hellman-group1-sha1 -o HostKeyAlgorithms=+ssh-rsa root@<内网地址> -p 22`（算法名以 `ssh -vv` 协商日志里的实际 offer 为准，本页不代填）；③ 依据见本页「OpenSSH Legacy Options」条目
  authority:: 高
  verified:: 2026-09-12

- 来源:: 小米路由器 API 认证与利用
  use_when:: 要通过 API 而非 SSH 操作路由器
  url:: wikilink://参考-小米路由器API认证与利用
  answers:: 小米路由器 API 的认证流程
  authority:: 高
  verified:: 2026-09-12

- 来源:: 网络路由与代理排障
  use_when:: 路由/代理分层排障
  url:: wikilink://参考-网络路由与代理排障
  answers:: 路由与代理的排障路径
  authority:: 中
  verified:: 2026-09-12

- 来源:: VPN 代理诊断与优化
  use_when:: 代理连通性/速度异常的诊断
  url:: wikilink://参考-VPN代理诊断与优化
  answers:: VPN/代理诊断与优化方法
  authority:: 中
  verified:: 2026-09-12

## 架构与日常操作

- 来源:: 网络架构说明
  use_when:: 要理解本机网络的整体拓扑与代理分层
  url:: wikilink://ARCHITECTURE
  answers:: 网络架构设计（v2rayN + xray 26.3.27，端口 10808）
  authority:: 高
  verified:: 2026-09-12

- 来源:: 网络日常操作指南
  use_when:: 执行日常网络操作
  url:: wikilink://GUIDE
  answers:: 日常操作步骤、配置脚本用法
  authority:: 高
  verified:: 2026-09-12

- 来源:: 网络优化总结
  use_when:: 回顾已完成的优化项
  url:: wikilink://FINAL-SUMMARY
  answers:: 优化成果与关键数据
  authority:: 中
  verified:: 2026-09-12

## 复盘与专项

- 来源:: 树莓派网络故障与路由器破解复盘
  use_when:: 处理路由器故障或需要完整排查复盘
  url:: wikilink://2026-07-21-树莓派网络故障与路由器破解完整复盘
  answers:: 完整故障链路与破解过程
  authority:: 高
  verified:: 2026-09-12

- 来源:: 路由器深度探索
  use_when:: 需要挖掘路由器未公开能力
  url:: wikilink://ROUTER-DEEP-EXPLORATION
  answers:: 路由器的深层能力探索记录
  authority:: 中
  verified:: 2026-09-12

- 来源:: 路由器优化
  use_when:: 优化路由器本身的配置
  url:: wikilink://ROUTER-OPTIMIZATION
  answers:: 路由器侧优化项
  authority:: 中
  verified:: 2026-09-12

- 来源:: 远程视频监控方案
  use_when:: 配置路由器的远程监控
  url:: wikilink://ROUTER-VIDEO-REMOTE-MONITOR
  answers:: 远程监控配置方法
  authority:: 低
  verified:: 2026-09-12

- 来源:: v2rayN 负载均衡复盘
  use_when:: 排查分流/负载均衡问题
  url:: wikilink://v2rayn-balancer-复盘-2026-08-09
  answers:: 负载均衡配置与失效模式
  authority:: 中
  verified:: 2026-09-12

> [!warning] 关联安全项（2026-09-12 审计）
> 本机 `~/.ssh/router_ssh.sh` 含**明文设备口令**，`router_root` 与 `id_rsa` 均为**未加密私钥**，且脚本设了 `StrictHostKeyChecking=no`。
> 路由器凭据应优先轮换——详见 `%USERPROFILE%\dsh-vulnerability-analysis.md` 的 S4 项（原文写 `%USERPROFILE%\dsh-vulnerability-analysis.md`；`%USERPROFILE%` 作为路径需人工替换，不是可点链接，故已补绝对路径）。
>
> **最小轮换清单与验收判据（2026-09-13 补，原文只有结论、无处置路径）**
> 1. 改路由器 `root` 口令 → 同步更新 `~/.ssh/router_ssh.sh`，口令不再明文落盘（改从凭据管理器/环境变量读）；
> 2. 给 `router_root` / `id_rsa` 加口令，或换新密钥并删除旧私钥；
> 3. `StrictHostKeyChecking=no` 改 `accept-new` 并落 `known_hosts`；
> 4. **验收**：新会话免密登录成功，旧口令 / 旧私钥登录失败；
> 5. 轮换后在 `dsh-vulnerability-analysis.md` 的 S4 项回写复核日期（本页尚未回写——待人工执行）。

## C4 复核新增（2026-09-13）：Windows 壳扩展与内核网络参数

- 来源:: 微软存档博客：覆盖图标处理器 15 个上限与字母序截断
  use_when:: 排查 Windows 文件夹覆盖图标过多 / 壳扩展空转；判断「清空全部 overlay」是否必要
  url:: https://learn.microsoft.com/en-us/archive/blogs/youhana/why-am-i-not-seeing-the-icon-overlays-in-shell-extensions-tfs-power-tools
  answers:: 系统最多 15 个 icon overlay，shell 只认**字母序前 15 个**；TortoiseSVN 用 `1TortoiseNormal` / `2TortoiseModified` 数字前缀挤进前列的同类做法
  authority:: 高
  verified:: 2026-09-13

- 来源:: Windows 系统错误码 1000-1299（微软官方）
  use_when:: 解释服务控制类失败码（如 `sc stop QPCore` 返回 1052）
  url:: https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1000-1299-
  answers:: `ERROR_INVALID_SERVICE_CONTROL` = 1052 (0x41C)，*The requested control is not valid for this service.*——「QPCore 只能改 StartType + 重启」的官方依据
  authority:: 高
  verified:: 2026-09-13

- 来源:: 内核 nf_conntrack sysctl 文档
  use_when:: 判定「路由器/NAT 连接表饱和」时取证（conntrack 满 → 新连接与 DNS 被丢）
  url:: https://docs.kernel.org/networking/nf_conntrack-sysctl.html
  answers:: `nf_conntrack_count` 只读、`nf_conntrack_max` 默认为 buckets 数、`nf_conntrack_tcp_timeout_time_wait` 默认 120 s；路由器侧计数 / 上限 / 超时的读取依据
  authority:: 高
  verified:: 2026-09-13

- 来源:: 内核 ip-sysctl（TCP keepalive 与 fin_timeout 默认值）
  use_when:: 计算死连接判死时间，或核对 keepalive 调优前后的基线数字
  url:: https://docs.kernel.org/networking/ip-sysctl.html
  answers:: `tcp_keepalive_time` *Default: 2hours*、`tcp_keepalive_probes` 9、`tcp_keepalive_intvl` 75 sec、`tcp_fin_timeout` *Default: 60 seconds*
  authority:: 高
  verified:: 2026-09-13

- 来源:: man 7 tcp
  use_when:: 与 ip-sysctl 交叉验证 keepalive 语义与「约 11 分钟判死」的量级
  url:: https://man7.org/linux/man-pages/man7/tcp.7.html
  answers:: keepalive 默认参数，及 *the connection will be aborted after ~11 minutes of retries*
  authority:: 高
  verified:: 2026-09-13

- 来源:: systemd resolved.conf 手册
  use_when:: 在「路由器同时是 DNS 服务器」的场景配独立备用解析
  url:: https://www.freedesktop.org/software/systemd/man/latest/resolved.conf.html
  answers:: `FallbackDNS=` 语义（空格分隔的备用 DNS 列表，未给时用编译内置列表）、`/etc/systemd/resolved.conf.d/` drop-in 位置
  authority:: 高
  verified:: 2026-09-13

> [!warning] C4 遗留判断（2026-09-13）
> [[2026-06-24-hermes-feishu-outage-postmortem]] 的「路由器 conntrack 饱和」目前仍是**推断**——本页只登记取证口径（count/max/time_wait 与 `dmesg | grep -i conntrack`），未登记任何实测计数。

## C8 复核补强（2026-09-13）：为库内自述的版本性论断补外部锚点

> 复核确认本页 13 条 wikilink 目标全部存在（原判断「审计写的 12 条 wikilink + 1 条安全提示」不准：末尾 warning 是 callout 不是条目）。但「xray 26.3.27 / legacy crypto / 固件版本」这类**版本性论断**此前全靠库内自述；以下 3 条为本轮实测可达的外部锚点（C4 节已另补 6 条 Windows/内核来源，故「本页 0 条外部来源」的旧判断已过期）。

- 来源:: OpenSSH Legacy Options（官方）
  use_when:: 复现 R4CM 的 legacy crypto 登录，或解释「OpenSSH 拒绝连接 legacy 服务器」的报错
  url:: https://www.openssh.org/legacy.html
  answers:: 用 `-o KexAlgorithms=+diffie-hellman-group1-sha1` / `-o HostKeyAlgorithms=+ssh-dss` 显式追加算法；`+` 前缀表示**追加**而非替换（服务器日后支持更好算法时自动升级）；`ssh -Q kex|key|cipher|mac` 列本机支持项、`ssh -G user@host` 打印实际生效配置。2026-09-13 实测 HTTP 200（`www.openssh.com/legacy.html` 会跨域重定向到 `www.openssh.org`，抓取须用后者）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Xray-core 发布（GitHub Release API）
  use_when:: 核对库内「xray 26.3.27」是否与上游一致，或判断是否该升级
  url:: https://api.github.com/repos/XTLS/Xray-core/releases/latest
  answers:: 2026-09-13 实测 latest = `v26.3.27`（published_at 2026-03-27）——与 [[ARCHITECTURE]] 记的 xray 26.3.27 一致，该版本性论断获外部锚点
  authority:: 高
  verified:: 2026-09-13

- 来源:: v2rayN 发布（GitHub Release API）
  use_when:: 核对 v2rayN 版本，或评估「内置下载器」类安全公告的影响面
  url:: https://api.github.com/repos/2dust/v2rayN/releases/latest
  answers:: 2026-09-13 实测 latest = `7.24.9`（published_at 2026-08-29；body 标「紧急安全更新：修复旧版本内置下载器可致 MITM 并下载恶意文件」，并移除 Xray `allowInsecure`）
  authority:: 高
  verified:: 2026-09-13

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 补疏漏 | 本页版本性论断（xray 26.3.27 / legacy crypto / 固件版本）全靠库内自述，无外部锚点 | 新增「C8 复核补强」节 3 条外部锚点：OpenSSH Legacy Options（实测 200）、Xray-core Release API（latest=`v26.3.27`，与库内一致）、v2rayN Release API（latest=`7.24.9`）；并注明 C4 节已另补 6 条 Windows/内核来源、「0 条外部来源」的旧判断已过期 |
| 加厚 | 「R4CM [IP已脱敏] fw 2.14.87、SSH root@22、legacy crypto 要求」把型号/IP/固件/账户压成一行，换机不可复现 | 展开为复现要素（`root` + 22 端口 + legacy 参数示例，算法名以 `ssh -vv` 实际 offer 为准），并说明 `[IP已脱敏]` 是脱敏占位、不是字段名 |
| 补疏漏 | 关联安全项 warning 只有结论 + `%USERPROFILE%` 占位，无处置路径 | 路径改为绝对路径；补最小轮换清单（改口令 / 密钥加口令或更换 / `StrictHostKeyChecking=accept-new`）与验收判据（新会话免密成功、旧口令与旧私钥失败），并要求轮换后回写复核日期 |
| —（复核成立） | 「12 条 wikilink + 1 条安全提示」的计数 | 复核确认 13 条 wikilink 目标全部存在；末尾 warning 是 callout、不是条目，未改条目结构 |

见 [[CORRECTIONS]]、[[AGENTS]]。

## C3 复核新增（2026-09-13）：路由器硬件/固件与客户端网络栈

> C3 簇（network 子库回写）需要为「固件版本、分区布局、legacy crypto、驱动、DNS/无线参数」这类论断补可核外部锚点；以下条目均在 2026-09-13 实际抓取过。

- 来源:: 小米路由器 4C 官方固件发布页（miuirom 镜像）
  use_when:: 核对 R4CM 的「官方最新固件」与「本机固件是否落后」
  url:: https://miuirom.org/miwifi/mi-router-4c
  answers:: 2026-09-13 实测 latest = `2.14.502`、*Last update 2024-02-21*（库内本机为 `2.14.87`，未升级）；引用固件号时须写明「本机实际 / 官方最新」
  authority:: 中
  verified:: 2026-09-13

- 来源:: OpenWrt Table of Hardware — Xiaomi Mi Router 4C
  use_when:: 刷机前核对分区布局与硬件批次门槛，或验证 stock 固件的分区表
  url:: https://openwrt.org/toh/xiaomi/xiaomi_mi_router_4c
  answers:: stock `/proc/mtd`：mtd0 `01000000` ALL、mtd6 `00100000` overlay、mtd7 `00c60000` OS1、mtd8 `00af0000` rootfs、mtd9 `00200000` disk（除 mtd0 外切片和 26.675MB > 16MB ⇒ **rootfs 嵌套在 OS1 内**）；警告 *03/2022 OpenWrt will not work on units fitted with Eon EN25QX128 16MB flash chip*；步骤 12 `mtd -r write /tmp/openwrt.bin OS1`
  authority:: 高
  verified:: 2026-09-13

- 来源:: OpenWrt 无线配置文档（UCI 参数名与 WPA3 默认支持）
  use_when:: 写 `/etc/config/wireless` 前确认参数名，或解释「WPA3 不可用是硬件还是固件问题」
  url:: https://openwrt.org/docs/guide-user/network/wifi/basic
  answers:: UCI 名为 `rts`（*Override the RTS/CTS threshold*，默认 driver default）与 `frag`，**不是** `rts_threshold` / `frag_threshold`；透传项 `hostapd_bss_options`（*Pass any custom options to hostapd-*.conf. Values passed as-is*）；「*WPA3 modes are supported by default starting with the OpenWrt 21.02 release.*」⇒ WPA3 取决于固件/hostapd 版本，非 MT7628 硬件
  authority:: 高
  verified:: 2026-09-13

- 来源:: OpenWrt ramips 设备树（mt7628an_xiaomi_mi-router-4c.dts）
  use_when:: 核对 R4CM 分区节点定义与嵌套关系（TOH 表格之外的源码级依据）
  url:: https://raw.githubusercontent.com/openwrt/openwrt/main/target/linux/ramips/dts/mt7628an_xiaomi_mi-router-4c.dts
  answers:: 分区节点定义（与 TOH 的 `/proc/mtd` 数字互证）
  authority:: 高
  verified:: 2026-09-13

- 来源:: LKML：mt76/mt7603 关闭 SKB loopback 补丁（2024-03-25，Rafał Miłecki）
  use_when:: 判断「debugfs 关帧缓冲」类优化在本机是否可执行，或核对 MT7628 高负载断流的成因
  url:: https://lkml.indiana.edu/hypermail/linux/kernel/2403.3/05496.html
  answers:: 原文「*disabling SKBs loopback code makes mt7603 devices much more stable under load. There are still some traffic hiccups…*」「*a close relation between MCU interrupts of type PKT_TYPE_TXS and slowdowns / stalls*」⇒ 是**相关性 + 可停数秒**，且该 debugfs 属性 2024-03-25 才进 mainline，原厂 3.10 内核不具备
  authority:: 高
  verified:: 2026-09-13

- 来源:: Qualcomm 驱动站设备清单（qc-drivers.eu）
  use_when:: 核对「QCA9377 最新驱动版本」这类说法是否有出处
  url:: https://www.qc-drivers.eu/wifi-device-list.html
  answers:: 2026-09-13 实测标题 *List of 305 Qualcomm WiFi devices*，全页检索 `9377` 命中 **0**、`QCA` 命中 **0** ⇒ QCA9377 不在该站清单，「最新版 v3.1.0.1486」无可核来源
  authority:: 低
  verified:: 2026-09-13

- 来源:: OpenSSH 8.8 发布说明（RSA/SHA-1 默认禁用）
  use_when:: 解释 8.8+ 客户端连 legacy 服务器为何仍失败，或补齐 `ssh` 参数集
  url:: https://www.openssh.org/txt/release-8.8
  answers:: 「*This release disables RSA signatures using the SHA-1 hash algorithm by default.*」⇒ 除 `KexAlgorithms`/`HostKeyAlgorithms`/`MACs` 外还需 `-o PubkeyAcceptedAlgorithms=+ssh-rsa`
  authority:: 高
  verified:: 2026-09-13

- 来源:: `ssh(1)` 手册（`-D` 动态转发语义）
  use_when:: 核对「`ssh -D` 的出口是谁」这类标注
  url:: https://man7.org/linux/man-pages/man1/ssh.1.html
  answers:: `-D` 在**执行 ssh 的本机**开 SOCKS 监听、出口为所登录的远端主机；替代抓取点 `https://man.openbsd.org/ssh`
  authority:: 高
  verified:: 2026-09-13

- 来源:: `resolv.conf(5)` 手册（解析器尝试顺序与可调项）
  use_when:: 设计/审查 DNS 配置，或解释「能上网但首次解析很慢」
  url:: https://man7.org/linux/man-pages/man5/resolv.conf.5.html
  answers:: 最多使用 MAXNS（当前 3）个 nameserver、按顺序尝试；`timeout:n`（秒）与 `attempts:n` 可调；`rotate` 轮转；首行放不可达 DNS 的代价是每次查询卡一个超时
  authority:: 高
  verified:: 2026-09-13

- 来源:: frp 发布（GitHub Release API）
  use_when:: 评估 frp 客户端在 1.4MB 可用空间的 `/userdisk` 上能否落地
  url:: https://api.github.com/repos/fatedier/frp/releases/latest
  answers:: 2026-09-13 实测 v0.71.0（published 2026-08-14）；MIPS 资产 `linux_mips` 11.91MB / `linux_mipsle` 11.71MB / `linux_mips64` 11.64MB / `linux_mips64le` 11.41MB ⇒ 远大于库内记的「~5MB」，必须走 `/tmp`(tmpfs)
  authority:: 高
  verified:: 2026-09-13

- 来源:: Microsoft Learn `netsh int tcp`（**已 404**）
  use_when:: 核对「`netsh int tcp set global` 参数与回读方法」——该页已失效，别再引用
  url:: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-int-tcp
  answers:: 2026-09-13 实测 **HTTP 404（Content not found）**；改用 `netsh int tcp show global` 回读 + `Get-NetTCPSetting` 交叉验证
  authority:: 低
  verified:: 2026-09-13

- 来源:: Microsoft Learn：Windows TCP/IP 性能已知问题
  use_when:: 排查 Windows 侧 TCP 吞吐/自动调优类问题时的官方替代入口
  url:: https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/tcpip-performance-known-issues
  answers:: TCP/IP 性能相关已知问题与调优注意点（替代上面已 404 的 netsh 参考页）
  authority:: 高
  verified:: 2026-09-13

- 来源:: RFC 8325《Mapping Diffserv to IEEE 802.11》
  use_when:: 判断 WMM/DSCP 视频优化能否生效，或为该优化写验收判据
  url:: https://www.rfc-editor.org/rfc/rfc8325.html
  answers:: Standards Track（2018-02）；定义 **DSCP → 802.11 用户优先级（UP）映射**与 **QoS Map** 机制 ⇒ 映射是标准化内容，能否生效取决于 AP 与客户端两侧实现一致，应作为验收项
  authority:: 高
  verified:: 2026-09-13

## C6 复核新增（2026-09-13）：Windows 动态端口默认值与已废弃的 TCP 卸载

> C6 簇核 `log-analysis-agent-windows-plan` 的 §4.2 参数表时发现：同表两行互相矛盾（一行写「默认 49152-65535」，另一行写 `MaxUserPort` 默认 5000），而 5000 是 2003 及更早的口径。

- 来源:: Microsoft Learn · KB 929851 默认动态端口范围（TCP/IP）
  use_when:: 写 Windows TCP 调优脚本或核对 `MaxUserPort` / 动态端口默认值时
  url:: https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/default-dynamic-port-range-tcpip-chang
  answers:: 逐字「The new default start port is **49152**, and the new default end port is **65535**. This is a change from **5000**.」（页面 Last updated 2026-02-12）⇒ Vista / Server 2008 及以后默认范围为 49152–65535，`5000` 仅适用于 Windows Server 2003 及更早；另核对同表 `TcpTimedWaitDelay` 默认 `0x78`(120s)、推荐 30 正确
  authority:: 高
  verified:: 2026-09-13

- 来源:: Microsoft Learn · TCP Chimney Offload（已废弃）
  use_when:: 判断 `netsh int tcp set global chimney=enabled` / `netdma=enabled` 这类命令还有没有效
  url:: https://learn.microsoft.com/en-us/previous-versions/windows/hardware/network/ndis-tcp-chimney-offload
  answers:: 页面逐字标注「[The TCP chimney offload feature is **deprecated and should not be used**.]」⇒ 库内 Phase 4 脚本里的 chimney / netdma 行只在历史记录意义上保留（`rss=enabled` 仍可用）
  authority:: 高
  verified:: 2026-09-13

见 [[CORRECTIONS]]、[[AGENTS]]。
