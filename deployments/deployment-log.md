# 部署审计日志

## 2026-06-23

### diagnostic-relay (部署)
- **时间**: 08:34
- **操作**: 部署
- **变更**: 插入透明 TCP 中继 relay.js 于 permafrost→proxy 之间
- **目的**: 捕获 CC 185 cancelRetry() 导致的 ECONNRESET 证据
- **预检**: ✅ proxy 在线, relay 语法通过, 端口可用
- **E2E**: ✅ CC→permafrost→relay→proxy→DeepSeek
- **逃生**: `bash diagnostic-relay/rollback.sh`
- **commit**: 96796d0

### diagnostic-relay (逃生)
- **时间**: 08:36
- **操作**: 逃生回滚
- **结果**: ✅ permafrost upstream 恢复为 proxy 直连, relay 进程已停止

### diagnostic-relay (重新部署)
- **时间**: 09:22
- **操作**: 部署
- **目的**: 捕获 session fddcf916 持续 attempt 状态证据
- **预检**: ✅
- **E2E**: ✅
- **结果**: ✅ 成功捕获 9 次 ECONNRESET 证据 (37.5% 异常率)

### diagnostic-relay (当前状态)
- **状态**: 🟢 运行中
- **relay PID**: 26354
- **逃生**: `bash deployments/diagnostic-relay/rollback.sh`

## 变更管控框架就绪

### 可用部署项

| 部署项 | 状态 | 逃生 |
|--------|------|------|
| diagnostic-relay | 🟢 运行中 | `bash deployments/diagnostic-relay/rollback.sh` |
| proxy-timeout-fix | ⬜ 待部署 | `bash deployments/proxy-timeout-fix/rollback.sh` |
| cc-version-switch | ⬜ 待部署 | `bash deployments/cc-version-switch/rollback.sh` |

### 部署规则 (强制)

1. 部署前 git commit 记录改动
2. deploy.sh 含预检 + E2E 验证 + 失败自动回滚
3. rollback.sh 可一键恢复到部署前状态
4. 每次部署/逃生均追加本日志

### proxy-timeout-fix (部署)
- **时间**: 2026-06-23T11:49+08:00
- **操作**: 部署
- **变更**: timeout 180s→90s, retries 3→1, backoff env var化
- **备份**: /root/workspace/claude-code-knowledge/deployments/proxy-timeout-fix/backups/proxy.js.20260623-114915
- **逃生**: `bash deployments/proxy-timeout-fix/rollback.sh`

### proxy-timeout-fix (逃生)
- **时间**: 2026-06-23T11:49+08:00
- **操作**: 逃生回滚
- **恢复**: timeout=180s retries=3 backoff=1s/3s/8s
- **备份来源**: /root/workspace/claude-code-knowledge/deployments/proxy-timeout-fix/backups/proxy.js.20260623-114915

### proxy-timeout-fix (测试部署→逃生)
- **时间**: 2026-06-23T11:49
- **操作**: 完整部署→验证→逃生测试
- **测试结果**:
  - 阶段1 语法检查: ✅
  - 阶段2 测试端口(8791)运行: ✅ API正常, env var覆盖生效
  - 阶段3 脚本安全性: ✅ 语法/幂等/重复部署检测
  - 阶段4 生产部署+逃生: ✅ 部署成功(timeout=90s,retries=1), API正常, 逃生恢复原始参数
- **结论**: 补丁安全, 部署/逃生有效, 生产已恢复原始状态
- **逃生**: `bash deployments/proxy-timeout-fix/rollback.sh`

### proxy-timeout-fix (部署)
- **时间**: 2026-06-23T11:51+08:00
- **操作**: 部署
- **变更**: timeout 180s→90s, retries 3→1, backoff env var化
- **备份**: /root/workspace/claude-code-knowledge/deployments/proxy-timeout-fix/backups/proxy.js.20260623-115104
- **逃生**: `bash deployments/proxy-timeout-fix/rollback.sh`

## 2026-07-03

### proxy.js 状态归档
- **时间**: 2026-07-03
- **操作**: 归档当前生产 proxy.js 状态至仓库
- **变更**: 将生产部署路径 `/root/claude-resilience-proxy.js` (含 timeout-fix 生产调优版) 同步至仓库
- **md5**: `d129c2e139ff5d2610abcdb913c5fa14` (部署) → 同步至仓库
- **关键参数**:
  - RETRIES: env `PROXY_RETRIES` 默认 1
  - BACKOFF: env `PROXY_BACKOFF_MS` 默认 1000ms
  - timeout: env `PROXY_TIMEOUT_MS` 默认 90000ms
  - abort: 已加入 retryable 列表
- **代理链路**: CC → permafrost (:8788) → proxy (:8787) → DeepSeek
  - permafrost_proxy.py 运行中 (PID 30738)
  - proxy.js 运行中 (端口 :8787)
- **逃生通道**:
  - L1: `bash /root/claude-permafrost-rollback.sh` → permafrost 绕过 proxy
  - L2: 直连 DeepSeek
- **已知问题**: 
  - `ANTHROPIC_BASE_URL=http://127.0.0.1:8788` (permafrost 端口), 非直接 :8787
  - CC v2.1.198 → v2.1.199 升级失败 (`install_failed`, 已记录于 `2026-07-02T15:39:40.687Z`)
  - SessionStart hook 可用: `bash /root/claude-version-hook.sh full`
- **commit**: (本次提交)
