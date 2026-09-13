---
title: Permafrost 补丁丢失事故复盘
aliases: []
tags: [ai/ops, incident]
created: 2026-06-17
updated: 2026-09-13
status: stable
---

# Permafrost 补丁丢失事故复盘

See also: [[Claude-Ops-KB-Home]] · [[PERMAFROST_MODIFICATIONS]] · [[claude-cache-incident-postmortem]]

> 日期: 2026-06-17 | 影响: permafrost 重启后补丁丢失，缓存优化失效

---

## 一、事故经过

1. 在 permafrost 源码上通过 Python 字符串替换打补丁
2. 多次替换导致缩进错误 → 语法错误
3. 执行 `cp .orig → permafrost_align.py` 恢复 → **.orig 是干净原版，补丁全部清零**
4. 后续 re-apply 补丁成功，但 .orig 未更新
5. Session 重启 → permafrost 加载了某次恢复操作后的原版代码
6. 生产 permafrost doctor 显示所有补丁字段缺失

## 二、根因

```
直接原因: .orig 备份是原版，恢复操作等于撤销补丁
深层原因: 
  - 字符串替换打补丁不可靠（缩进/转义容易出错）
  - 补丁权威版本未集中管理（磁盘、repo、内存三处不一致）
  - deploy.sh 不验证补丁是否生效
  - .orig 没有在补丁成功后更新
```

## 三、修复措施

| 措施 | 说明 |
|------|------|
| .orig 更新 | 补丁生效后 `cp patched → .orig` |
| deploy.sh 自检 | 启动时自动检测补丁，缺失则从 repo 恢复 |
| repo patches/ | 权威补丁文件，单一真相来源 |
| 记录文档 | PERMAFROST_MODIFICATIONS.md 完整记录每处修改 |

> [!warning] 更正（2026-09-13）：把 `.orig` 覆盖成补丁版，与 `.orig` 的既定语义正相反（原表述为「.orig 更新｜补丁生效后 `cp patched → .orig`」）
> `patch(1)` 手册逐字：`-b`/`--backup` 是 *Make backup files. That is, when patching a file, rename or copy the original instead of removing it.*；不给 `-B`/`-Y`/`-z` 时 *a simple backup suffix is used; it is the value of the SIMPLE_BACKUP_SUFFIX environment variable if set, and is `.orig` otherwise.*——即 `.orig` 的约定含义是「**未被改动的原版**」。本文把它更新为补丁版后，§一 的恢复路径（`cp .orig → permafrost_align.py`）恢复出的是**补丁版**，与「恢复 = 回到干净基线」的预期相反（§四 教训 2 是刻意这么定的，不是笔误，但需要显式命名区分）。
> 建议：`.orig` 保留原版语义；补丁产物交给版本控制或独立命名（`.patched` / `patches/` + sha256 清单），并写清「哪个是可恢复基线、哪个是当前生产版本」。
> 来源：https://man7.org/linux/man-pages/man1/patch.1.html

> [!warning] 补疏漏（2026-09-13）：§三 四条措施都没有命令、断言或输出示例，等于不可验证
> 最小自检实现（放进 deploy.sh / 启动自检）：
> ```bash
> # 断言磁盘文件带补丁特征；缺失即非零退出并从 patches/ 恢复
> if ! grep -q 'stabilize_current_date' permafrost_align.py \
>    || ! grep -q 'date_stabilized: 1' permafrost_align.py \
>    || ! grep -q 'normalize_tools' permafrost_align.py; then
>   echo "PATCH-MISSING: permafrost_align.py 缺少 currentDate/tools 补丁特征" >&2
>   cp patches/permafrost_align.py.patched permafrost_align.py && exit 1
> fi
> echo "PATCH-OK $(sha256sum permafrost_align.py | cut -c1-12)"
> ```
> 判据：正常输出 `PATCH-OK <哈希前12位>` 且退出 0；缺补丁输出 `PATCH-MISSING …` 并以非零码退出。**否证式验收**：手工删掉一处补丁特征后，自检必须以非零码失败并指名文件——否则自检不算生效（同族教训见 [[CORRECTIONS]] C-007「拿配置组合当运行时证明」、C-020「把命令退出 0 当成副作用已生效」）。

## 四、教训

1. **不要用字符串替换打补丁** — 用完整文件备份替代
2. **每次修改后更新 .orig** — 确保恢复操作指向最新工作版本
3. **部署前验证磁盘状态** — 不仅看运行中的 permafrost，也看磁盘文件
4. **单点真相来源** — repo patches/ 是唯一权威版本

> [!warning] 补疏漏（2026-09-13）：§四 教训 1「用完整文件备份替代字符串替换」与 §三「repo patches/ 是权威补丁文件」是两种策略，文中没说最终用哪条
> | 策略 | 优点 | 代价 |
> |------|------|------|
> | 完整文件替换 | 简单、幂等、可直接 sha256 断言 | 与上游版本强绑定，上游一升级就要重做 |
> | diff 补丁（`patches/`） | 可审计改动、体积小 | 依赖上下文行，上游一改就 fuzz，需要记录基准版本 |
> | 直接改上游插件目录内文件 | 无 | 无追踪、无回滚——本次事故就是这么来的 |
> 应在文中写明本文选哪条；若选 diff，必须记录原始版本号与哈希，且应用后 `diff` 输出只应含预期 hunk。

## 五、当前状态（2026-06-17）

- 磁盘补丁 ✅ currentDate + tools 重排
- 生产运行 ✅ 96%+ 命中率
- deploy.sh 自检 ✅ 自动恢复
- .orig 备份 ✅ 已更新为补丁版本
- 逃生通道 ✅ 完整梯队七级（补丁级 L0m/L0a/L0b + 结构级 L1-L4，定义见 claude-permafrost-rollback.sh）

> [!warning] 更正（2026-09-13）：§五 五项全部 ✅ 缺数据口径，且与姊妹篇时间线冲突（原表述即上列五项，均为 ✅）
> - **口径缺失**：「生产运行 ✅ 96%+ 命中率」未写是 permafrost 自报的 `/permafrost/stats`，还是上游 usage 的 `prompt_cache_hit_tokens`。[[claude-cache-postmortem-2026-06-13]] §2.2 明写「permafrost 侧显示 97%+ 命中率，但 DeepSeek 后台低得多」——两个口径差距很大，不能混用。
> - **时间线冲突**：[[claude-cache-incident-postmortem]]（06-16）§四 已把 `stabilize_current_date()` 与 `normalize_tools()` 列为**已删除**并「重新从 npm 安装原版」；本文（06-17）又写磁盘补丁 ✅。两篇都没有记录「06-16 删除 → 06-17 重新打上」这个反转，需补反转日期并互相回链。

> [!warning] 补疏漏（2026-09-13）：「.orig 备份 ✅ 已更新」没有一致性判据（§二 深层原因正是「磁盘、repo、内存三处不一致」）
> - 判据：`sha256sum permafrost_align.py .orig`（两份各自路径），把两个哈希写进本文——没有哈希就无法判断当前是否一致。
> - 位置 × 角色 × 更新者：
> | 位置 | 角色 | 更新者 |
> |------|------|--------|
> | 磁盘 `.orig` | 可恢复基线 | deploy.sh |
> | 磁盘 `permafrost_align.py` | 当前生产版本 | deploy.sh |
> | repo `patches/` | 权威补丁 | 人工提交 |
> | 内存（运行中的进程） | 实际生效代码 | 重启时从磁盘加载 |
> - 红线：任何恢复操作前先比对哈希，不一致先停下。

> [!warning] 补疏漏（2026-09-13）：「逃生通道 ✅ 七级」只给了脚本名，等于无法判定可用
> | 级别 | 命令参数 | 触发条件 | 回滚后验证 |
> |------|---------|---------|-----------|
> | L0m | `model-off` | model 路由（currentDate 稳定化）出问题 | permafrost doctor 中该字段归零，且 `:8788` 仍在监听 |
> | L0a | `tools-off` | tools 重排出问题 | doctor 中 tools 顺序回到默认，currentDate 补丁仍在 |
> | L0b | `patches-off` | 全部补丁出问题 | 还原 `.orig` 后 doctor 全字段归零，permafrost 仍可服务 |
> | L1 | 默认（无参数） | proxy 故障 | 方案 C→B：`:8788` 直连上游，缓存优化保留 |
> | L2 | `full` | permafrost / proxy 整体故障 | `ANTHROPIC_BASE_URL` 回到官方直连且可用 |
> | L3 | `disable` | auto-deploy 死循环 | 自动部署停止，文件不再被重写 |
> | L4 | `nuke` | 完全清零 | 无残留进程 + 直连可用 |
> 命令参数以 `claude-permafrost-rollback.sh` 的用法行为准（级别清单与 [[claude-cache-postmortem-2026-06-13]] §3.5 的四级定义 + 06-17 扩充说明一致）。

---

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | §三「.orig 更新｜补丁生效后 `cp patched → .orig`」 | 保留原表述并加更正：`patch(1)` 的 `.orig` 语义是「未改动的原版」（`SIMPLE_BACKUP_SUFFIX` 默认 `.orig`），覆盖后 §一 的恢复路径会恢复出补丁版；建议 `.orig` 留原版语义、补丁产物用 `.patched` / `patches/` + sha256 清单 |
| 加厚 | §三 四条措施无命令、断言、输出示例 | 补最小自检实现（grep 补丁特征 → 缺失则非零退出并从 `patches/` 恢复）与正常 / 缺失两种输出，附否证式验收（手工删特征后自检必须失败） |
| 补疏漏 | §四 教训 1（完整文件备份）与 §三 `patches/`（diff 补丁）未说明取舍 | 补三种策略对照表（完整文件 / diff 补丁 / 直接改插件目录）与判据：选 diff 必须记录原始版本号与哈希，应用后 `diff` 只应含预期 hunk |
| 纠错 | §五 五项全 ✅、无数据口径，且与 06-16 姊妹篇时间线冲突 | 保留原表述并加更正：96%+ 未写 permafrost 自报 / 上游 usage 口径（[[claude-cache-postmortem-2026-06-13]] §2.2 记 97%+ vs 后台低得多）；补「06-16 删除 → 06-17 重打」反转说明与互链 |
| 加厚 | §五「.orig 备份 ✅ 已更新」无一致性判据 | 补 sha256 判据与「位置 × 角色 × 更新者」表（磁盘 `.orig` 基线 / 磁盘 `.py` 生产 / `patches/` 权威 / 内存运行中），并加恢复前先比哈希的红线 |
| 加厚 | §五「逃生通道 ✅ 七级（定义见 claude-permafrost-rollback.sh）」只给脚本名 | 补七级表（级别 / 命令参数 / 触发条件 / 回滚后验证），命令以 rollback.sh 用法行为准 |

依据与索引：[[CORRECTIONS]] · [[AGENTS]]
