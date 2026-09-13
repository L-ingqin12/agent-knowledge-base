---
title: Claude Code 无人值守方案
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-06-11
updated: 2026-09-13
status: review
---

# Claude Code 无人值守方案

See also: [[Claude-Ops-KB-Home]] · [[claude-unattended-cross-platform-guide]] · [[claude-unattended-methodology]]

> 基于当前环境（Android/Termux/PRoot/Ubuntu 24.04 aarch64, Claude Code v2.1.172）设计
> 更新日期：2026-06-11

> [!warning] 更正（2026-09-13）：版本数字落后近百个补丁版本
> 上面「Claude Code v2.1.172」（原表述，活跃 session 为 v2.1.170）是**撰写时基线**，不是当前版本：官方 changelog 显示 **2026-09-12 已发布 v2.1.270**（2.1.269 为 09-11）。本文依赖的机制另有版本门槛：
> - fork 式 `/subtask` 需 **v2.1.212+**；
> - 子代理并发上限 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`（默认 **20**，超限报 `Concurrent subagent limit reached`）需 **v2.1.217+**。
>
> 因此本文的 v2.1.172 应改写为「撰写时 2.1.172；本文机制依赖 **≥2.1.217**」，附录速查表的 PID / 会话号同理属**示例值，勿当现状**。
> 来源：<https://code.claude.com/docs/en/changelog.md> · <https://code.claude.com/docs/en/sub-agents.md>

---

## 一、环境约束与可用能力

### 1.1 环境架构

```
Android (aarch64)
  └── Termux (PID 22061)
       └── PRoot Ubuntu 24.04
            ├── Claude daemon (PID 21625, v2.1.172)
            ├── 活跃 session: 27780 (v2.1.170), 29097, 30349, 2990
            └── /root/workspace/ (多个 git 仓库)
```

### 1.2 约束清单

| 约束 | 影响 | 应对 |
|------|------|------|
| 无 systemd | 不能写 `.service` 文件 | 使用 Claude daemon + CronCreate |
| 无 tmux/screen | 不能 detach/attach 会话 | 使用 `claude --resume` + daemon 模式 |
| 无 cron daemon | 不能 crontab | 使用 Claude 内置 CronCreate |
| Android 进程管理 | Termux 可能被系统杀掉 | `termux-wake-lock` + daemon 自动重连 |
| PRoot 限制 | 部分 syscall 不可用 | 已验证 daemon 正常运行，无影响 |
| 双 npm 体系 | 升级搞错会破坏 claude | 严格遵守升级流程（见 memory） |

### 1.3 可用能力

| 能力 | 用途 | 命令/路径 |
|------|------|-----------|
| Claude daemon | 持久后台进程，管理 session 生命周期 | PID 21625，自动重启 |
| `claude --resume` | 恢复之前的会话 | 已有 session: 27780, 29097, 30349, 2990（共 4 个） |
| `claude -p` | 非交互式一次性任务 | `claude -p "任务" --permission-mode accept-edits` |
| `CronCreate` | 会话内定时任务 | 已在 `.claude/scheduled_tasks.json` 持久化 |
| `/loop` | 自主循环执行 | `/loop 10m 检查CI状态并修复失败` |
| `PushNotification` | 桌面/手机通知 | 任务完成/异常时推送 |
| `termux-wake-lock` | 防止 Android CPU 休眠 | `/data/data/com.termux/files/usr/bin/termux-wake-lock` |
| settings.local.json | 精细权限白名单 | `/root/.claude/settings.local.json` |

> 注（2026-09-13）：上两表的 **daemon 相关条目属本机观察**（`supervisorPid` 一类字段名未见于官方文档），其判活写法与官方替代路径（后台会话 + agent view）见 §3.1 更正；版本号见文首更正。

---

## 二、权限配置：消除确认弹窗

### 2.1 现状分析

当前 `settings.local.json` 有 ~200 条 allow 规则，但存在问题：

- **过于具体**：`Bash(git -C /root/workspace/gomoku status)` 只能匹配这一个仓库
- **大量一次性条目**：临时测试命令的 allow 规则堆积
- **缺少通用模式**：没有 `Bash(git status)` 这样的通用规则

### 2.2 推荐配置

在 `settings.local.json` 中按分层策略重构 permissions：

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(python3:*)",
      "Bash(node:*)",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(apt-get:*)",
      "Bash(apt:*)",
      "Bash(dpkg:*)",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(find:*)",
      "Bash(grep:*)",
      "Bash(mkdir:*)",
      "Bash(cp:*)",
      "Bash(mv:*)",
      "Bash(rm:*)",
      "Bash(tar:*)",
      "Bash(gzip:*)",
      "Bash(chmod:*)",
      "Bash(ln:*)",
      "Bash(echo:*)",
      "Bash(ps:*)",
      "Bash(kill:*)",
      "Bash(which:*)",
      "Read(//root/workspace/**)",
      "Read(//root/.claude/**)",
      "Read(//etc/**)",
      "Read(//usr/lib/**)",
      "Read(//usr/bin/**)",
      "Read(//tmp/**)",
      "Write(//root/workspace/**)",
      "Write(//tmp/**)",
      "Edit(//root/workspace/**)",
      "WebSearch",
      "WebFetch"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(rm -rf ~)",
      "Bash(rm -rf /root)",
      "Bash(rm -rf /*)",
      "Bash(git push --force:*)",
      "Bash(git push -f:*)",
      "Bash(claude update:*)",
      "Bash(npm -g uninstall @anthropic-ai/claude-code:*)",
      "Bash(shutdown:*)",
      "Bash(reboot:*)",
      "Bash(dd:*)",
      "Bash(>: /dev/sda:*)",
      "Bash(chmod 777:*)"
    ]
  }
}
```

> [!warning] 更正（2026-09-13）：`Bash(git:*)` 不是有效的 allow 规则写法
> 上面 allow 清单里的 `Bash(git:*)`、`Bash(npm:*)`、`Bash(rm:*)` 等（原表述为 `Bash(<命令>:*)`）以及 `Read(//root/workspace/**)` 的双斜杠写法需按官方权限语法修正：
> - 官方语法确有 `Tool(param:value)` 参数匹配，但**只用于 deny/ask**；**allow 规则继续使用各工具自己的 specifier 语法**，且不允许对 `command`/`file_path` 这类主内容字段做参数匹配（`Bash(command:rm *)` 会被忽略并在启动时告警）。故 allow 里的 `Bash(git:*)` **不会被当作前缀规则匹配**。
> - 正确写法是把 `*` 放在**子命令之后**：`Bash(git *)`、`Bash(npm run *)`、`Bash(git log *)`。
> - `*` 匹配任意文本（含空格）；**无 `*` 则要求完全相等**（`Bash(npm run build)` 不匹配 `npm run build --watch`）；`*` 出现在子命令之前（如 `Bash(git * main)`）会在启动时告警。
> - **最容易被绕过的点**：Bash 规则匹配**字面前缀**，`git -C . push` 这类变体不会被 `Bash(git push *)` 覆盖——deny 清单要按此复查。
>
> 来源：<https://code.claude.com/docs/en/permissions.md>

### 2.3 权限模式组合拳

| 场景 | permission-mode | + settings allowlist | 说明 |
|------|-----------------|---------------------|------|
| 交互开发 | `default` | ✅ | 保留关键确认 |
| 无人值守任务 | `accept-edits` | ✅ | 读写自动放行，网络仍需确认 |
| 全自动 CI/CD | `bypass` | ✅ | 全部跳过，仅限可信脚本 |

**最佳实践**：始终保留 `deny` 清单，不论使用什么模式。

> [!warning] 更正（2026-09-13）：权限模式已有六种，无人值守首选 `auto`
> 上表只列了三种，且把无人值守任务定为 `accept-edits`（原表述）。官方当前为**六种、配置值 camelCase**：`default`（CLI/扩展中显示为 **Manual**）、`acceptEdits`、`plan`、**`auto`**、**`dontAsk`**、`bypassPermissions`。
> - **`auto`**：由第二个模型（classifier）**逐条审动作**，是官方给出的**长任务推荐档**，Pro/Max/Team 计划的默认起始模式就是它——本文完全没提这一档，它恰是无人值守场景最该用的。
> - `acceptEdits` 的放行范围是「读取、文件编辑与常见文件系统命令（`mkdir`/`touch`/`mv`/`cp` 等）」，**网络操作并不因此自动放行**（原文该行说明正确）。
> - **`dontAsk`**：只允许**预先批准**的工具，其余**直接拒绝而非弹窗**——免打扰但不放权，适合心跳类只读任务。
> - 另可依赖一条兜底：关键路径删除（`rm -rf ~`、`rm -rf /`，含写在命令替换里的形式）在**所有模式下都由 Claude Code 自身无条件拒绝**，不依赖用户 deny 规则。
>
> 来源：<https://code.claude.com/docs/en/permission-modes.md>

---

## 三、会话持久化：用户断开后保持运行

### 3.1 Daemon 模式（当前已有）

Claude daemon (PID 21625) 是核心持久化层：
- 管理所有 session 的生命周期
- 在二进制更新后自动重启（日志已证实：v2.1.170 → v2.1.172）
- 进程挂在 init (PID 1) 下，不依赖用户终端

> [!warning] 更正（2026-09-13）：daemon 细节属**本机观察**；官方路径是「后台会话 + agent view」
> 官方 changelog 确实存在后台 daemon 概念（`cc-daemon-*` 临时目录残留的修复条目、daemon lock file 指向被复用 pid 的修复条目、background daemon start 等），说明该进程形态存在；但 `daemon.status.json` / `supervisorPid` 这两个**具体字段名在公开文档中检索不到**，属仅由本机观察支撑（同上文 §3.2 的判活写法）——应标注为「本机观察，字段名未见于官方文档」。
> 官方推荐的持久化/无人值守路径是**后台会话 + agent view**：
> - `/background` 把会话脱离终端，`claude agents` 集中监控；
> - **机器重启后 48 小时内**会话显示 `failed`，attach/回复即**从断点续跑**；**超过 48 小时**显示 `stopped`，可 `claude attach <id>` 恢复；
> - transcript 清理由 `cleanupPeriodDays` 控制。
>
> 故「靠 daemon 保活」宜改写为「靠后台会话 + agent view」，daemon 细节降级为本机现状记录。
> 来源：<https://code.claude.com/docs/en/agent-view.md> · <https://code.claude.com/docs/en/changelog.md>

### 3.2 启动无人值守会话的 SOP

```bash
# 步骤1：确保 daemon 存活
ps -p $(cat /root/.claude/daemon.status.json | python3 -c "import sys,json; print(json.load(sys.stdin)['supervisorPid'])")

# 步骤2：获取 wake-lock（防止 Android 杀进程）
/data/data/com.termux/files/usr/bin/termux-wake-lock

# 步骤3：以非交互模式启动任务
claude -p "你的任务描述" --permission-mode accept-edits

# 步骤4：或者在交互模式中启动 /loop
claude --permission-mode accept-edits
# 进入后：
# /loop 10m 你的循环任务
```

### 3.3 会话恢复

```bash
# 列出可恢复的会话
ls /root/.claude/sessions/

# 恢复指定会话
claude --resume --session-id <session-id> --permission-mode accept-edits

# 或在 daemon 存活的情况下直接
claude --resume
```

### 3.4 会话文件说明

```
/root/.claude/sessions/
├── 27780.json   # fork-session (v2.1.170), 长期运行
├── 29097.json   # --resume 会话
├── 30349.json   # 当前交互会话
└── 2990.json    # 最新会话

/root/.claude/scheduled_tasks.json  # 定时任务持久化
/root/.claude/shell-snapshots/      # shell 环境快照（会话恢复用）
```

> [!warning] 更正（2026-09-13）：会话不在 `~/.claude/sessions/`
> 官方路径**不是** `~/.claude/sessions/*.json`（原表述）。transcript 默认以 **JSONL** 存放在 `~/.claude/projects/<project>/<session-id>.jsonl`，其中 `<project>` 由**工作目录路径把非字母数字替换为 `-`** 得到（超过 200 字符会截断并追加完整路径哈希）。
> - 恢复三件套：`claude --resume`（打开选择器）/ `claude --resume <session-id>` / **直接传 transcript 绝对路径**。故 §3.3 的 `ls /root/.claude/sessions/` 应改为这套写法。
> - §8.3 的 `~/.claude/history.jsonl` 在所引官方页面中**均无记载**，「它是完整对话历史」这一说法无法确认 ⇒ 应改标**本机观察**。
>
> 来源：<https://code.claude.com/docs/en/sessions.md>

---

## 四、任务调度：定时与自主执行

### 4.1 三种调度方式对比

| 方式 | 持久化 | 需要会话在线 | 适用场景 |
|------|--------|-------------|----------|
| `CronCreate` | ✅ 写入 scheduled_tasks.json | ✅ | 固定时间点执行 |
| `/loop` 固定间隔 | ❌ 会话内 | ✅ | 周期检查/监控 |
| `claude -p` | ❌ 一次性 | ❌ | 脚本化单次任务 |

### 4.2 CronCreate — 会话内定时任务

当前已有示例（每工作日 9:13 检查 Claude Code 社区更新）：

```json
{
  "id": "[已脱敏]",
  "cron": "13 9 * * 1-5",
  "prompt": "Monitor Claude Code community updates...",
  "recurring": true
}
```

**新任务示例**：

```
# 每 2 小时检查 CI 状态
/cron 7 */2 * * * 检查 gomoku 仓库的测试状态，运行 pytest，如果失败尝试修复

# 每天晚上 22 点生成工作日报
/cron 3 22 * * * 扫描 /root/workspace 中所有 git 仓库今日的 commit，生成日报

# 每天早上 8 点拉取所有仓库最新代码
/cron 13 8 * * * 遍历 /root/workspace 中所有 git 仓库，执行 git pull
```

**注意**：CronCreate 任务只在创建它的会话存活时生效。需要长期运行的话，必须：
- 保持至少一个交互会话在线（配合 daemon）
- 或使用 `claude --resume` 恢复该会话

> [!warning] 更正（2026-09-13）：没有 `/cron` 这个斜杠命令，触发规则也需补全
> 上面用例写的 `/cron 7 */2 * * * …` 不是官方命令（官方命令表中**没有 `/cron`**，该页全文无 cron 字样）。底层是 **`CronCreate` / `CronList` / `CronDelete`** 三个工具；用户侧既可用自然语言排程，也可用 **`/loop`**（bundled skill）。
> 原文「只在创建它的会话存活时生效」**不完整**，官方规则如下：
> - 任务只在 **Claude Code 运行且空闲**时触发；
> - **新开对话会清空全部会话级任务**，但 `--resume` / `--continue` 会**恢复** `CronCreate` 建的任务（已过期的 recurring 与已过时的一次性任务除外；自定步长的 `/loop` **不恢复**）；
> - recurring 任务 **7 天后过期**、最后一次触发后自删；单会话最多 **50 个**任务；
> - 存在**确定性 jitter**：recurring 可晚至 **30 分钟或半个间隔**，整点/半点的一次性任务最多**提前 90 秒** ⇒ 原文 `13 9 * * 1-5` 这类写法是对的，但「每 2 小时」的实际触发会漂移。
>
> 来源：<https://code.claude.com/docs/en/scheduled-tasks.md> · <https://code.claude.com/docs/en/commands.md>

### 4.3 /loop — 自主循环

```bash
# 进入交互会话
claude --permission-mode accept-edits

# 固定间隔模式
/loop 15m 检查 gomoku 仓库的 CI 状态，如果有失败的测试就修复它们

# 自适应模式（Claude 自己决定检查频率）
/loop 监控 /root/workspace 中所有仓库，发现新 issue 时通知我
```

### 4.4 claude -p — 一次性脚本

```bash
# 在 Termux 的 crontab 或 job scheduler 中使用
claude -p "检查所有仓库状态，提交并推送未提交的更改" --permission-mode accept-edits

# 链式调用
claude -p "更新 gomoku 依赖" --permission-mode accept-edits && \
claude -p "运行 gomoku 测试套件" --permission-mode accept-edits
```

### 4.5 官方的无人值守调度对照（2026-09-13 补）

原文把「无人值守」等同于「保住一个本地会话 + 会话内 cron」，遗漏了官方为无人值守提供的云侧与原生长驻方案：

| 方案 | 运行位置 | 机器可关机 | 最短间隔 | 备注 |
|---|---|---|---|---|
| Cloud Routines | 云端 | ✅ | 1 小时 | 不依赖本机在线 |
| Desktop scheduled tasks | 本机 | ❌ | 1 分钟 | 不限会话、**可访问本地文件** |
| `/loop` | 会话内 | ❌ | 1 分钟 | 需开着会话 |
| `CronCreate`（本文 §4.2） | 会话内 | ❌ | — | 会话存活且空闲才触发 |

需要由**外部事件**驱动而非轮询时用 **Channels**（把 CI 失败等事件直接推进会话）。§十「CronCreate 只在会话存活时生效」这一真正的痛点，在这张表里有官方答案——不必只靠 Termux 侧 `while` 循环硬撑。

来源：<https://code.claude.com/docs/en/scheduled-tasks.md>

---

## 五、Android 进程存活保障

### 5.1 问题

Android 的电源管理会杀死后台进程，Termux 也不例外。即使有 wake-lock，系统也可能在内存压力下杀掉进程。

### 5.2 多层防护

**第1层：Termux wake-lock**
```bash
# 获取 CPU 唤醒锁（防止深度休眠）
/data/data/com.termux/files/usr/bin/termux-wake-lock

# 释放（仅在需要时）
/data/data/com.termux/files/usr/bin/termux-wake-unlock
```

**第2层：Termux 后台服务**
在 Termux 侧（非 PRoot）创建 `~/.termux/boot/` 或 `~/.termux/tasker/` 脚本：
```bash
#!/data/data/com.termux/files/usr/bin/bash
# ~/.termux/boot/start-claude-daemon.sh
termux-wake-lock
proot-distro login ubuntu -- bash -c 'claude --resume --permission-mode accept-edits'
```

**第3层：Daemon 自动恢复**
- Claude daemon 在检测到二进制变更后会自动重启（日志已证实）
- 如果 daemon 被 kill，下次任何 `claude` 命令都会自动拉起新 daemon

**第4层：定期心跳**
```bash
# 在 Termux 侧设置 Termux job scheduler（需要 Termux:API）
# 或简单地在 Termux 侧写 while 循环
while true; do
  # 注: ANTHROPIC_BASE_URL 指向 DeepSeek 兼容端点时，模型名用 deepseek-chat（原 claude-haiku-4-5 为 Anthropic 模型名）
  proot-distro login ubuntu -- bash -c 'claude -p "ping" --model deepseek-chat --permission-mode bypass'
  sleep 300
done
```

> [!warning] 更正（2026-09-13）：心跳示例不应使用 `--permission-mode bypass`
> 上面示例的 `--permission-mode bypass`（原表述）与 §十 局限表「`--permission-mode bypass` 过于宽松，应始终配置 deny 清单」**属同一文档内先禁止再示范**。可用替代：
> - 心跳这类**只读探测**用 `--allowedTools` 限定到最小集合；
> - 或用 `claude -p --bare`（官方 permissions 文档确认 `--bare` **不读 hooks/skills/自定义命令/子代理/插件**，启动更快也少副作用）；
> - 确需免打扰时用 **`dontAsk`**（只放行预先批准的工具），而非 `bypassPermissions`。
>
> 局限表也应给出「什么情况才允许 `bypassPermissions`」的明确判据（建议限定为：一次性、可丢弃的沙箱，且不在生产凭据可达范围内）。
> 来源：<https://code.claude.com/docs/en/permission-modes.md> · <https://code.claude.com/docs/en/permissions.md>

### 5.3 Android 电池优化

1. 在 Android 设置中，将 Termux 设为"不优化"（电池优化白名单）
2. 在 Termux 通知栏中保持前台通知（防止被判定为后台无意义进程）
3. 如果使用 Termux:Float 插件，可以保持常驻通知

---

## 六、通知机制

### 6.1 PushNotification 工具

Claude 内置的 `PushNotification` 工具可以在任务完成或异常时推送通知：

```
# 任务中指示 Claude 在完成时通知
帮我完成 gomoku 的 Python 3.7 兼容性修复，完成后用 PushNotification 通知我

# 监控任务
/loop 30m 检查 CI 状态。如果发现失败，立即用 PushNotification 通知并尝试修复。
如果全部通过，每 2 小时通知一次状态。
```

### 6.2 通知分级

| 级别 | 触发条件 | 通知方式 |
|------|----------|----------|
| 🔴 紧急 | 测试失败、构建中断、服务宕机 | PushNotification 立即 |
| 🟡 警告 | 依赖过期、代码冲突、性能下降 | PushNotification + session 内记录 |
| 🟢 信息 | 任务完成、定时报告 | session 内记录，不推送 |

### 6.3 缺少 Termux:API 的情况

当前环境没有安装 Termux:API（`termux-notification` 不可用），这意味着：
- **Claude 的 PushNotification 走的是 Claude Code 的推送通道**，不依赖 Termux:API
- 如果手机端安装了 Claude Code 配套的 Remote Control，推送会到达手机
- 否则仅在终端桌面通知中显示

---

## 七、完整无人值守场景与操作流程

### 场景A：让 Claude 自主开发一个功能

```bash
# 1. 获取 wake-lock
/data/data/com.termux/files/usr/bin/termux-wake-lock

# 2. 启动一次性自主任务
claude -p "
完成 gomoku 项目的以下任务：
1. 分析当前代码结构
2. 添加 AI 难度选择功能（easy/medium/hard）
3. 编写对应的单元测试
4. 运行完整测试套件，确保全部通过
5. 提交代码并推送
6. 完成后用 PushNotification 通知
" --permission-mode accept-edits --output-format stream-json

# 3. 用户可以断开终端，Claude 自己执行完
```

### 场景B：长期自主监控 + 维护

```bash
# 终端1：启动交互会话
claude --permission-mode accept-edits

# 会话内设置：
/loop 15m 检查以下仓库的 git status：
- /root/workspace/gomoku
- /root/workspace/pyc_decompiler
- /root/workspace/weekly_summary_for_my_girl

如果有未提交的更改或需要合并的 PR，自动处理。
每 2 小时汇总一次状态。
/cron 3 22 * * * 生成今日工作总结，写入 /root/workspace/daily-report.md
```

### 场景C：手机端远程控制

```bash
# 通过 Termux 的 SSH 或 Remote Control 连接
ssh user@android-ip
# 或使用 Termux 的 termux-open 等工具

# 检查状态
claude --resume  # 恢复之前的会话

# 查看历史
cat /root/.claude/history.jsonl | tail -50

# 查看定时任务
cat /root/.claude/scheduled_tasks.json
```

---

## 八、安全边界与风险控制

### 8.1 硬性 deny 规则

无论什么权限模式，这些操作必须被阻止：

```json
{
  "permissions": {
    "deny": [
      "Bash(rm -rf /:*)",
      "Bash(rm -rf /root:*)",
      "Bash(rm -rf ~:*)",
      "Bash(git push --force:*)",
      "Bash(claude update:*)",
      "Bash(npm uninstall @anthropic-ai/claude-code:*)",
      "Bash(dd if=*of=*)",
      "Bash(shutdown:*)",
      "Bash(reboot:*)",
      "Bash(chmod 777 /:*)",
      "Bash(curl * | sh:*)",
      "Bash(wget * -O - | sh:*)"
    ]
  }
}
```

### 8.2 销毁开关（Kill Switch）

如果无人值守任务失控，最快的终止方式：

```bash
# 从 Termux 侧杀掉 Ubuntu PRoot 内的 Claude 进程
proot-distro login ubuntu -- bash -c 'killall -9 claude'

# 或者杀掉整个 PRoot session
pkill -f "proot.*ubuntu"

# 释放 wake-lock
termux-wake-unlock
```

### 8.3 日志追踪

所有无人值守操作的痕迹：
- `/root/.claude/history.jsonl` — 完整对话历史
- `/root/.claude/daemon.log` — daemon 事件日志
- `/root/.claude/telemetry/` — 遥测数据
- Session 文件 — 每个 session 的 JSONL 记录

---

## 九、当前环境的快速实施清单

按优先级排列：

- [ ] **P0** — 获取 termux-wake-lock，防止 Android 杀进程
- [ ] **P0** — 优化 `settings.local.json`，添加通用 allow + 硬性 deny 规则
- [ ] **P1** — 确认 daemon 稳定运行（`ps -p 21625`，或重启 daemon）
- [ ] **P1** — 在 Termux 侧设置电池优化白名单
- [ ] **P1** — 为 `weekly_summary_for_my_girl` 仓库设置自动提交推送的定时任务
- [ ] **P2** — 测试 `claude -p` 一次性任务是否能完整执行无需人工介入
- [ ] **P2** — 配置 PushNotification 验证通知可达
- [ ] **P3** — 在 Termux 侧设置 boot 脚本（开机自启 daemon）
- [ ] **P3** — 安装 Termux:API 以获取更丰富的通知能力
- [ ] **P3** — 将 `settings.local.json` 的现有细粒度规则精简合并

---

## 十、已知局限与缓解

| 局限 | 缓解 |
|------|------|
| CronCreate 任务只在创建它的会话存活时生效 | 保持至少一个 daemon-backed session；或用外部Termux脚本模拟 cron |
| `claude -p` 无状态，每次都是新对话 | 将上下文写入文件（如 CLAUDE.md 或 task context），任务启动时读取 |
| Android 极端内存压力下即使 wake-lock 也可能被杀 | 配置 Termux 前台通知；降低 claude 并发模型级别 |
| `--permission-mode bypass` 过于宽松 | 始终配置 deny 清单；定期审查 settings.local.json |
| 双 npm 体系可能因错误升级而破坏 claude | 在 deny 中加入 npm uninstall 规则；每次升级前人工确认 |
| 无 Termux:API 导致无法使用 Android 原生通知 | Claude 的 PushNotification 走独立通道；或安装 Termux:API |

---

## 附录：环境速查表

```
Daemon PID:     21625
Claude binary:  /usr/lib/node_modules/@anthropic-ai/claude-code/bin/claude  (Linux aarch64 无 .exe，原记 claude.exe 有误)
Claude version: 2.1.172
Active sessions: 27780, 29097, 30349, 2990
Settings:        /root/.claude/settings.json + settings.local.json
Wake-lock:       /data/data/com.termux/files/usr/bin/termux-wake-lock
Platform:        Android aarch64 → Termux → PRoot → Ubuntu 24.04
```

> [!note] 上表读法（2026-09-13）
> 该速查表的 `Daemon PID`、`Active sessions` 均为**示例值，勿当现状**；`Claude version: 2.1.172` 为撰写时基线（当前已至 v2.1.270 系列，见文首更正）。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 全文按 v2.1.172 设计，实际落后近百个补丁版本 | 保留原值并标注「撰写时基线 / 机制依赖 ≥2.1.217」，补 `/subtask` v2.1.212+ 与并发上限 v2.1.217+（changelog / sub-agents 官方页） |
| 纠错 | allow 规则写成 `Bash(git:*)` 形式，实际不会被前缀匹配 | 保留原清单并加更正：allow 用工具自身 specifier 语法、`*` 置子命令之后、无 `*` 需完全相等、字面前缀可被 `git -C . push` 绕过（permissions 官方页） |
| 纠错 | 权限模式只列三种，遗漏无人值守首选的 `auto` | 保留原表并补六种模式：`auto`（classifier 逐条审）、`dontAsk`、`acceptEdits` 实际放行范围、关键路径删除由 CLI 无条件拒绝（permission-modes 官方页） |
| 纠错 | 用 `/cron` 教用户建任务，且只写「会话存活才生效」 | 更正为 `CronCreate`/`CronList`/`CronDelete` + `/loop`，补全触发/清空/恢复/7 天过期/50 上限/jitter 五条规则（scheduled-tasks、commands 官方页） |
| 纠错 | 会话文件写成 `~/.claude/sessions/*.json`，`history.jsonl` 当「完整对话历史」 | 更正为 `~/.claude/projects/<project>/<session-id>.jsonl` 与恢复三件套；`history.jsonl` 改标本机观察（sessions 官方页） |
| 纠错 | 把 daemon 的 `daemon.status.json`/`supervisorPid` 当判活依据 | 降级为本机观察，改以「后台会话 + agent view」为官方路径（48 小时断点续跑规则；agent-view 官方页） |
| 纠错 | 心跳示例用 `--permission-mode bypass`，与 §十 局限表自相矛盾 | 保留原示例并给替代：`--allowedTools` 最小集合 / `claude -p --bare` / `dontAsk`，并要求补「何时才允许 bypassPermissions」判据（permissions 官方页） |
| 补疏漏 | 全篇把无人值守等同于「本地会话 + 会话内 cron」 | 新增 §4.5 官方调度对照表（Cloud Routines / Desktop scheduled tasks / `/loop` / `CronCreate`）+ Channels 事件驱动（scheduled-tasks 官方页） |

回链：[[CORRECTIONS]] · [[AGENTS]]
