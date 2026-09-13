---
title: 树莓派状态排查与预防措施计划
aliases: [Pi 状态排查计划, API Key 预防措施, GitHub Key 泄漏排查]
tags: [ai/ops, incident]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# 树莓派状态排查与预防措施计划

See also: [[Claude-Ops-KB-Home]] · [[api-key-leak-postmortem]] · [[claude-deployment-record]] · [[deploy-workflow-write-to-repo-first]]

> 日期: 2026-06-29 | 状态: Pi 离线, 等待上线执行

---

## 一、GitHub Key 泄漏 — 已确认并清除

### 发现
公开仓库 `agent-knowledge-base` 的 `diagnostic-relay/deploy.sh` 包含完整 DeepSeek key `sk-<REDACTED>...`

### 清除
- `git filter-branch` 从历史中彻底移除
- force push 覆盖远程

> [!warning] 更正（2026-09-13）：节标题「已确认并清除」是过度断言（原表述为上面「清除」两条 + 节标题）
> GitHub 官方逐字：「If you only rewrite your history and force push it, the commits with sensitive data **may still be accessible elsewhere**: In any clones or forks of your repository / Directly via their SHA-1 hashes in **cached views** on GitHub / Through any pull request that references them」；**cached views 需联系 Support 才能永久清除**，且官方只在「风险无法通过轮换凭据缓解」时才协助。
> 另：官方推荐用 **`git-filter-repo`**（≥2.47 的 `--sensitive-data-removal`）；`git filter-branch` 手册开篇逐字警告「has a plethora of pitfalls… **its use is not recommended**」。
> 正确结论应写成：**「已从分支可及历史中移除；GitHub 缓存视图、他人 clone / fork 未清除，需 Support 工单 + 通知协作者」**。
> 依据：<https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository> · <https://man7.org/linux/man-pages/man1/git-filter-branch.1.html>

### 提交信息
```
commit f5a1229 (Jun 29 00:23)
Author: L-ingqin12
feat: CC缓存修复(35.5%→85%+) + Hermes缓存监控 + Pi/Termux差异指南
```

> [!warning] 补（2026-09-13）：泄漏载体、commit 与清除结果都没有外部可核验链接（原表述为上面「发现 / 清除 / 提交信息」三节）
> 文档只写「公开仓库 `agent-knowledge-base` 的 `diagnostic-relay/deploy.sh`」「commit f5a1229 (Jun 29 00:23)」，**没有仓库 / commit 的 permalink**，因此「泄漏载体是什么、清除范围多大、结果如何」全都只能靠自我声明——配合上一条 GitHub 缓存视图的限制，这份「已确认并清除」**不可复核**。
> 至少应补：①仓库与 commit 的 **permalink**；②清理**前后**的 `git log --oneline` 片段；③**哪些 ref 已被重写**的清单（`git for-each-ref` 输出）；④Support 工单号（若已提交）。

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

> [!warning] 补（2026-09-13）：这套扫描**看不到历史，也看不全文件类型**（原表述为上面 `--depth 1` + 扩展名白名单的写法）
> **① 看不到历史**：命令用 `gh repo clone … --depth 1`，只取最新工作树。而本次事故**恰恰是「密钥进了历史后被 filter-branch 处理」**——工作树扫描对这类残留**天然无效**。本库首页 2026-09-13 的订正踩过同一个坑（「工作树 ≠ 远端」，且过滤器把待查对象筛掉还谎报「无残留」）。
> **② 文件类型不全**：`--include` 白名单只有 `*.sh` / `*.md` / `*.json` / `*.yaml` / `*.py`，漏了 `.js` / `.ts` / `.tsx` / `.env` / `.toml` / `.yml` / `.txt` / `.xml` / `.properties` 等常见载体。
> **③ 排除规则会把待查对象筛掉**：`grep -v "…placeholder\|example\|<ARK\|<FEISHU\|settings.local"` 属于「用过滤器消除命中」——按本库教训，这会**自己制造「无残留」的假象**；排除项必须逐条写明理由，并**单独输出被排除的命中数**。
> 该补：①改用 **`git log -p --all`** 做全历史扫描，或直接上 **gitleaks / trufflehog**（带 baseline）；②白名单改成「全文件类型扫描 + 跳过二进制」；③明确写出「**扫描对象 + 模式 + ref 范围 + 日期 + 可重跑命令**」。

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

> [!warning] 补（2026-09-13）：清单漏了泄漏响应的**第一步**——吊销 / 轮换（原表述为上面「立即实施」四项）
> GitHub 官方逐字：「as a **first step** you need to **revoke and/or rotate** that secret. Once the secret is revoked or rotated, it can no longer be used for access, and **that may be sufficient to solve your problem**. Going through the extra steps to rewrite the history and remove the secret **may not be warranted**.」
> 本文 §3.1 只列了 pre-commit / `.gitignore` / 死锁修复 / 单 key 原则——**全是事后预防，没有一条响应动作**。该补：
> - **被泄漏 key 的吊销时间**与**责任人**；
> - **「已确认失效」的验证方式**：用旧 key 调一次 API，**期望返回 401**（把命令与输出记下来）；
> - 轮换后新 key 的存放位置（与 §3.3 保持一致）。
> 依据：<https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository>
>
> 同表另有两项**只有结论、没有可复核定义**：
> ① **「model_router 死锁修复：已实施」**缺验收命令与证据——`systemctl cat model-router` 的输出片段、**一次真实调用落在树莓派 key 上的证明**、手机 key 侧**零消耗**的账单依据。没有这三样，「已实施」无法被后来者复核。
> ② **「每周 cron 扫描」**（见 §3.4）没给**脚本路径、执行位置（哪台机器）、失败告警去处与结果归档位置**。按本库「日志可审计」，cron 必须留下可回查的运行记录。

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

> [!warning] 更正（2026-09-13）：上面 `xargs grep -lP` 那一行有两个实用缺陷（原表述为该行）
> GNU xargs 手册逐字：「`-r, --no-run-if-empty`: If the standard input does not contain any nonblanks, do not run the command. **Normally, the command is run once even if there is no input.**」
> - **① 没有暂存文件时 `grep` 仍会被执行**，且不带文件参数——于是它去读 **stdin**（提交时表现为**卡住**）。
> - **② `--name-only` 按空白切分**，含空格或特殊字符的文件名会被拆坏。
>
> 修法：
> ```bash
> git diff --cached --name-only -z | xargs -0 -r grep -lP -- "$patterns"
> # 或者直接用 git grep
> git grep --cached -lP -- "$patterns"
> ```
> 另：`grep -P` 依赖 GNU grep，脚本应先检测再降级到 `-E`。
> 依据：<https://man7.org/linux/man-pages/man1/xargs.1.html>

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

> [!warning] 补（2026-09-13）：7 项复选框没有优先级、顺序依赖与完成判据（原表述为上面整节）
> 条数核对为 **7 ✓**；第 7 项「更新 `api-key-leak-postmortem.md` 最终结论」**依赖第 1–3 项**，属收口动作，必须放在最后。
> 该补：①**执行顺序与阻塞关系**（建议 1 → 2 → 3 → 5 → 6 → 4 → 7：先做能产出证据的扫描与 hook，再做健康检查与结论收口）；②每项的**产出物**（扫描报告落盘路径、hook 部署后一次 `git commit` 试跑的输出、日志片段）；③**「什么算完成」**——例如第 1 项完成 = 扫描报告落盘，且报告里写明「扫描对象 + 模式 + ref 范围 + 日期 + 可重跑命令」。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 纠错 | 「`git filter-branch` 从历史中彻底移除 + force push 覆盖远程」写在「已确认并清除」标题下，属过度断言 | §一保留原文并加更正块：GitHub 官方列出三种「commits may still be accessible」路径（clone/fork、cached views、PR 引用），cached views 需 Support 清除；官方推荐 git-filter-repo，filter-branch 手册自述「not recommended」。改为「已从分支可及历史移除；缓存视图与他人 clone 未清除」 |
| 纠错 | pre-commit hook 里 `if git diff --cached --name-only \| xargs grep -lP "$patterns"` 有两个实用缺陷 | §3.2 保留原因并加更正块：无输入时 xargs 仍会运行一次 grep 且无文件参数 → 读 stdin 卡住；`--name-only` 按空白切分会拆坏含空格文件名。给出 `-z`/`-0 -r` 与 `git grep --cached` 两种修法，并提示 `-P` 需降级到 `-E`。依据 man7 xargs |
| 补疏漏 | GitHub 全面扫描用 `--depth 1` + 工作树 grep + 五个扩展名白名单，看不到历史也看不全文件类型 | §2.1 加补正块三点：工作树扫描对「历史里的残留」天然无效、白名单漏 `.js/.ts/.env/.toml/.yml` 等、`grep -v` 排除规则会制造「无残留」假象；改法为 `git log -p --all` 或 gitleaks/trufflehog，并要求写明扫描对象+模式+ref 范围+日期 |
| 补疏漏 | 预防措施清单缺少泄漏响应的第一步：吊销 / 轮换 | §3.1 加补正块，引 GitHub 官方「as a first step you need to revoke and/or rotate that secret」；要求补吊销时间、责任人、与「用旧 key 调 API 期望 401」的验证记录 |
| 加厚 | 「model_router 死锁修复：已实施」与「每周 cron 扫描」两项都只有结论，没有可复核定义 | 同 §3.1 补正块中给出：model-router 需 systemctl 输出片段 + 真实调用落在树莓派 key 的证明 + 手机 key 零消耗账单；cron 需脚本路径、执行位置、失败告警去处与结果归档 |
| 加厚 | 「四、待 Pi 上线后执行」7 项复选框没有优先级、顺序依赖与完成判据 | §四加补正块：条数核对为 7；第 7 项依赖 1–3 项须收口；给出建议执行顺序 1→2→3→5→6→4→7、每项产出物与完成判据 |
| 补疏漏 | 泄漏载体、commit 与清除结果都无外部可核验链接（无仓库 URL、无 commit URL） | §一「提交信息」后加补正块：要求仓库/commit permalink、清理前后 `git log --oneline` 片段、被重写 ref 清单（`git for-each-ref`）、Support 工单号 |

> [!note] frontmatter 变更
> `status: draft → review`：本文首次获得可核验的外部来源（GitHub 官方 sensitive-data 文档、man7 手册），但 Pi 侧排查与结论收口仍需人工执行，故停在 `review` 而非 `stable`。

回链：[[CORRECTIONS]] · [[AGENTS]]
