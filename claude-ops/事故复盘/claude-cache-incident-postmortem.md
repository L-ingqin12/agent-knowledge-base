---
title: 缓存优化事故复盘
aliases: []
tags: [ai/ops, incident]
created: 2026-06-16
updated: 2026-09-13
status: stable
---

# 缓存优化事故复盘

See also: [[Claude-Ops-KB-Home]] · [[claude-cache-postmortem-2026-06-13]] · [[claude-cache-optimization]]

> 日期: 2026-06-16 | 影响: 多次会话中断 | 根因: permafrost 代码补丁 + 反复重启 + 竞态条件

---

## 一、时间线

| 时间 | 事件 |
|------|------|
| 06-13 | 方案 B 应急部署，permafrost 原版运行，命中率 85%-97% |
| 06-16 | CC 自动升级 v2.1.177，新增 WebSearch/WebFetch 工具，锚点分裂 |
| 06-16 | 切入 v2.1.177 后命中率降至 70%（Pro）44%（Flash） |
|  | 开始尝试 permafrost 代码补丁修复 |
|  | → currentDate 稳定化补丁（第一次重启） |
|  | → normalize_tools 工具集重排补丁（第二次重启） |
|  | → normalize_tools 反复调整（第三、四次重启） |
|  | 每次重启 permafrost 导致会话中断 |
|  | 补丁加载后引入 Python .pyc 缓存问题 |
|  | 部署脚本端口竞态条件导致 L1 逃生失败 |
|  | 用户手动回滚至直连 DeepSeek |
| 06-16 | 最终回退：clean permafrost + v2.1.174 + 直连 DeepSeek |

> [!warning] 更正（2026-09-13）：`06-16 CC 自动升级 v2.1.177` 一条混了两个事实（原表述把「版本出现」与「升级发生」写在同一行）
> - **版本时间可复算**：npm per-version 元数据的 `_npmOperationalInternal.tmp` 时间戳——2.1.177 → 1781312661577 ms = **2026-06-13 01:03:58Z**，2.1.174 → 1781216871895 ms = 2026-06-11 22:27:52Z。故 `06-16` 只能是**自动升级发生的时间**，不是版本发布时间，两者不能混写。
> - **「新增 WebSearch/WebFetch 工具」仍未证实**：官方 changelog 页本次抓取超时（30 s），无法确认条目留存范围，该半句维持「未证实」，需另找可引用出处。
> 来源：https://registry.npmjs.org/@anthropic-ai/claude-code/2.1.177 ｜ https://registry.npmjs.org/@anthropic-ai/claude-code/2.1.174

> [!warning] 补疏漏（2026-09-13）：85%-97%（06-13）与 70% / 44%（06-16）并列，却没标口径
> 两处命中率必须写清是 **permafrost 自报**还是**上游 usage**：[[claude-cache-postmortem-2026-06-13]] §2.2 明写「permafrost 侧显示 97%+ 命中率，但 DeepSeek 后台低得多」。DeepSeek 官方只定义了唯一可比口径的两个字段：`prompt_cache_hit_tokens` 与 `prompt_cache_miss_tokens`。
> 处置：命中率统一用上游 usage 字段计算并按 session 分段记录，permafrost 自报值另列一栏；否则「97% → 70%」支撑不了「版本升级影响命中率」这个核心论断。
> 来源：https://api-docs.deepseek.com/guides/kv_cache

## 二、根因分析

### 直接原因

1. **反复重启 permafrost** — 每次 `kill` + 重新启动导致 2-5s 停机窗口，CC 连接中断
2. **Python .pyc 缓存** — 修改 `.py` 源文件后未清除 `__pycache__/`，旧字节码继续运行
3. **部署脚本端口竞态** — `kill` 后立即 `bind` 同一端口，`Address already in use`

> [!warning] 更正（2026-09-13）：`.pyc` 这条只在边界条件下成立（原表述为「修改 `.py` 源文件后未清除 `__pycache__/`，旧字节码继续运行」）
> Python 官方 `py_compile` 文档逐字：TIMESTAMP 模式下 *The .pyc file includes the timestamp and size of the source file, which Python will compare against the metadata of the source file at runtime to determine if the .pyc file needs to be regenerated.*；只有 `UNCHECKED_HASH` 模式才完全不校验（默认失效模式实为 TIMESTAMP，除非设置了 `SOURCE_DATE_EPOCH`，此时默认 CHECKED_HASH）。
> 故「改了源码还继续跑旧字节码」需要边界条件：mtime 与 size 都没变（保留 mtime 的写回、同一秒内等长改写），或部署用了 `UNCHECKED_HASH`。
> 判据与处置：`stat -c '%Y %s' 源文件` 与 `.pyc` 头部记录对照；部署脚本清 `__pycache__/` 或设 `PYTHONDONTWRITEBYTECODE=1`。§五 教训 5 / §六 措施 5 按此收紧。
> 来源：https://docs.python.org/3/library/py_compile.html

### 深层原因

4. **测试与生产未隔离** — 补丁直接在生产的 `permafrost_align.py` 上修改，无独立测试环境
5. **缺少回滚门禁** — 每次改动前未先保存工作版本的完整快照
6. **反复修改同一文件** — 多次编辑导致文件状态混乱，最终无法确定哪个版本在运行

## 三、影响评估

| 维度 | 影响 |
|------|------|
| 会话可用性 | 多次中断（每次 permafrost 重启），用户需手动恢复 |
| 缓存命中率 | 从 97% → 70% → 恢复到 95%（补丁曾奏效） |
| 运维复杂度 | 配置被多次改写，hook 膨胀，需手动清理 |
| 用户时间 | ~3 小时排查 + 回退 |

## 四、哪些改动保留了，哪些回退了

### 保留

| 项目 | 说明 |
|------|------|
| 方案 C 架构 | permafrost → proxy → DeepSeek ✅ |
| 四级逃生通道 | L1-L4 rollback 脚本 ✅（06-17 后扩充补丁级 L0m/L0a/L0b，完整梯队七级）|
| 版本切换器 | `claude-version-switch.sh` ✅ |
| 缓存监控 | `claude-cache-monitor.sh` ✅ |
| 部署脚本端口修复 | deploy.sh 端口等待改为轮询 ✅ |

### 回退

| 项目 | 说明 |
|------|------|
| currentDate 稳定化补丁 | `stabilize_current_date()` — 已删除 |
| 工具集重排补丁 | `normalize_tools()` / `_ANCHOR_TOOLS` — 已删除 |
| permafrost_align.py | 重新从 npm 安装原版 |
| 所有自定义 hook | settings.local.json 恢复最简 |

> [!warning] 补疏漏（2026-09-13）：「重新从 npm 安装原版」缺三要素，无法回溯（原表述即上表该行）
> 「原版」指向哪个包的哪个版本无从确认——缺**包名、版本、安装后哈希**；本库另一篇把 permafrost 写作 `~/.claude/plugins/cache/permafrost/.../permafrost_align.py` 形式的插件缓存，故必须先写清是全局 npm 包还是插件缓存。对照 [[proxy-cancelretry-hook-incident]] §六「受控版本 md5 一致已回退」至少留了哈希。
> 应补：`npm ls -g`（或插件清单）中的包名 + 版本、安装命令、安装后 `sha256sum`，并用 permafrost doctor 输出回证。

## 五、经验教训

1. **永远不要在 permafrost 源码上直接改** — 用补丁目录 + 隔离测试，通过后再部署
2. **改配置不动代码** — 90% 的问题可以通过 URL/ENV/version 配置解决，不应触及源码
3. **重启前先验证** — 修改后先在隔离端口（:8789）测试，通过后切换上游
4. **保存工作快照** — 每次改动前 `cp` 备份原文件
5. **Python 修改后必清 .pyc** — 新增 `rm -rf __pycache__/` 到部署脚本
6. **生产操作需确认** — 涉及进程 kill 的操作先确认，不自动执行
7. **尊重"如果没坏就别修"原则** — 97% 命中率已经足够好，追加优化收益递减

## 六、改进措施

1. permafrost 补丁 → 独立测试端口 :8789 验证 → 确认后切换上游（不重启）
2. 部署脚本已加入端口等待轮询（修复竞态）
3. 源码备份到 `patches/` 目录
4. CC 版本锁定 + 自动更新禁用

> [!warning] 补疏漏（2026-09-13）：版本锁定只有结论，没有键名、命令与验收判据（原表述即上一行）
> 官方 settings 文档的配置优先级（与本文所述一致）：managed settings > command line（`claude --settings`）> project local（`.claude/settings.local.json`）> shared project（`.claude/settings.json`）> user（`~/.claude/settings.json`）。
> 应补：① 锁定值放在哪一层、该层可用的键或环境变量与示例值（以官方 settings / env-vars 页为准）；② 验收——连续 N 天 `claude --version` 不变、升级只能人工触发；③ 例外与回滚，以及锁定过久导致工具 / 模型不匹配的信号。
> 来源：https://code.claude.com/docs/en/settings.md

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | §一「06-16 CC 自动升级 v2.1.177，新增 WebSearch/WebFetch 工具」 | 保留原表述并加更正：npm 元数据可复算 2.1.177 发布于 2026-06-13 01:03:58Z，故 06-16 是升级发生时间；「新增 WebSearch/WebFetch」因官方 changelog 抓取超时仍标未证实 |
| 纠错 | §二 直接原因 2「改 `.py` 后未清 `__pycache__/` → 旧字节码继续运行」 | 保留原表述并加更正：TIMESTAMP 模式会比对 mtime + size，仅边界条件（mtime/size 未变或 UNCHECKED_HASH）成立；补 `stat -c '%Y %s'` 判据与 `PYTHONDONTWRITEBYTECODE=1` |
| 补疏漏 | §一/§三 85%-97% 与 70%/44% 并列但未标口径 | 补口径要求：统一用上游 `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`，permafrost 自报值另列（姊妹篇记两者差距很大） |
| 补疏漏 | §四「重新从 npm 安装原版」缺包名 / 版本 / 哈希 | 补三要素要求与 `npm ls -g`、安装后 `sha256sum`、permafrost doctor 回证；对照 [[proxy-cancelretry-hook-incident]] 的 md5 做法 |
| 加厚 | §六 措施 4「CC 版本锁定 + 自动更新禁用」只有 12 字 | 补官方 settings 优先级链、锁定层级与键位待核项、连续 N 天 `claude --version` 不变的验收、例外与回滚 |

依据与索引：[[CORRECTIONS]] · [[AGENTS]]
