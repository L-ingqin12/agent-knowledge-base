---
title: Proxy cancelRetry Hook 事故复盘
aliases: []
tags: [ai/ops, incident]
created: 2026-06-22
updated: 2026-09-13
status: stable
---

# Proxy cancelRetry Hook 事故复盘

See also: [[Claude-Ops-KB-Home]] · [[claude-proxy-restart-incident]] · [[claude-streaming-forward-design]]

> 日期: 2026-06-22 ~ 2026-06-23 | 影响: 多个会话处于 "resuming conversation" / "处理中" 卡死状态

---

## 一、事故现象

- **Jun 23 08:00** 前后，多个 Claude Code 会话卡在 "resuming conversation" 或首条消息持续"处理中"
- 用户端无任何错误提示，表现为无限等待
- `ps aux` 显示一个 claude 进程处于 **D 状态（disk sleep, `_do_fork`）**，另一个处于空闲 S 状态
- **重启 proxy 后恢复** → 确认代理链路为直接原因

## 二、完整时间线

| 时间 | 事件 |
|------|------|
| Jun 22 14:10 | Session `6df16972` 启动："排查后台另一session的API任务一直处于API error原因" |
| Jun 22 下午 | 在 session 中发现 CC 185 新增 `cancelRetry()` 方法 |
| Jun 22 L431 | **Agent 对 `/root/claude-resilience-proxy.js` 执行 Edit**：添加 request ID 计数器 + `clientReq.on('close')` 诊断 hook |
| Jun 22 L443 | 重启 proxy 使诊断代码生效 |
| Jun 22 L445 | **立即出现故障**：首条请求 "Request timed out" |
| Jun 22 L459 | 后续请求出现 "API Error: ConnectionRefused" |
| Jun 22 L479 | **用户回退 proxy.js**："回退原因是你添加的hook部分会造成原有的proxy通路拥塞导致会话可能不可达等问题" |
| Jun 22 L489+ | Agent 改为构建 **diagnostic-relay**（独立外部中继，零侵入） |
| Jun 23 ~08:00 | 会话恢复时再次出现卡死状态（proxy.js 可能在会话间被再次修改试图 hook cancelRetry） |
| Jun 23 08:10 | proxy.js Modify 时间戳 — 问题版本落盘（**未经过 git 追踪**） |
| Jun 23 08:38 | 回退 proxy.js → 重启 proxy → 链路恢复 |

## 三、根因分析

### 3.1 致命 BUG：`clientReq.on('close')` 竞态条件

问题代码（Edit L431 新增部分）：

```javascript
// [诊断] 检测客户端提前断开 — CC cancelRetry() 的直接证据
clientReq.on('close', () => {
    const elapsed = Date.now() - start;
    if (!clientRes.headersSent) {
        clientClosed = true;
        console.error(`[proxy] #${reqId} CLIENT-CLOSED at ${elapsed}ms`);
    }
});

// 后续在 try 块中:
const result = await doRequest({...}, body, RETRIES);  // ✓ 拿到 DeepSeek 响应
// ⚠️ 'close' 事件可能已在此刻触发 → clientClosed = true

if (!clientClosed) {              // ✗ BUG: 竞态条件下 clientClosed 为 true
    clientRes.writeHead(...);      // ← 跳过
    clientRes.end(result.body);    // ← DeepSeek 响应被静默丢弃
}
```

**`clientReq.on('close')` 并非只在"提前断连"时触发**。Node.js 中该事件在以下情况都会触发：

1. 客户端主动断开 TCP 连接 ✓ （cancelRetry 的目标检测场景）
2. 请求正常完成，HTTP 消息体消费完毕 ✗ （正常流程）
3. 底层 socket 因任何原因关闭 ✗

> [!note] 补疏漏（2026-09-13）：本条机制有官方文档 + 提交记录双重支持（结论不改）
> Node 官方文档对 `http.ClientRequest` 的 `close` 现写作 *Indicates that the request is completed, or its underlying connection was terminated prematurely*；提交 `f2dc7c84d6` 的 patch 原文为 `-Indicates that the underlying connection was closed.` / `+Emitted when the request has been completed.`，提交说明写明 *The close event is now emitted when the request has been completed and not when the underlying socket is closed.*。
> 出处归属更正：该行为源自 **PR #33035**（Node 16 起生效），而 `f2dc7c84d6` 本身是 PR #42521 的**文档**提交——引用时不要写成「对应 PR #33035 的那次提交」。
> 来源：https://nodejs.org/docs/latest/api/http.html ｜ https://api.github.com/repos/nodejs/node/commits/f2dc7c84d6

当 `close` 事件恰好在 `await doRequest()` 返回后、`writeHead()` 之前的窗口触发，`clientClosed = true` 导致合法的 DeepSeek 响应被**静默丢弃**。Claude 端永远收不到 API 响应 → 表现为无限 "处理中"。

### 3.2 架构性错误

```
    Claude Code ──▶ proxy.js ──▶ DeepSeek
                        │
                    单点故障
                    所有会话共用同一通路
```

proxy.js 是**所有会话的唯一 API 通路**。在其内部修改控制流（即使是诊断意图），一旦出错：

- 没有备用通路
- 没有进程级隔离
- 错误表现为"卡死"而非"报错"（响应被丢弃，TCP 连接未断开）

### 3.3 流程性错误

1. **无 git 追踪**：问题版本的修改直接发生在 `/root/claude-resilience-proxy.js`（部署路径），而非通过 workspace → deploy.sh 的受控流程
2. **无备份**：deploy.sh 无 `cp proxy.js proxy.js.bak` 步骤
3. **无隔离测试**：诊断代码在唯一生产通路上直接验证
4. **诊断与控制流混合**：`console.error`（诊断）与 `if (!clientClosed)`（控制流）混在同一改动中

## 四、恢复操作

1. 从 workspace 恢复正确版本：`cp ~/workspace/agent-knowledge-base/claude-resilience-proxy.js /root/claude-resilience-proxy.js`（目录旧名 `claude-code-knowledge`，2026-09-13 复核改名，见 §六）
2. 重启 proxy 进程
3. 验证：`curl -sI http://127.0.0.1:8787/` 返回正常
4. 确认会话恢复

## 五、教训与规则

### 5.1 硬规则（追加到行动前检查清单）

| # | 规则 |
|---|------|
| 1 | **禁止在部署路径直接编辑生产文件**。所有修改通过 workspace → deploy.sh 流程 |
| 2 | **诊断日志 ≠ 控制流修改**。诊断代码只能 `console.error`，不能引入 `if/else` 分支改变响应路径 |
| 3 | **单点通路的修改必须有逃生通道**。在唯一代理上验证前，先确保 rollback 脚本可用 |
| 4 | **修改前 git commit 当前状态**。确保 `git diff HEAD` 能精确显示改动内容 |
| 5 | **重启代理前验证语法**：`node --check proxy.js && timeout 5 node -e "require('./proxy.js')"` 确保能启动 |
| 6 | **修改代理后先 curl 验证**再让 Claude 会话使用：`curl -s -X POST http://127.0.0.1:8787/v1/messages ...` |

> [!warning] 补疏漏（2026-09-13）：规则 2 只说「不能改控制流」，没给正确检测客户端取消的替代实现
> Node 文档确认可用路径：`clientRes.writableEnded` / `writableFinished` / `destroyed` 均为文档化属性；`req.on('aborted')` 已标 *Deprecated in: v17.0.0, v16.12.0*、*Stability: 0 - Deprecated*，原文即 *Listen for the 'close' event instead.*
> 最小正确实现：判断响应是否已写出用 `clientRes.writableEnded || clientRes.writableFinished || clientRes.destroyed`，或在 `clientRes.on('close')` 中配合 `writableEnded`；**不要**再用 `req.on('aborted')`。
> 否证式自测：`curl --max-time 2` 主动中断时诊断日志必须出现，正常请求时必须不出现。

> [!warning] 补疏漏（2026-09-13）：规则 6 只有命令骨架，没有期望输出与失败判据
> 可复用四段式健康判据（每段给期望值，任一段不满足即回滚到 `.bak`）：① 进程在——`pgrep -f claude-resilience-proxy`；② 端口在听——`ss -tlnp | grep 8787`；③ 非流式请求应拿到**上游语义**的状态码（缺 key 时是 DeepSeek 认证错误，而不是本地 404 / 超时——对照 [[claude-proxy-deployment-postmortem]] §6.3 的两个可区分响应）；④ 流式请求用与真实客户端相同的协议栈，首字节在 N 秒内到达，且中途断开不影响后续请求。

### 5.2 正确的诊断架构

```
Claude Code → permafrost :8788 → relay :8789 → proxy :8787 → DeepSeek
                                    │
                              独立外部观察者
                              纯管道转发，零字节修改
                              带 /rollback.sh 逃生
```

`diagnostic-relay` 是正确方向：透明 TCP 中继，不解析/不修改任何字节，记录时间戳后原样转发。

> [!warning] 补疏漏（2026-09-13）：`:8789` 在本库同时承担两个用途，链路图也不一致
> 本文 §5.2 的链路是 `CC → permafrost :8788 → relay :8789 → proxy :8787`；[[claude-cache-incident-postmortem]] §五 教训 3 / §六 措施 1 把 `:8789` 当作**补丁隔离测试端口**；[[claude-cache-postmortem-2026-06-13]] §四 的架构图是 `CC → permafrost :8788 → proxy :8787`（无 relay）。
> 应补一张当前生效表并给出核对命令：
> | 监听者 | 端口 | 上游 | 用途 | 生命周期 |
> |--------|------|------|------|---------|
> | permafrost | 8788 | proxy / 上游 | 缓存对齐 | 常驻 |
> | relay（诊断中继） | 8789 | proxy | 观测（零字节修改） | 排障期 |
> | proxy | 8787 | DeepSeek | 韧性转发 | 常驻 |
> 核对：`ss -tlnp | grep -E '8787|8788|8789'` + 各端口健康检查（`curl http://127.0.0.1:<port>/`）。

### 5.3 文件部署规程

```bash
# 正确流程
cd ~/workspace/agent-knowledge-base
git add claude-resilience-proxy.js
git commit -m "fix: 描述改动"
cp claude-resilience-proxy.js /root/claude-resilience-proxy.js.$(date +%s).bak  # 备份
cp claude-resilience-proxy.js /root/claude-resilience-proxy.js                   # 部署
node --check /root/claude-resilience-proxy.js                                     # 验证
# 重启 proxy
# curl 验证
```

> [!warning] 补疏漏（2026-09-13）：§5.1 的 6 条硬规则全是文字约定，没有一条落到机器约束上
> §5.1 恰为 6 条规则、全是文字约定；§5.3 给的是人工流程（`git add/commit` → `cp .bak` → `cp` → `node --check`）——靠「记住要小心」挡不住同一处再犯（同族教训见 [[CORRECTIONS]] C-013：敏感字面量写进会公开的文档后同日复发四次，最终靠 `scripts/prepush-selfscan.sh` + CI 这类机器约束收敛）。
> 应补三条机器约束：① **部署闸门**——deploy.sh 部署前断言 workspace 与目标文件的哈希关系或已生成 `.bak`，否则拒绝部署；② **生产路径保护**——`chmod 444` 或属主分离，改写必须走 deploy.sh；③ **红测自证**——故意改坏生产文件后，自检必须报错并以非零码退出。

## 六、相关文件

| 文件 | 说明 |
|------|------|
| `/root/claude-resilience-proxy.js` | 部署路径（事故目标） |
| `~/workspace/agent-knowledge-base/claude-resilience-proxy.js` | 受控版本（md5 一致已回退） |
| `~/workspace/agent-knowledge-base/diagnostic-relay/` | 正确的诊断方案（外部中继） |
| `~/workspace/agent-knowledge-base/claude-proxy-restart-incident.md` | 前次 proxy 重启事故复盘 |
| Session `6df16972` | 事故发生会话（`claude --resume` 可查看完整对话） |

> [!warning] 更正（2026-09-13）：workspace 仓库已改名，原路径为 `~/workspace/claude-code-knowledge/`（本节与 §5.3、§四 的路径本次一并更新）
> 现名 **`L-ingqin12/agent-knowledge-base`**（旧路径 302 重定向：id 1265645967，public，pushed_at 2026-09-13T06:39:45Z）。按旧名 clone 会得到第二份目录，重演「同一文件两份拷贝」；§七 的哈希与提交要与新目录对应核对。
> 来源：https://api.github.com/repos/L-ingqin12/claude-code-knowledge

## 七、版本追踪状态

- **问题版本**：未被 git 追踪，已丢失（仅能从 session transcript 还原改动内容）
- **当前版本**：md5 `88ef3fe2a6f5348f160981ec3c8087a5`，与 workspace 一致
- **最近提交**：`eac4572 feat: 零中断重启 + SO_REUSEPORT + 备用端口滚动`

> [!warning] 补疏漏（2026-09-13）：哈希与提交要带命令、时间与比对结论；规则 5 的命令要给期望输出
> - 可复算：`md5sum /root/claude-resilience-proxy.js ~/workspace/agent-knowledge-base/claude-resilience-proxy.js`（期望两者同为 `88ef3fe2a6f5348f160981ec3c8087a5`）、`git log -1 --format='%H %cI %s'`（期望 `eac4572…` + 提交时间），并写明比对结论与执行时间。
> - 规则 5 的期望输出：`node --check proxy.js && timeout 5 node -e "require('./proxy.js')"` 应打印启动日志行并列出监听端口；没有期望输出，「验证通过」不可判定。
> - transcript 还原步骤与判据：在 Session `6df16972` 定位 L431 的 Edit diff → 重放该 diff → `node --check` 通过 + 一次流式自测成功，方可视为还原完成。

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 补疏漏 | §3.1 的机制结论无出处（结论本身正确） | 补 Node 官方文档 + 提交 `f2dc7c84d6` 双重出处，并更正归属：行为源自 PR #33035，该提交是 PR #42521 的**文档**提交 |
| 补疏漏 | §5.1 规则 2 没给「正确检测客户端取消」的替代实现 | 补 `writableEnded` / `writableFinished` / `destroyed` 用法、`'abort'` 已废弃的官方标注，以及 `curl --max-time 2` 的否证式自测 |
| 加厚 | §七 只给 md5 与提交号（无命令、时间、比对结论）；规则 5 命令无期望输出 | 补 `md5sum` 双路径与 `git log -1 --format='%H %cI %s'` 的期望值、`node --check` 启动日志期望、Session `6df16972` transcript 还原步骤与判据 |
| 补疏漏 | §5.2 把 relay 画在 `:8789`，与姊妹篇「补丁隔离测试端口 `:8789`」及无 relay 的架构图冲突 | 补「监听者 / 端口 / 上游 / 用途 / 生命周期」生效表与 `ss -tlnp \| grep -E '8787\|8788\|8789'` 核对命令 |
| 加厚 | §5.1 规则 6 只有 `curl` 命令骨架 | 补四段式健康判据（进程 / 端口 / 上游语义状态码 / 流式首字节）与「任一段不满足即回滚 `.bak`」 |
| 纠错 | §四 / §5.3 / §六 的 workspace 路径仍用旧仓库名 `claude-code-knowledge` | 保留旧名说明并更新为 `agent-knowledge-base`（GitHub 302 重定向 + 仓库元数据可核），避免按旧名 clone 出第二份 |
| 补疏漏 | §5.1 六条规则全是文字约定，无机器约束 | 补三条机器约束：部署闸门（哈希 / `.bak` 断言）、生产路径保护（`chmod 444` 或属主分离）、红测自证（改坏后必须非零退出），对齐 [[CORRECTIONS]] C-013 的落点 |

依据与索引：[[CORRECTIONS]] · [[AGENTS]]
