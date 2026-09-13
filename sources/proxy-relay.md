---
title: 来源登记 — 代理与中继
aliases: [sources-proxy-relay, 代理中继来源登记]
tags: [meta, reference, source]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 来源登记 — 代理与中继

> [!abstract] 本页用途
> 存放「代理与中继」主题的来源条目，供 [[URL-Lookup]] 检索。
> 可读版见 [[URL-REGISTRY#3-代理与中继本库自有资产]]。

## 现役资产

- 来源:: cache-relay 实现
  use_when:: 要复用或排障现役中继（:8790）
  url:: file:///D:/Document/local/knowledge/scripts/claude-ops-deployments/cache-relay/cache-relay.mjs
  answers:: 多源缓存对齐策略、provider 自动识别、软回滚开关、健康检查路径；**现役状态的确认方法（2026-09-13 补）**：`netstat -ano | findstr :8790` 应见 LISTENING，或健康检查路径返回 200——状态结论必须附「确认命令 + 确认日期」。本条此前只有「现役」字样，无判据、也无上次确认时间（`verified:: 2026-09-12` 是登记日期，不代表当日复跑过）
  authority:: 高
  verified:: 2026-09-12

- 来源:: 部署管控框架
  use_when:: 任何生产改动前，确认部署四规则（记录/预检/逃生/审计）
  url:: wikilink://deployment-framework
  answers:: 四规则定义、deploy.sh 与 rollback.sh 约定
  authority:: 高
  verified:: 2026-09-12

- 来源:: 部署审计日志
  use_when:: 查历史部署与逃生记录
  url:: file:///D:/Document/local/knowledge/scripts/claude-ops-deployments/deployment-log.md
  answers:: 每次部署的时间/变更/预检/E2E/逃生/commit
  authority:: 高
  verified:: 2026-09-12

## 已退役资产

- 来源:: ds2ox-proxy 脱敏归档
  use_when:: 要查已退役路由代理的实现或缺陷
  url:: file:///D:/Document/local/knowledge/scripts/claude-ops-deployments/ds2ox-proxy/ds2ox-proxy.mjs
  answers:: 路由改写逻辑、熔断策略、3 处设计缺陷（D1/D2/D3，见本页下方小表）；密钥已外置
  authority:: 高
  verified:: 2026-09-12

> [!note] ds2ox 的 3 处设计缺陷（2026-09-13 补）
> 本页原来只在上面 `answers` 里写「3 处设计缺陷」而未展开，读者必须跳到 [[security-audit]] 才知道 D1/D2/D3。完整描述见 [[security-audit]]（D1 无鉴权 / D2 无 Host 校验 / D3 抢占即劫持）与 [[ds2ox-proxy-retirement]]；本页只是索引。

| 编号 | 一句话机制 | 对应要求 |
|---|---|---|
| D1 | 无入站鉴权——本机任何进程都能直接使用该代理 | 入站鉴权：无 token 必须 401 |
| D2 | 无 `Host` 头校验 | 伪 `Host` 必须 400 |
| D3 | 固定监听端口，被抢占即劫持 | 端口被占必须失败退出（或改用本地套接字） |

- 来源:: ds2ox-proxy 退役归档说明
  use_when:: 处置该代理的文件与凭据，或确认残留复活路径
  url:: wikilink://ds2ox-proxy-retirement
  answers:: 退役判定证据、凭据处置顺序、配置来源
  authority:: 高
  verified:: 2026-09-12

## 事故复盘（同类问题先查这里，避免重犯）

- 来源:: 代理部署事故复盘
  use_when:: 部署代理前，查已有踩坑记录
  url:: wikilink://claude-proxy-deployment-postmortem
  answers:: 代理部署中的失效模式
  authority:: 高
  verified:: 2026-09-12

- 来源:: cancel/retry hook 事故
  use_when:: 排查代理的取消/重试行为异常
  url:: wikilink://proxy-cancelretry-hook-incident
  answers:: cancel 与 retry 交互引发的问题
  authority:: 高
  verified:: 2026-09-12

- 来源:: 代理重启事故
  use_when:: 排查代理重启后的状态一致性问题
  url:: wikilink://claude-proxy-restart-incident
  answers:: 重启引发的故障与处置
  authority:: 高
  verified:: 2026-09-12

- 来源:: cache-relay 缓存事故
  use_when:: 排查缓存命中率异常
  url:: wikilink://claude-cache-incident-postmortem
  answers:: 缓存失效根因与修复
  authority:: 高
  verified:: 2026-09-12

- 来源:: 端口重绑定方案
  use_when:: 代理端口被占用或需换端口
  url:: wikilink://claude-port-rebind-solution
  answers:: 端口重绑定的做法
  authority:: 中
  verified:: 2026-09-12

- 来源:: 代理韧性优化
  use_when:: 要提升代理在断网/超时下的稳定性
  url:: wikilink://proxy-resilience-optimization-2026-07-09
  answers:: 代理韧性优化措施
  authority:: 中
  verified:: 2026-09-12

> [!tip] 新写代理时的最低要求（从 ds2ox 的 3 处缺陷反推）
> ① 入站鉴权 ② `Host` 头校验 ③ 不固定监听端口或改用本地套接字；
> ④ 密钥不落地（参照 cache-relay 的透传头做法）。

对应验收判据（2026-09-13 补，原 tip 只有结论、无验收方法）：

| 缺陷 | 要求 | 验收方法 |
|---|---|---|
| D1 无入站鉴权 | 入站必须鉴权 | 不带 token 请求 → 必须 **401** |
| D2 无 `Host` 校验 | 校验 `Host` 头 | 伪 `Host` 请求 → 必须 **400** |
| D3 固定端口被抢占即劫持 | 不固定监听端口或改用本地套接字 | 先占住端口再启动 → 必须**失败退出**，不得静默改口 |
| — | 密钥不落地（参照 cache-relay 透传头） | 查配置/抓包确认本地无密钥明文（`~/.cache-relay/config.json` 只放 `authTokenSource` 指针） |

## A2 复核新增（2026-09-13）：兜底目标与生效路由

- 来源:: OpenRouter 兜底目标端点（`z-ai/glm-5.3-flash`）
  use_when:: 兜底改投前确认目标模型在架；或核对兜底成本
  url:: https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints
  answers:: endpoints 实测 26 个；pricing prompt $0.15/M、completion $0.5/M、cache_read $0.03/M
  authority:: 高
  verified:: 2026-09-13

- 来源:: 本机 Claude Code 生效路由配置（两份，取值相反）
  use_when:: 判断请求是否真的经过 cache-relay（:8790）——直连会让缓存对齐与 400 兜底**同时静默失效**
  url:: file:///%USERPROFILE%/.claude/settings.json
  answers:: settings.json L4 `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`（官方直连）+ L6 `ANTHROPIC_MODEL=deepseek-flash[1m]`；`settings.local.json` L3 `=http://127.0.0.1:8790`（走 relay）；合并优先级无公开可引用条目，只能实测判定
  authority:: 高
  verified:: 2026-09-13

- 来源:: cache-relay 兜底配置与密钥来源
  use_when:: 核对兜底 modelMap、authTokenSource 指向与密钥是否落地
  url:: file:///%USERPROFILE%/.cache-relay/config.json
  answers:: `fallback.modelMap` = `{"deepseek-v4-pro[1m]", "deepseek-v4-flash", "*"} → z-ai/glm-5.3-flash`；`authTokenSource` 指向 `~/.claude/oxalpha-settings.json`（顶层键 model/env，密钥未落地到 relay 配置）；`stealth/ox-alpha` 已下线（endpoints 空、不在 445 条列表）
  authority:: 高
  verified:: 2026-09-13

## C4 复核新增（2026-09-13）：代理链路的官方口径（undici / coreutils / Node http）

- 来源:: undici `Client` 文档（HTTP/2 与 ALPN 语义）
  use_when:: 判断「Node 默认 HTTP/2，所以和 Python 代理不兼容」这类说法是否成立（尤其是明文 `http://` 的本地代理链路）
  url:: https://undici.nodejs.org/api/Client
  answers:: `allowH2` 默认 true 但需 *the server assigns it a higher priority through ALPN negotiation*；`h2Options.useH2c` 默认 **false**（*Enforces h2c (HTTP/2 cleartext) for non-HTTPS connections*）；HTTP/2 需服务端在 ALPN 协商中选择——明文链路无 ALPN，仍是 HTTP/1.1
  authority:: 高
  verified:: 2026-09-13

- 来源:: Python 官方 `http.server` 文档
  use_when:: 决定是否用 `http.server` 做生产代理，或解释「curl 能过、真实客户端不通」
  url:: https://docs.python.org/3/library/http.server.html
  answers:: *http.server is not recommended for production.*——只有 HTTP/1.1 基础实现，流式 / SSE 需自行处理
  authority:: 高
  verified:: 2026-09-13

- 来源:: GNU coreutils `timeout` 手册
  use_when:: 解释 timeout 的退出码，或判断「SIGTERM 会波及同 shell 的后台进程」是否成立
  url:: https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html
  answers:: 退出码 124（超时且未用 `--preserve-status`）/125/126/127/137（KILL = 128+9），**无 144**；默认新建独立程序组，只有 `--foreground` 才是 *Don't create a separate background program group*
  authority:: 高
  verified:: 2026-09-13

- 来源:: Node.js `http` 模块文档（ClientRequest / ServerResponse 事件与属性）
  use_when:: 判定「客户端是否取消」「响应是否已写出」——代理里最容易误判的一处
  url:: https://nodejs.org/docs/latest/api/http.html
  answers:: `http.ClientRequest` 的 `close` 现表示 *the request is completed, or its underlying connection was terminated prematurely*；`'abort'` 已 *Deprecated*（v17.0.0 / v16.12.0，原文 *Listen for the 'close' event instead.*）；`writableEnded` / `writableFinished` / `destroyed` 均为文档化属性
  authority:: 高
  verified:: 2026-09-13

- 来源:: nodejs/node 提交 f2dc7c84d6（`close` 语义变更的文档提交）
  use_when:: 追溯「close 曾经 = 底层 socket 关闭」这一行为变更的出处与版本
  url:: https://api.github.com/repos/nodejs/node/commits/f2dc7c84d6
  answers:: patch 原文 `-Indicates that the underlying connection was closed.` / `+Emitted when the request has been completed.`；行为源自 PR #33035（Node 16 起生效），该提交本身是 PR #42521 的**文档**提交（易被误引）
  authority:: 高
  verified:: 2026-09-13

## 相关

- [[claude-resilience-architecture]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 补疏漏 | `ds2ox-proxy` 条目的 `answers` 写「3 处设计缺陷」但本页不展开，读者必须跳到 `security-audit.md` 才知道 D1/D2/D3 | 本页补 3 行小表（缺陷编号 / 一句话机制 / 对应要求），并注明本页只是索引；完整描述仍在 [[security-audit]] 与 [[ds2ox-proxy-retirement]] |
| 补疏漏 | 「新写代理时的最低要求」tip 只列 4 条结论、无验收判据 | 原 tip 原文保留，另补「缺陷 → 要求 → 验收方法」表（无 token → 401、伪 Host → 400、端口被占 → 失败退出、配置内无密钥明文） |
| 加厚 | `cache-relay` 标「现役」却无「如何确认它现在仍在跑」的命令与判据 | `answers` 补确认命令（`netstat -ano` 输出含 `:8790`，或健康检查路径 200）与「状态 + 确认命令 + 确认日期」的书写要求；现场确认日期仍待执行 |
| —（复核成立） | 本页 11 条内部资产：3 条 `file:///` + 8 条 `wikilink://` 的目标是否存在 | 复核独立重跑成立（三条 `file://` 路径 Test-Path 为真、8 个 wikilink basename 全库命中），未修改 |

见 [[CORRECTIONS]]、[[AGENTS]]。

## C3 复核新增（2026-09-13）：Xray / v2rayN 上游行为与版本口径

> C3 簇（network 子库回写）需要为「balancerTag 引用、Mux 与 Vision、UDP 443、observatory 频率、版本漂移」这些论断补**上游一手**依据；以下条目均在 2026-09-13 实际抓取过。

- 来源:: Xray 路由配置文档（引用关系与策略参数）
  use_when:: 写/审路由规则时确认 balancer 的正确引用字段，或解释「只有命中该规则的域名全挂」
  url:: https://xtls.github.io/config/routing.html
  answers:: 「转发至它所指定的 outboundTag 或 balancerTag」「**balancerTag 和 outboundTag 须二选一。当同时指定时，outboundTag 生效**」；`ip` 规则接受 CIDR 列表并支持 `geoip:`/`geosite:`；`tolerance` **仅 leastLoad 可配**（其下设 `expected`/`maxRTT`/`tolerance`/`baselines`/`costs`），`type` ∈ `random|roundRobin|leastPing|leastLoad` ⇒ 加 tolerance 必须连同把 leastPing 换成 leastLoad
  authority:: 高
  verified:: 2026-09-13

- 来源:: Xray 出站配置文档（Mux 定位与 `xudpProxyUDP443`）
  use_when:: 判断「Mux 与 XTLS-Vision 不兼容」是否成立，或决定 UDP 443 要不要一律 block
  url:: https://xtls.github.io/config/outbound.html
  answers:: Mux 是**性能取舍**——「Mux 是为了减少 TCP 的握手延迟而设计，而非提高连接的吞吐量。使用 Mux 看视频、下载或者测速通常都有反效果」（**未**声称协议层不兼容）；`xudpProxyUDP443` 三档：默认 `reject`（「一般浏览器会自动回落到 TCP HTTP2」）/ `allow`（「允许走 Mux 连接」）/ `skip`（「不使用 Mux 模块承载 UDP 443 流量…VLESS 会使用 UoT」）
  authority:: 高
  verified:: 2026-09-13

- 来源:: Xray Observatory 文档（探测周期与灵敏度边界）
  use_when:: 设定 `observatory`/`burstObservatory` 的 interval/sampling，或回答「多久判定节点故障」
  url:: https://xtls.github.io/config/observatory.html
  answers:: 持续探测失败的节点**最快 1 个周期、最慢 2 个周期**被标记为故障；恢复需一次成功探测、**最慢 1 个周期**；`interval` 过小 / `sampling` 过大使探测特征更明显（对伪装不利）⇒ 频率是「灵敏 ↔ 隐蔽」取舍
  authority:: 高
  verified:: 2026-09-13

- 来源:: Xray-core 分发器源码 `app/dispatcher/default.go`
  use_when:: 解释「路由规则引用了不存在的 outboundTag」的运行时表现（决定排查判据）
  url:: https://raw.githubusercontent.com/XTLS/Xray-core/main/app/dispatcher/default.go
  answers:: `errors.LogWarning(ctx, "non existing outTag: ", outTag)` 后 `common.Close(link.Writer)` / `common.Interrupt(link.Reader)`，并带注释 *DO NOT CHANGE: the traffic shouldn't be processed by default outbound if the specified outbound tag doesn't exist (yet)* ⇒ **不回落默认出站**，只数 outbounds 数量会漏判
  authority:: 高
  verified:: 2026-09-13

- 来源:: Xray-core 提交 `4f601530`（Vision 出站移除 Mux 警告）
  use_when:: 追溯「Mux 与 XTLS-Vision 不兼容」说法的上游现状
  url:: https://github.com/XTLS/Xray-core/commit/4f601530fabf045b0dc08e5526426ba7331c1133
  answers:: RPRX，2023-04-14，*Allow multiple XUDP in Mux when using XTLS Vision (client side)*——删除 Vision 出站对 Mux 的 `doesn't support Mux` 警告 ⇒ 当前上游允许该组合（只是不推荐），「不兼容」应改述为「实测组合劣化」
  authority:: 高
  verified:: 2026-09-13

- 来源:: Xray-core Releases API（**含预发布**）
  use_when:: 核对「上游最新版本」时区分正式版与预发布，避免与 `/releases/latest` 口径打架
  url:: https://api.github.com/repos/XTLS/Xray-core/releases?per_page=5
  answers:: 2026-09-13 实测首条 `v26.9.9`（`prerelease=true`，2026-09-08）；`v26.3.27` `prerelease=false`（2026-03-27）。`/releases/latest` 只返回非预发布版，故本页 C8 节记的 latest=`v26.3.27` 与本条**不矛盾**——引用时须注明预发布性质
  authority:: 高
  verified:: 2026-09-13

- 来源:: v2rayN Releases API（版本配对约束与预发布）
  use_when:: 排查「核心起不来 / 起来也不通」，或核对 v2rayN 与 xray-core 的版本配对要求
  url:: https://api.github.com/repos/2dust/v2rayN/releases/tags/7.19.5
  answers:: 7.19.5 body：*跟进 xray 配置，需要使用 xray-core v26.2.6*、*添加 一键生成策略组*、*重构配置生成代码* ⇒ 版本配对被上游显式约束；`7.24.6` `prerelease=true`（2026-08-08，body 为 Avalonia 12 / 内置下载器 MITM 修复 / HappyEyeballs，**无 balancer 修复条目**）；`7.25.1` published 2026-09-10（同为预发布）
  authority:: 高
  verified:: 2026-09-13

- 来源:: v2rayN PR #8849「Fix balancer routing」
  use_when:: 评估 v2rayN 生成器自身的 balancer 回归风险，或核对上游是否修过该 bug
  url:: https://github.com/2dust/v2rayN/pull/8849
  answers:: `title="Fix balancer routing"`、`merged=true`、`merged_at 2026-02-27`，`html_url` 为 `.../pull/8849` ⇒ **是 PR 不是 issue**（同页 #9727 为 *Revert "Fix"*，issue #9699 记 7.23.2 回归）
  authority:: 高
  verified:: 2026-09-13

- 来源:: v2rayN 配置生成源码 `ConfigHandler.cs`
  use_when:: 核实文档里引用的 v2rayN 方法名/枚举是否真实存在
  url:: https://raw.githubusercontent.com/2dust/v2rayN/master/v2rayN/ServiceLib/Handler/ConfigHandler.cs
  answers:: 检索 `GenerateClientMultipleLoadConfig` **命中 0**，只见 `MultipleLoad = EMultipleLoad.LeastPing`（2 处）⇒ 引用应改为「策略组 `MultipleLoad = LeastPing`（GUI 即『一键生成策略组』）」
  authority:: 高
  verified:: 2026-09-13

- 来源:: 免费代理清单仓库 gfpcom/free-proxy-list
  use_when:: 找免费 VLESS 节点源，或核对「更新频率 / 节点数量」类说法
  url:: https://api.github.com/repos/gfpcom/free-proxy-list
  answers:: 仓库描述「🔄 Updated Every 30 Minutes⏰」⇒ **30 分钟频率属实**；但描述与页面均**没有** ~95,000 这一计数（库内该数字无来源）
  authority:: 中
  verified:: 2026-09-13

## C6 复核新增（2026-09-13）：nginx for Windows 的连接上限与生产适用性

> C6 簇核 `log-analysis-agent-architecture` ADR-4 时发现：「select 上限约 1024」被写成可用「增大 `worker_connections` 到 8192」缓解——**该缓解措施对 1024 无效**（1024 是 `select()` 的 `FD_SETSIZE` 硬限），而该限制上游已用 `use poll;` 解除。

- 来源:: nginx 官方文档 · nginx for Windows
  use_when:: 评估「Windows 上跑 nginx 做反向代理」的代价与连接上限时
  url:: https://nginx.org/en/docs/windows.html
  answers:: 现存文本**已无「1024」字样**，逐字「Only the `select()` and `poll()` (1.15.9) connection processing methods are currently used, so high performance and scalability should not be expected.」；同页自述 Windows 版「is considered to be a **beta** version」⇒ 生产选型必须记录 beta 与性能免责声明
  authority:: 高
  verified:: 2026-09-13

- 来源:: nginx 邮件列表 · Maxim Dounin, 2022-11-16（poll / WSAPoll 解除 1024 硬限）
  use_when:: 判断 Windows 版 nginx 的 1024 连接上限是否仍存在、怎么解除
  url:: https://mailman.nginx.org/pipermail/nginx/2022-November/ZX6HFYZ5HYUAASJ2CEAAI22UOYS2FVNK.html
  answers:: 逐字「With the poll event method… nginx will use the `WSAPoll()` function, which, in contrast to `select()`, does not impose a **hard-coded limit on the number of connections**」⇒ 前提是配置里写 `use poll;`；注意 `WSAPoll()` 已知的 connect 错误上报延迟问题
  authority:: 高
  verified:: 2026-09-13

见 [[CORRECTIONS]]、[[AGENTS]]。
