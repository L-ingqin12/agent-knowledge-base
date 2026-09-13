---
title: 路由器深度探索报告
tags: [network/router, network]
aliases: [路由器深度探索]
created: 2026-07-28
updated: 2026-09-13
status: stable
---

# 路由器深度探索报告 — Xiaomi R4CM 2.14.87

See also: [[Network-KB-Home]] | [[GUIDE]] | [[ROUTER-FULL-CAPABILITY]] | [[ROUTER-OPTIMIZATION]]

## 硬件规格

| 参数 | 值 |
|------|-----|
| 型号 | R4CM (小米路由器 4C) |
| SoC | MT7628AN (MIPS 24KEc V5.5, 575MHz) |
| RAM | 64MB DDR2 @ 800MHz |
| Flash | 16MB (SPI NOR) |
| WiFi | 2.4GHz only (MT7628 内置), 802.11bgn |
| 内核 | Linux 3.10.14 (2019-11-26) |
| 固件 | MiWiFi-R4CM-2.14.87 |

> [!warning] 更正（2026-09-13）：上表固件行缺「官方最新 / 本机实际 / 是否升级」三列，易被读成当前最新（原表述保留于上）。
> | 项 | 值 |
> |---|---|
> | 本机实际 | `MiWiFi-R4CM-2.14.87`（本文档 2026-07-28 实测） |
> | 官方最新 | `2.14.502`（发布页标注 last update **2024-02-21**） |
> | 是否升级 | **未升级**；该机型已停止功能更新，升级前需评估 [[FINAL-SUMMARY]] 中 P2 各项是否依赖旧内核行为 |
> 来源：<https://miuirom.org/miwifi/mi-router-4c>

## Flash 分区布局

| 分区 | 大小 | 名称 | 用途 |
|------|------|------|------|
| mtd0 | 16MB | ALL | 全镜像 |
| mtd1 | 128KB | Bootloader | U-Boot |
| mtd2 | 64KB | Config | 配置 |
| mtd3 | 64KB | **Factory** | TX power校准/SN/MAC |
| mtd4 | 64KB | crash | 崩溃日志 |
| mtd5 | 64KB | cfg_bak | 配置备份 |
| mtd6 | 1MB | overlay | 持久化存储(/data) |
| mtd7 | 12.4MB | OS1 | 系统固件 |
| mtd8 | 10.9MB | rootfs | 根文件系统 |
| mtd9 | 2MB | disk | 用户数据(/data) |

> [!warning] 更正（2026-09-13）：上表 mtd6 与 mtd9 的用途**都写成 `/data`，且与 [[ROUTER-FULL-CAPABILITY]] 口径不一致**（原表述保留于上）。
> 上游只给分区名、不给挂载点：OpenWrt TOH 页列出的 stock `/proc/mtd` 为 `overlay` / `OS1` / `rootfs` / `disk`，**挂载点必须实测**。库内统一口径应为：**mtd6 `overlay` → `/data`（连同 `/etc` 持久化）**、**mtd9 `disk` → `/userdisk`**（[[ROUTER-FULL-CAPABILITY]] 的「三、存储使用」表即按此记，`/userdisk` 2.0M）。另注：上表 mtd7 `OS1`（12.4MB）与 mtd8 `rootfs`（10.9MB）并非并列分区，**mtd8 嵌套在 mtd7 内**（切片和 26.675MB > 16MB 芯片容量）。
> 来源：<https://openwrt.org/toh/xiaomi/xiaomi_mi_router_4c>

## 运行进程

| 进程 | 用途 | 端口 |
|------|------|------|
| dropbear | SSH (LAN-only) | [IP已脱敏]:22 |
| dnsmasq | DNS/DHCP | 53 |
| sysapihttpd | Web API (nginx-based) | 80, 8899, 8999 + 15个后端端口 |
| himan | 小米 IoT 管理器 | 8080 |
| tbusd | 小米内部消息总线 | 784 |
| fcgi-cgi | FastCGI 后端 | 127.0.0.1:8920 |
| taskmonitor | 任务监控 | — |
| trafficd | 流量统计 | — |
| datacenter | 数据中心(遥测) | — |
| smartcontroller | 智能家居控制 | — |
| plugincenter | 插件中心 | — |
| messagingagent | 消息代理 | — |
| rmonitor | 远程监控 | — |
| crond | 定时任务 | — |
| iweventd | WiFi 事件监控 | — |
| mald | 恶意攻击检测 | — |
| btnd | 按钮守护进程 | — |
| netapi | 网络 API | — |

## Web API 端点 (Lua 控制器)

| 文件 | 功能 |
|------|------|
| xqsystem.lua | 系统(登录/信息/固件) |
| xqnetwork.lua | 网络设置(WiFi/WAN/LAN) |
| misystem.lua | 设备管理(设备列表/状态) |
| xqsmarthome.lua | 智能家居 |
| xqtunnel.lua | 隧道/代理 |
| xqdatacenter.lua | 数据遥测 |
| xqnetdetect.lua | 网络检测 |
| xqpassport.lua | 账户 |
| miats.lua | 防盗安全 |
| misns.lua | 社交网络服务 |
| cportal.lua | 强制门户 |

注意: Lua 源码已预编译为字节码，无法直接阅读。

## sysctl 关键内核参数

```
conntrack_max = 16384
tcp_keepalive_time = 60s
tcp_fin_timeout = 10s
tcp_tw_reuse = 1
tcp_mtu_probing = 1
tcp_ecn = 0
conntrack_tcp_timeout_established = 3600
```

## 可利用的机制

### 1. rc.local 持久化 (已验证)
```bash
# /etc/rc.local 在启动时执行，已配置:
/data/dropbear/dropbear -p [IP已脱敏]:22 &  # SSH
busybox telnetd -p 23 -l /bin/ash &            # Telnet (实际未生效)
```

### 2. iweventd WiFi 事件钩子
WiFi 状态变化时触发 `/data/etc/iwevent.d/*.sh`。可用于:
- WiFi reload 时自动重设 AP 隔离
- 设备连接/断开时执行自定义脚本

### 3. Factory 分区 (mtd3)

> [!warning] Factory 分区操作风险
> 
> 偏移 0xA0 处 14 字节为 TX power 校准值。修改为 FF 可解锁到 30dBm。
> 但当前 iwinfo 显示 Tx-Power: 18 dBm，可能已部分解锁。
> 
> **警告**: 修改 Factory 分区有砖机风险。务必先备份:
> 
> ```bash
> dd if=/dev/mtdblock3 of=/tmp/factory.bak bs=64k
> ```

### 4. Xiaomi smartvpn (已不可用)

> [!warning] SmartVPN 服务器已死
> 内置 VPN 代理功能，type=vpn, 出口 IP [IP已脱敏]:10080。
> **2026-07-28 测试**: 服务器 100% 丢包，代理域名列表为空，已不可用。
> 替代方案见 [[ROUTER-VIDEO-REMOTE-MONITOR]]。

### 5. miqos (已禁用)
内置 QoS 流量整形，4 级优先级(p1 VoIP/p2 Web/p3 Email/p4 FTP)。

### 6. 无固件签名验证

> [!info] 可刷写自定义固件
> 
> 可刷写自定义 OpenWrt 固件获得:
> - 新版内核 + debugfs (修复 MT7628 帧缓冲)
> - iptables + QoS
> - 现代 dropbear (支持密钥认证)
> - 5GHz USB 网卡支持

> [!warning] 补疏漏（2026-09-13）：上节只讲「可以刷」，**漏了硬件批次门槛与刷写路径**（原表述保留于上）。
> - **批次门槛**：OpenWrt TOH 页明确警告「*03/2022 OpenWrt will not work on units fitted with **Eon EN25QX128 16MB flash chip***」——**先核对本机 flash 芯片批次再动手**。
> - **刷写路径**：TOH 步骤 12 用 `mtd -r write /tmp/openwrt.bin OS1`，即写入 **mtd7 OS1**（印证上文 mtd8 rootfs 嵌套在 OS1 内）。
> - **debugfs 与内核版本绑定**：相应 debugfs 属性由 mt76/mt7603 补丁在 **2024-03-25** 才进 mainline，因此「刷 OpenWrt 才能修帧缓冲」的前提是**用足够新的 OpenWrt**，旧版 OpenWrt 同样没有。
> - **未复核项**：审计另称「官方明确警告不要用 WiFi 刷机」，本次在 TOH 页未检索到该表述，**该细节未能复核**，引用前请自行确认。
> 来源：<https://openwrt.org/toh/xiaomi/xiaomi_mi_router_4c>、<https://lkml.indiana.edu/hypermail/linux/kernel/2403.3/05496.html>

## 限制

> [!warning] 已知限制
> 
> | 限制 | 说明 |
> |------|------|
> | `iptables` 用户空间缺失 | 未编译进 busybox; 内核模块 (compat_xtables 等) 已全加载, 但无 iptables 二进制 |
> | iptables 缺失 | 无防火墙/NAT 管理能力 |
> | debugfs 缺失 | 无法禁用 MT7628 frames buffering |
> | uci 不可用 | 必须直接编辑 /etc/config/* |
> | dropbear 0.52 | 不支持现代 SSH 密钥格式 |
> | Lua 字节码 | 无法修改 Web API 逻辑 |
> | telnetd 无法启动 | busybox telnetd 启动失败(原因不明) |
> | MT7628 帧缓冲 Bug | 无 debugfs 修复，需刷 OpenWrt |

> [!warning] 更正（2026-09-13）：上表「iptables 缺失 | 无防火墙/NAT 管理能力」**结论过强**（原表述保留于上表）。
> 设备**确实在做 NAT**——[[ROUTER-OPTIMIZATION]] 记录的「双 NAT」是实测成立的，只是没有 `iptables` 用户态二进制可用于**查看/增删规则**。准确表述应收窄为「**无规则级防火墙/NAT 管理能力**（内核模块已加载，缺 iptables 二进制）」，不要读成「设备没有 NAT」。

## SSH 连接方法

```bash
# 唯一可用的连接方式
/d/Users/%USERPROFILE%/AppData/Roaming/MobaXterm/slash/bin/sshpass -p [已脱敏] \
  /d/Users/%USERPROFILE%/AppData/Roaming/MobaXterm/slash/bin/ssh \
  -o KexAlgorithms=+diffie-hellman-group1-sha1 \
  -o HostKeyAlgorithms=+ssh-rsa \
  -o MACs=+hmac-sha1-96,hmac-sha1,hmac-md5 \
  -o StrictHostKeyChecking=no \
  -o ConnectTimeout=8 \
  root@[IP已脱敏]

# Wrapper 脚本
bash scripts/router_ssh.sh "command"
```

密钥认证不可用(dropbear 0.52 与 OpenSSH 密钥格式不兼容)。

> [!warning] 更正（2026-09-13）：上句标题「**唯一可用**的连接方式」与参数集**都不完整**（原表述保留于上）。
> 该组合缺了一项现代 OpenSSH 必需的参数：**OpenSSH 8.8 起默认禁用基于 SHA-1 的 RSA 签名**（release notes 原文：「*This release disables RSA signatures using the SHA-1 hash algorithm by default.*」）。现有命令只加了 `KexAlgorithms` / `HostKeyAlgorithms` / `MACs`，**没有 `PubkeyAcceptedAlgorithms`**；在 8.8+ 客户端上应补 `-o PubkeyAcceptedAlgorithms=+ssh-rsa`（与 `HostKeyAlgorithms=+ssh-rsa` 配对）。注意这属于**参数集不完整**，不是「文档过期」：本文写于 8.8 之后，只是没覆盖该默认值变更。
> 来源：<https://www.openssh.org/txt/release-8.8>、<https://man7.org/linux/man-pages/man1/ssh.1.html>

## Related

- [[Network-KB-Home]] — 网络知识库主页
- [[GUIDE]] — 使用指南
- [[ROUTER-FULL-CAPABILITY]] — 路由器完全能力手册
- [[ROUTER-OPTIMIZATION]] — 路由器优化分析

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 硬件表固件 `MiWiFi-R4CM-2.14.87` 缺「官方最新/本机实际/是否升级」 | 加更正块补齐三列：官方最新 2.14.502（2024-02-21），本机未升级（miuirom.org） |
| 纠错 | Flash 分区表把 mtd6 与 mtd9 用途都写成 `/data`，且与 [[ROUTER-FULL-CAPABILITY]] 不一致 | 加更正块：mtd6 overlay→`/data`、mtd9 disk→`/userdisk`；并补 mtd8 rootfs 嵌套在 mtd7 OS1 内（OpenWrt TOH） |
| 补疏漏 | §6「无固件签名验证」只讲可刷，漏批次门槛与刷写路径 | 加注：Eon EN25QX128（03/2022）批次警告、`mtd -r write … OS1`、debugfs 需 2024+ mainline；并标注「不要用 WiFi 刷机」一说本次未能复核 |
| 纠错 | 限制表「iptables 缺失 \| 无防火墙/NAT 管理能力」过强 | 保留原行并加更正块：设备确实在做 NAT，应收窄为「无规则级管理能力」 |
| 纠错 | SSH 节「唯一可用的连接方式」参数集缺 `PubkeyAcceptedAlgorithms` | 保留原句并加更正块：OpenSSH 8.8 起默认禁用 SHA-1 RSA 签名，需补 `-o PubkeyAcceptedAlgorithms=+ssh-rsa`（release-8.8 / ssh(1)） |

相关：[[CORRECTIONS]] · [[AGENTS]]

