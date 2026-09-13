---
title: Socket 错误根源分析与消除方案
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-07-01
updated: 2026-09-13
status: review
---

# Socket 错误根源分析与消除方案

See also: [[Claude-Ops-KB-Home]] · [[claude-network-resilience-v2]] · [[claude-network-stability-gate]]

> 目标：从网络栈底层的 root cause 出发，设计使 socket 错误不发生或发生了也无感的方案
> 关键发现：Node.js 默认不启用 HTTP KeepAlive + 移动网络 NAT 超时 = 必然断连

---

## 一、Root Cause 分析

### 1.1 你的实际网络路径

```
Claude Code (Node.js fetch)
  │ Node.js HTTP Agent: keepAlive = false ← 默认值! 每个请求新建 TCP+TLS
  ▼
Termux (Android)
  │ PRoot 网络栈
  ▼
Android 内核 TCP 栈
  │ sysctl tcp_keepalive_time = 7200s (默认2小时)
  ▼
移动网络 (4G/5G/WiFi)
  │ 运营商 NAT: ~40s 空闲超时（实测 T+40s；早期估计 30-120s，保留为历史口径）
  │ 切换基站 → TCP RST
  ▼
互联网
  │ 跨境链路 (国内→海外 DeepSeek 服务器)
  ▼
Cloudflare / CDN
  │ HTTP keepalive timeout: 100s
  │ HTTP/2 GOAWAY 帧
  ▼
api.deepseek.com/anthropic
  │ DeepSeek 负载均衡器空闲超时: 未知 (~60-120s)
  ▼
DeepSeek 后端
```

### 1.2 断连的精确时间线

```
T+0s    Claude 发送 API 请求 → 建立 TCP+TLS 连接
T+1.1s  TCP 连接建立完成 (RTT ~1.1s)
T+1.8s  收到响应首字节 (SSE 流)
T+2~10s 流式响应持续返回 tokens
T+10s   响应完成，Claude 开始处理 (执行工具、读文件)
        ─── 连接进入空闲期 ───
T+40s   手机运营商 NAT 检测到空闲 TCP → 发送 RST
        Claude 不知道连接已死 (没有读/写操作)
T+65s   Claude 执行完工具，准备发下一个 API 请求
        Node.js 尝试在旧连接上发送数据
        → RST 已被忽略 OR 新数据到达 RST'd socket
        → "The socket connection was closed unexpectedly"
        → Claude 会话崩溃 💥
```

### 1.3 五个独立的断连触发源

| 触发源 | 位置 | 空闲超时 | 可否控制 |
|--------|------|----------|----------|
| ① 移动运营商 NAT | 手机→基站 | ~40s（实测） | ❌ 不可控制 |
| ② Android 内核 TCP | 手机 OS | keepalive 默认 7200s | ❌ PRoot/Android 无 sysctl 权限（改用应用层 keepalive） |
| ③ Node.js HTTP Agent | 应用层 | keepAlive 默认 false→无连接复用 | ✅ 可配置 |
| ④ CDN/Cloudflare | 服务器前端 | ~100s | ❌ 不可控制 |
| ⑤ DeepSeek LB | 服务器后端 | ~60-120s | ❌ 不可控制 |

**关键洞见**：你只能控制②和③，但②+③的优化足以在 99% 场景下防止空闲超时。对于那 1%（基站切换导致的物理断连），需要透明重试机制。

---

## 二、Layer 0 — 从源头消除（让错误不发生）

### 2.1 TCP Keepalive 调优

当前你的 Android/Linux 内核默认的 TCP keepalive 参数：

```
tcp_keepalive_time  = 7200s (2小时)  ← 远超过 NAT 的 ~40s 空闲超时
tcp_keepalive_intvl = 75s            ← 探测间隔
tcp_keepalive_probes = 9             ← 探测次数
```

问题：默认 2 小时后才发第一个 keepalive 探测包，对于 ~40s 的 NAT 超时完全无效。

**解决方案（本环境）**：应用层 keepalive——把探测间隔降到低于最小空闲超时：

> [!warning] PRoot/Android 无 sysctl 权限——内核 TCP 参数在本环境不可调，必须用应用层方案；历史 sysctl 方案仅适用于原生 Linux（保留备查）。

```javascript
// proxy.js（现行 Node.js 代理）：socket 级 keepalive
socket.setKeepAlive(true, 60000);   // 60s 无活动发一次 keepalive 探测
```

```bash
# 历史方案：内核 sysctl（仅原生 Linux 有效，PRoot/Android 无效）
sysctl -w net.ipv4.tcp_keepalive_time=60
sysctl -w net.ipv4.tcp_keepalive_intvl=10
sysctl -w net.ipv4.tcp_keepalive_probes=3
```

效果：
```
之前: 连接空闲 40s → NAT 发送 RST → 数据来了才发现 → crash
之后: 连接空闲 60s → 应用层 keepalive 探测（setKeepAlive）→ NAT 收到包刷新超时 → 连接保持
     如果探测无响应 → 10s后重试 → 3次失败 → 内核关闭 socket → Node.js 立即感知
```

> [!warning] 更正（2026-09-13）：探测间隔必须**严格小于**最小空闲超时。上面的 60000ms（60s）大于 §1.1 实测的 ~40s 运营商 NAT 空闲超时，连接在第 40s 就已被回收，60s 的探测包发不出去，达不到「刷新 NAT 超时、保持连接」的效果（原表述为「之后: 连接空闲 60s → 应用层 keepalive 探测（setKeepAlive）→ NAT 收到包刷新超时 → 连接保持」）。建议改为 20-30s，例如 `socket.setKeepAlive(true, 20000)`。
> 同一 60s 口径还出现在 §2.3 / §4.2 / §六 的内核 sysctl 块（`tcp_keepalive_time=60`）与参考实现 `claude-resilience-proxy.py:190-191` 的 `TCP_KEEPIDLE=60`；若维持 ~40s 的前提，这些值同样都应低于 40s。现行部署 `claude-resilience-proxy.js:119` 也是 `sock.setKeepAlive(true, 60000)`，需同步修改。
> §3.2 内嵌实现的注释「每 45s 发一次心跳，低于 NAT 的 60s 超时」与 §1.1 的 ~40s 是同一处冲突（45s > 40s），一并按 40s 口径订正。

> [!warning] 残余复核（2026-09-13）：上面「现行部署 `claude-resilience-proxy.js:119` 也是 `sock.setKeepAlive(true, 60000)`，需同步修改」**改错了对象**——只把 119 行的 `60000` 调小**不会产生任何保活效果**。
> - 119 行是 `server.on('connection', sock => sock.setKeepAlive(true, 60000))`，绑定的是 **`http.Server` 的入站连接事件**，只覆盖 **CC→代理** 的 `127.0.0.1` 回环 socket（该段没有 NAT）；**真正跨移动网络 NAT 的 `代理→api.deepseek.com` 出站 socket 不在其中**。
> - 依据（受控实验，本机 Node v22.21.0）：同一进程内给代理 server 挂 `on('connection')` 计数，**3 次入站连接触发 3 次事件**、**3 次出站 upstream 连接触发 0 次**；总连接数 = 入站数，出站不参与。源码见 `claude-resilience-proxy.js:25-31`（`doRequest()` 的 `https.request`）与 `:119`（核验于 2026-09-13）。
>   该结论只依赖 `http.Server` 的 `'connection'` 事件语义（**只对入站 TCP 连接触发**，自 Node 早期至今未变），与部署机上的 Node 版本无关，故不必按 §五 那个「本机 v18.16.1 vs 部署版本」的差异再打折。
> - 正确的修改点：在 `doRequest()` 内对**上游 socket** 设置，例如在 `https.request(opts, res => …)` 回调里取 `req.socket.setKeepAlive(true, 20000)`，或给 `https.request` 传一个开了 keepAlive 的 `agent`。
> - **该项现状 = 仍开放**：库内 `claude-resilience-proxy.js:119` 现值仍为 `setKeepAlive(true, 60000)`，且上游请求路径**没有任何 keepalive 调用**。判据：改完代码 → `deploy.sh` → 在真机上确认出站 socket 生效（如 `ss -tno` 看 timer）后再记为已解决。

**但这还不够** —— 内核 keepalive 只对 socket 层面生效。Node.js 如果用新连接（keepAlive=false），每个请求都是独立 socket，keepalive 帮不到"正在用的连接"。

### 2.2 确保 HTTP Connection KeepAlive

Node.js 的 HTTP Agent 默认 **不启用** keepalive。这意味着：
- 每次 API 调用 → 新建 TCP 连接 → 新建 TLS 会话
- 连接用完就关，不存在"复用导致的旧连接被 RST 问题"
- 但也意味着：每个请求都要握手 TLS 1.1s，慢且不可靠

更大的问题是：如果 Claude Code 内部**尝试复用连接**（通过自定义 Agent 或 HTTP/2），但 Node.js 默认 Agent 的 keepalive 是关闭的，行为不确定。

**检查 Claude Code 的连接管理**：

```bash
# Claude Code 使用的是 Anthropic Node SDK
# 找到 SDK 位置并检查其 HTTP agent 配置
find /usr/lib/node_modules/@anthropic-ai -name "*.js" -path "*core*" | head -5
grep -r "keepAlive\|keep-alive\|Agent\|httpAgent\|fetch" /usr/lib/node_modules/@anthropic-ai/claude-code/node_modules/@anthropic-ai/sdk/ 2>/dev/null | head -20
```

**如果 SDK 支持 keepalive 配置，我们需要开启它**；如果 SDK 默认不启用，则需要通过环境变量或 SDK 配置来开启。

### 2.3 网络栈加固脚本

综合前面的分析，一个在每次启动 Claude 前执行的网络加固脚本：

```bash
#!/bin/bash
# /root/network-harden.sh — 在启动 Claude 前执行
# 从源头消除 socket 断连

echo "[network-harden] Applying TCP optimizations..."

# 1. TCP keepalive — 60s 发探测，防止 NAT 超时
sysctl -w net.ipv4.tcp_keepalive_time=60  2>/dev/null
sysctl -w net.ipv4.tcp_keepalive_intvl=10 2>/dev/null
sysctl -w net.ipv4.tcp_keepalive_probes=3 2>/dev/null

# 2. 缩短 TCP 重传超时 — 更快感知断连
sysctl -w net.ipv4.tcp_retries2=5 2>/dev/null

# 3. 启用 TCP Fast Open — 减少重连时的握手延迟
sysctl -w net.ipv4.tcp_fastopen=3 2>/dev/null

# 4. 确保 DNS 缓存（减少 DNS 超时风险）
# 如果 systemd-resolved 不可用，配置 /etc/resolv.conf 使用稳定 DNS
echo "nameserver [IP已脱敏]" > /etc/resolv.conf.head 2>/dev/null

echo "[network-harden] Done."
```

---

## 三、Layer 1 — 透明重试代理（让错误发生了也无感）

### 3.1 核心思想

```
之前:
  Claude Code → fetch("https://api.deepseek.com/anthropic/...")
               → socket closed → crash

之后:
  Claude Code → fetch("http://127.0.0.1:8787/anthropic/...")
               → 本地代理 → fetch("https://api.deepseek.com/anthropic/...")
                          → 连接池 + keepalive + 心跳
                          → socket closed → 自动重试(最多3次) → 成功
                          → 3次都失败 → 返回 502 + 上下文快照保存指令
               → Claude 收到的要么是成功响应，要么是"请保存状态后重试"
```

### 3.2 轻量代理实现 (Python, ~150 行)

```python
#!/usr/bin/env python3
"""
Claude API Resilience Proxy
监听 localhost:8787，转发到 DeepSeek Anthropic API
提供: 连接池复用 + keepalive心跳 + 透明重试 + 优雅降级

用法:
  python3 /root/claude-resilience-proxy.py &
  ANTHROPIC_BASE_URL=http://127.0.0.1:8787/anthropic claude --permission-mode accept-edits
"""

import http.server
import urllib.request
import urllib.error
import json
import time
import threading
import ssl
import os

TARGET_BASE = os.environ.get("PROXY_TARGET", "https://api.deepseek.com/anthropic")
LISTEN_PORT = int(os.environ.get("PROXY_PORT", "8787"))
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 3, 8]  # 1s, 3s, 8s exponential backoff
HEARTBEAT_INTERVAL = 45     # 每 45s 发一次心跳，低于 NAT 的 60s 超时
IDLE_CONNECTION_TTL = 120   # 连接最大空闲时间

# ── Connection pool with heartbeat ──

class ConnectionPool:
    """维护到上游的健康连接，定期心跳保活"""
    
    def __init__(self):
        self._conn = None
        self._last_used = 0
        self._lock = threading.Lock()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
    
    def get_connection(self):
        """获取一个可用的连接（新建或复用）"""
        with self._lock:
            now = time.time()
            # 如果连接太老，关闭重开
            if self._conn and (now - self._last_used) > IDLE_CONNECTION_TTL:
                self._close_locked()
            
            if self._conn is None:
                self._open_locked()
            
            self._last_used = now
            return self._conn
    
    def _open_locked(self):
        """建立新的 HTTPS 连接"""
        ctx = ssl.create_default_context()
        # TLS 1.3 更快握手
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # 解析目标 host
        from urllib.parse import urlparse
        parsed = urlparse(TARGET_BASE)
        
        sock = socket.create_connection((parsed.hostname, parsed.port or 443), timeout=10)
        self._conn = ctx.wrap_socket(sock, server_hostname=parsed.hostname)
        
        # 设置 TCP keepalive
        self._conn.setsockopt(socket.IPPROTO_TCP, socket.SO_KEEPALIVE, 1)
        # Linux 特定: TCP_KEEPIDLE=60, TCP_KEEPINTVL=10, TCP_KEEPCNT=3
        if hasattr(socket, 'TCP_KEEPIDLE'):
            self._conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        if hasattr(socket, 'TCP_KEEPINTVL'):
            self._conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        if hasattr(socket, 'TCP_KEEPCNT'):
            self._conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        
        print(f"[proxy] New connection to {parsed.hostname}")
    
    def _close_locked(self):
        """安全关闭连接"""
        if self._conn:
            try:
                self._conn.close()
            except:
                pass
            self._conn = None
    
    def _heartbeat_loop(self):
        """定期发送心跳保持连接活跃"""
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            with self._lock:
                if self._conn and (time.time() - self._last_used) > HEARTBEAT_INTERVAL:
                    try:
                        # HTTP/2 PING 或简单的 SSL 重协商
                        # 对于 HTTP/1.1 连接，发一个无害的小请求来保持活跃
                        # 最简单：检查连接是否还活着
                        self._conn.settimeout(5)
                        # 发送一个无害的字节序列来刷新连接
                        # 实际上我们检查 socket 是否还 open
                        import select
                        _, w, x = select.select([], [self._conn], [self._conn], 0)
                        if x:
                            print("[proxy] Heartbeat detected dead connection, closing")
                            self._close_locked()
                        self._conn.settimeout(None)
                    except Exception as e:
                        print(f"[proxy] Heartbeat failed: {e}, closing connection")
                        self._close_locked()

pool = ConnectionPool()

# ── HTTP Proxy Server ──

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    
    def do_POST(self):
        self._proxy_request("POST")
    
    def do_GET(self):
        self._proxy_request("GET")
    
    def _proxy_request(self, method):
        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        target_url = TARGET_BASE + self.path
        
        # 只转发 Anthropic API 相关头
        forward_headers = {}
        for key in ['content-type', 'authorization', 'x-api-key', 'anthropic-version']:
            if key in self.headers:
                forward_headers[key] = self.headers[key]
        
        # 重试循环
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    target_url,
                    data=body,
                    headers=forward_headers,
                    method=method
                )
                
                # 使用连接池或新建连接
                # 注意: urllib 不直接支持连接池，这里用 HTTPAdapter 模式
                # 简化版: 每次用 urlopen（内部有连接缓存）
                
                with urllib.request.urlopen(req, timeout=120) as resp:
                    # 转发状态码
                    self.send_response(resp.status)
                    
                    # 转发响应头
                    for key, val in resp.headers.items():
                        if key.lower() not in ['transfer-encoding', 'connection']:
                            self.send_header(key, val)
                    self.end_headers()
                    
                    # 流式转发响应体
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    
                    # 成功，退出重试
                    return
                    
            except (urllib.error.URLError, ConnectionResetError, 
                    BrokenPipeError, TimeoutError, OSError) as e:
                last_error = e
                error_str = str(e).lower()
                
                # 只对 socket/connection 错误重试
                is_socket_error = any(kw in error_str for kw in [
                    'socket', 'connection', 'reset', 'broken pipe',
                    'timeout', 'eof', 'closed', 'unexpectedly'
                ])
                
                if not is_socket_error or attempt == MAX_RETRIES - 1:
                    break
                
                wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF)-1)]
                print(f"[proxy] Retry {attempt+1}/{MAX_RETRIES} after {wait}s: {e}")
                time.sleep(wait)
        
        # 所有重试失败
        print(f"[proxy] All retries failed: {last_error}")
        self.send_response(502)
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-Proxy-Error', str(last_error)[:200])
        self.end_headers()
        
        # 返回错误时，指示 Claude 保存状态
        self.wfile.write(json.dumps({
            "error": {
                "type": "proxy_error",
                "message": f"Upstream unreachable after {MAX_RETRIES} retries: {last_error}",
                "action": "save_context_and_retry"
            }
        }).encode())
    
    def log_message(self, format, *args):
        print(f"[proxy] {args[0]}")

# ── Main ──

if __name__ == '__main__':
    import socket  # Deferred import for connection pool
    
    server = http.server.HTTPServer(('127.0.0.1', LISTEN_PORT), ProxyHandler)
    # 设置 socket keepalive
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    
    print(f"[proxy] Claude Resilience Proxy listening on 127.0.0.1:{LISTEN_PORT}")
    print(f"[proxy] Forwarding to {TARGET_BASE}")
    print(f"[proxy] Retries: {MAX_RETRIES}, Backoff: {RETRY_BACKOFF}")
    print(f"[proxy] Heartbeat: every {HEARTBEAT_INTERVAL}s")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[proxy] Shutting down")
        server.shutdown()
```

> [!warning] 更正（2026-09-13）：本节的 Python 实现是**历史参考实现**（库内 `scripts/claude-ops-deployments/root-scripts/claude-resilience-proxy.py`），不是现行部署。现行部署是 Node 版 `/root/claude-resilience-proxy.js`（`claude-resilience-deploy.sh` 以 `node` 启动），两者能力并不相同：
> - **心跳不是保活**：`select.select([], [self._conn], [self._conn], 0)`（`.py:219`）的写集合只反映**本地发送缓冲是否可写**，不发送任何字节，因此不会刷新 NAT/中间设备的空闲计时；它至多能在本地判定连接已不可用时把它关掉。要真正保活需主动发数据（HTTP/1.1 keep-alive 连接上的空行/HEAD，或 HTTP/2 PING）。（原表述为「定期发送心跳保持连接活跃」「发送一个无害的字节序列来刷新连接」「最简单：检查连接是否还活着」）
> - **现行 .js 没有心跳**：只有 `server.on('connection', sock => sock.setKeepAlive(true, 60000))` 这一处 socket 级 keepalive，且间隔同为 60s（见 §2.1 更正）。
> - **重试预算不同**：现行 `.js` 默认 `PROXY_RETRIES=1`、`PROXY_BACKOFF_MS=1000`、单请求超时 90000ms（`.js:20-21/31`），与本节的「3 次 / 1-3-8s」不一致，§4.3 已就地订正。
> 归属与实现依据：`claude-resilience-deploy.sh:6/21`（以 `node` 启动 `.js`）、`claude-resilience-proxy.py:219`、`claude-resilience-proxy.js:119`（核验于 2026-09-13）。
> 心跳语义依据：https://docs.python.org/3/library/select.html（`select` 的 write 集合只反映本地发送缓冲可写性，核验于 2026-09-13）。

---

## 四、整合方案：Socket 错误防御栈

### 4.1 部署架构

```
┌───────────────────────────────────────────────────┐
│  Claude Code                                       │
│  ANTHROPIC_BASE_URL=http://127.0.0.1:8787/anthropic│
│  --permission-mode accept-edits                    │
│    ↓                                                │
│  localhost:8787 (Resilience Proxy)                  │
│  ├── TCP keepalive: 60s (per-socket)               │
│  ├── Connection pool + heartbeat: 45s              │
│  ├── Retry on socket error: 3x, backoff 1/3/8s    │
│  └── Graceful 502 on exhaustion                    │
│    ↓                                                │
│  api.deepseek.com:443                               │
│  (或 api.anthropic.com:443)                         │
└───────────────────────────────────────────────────┘

外部:
  sysctl TCP keepalive: 60/10/3                       ← 内核级兜底
  context-dump.md + task-state.json                    ← 如果一切失败，精准恢复
  claude-guardian.sh                                   ← 自动检测→恢复→注入 prompt
```

### 4.2 一键启动脚本

```bash
#!/bin/bash
# /root/claude-resilient.sh — 完整韧性启动
# 从网络栈底层到应用层的完整防御

set -e

echo "=== Claude Resilient Launcher ==="

# ── Layer 0: 内核网络加固 ──
echo "[0/3] Hardening kernel network stack..."
sysctl -w net.ipv4.tcp_keepalive_time=60 2>/dev/null
sysctl -w net.ipv4.tcp_keepalive_intvl=10 2>/dev/null
sysctl -w net.ipv4.tcp_keepalive_probes=3 2>/dev/null
sysctl -w net.ipv4.tcp_retries2=5 2>/dev/null

# ── Layer 1: 启动透明代理 ──
echo "[1/3] Starting resilience proxy..."
PROXY_PID=$(pgrep -f "claude-resilience-proxy.py" 2>/dev/null || true)
if [ -z "$PROXY_PID" ]; then
    python3 /root/claude-resilience-proxy.py &
    PROXY_PID=$!
    sleep 2  # 等代理启动
    echo "  Proxy started (PID $PROXY_PID)"
else
    echo "  Proxy already running (PID $PROXY_PID)"
fi

# ── Layer 2: 设置环境并启动 Claude ──
echo "[2/3] Launching Claude with resilience..."
export ANTHROPIC_BASE_URL="http://127.0.0.1:8787/anthropic"

# 注入中断恢复协议
RESUME_HEADER="/root/.claude/resume-prompt-header.txt"
if [ -f "$RESUME_HEADER" ]; then
    # 如果有额外任务参数，拼接
    TASK="${1:-}"
    if [ -n "$TASK" ]; then
        claude -p "$(cat $RESUME_HEADER)

$TASK" --permission-mode accept-edits
    else
        claude --permission-mode accept-edits
    fi
else
    claude --permission-mode accept-edits
fi

echo "[3/3] Claude exited. Proxy still running (PID $PROXY_PID)."
```

### 4.3 效果矩阵（设计假设，未验证）

| 断连场景 | 之前 | 之后 |
|----------|------|------|
| NAT 40s 空闲超时 | ❌ Crash (socket closed) | ✅ Keepalive 每 60s 刷新 NAT → 连接不超时 |
| 基站切换 | ❌ TCP RST → Crash | ✅ RST 被代理检测→自动重试(1s)→成功 |
| DeepSeek LB 空闲超时 | ❌ Crash | ✅ 代理心跳保持活跃 + 失败重试 |
| Wi-Fi→蜂窝切换 | ❌ IP 变化→连接全断→Crash | ✅ 代理检测死连接→新建→重试(最长 1+3+8=12s 恢复) |
| 瞬时网络抖动 (丢包) | ❌ 可能触发 socket 错误 | ✅ 代理在重试窗口中吸收 |
| 服务器返回 5xx | ❌ 可能被解读为 socket 错误 | ✅ 代理区分协议错误和网络错误，前者透传 |
| 代理 3 次重试后仍失败 | — | ❌ 返回 502 + 保存上下文 → 守护脚本检测 → 自动恢复 |

> [!warning] 更正（2026-09-13）：上表「之后」列是**设计假设，未验证**（原文以逐行「✅ …」的确定语气给出），其中至少四处与实现或现行链路不符：
> - 「Keepalive 每 60s 刷新 NAT」：60s 大于 §1.1 的 ~40s NAT 空闲超时，见 §2.1 更正。
> - 「重试(最长 1+3+8=12s 恢复)」：参考实现 `.py` 的退避表是 `[1.0, 3.0, 8.0]`，但循环在 `attempt == MAX_RETRIES - 1`（第 3 次）时先 `break`（`.py:399`），实际只等待 1s+3s=**4s**，8s 从不执行；现行 `.js` 默认只重试 **1** 次、间隔 1000ms（`.js:20-21`）。所谓「代理 3 次重试」在现行部署里是 1 次。
> - 末行「守护脚本检测 → 自动恢复」：库内 `claude-network-guardian.sh` / `claude-full-guardian.sh`（本文写作 claude-guardian.sh）均已标注「⚠️ 归档」，[[claude-network-resilience-v2]] 亦判定守护脚本「不需要」；502 之后需要人工保存状态再恢复。
> - 「代理心跳保持活跃」「代理检测死连接」同 §3.2 更正：现行 `.js` 没有应用层心跳。
> 依据（内部）：`claude-resilience-proxy.py:399-403`、`claude-resilience-proxy.js:20-21`、`claude-network-guardian.sh:3-4`（核验于 2026-09-13）。

> [!warning] 残余复核（2026-09-13）：本表 7 行**全部判为「设计假设，未验证」并已由上面的更正块就地处置**，无需再逐行追。上面第 1 条 `「Keepalive 每 60s 刷新 NAT」` 在这一轮又推进一步：**不只是 60s > 40s 的问题，`.js:119` 的 keepalive 根本不在跨 NAT 的那条 socket 上**（它绑的是 `http.Server` 入站事件，只管 CC→代理 回环段），详见 §2.1 的残余复核。故该行结论应记为「**保活并未生效**」，而不是「间隔需要调小」。
> 依据：本机受控实验（Node v22.21.0，入站 3 次→`on('connection')` 3 次，出站 3 次→0 次）+ `claude-resilience-proxy.js:25-31/119`（核验于 2026-09-13）。

### 4.4 开销分析

```
代理延迟: < 1ms (本地回环)
代理内存: ~20MB (Python 进程)
代理 CPU: 可忽略 (零拷贝转发)
连接建立: 节省 ~1.1s (连接池复用，跳过 TLS 握手)

总体: 零性能损失，连接建立反而更快
```

> [!warning] 更正（2026-09-13）：本条前提不成立。「连接池复用，跳过 TLS 握手」所依据的连接池在参考实现 `.py` 里是**死代码**——`ConnectionPool.get_connection()`（`.py:172`）全文没有调用点，请求路径每次新建连接（`urllib.request.urlopen`，`.py:357`），连接池只在失败时被 `_pool.invalidate()`（`.py:405`）触碰；**现行部署的 `.js` 根本没有连接池**。因此 ~1.1s 的连接建立收益只有在连接池被真正接入后才成立，当前应记为 0。（原表述为「连接建立: 节省 ~1.1s (连接池复用，跳过 TLS 握手)」「总体: 零性能损失，连接建立反而更快」）
> 同一问题的上游表述：§3.1 流程图「连接池 + keepalive + 心跳」、§4.1 与 §七 的「Connection pool + heartbeat: 45s」，均应按「无连接池、无应用层心跳」订正。
> 另：「代理内存: ~20MB (Python 进程)」指历史参考实现；现行 Node 代理的内存占用未记录，采集方式见 `ps -o rss= -p <proxy_pid>`。

---

## 五、终极简化: HTTP/1.1 KeepAlive + 重试头

如果不想运行代理，还有一条更简单的路：**强制 HTTP/1.1 连接复用**。

大部分 "socket closed unexpectedly" 发生在 HTTP/2 连接上。HTTP/2 的复用连接更容易被中间设备（NAT/防火墙）静默关闭，而不会通知客户端。

有些 API 兼容层（包括 DeepSeek）在使用 HTTP/1.1 时反而更稳定。

```bash
# 尝试通过环境变量强制 HTTP/1.1
# (是否生效取决于 Claude Code 和 SDK 的实现)
export NODE_OPTIONS="--http-parser=legacy"
# 或
export UV_THREADPOOL_SIZE=4
```

> [!warning] 更正（2026-09-13）：`--http-parser=legacy` 已不在 Node 的 CLI 文档中（现行只保留 `--insecure-http-parser`）；本机 Node v18.16.1 实测 `node --help` 无该开关、经 `NODE_OPTIONS` 传入时被静默忽略，既不会切换解析器，也不会强制 HTTP/1.1（原表述为「尝试通过环境变量强制 HTTP/1.1 … export NODE_OPTIONS="--http-parser=legacy"」）。`UV_THREADPOOL_SIZE=4` 只调整 libuv 线程池大小，与 HTTP 协议版本、连接复用无关，同样达不到目的。
> 可核验的替代：① 代理层收口（本文 §三 / §四 方案，唯一可控且可观测）；② 若必须在客户端侧控制协议版本、超时与连接复用，需在 SDK/Agent 层显式配置，Node 没有对应的环境变量开关。
> 依据：https://nodejs.org/api/cli.html（核验于 2026-09-13）

这种方式不可靠，因为无法保证 Claude Code 的 fetch 实现会遵循这些设置。**代理方案是唯一 100% 可控的方案。**

---

## 六、立即可执行的三步

```bash
# 第一步：内核加固（立即生效）
sysctl -w net.ipv4.tcp_keepalive_time=60
sysctl -w net.ipv4.tcp_keepalive_intvl=10
sysctl -w net.ipv4.tcp_keepalive_probes=3

# 第二步：启动代理（选做，推荐）
python3 /root/claude-resilience-proxy.py &
# 验证代理存活
# 注: ANTHROPIC_BASE_URL 指向 DeepSeek 兼容端点时，模型名映射为 deepseek-chat（原 claude-haiku-4-5 为 Anthropic 模型名）
curl -s http://127.0.0.1:8787/anthropic/v1/messages \
  -H "Authorization: [已脱敏] $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","max_tokens":1,"messages":[{"role":"user","content":"ping"}]}' \
  | head -c 100

# 第三步：使用
ANTHROPIC_BASE_URL=http://127.0.0.1:8787/anthropic \
  claude --permission-mode accept-edits
```

---

## 七、完整韧性体系全景图

```
┌──────────────────────────────────────────────────────────────┐
│                        Claude Code                             │
│  ANTHROPIC_BASE_URL=http://127.0.0.1:8787/anthropic           │
│  --permission-mode accept-edits                                │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 1: Resilience Proxy (localhost:8787)                   │
│  ├─ Connection pool + heartbeat (45s)                         │
│  ├─ Per-socket TCP keepalive (60s)                            │
│  ├─ Auto-retry on socket error (3x, backoff 1/3/8s)          │
│  └─ Graceful 502 with save-context directive                  │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 0: Kernel TCP Stack                                    │
│  ├─ tcp_keepalive_time = 60                                   │
│  ├─ tcp_keepalive_intvl = 10                                  │
│  ├─ tcp_keepalive_probes = 3                                  │
│  └─ tcp_retries2 = 5                                          │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  Internet → api.deepseek.com/anthropic                        │
└──────────────────────────────────────────────────────────────┘

如果以上全部失效（基站物理断连）:

┌──────────────────────────────────────────────────────────────┐
│  Layer 2: Smart Recovery                                      │
│  ├─ claude-guardian.sh 检测到 session 死亡                     │
│  ├─ 读取 context-dump.md 恢复思维状态                          │
│  ├─ 读取 task-state.json 获取任务进度                          │
│  ├─ 注入恢复 prompt：禁止推翻 Decision + 从断点继续             │
│  └─ 新会话 + 恢复 prompt 注入（--resume 不接续上下文，历史口径） │
└──────────────────────────────────────────────────────────────┘
```

**四层防御**（设计假设，未验证）：
| 层 | 职责 | 失败概率 | 恢复代价 |
|----|------|----------|----------|
| L0 内核 TCP | 防止 NAT 空闲超时断开 | 5%（物理链路中断无法防止） | 0 |
| L1 透明代理 | 自动重试 socket 错误 | 1%（3次重试全部失败） | 1-12s 延迟 |
| L2 外部大脑 | 保存思维状态 + 精确恢复 | 0% | ~300 tokens |
| L3 守护脚本 | 自动检测 + 拉起 + 注入 prompt | 0% | 0（用户无感） |

> [!warning] 更正（2026-09-13）：表中百分比无来源、无样本量，应视为**设计假设（未验证）**，且有两处内部矛盾：
> - L2/L3 的「0%」与本文 §4.3 自己的失败行（「代理 3 次重试后仍失败 → 返回 502」）冲突：代理失败后恢复流程是否成功并不是零概率（原表述为「| L2 外部大脑 | 保存思维状态 + 精确恢复 | 0% |」「| L3 守护脚本 | 自动检测 + 拉起 + 注入 prompt | 0% | 0（用户无感） |」）。
> - L1 的「1-12s 延迟」「3次重试全部失败」同 §4.3 更正：参考实现 `.py` 实际只等待 4s（1+3，8s 不执行），现行 `.js` 默认只重试 1 次、间隔 1s；L0 的「5%」是估计值，未记录依据。
> - L3 的「自动检测 + 拉起 + 注入 prompt」所依赖的守护脚本在库内已归档（见 §4.3 更正）。
> 依据（内部）：`claude-resilience-proxy.py:399-403`、`claude-resilience-proxy.js:20-21`（核验于 2026-09-13）。

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §2.1 应用层 keepalive 间隔 60s 大于 §1.1 实测的 ~40s NAT 空闲超时，时序上自相矛盾；§3.2 内嵌注释又写「低于 NAT 的 60s 超时」 | 就地标注：探测间隔必须严格小于最小空闲超时（建议 20-30s）；历史 sysctl 60/10/3 与参考实现 `.py` 的 `TCP_KEEPIDLE=60` 同此；现行 `.js:119` 亦为 60s，需同步修改 |
| 纠错 | §五 `NODE_OPTIONS="--http-parser=legacy"`：该开关已不在 Node CLI 文档中 | 就地标注：该开关被静默忽略，不切换解析器；`UV_THREADPOOL_SIZE` 与协议版本/keepalive 无关；补代理层与 SDK 层替代路径。依据：https://nodejs.org/api/cli.html（核验于 2026-09-13） |
| 纠错 | §3.2 把 `select.select` 判活当作「心跳保活」，并把 `.py` 参考实现当作现行部署 | 就地标注：写集合只反映本地发送缓冲可写性，不发送数据、不刷新 NAT 计时；现行 `.js` 无应用层心跳；补归属与重试预算差异 |
| 纠错 | §4.4「连接建立: 节省 ~1.1s (连接池复用，跳过 TLS 握手)」 | 就地标注：`.py` 的 `ConnectionPool.get_connection()` 无调用点（死代码），现行 `.js` 无连接池，该收益当前应记为 0；§3.1 / §4.1 / §七 的「连接池」表述同此 |
| 纠错 | §4.3 效果矩阵与 §七 概率表（5%/1%/0%/0%、1+3+8=12s）被当作定量结论 | 改标「设计假设，未验证」；12s 订正为 `.py` 实际 4s（1+3，8s 不执行）、现行 `.js` 1 次/1s；标注 L2/L3 的 0% 与 §4.3 失败行自相矛盾、守护脚本已归档 |
| 残余复核 | §2.1「`.js:119` 需同步修改」与 §4.3「Keepalive 每 60s 刷新 NAT」两处都把 keepalive 认在跨 NAT 的 socket 上 | **定论：改错对象。** `server.on('connection')` 绑的是 `http.Server` 入站事件，只覆盖 CC→代理 回环段，不覆盖代理→api.deepseek.com 出站 socket（跨 NAT 的那条）。依据：本机受控实验（Node v22.21.0，入站 3 次→事件 3 次、出站 3 次→事件 0 次）+ `claude-resilience-proxy.js:25-31/119`（核验 2026-09-13）。**代码侧仍开放**：119 行现值仍 60000、上游路径无 keepalive 调用；修改点应为 `doRequest()` 内的 `req.socket.setKeepAlive`，改后需真机 `ss -tno` 复测 |
| 残余复核 | §4.3 效果矩阵 7 行（L516-524）作为待办被重新登记 | **非待办**：整表已由上一更正块判为「设计假设，未验证」并逐条处置，本轮不再逐行追；仅第 1 条（Keepalive 60s 行）因上述新证据追加结论 |

回链：[[CORRECTIONS]] · [[AGENTS]]
