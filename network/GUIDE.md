---
title: 日常使用指南
aliases: [使用指南, 操作手册]
tags: [network/guide, network]
created: 2026-07-27
updated: 2026-09-13
status: stable
---

# 日常使用指南

> [!tip] 从这里开始
> 日常无需操作。增强的多节点代理 + 路由器优化已自动运行。

## 代理操作

### 订阅更新后

```powershell
powershell -File "scripts/enhance-config.ps1" -DryRun   # 预览
powershell -File "scripts/enhance-config.ps1" -Apply    # 应用
```

### 速度变慢 / 视频卡顿

```powershell
powershell -File "scripts/enhance-config.ps1" -Status
```

若显示 `Proxy outbounds: 1`，重新 `-Apply`。

> [!warning] 更正（2026-09-13）：只数 outbounds 个数**会漏判**（原表述为「若显示 `Proxy outbounds: 1`，重新 `-Apply`」）。
> 复核 Xray-core 分发器源码：当路由规则引用了不存在的 outboundTag 时，运行期只打印 `non existing outTag: <tag>` 的 **warning**，随后 `Close(link.Writer)` / `Interrupt(link.Reader)` 掐断该连接——**不会回落默认出站**（源码注释明确要求不得回落）。因此出站数量正常、规则字段写错时，表现为「只有命中该规则的域名全挂、其他站点正常」。
> 补充判据：① `-Status` 仍要跑，但看的是**路由规则里用的是 `balancerTag` 还是 `outboundTag`**；② 查 xray 日志是否出现 `non existing outTag`；③ 现象与 [[v2rayn-balancer-复盘-2026-08-09]] 一致时按该复盘处理。来源：<https://raw.githubusercontent.com/XTLS/Xray-core/main/app/dispatcher/default.go>

### 应急回滚

```powershell
# 目标为 v2rayN 的 binConfigs 目录（<你的v2rayN目录> 替换为实际路径）
# 本机实际: D:\Document\Download\v2rayN-windows-64-desktop\v2rayN-windows-64\binConfigs\config.json
copy "scripts/config.json.bak-20260728" "<你的v2rayN目录>\binConfigs\config.json"
```

> [!danger] 更正（2026-09-13）：该回滚命令当前**不可用**（原表述为直接 `copy "scripts/config.json.bak-20260728" ...`）。
> 全库递归检索 `config.json.bak*` / `*.bak-2026*` **命中 0 个**：`scripts/` 下只有 `enhance-config.ps1`、`v2rayN-config-hook.ps1`、`xray-config-v2-working.json`、`xray-config-fixed.json`、`xray-config-optimized.json`、`generate-xray-config.sh` 等，并没有这份 `config.json.bak-20260728`。**回滚前先确认备份文件真实存在**；确认缺失时，改用 v2rayN 自身重新生成 `config.json`，或以 `scripts/xray-config-v2-working.json` 作为已知可用基线。

> [!note] 代理架构
> 主节点 p1d2 处理所有流量，多节点仅故障 fallback。DNS 走 p1d2。Mux 全关（VLESS Vision 兼容）。详见 [[ARCHITECTURE]]。

> [!warning] 更正（2026-09-13）：上句「主节点 p1d2 处理所有流量，多节点仅故障 fallback」与库内现状冲突（原表述保留于上方引用块）。
> [[FINAL-SUMMARY]] 的「当前生效配置」记的是 `Balancer: SG1 + US1 + US3 + JP1 (leastPing)，fallback: us1`，路由为「Google → balancer、其他 → balancer」——即**日常出口是 balancer 池，并非单节点 p1d2**。DNS 项不冲突：FINAL-SUMMARY 的「境外走 Cloudflare via p1d2」与本句一致。**以 [[ARCHITECTURE]] 决策 3/4/5 与 FINAL-SUMMARY 现役配置为准**，本页旧表述仅作历史记录。

## 路由器操作

```bash
bash scripts/router_ssh.sh "command"   # SSH
```

已执行优化: AP 隔离关闭、OTA 禁用、遥测禁用、DNS 缓存 2000、UPnP 禁用。详见 [[ROUTER-OPTIMIZATION]] 和 [[ROUTER-FULL-CAPABILITY]]。

## 故障排查

| 现象 | 原因 | 参考 |
|------|------|------|
| 代理不可用 | xray 未运行 | 重启 v2rayN 核心 |
| Google/YouTube 打不开但其他正常 | v2rayN 生成 balancer 无效规则（outboundTag） | [[v2rayn-balancer-复盘-2026-08-09]]（watcher 已自动修复） |
| 视频卡顿 | WiFi 延迟尖峰 | [[FINAL-SUMMARY]] |
| 路由器连不上 | dropbear 挂掉 | [[ROUTER-FULL-CAPABILITY#九、SSH 连接]] |

> [!warning] 补疏漏（2026-09-13）：上表「代理不可用 → xray 未运行 → 重启 v2rayN 核心」缺了**最常见的一类成因——v2rayN 与 xray-core 版本不配对**（原表述只给了「重启核心」一步）。
> 上游把版本配对视作硬约束：v2rayN `7.19.5` 的 release 说明写明「跟进 xray 配置，需要使用 xray-core v26.2.6」，同版还有「添加 一键生成策略组」「重构配置生成代码」。因此「核心起不来/起来也不通」时，先核对 v2rayN ↔ xray-core 的版本配对，再谈重启；本文全文未记任何 xray/v2rayN 版本号，排查时请以 [[ARCHITECTURE]]、[[FINAL-SUMMARY]] 及 v2rayN 发布说明为准。来源：<https://api.github.com/repos/2dust/v2rayN/releases/tags/7.19.5>

## 相关知识

- [[Network-KB-Home]] — 知识库首页
- [[FINAL-SUMMARY]] — 完整优化总结
- [[ARCHITECTURE]] — 架构设计文档
- [[OPTIMIZATION-AUDIT]] — 优化审计清单

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 应急回滚 `copy "scripts/config.json.bak-20260728"` 指向不存在的文件 | 保留原命令并加 `danger` 更正块：全库递归检索该备份 0 命中，给出「先确认存在 / 用 v2rayN 重生成或 `xray-config-v2-working.json` 兜底」的替代路径 |
| 纠错 | 「主节点 p1d2 处理所有流量，多节点仅故障 fallback」与现役配置冲突 | 保留原句并加更正块，指向 [[FINAL-SUMMARY]] 的 balancer 池 + fallback: us1；同时说明 DNS 半句并不冲突 |
| 补疏漏 | 「`Proxy outbounds: 1` 就重新 `-Apply`」判据过浅 | 加判据：outboundTag 引用失效只在运行期打 `non existing outTag` warning 且不回落默认出站，需查规则字段与 xray 日志（Xray-core `default.go`） |
| 补疏漏 | 排查表「代理不可用」只给「重启核心」，未提版本配对 | 加版本配对约束：v2rayN 7.19.5 发布说明要求配 xray-core v26.2.6 |

相关：[[CORRECTIONS]] · [[AGENTS]]
