---
title: DSH 会话脱敏插件缺陷档案
aliases: [修复日志, 数据丢失缺陷, 会话日志损坏]
tags: [ai/tools, incident]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# DSH 会话脱敏插件缺陷档案

See also: [[AI-Links-KB-Home]] | [[DSH插件与Hook开发最佳实践]] | [[DSH-TUI插件使用手册]] | [[DSH会话脱敏项目方法论复盘]] | [[CORRECTIONS]]

> [!abstract] 本文档是什么
> `dsh-plugin-redact`（在 TUI 里**原地改写**已落盘的 DSH 会话日志 `session.vN.jsonl.zstd`）在 v0.1.0 定稿前被查出的全部缺陷，按机制分六类，逐条给出**用户可见症状 / 机制与成因 / 如何被发现 / 如何修复 / 由哪条断言守住**。
>
> 材料来源：红队报告 `docs/reports/redteam/REPORT-zh.md`（F1–F10）、修复报告 `docs/reports/fix/REPORT-FIX-zh.md`、对话框根因与契约核对 `docs/reports/dialog-root-cause/ROOT-CAUSE.zh.md` / `docs/reports/dialog-contract/REPORT.zh.md`、启动扫描 `docs/reports/boot-verify/`、两个包的 README 与 `test/` 套件。所有夹具均为合成日志，未读取任何真实会话内容、缓存或 `*.jsonl.zstd`。
>
> **为什么值得单独立档**：这个工具改的是**不可再生**的数据。它的每一条缺陷都不是"功能不好用"，而是"用户以为抹干净了 / 以为还能打开，实际相反"。同类工具的缺陷清单就是安全模型的一部分。

> [!danger] 一句话结论
> 定稿前存在 **5 个数据丢失/损坏级**缺陷，其中 2 个会让会话**永久打不开**，而工具**全程报告成功**（红队报告首行结论）。这些缺陷之所以能活到红队介入，是因为仓库里的 159 条断言用的夹具**根本不是读取端合法日志**——这一条本身是缺陷 0，详见 [[DSH会话脱敏项目方法论复盘]]。

---

## 0. 分类总览

| 类 | 缺陷 id | 暴露方式 | 后果 |
|---|---|---|---|
| 一、会话日志损坏 | D-01 D-02 D-03 D-04 D-05 | 读取端拒绝 / 静默丢事件 | 数据丢失、会话打不开 |
| 二、杀进程 | D-06 D-07 D-08 | 宿主进程退出 / profile 启动中止 | 整个应用不可用 |
| 三、界面锁死 | D-09 | 键盘无响应，只能等超时 | 交互不可用 |
| 四、输出误导 | D-10 D-11 D-12 D-13 | 报告与实际不符 | 决策错误、隐私泄漏 |
| 五、分页与识别 | D-14 D-15 | 目标不可达 / 认不出目标 | 功能不可用 |
| 六、工程卫生 | D-16 D-17 D-18 D-19 | 外人跑不起来 / 静默变绿 | 交付物不可复现 |

红队编号 F1–F10 与本档编号不是一一对应：本档还含作者自查与启动扫描查出的缺陷（D-07、D-08、D-10、D-11、D-12、D-16–D-19）。凡来自红队的条目在正文里标出 F 编号。

---

## 一、会话日志损坏类

共同点：**工具报告成功、磁盘字节确实变了、DSH 打不开或静默少读**。判据只能是真实读取端 `JsonlSessionPersistence.open()` 与真实 `dsh-session-title` 不变式——工具自己的自检看不见这类问题。

### D-01 游程形态的 `sourceEventSeqs` 没有被重映射（F1）

> [!danger] 数据丢失 · 不可逆 —— 症状：`/redact apply <plan.json>`（计划带 `renumber: true` 且删中间行）打印"已就地脱敏"，但该会话**从此永久打不开**（resume 第一步 `persistence.open` 就抛错）。唯一救援是手工用 `.quarantine-*` 覆盖回去。

**机制与成因 → 如何被发现。** 旧实现只做 `row.sourceEventSeqs.map(map)`，`map` 对非整数**原样返回**，悬空检查 `dropped.has(v+1)` 对区间元素也永远不触发（`:46-47`）；而盘上格式不是内存格式——读取端读时用 `decodeSeqRanges(record.sourceEventSeqs, seq)`、写时用 `encodeSeqRanges()`，后者把 **≥3 个连续 seq 压成 `[start,end]` 对**（`docs/reports/redteam/REPORT-zh.md:43-45`）。于是区间里的 seq 停留在旧编号上，解码端 `end >= maxEntries` 直接抛 `SessionFormatError: sourceEventSeqs range exceeds its event seq`（`:48-50`）。自然生产者是 `compaction/summary` 遮蔽一段连续 surface 节点——那种行的 `sourceEventSeqs` 天然是长游程，**必被压缩**（`:52`）。红队用真实编解码器 + 真实后端写复现脚本：先证明夹具改写前 DSH 打得开（8 events），再让引擎接受删除、让引擎自检通过，最后用真实后端打开输出——失败（`:57-67`）。关键动作是**把"DSH 打得开吗"当成独立判据**，而不是问工具自己。

**如何修复。** `remapRefs` 改成**形态感知**（`packages/dsh-plugin-redact/lib/engine.mjs:571`、`:599-624`）：全整数→逐项 `map`（保持整数形态）；含 `[start,end]`→**展开成每一个 seq**、逐个 `map`，再用与读取端写入路径同一份 `encodeSeqRanges` 重新压缩；其它任何形状（长度≠2 的数组、字符串、负数、非安全整数、超长区间）一律 `die()` 拒绝。同时补总闸：`applyPlan` 写盘前用 `verifyLog` **按读取端语义回放**输出（`lib/engine.mjs:337`、`:663`）。

**由哪条断言守住。** `test/hardening.mjs` F1 组 8 条（游程重映射成 `[[1,3]]`、真实后端可打开、区间中间被删则拒绝、非法形态被拒）；总闸另有 7 条一票否决断言（游程超界/重复引用/seq 缺口/头部非法/`surfaceOp` 端点不更早/title 引用非人类 user/message/合法日志放行）。

### D-02 `session/title.data.messageSeqs` 不在引用清单里，重编号后悬空（F2）

> [!danger] 数据丢失 · 可静默错指 —— 症状：装了 title 插件的组合里该会话无法恢复；若指针恰好落在另一条 `user/message` 上，则**静默引用错消息**（标题来源被悄悄换成另一轮对话，全程无报错）。

**机制与成因。** 旧实现只处理 `data.shadowedSeqs` / `data.shadowedRange`，漏了 `data.messageSeqs`——它是**持久化的 seq 引用**，真实不变式在 `sessions.list()` / `session/created` 时逐条校验"`message seq N must name an earlier human user/message`"（`REPORT-zh.md:78-81`）。根因是"需要重映射的字段"没有权威清单，作者按记忆列了几个。

**如何被发现 → 如何修复。** 同一个 `p1-refs.mjs` 的 (b) 段：改写后 title 行仍是 `messageSeqs=[2]`，真实 title 不变式拒绝（`:82-88`）。修复：建立**显式引用清单** `REF_PATHS`（`lib/engine.mjs:137-147`），来源是读取端自己唯一权威的那份映射（`dsh-session-format-v2-to-v3` 的 `remapEvent()`）：`surfaceOp.startSeq/endSeq`、`sourceEventSeqs`、`data.shadowedSeqs`、`data.shadowedRange.start/end`、**`data.messageSeqs`**、**`data.sourceEventSeq`**（`command/done`，红队清单里没写但读取端确实要搬）以及行自身的 `seq`。并新增**失败关闭审计** `auditRefFields`（`lib/engine.mjs:225`）：递归扫描每一个会被重编号的行，凡键名以 `seq`/`seqs` 结尾却不在清单里的字段→`die()` 并报出完整路径。注意红队给的正则 `/(^|_)(seq|seqs)$/i` 对驼峰**完全无效**（`messageSeqs`/`shadowedSeqs`/`sourceEventSeq`/`sourceEventSeqs` 一个都匹配不到），审计会形同虚设，所以实现用的是等价加强版（`lib/engine.mjs:151`、`REPORT-FIX-zh.md:105-107`）。

**由哪条断言守住。** `hardening.mjs` F2 组 7 条："`messageSeqs` 被重映射（2 → 1）"、"引用落在 user/message"、"**真实 `dsh-session-title` 不变式接受改写后的日志**"、"清单外的 `*Seq` 字段被失败关闭"（用 `data.somePluginSeq` 触发）、"`data.sourceEventSeq` 也被重映射"。

> [!warning] 这条修复有一个"比裸读取端更严"的取舍 —— `JsonlSessionPersistence.open()` 本身不看 title 的 `messageSeqs`（该不变式由 title 插件执行）。因此**在不装 title 插件的组合里**，一条本来就违反不变式的 title 行会让 `applyPlan` 拒绝执行。取舍理由：放过它意味着在装 title 的组合里整个会话恢复失败；拒绝时错误点名行号与原因，用户仍可改用 `blankLines`/`substitutions`（`REPORT-FIX-zh.md:349`）。这是全套判定里唯一一处比裸读取端更严。

### D-03 `undo` 不校验隔离备份就覆盖健康日志（F3）

> [!danger] 数据丢失 · 把健康日志换成坏日志 —— 症状：`/redact undo --commit` 打印"已恢复"，实际把一份截断/损坏的备份装了回去。两种坏结局：截断在帧边界附近→读取端当成"崩溃尾"**静默少读若干事件**（`ok=true events=3`，原本 7 条，用户看不出少了什么）；备份中间损坏→会话**硬打不开**。

**机制与成因。** 旧实现只 `statSync` 拿大小、按 mtime 排序取最新，然后 `copyFileSync(found.file, aside)` → `copyFileSync(newest.path, found.file)`，**全程没有帧校验、没有 `seq` 密度检查、没有头部校验**（`REPORT-zh.md:99-101`）。而备份本身可能就是坏的：`index.js:313-314` 先复制后写入，复制失败时半截文件就留在盘上（`:97-98`）。

**如何被发现 → 如何修复。** 红队故意把最新备份截断（`641 → 320` 字节）再执行 `undo`，两条断言"undo 报告成功（没有校验备份）"与"当前日志被坏备份覆盖"都 PASS——即缺陷成立（`:102-112`）。修复：装回之前读出备份字节→`verifyLog` 必须 `ok`；**额外**要求 `tornStart === undefined`（帧边界处的截断不留残帧，却会静默少事件）；再做交叉检查——备份的事件数**不得少于**当前日志（`packages/dsh-plugin-redact/index.js:799-820`）。任何一条不过即 `kind:'error'`，文案含"当前日志未改动（N B）"与"可改用更早的 `.quarantine-*` / `.before-undo-*` 备份手工恢复"，且**不做任何写操作**；安装方式改为"写 `.redact-tmp` → `fsync` → `renameSync`"，失败时清理 tmp（`index.js:821-844`）。

**由哪条断言守住。** `hardening.mjs` F3 组 9 条（截断备份拒绝恢复、拒绝后零改动且真实后端仍能打开、拒绝信息给出替代备份路径、中间损坏备份拒绝、健康备份恢复成功、恢复后逐字节一致）；`bugfix-regression.mjs` 守住 undo 正常路径。

### D-04 live 原地覆盖的写序（`write` → `ftruncate`）会吃掉并发追加的事件（F4）

> [!danger] 数据丢失 · 静默 —— 症状：对**正在运行的会话**执行 `apply --allow-live`，期间后端追加的一批事件被 `ftruncate` **从文件里抹掉**，同时让后端内存偏移与实际文件错位；之后打开会话 `ok=true events=20`——**少了事件，没有任何报错**。另一半：写入中途崩溃留下"新头 + 旧帧"的混合体，读取端在帧魔数处硬拒绝（`invalid frame magic at byte 1254`）。

**机制与成因。** 旧顺序是 `open('r+')` → `writeSync` → **`ftruncateSync(out.length)`** → `fsyncSync`。并发保护只有写入**之前**的一次修订号比对（size:mtimeMs:ctimeMs），之后到 `ftruncate` 之间的追加完全没被看见（`REPORT-zh.md:124-128`）。附带两条代码级缺陷：`fs.writeSync` 的返回值被忽略（短写无法察觉）、idle 路径 `renameSync` 之后没有目录 `fsync`（掉电后目录项可能回滚到改写前，属**泄漏**方向而非丢失方向）。

**如何被发现。** 红队在完全相同的 syscall 序列中间插入一次 `appendFileSync`：写后+追加 = 1337B，`ftruncate(1254)` 之后 = 1254B，追加的 71B 帧消失（`:129-137`）。

**如何修复。** 顺序倒过来（`packages/dsh-plugin-redact/index.js:473-541`、`:446-453`）：输出比原文件短时**先 `ftruncate` 再写**（被打断只可能留下"尾部被截短"的日志，读取端本来就按崩溃尾容忍）；输出更长时**故意不用 `ftruncate` 打头**（那会先把尾部补 0，中断反而制造"完整帧边界 + 0"的硬损坏）。另外：打开 fd 后、写入前**再比一次修订号**；写入用 `writeAllSync` 循环到写完并校验累计字节数；写完要求文件长度**精确等于** `out.length`；最后 `fsync` fd 与目录。

**由哪条断言守住。** `hardening.mjs` F4 组 9 条（用**打补丁注入真实并发事件**的方式驱动真实 handler，而不是手工复刻 syscall）："打开 fd 后被并发追加→中止写入并报错"、"并发追加的事件没有被吃掉（656 → 727，+71）"、"并发追加的帧没有被 ftruncate 吃掉"、"截断后崩溃→文件是旧日志的前缀而不是新旧混合体"、"该状态能被真实后端打开（=可容忍的短尾）"、"文件长度精确等于 out.length"、"改写后真实后端可打开且事件数不变"。

> [!warning] 残留窗口（诚实边界） —— "写入 syscall 本身被打断"（写到一半进程死）仍会留下"新前缀 + 旧尾巴"的混合体：`write(2)` 对大 buffer 不是原子的，任何"原地覆盖"方案都有这个窗口；彻底关掉需要独占写句柄/锁或改名安装，超出本次修复范围（`REPORT-FIX-zh.md:347`）。另外短写循环与长度复查只有代码级保证，没有伪造"内核短写"实测（`:348`）。

### D-05 邻居写入让"合法变短的日志"撞上写后长度闸（F4 附带）

> [!bug] 误导 · 变更已生效但报"失败" —— 症状：`apply --allow-live` 报"写入失败（隔离备份 … 仍含原文）：写入期间日志被并发追加（文件 N 字节 ≠ 预期 M 字节）"，用户以为**什么都没做**；实际改写已经落盘，且多出一份含原文的隔离备份。

**机制与成因。** 修复后的写路径在写完做长度复查：`finalSize !== out.length` 即报错。这条闸本身是对的（它保证"绝不 truncate 掉并发追加的内容"），但它与 F5 是同一类形状的问题：**写盘成功之后才判定失败**，而失败文案只说了后半句，没说"树上的字节已经变了"。触发者可以是任何在写窗口内追加的邻居写入者——会话自身的持久化句柄，或另一个并发的 `dsh-redact` 进程。

**如何被发现。** 修复过程的注入式 F4(b) 用例把它逼出来了（`REPORT-FIX-zh.md:184-186`、`docs/reports/fix/after/hardening.txt` 第 47-50 行）。

**如何修复。** 判定保留，但**文案与语义都写实**：报错里点名"已保留追加内容，但该批次可能与改写后的布局错位"，并点名隔离备份仍含原文（`packages/dsh-plugin-redact/index.js:493-496`、`:543-548`）。与 F6 的 `touched` 判定配合：目标文件已被改动→保留备份并点名；一个字节都没动→删掉刚复制的备份（`index.js:477`、`:525-538`）。

**由哪条断言守住。** `hardening.mjs` 3 条："★ F4(b) 检测到写入期间的并发追加并报错"、"★ F4(b) 报错时点名仍含原文的隔离备份（F6）"、"F4(b) 隔离备份确实在盘上"。

> [!question] 已知未修 —— 报错文案仍以"写入失败"开头，用户要读到中段才知道"改写已生效"。这是 200 显示格预算下的取舍（关键信息必须排在最前），不是遗漏，但下一次改动应把"已生效"提到最前。

---

## 二、杀进程类

共同点：**插件行挂载失败 = 整个 profile 起不来**。DSH 的启动器把"任何一行 FAILED / 永远 PENDING"升级为致命错误，所以插件的 import 面与配置校验是**全局爆炸半径**，不是局部质量问题（扫描证据：`docs/reports/boot-verify/sweep3.txt:13-21`——同一批里 `throwImport`/`throwApply`/`missing`/`pending`/`badConfig`/`badApply`/`dupRules`/`redactBadShape` 全部以 `dsh: plugin tree failed to load` 收场）。

### D-06 引擎的错误路径调用 `process.exit(1)`，任何一次拒绝都杀掉宿主应用

> [!danger] 杀进程 · 最严重的一类 —— 症状：在 TUI 里执行 `/redact plan`（计划里写了非法的删行）→ **整个 agent 应用退出**。用户失去的不只是一条命令，是整段会话界面。

**机制与成因 → 如何被发现。** 引擎 `die()` 的实现是"打印到 stderr + `process.exit(1)`"——这是离线 CLI 的写法，但同一个引擎被插件 handler 在**宿主进程内**调用（该约束如今写在 `docs/reports/boot-verify/frozen/dsh-plugin-redact/lib/engine.mjs:73` 的注释里：**引擎级拒绝必须抛错，因为插件与 CLI 跑在同一个进程里**；旧实现恰恰违反它）。作者自查时暴露，并立成回归套件（`bugfix-regression` 的 BUG-1/BUG-1b/BUG-2 三个用例就是为这条立的）。

**如何修复。** `die()` 改为抛 `RedactError`；插件层 `try/catch` 把它变成普通的 `未执行：<原因>` 错误结果，离线 CLI 由 `main()` 顶层统一转成 stderr + 退出码 1（对外行为不变，`packages/dsh-plugin-redact/README.zh.md:610`）。

**由哪条断言守住。** `handler.selftest.mjs` 的**全局安全网**：整个运行期把 `process.exit` 换成抛异常（`test/handler.selftest.mjs:49-62`），只有这样"被测代码到底有没有调 exit"才可观测（`:188-193`）；"★ 9d 中间行删除被拒绝（抛 `RedactError`，不杀宿主进程）"断言 `exited=false`。`bugfix-regression.mjs` 另有"非法计划只返回错误、进程存活"一组。

### D-07 插件文件里的语法错误（缺一个 `async`）会中止整个启动

> [!danger] 杀进程 · 单行语法错误 = profile 全线不可用 —— 症状：改完插件后启动 TUI，报 `plugin tree failed to load: failed to import loader entry …`，**整个 profile 起不来**——不是"这个插件不可用"，而是"什么都用不了"。

**机制与成因 → 如何被发现 → 如何修复。** 加载器解析模块是启动的关键路径：模块解析失败（`SyntaxError`）与 `import()` 抛错同级。缺失的 `async` 让一个 `await` 落进非 `async` 上下文，文件在**解析期**就失败，`apply` 根本没机会跑；写完直接启动即暴露。修复是补上 `async`；更重要的动作是**把"改文件后必须做一次启动自检"变成流程**——`docs/reports/boot-verify/sweep.mjs` 用 SHA-256 把整轮扫描**包夹**在被测修订之间，只有前后哈希一致才承认结果（`sweep.mjs:19-23`、`:36`），把"这个结论属于哪一版字节"钉死。

**由哪条断言守住。** 启动扫描本身（`probe.mjs` 的 `throwImport` 场景 + `sweep*.txt`），以及 `stable.mjs` 的"整轮修订号不变才算数"重试循环（`docs/reports/boot-verify/stable.mjs:50-65`）。这是**流程守卫**而非断言——代码库里没有"语法错误"的断言，因为没有语法错误的文件才能跑断言。

### D-08 空 YAML `config:` 传进 `null`，直接中止启动

> [!danger] 杀进程 · 一个空键 = profile 全线不可用 —— 症状：在 profile 补丁里写了 `config:` 后面忘填内容（或整段注释掉值），启动报 `dsh-redact: invalid config: …`，**整个 profile 起不来**。

**机制与成因。** YAML 里 `config:` 留空解析成 **`null`**（不是 `undefined`）。旧校验把"非对象"一律当错误，于是 `null` 触发 `throw`；而 `apply()` 里的抛错会被 `dsh-app-boot` 升级为致命错误。**注意这不是"写得不对"**——"留空"在配置语义里应当等于"用默认值"，所有字段都有默认值。

**如何被发现。** 启动扫描的配置边界矩阵（`docs/reports/boot-verify/cfgmatrix.txt`，20 个用例）与逐格复跑的 `stable.txt`。`cfgmatrix.txt:3` 专门标注了 `null (YAML config: left empty)`。

**如何修复。** `apply(ctx, config = {})` 里把 `null` 与 `undefined` 一并视同 `{}`（`packages/dsh-plugin-redact/index.js:559`、`:565-567`），其余校验保持严格：非对象（字符串、数组）拒绝；`root`/`cacheRoot`/`placeholder` 的空串或非字符串拒绝；`argsCells`/`dialogTimeoutMs` 必须是非负整数；`allowDialogs` 必须是布尔（`index.js:571-604`）。未知键只告警不拒绝，理由写在代码注释里：不能让一个手滑的键名打断整个 profile 的启动（`index.js:605-611`）。

**由哪条断言守住。** 配置边界矩阵本身：`stable.txt:8-23` 逐格给出 `BOOT_OK` / `BOOT_ABORTED` 与**逐字错误文案**（如 `dsh-redact: invalid config: $.argsCells must be a non-negative integer`），其中 `cfg omitted / {} / null / {bogus:1}` 四格必须 `BOOT_OK`。`handler.selftest.mjs` 的 config 节另有等价断言（`null`/`undefined`/非对象/空串/未知键/两个数字字段的四类非法值/`allowDialogs` 非布尔）。

> [!tip] 这一类的通用教训 —— 插件是**共享启动路径上的一个节点**：它的 import 面、配置校验、`apply` 的同步部分，任何一处抛错都等于"整个应用起不来"。所以正确的响应是**响亮失败 + 精确报错**（用户一眼知道改哪一行），而不是静默降级——静默降级会把"插件没生效"变成"用户以为脱敏在跑"。

---

## 三、界面锁死类

### D-09 `/redact pick` 让 TUI 键盘被无条件让出，且面板可能永远不挂载

> [!danger] 锁死 · 唯一自救是等超时，`Ctrl+C` 无效 —— 症状：在有 approval 面板挂着时输入 `/redact pick` → **界面完全不可操作**：输入框光标还在闪但打字没反应、`Esc` 无效、`Ctrl+C` 既取消不了也退不出程序。只能干等超时（默认 15 秒，旧默认 120 秒）。

**机制（三部件，缺一不锁）。**

| # | 部件 | 位置 | 作用 |
|---|---|---|---|
| 1 | promise 停在 store 里 | `dsh-adapter/dialogs.js:46-115`、`:164-169` | 插件的 `dialogs.select()` 是一个**永不主动结束**的 promise：只有 `decide`/`cancel`/调用方超时/`AbortSignal`/`settleAll` 能结束它 |
| 2 | 键盘无条件让出 | `screens/Chat.js:2566` | `questionSnapshot !== null \|\| approvalSnapshot !== null \|\| dialogSnapshot !== null → return`，Chat 全局 `useInput` 后续所有键全不处理 |
| 3 | 输入框停用 | `components/PromptInput.js:2456`（`isActive: !suspended`，`suspended` 含 `dialogSnapshot !== null`） | 打字没反应 |

而**面板唯一的挂载点**是 `Chat.js:3585` 的提示槽三元链，且 `approvalPanelNode !== null` 抢在 `ExtensionDialog` 前面——**只要 approval 挂着，插件对话框永远不会挂载，而 store 里的 active 依然存在**（`ROOT-CAUSE.zh.md:42-57`）。ApprovalStore **没有任何超时**（全文 grep 无 `setTimeout`），所以"审批长期挂着"是稳态（`:191`）。`decide`/`cancel` 按 key 校验，没挂载过的面板永远拿不到那个 key——**唯一能解冻的人正是那个没被渲染出来的面板**（`:166`）。渲染/键盘分歧矩阵实测出 **7 个死锁态**（`:186-187`）。

**如何被发现。** 用户实际踩到 → 无 TTY 复现（三个脚本 import 部署里的真模块，`ROOT-CAUSE.zh.md:130-136`）→ 15 秒超时路径实测 `15011 ms / 15026 ms` 结算（`:149`、`:198`）→ 契约核对确认"请求形状完全被接受、服务可达性有保证"（`docs/reports/dialog-contract/REPORT.zh.md:12`）——**即：这不是请求写错了，是机制本身不安全**。

**如何修复（判定表）。**

| 选项 | 结论 |
|---|---|
| 继续用 `dialogs.select` | ❌ 它把"15 秒全局键盘封锁"变成一次正常交互的一部分 |
| 默认禁用（`dialogTimeoutMs: 0`） | ⚠️ 不够：冻结被配置挡住，机制仍在 |
| 缩短超时 | ❌ 不是修复，1 秒和 15 秒都仍是"按什么都没反应" |
| **换机制：把"选择"拆成两次同步命令** | ✅ 已采用 |

落地：`pick` 默认关闭（`allowDialogs` 默认 `false`，`packages/dsh-plugin-redact/index.js:601`），且**关着时连服务都不碰**；默认路径改成 `/redact nodes` 看编号 → `/redact hide <序号> --commit`；`dialogTimeoutMs` 默认 120000 → **15000**（`index.js:592`、`:588-591` 的注释把这笔账写清楚了）；`nodes` 尾部的 `选择 /redact pick · ` 提示只在 `allowDialogs === true` **且** `tuiDialogs` 可用时才出现，免得推荐一条已关掉的路径（`index.js:992-993`）。另外把"面板没弹"与"人真的取消了"分开报：`select` 在 **50ms 内**返回取消被判定为宿主未接纳本行（人按 Esc 不可能这么快），报专门的文案（`index.js:909-912`、`:936-937`）。

**由哪条断言守住。** `handler.selftest.mjs` 的 `pick` 节：`allowDialogs` 默认 `false` 时"拒绝且一次都不调用对话框"、`nodes` 也不推荐 `pick`；打开后覆盖有/无 `tuiDialogs`、`select`/`confirm` 的请求形状、人取消 vs 面板没弹的 <50ms 判据、`dialogTimeoutMs` 自定义与 `0`、无效 id / 非数字 id、抛错、60 条上限、`argsCells=0` 时不给 `description`。契约核对另有：`select` 的 60 个选项/标题/`id: String(n)`/`timeoutMs` 逐条通过真实运行时校验（`REPORT.zh.md:12`）。

> [!bug] 上游建议（本次调查副产品） —— `Chat.js:3585` 让 `approvalPanelNode` 无提示压掉 `ExtensionDialog`，而 `:2566` 已让出键盘 → "active 但不可见、不可应答"。要么渲染对话框、要么拒绝 `ask`，不能两者都不做（`ROOT-CAUSE.zh.md:297`）。这是宿主的形状问题，插件侧只能"别把 promise 停进去"。

---

## 四、输出误导类

### D-10 隐私开关 `argsCells: 0` 留下一串 `…` 占位符

> [!bug] 误导 · 隐私开关名义上关掉了，实际留痕迹 —— 症状：用户把"显示工具调用命令行"的预算设成 `0`（意思是**完全不显示**），清单文件里仍出现 `…`——没有内容，但"这里有一条被截断的命令行"这件事被写进了文件。

**机制与成因。** 截断函数的第一步是循环：`budget <= 0` 时循环立即 `break`，返回 `out + '…'`，即只剩一个省略号。开关的语义是"不显示"，实现却给了"显示一个空壳"。第二个成因在调用侧：`info?.args && argsCells > 0 ? … : ''` 把空命令行写成**空字符串**而不是"字段不存在"，于是下游仍然渲染出占位符。

**如何被发现。** 作者自查（在给 `argsCells` 写三态契约时逐态对照输出）。

**如何修复。** `clamp()` 在 `budget <= 0` 时**短路返回空字符串**，代码注释把踩坑写下来了（`packages/dsh-plugin-redact/index.js:41-52`，尤其 `:42-43`：`argsCells: 0 关不掉命令行就是这个原因`）；调用侧要求"整段省略"而非空串（`index.js:109`），`nodes full` 不留占位符、`pick` 不设 `description`（`README.zh.md:116`、`:325`）。

**由哪条断言守住。** `handler.selftest.mjs` 的 `argsCells` 三态断言："默认 120 → 命令行进 `description`"、"无命令行时不设 `description` 字段（不是空串）"、"超长命令行被截断到预算内"（`cellsOf(truncDesc) <= 10 && endsWith('…')`）、"控制字符被换成空格、空白被压平"、"**`argsCells=0` → `nodes full` 完全不写命令行（也不留占位符）**"。

### D-11 子命令忽略 `--session`，静默显示另一个会话

> [!bug] 误导 · 命令回答的不是你问的问题 —— 症状：`/redact nodes --session <别的会话>` 不报错，而是**照常列出当前会话**的节点。用户以为在看目标会话的清单，实际看的是当前会话——下一步 `hide <序号>` 就会作用在错误的会话上。

**机制与成因。** `nodes` / `hide` / `pick` 读写的是**活会话的内存 surface**，而 `--session` 的通用解析在更早的位置就把目标 id 解析出来了；三个子命令没有为"我不支持跨会话"这件事单独设守卫，于是 flag 被静默忽略。

**如何被发现。** 回归陷阱（G1）：作者在补守卫时发现"拒绝时的输出与不带 flag 时不再相同"才是一条需要断言的回归线（`test/handler.selftest.mjs:1076-1089`）。

**如何修复。** 三个子命令**显式拒绝**别的会话，并说明为什么：`nodes` → `nodes 只能列出当前会话的节点（surface 是活会话的内存状态） · 其它会话请用 /redact apply 处理其日志`（`index.js:960`）；`hide`/`pick` → `… 只作用于当前会话；其它会话请用 /redact apply 重写日志。`（`index.js:879`、`:1052`）。

**由哪条断言守住。** `handler.selftest.mjs`："★ `nodes --session <别的会话>` → `kind:error` 且说明只列当前会话"、"★ `nodes` 拒绝时的输出与不带 flag 不再相同（G1 回归陷阱）"、"`nodes` 被拒绝时零改动"、"`nodes full --session <别的会话>` 同样被拒绝且不写文件"、"`hide --session` 指向别的会话 → `kind:error`"。

### D-12 报"成功"而替换结果与原文**逐字节相同**（F10）

> [!bug] 误导 · 最危险的一句谎 —— 症状：`/redact hide --commit` 打印 `已隐藏 1 个节点 · 下一轮请求起模型不再看到`，实际替换节点的正文与原文**一模一样**——什么都没隐藏，而用户会据此认为"这段内容已经移出模型视野"，不再采取别的措施。

**机制与成因。** 当 `data.message.content` 不是数组（或数组里没有任何 `text` 块）时，构造出的 `nextOuter` 原样保留，但成功分支仍然按"已隐藏 N 个节点"回报。

**如何被发现。** 红队 `p3-hide.mjs` 的 C 段（`REPORT-zh.md:230-234`）。**可达性限制也一并记录**：当前类型 `ToolResultMessage.content` 是必填单元组，所以只有非规范/历史/受损日志才会命中，真实的 `Session.append` 也会拒绝这种消息——故降级为低危（"不该无声成功"，不是数据丢失）。

**如何修复。** 进入替换前先要求 `data.message` 是对象；算出替换后的 `message` 后，若它与原文 `JSON.stringify` **逐字节相同**（`content` 不是数组、或没有任何 `text` 块、或 `JSON.stringify` 抛错），就返回 `第 N 个节点（seq S）的消息形态不受支持（…），未做改动`，**不 append、不报成功**；若此前已有节点落地，错误里同样带上"已有 N 个被永久遮蔽"（`packages/dsh-plugin-redact/index.js:311`、`:337-338`）。

**由哪条断言守住。** `hardening.mjs`："★ F10 消息形态不受支持 → `kind:error`（不再谎报"已隐藏 1 个节点"）"、"★ F10 报出「未做改动」"。

> [!note] 同族缺陷（F9，一并修掉） —— `hide` 多目标**半途失败**时旧实现只报"第 N 个节点替换失败"，把已经永久遮蔽的节点（`landed`）丢掉了。修复后错误分支追加 `· 已有 N 个节点被永久遮蔽（seq …），该变更已生效且不可撤销，建议重开会话`（`index.js:1061-1066`）。红队建议的"先做可提交性预检"**故意没做**：`session.append` 的失败源（磁盘满/句柄失效/校验失败）无法在不提交的前提下预判，硬做一个假检查只会制造虚假的安全感（`REPORT-FIX-zh.md:364`）。守护断言：`hardening.mjs` 的 4 条 F9 断言（含"半途状态属实：第 1 个节点的替换确实已提交"）。

### D-13 Node 版本不符被误诊为"日志损坏"

> [!bug] 误导 · 报错指向错误的对象 —— 症状：在 Node < 22.15 上跑套件，看到的是 `RedactError: 日志无法解析：帧魔数非法 @ 字节 …`——**看起来像日志坏了**，实际是运行时不提供 `zlib.zstdCompressSync`。

**机制与成因。** 引擎依赖 zlib 的 zstd API（Node ≥ 22.15）。当运行时缺这个 API 时，模块**加载期**就抛错；而套件与 CLI 的顶层没有把"运行时能力缺失"从"日志损坏"里分出来，加上旧引擎用 `process.exit(1)` 表示拒绝，测试进程被直接杀掉，观察到的就只剩"日志相关的报错"。

**如何被发现。** 作者自查：本机 PATH 上的 `node` 是 v18.16.1，而 DSH 部署自带的是 v22.21.0（本档写作时复跑套件实测：默认 `node` = v18.16.1，`& "...\nodejs-x64\node-v22.21.0-win-x64\node.exe"` = v22.21.0）。

**如何修复。** ① 引擎在模块加载期做**显式**的版本/API 检查，报错文案直接说清要升 Node（`packages/dsh-plugin-redact/lib/engine.mjs` 顶部装载检查，实测输出：`dsh-redact 需要 Node >= 22.15（zlib 的 zstd API 自该版本起提供）；当前运行时 v18.16.1 缺少 zstdDecompressSync / zstdCompressSync。请升级 Node 后重试。`）；② 拒绝改为抛 `RedactError`（D-06），于是"进程被杀"不再污染诊断；③ `package.json` 声明 `engines.node >= 22.15.0`（`packages/dsh-plugin-redact/package.json:29-31`）；④ CI 矩阵显式列出 `22.15 / 22.x / 24.x`（`.github/workflows/ci.yml:16`）。

**由哪条断言守住。** 本档写作时以默认 `node`（v18.16.1）复跑 `handler.selftest.mjs`：得到**一句可读的版本诊断 + 退出码 1**，而不是"日志损坏"或静默通过。这是**行为实测**而非断言；`handler.selftest.mjs` 的"被测版本"打印（被测文件的字节数 + sha256 前 12 位，`test/handler.selftest.mjs:83`）是配套的可追溯手段。

---

## 五、分页与识别类

### D-14 固定页大小让"装不下的那几条"永远看不到

> [!bug] 功能不可达 · 目标行无法选中 —— 症状：`/redact nodes` 用固定条数切页，页尾因为要放"是否还有下一页"的提示，**把这一页最后几条挤掉**——被挤掉的序号在后续任何一页都不会再出现。用户翻到最后一页也找不到它，而命令本身不报错。

**机制与成因。** 输出在离开 handler 前就被 `clamp(s, 200)` 收敛到 200 显示格（`packages/dsh-plugin-redact/index.js:32`、`:41-52`），渲染端 `cleanRenderText(text, COMMAND_RESULT_CELLS = 200)` 还会压平换行并截断（`README.zh.md:236-254`）。按**固定条数**切页时，"这一页还剩几格"是没有被计算的量，于是页尾条目与"续 /redact nodes N"提示互相踩。

**如何被发现 → 如何修复。** 作者在给 `nodes` 写分页契约时逐页核对序号连续性，发现被挤掉的条目在任何页都不再出现。修复：改成**按显示格预算切块**——多页时 head 变成 `… 第1/7页：`，未到底接 ` 续 /redact nodes 2（还有17条） · `，末页没有"续"只有 ` 全文 … · 隐藏 …`；**序号跨页连续**，任何一页看到的序号都能直接喂给 `hide`；页号越界自动落到最后一页（`README.zh.md:224`、`:278`）。`list` / `scan` 同理：宁可主动少列几条（`…另N个` / `…共M`），也不让关键的行号被截掉（`:268`）。

**由哪条断言守住。** `handler.selftest.mjs` 的 `nodes` 节：**"★ 逐页翻到底：序号 1..20 全覆盖、无缺口、无重复"**（20 个节点实测 7 页）、"`nodes` 分页不止一页（按显示格切块，而非固定条数）"、"`nodes` 每页尾部完整（以「隐藏 /redact hide <序号>」结尾）"。

### D-15 条目里没有人能用来"认出是哪一条"的信息

> [!bug] 功能不可用 · 用户的问题原话是"根本看不出来是哪条" —— 症状：清单里每条只有 `[序号] 工具 体积`。同一轮里跑过两个 `pwsh`、一次 `web_search`，用户无法判断该隐藏哪一条；想隐藏就得先去翻原会话。

**机制与成因 → 如何被发现。** 收集节点时只取了 `tool/result` 事件自身能给出的字段；工具名与命令行需要**回到同一 `callId` 的 `tool/call` 事件**去对，这一步最初没做。而 `nodes` 的单行通知又极度吃紧（200 格），"信息足够"与"放得下"互相竞争。用户反馈直接给了原话（README 引用了它：`README.zh.md:296`）。

**如何修复。** 六项识别元数据补齐：**序号 / 日志行号 / 轮次 / 工具名 / 体积 / 该次工具调用的命令行**（命令行受 `argsCells` 控制）。字段来源逐项写进文档：序号=surface 位次；行号=`seq + 2`；**轮次取 `tool/result` 事件自己的 `data.turn`**（不是从别处推）；工具名与命令行用 `message.source.callId` 回查 `tool/call`（`README.zh.md:318-325`、`index.js:76-114`）。两条硬约束同时保留：**工具结果的正文永远不显示**；命令行本身可能含敏感查询词，所以有 `argsCells` 这个开关。另外 `nodes full` 写出的清单每行直接附 `→ /redact hide <n> --commit`，用户**不用从通知里复制任何字符**（`:267`、`:278`）。

**由哪条断言守住。** `handler.selftest.mjs`："★ `nodes` 每条都带「轮 T」，且行号/轮次/工具与节点账本一一对应"、"★ `nodes full` 每行都含轮次、行号与命令行（认出是哪一条）"、"`nodes full` 每行含 `→ /redact hide <n> --commit`（序号可直接用）"、"`argsCells` 默认 120 → `nodes full` 含完整命令行"。

---

## 六、工程卫生类

### D-16 随包发布的测试里写着作者的绝对路径

> [!bug] 卫生 · 交付物泄漏作者环境，且外人跑不通 —— 症状：陌生人 `npm install` 之后跑套件，报错与断言文案里全是 `%USERPROFILE%` 下的具体路径；报告类产物（修复前后的存档输出）里同样带着作者的绝对路径。

**机制与成因。** 测试与报告是在作者机器上"就地"跑出来的，脚本与断言直接把工作路径打进了输出。

**如何被发现。** 发布前审计（逐文件过 `files` 列表与报告存档）。

**如何修复。** 公开仓库中的路径一律改写为 `%USERPROFILE%\…` / `$DSH_HOME/…`；套件本身不再依赖固定的作者路径（`handler.selftest.mjs` 把 `DSH_HOME` 指向 `mkdtemp` 出来的临时目录，`test/handler.selftest.mjs:16`、`:78`；需要真实 DSH 的套件改用 `DSH_REDACT_DSH_LIB` / `DSH_NODE_MODULES` 覆盖，`test/real-reader.mjs:22-41`）。

**由哪条断言守住。** 无断言，只有**发布清单**：`package.json` 的 `files` 显式列出随包发布的文件（两份含 `preflight.mjs` 与 `handler.selftest.mjs`，`packages/dsh-plugin-redact/package.json:17-28`），其余套件只在源码仓库里。

### D-17 依赖 DSH 的套件在跑不了的时候退出码 0

> [!bug] 卫生 · 陌生人的 `npm test` 静默变绿 —— 症状：机器上没有 DSH 安装目录时，套件打印一句"跳过"就 **exit 0**。CI 与本地都显示通过，实际**一个字都没测**。

**机制与成因。** "找不到依赖就跳过"是常见写法，但它与"通过"共用同一个退出码，于是"没跑"和"跑了且对"不可区分。

**如何被发现。** 发布前审计（对照 [[CORRECTIONS]] C-003"信任未经校准的扫描结果"的同构形状：**下"未发现"结论前先证明扫描器看得见目标**——这里就是"下'通过'结论前先证明测试真的跑了"）。

**如何修复。** 三类套件全部改成**响亮失败**：`registry-e2e.mjs` 找不到 `@deepseek-ai/dsh-tools` 时以**退出码 3** 退出并说明原因，源码注释写明"不能用 0，否则「本轮根本没跑」会被当成通过"（`packages/dsh-plugin-content-policy/test/registry-e2e.mjs:20`、`:37-39`）；`config-schemastery.mjs` 同样 `exit 3`（`test/config-schemastery.mjs:15-16`、`:35-39`）；`real-reader.mjs` 直接**抛错而不是跳过**——判据不能降级（`packages/dsh-plugin-redact/test/real-reader.mjs:32-41`）。CI 里显式写明这些套件为什么不在矩阵里跑（`.github/workflows/ci.yml:46-47`）。

**由哪条断言守住。** 流程断言（退出码契约）而非用例断言。本档写作时实测：五个套件在 Node 22.21.0 + 本机 DSH 安装下全部实跑通过（`248/248`、`54/54`、`78/78`、`34/34`、content-policy 四套 `45+36+17+5`）。

### D-18 缺 LICENSE 文件

> [!bug] 卫生 · 声明的许可没有正文 —— 症状：`package.json` 写 `"license": "MIT"`、README 写"MIT"，但包里**没有 LICENSE 文件**；`files` 列表里也没有它。作者本地的未发布插件仓库里同样没有。

**机制与成因 → 如何被发现 → 如何修复。** 许可只在 manifest 与 README 里被声明，从未落成文件；而 `files` 列表又是手写的，于是"声明过"与"真的会发出去"之间没有交叉检查。发布前逐包核对 `files` 与目录内容时发现。修复：仓库根与两个包各自补上 `LICENSE`（MIT 全文），并加进两个包的 `files` 列表（`packages/dsh-plugin-redact/package.json:27`、`packages/dsh-plugin-content-policy/package.json:21`）；打包体积与文件清单已实测记录（`README.zh.md:701`）。

**由哪条断言守住。** 无断言，只有发布清单与打包实测（`npm pack` 的文件列表）。

### D-19 有一个包完全没有 `test` 脚本

> [!bug] 卫生 · `npm test` 报错，或什么都不跑 —— 症状：`dsh-plugin-redact` 的 `package.json` 里没有 `scripts` 段。陌生人 `npm test` 得到 npm 的"missing script"错误；就算有脚本，也不知道该按什么顺序跑、哪些依赖真实 DSH。

**机制与成因 → 如何被发现 → 如何修复。** 套件是"作者直接 `node test/xxx.mjs`"跑起来的，脚本入口从未被写进 manifest——README 一度还写着"`package.json` 没有配置 `scripts`，请直接 `node <文件>` 运行"（`README.zh.md:599`）。发布前审计时发现。修复：两个包都补上 `scripts.test`——redact 是 `node test/handler.selftest.mjs && node test/preflight.mjs`（`packages/dsh-plugin-redact/package.json:60-62`，两个都**不需要** DSH 安装，所以随包发布）；content-policy 是 `node test/selftest.mjs && node test/harness.mjs`，并把需要真实 DSH 的两套单列成 `test:config` / `test:registry`（`packages/dsh-plugin-content-policy/package.json:23-28`）。

**由哪条断言守住。** 无断言；CI 直接调用同样的入口（`.github/workflows/ci.yml:32-44`）。

> [!warning] 卫生类的共同点 —— 这一类的每一条都**不影响作者本机**，只影响"陌生人能否复现"。检出方式不是测试，而是**发布前按清单逐项核对**——所以修复动作里最重要的一步是把清单本身写进仓库（`files` + `scripts` + CI）。

---

## 收尾对照表：缺陷 → 严重度 → 由哪条断言/套件守住

| id | 严重度 | 守住的断言 / 套件 |
|---|---|---|
| D-01 | 数据丢失（不可逆，会话硬打不开） | `hardening.mjs` F1 组 8 条（游程重映射、真实后端可打开、区间中间被删则拒绝）+ 总闸 7 条一票否决 |
| D-02 | 数据丢失（悬空或静默错指） | `hardening.mjs` F2 组 7 条（含**真实 `dsh-session-title` 不变式**、清单外 `*Seq` 失败关闭） |
| D-03 | 数据丢失（坏备份覆盖健康日志） | `hardening.mjs` F3 组 9 条；`bugfix-regression.mjs` 的 undo 正常路径 1 条 |
| D-04 | 数据丢失（静默丢事件 / 混合体硬损坏） | `hardening.mjs` F4 组 9 条（注入式并发） |
| D-05 | 误导（变更已生效却报失败） | `hardening.mjs` F4(b) 3 条（检测并发追加、点名备份、备份在盘上） |
| D-06 | 杀进程（任何拒绝即整个应用退出） | `handler.selftest.mjs` 的 `process.exit` 安全网 + "★ 9d 抛 `RedactError`，不杀宿主进程"；`bugfix-regression.mjs` 进程存活组 |
| D-07 | 杀进程（单行语法错误 = boot 中止） | 流程守卫：`boot-verify` 扫描（`throwImport` → `BOOT_ABORTED`）+ `stable.mjs` 修订号包夹 |
| D-08 | 杀进程（空 `config:` = boot 中止） | `boot-verify/cfgmatrix.txt` + `stable.txt` 20 格配置矩阵（`omitted`/`{}`/`null`/`{bogus:1}` 必须 `BOOT_OK`）；`handler.selftest.mjs` config 节等价断言 |
| D-09 | 锁死（键盘封锁，`Ctrl+C` 无效） | `handler.selftest.mjs` 的 `pick` 节（默认关闭且不调用服务、<50ms 判据、`dialogTimeoutMs` 三态）；契约核对报告的形状矩阵 |
| D-10 | 误导（隐私开关留痕迹） | `handler.selftest.mjs` `argsCells` 三态（含"★ `argsCells=0` → `nodes full` 完全不写命令行，也不留占位符"） |
| D-11 | 误导（忽略 `--session`） | `handler.selftest.mjs` G1 组 4 条（拒绝、输出不同、零改动、`nodes full` 同拒） |
| D-12 | 误导（报成功而正文未变） | `hardening.mjs` F10 2 条；F9 4 条（半途失败如实上报已落地节点） |
| D-13 | 误导（版本问题被说成日志损坏） | 行为实测：Node 18 下得到一句版本诊断 + 退出码 1；`package.json` `engines` + CI 版本矩阵 |
| D-14 | 分页（固定条数导致目标不可达） | `handler.selftest.mjs`："★ 逐页翻到底：序号 1..20 全覆盖、无缺口、无重复"、"按显示格切块，而非固定条数" |
| D-15 | 识别（认不出是哪一条） | `handler.selftest.mjs`：轮 T 与账本一一对应、`nodes full` 含轮次/行号/命令行、每行附可复制的 `hide` 命令 |
| D-16 | 卫生（作者绝对路径 / 外人跑不通） | 无断言；`files` 发布清单 + 套件改用临时目录与 `DSH_REDACT_DSH_LIB` |
| D-17 | 卫生（跑不了却 exit 0） | 退出码契约：缺依赖 `exit 3`；`real-reader.mjs` 抛错不跳过；CI 注释说明 |
| D-18 | 卫生（缺 LICENSE） | 无断言；`files` 清单 + `npm pack` 实测 |
| D-19 | 卫生（无 `test` 脚本） | 无断言；两个包的 `scripts.test` + CI 调用同一入口 |

### 最终实跑计数（本档写作时，Node 22.21.0，全部退出码 0）

`handler.selftest.mjs` **248/248**（假 ctx + 合成日志，不需 DSH）· `bugfix-regression.mjs` **54/54**（判据是**真实** `JsonlSessionPersistence.open()`）· `hardening.mjs` **78/78**（真实读取端 + 真实 title 不变式）· 引擎/CLI 套件 **34/34** · content-policy 四套 **45 + 36 + 17 + 5 = 103**（纯逻辑 / 假 ctx / 真注册表 / 双轨 Config）。

> [!success] 判据的唯一性 —— `handler.selftest.mjs` 会打印**被测文件的字节数与 sha256 前 12 位**（`test/handler.selftest.mjs:83`），报告里的每个数字因此都能对到具体一版字节；`applyPlan` 的自检、`verify` 子命令、`undo` 的备份校验**复用同一个 `verifyLog`**（`lib/engine.mjs:337`），判据不存在第二份实现。

---

## 关联

| 关联对象 | 关系 |
|---|---|
| [[DSH会话脱敏项目方法论复盘]] | 姊妹篇：这些缺陷为什么能活到红队介入（绿测试陷阱、被推翻的假设、委派得失） |
| [[DSH插件与Hook开发最佳实践]] | 上游规范：`inject`、patch 语义、Config 契约、"配置错误要响亮" |
| [[CORRECTIONS]] | 同源条目：**C-005**（拿工具自检当读取端验收 → D-01/D-02）、**C-006**（"通知会是多行" → D-14 与 200 格预算）、**C-007**（`--dump-config` 当运行时证明 → D-07/D-08）、**C-008**（绿色测试当可用性证据 → 元发现）、**C-009**（服务存在 → D-09）、**C-010**（`!!js disabled` 当稳定值 → D-08 同批）、**C-011**（只测常规值不测边界 → D-10）、**C-003**（未校准的扫描器 → D-17）；共同根源是"把观察到的现象直接当成结论" |
| [[DSH-TUI插件使用手册]] | D-09 的宿主侧机制（键盘让出、面板挂载点、200 格渲染）所在前端 |
| `%USERPROFILE%\dsh-redaction\docs\reports\` | 原始证据：红队报告与复现脚本、修复报告与 before/after 存档、启动扫描矩阵 |

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-12 | 建库：汇总红队 F1–F10、修复报告、对话框根因/契约、启动扫描与两个包的测试套件，形成 19 条缺陷档案与收尾对照表 |
