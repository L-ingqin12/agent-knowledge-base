---
title: 路由器视频/远程/监测方案
aliases: [QoS, 远程访问, 流量监测]
tags: [network/router, network/optimization]
created: 2026-07-28
updated: 2026-09-13
status: stable
---

# 路由器视频优化、远程访问与流量监测

See also: [[Network-KB-Home]] | [[ROUTER-FULL-CAPABILITY]] | [[ROUTER-OPTIMIZATION]]

> [!abstract] 硬件约束
> - RAM: 64MB (空闲 ~15MB), CPU: 575MHz 单核
> - /data: 272KB 剩余, /userdisk: 1.4MB 剩余
> - 无 iptables (无法端口转发/NAT 规则)
> - 无 uci (miqos 无法启动)

## 一、视频优化

### WMM (WiFi Multimedia) — 已生效

MT7628 驱动级 QoS，4 个优先级队列：

| 优先级 | 队列 | 典型流量 |
|--------|------|----------|
| Voice (最高) | AC_VO | VoIP, 游戏 |
| **Video** | **AC_VI** | **视频流, Telegram** |
| Best Effort | AC_BE | Web, 普通 TCP |
| Background | AC_BG | 下载, P2P |

WMM 在 `/etc/config/wireless` 中 `option wmm '1'` 已启用。WiFi 驱动自动根据 IP TOS/DSCP 标记将包分配到对应队列。

> [!warning] miqos 不可用
> miqos 依赖 uci 命令（R4CM 2.14.87 中缺失），启动时崩溃: `uci: not found`。配置已写入但无法运行。

### 客户端侧优化 (Windows)

```powershell
# 启用 TCP 窗口自动调优
netsh int tcp set global autotuninglevel=normal
# 启用 CTCP 拥塞控制
netsh int tcp set global congestionprovider=ctcp
```

> [!warning] 补疏漏（2026-09-13）：上面两条命令**没有输出示例，也没有验收判据**；且原参考页已失效。
> 复核发现所引 Microsoft Learn 参考页 `windows-commands/netsh-int-tcp` 返回 **HTTP 404（Content not found）**。补验收方法：执行后用 **`netsh int tcp show global`** 回读 `Receive Window Auto-Tuning Level` 与 `Congestion Provider`（`ctcp` 只在部分 Windows 版本/驱动栈下可用，回读为空或非 ctcp 即视为未生效），并以 `Get-NetTCPSetting` 交叉确认。**在拿到回读值之前，不要把这组命令计入优化收益**。来源：<https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-int-tcp>（404）、<https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/tcpip-performance-known-issues>

### 效果

WMM 无法主动标记包（需要 iptables），但尊重已有的 DSCP 标记。xray/VLESS 流量不携带特定 DSCP，因此 WMM 对代理流量的视频优化效果**有限**。主要收益在于：非代理直连流量（如国内视频网站）可被正确分类。

> [!warning] 补疏漏（2026-09-13）：上段结论方向成立，但**漏了「映射本身是标准化内容」这一层，因而没法验收**（原表述保留于上；注：该段实际位于「### 效果」小节，不在「WMM」小节）。
> RFC 8325《*Mapping Diffserv to IEEE 802.11*》（Standards Track，2018-02）定义的正是 **DSCP → 802.11 用户优先级（UP）映射**与 **QoS Map** 机制——即「打标记 → 映射到 AC 队列」这条链路是有标准的，能不能生效取决于 **AP 与客户端两侧实现是否一致**。因此应把它列为**验收项**：① 在客户端标记 DSCP，② 在 AP 侧观察包是否落到 AC_VI 队列，③ 两侧不一致时优化无效。xray 侧确实不打 DSCP 标记（需要 iptables，本机缺失），所以当前对代理流量无收益的判断不变。
> 来源：<https://www.rfc-editor.org/rfc/rfc8325.html>

## 二、远程访问

### 方案 A: SSH 隧道 (推荐, 零存储, 即时可用)

从 Windows 本机 (已有 SSH 到路由器) 建立到 VPS 的远程隧道：

```bash
# 方案 A1: 反向隧道 (从 Windows → VPS, 暴露路由器端口)
ssh -R 2222:[IP已脱敏]:22 -o ServerAliveInterval=60 user@your-vps

# 方案 A2: SOCKS 动态转发 (路由器作为代理出口)
ssh -D 2080 -N user@your-vps
# 然后浏览器配置 SOCKS5: 127.0.0.1:2080

# 方案 A3: 本地转发 (访问远程服务)
ssh -L 8080:remote-service:80 user@your-vps
```

> [!warning] 更正（2026-09-13）：A2 的注释「**路由器作为代理出口**」与 `ssh -D` 语义不符（原表述保留于上）。
> `ssh -D 2080 -N user@your-vps` 是在**执行 ssh 的这台机器**（本处为 Windows 本机）上开一个 SOCKS 监听，出口是**所登录的 VPS**——整条链路与路由器无关；路由器只出现在 A1 的反向隧道里。请把注释改为「**本机开 SOCKS，出口为 VPS**」。来源：<https://man.openbsd.org/ssh>、<https://man7.org/linux/man-pages/man1/ssh.1.html>

优点: 安全加密, 无需端口转发, 无需路由器存储
缺点: 需要一台有公网 IP 的 VPS; 连接断开需重连

### 方案 B: xl2tpd L2TP VPN (替代 SmartVPN, 路由器原生)

xl2tpd 二进制已存在 (/usr/sbin/xl2tpd, 97KB):

```bash
# 配置 L2TP 客户端连接远程 VPN 服务器
# 编辑 /data/etc/xl2tpd/xl2tpd.conf
# 编辑 /data/etc/xl2tpd/xl2tp-secrets (已存在模板)
# 启动: /etc/init.d/xl2tpd start
```

最小配置示例 (`/data/etc/xl2tpd/xl2tpd.conf`):

```ini
[lac remote]
lns = <你的VPN服务器IP>
pppoptfile = /data/etc/xl2tpd/options
require chap = yes
ppp debug = no
```

优点: 路由器原生支持, 2 层隧道, 可路由整个子网
缺点: 需要远程 L2TP 服务器; 配置复杂

### 方案 C: nc TCP 中继 (最轻量, 0 存储)

```bash
# 从路由器转发端口到外部服务器
mkfifo /tmp/fifo   # 仅需执行一次; nc 循环需配合 sleep, 防止无数据时忙等
while true; do
  busybox nc <remote_server> <remote_port> < /tmp/fifo | busybox nc localhost 80 > /tmp/fifo
  sleep 1   # 连接断开后稍歇再重试
done &
```

优点: 零存储, busybox 内置
缺点: 不稳定, 无加密, 单向

### 方案 D: frp/nps 内网穿透 (最灵活)

```bash
# 下载 frp MIPS 客户端到 /userdisk (1.4MB 可用)
cd /userdisk && wget <frp-mips-url>
# 配置指向有公网 IP 的 frp 服务端
# 开机自启 via rc.local
```

优点: 功能完整, 支持多端口映射, 可穿透多层 NAT
限制: 需要外部 frp 服务端; frp 二进制 ~5MB (/userdisk 只有 1.4MB, 需用 tmpfs 运行)

> [!check] 已核验并更正（2026-09-13）：`~5MB` **偏小，实际约 11.4~11.9MB**；但「必须放 tmpfs」的结论**正确**（原表述保留于上）。
> 复核 frp 最新版 `v0.71.0`（published 2026-08-14）的 MIPS 资产：`linux_mips` **11.91 MB**、`linux_mipsle` **11.71 MB**、`linux_mips64` **11.64 MB**、`linux_mips64le` **11.41 MB**。`/userdisk` 仅剩 1.4MB，**无论 5MB 还是 11.9MB 都放不下**，因此下方「下载到 `/tmp`(RAM) + 配置存 /userdisk」的推荐方案不变；引用体积时应改用实测值。
> 来源：<https://api.github.com/repos/fatedier/frp/releases/latest>

> [!tip] 推荐方案
> 当前最优: **frp/tmpfs + 外部 frp 服务端**。frp 客户端下载到 /tmp (RAM), 每次启动时 wget 拉取, 不占用 flash。配置存 /userdisk。

## 三、流量监测

### 实时监测脚本 (已部署)

`/userdisk/traffic_monitor.sh` — 每分钟采集:

```
格式: timestamp WAN_RX_bps WAN_TX_bps WiFi_bps conntrack_count
输出: /userdisk/traffic.log (自动轮转, 保留 200 行)
```

**存储占用**: 脚本 ~800B, 日志 ~14KB, 总计 <15KB

```bash
# 查看最近 10 条记录
tail -10 /userdisk/traffic.log

# 实时连接数
cat /proc/sys/net/netfilter/nf_conntrack_count

# 接口累计流量
cat /proc/net/dev | grep eth0.2
```

### 数据解读

| 指标 | 来源 | 含义 |
|------|------|------|
| WAN_RX_bps | /proc/net/dev eth0.2 | WAN 下载速率 (bps) |
| WAN_TX_bps | /proc/net/dev eth0.2 | WAN 上传速率 (bps) |
| WiFi_bps | /proc/net/dev wl1 | WiFi 接口速率 |
| conntrack | nf_conntrack_count | 活跃连接数 |

### 扩展: 设备级流量

```bash
# 通过 API 获取每个设备的实时速率
curl "http://[IP已脱敏]/cgi-bin/luci/;stok=TOKEN/api/misystem/devicelist"
# 返回每个设备的 upspeed/downspeed (单位: B/s, 待实测确认)
```

### 扩展: 远程日志

```bash
# 通过 nc 发送到外部日志服务器
tail -f /userdisk/traffic.log | busybox nc <log-server> 514 &
```

## 四、存储使用

| 文件 | 大小 | 位置 |
|------|------|------|
| traffic_monitor.sh | ~800B | /userdisk |
| traffic.log | ≤14KB | /userdisk |
| miqos 配置 | ~1KB | /data/etc/config |
| rc.local 修改 | +100B | /data/etc |
| **总计** | **<16KB** | — |

剩余: /data 272KB, /userdisk 1.4MB

## Related

- [[ROUTER-FULL-CAPABILITY]] — 路由器能力手册
- [[ROUTER-OPTIMIZATION]] — 路由器优化分析
- [[Network-KB-Home]] — 知识库首页

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 补疏漏 | `netsh int tcp` 两条命令无输出示例/验收判据，且所引参考页已 404 | 加注：MS Learn `netsh-int-tcp` 返回 404；补 `netsh int tcp show global` / `Get-NetTCPSetting` 回读验收 |
| 纠错 | 方案 D「frp 二进制 ~5MB」数字偏小 | 保留原句并加已核验块：v0.71.0 各 MIPS 资产实测 11.41~11.91MB；「必须 tmpfs」结论正确 |
| 补疏漏 | 「WMM 无法主动标记包」未提 DSCP→UP 映射是标准化内容，无法验收 | 加注 RFC 8325（DSCP→802.11 UP 与 QoS Map），给出 AP/客户端一致性验收三步 |
| 纠错 | 方案 A2 注释「路由器作为代理出口」与 `ssh -D` 语义不符 | 保留原句并加更正块：`ssh -D` 在本机开 SOCKS、出口为 VPS，路由器只出现在 A1 |

相关：[[CORRECTIONS]] · [[AGENTS]]

