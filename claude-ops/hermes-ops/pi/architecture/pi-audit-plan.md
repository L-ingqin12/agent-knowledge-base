# 树莓派状态排查与预防措施计划

> 日期: 2026-06-29 | 状态: Pi 离线, 等待上线执行

---

## 一、GitHub Key 泄漏 — 已确认并清除

### 发现
公开仓库 `agent-knowledge-base` 的 `diagnostic-relay/deploy.sh` 包含完整 DeepSeek key `sk-<REDACTED>...`

### 清除
- `git filter-branch` 从历史中彻底移除
- force push 覆盖远程

### 提交信息
```
commit f5a1229 (Jun 29 00:23)
Author: L-ingqin12
feat: CC缓存修复(35.5%→85%+) + Hermes缓存监控 + Pi/Termux差异指南
```

---

## 二、Pi 上线后排查清单

### 2.1 GitHub 全面扫描
```bash
# 所有仓库扫描 (需在 Pi 上跑)
for repo in $(gh repo list L-ingqin12 --limit 50 --json name -q '.[].name'); do
    gh repo clone "L-ingqin12/$repo" "/tmp/scan/$repo" -- --depth 1 2>/dev/null
    matches=$(grep -rn "sk-[a-zA-Z0-9]\{20,\}\|ark-[a-z0-9]\{20,\}\|Bearer [a-zA-Z0-9_-]\{20,\}" \
        "/tmp/scan/$repo/" --include="*.sh" --include="*.md" --include="*.json" --include="*.yaml" --include="*.py" \
        2>/dev/null | grep -v "node_modules\|.git/\|placeholder\|example\|<ARK\|<FEISHU\|settings.local")
    [ -n "$matches" ] && echo "⚠️ $repo: $matches"
    rm -rf "/tmp/scan/$repo"
done
```

### 2.2 Pi 本地 key 审计
```bash
# 所有 API key 分布
grep -rn "sk-\|ark-\|cli_aaa\|Bearer " /home/pi/ /root/ \
    --include="*.yaml" --include="*.json" --include="*.sh" --include="*.env" \
    --include="*.py" --include="*.js" --include="*.md" \
    2>/dev/null | grep -v ".git/\|node_modules\|__pycache__\|.bak\|.log"

# 列出 key 清单 (脱敏)
# 输出格式: 文件路径 | key 前缀 | key 用途
```

### 2.3 sk-<REDACTED> 消费路径确认
```bash
# Claude Code permafrost 日志
cat /home/pi/.claude/proxy.log | head -100
cat /home/pi/.permafrost/logs/*.log 2>/dev/null | head -100

# Claude Code 历史
python3 -c "
import json
with open('/home/pi/.claude/history.jsonl') as f:
    for line in f:
        d = json.loads(line)
        print(f\"{d.get('timestamp','')[:19]} | msgs={d.get('message_count',0)} | model={d.get('model','')}\")
" | tail -50

# ARK 消费确认 (正常)
curl -s http://127.0.0.1:18888/stats
```

### 2.4 服务健康检查
```bash
systemctl --user status hermes-gateway hermes-gateway-ranzi model-router
systemctl status xray-proxy
ss -tlnp | grep -E "8787|8788|18888|10808"
```

---

## 三、预防措施

### 3.1 立即实施

| 措施 | 说明 |
|------|------|
| **Git pre-commit hook** | 扫描 `sk-`/`ark-`/`Bearer` 模式, 匹配到则拒绝提交 |
| **`.gitignore` 全局规则** | 忽略 `deploy.sh` / `.env` / 含 key 的文件 |
| **model_router 死锁修复** | 已实施: `--api-key` 显式传参, 不再从 config 回退 |
| **hermes config 单 key 原则** | 所有 `api_key` 字段使用同一把 key, 不混用 |

### 3.2 Git Pre-commit Hook

```bash
# 部署到所有 repo: ~/.git-templates/hooks/pre-commit
#!/bin/bash
# 禁止提交含 API key 的文件
patterns='sk-[a-zA-Z0-9]{20,}|ark-[a-z0-9]{20,}|Bearer [a-zA-Z0-9_-]{20,}|cli_aaa[a-z0-9]{10,}'
if git diff --cached --name-only | xargs grep -lP "$patterns" 2>/dev/null; then
    echo "⛔ 检测到 API key! 请移除后再提交"
    echo "   匹配模式: sk-*/ark-*/Bearer */cli_aaa*"
    exit 1
fi
```

### 3.3 Pi 全局配置规范

```
所有 API key 统一存放位置:
  /home/pi/.hermes/.env          ← hermes 用
  /home/pi/.claude.json          ← Claude Code 用 (由 permafrost 管理)
  
禁止存放位置:
  ❌ 任何 .sh 脚本中硬编码
  ❌ 任何 .md 文档中明文
  ❌ 任何 git 仓库中
  ❌ 飞书聊天消息中
```

### 3.4 监控与告警

| 项目 | 方法 |
|------|------|
| GitHub key 扫描 | 每周 cron: `grep` 所有 repo 的 shell/md/json 文件 |
| 日 token 消耗 | hermes guardian 新增 P7 探针: 读 model_router /stats |
| 异常消耗告警 | 单日 >100 次 API 调用 → 通知 |
| Config 变更审计 | `config.yaml` 的 `api_key` 变更记录到 git |

### 3.5 流程改进

| 当前做法 | 风险 | 改进 |
|---------|------|------|
| 飞书发送 key | key 进入聊天记录 | SSH 直接编辑 `.env` |
| deploy.sh 含 key | 容易被 git 提交 | 从环境变量读取 |
| model_router 从 config 回退读 key | 不可见的 key 切换 | 已修复: 显式 `--api-key` |
| 多个 ARK key 混用 | 难以追踪消费 | 统一为一把 key |

---

## 四、待 Pi 上线后执行

1. [ ] 运行 2.1 GitHub 全量扫描
2. [ ] 运行 2.2 本地 key 审计
3. [ ] 确认 2.3 sk-<REDACTED> 消费路径
4. [ ] 运行 2.4 服务健康检查
5. [ ] 部署 Git pre-commit hook
6. [ ] 部署每周 key 扫描 cron
7. [ ] 更新 `api-key-leak-postmortem.md` 最终结论
