---
title: PRoot 端口重启问题 — 根因与修复
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-07-02
updated: 2026-09-13
status: review
---

# PRoot 端口重启问题 — 根因与修复

See also: [[Claude-Ops-KB-Home]] · [[claude-proxy-restart-incident]] · [[claude-resilience-architecture]]

> 日期: 2026-07-02 | 影响: kill proxy 后端口永久占用，必须重启 Termux

---

## 根因

PRoot + Android 内核下，TCP 端口被释放后进入 TIME_WAIT 状态，**`SO_REUSEADDR` 无法覆盖**，端口长时间占用（实测 >60s，非永久）。

```
kill 进程 → 端口 TIME_WAIT → bind 同一端口 → EADDRINUSE
SO_REUSEADDR 生效                    ❌ 失败
SO_REUSEADDR + SO_REUSEPORT          ✅ 成功
```

## 修复: proxy 加 SO_REUSEPORT

```javascript
// claude-resilience-proxy.js 新增
server.on('listening', () => {
    const sock = server._handle; // 获取底层 socket
    // 实际上 Node.js http server 不直接暴露，需要在创建时设置
});

// 正确方式: Node.js ≥13.9 支持 net.Server listen 的 options.reusePort
// (http.createServer 返回的 server 继承 net.Server，其 listen 同样接受 options)
net.createServer(handler).listen({ port: 8787, host: '127.0.0.1', reusePort: true });
```

**Node.js 下的实施方式**：在 server 创建后、listen 前设置：

```javascript
const server = http.createServer(handler);
server.on('listening', () => {
    // 已监听，无需额外操作
});
// 关键: 在 createServer 层面无法设 SO_REUSEPORT
// 替代方案: 用 net.createServer 手动设置后传给 http
```

**或者最简单的修复**：deploy.sh 中如果 proxy 启动失败（端口占用），自动使用备用端口，同时更新 permafrost upstream。

```bash
# deploy.sh start_proxy 改为:
start_proxy() {
    for port in 8787 8789 8790; do   # 跳过 8788 (permafrost 固定端口)
        if ! curl -s "http://127.0.0.1:$port/" >/dev/null 2>&1; then
            PROXY_PORT=$port
            node /root/claude-resilience-proxy.js > /root/.claude/proxy.log 2>&1 &
            ...
            break
        fi
    done
}
```

> [!warning] 更正（2026-09-13）：上面的备用端口池与**现行端口占用冲突**——`8790` 已是 cache-relay 常驻端口（`cache-relay.mjs`），不能再作代理备用端口；**候选池应改为 `8791+`**。（原表述为「for port in 8787 8789 8790; do   # 跳过 8788 (permafrost 固定端口)」）

**端口所有者登记（2026-09-13 校）**

| 端口 | 所有者 | 状态 |
|------|--------|------|
| 8787 | `claude-resilience-proxy.js`（现行部署，Node 版） | 在用；未监听时先核对配置再判故障 |
| 8788 | permafrost 固定端口 | 在用，勿借用（原表已跳过） |
| 8789 | 待隔离测试预留（[[claude-streaming-forward-design]] 附1；`claude-permafrost-deploy.sh` 候选） | **预留，非已占用** |
| 8790 | cache-relay（`cache-relay.mjs`） | 在用 |
| 8791+ | — | 备用候选池 |

判定命令（不要凭记忆，先看真实占用）：

```bash
ss -tlnp | grep -E ':(8787|8788|8789|8790|8791)\b'
# 示例输出（进程名取自库内登记，PID 省略）：
# LISTEN 0 511 127.0.0.1:8787 0.0.0.0:* users:(("node",pid=…,fd=…))
# LISTEN 0 511 127.0.0.1:8790 0.0.0.0:* users:(("node",pid=…,fd=…))
```

> 注意：据 [[deepseek-400-mitigation-usage]]，`~/.claude/settings.local.json` 的 `ANTHROPIC_BASE_URL` 指向 `http://127.0.0.1:8790`（cache-relay 常驻端口），但**生效值取决于配置合并优先级**（该文 §一 已注明本机 `settings.json` 可能仍是直连）。因此 **8787 无监听并不必然等于链路故障**——判定前先核对生效 base URL 与实际监听，再下结论。

**回滚步骤**：(1) 通用退路 `bash /root/claude-rollback.sh`（停全部代理、恢复直连 DeepSeek）；(2) 仅改端口出错时，把 `ANTHROPIC_BASE_URL` 改回 `https://api.deepseek.com/anthropic` 或改回原端口，再 `bash /root/claude-resilience-deploy.sh status` 确认代理状态。

## 已验证结论

| 方案 | PRoot 下效果 |
|------|-------------|
| SO_REUSEADDR 单独 | ❌ 无效 |
| SO_REUSEPORT + SO_REUSEADDR | ✅ 立即可绑 |
| 等待端口释放 | ❌ >60s 不行 |
| 用不同端口 | ✅ 可行 |
| Termux 完全重启 | ✅ 可行 |

### 最小复现记录（补，2026-09-13）

> [!warning] 加厚（2026-09-13）：上表四行结论原文未附验证环境、命令与输出，无法复核。以下为可重跑的最小复现步骤；标「未记录」的字段需在下次复现时回填。

**环境（原文未记录）**：Android Termux + PRoot。复现前先记录 `uname -a`、`getprop ro.build.version.release`、`node -v`——原文未留这些值，无法判断结论是否随内核 / Termux 版本漂移。

```python
# bind-close-bind 最小复现：对比「仅 SO_REUSEADDR」与「SO_REUSEPORT + SO_REUSEADDR」
python3 - <<'PY'
import socket
def bind_once(tag, reuseport=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if reuseport:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    try:
        s.bind(("127.0.0.1", 8787)); s.listen(1)
        print(tag, "bind OK")
    except OSError as e:
        print(tag, "bind FAIL errno=%d (%s)" % (e.errno, e.strerror))
    return s
a = bind_once("first"); a.close()      # 关闭 → TIME_WAIT
bind_once("rebind")                    # 仅 SO_REUSEADDR
bind_once("rebind+reuseport", True)    # 两标志齐上
PY
```

| 原文结论 | 复现命令 | 观察点（按原文期望；实测不符则就地修订该行） |
|----------|----------|-----------------------------------------------|
| SO_REUSEADDR 单独 ❌ 无效 | 上面的脚本，`reuseport=False` | 期望 `rebind bind FAIL errno=98 (EADDRINUSE)` |
| SO_REUSEPORT + SO_REUSEADDR ✅ 立即可绑 | 上面的脚本，`reuseport=True` | 期望 `rebind+reuseport bind OK` |
| 等待端口释放 ❌ >60s 不行 | 关闭后每 5s 试绑一次，记录首次成功时刻 | 原文未记录测量方法与样本数 |
| 用不同端口 ✅ 可行 | 把 `bind` 端口换成 8791 | 期望 `bind OK` |
| Termux 完全重启 ✅ 可行 | 重启后直接绑原端口 | 期望 `bind OK` |

**「>60s」的测量口径（原文未记录，建议补）**：`t0=$(date +%s)` 记 close 时刻，循环 bind 至成功，输出 `$(( $(date +%s) - t0 ))`；单次观察不足以支撑「>60s」这类区间描述，至少重复 3 次并逐次记秒数。

## 规则

1. 永不手动 kill 生产进程（已有规则）
2. proxy 代码加 SO_REUSEPORT（下次更新时一并改）
3. deploy.sh 加备用端口机制

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §修复 的备用端口表 `for port in 8787 8789 8790` 与现行端口占用冲突（`8790` 已成为 cache-relay 常驻端口） | 就地加注：候选池改为 `8791+`，补端口所有者登记表、`ss -tlnp` 判定命令与回滚步骤；对 8789 改用弱化措辞（仅「待隔离测试」预留，非已占用）；依据 [[deepseek-400-mitigation-usage]]、[[claude-cache-relay-design]]、[[claude-streaming-forward-design]] |
| 加厚 | §已验证结论 表把四行结论列为「已验证」，但无验证环境、命令与输出 | 新增「最小复现记录」：bind-close-bind 的 `python3` 复现脚本、逐行观察点与 errno（EADDRINUSE=98）、`>60s` 的测量口径；环境与样本量原文缺失，标为「未记录」待回填 |

回链：[[CORRECTIONS]] · [[AGENTS]]
