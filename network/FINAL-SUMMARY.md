---
title: 完整优化总结
aliases: [Final Summary, 总结]
tags: [network/optimization, network/proxy, network/router, network]
created: 2026-07-28
updated: 2026-09-13
status: stable
---

> [!success] 核心结论
> Telegram 视频卡顿由 **WiFi 层 + 路由器硬件 Bug** 双重导致，非代理问题。代理策略 Bug 已全部修复。详见 [[ARCHITECTURE]] 和 [[GUIDE]]。

## 性能基线

| 指标 | 当前值 | 评级 |
|------|--------|------|
| 代理出口 | [IP已脱敏] (p1d2)（2026-07-28 实测） | ✅ 稳定 |
| 下载速度 | ~375 KB/s (3.0 Mbps)（2026-07-28 实测） | △ 勉强 720p |
| Telegram API | 1.5s | △ 偏慢 |
| WiFi 网关延迟 | 2-113ms, avg **31ms** | ✅ 已达标 |
| 信号 | 82%, RSSI -58 | ✅ |

> [!info] 瓶颈已转移
> WiFi 延迟从 541ms → 113ms (改善 79%)，平均延迟 154ms → 31ms (改善 80%)（基准: [[SESSION-ARCHIVE-2026-07-28]] Phase 4 测量表）。当前瓶颈是**代理带宽 3 Mbps** — 刚好 720p 临界点，1080p 不够。换更快的代理节点是下一步关键。

> [!question] 信号强度口径（勘误: 库内曾并存 82/86/88%）
> 信号百分比曾出现 88%（2026-07-27 初测，[[network-analysis-2026-07-28]]）、86%（[[ROUTER-FULL-CAPABILITY]] 原记）、82%（本页）。三处 RSSI 均为 **-58 dBm**；统一采用最保守的 **82%**，后续以 RSSI (dBm) 为唯一口径。

## 根因分析

### 主因 1: WiFi 层周期性断流

**现象**: Ping 网关每 3-8 秒出现一次 100-182ms 尖峰

**公开知识确认**:
1. **QCA9377 网卡驱动过时** — 当前 2021-05-19 v12.0.0.1118，最新版 v3.1.0.1486 (2025-06)。旧驱动有已知延迟问题。[qc-drivers.eu](https://www.qc-drivers.eu)

> [!warning] 更正（2026-09-13）：「最新版 v3.1.0.1486」**无可核来源**（原表述保留于上条）。
> 复核所引驱动站：设备清单页标题为「List of 305 Qualcomm WiFi devices」，全页检索 `9377` **命中 0**、`QCA` **命中 0**——QCA9377 不在该站清单内，故既无法确认它给出过 v3.1.0.1486，也无法确认 12.x → 3.x 的版本关系（主版本号倒挂，本身可疑）。**可成立的部分**是：本机驱动为 2021-05-19 v12.0.0.1118（库内实测），且该驱动版本确实陈旧。处置建议不变（更新驱动），但**引用「最新版 v3.1.0.1486」时应删除该数字或标注待核**。来源：<https://www.qc-drivers.eu/wifi-device-list.html>
2. **WiFi 省电模式** — 默认开启，导致网卡间歇性休眠。关闭后延迟稳定性显著提升。
3. **蓝牙共存干扰** — QCA9377 是 WiFi+BT 二合一芯片，蓝牙活动导致 2.4GHz 信道冲突。

### 主因 2: MT7628 Frames Buffering Bug

**现象**: WiFi 在高负载下断流数秒（吞吐降到 0 bps）

**公开知识确认**:
- Linux 内核邮件列表: MT7628 (mt7603 驱动) 的 MCU 中断 `PKT_TYPE_TXS` 处理异常，帧缓冲导致 WiFi 传输完全停止。[lkml.indiana.edu](https://lkml.indiana.edu/hypermail/linux/kernel/2403.3/05496.html)
- OpenWrt 社区: R4CM 特定型号在高流量下频繁出现 WiFi 断流，通过 debugfs 关闭 SKB loopback 可大幅改善。[OpenWrt Forum](https://forum.openwrt.org/t/openwrt-for-xiaomi-mi-router-4c/72175/129)

> [!warning] 更正（2026-09-13）：上述两条的**引文与因果都需修正**（原表述保留于上）。
> 1. **引文错位**：所引 OpenWrt Forum 帖 `/72175/129` 实为 2021-12-29 一条与主题无关的回复（「Before mocking me, maybe you should try to find out what you've done wrong…」），全文**不含**断流 / SKB loopback / debugfs 任何一项。真正对应的来源是 lkml 上 Rafał Miłecki 的 mt76/mt7603 补丁（2024-03-25），原文：「*disabling SKBs loopback code makes mt7603 devices much more stable under load. There are still some traffic hiccups but those happen like once every an hour…*」。故应写作「**关闭 SKB loopback 后高负载下明显更稳定，但并非完全解决**」——「大幅改善」略过头（补丁原话是 much more stable），「并非完全解决」成立。
> 2. **因果过强**：补丁原文为「*MT7603EN and MT7628AN were reported by multiple users to be unstable under high traffic. Transmission of packets could stop for seconds often leading to disconnections.*」「*Long research & debugging revealed a close relation between MCU interrupts of type PKT_TYPE_TXS and slowdowns / stalls.*」——是**相关性 + 可停数秒**，非「帧缓冲导致传输完全停止」的确定因果；且该 debugfs 开关 **2024 年才进 mainline**，2026 年的原厂固件不具备（见下方 P2 更正）。
> 来源：<https://lkml.indiana.edu/hypermail/linux/kernel/2403.3/05496.html>

### 主因 3: MT7628 TX Power 出厂锁 14 dBm（勘误：当前实测 18 dBm）

**现象**: 出厂固件默认限制 WiFi 发射功率为 14 dBm (25mW)，而硬件支持 30 dBm (1000mW)。**勘误**: 当前 iwinfo 实测 Tx-Power 为 **18 dBm**（已部分解锁），全库口径统一为 18 dBm，见 [[ROUTER-DEEP-EXPLORATION]] / [[ROUTER-FULL-CAPABILITY]]。

**公开知识确认**:
- anywlan 论坛: R4CM factory 分区偏移 0xA0 处 14 字节控制 TX power，改为 `FF` 解锁 30 dBm。[anywlan.com](https://www.anywlan.com/thread-447807-1-6.html)

> [!warning] 更正（2026-09-13）：本条**取证失败，30 dBm 与偏移量均无来源**（原表述保留于上）。
> 抓取所引 anywlan 帖子返回 **HTTP 403**，正文不可得（无法核实「偏移 0xA0 / 14 字节 / 改 FF」）。另外**明确一点免于误判**：本页 L48 标题、上段与 P2 清单三处都已显式标注「勘误：当前实测 18 dBm」，口径统一在**实测 18 dBm**，不存在前后不一致；遗留缺陷只是 **30 dBm 上限与 factory 偏移量缺 datasheet / 源码级来源**。**在拿到 datasheet 或固件源码证据前，不要执行 factory 分区写入**。来源：<https://www.anywlan.com/thread-447807-1-6.html>（HTTP 403）

### 主因 4: 代理策略 Bug（已全部修复）

| Bug | 修复 | 状态 |
|-----|------|------|
| Mux+Vision 冲突 → 队头阻塞 | 所有 VLESS 出站 mux: false | ✅ |
| 无 catch-all → Telegram 不走 balancer | 添加 `tcp,udp → balancerTag: balancer` | ✅ |
| Balancer 引用错误 (outboundTag) | 改为 balancerTag | ✅ |
| DNS 路径分裂 → CDN 不匹配 | DNS 走固定 proxy，不走 balancer | ✅ |
| Balancer 包含高延迟 US 节点 | selector 改 `["proxy"]` only | ✅ |
| Observatory 频率过高 | 3min → 10min | ✅ |

## 优化优先级

```
P0 (立即 — 代理配置) — 全部已完成 ✅
  ✅ Mux 禁用
  ✅ catch-all 添加
  ✅ balancerTag 修正
  ✅ DNS 一致性
  ✅ balancer proxy-only
  ✅ observatory 10min

P1 (本周 — 客户端侧)
  ⬜ 更新 QCA9377 驱动到最新版
  ⬜ 关闭 WiFi 省电模式 (设备管理器)
  ⬜ 关闭蓝牙 (如不用)
  ⬜ netsh winsock reset + 网络重置

P2 (本月 — 路由器侧, 需SSH)
  ⬜ 禁用 MT7628 frames buffering (debugfs)
  ⬜ 解锁 TX power 18→30 dBm (factory分区)（勘误：原记 14dBm）
  ⬜ 永久写入 AP 隔离 (/etc/config/wireless)
  ⬜ Beacon interval 100→200ms
  ⬜ 上游 DNS 改直连 [IP已脱敏]

P3 (长期 — 硬件)
  ⬜ 换双频 WiFi 6 路由器 (AX3000/AX6S)
  ⬜ 消除双 NAT (上游桥接 或 R4CM AP模式)
  ⬜ FileSystemWatcher hook 全自动化
```

> [!warning] 更正（2026-09-13）：P2 的两项**在现固件上不可执行**（原清单保留于上）。
> - **「禁用 MT7628 frames buffering (debugfs)」**：相应 debugfs 属性由 mt76/mt7603 补丁在 **2024-03-25** 才加入 mainline；本机原厂固件为 **Linux 3.10.14（2019-11-26）**，不可能具备——这与 [[ROUTER-FULL-CAPABILITY]]「❌ debugfs (原厂内核不支持)」的记载一致。要执行本项必须先刷 OpenWrt。
> - **「解锁 TX power 18→30 dBm (factory分区)」**：见上文 anywlan 来源 403，无 datasheet / 源码依据，暂缓。
> - 刷机本身还有硬件门槛：OpenWrt TOH 页警告「*03/2022 OpenWrt will not work on units fitted with Eon EN25QX128 16MB flash chip*」，需先核对本机 flash 批次。
> 来源：<https://lkml.indiana.edu/hypermail/linux/kernel/2403.3/05496.html>、<https://openwrt.org/toh/xiaomi/xiaomi_mi_router_4c>

## 路由器优化速查（R4CM）

| 优化 | 生效方式 | 需要 |
|------|----------|------|
| AP 隔离=0 | API (临时) / SSH (永久) | 已执行API |
| 信道优化 | API `set_wifi channel=N` | 已执行 |
| 40MHz 带宽 | API (未生效) / SSH uci | SSH |
| Beacon间隔 | SSH `/etc/config/wireless` | SSH |
| RTS阈值 | SSH `/etc/config/wireless` | SSH |
| 帧缓冲禁用 | SSH debugfs | SSH+补丁 |
| TX power解锁 | 改factory分区 | SSH+hex |
| DNS直连 | SSH uci network | SSH |
| MTU调整 | SSH uci network | SSH |
| 双NAT消除 | 网络拓扑变更 | 手动 |

> [!warning] 路由器优化
> R4CM 的多项优化（帧缓冲、TX power、Beacon）通过 SSH 操作，详见 [[ROUTER-OPTIMIZATION]]。

## 当前生效配置

```
Balancer: SG1 + US1 + US3 + JP1 (leastPing, 2026-08-09 换池), fallback: us1
Observatory: 10分钟, 4节点健康检查
DNS: 直连走 Alibaba, 境外走 Cloudflare via p1d2
路由: CN → direct, Google → balancer, 其他 → balancer
出站: SG1 + US1 + US3 + JP1 (全部 mux:false)
```

## 日常操作

订阅更新后运行 (2-3分钟):
```powershell
powershell -File "D:\Document\local\knowledge\network\scripts\enhance-config.ps1" -DryRun
powershell -File "D:\Document\local\knowledge\network\scripts\enhance-config.ps1" -Apply
```

查看状态:
```powershell
powershell -File "D:\Document\local\knowledge\network\scripts\enhance-config.ps1" -Status
```

---

*Home: [[Network-KB-Home]] | Architecture: [[ARCHITECTURE]] | Router: [[ROUTER-OPTIMIZATION]] | Guide: [[GUIDE]]*

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 主因 1「最新版 v3.1.0.1486 (2025-06)」无可核来源 | 保留原句并加更正块：qc-drivers.eu 清单 305 款、检索 `9377` 命中 0，QCA9377 不在其中；仅保留「本机 v12.0.0.1118 陈旧」这一可证部分 |
| 纠错 | 主因 2 引用的 OpenWrt Forum 帖与结论无关（引文错位） | 保留原链接并加更正块，改引 lkml mt76/mt7603 补丁（2024-03-25）原话：高负载下 much more stable，但非完全解决 |
| 纠错 | 主因 2 把 PKT_TYPE_TXS 与帧缓冲写成确定因果 | 保留原句并加更正块：补丁原文是「close relation」+「可停数秒」，且 debugfs 开关 2024 年才进 mainline |
| 加厚 | 主因 3 anywlan 引文（403）与 30 dBm 上限缺依据 | 加更正块：URL 返回 403 不可核；同时澄清 L48/L50/P2 三处口径已统一在实测 18 dBm，非自相矛盾；未取证前禁止写 factory 分区 |
| 纠错 | P2「禁用 frames buffering (debugfs)」在现固件不可执行 | 加更正块：debugfs 属性 2024 年才入 mainline，本机 Linux 3.10.14 不具备；并补 OpenWrt TOH 的 Eon EN25QX128 刷机警告 |

相关：[[CORRECTIONS]] · [[AGENTS]] · [[ROUTER-FULL-CAPABILITY]]

