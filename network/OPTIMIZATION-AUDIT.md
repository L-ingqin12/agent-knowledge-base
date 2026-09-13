---
title: 优化审计报告
aliases: [Optimization Audit, 优化审计, 设计漏洞]
tags: [network/optimization, network/proxy, network/analysis, network]
created: 2026-07-28
updated: 2026-09-13
status: review
---

# 优化审计 — Telegram 视频卡顿根因与修复

See also: [[Network-KB-Home]] | [[FINAL-SUMMARY]] | [[ARCHITECTURE]] | [[ROUTER-OPTIMIZATION]]

## 当前性能基线

| 指标 | 数值 | 目标 |
|------|------|------|
| 代理出口 IP | [IP已脱敏] (p1d2) | — |
| 下载速度 | ~375 KB/s (3.0 Mbps) | >1 MB/s |
| WiFi 网关延迟 | 2-113ms (avg **31ms**) ✅ | <10ms 稳定 (已大幅改善, 未完全达标) |
| WiFi 速率 | 72.2 Mbps (2.4GHz 802.11n) | >150 Mbps |

## 四层优化清单

### L1 — WiFi 物理层 (影响最大)

| # | 优化点 | 当前 | 收益 | 难度 |
|---|--------|------|------|------|
| 1 | 更新 QCA9377 驱动 | v12.0.0.1118 (2021) | 延迟 -50~80% | 低 |
| 2 | 换双频路由器 | R4CM 仅 2.4GHz | 速率 72→300+ | 硬件 |
| 3 | 减少 IoT 争用 | 8 ESP32 | 小幅降延迟 | 中 |
| 4 | HT40 40MHz | API 返回成功未生效 | 速率翻倍 | SSH |

> [!warning] WiFi 是最大瓶颈
> 2-182ms 延迟抖动使视频每几秒 TCP 重传，直接导致缓冲循环。

> [!warning] 更正（2026-09-13）：上表 #3 的「8 ESP32」与设备清单不符（原表述保留于上表）。
> [[network-analysis-2026-07-28]] 第四节实为 13 台设备，其中 `ESP_`/`ESP-` 前缀 **7 台** + 1 台 Unknown。IoT 争用的结论不变，引用时请改用 7 台或直接引用该节清单。

### L2 — 路由器层

| # | 优化点 | 收益 | 难度 |
|---|--------|------|------|
| 5 | 消除双 NAT ([[ROUTER-OPTIMIZATION]]) | -5~10ms | 中 |
| 6 | SSH 永久 AP 隔离 | 避免复发 | 低 ✅ |
| 7 | conntrack 调优 | 减丢包 | SSH |

### L3 — 代理策略层 (详见 [[ARCHITECTURE]])

| # | 优化 | 状态 |
|---|------|------|
| 8 | catch-all 缺失 | ✅ 已修复 |
| 9 | 评分单维度 (仅 Ping) | ⬜ 待复合评分 |
| 10 | Balancer 节点质量 | ✅ proxy-only |
| 11 | 节点消失无感知 | ✅ 每次重测 |
| 12 | Observatory 频率 | ✅ 3min→10min |

### L4 — 协议层

| # | 优化点 | 难度 |
|---|--------|------|
| 13 | Telegram IP 段路由 | 中 |
| 14 | TCP 握手开销 | 客户端控制 |
| 15 | Reality 开销 | 无优化 |

> [!warning] 补疏漏（2026-09-13）：#13「Telegram IP 段路由」原表只有名称与难度，**补上可执行的写法与验收判据**（原表述为「| 13 | Telegram IP 段路由 | 中 |」）。
> - **网段来源**：Telegram 官方公布的网段列表（`core.telegram.org/resources/cidr.txt` 一类）需在运行时快照留档，不要手抄硬编码。
> - **规则写法**：Xray 路由文档确认 `ip` 规则接受 **CIDR 列表**，也支持 `geoip:` / `geosite:` 匹配；因此可写成 `{"ip": ["<CIDR 列表>"], "outboundTag|balancerTag": "<目标>"}`。注意引用 balancer 必须用 `balancerTag`（见 [[ARCHITECTURE]] 决策 5）。
> - **验收判据**：规则生效后，Telegram 媒体流量应命中该规则而非 catch-all；`-Status` 之外要查 xray 日志有无 `non existing outTag`。
> 来源：<https://xtls.github.io/config/routing.html>

## 设计漏洞 (6 个)

| # | 漏洞 | 方案 | 参考 |
|---|------|------|------|
| 1 | 评分仅用 Ping | guiNDB.db 复合评分 | [[ARCHITECTURE#五、未来可能的增强]] |
| 2 | 非自动触发 | FileSystemWatcher hook | [[ARCHITECTURE#Phase 3]] |
| 3 | Balancer 频繁切换 | tolerance 容差 | — (tolerance 未在 [[ARCHITECTURE]] 中定义) |
| 4 | 无 Telegram 路由 | 加 IP 段规则 | — |
| 5 | SSH 可能失效 | CVE-2019-18370 | [[ROUTER-DEEP-EXPLORATION]] |
| 6 | 高延迟 US 节点 | proxy-only selector | ✅ 已修复 |

> [!warning] 补疏漏（2026-09-13）：#3「Balancer 频繁切换 → tolerance 容差」**不能只加一行配置**——本页与 [[ARCHITECTURE]] 均未写明前提（原表只给「tolerance 容差」）。
> 上游路由文档：`tolerance` 属 **leastLoad 专属**——「这是一个可选配置项，**不同负载均衡策略的配置格式有所不同。目前只有 leastLoad 负载均衡策略可以添加这个配置项**」，其下设 `expected` / `maxRTT` / `tolerance` / `baselines` / `costs`；`type` 取值为 `random|roundRobin|leastPing|leastLoad`。现役池是 **leastPing**，因此**加 tolerance 必须连同把 `type: leastPing` 换成 `leastLoad`**（换策略会改变选路行为，需单独验收）。来源：<https://xtls.github.io/config/routing.html>

> [!warning] 补疏漏（2026-09-13）：本清单标称「6 个」漏洞，**漏了第 7 类风险——v2rayN 生成器自身的回归**（上表计数仍为 6，故不插入新行）。
> 上游确有该类修复记录：PR **#8849「Fix balancer routing」**（`merged=true`，merged_at **2026-02-27**）——即 v2rayN 会生成/修复 balancer 路由，其生成器行为随版本变化，应纳入回归清单（与本库 [[v2rayn-balancer-复盘-2026-08-09]] 记录的 `outboundTag` 事故同源）。来源：<https://github.com/2dust/v2rayN/pull/8849>

## 优先级 (ROI)

```
P0 ✅ catch-all, balancer proxy-only, observatory 10min
P1 ⬜ 驱动更新, Telegram IP 段
P2 ⬜ 复合评分, 消除双 NAT
P3 ⬜ WiFi 6 路由器, Hook 自动化
```

## Related

- [[FINAL-SUMMARY]] — 完整总结
- [[ARCHITECTURE]] — 架构与决策
- [[ROUTER-OPTIMIZATION]] — 路由器优化
- [[Network-KB-Home]] — 知识库首页

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 补疏漏 | 漏洞 #3 只写「tolerance 容差」，未说它专属 leastLoad | 加注：`tolerance` 仅 leastLoad 可配（含 expected/maxRTT/baselines/costs），加它必须同时把 `type: leastPing` 换成 `leastLoad`（Xray 路由文档） |
| 补疏漏 | L4 协议层 #13「Telegram IP 段路由」只有名称与难度 | 加注：补网段来源、`ip` 规则的 CIDR/geoip 写法与验收判据（Xray 路由文档） |
| 补疏漏 | 「设计漏洞 (6 个)」未覆盖 v2rayN 生成器回归风险 | 不插入新行（保留 6 的计数），加注第 7 类风险：PR #8849「Fix balancer routing」merged 2026-02-27 |
| 补疏漏 | L1 #3「减少 IoT 争用 | 8 ESP32」与设备清单不符 | 加注：清单实为 7 台 ESP 前缀 + 1 台 Unknown，口径见 [[network-analysis-2026-07-28]] |

相关：[[CORRECTIONS]] · [[AGENTS]]
