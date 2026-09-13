---
title: 路由器优化分析
tags: [network/router, network/optimization, network]
aliases: [路由器优化]
created: 2026-07-28
updated: 2026-09-13
status: stable
---

# 路由器优化深度分析 — Xiaomi R4CM 2.14.87

See also: [[Network-KB-Home]] | [[GUIDE]] | [[ROUTER-FULL-CAPABILITY]] | [[ROUTER-DEEP-EXPLORATION]]

## 硬件规格

| 参数 | 规格 | 备注 |
|------|------|------|
| 型号 | R4CM | SoC: MT7628 (MIPS 24Kc) |
| CPU | 单核 575MHz | 当前负载 5.4%（2026-07-28 测量），充裕 |
| RAM | 64MB DDR2 @ 800MHz | 当前使用 46%（2026-07-28 测量），正常 |
| WiFi | 2.4GHz only (MT7628 内置) | **硬伤** — 无法 5GHz |
| 固件 | 2.14.87 | 较新，API 有限 |
| WAN | eth0.2 DHCP → [IP已脱敏] | 双 NAT |
| LAN | [IP已脱敏]/24 | 设备 IP 池 |

> [!warning] 更正（2026-09-13）：上表固件行 `2.14.87` 是**本机历史实测值**，官方发布页最新为 **2.14.502（2024-02-21）**（原表述保留于上）。引用时应写明「本机 2.14.87 / 官方最新 2.14.502，未升级」。来源：<https://miuirom.org/miwifi/mi-router-4c>
> 另注：本文多处写「8 个 IoT 设备」，与设备清单不符——[[network-analysis-2026-07-28]] 第四节 13 台中 `ESP_`/`ESP-` 前缀实为 **7 台**（另 1 台 Unknown）。

## API 探测结果

```
可用:
  /api/xqnetwork/set_wifi       WiFi 参数修改
  /api/xqnetwork/wan_info       WAN 口信息
  /api/xqnetwork/lan_info       LAN 口信息
  /api/misystem/status          系统状态 (CPU/RAM/WAN吞吐)
  /api/misystem/devicelist      设备列表
  /api/xqsystem/login           登录
  /api/xqsystem/bdata           硬件信息 (免认证)

不可用:
  /api/xqnetwork/dns_info       404
  /api/xqnetwork/firewall_info  404
  /api/xqnetwork/qos_info       500 (无 QoS 模块)
  /api/xqnetwork/wifi_advanced  404
  /api/xqnetwork/nat_info       404
  /api/xqsystem/upgrade_info    404
```

**结论**: R4CM API 非常有限，高级设置（DNS/QoS/防火墙/WiFi高级参数）都需 SSH 进入路由器 (root@[IP已脱敏]) 后通过 UCI 命令或直接编辑 `/etc/config/*` 完成，不可在 Windows 本机执行。

## 可优化点 (需 SSH)

> [!warning] R4CM 实测无 uci 命令
> R4CM 无 `uci` 命令（见 [[ROUTER-DEEP-EXPLORATION]]），以下 uci 示例仅为通用 OpenWrt 语法；在 R4CM 上需改用直接编辑 `/etc/config/*` 的方式执行（同样需先 SSH 进入 root@[IP已脱敏]）。

### 1. MTU 优化

当前: 1500 (标准以太网)
建议: 若上游是 PPPoE，MTU 应为 1492。当前双 NAT 环境可测试 1492 或 1480。

> [!warning] 更正（2026-09-13）：「当前双 NAT 环境可测试 1492 或 1480」**与同页 WAN 类型相抵**（原表述保留于上）。
> 本页「硬件规格」表记 WAN 为 **`eth0.2` DHCP**（不是 PPPoE）——1492 只在 PPPoE 链路上是硬要求，DHCP/以太网链路上改 MTU 属试探性调整，需先用 `ping -M do -s <size>` 探测路径 MTU，不能无条件推荐。前半句「若上游是 PPPoE，MTU 应为 1492」已自带条件，问题只在后半句。

```bash
# 需 SSH 进入路由器 (root@[IP已脱敏]) 后执行，勿在 Windows 本机运行
uci set network.wan.mtu='1492'
uci commit network
ifup wan
```

### 2. DNS 优化

当前: WAN DNS → `[IP已脱敏]` (上游路由器)
问题: 上游路由器再转发 DNS，多一跳延迟。
建议: 直接设置公共 DNS。

```bash
# 需 SSH 进入路由器 (root@[IP已脱敏]) 后执行，勿在 Windows 本机运行
uci set network.wan.peerdns='0'
uci add_list network.wan.dns='[IP已脱敏]'
uci add_list network.wan.dns='[IP已脱敏]'
uci commit network
```

### 3. WiFi 高级参数

| 参数 | 默认值 | 建议值 | 原因 |
|------|--------|--------|------|
| beacon_interval | 100ms | 200ms | 8个IoT设备时减少beacon开销 |
| dtim_period | 2 | 3 | IoT设备省电，减少唤醒频率 |
| rts_threshold | 2347 | 1500 | 8个IoT设备时减少冲突 |
| frag_threshold | 2346 | 2346 | 保持默认（分片降低吞吐） |
| short_preamble | 1 | 1 | 保持（提高效率） |
| wmm | 1 | 1 | 保持（QoS必需） |
| isolate | 1 | **0** | 已通过API设置，需永久写入 |

> [!warning] 补疏漏（2026-09-13）：「`rts_threshold` 2347 → 1500（8 个 IoT 设备时减少冲突）」原表**只给结论，没有机制、代价与回滚**。
> OpenWrt 文档确认 `rts` 即 RTS/CTS 阈值（默认由驱动决定）。补：**机制**——阈值降到 1500 意味着大于该值的帧先发 RTS/CTS 握手再传，密集小报文场景可减少碰撞；**代价**——控制帧开销上升，单流吞吐可能下降，且 802.11n 的 2347 上限常被驱动用于「等效关闭 RTS」；**回滚**——把 `rts` 改回 `2347`（或删除该 option 回到 driver default）并 `wifi reload`，用同一测速口径复测。**验收判据**：延迟尖峰频率与吞吐两项都要测，不能只看冲突率。来源：<https://openwrt.org/docs/guide-user/network/wifi/basic>

> [!warning] 更正（2026-09-13）：上表与下方示例块**用了两套互不相同的参数名**（原表写 `beacon_interval` / `rts_threshold` / `frag_threshold` / `short_preamble`，示例块写 `beacon_int` / `dtim_period` / `rts`）。
> 查 OpenWrt wireless 文档：`/etc/config/wireless` 侧的 UCI 名是 **`rts`**（「Override the RTS/CTS threshold」，默认 driver default）与 **`frag`**，并非 `rts_threshold` / `frag_threshold`；文档同时提供透传项 **`hostapd_bss_options`**（「Pass any custom options to hostapd-*.conf. Values passed as-is」）用于写 hostapd 原生键名（如 `beacon_int`、`short_preamble`）。**示例块的写法更接近正确**；上表名称为通用 hostapd 术语，直接抄进 `/etc/config/wireless` 不会生效。来源：<https://openwrt.org/docs/guide-user/network/wifi/basic>

```bash
# /etc/config/wireless 中修改
config wifi-iface
    option device 'radio0'
    option network 'lan'
    option mode 'ap'
    option ssid '302-1'
    option encryption 'psk2+ccmp'
    option key '19890520'
    option isolate '0'
    option beacon_int '200'
    option dtim_period '3'
    option rts '1500'
    option wmm '1'
```

### 4. 连接跟踪优化

当前: 默认 conntrack 参数 (max 根据 RAM 自动计算)
13 设备下可能有连接数压力。

> [!warning] 更正（2026-09-13）：上句「默认 conntrack 参数…自动计算」与下方 `nf_conntrack_max=16384` **互相打架——该值就是现值，写了等于没改**（原表述保留于上）。
> [[ROUTER-DEEP-EXPLORATION]] 实测记录 `conntrack_max = 16384`，即「优化」把系统已经生效的值又赋了一遍。若确需调整，应先读取实际 `nf_conntrack_count` / `nf_conntrack_max` 与内存水位再定量，并在改动后复测；仅 `tcp_timeout_established` / `udp_timeout` 两项属真正的时间参数调整。

```bash
# /etc/sysctl.conf
net.netfilter.nf_conntrack_max=16384
net.netfilter.nf_conntrack_tcp_timeout_established=3600
net.netfilter.nf_conntrack_udp_timeout=30
net.netfilter.nf_conntrack_udp_timeout_stream=120
```

### 5. 内核网络参数

```bash
# 减少缓冲区膨胀
net.core.rmem_max=4194304
net.core.wmem_max=4194304
net.ipv4.tcp_rmem='4096 87380 4194304'
net.ipv4.tcp_wmem='4096 65536 4194304'
# 启用 TCP 窗口缩放
net.ipv4.tcp_window_scaling=1
# 减少 TIME_WAIT
net.ipv4.tcp_fin_timeout=15
```

### 6. 双 NAT 消除

> [!info] 双 NAT 消除方案
> 
> 当前: R4CM ([IP已脱敏]) → 上游 ([IP已脱敏]) → WAN
> 
> **方案 A**: 上游改桥接模式 → R4CM 直接拨号 (消除一层 NAT)
> **方案 B**: R4CM 改 AP 模式 → 由上游统一 NAT (消除一层 NAT)
> 
> 方案 B 最简单，但会失去 R4CM 的路由功能（DHCP/端口转发等）。

### 7. WiFi 信道固定

当前: 路由器自动选信道 (当前信道 8)
建议: 手动扫描后固定到最干净的信道 (1/6/11 之一)。

```bash
# 通过 API 设置
curl "http://[IP已脱敏]/cgi-bin/luci/;stok=TOKEN/api/xqnetwork/set_wifi" \
  --data "channel=11"
```

## 无需 SSH 的优化 (已执行)

| 优化 | 方法 | 状态 |
|------|------|------|
| AP 隔离关闭 | API `set_wifi` → `isolate=0` | 已执行 (临时) |
| 信道调整 | API `set_wifi` → `channel=1` | 路由器自动选了 8 |
| 40MHz 带宽 | API `set_wifi` → `bandwidth=40` | API 返回成功但未生效 |

## 路由器优化优先级

> [!info] 优化优先级
> 
> ```
> P0: 获取 SSH 访问 (如需，重新运行 CVE-2019-18370)
> P1: 永久 AP 隔离 + WiFi 高级参数 (beacon_int, rts)
> P2: DNS 直连 [IP已脱敏] + MTU 调整
> P3: 双 NAT 消除
> ```

## 硬件升级建议

> [!warning] R4CM 核心限制与升级建议
> 
> 当前 R4CM 核心限制:
> - 仅 2.4GHz (协商速率上限 72.2Mbps 单流)
> - 64MB RAM (连接数容量有限)
> - 单核 575MHz MIPS (无硬件 NAT 加速)
> 
> 推荐升级:
> - **小米 AX3000** (~¥200): WiFi 6, 256MB, 双核, 硬件 NAT
> - **小米 AX6S** (~¥300): WiFi 6, 256MB, 双核, 160MHz
> - 升级后收益: 5GHz 协商速率 600+ Mbps, 延迟稳定 <5ms

> [!warning] 补疏漏（2026-09-13）：上表价格为**库内估价、无厂商来源**，且**未说明与客户端网卡的匹配度**（原表述保留于上）。
> 本机网卡是 **QCA9377（2.4/5GHz 802.11ac，1×1）**，不支 WiFi 6——换 AX3000/AX6S 后，5GHz 侧协商上限由网卡决定（11ac 1×1 ≈ 433Mbps 理论），**「600+ Mbps」只在同时更换网卡时才成立**。采购前请以厂商规格页复核价格与射频参数，并明确收益预期按客户端网卡实测算。

## Related

- [[Network-KB-Home]] — 网络知识库主页
- [[GUIDE]] — 使用指南
- [[ROUTER-FULL-CAPABILITY]] — 路由器完全能力手册
- [[ROUTER-DEEP-EXPLORATION]] — 路由器深度探索报告

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | WiFi 高级参数表与示例块用了两套参数名（`beacon_interval`/`rts_threshold`/`frag_threshold`/`short_preamble` vs `beacon_int`/`rts`） | 加更正块：OpenWrt UCI 名为 `rts`/`frag`，hostapd 原生键需走 `hostapd_bss_options` 透传；示例块写法更接近正确 |
| 补疏漏 | 「`rts_threshold` 2347 → 1500」只有结论 | 加注：补机制（RTS/CTS 门限）、代价（控制帧开销、吞吐可能下降）、回滚（改回 2347 / `wifi reload`）与双指标验收判据 |
| 纠错 | MTU 节「当前双 NAT 环境可测试 1492 或 1480」与同页 WAN=eth0.2 DHCP 相抵 | 保留原句并加更正块：1492 是 PPPoE 硬要求，DHCP 链路需先 `ping -M do` 探路径 MTU |
| 纠错 | 连接跟踪节「默认 conntrack 参数」与所设 `nf_conntrack_max=16384` 打架（等于现值，空操作） | 保留原句并加更正块：库内实测现值即 16384，真正可调的只有 timeout 两项 |
| 补疏漏 | 硬件升级建议价格无来源，且未说明与 QCA9377（11ac 1×1）的匹配度 | 加注：AX3000/AX6S 收益受客户端网卡封顶，「600+ Mbps」需同时换网卡；价格待厂商规格页复核 |
| 纠错 | 硬件表固件 `2.14.87` 无对照；文中多处「8 个 IoT 设备」失实 | 加更正块：官方最新 2.14.502（2024-02-21）；ESP 前缀实为 7 台（见 [[network-analysis-2026-07-28]]） |

相关：[[CORRECTIONS]] · [[AGENTS]]

