---
title: 架构设计文档
aliases: [Architecture, 架构]
tags: [network/architecture, network/proxy, network]
created: 2026-07-28
updated: 2026-09-13
status: stable
---
# 网络优化架构设计文档

> [!info] 文档定位
> 本文档是 [[Network-KB-Home]] 的核心参考，详细记录了网络代理优化架构的设计目标、演进历程和关键技术决策。完整分析见 [[FINAL-SUMMARY]]，优化审计见 [[OPTIMIZATION-AUDIT]]，路由器能力分析见 [[ROUTER-FULL-CAPABILITY]]。
## 一、设计目标

| 目标 | 含义 |
|------|------|
| 用户无感 | 不需要手动维护配置、不需要重启切换 |
| 自适应 | 订阅更新后自动发现新节点，路由器变化后自动适配 |
| 安全 | 保留 Reality 伪装/SNI 指纹，CN IP 直连不泄露，无额外开放端口 |
| 灵活 | 不硬编码节点，不覆盖 v2rayN 原生设置 |
| 容错 | 任何变更先验证后应用，失败自动回滚 |

## 二、架构演进

### Phase 1: 固定多节点配置 (xray-config-optimized.json) — **废弃**

> [!bug] Phase 1 关键问题
> 1. Mux 开启 → VLESS Vision 流被打乱 → Telegram 视频卡住
> 2. 无 catch-all 规则 → 非 Google 境外流量走到第一个出站（韩国节点），不走 balancer
> 3. `outboundTag` 引用 balancer → xray 报 `non existing outTag`
> 4. DNS 走 balancer、数据走第一个出站 → CDN 边缘节点不匹配
> 5. 节点硬编码 → 订阅更新后被 v2rayN 覆盖

**结论**: 固定配置不可行，必须"增强"而非"替换"。

### Phase 2: 定时任务方案 (auto-optimizer.ps1) — **废弃**

> [!warning] 定时轮询的问题
> - 定时轮询浪费资源
> - 节点变动和脚本执行之间存在窗口期
> - 不是事件驱动

### Phase 3: FileSystemWatcher Hook (v2rayn-config-hook.ps1) — **备选**

> [!info] 设计思路
> 监听 v2rayN 的 config.json 写入事件，在 v2rayN 生成新配置后、xray 启动前拦截并增强。

**流程**:
```
v2rayN 写入 config.json
    ↓ FileSystemWatcher 检测变化
    ↓ 延迟 3s（等待写入完成）
    ↓ 检查冷却期（5 分钟，防止死循环）
    ↓ 检查是否已是多节点配置
    ↓ 从 configTest 文件发现节点 + Ping 测速
    ↓ 增强配置（添加出站 + balancer）
    ↓ 写入 config.json
    ↓ v2rayN/xray 读取增强后的配置
```

**优点**: 事件驱动，资源占用极低，完全透明
**缺点**: 依赖 PowerShell 进程常驻；v2rayN 重写配置时会再次触发

**状态**: 代码已完成，作为备选方案保留。当前使用 Phase 4。

### Phase 4: 按需增强脚本 (enhance-config.ps1) — **当前方案**

> [!info] 当前方案
> 订阅更新后手动触发一次，脚本完成测速、评分、配置生成、验证、应用的完整流程。日常无需运行。

**流程**:
```
1. 读取 v2rayN 当前 config.json
2. 从 configTest*.json 发现所有可用节点
3. Ping 所有节点 → 过滤 < 500ms
4. 排除与当前主代理相同地址的节点
5. 去重（每个地址只保留最佳端口）
6. 选 Top 3 不同地理位置的节点
7. 在 v2rayN 原始配置基础上增量添加出站
8. 保留所有原生路由（CN直连/DNS/Reality伪装）
9. 添加 balancer + observatory
10. xray -test 语法验证
11. 原子写入（失败自动回滚原配置）
12. 重启 xray
```

## 三、核心设计决策

### 决策 1: 增强而非替换

**选择**: 读取 v2rayN 的原生配置，只增量修改出站和路由。
**原因**: v2rayN 管理着路由策略（CN 绕过/DNS 分流），直接替换会丢失这些设置。

### 决策 2: Mux 永久禁用

> [!warning] Mux 与 Vision 不兼容
> **选择**: 所有 VLESS+Vision 出站 `mux: false`。
> **原因**: VLESS XTLS-Vision 依赖精确的包时序进行 TLS 伪装。Mux 多路复用会交错不同流的数据包，破坏 Vision 的流顺序，导致队头阻塞。实测：开启 Mux → Telegram 视频卡住。

> [!warning] 更正（2026-09-13）：「不兼容」是**推断而非上游结论**（原表述为「Mux 与 Vision 不兼容」，决策本身不变——仍然全关 Mux）。
> 复核上游两处：① Xray 出站文档对 Mux 的定性是**性能取舍**——「Mux 是为了减少 TCP 的握手延迟而设计，而非提高连接的吞吐量。使用 Mux 看视频、下载或者测速通常都有反效果」，并未声称与 XTLS-Vision 协议层不兼容；② commit `4f601530`（RPRX，2023-04-14，*Allow multiple XUDP in Mux when using XTLS Vision (client side)*）**已删除** Vision 出站对 Mux 的 `doesn't support Mux` 警告，即当前上游允许该组合、只是不推荐。保留原决策的依据是**库内实测**（开 Mux → Telegram 视频卡住），引用时应写作「实测组合劣化/不推荐」，而不是「协议不兼容」。来源：<https://xtls.github.io/config/outbound.html>、<https://github.com/XTLS/Xray-core/commit/4f601530fabf045b0dc08e5526426ba7331c1133>

### 决策 3: DNS 走固定代理

**选择**: DNS 模块路由到原始代理 (`proxy` tag)，不使用 balancer。
**原因**: DNS 解析时，CDN 根据 DNS 出口 IP 返回最优边缘节点。如果 DNS 走 balancer（可能选韩国节点），数据走另一个节点，CDN 边缘节点不匹配 → 视频加载失败。

### 决策 4: catch-all → balancer

**选择**: 末尾添加 `network: tcp,udp → balancerTag: balancer`。
**原因**: 没有 catch-all 时，未匹配流量走到 `outbounds[0]`（第一个出站），绕过了 balancer。

### 决策 5: balancerTag 而非 outboundTag

**选择**: 路由规则中引用 balancer 时用 `balancerTag` 字段。
**原因**: xray 的路由分发器对 `outboundTag` 只在出站列表中查找，对 `balancerTag` 在 balancers 列表中查找。用错字段 → `non existing outTag` 错误。

> [!check] 已核验（2026-09-13）：本条**结论与方向均正确**，无需改动。
> 上游路由文档原文：「转发至它所指定的 outboundTag 或 balancerTag」「**balancerTag 和 outboundTag 须二选一。当同时指定时，outboundTag 生效**」「此负载均衡器的标识，用于匹配 RuleObject 中的 balancerTag」；分发器侧对查不到的 outTag 打印 `non existing outTag: ` 并 `Close`/`Interrupt`，不回落默认出站。来源：<https://xtls.github.io/config/routing.html>、<https://raw.githubusercontent.com/XTLS/Xray-core/main/app/dispatcher/default.go>

> [!bug] 2026-08-09 实测：v2rayN 7.19.5 GUI 均衡组自己也生成 `outboundTag`
> 在 GUI 配置均衡组后，v2rayN 生成 `{"domain":["geosite:google"],"outboundTag":"balancer"}` 的无效规则 → Google 全挂、其余网站正常。已用 watcher（`fix_balancer_watcher.ps1`）自动改写为 `balancerTag` 并重启 xray。完整事故复盘见 [[v2rayn-balancer-复盘-2026-08-09]]。**注意：本决策此前只防住了外部脚本，没防住 v2rayN 原生生成。**

### 决策 6: 排除原始代理地址

**选择**: 候选节点中排除与主代理相同 IP 的节点。
**原因**: 同一服务器不同端口没有地理多样性价值。不排除的话，39 个订阅节点中 ~25 个是 p1d2 不同端口，选出来的全是同一台机器。

> [!warning] 更正（2026-09-13）：括号内两个数字**与库内数据不符且无统计口径**（原表述为「39 个订阅节点中 ~25 个是 p1d2 不同端口」）。
> 库内唯一节点清单 `scripts/proxy-nodes.json` 自述为「17 节点, 4 供应商」（实为 ranking 7 + unreachable 6 + slow 4），其中 p1d2 仅 **1** 条；全库亦无 `configTest*.json` 可复算。**决策 6 本身（排除与主代理同 IP 的候选节点）成立**，但引用时应改述为「同一 IP 会重复占用候选位」，不要再引用 39/~25 这两个数。

### 决策 7: 安全约束

> [!info] 安全约束一览
> | 约束 | 实现 |
> |------|------|
> | Reality 指纹伪装 | 保留 v2rayN 为每个节点配置的独立 SNI/公钥/fingerprint |
> | DNS 防泄露 | CN 域名 → Alibaba DNS（直连）；境外 → Cloudflare DNS（通过代理） |
> | CN IP 直连 | 保留 `geoip:cn → direct` 和 `geosite:cn → direct` |
> | UDP 443 阻断 | 保留 `port:443, network:udp → block` 防 QUIC 绕过代理 |
> | 无开放端口 | 代理仅监听 127.0.0.1:10808，不对局域网开放 |

> [!warning] 补疏漏（2026-09-13）：上表「UDP 443 阻断」只写了 `block` 一种处置，**漏了上游自带的代理 UDP 443 的三档开关**（原表述只给「保留 `port:443, network:udp → block` 防 QUIC 绕过代理」）。
> Xray 出站文档的 `xudpProxyUDP443` 有三种取值：默认 `reject`（「拒绝流量（一般浏览器会自动回落到 TCP HTTP2）」）、`allow`（「允许走 Mux 连接」）、`skip`（「不使用 Mux 模块承载 UDP 443 流量……VLESS 会使用 UoT」）。即「代理 UDP 443」并非没有上游方案——需要放行 QUIC 时可用 `skip`/UoT，比全局 `block` 更可控。当前选择 `block` 属**保守取舍**，不是唯一解。来源：<https://xtls.github.io/config/outbound.html>

## 四、文件说明

| 文件 | 状态 | 说明 |
|------|------|------|
| `enhance-config.ps1` | **当前** | 按需增强脚本，订阅更新后运行 |
| `v2rayn-config-hook.ps1` | 备选 | FileSystemWatcher 事件驱动 hook |
| `auto-optimizer.ps1` | 废弃 | 定时任务方案 |
| `generate-xray-config.sh` | 废弃 | Bash 版配置生成器 |
| `score-nodes.ps1` | 废弃 | 复合评分原型（速度测试不稳定） |
| `xray-config-v2-working.json` | 当前生效 | 最终增强配置 |
| `xray-config-optimized.json` | 存档(有Bug) | v1 固定配置 |
| `xray-config-fixed.json` | 存档(有Bug) | v2 修复尝试 |
| `config.json.bak-20260728` | 备份 | v2rayN 原始配置 |
| `proxy-nodes.json` | 参考 | 代理节点速查表 |
| `network-analysis-2026-07-28.md` | 参考 | 完整网络分析 |

> [!warning] 更正（2026-09-13）：上表 `config.json.bak-20260728` 一行**指向不存在的文件**（原表述记为「备份 | v2rayN 原始配置」）。
> 全库递归检索 `config.json.bak*` / `*.bak-2026*` **命中 0 个**；表中其余实体均可对上（`xray-config-v2-working.json`、`xray-config-optimized.json`、`xray-config-fixed.json`、`proxy-nodes.json` 均在 `network/scripts/` 下）。该行仅作历史登记保留，**不要据此执行回滚**，替代路径见 [[GUIDE]] 应急回滚一节。

## 五、未来可能的增强
1. **下载速度综合评分**: 在 Ping 排序后对 Top 节点做 1MB 下载测试，延迟+速度加权评分（30/70）。当前因临时 xray 实例启动不稳定暂缓。
2. **Hook 常驻模式**: 将 FileSystemWatcher 方案作为 v2rayN 的透明 hook 启用，订阅更新后全自动处理。当前用户可以按需运行 enhance-config。
3. **v2rayN 原生多选**: v2rayN 本身支持多选服务器后自动生成 balancer 配置（`GenerateClientMultipleLoadConfig`），如 v2rayN 后续版本在 GUI 中暴露此功能，则可完全替代外部脚本。

> [!warning] 更正（2026-09-13）：上述方法名**在上游源码中不存在**，改用可核对表述（原表述为 `GenerateClientMultipleLoadConfig`）。
> 复核 v2rayN 源码 `ServiceLib/Handler/ConfigHandler.cs` 全文：检索 `GenerateClientMultipleLoadConfig` **命中 0**，只见 `MultipleLoad = EMultipleLoad.LeastPing`（2 处）；v2rayN `7.19.5` 的 release 说明写作「添加 **一键生成策略组**」。建议改述为：**「策略组配置 `MultipleLoad = LeastPing`（GUI 侧即『一键生成策略组』）」**。来源：<https://raw.githubusercontent.com/2dust/v2rayN/master/v2rayN/ServiceLib/Handler/ConfigHandler.cs>、<https://api.github.com/repos/2dust/v2rayN/releases/tags/7.19.5>

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 加厚 | 决策 5「balancerTag 而非 outboundTag」原无来源 | 加「已核验」块并登记上游路由文档与 Xray-core `default.go`（含「同时指定时 outboundTag 生效」） |
| 纠错 | 决策 2 把「Mux 与 XTLS-Vision」写成协议层不兼容 | 保留原决策与实测结论，加注：上游定性为性能取舍，且 commit `4f601530`（2023-04-14）已移除 `doesn't support Mux` 警告 |
| 补疏漏 | 安全约束表「UDP 443 阻断」未提上游 `xudpProxyUDP443` 三档 | 加注 `reject`(默认)/`allow`/`skip`(UoT) 三档语义，说明 `block` 是保守取舍而非唯一解 |
| 纠错 | 决策 6 依据「39 个节点中 ~25 个是 p1d2 端口」无统计口径且与库内 17/1 冲突 | 保留原句并加更正块：决策成立、数字不可引用 |
| 纠错 | 文件表 `config.json.bak-20260728` 指向不存在文件 | 保留该行并加更正块：全库 0 命中，禁止据此回滚，改见 [[GUIDE]] |
| 纠错 | 增强项 3 引用不存在的方法名 `GenerateClientMultipleLoadConfig` | 保留原句并加更正块，改述为 `MultipleLoad = LeastPing` / 「一键生成策略组」 |

相关：[[CORRECTIONS]] · [[AGENTS]]

