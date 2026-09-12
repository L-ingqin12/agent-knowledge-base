---
title: SESSION-ARCHIVE 2026-09-12
aliases: [会话归档 2026-09-12, DSH会话脱敏归档, dsh-redaction归档]
tags: [meta, session-archive, ai/tools, incident]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# 会话归档 — 2026-09-12：DSH 会话日志脱敏（预防 + 修复两个插件）与平台研究

See also: [[HOME]] | [[AGENTS]] | [[AI-Links-KB-Home]] | [[CORRECTIONS]] | [[DSH插件组合与启动中止语义]] | [[DSH会话日志格式与读取端约束]] | [[DSH会话持久化与活跃改写安全]] | [[DSH-TUI内部机制与键盘卡死陷阱]] | [[DSH会话脱敏插件缺陷档案]] | [[DSH会话脱敏项目方法论复盘]]

> [!abstract] 主题
> **起因**：一次公开检索 / 一条 `gh` 命令 / 一次日志抓取，返回的内容里有你不该留存的东西。在 DSH 里它不只是"经过"——**落盘的 `tool/result` 事件本身就是面向模型的那条消息**，一次写入同时提交给持久化会话日志与之后每一轮 provider 请求。撞上服务端内容风控（`Content Exists Risk`）时，失败的不只是那一轮，而是此后每一轮（历史一直带着它）。
> **做法**：两个可分发插件（事前预防 + 事后修复）+ 一套把 DSH 读穿的实测研究（会话日志格式、持久化写路径、工具结果管线、TUI 扩展面）。
> **产出**：公开仓库 `dsh-redaction`（MIT，2 个包）+ 6 篇笔记 + [[CORRECTIONS]] 新增 C-005~C-012（其中 C-012 是首次推送 GitHub Actions CI 之后追加的）。

## 一、要求与交付

| 要求 | 交付 | 落点 |
|---|---|---|
| 内容不再进入（预防） | `dsh-plugin-content-policy` **0.2.0**：规则与结构剥离挂在 `tools/execute` waterfall 上，在结果落盘**之前**改写结果 **`value`**——于是渲染文本与持久化的 `meta` 一起被清 | `packages/dsh-plugin-content-policy/` |
| 已经落盘的字节抹掉（修复） | `dsh-plugin-redact` **0.1.0**：原地脱敏 / 按轮回退既有 `session.vN.jsonl.zstd`，帧级引擎同时是 `dsh-redact` 离线 CLI；含会话内 `hide`、`rollback`、`undo` | `packages/dsh-plugin-redact/` |
| 能被别人复现 | 原始证据：`docs/reports/{redteam,fix,dialog-root-cause,dialog-contract,boot-verify}` + `surveys-existing-plugins.zh.md`；设计稿归档在 `docs/design-notes/` | 同仓库 |
| 能在本机真的用上 | 两份本地工作副本 `%USERPROFILE%\dsh-plugin-redact`、`%USERPROFILE%\dsh-plugin-content-policy`，以 `link:` 依赖装进 `dsh-tui` profile，并进 `bundles`（复核 `~/.dsh/profiles/dsh-tui/package.json`） | 本机 profile |
| 知识沉淀 | 6 篇新笔记 + 6 处既有文档回写（MOC / HOME / 两篇 DSH 手册 / `AGENTS.md` / `CORRECTIONS.md`）；首次推送 CI 之后再补三处：[[CORRECTIONS]] C-012、[[DSH会话脱敏插件缺陷档案]] 第七类 D-20–D-22、[[DSH会话脱敏项目方法论复盘]] §2.6 与 §六·五 | 本库 |

**两个包是刻意分开的**：预防救不了已经在盘上的东西，修复也管不了下一条检索结果。

## 二、工程时间线（成功与失败一并记）

**主线**：`/redact` 命令面（`list|nodes|pick|scan|hide|plan|apply|verify|purge|rollback|undo`）→ 自测全绿 → **独立红队对抗审查**（F1–F10 + 一条元发现）→ 逐条修复并用**真实读取端**当判据 → 启动路径扫描（boot-verify）→ 打包发布准备。

### 2.1 失败的十处（按发生顺序）

| # | 失败 | 机制 | 处置 |
|---|---|---|---|
| 1 | 先把「删中间行」当成安全能力写进文档与流程 | 读取端逐行断言 `event.seq === eventCount`（`seq` 必须等于 0-based 行号）。**删掉中间任意一行 = 整份日志判损坏 = 会话根本打不开**，不是"少一行" | 删除降级为补充手段：安全面只有**原地改写**（行数/`seq` 全不变）与**后缀删除**；删中间行必须显式 `renumber` 并重映射引用 → [[CORRECTIONS#C-005 拿工具自检当读取端验收]] |
| 2 | 命令结果按多行排版设计，**做了两轮才去读渲染端** | dsh-tui 不直接显示 handler 的 `text`：先过 `cleanRenderText(text, 200)`——把 `[\x00-\x1f\x7f-\x9f]`（含 `\n`/`\t`）全换成空格、连续空白压成一个，再按 **200 显示格**截断补 `…`（CJK 算 2 格）。多行必成一行，超长必砍尾 | 两轮排版作废，全部推倒：单行 + ` · ` 分隔 + 最重要信息在最前；插件自己实现同规则 `clamp(s, 200)` 先用 `clampResult()` 包住 handler → [[CORRECTIONS#C-006 假设渲染行为而不读渲染端]] |
| 3 | 残帧默认丢弃——**比读取端更狠的数据丢失** | 引擎把整段未写完的尾部帧丢掉；真实读取端会用 `ZSTD_e_flush` 解出残帧前缀、保留其中**完整行**再重写。工具在这里比读者更具破坏性 | 改成按 zstd block（128 KiB 解码）粒度恢复并报告条数。实测：6000 行 / 795 KB 的尾帧截到 72% → **恢复 2973 行**（原先整段丢）。新增 `test/torn-recovery.mjs`（11 条）随包发布并进 `npm test` |
| 4 | 引擎 `die()` 里 `process.exit(1)`，而它在**宿主进程内**执行 | 这是离线 CLI 的写法，被插件 handler 复用：计划里一处非法删行 → `/redact plan` **直接把整个 agent 应用杀掉**，用户失去的是整段会话界面 | `die()` 改抛 `RedactError`；插件层 `try/catch` 转成普通的 `未执行：<原因>`，CLI 由 `main()` 顶层转 stderr + 退出码 1（对外行为不变）。回归守卫：`bugfix-regression` BUG-1/BUG-1b/BUG-2 + `handler.selftest.mjs` 的 `process.exit` 安全网 |
| 5 | 插件文件里缺一个 `async` = 解析期 `SyntaxError` | 加载器解析模块在启动关键路径上，解析失败与 `import()` 抛错**同级**：文件在解析期就死，`apply` 根本没机会跑 → 整个 profile 起不来 | 补 `async`；更重要的是立流程守卫——`boot-verify` 用 SHA-256 把整轮扫描**包夹**在被测修订之间，前后哈希一致才承认结果（"这个结论属于哪一版字节"钉死） |
| 6 | 空 YAML `config:` 传进 `null`，直接中止启动 | YAML 空键解析成 **`null`**（不是 `undefined`）。旧校验把"非对象"一律当错误 → `apply()` 抛错 → 启动器把未激活/抛错的行升级为**致命错误** | `config = {}` + `null`/`undefined` 一并视同 `{}`；20 格配置边界矩阵里 `omitted`/`{}`/`null`/`{bogus:1}` 四格必须 `BOOT_OK`（实测 `redactNoConfig` / `redactNullConfig` 均 `BOOT_OK`，`redactBadShape` 仍 `BOOT_ABORTED`） |
| 7 | `/redact pick` 的模态对话框**锁死 TUI 键盘** | promise 停在 `TuiDialogStore` 里 → `Chat.js:2566` 无条件让出聊天键盘、`PromptInput` 变 `isActive:false`（光标还在闪但打字没反应）；而面板**唯一**的挂载点被 approval 面板无提示压掉，approval 又**没有超时**。`Ctrl+C` 也退不出（`exitOnCtrlC: false`） | 面板路径**默认关闭**（`allowDialogs: false`）——不是保守，是根因结论；改两段式 `/redact nodes` 看编号 → `/redact hide <序号> --commit`，**结构上不可能冻结**。唯一无条件自救是等超时（实测 15011 / 15026 ms）→ [[CORRECTIONS#C-009 把服务存在外推为效果出现]] |
| 8 | 隐私开关 `argsCells: 0` 反而留下了痕迹 | 截断函数 `clamp(s, 0)` 循环第一步就 `break`，返回 `'' + '…'`——「完全不显示命令行」变成"留一个 `…` 占位符" | `clamp` 对 `budget <= 0` 短路返回 `''`；套件加"不留占位符"断言 → [[CORRECTIONS#C-011 只测常规值不测边界]] |
| 9 | **自伤回归**：profile 补丁行漏写 `allowDialogs: true` | patch 命中的行是**整个 config 被替换**（不是深合并），不写这一项就落回默认 `false`，那行 `inject: [commands, tuiDialogs]` 等于白加——**刚确认可用的面板被自己悄悄关掉** | 已改正：`~/.dsh/profiles/dsh-tui/cordis.patch.yml:33-41` 现含 `allowDialogs: true` 及"必须显式写出来"的注释（本归档写作时复核）。⚠️ 笔记 [[DSH-TUI内部机制与键盘卡死陷阱]] §8.2 仍写着"没有 `allowDialogs: true`"——**那句已过期** |
| 10 | **首次推送 CI 37 秒红**：随包发布的测试里写着 Windows 专有假设 | `packages/dsh-plugin-redact/test/preflight.mjs` 用 `process.env.USERPROFILE` 推导 DSH 主目录；这个变量**只存在于 Windows**，在 `ubuntu-latest` 上是 `undefined` → `path.join(undefined, '.dsh')` 抛 `ERR_INVALID_ARG_TYPE`（**不是断言失败，是套件起不来**）。同批另两处同类：`new URL(import.meta.url).pathname`（2 个文件，路径含空格/中文时残留 `%20`）、同名 `engine.selftest.mjs` **两份拷贝分叉**（部署那份有夹具清理、仓库那份没有 → 每跑一次测试就在源码目录留下 `broken.zstd`、`needle.txt`、`plan-*.json`） | `os.homedir()` 取代平台专有环境变量、`fileURLToPath` 取代 `.pathname`、清理块补回仓库副本、`.gitignore` 兜底；新增 `.github/scripts/portability.mjs` 静态守卫（四条规则）+ 可证伪自检 `portability.selftest.mjs`（把真实缺陷注入回 `preflight.mjs`，断言守卫退出码 1 且指对文件与行号，`finally` 恢复）。**严重性**：该文件在 `files` 白名单里 ⇒ 任何 Linux/macOS 消费者的 `npm test` 都会炸，是发布物缺陷而非 CI 配置问题 → [[CORRECTIONS#C-012 拿本机绿测当跨平台验收]] |

### 2.2 红队与修复的账（数据丢失级）

> [!bug] 红队结论摘要
> 5 个「数据丢失 / 不可逆损坏」级缺陷，**其中 2 个会让会话永久打不开，而工具全程报告成功**。两条最狠的：`sourceEventSeqs` 的**盘上游程形式**（`[[a,b]]`）没有被重映射 → 读取端 `range exceeds its event seq` 硬拒；`session/title.data.messageSeqs` 不在引用清单里 → 重编号后悬空（不报错时更坏：静默指向另一轮对话）。另外 `undo` 会把**未校验**的隔离备份覆盖到健康日志上（截断备份被当崩溃尾 → 静默丢事件）。

修复后的实测（判据一律是**真实** `JsonlSessionPersistence.open()` / 真实 `Session` / 真实 title 不变式，不用引擎自检）：

| 指标 | before | after |
|---|---|---|
| F1 游程引用 | 输出 `sourceEventSeqs=[[2,4]]`，后端**打不开** | 输出 `[[1,3]]`，后端 **7 events 正常打开** |
| F2 title 引用 | 真实不变式报 `message seq 2 must name an earlier human user/message` | `messageSeqs=[1]`，不变式**通过** |
| F3 坏备份装回 | 静默丢事件（`ok=true events=3`）/ 会话硬损坏 | **拒绝恢复**，当前日志零改动、仍可打开 |
| F7 病态开销 | `applyPlan` 4511 ms / 峰值 RSS 589.8 MB / 1001 帧 2420 ms / 30 万行 `RangeError` | **2033 ms / 417.6 MB / 490 ms / 1979 ms 完成** |

### 2.3 元发现（和修复本身一样重要）

**旧的绿测试证明不了任何事**：`bugfix-regression.mjs` 的夹具不是读取端合法日志（把 `tool/result` 写成 `role:'tool'`，真实形状是 `role:'user'` + `source:{kind:'tool',callId}`），于是 F1/F2 两类缺陷从 241 条全绿里溜了过去。处置：新增 `test/real-reader.mjs`（真实 `Session` + 真实编解码器 + 真实后端 + 真实 title 不变式），夹具本身**必须先被真实后端打开**才算数 → [[CORRECTIONS#C-008 拿绿色测试当可用性证据]]。

## 三、已解决 / 未解决

### 3.1 已解决 ✅

- 红队 F1–F10 逐条修复，并有 before/after 存档（`%USERPROFILE%\dsh-redact-fix\{baseline,after}\`）；总闸 `verifyLog` 把「读取端会拒绝的输出」挡在写盘之前，`applyPlan` 自检、`verify` 子命令、`undo` 的备份校验**复用同一份实现**
- 三条杀进程路径（D-06 引擎 `process.exit` / D-07 语法错误 / D-08 空 `config:`）全部闭合，且都有断言或流程守卫
- 键盘卡死有结构性替代（两段式命令 + 序号快照校验），模态路径默认关闭
- 隐私开关、`--session` 被静默忽略、"报成功而正文未变"等误导类缺陷闭合（D-10~D-12）
- 卫生类 D-16~D-19：作者绝对路径、跑不了却 `exit 0`、缺 `LICENSE`、无 `test` 脚本
- **可移植性类 D-20~D-22（首次推送 CI 后新增）**：随包发布的 `preflight.mjs` 里的 Windows 专有假设、`import.meta.url` 配 `.pathname`、同名两份拷贝分叉——三处全部修复，并落地 `.github/scripts/portability.mjs` 静态守卫 + 可证伪自检
- **CI 从"没推上去"变成"跑起来且全绿"**：`.github/workflows/ci.yml` 随首次推送入库，在 GitHub Actions 上真实执行；首跑 37 秒红（见 §2.1 第 10 条），修复后推送前在 WSL2 里 **1:1 复现 `ubuntu-latest` 全部步骤 7/7 绿**，Windows 侧 9/9 套件全绿（复现方法见 §5.4）
- 公开仓库两次提交 `1a440d9`（两包 + 研究）+ `3cbf0a5`（残帧恢复 + 证据脚本去个人路径）

### 3.2 未解决 ⚠️

1. ~~**CI 工作流没能推上去**：`gh` token 缺 `workflow` 作用域。复核结论：已发布仓库里 `.github/workflows/` 是**空目录**，`ci.yml` 从未被 git 跟踪（`git ls-files .github` 为空）——而笔记与 README 里已经在引用 `.github/workflows/ci.yml:16 / :32-44 / :46-47`。**下次推送前先补这一条，否则文档引用的是不存在的文件。**~~ → **已解决**（`ci.yml` 已入库并真的跑起来。而且它**第一次跑就红了**——见 §2.1 第 10 条：当初担心的"文档引用了不存在的文件"，变成了"那个文件替我们抓到了发布物缺陷"。文档里引用的行号现已指向真实文件。）
2. **模态对话框路径仍默认关闭**：机制还在（`allowDialogs: true` + 行级 `inject: [commands, tuiDialogs]` 可开），approval 挂起时仍会锁键盘；而且那层 `inject` 在没有 `tuiDialogs` 提供者的 profile 上会让该行永远 PENDING → 整个 profile 起不来。
3. **live 原地写入的 syscall 内部仍有残余窗口**：`write(2)` 对大 buffer 不是原子的，"写到一半进程死"仍会留下「新前缀 + 旧尾巴」。彻底关掉要独占写句柄/锁或改名安装，超出本轮最小修复范围。
4. **`undo` 在日志本身缺失时无法恢复**：源码注释曾承诺"日志缺失也允许恢复"，实现做不到（F8 未修，注释与实现不一致）。
5. **两个包都还没发布到 npm**，目前只以 `link:` 装进本机 `dsh-tui` profile。
6. ~~**笔记缺口**：`DSH工具结果管线与meta陷阱` 被三处链接但文件不存在~~ → **已解决**（本会话末补写完成，259 行，已登记进 [[AI-Links-KB-Home]] 文档地图，悬空 wikilink 已消除）。
7. ~~引擎 / CLI 那份 34 条套件只在本地开发树，未随仓库发布~~ → **已解决**（提交 `dcf5c93`：`test/engine.selftest.mjs` 随包发布、纳入 `npm test` 与 CI，且套件自己清理夹具不留残留）。⚠️ **但"不留残留"只对部署那一份成立**：随后发现仓库那份**没有夹具清理块**（部署那份有），每跑一次测试仍在源码目录留下 `broken.zstd` / `needle.txt` / `plan-*.json`——同一文件两份拷贝悄悄分叉，见 §2.1 第 10 条与 [[DSH会话脱敏插件缺陷档案]] D-22。
8. **`dsh-tui` profile 里那两个包仍是 `link:` 依赖**，指向本地工作副本而非已发布版本；改包后需重启 profile 才加载新模块（行级配置是热重载，模块内容不是）。

## 四、被撤回的结论（本会话写入 [[CORRECTIONS]] C-005~C-012）

| 条目 | 被撤回的结论 | 事实 |
|---|---|---|
| [[CORRECTIONS#C-005 拿工具自检当读取端验收]] | "删行是安全的通用能力——自检（JSON 可解析/头部合法/`seq` 密集）过了日志就是好的" | 判据必须是**对方自己的校验**；`seq === 行号-1` 写在读取端，自检清单只覆盖工具自己关心的性质 |
| [[CORRECTIONS#C-006 假设渲染行为而不读渲染端]] | "字符串里写 `\n`，用户就会看到多行" | **输出格式是消费端的属性**：渲染端先压平（控制字节→空格）再按 200 显示格截断 |
| [[CORRECTIONS#C-007 拿配置组合当运行时证明]] | "`dsh --profile <name> --dump-config` 里出现 `id: dsh-redact` ⇒ 插件能加载、命令能注册" | `--dump-config` **从不 import 插件模块**：插一行不存在的包名，dump 照样打出该行、进程照样退出码 0；要证明插件真的起来，判据是启动后的行状态（ACTIVE）与它注册出的命令 |
| [[CORRECTIONS#C-008 拿绿色测试当可用性证据]] | "三套自测 241 条全绿 ⇒ 工具工作正常、输出能被打开" | **测试可信度上限 = 夹具与真实产物的同形度**；夹具 `role:'tool'` 被真实后端一句 `message must have role "user"` 拒掉，F1/F2 正住在这个盲区 |
| [[CORRECTIONS#C-009 把服务存在外推为效果出现]] | "`ctx.get('tuiDialogs')` 有值 ⇒ 面板会弹" | **服务存在 ≠ 效果可达**：准入守卫（`bindOwnerEffect` 失败即立刻以取消结清）+ 挂载点优先级（`approvalPanelNode` 无提示压掉对话框）+ 键盘归属，三道独立闸门任一关闭效果就不存在 |
| [[CORRECTIONS#C-010 把配置字段当作稳定值]] | "`disabled` 是个布尔字段，写个 `!!js` 判据就能让两种 profile 自动二选一" | `Entry.disabled` 是**实时 getter**，判据随挂载进度翻转（提供者排在后面时），启动器把未激活/PENDING 升级为致命错误 → **整个 boot 中止**。要二选一就用**静态的两层** |
| [[CORRECTIONS#C-011 只测常规值不测边界]] | "预算设成 `0` 就等于这个字段不存在" | 只按常规值验收 = 没验收；`clamp(s, 0)` 返回 `'' + '…'`，**"关闭"档必须单独测，判据落在成品上**（产物里到底有没有那个字符） |
| [[CORRECTIONS#C-012 拿本机绿测当跨平台验收]] | "本机 9 套全绿 ⇒ 交付物在任何平台都跑得起来；CI 只是把本机做过的事再做一遍" | **平台专有假设在写它的平台上隐形**：`USERPROFILE` 只存在于 Windows，CI 首跑 37 秒就红；该文件随包发布 ⇒ 陌生人 `npm test` 必炸。判据是「**在目标平台上跑过**」，不是「本机跑过」 |

> [!note] 同步改动：[[AGENTS]] §六·五
> 本会话新增 [[AGENTS]] §六·五（错误记忆协议：出结论前回查 [[CORRECTIONS]] 速查索引）。该节把记录数口径写成 **11 条、同一根源的两个变体**——C-001~C-004 把**外部信息**当结论，C-005~C-011 把**自己这一侧的通过**当**对方的验收**（自检通过 / 假设渲染 / 配置组合当运行时 / 绿测试当可用性 / 服务当效果 / 配置字段当稳定值 / 只测常规值）。本库同日早些时候建库时只有 C-001~C-004 四条。
>
> **后续口径（首次推送 CI 之后）**：追加 [[CORRECTIONS#C-012 拿本机绿测当跨平台验收]] 后，C-012 归入**第二个变体**（"自己这一侧的通过 = 对方的验收"从"读取端"扩展到了"目标平台"）；同日另一条工作线（[[repo-merge-2026-09-12]]）又补了 C-013 / C-014，因此 [[AGENTS]] §六·五 里那句「4 条记录」的旧口径已同步改为当前的 **14 条**。

## 五、可复用产物

### 5.1 跑自测（**必须显式用 Node ≥ 22.15**）

> [!warning] PATH 上的 `node` 常常太旧
> 本机 `node --version` → **v18.16.1**；zstd API 从 **22.15** 才有，旧解释器会让几乎每个脚本以**误导性的方式**失败（`zstdDecompressSync` 是 `undefined`）。本机可用的 22.x 在 `%USERPROFILE%\nodejs-x64\node-v22.21.0-win-x64\node.exe`（实测 v22.21.0）。

```powershell
$node = "$env:USERPROFILE\nodejs-x64\node-v22.21.0-win-x64\node.exe"
& $node --version                                   # 先确认 >= 22.15

# dsh-plugin-redact（在 packages/dsh-plugin-redact 里）
& $node test/handler.selftest.mjs     # 248/248
& $node test/bugfix-regression.mjs    # 54/54   （判据=真实 JsonlSessionPersistence.open()）
& $node test/hardening.mjs            # 78/78   （真实读取端 + 真实 title 不变式）
& $node test/torn-recovery.mjs        # 11/11
& $node test/preflight.mjs            # 冒烟，无断言，只打印观察

# content-policy（在 packages/dsh-plugin-content-policy 里）
& $node test/selftest.mjs ; & $node test/harness.mjs
& $node test/registry-e2e.mjs ; & $node test/config-schemastery.mjs

# 引擎 / CLI（34/34）—— 只在本地开发树，不在仓库里
& $node "$env:USERPROFILE\session-surgery\selftest.mjs"
```

| 套件 | 断言 |
|---|---|
| `handler.selftest.mjs` | **248** |
| `bugfix-regression.mjs` | **54** |
| `hardening.mjs` | **78** |
| 引擎 / CLI（`session-surgery/selftest.mjs`） | **34** |
| `torn-recovery.mjs` | **11** |
| content-policy 四套 | **103**（45 + 36 + 17 + 5：纯逻辑 / 假 ctx / 真注册表 / 双轨 Config） |

两个约束：需要 **Node ≥ 22.15**；依赖真实 DSH 的套件（`hardening`、`bugfix-regression`、`real-reader`）找不到 `@deepseek-ai/*` 时**抛错而不是跳过**（判据不能降级），可用 `DSH_REDACT_DSH_LIB` 指路。`handler.selftest.mjs` 会打印**被测文件字节数 + sha256 前 12 位**，报告里每个数字都能对到具体一版字节。

### 5.2 发布（注意 registry）

> [!warning] 本机 npm 指向镜像
> `npm config get registry` → **`https://registry.npmmirror.com/`**。镜像不承接发布，命令里**必须显式写官方 registry**（`--access public` 只解决 scoped 包的可见性，不解决发到哪）。

```powershell
# 先打包预览，确认没漏文件、也没把夹具/plan.json/needle.txt 带进去
npm pack --dry-run     # 实测 dsh-plugin-redact@0.1.0：11 文件 / 137.0 kB；content-policy@0.2.0：10 文件 / 61.9 kB

npm login --registry=https://registry.npmjs.org/
npm publish --registry=https://registry.npmjs.org/                    # 无 scope 包
npm publish --registry=https://registry.npmjs.org/ --access public    # scoped 包首次必须显式公开
```

发布**不是必需的**：官方支持 npm 包 / tarball / git 依赖三条路；走 git 分发时 pnpm ≥10 会拒绝执行依赖的 `prepare`，需把 key 抄进 profile 的 `pnpm-workspace.yaml` 的 `allowBuilds` 再重试。消费者侧安装：

```powershell
dsh plugin --profile <name> add ./dsh-plugin-redact
dsh plugin --profile <name> add ./dsh-plugin-content-policy
dsh --profile <name> --dump-config     # 只证明配置组合，不证明加载（见 C-007）
```

### 5.3 证据与现场

| 路径 | 是什么 |
|---|---|
| `%USERPROFILE%\dsh-redaction\docs\reports\redteam\` | 对抗审查：F1–F10、复现脚本 `p1`–`p8`、reader-as-oracle 判定 |
| `…\docs\reports\fix\` | 修复报告 + 每条 finding 的 before/after 输出 + 套件实跑 |
| `…\docs\reports\dialog-root-cause\` | 键盘锁死的三段机制、死锁态矩阵、无 TTY 复现脚本 |
| `…\docs\reports\boot-verify\` | 真实 `boot()` 扫描、20 格配置矩阵、双轨 `Config` 对比、`--dump-config` 不 import 模块的实测 |
| `%USERPROFILE%\dsh-redact-redteam\` | 红队复现脚本原件（务必**串行**跑：共用 `%TEMP%\rt-redact\root`） |
| `%USERPROFILE%\dsh-redact-fix\` | before/after 存档、`run-all.ps1` |
| `%USERPROFILE%\session-surgery\` | 引擎 / CLI 套件与 `zsplice.mjs`（与 `lib/engine.mjs` 逐字节相同的孪生件） |

### 5.4 在本地 1:1 复现 `ubuntu-latest`（WSL2 + 官方 Linux Node）

> [!warning] 本机是 Windows，"CI 红不红"以前只有推上去才知道
> 首次 CI 首跑 **37 秒红**（§2.1 第 10 条）之后补的流程：**平台专有假设在写它的平台上隐形**，所以必须在**目标平台**上跑一次。不需要 Docker，也不需要第二台机器——本机已有 Debian 与 Ubuntu 两个 WSL2 发行版。

```sh
# 1) 装一份官方 Linux Node（解到 /opt；发行版仓库里的版本通常 < 22.15，缺 zlib 的 zstd API）
curl -LO https://nodejs.org/dist/v22.21.0/node-v22.21.0-linux-x64.tar.xz
sudo tar -xf node-v22.21.0-linux-x64.tar.xz -C /opt
export PATH=/opt/node-v22.21.0-linux-x64/bin:$PATH
node --version        # 必须 >= 22.15，否则会把"版本不足"误诊成"日志损坏"（D-13）

# 2) 在仓库根，按 .github/workflows/ci.yml 的步骤顺序逐步执行
#    （依赖安装 → 两个包的 npm test → .github/scripts/portability.mjs 与它的自检）
```

| 侧 | 本次实测（推送前） |
|---|---|
| WSL2（Linux，与 CI 同平台） | 按 `ci.yml` 顺序 **7/7 步全绿** |
| Windows | **9/9 套件全绿**（Node 22.21.0） |

这样"推上去看 CI 红不红"就变成了"**推之前本地就能确认**"：CI 不再是第一道验证，而是最后一道确认。

## 六、下次注意

1. **改「别人要读的文件」时，判据去读对方的校验代码**，不要用自己的自检清单——说不出 `文件:行号` 就是没验证过（C-005）。
2. **面向 UI 的输出先读消费端**：找到那个压平/截断的函数与常量，再决定排版（C-006）。
3. **`--dump-config` 不是加载证明**；证明插件起来了，看行状态（ACTIVE）与它注册出的命令（C-007）。
4. **夹具形状决定断言的意义**：改别人产物时至少留一条「真实消费者能打开输出」的断言（C-008）。
5. **UI 效果要按「服务 → 准入 → 挂载点 → 键盘归属」逐道闸门验**，或者直接换成结构上不可能失败的路径（C-009）。
6. **配置里能求值的东西都要问「何时求值、求值几次」**；要条件化就用静态的两层，不要用运行时判据（C-010）。
7. **凡「设 0/空/false 即关闭」的开关，单独测边界值，判据落在成品字符上**（C-011）。
8. **一次改动后必须做一次启动自检**（插件在共享启动路径上，单行错误 = 整个 profile 用不了）；扫描用修订号包夹，别拿两次不同字节的结果对比。
9. **不可再生数据（会话日志）的工具，红队审查的投入产出比极高**——一次审查换来"数据丢失类缺陷归零 + 78 条真实读取端回归"。
10. **别让写盘成功之后的旁枝异常污染成功路径**：`purgeCache` 抛 `EISDIR` 曾把一次**已经成功的改写**报成失败（"命令炸了"），而磁盘上原文已经没了、还多出一份含原文的隔离备份。成功的操作必须有一个不会被旁枝异常改写结论的返回路径。
11. **推送前在目标平台跑一遍**（WSL2 + 官方 Linux Node 即可 1:1 复现 `ubuntu-latest`，见 §5.4）——**本机全绿不构成跨平台证据**：平台专有假设在写它的平台上隐形（C-012）。
12. **静态守卫必须能失败**：把 `USERPROFILE`/`HOMEDRIVE`/`APPDATA`/`LOCALAPPDATA`、`import.meta.url` 配 `.pathname`、硬编码盘符、`path.win32` 这类写法做成守卫，并配一个"**把真实缺陷注入回去**"的自检（断言它红、并指对文件与行号）。写完再问一遍：「什么样的缺陷能从我的规则里穿过去？」——第一版守卫恰恰放过了它要抓的那一行（`??` 判在整行而不是变量本身）。

## Related

[[DSH会话脱敏插件缺陷档案]] · [[DSH会话脱敏项目方法论复盘]] · [[DSH插件组合与启动中止语义]] · [[DSH会话日志格式与读取端约束]] · [[DSH会话持久化与活跃改写安全]] · [[DSH-TUI内部机制与键盘卡死陷阱]] · [[DSH-TUI插件使用手册]] · [[DSH插件与Hook开发最佳实践]] · [[DSH提效与Token插件调研]] · [[CORRECTIONS]] · [[AGENTS]] · [[HOME]] · [[AI-Links-KB-Home]] · [[SESSION-ARCHIVE-2026-08-30]]
