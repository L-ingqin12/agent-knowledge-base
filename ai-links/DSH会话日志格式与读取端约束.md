---
title: DSH 会话日志格式与读取端约束
aliases: [session.v3.jsonl.zstd, 会话日志格式, seq 密集性]
tags: [ai/tools, ai/agent]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# DSH 会话日志格式与读取端约束

See also: [[AI-Links-KB-Home]] | [[DSH插件与Hook开发最佳实践]] | [[DSH会话持久化与活跃改写安全]] | [[DSH会话脱敏插件缺陷档案]] | [[AGENTS]]

> [!abstract] 本文只回答一个问题
> **`session.vN.jsonl.zstd` 在盘上长什么样，读取端接纳什么、拒绝什么。**
> 面向要写或评审「会话日志改写工具」的人：动一个字节之前，先知道读取端会因为什么把整份日志判死。

> [!danger] 三句话结论
> 1. **行号即身份**：第 n 行的 `seq` 必须等于 n−1。删掉中间某行后，其后每一行都要**重编号**，且**所有引用**都要按同一映射改写；`seq` 忘了改 → 必挂，引用漏改 → 也挂，引用改错（指向合法但错误的行）→ **不报错但语义已坏**。
> 2. **容器层不防编辑**：每帧校验和只覆盖该帧自己的压缩字节，改完重压即合法。真正拦住你的是行级语义（seq 密集 + 引用规则），不是校验和。
> 3. **判据只有一个**：本机 `dsh-session-persistence-jsonl` 的 `open()`。⚠ 但它会把「看着像未完成末帧」的损坏**静默截断**——必须配合事件计数与逐字节帧走查才可信。

## 〇、判据、取证与标注规则

| 项 | 值 |
|---|---|
| 源码根 | `C:\%USERPROFILE%\nodejs-x64\node-v22.21.0-win-x64\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\` |
| 格式版本 | `SESSION_FORMAT_VERSION = 3`（`dsh-session/lib/index.js:56`）；后端包 0.1.5-rc.2 |
| 取证方式 | **合成日志**：假数据 + 真实编解码器 + 真实后端；夹具写在 `%TEMP%\dsh-logfmt\`，**未读取任何真实会话内容、缓存或 `*.jsonl.zstd`** |
| 权威判据 | `new JsonlSessionPersistence(ctx, { root, compression:'zstd' })` → `open(id,'read')` → `handle.read(0)` |

后文引用简写（一律 `简写:行`）：

- `J` = `dsh-session-persistence-jsonl/lib/index.js`（容器、扫描器、后端）
- `F` = `dsh-session-persistence-jsonl/lib/types/format.d.ts`（契约声明）
- `V12` = `dsh-session-format-v1-to-v2/lib/index.js`（行解码器、游程引用）
- `V23` = `dsh-session-format-v2-to-v3/lib/index.js`（当前 codec 包装与准入检查）
- `V01` = `dsh-session-format-v0-to-v1/lib/index.js`（引用关系与载荷语义）
- `P` = `dsh-session-persistence/lib/index.js`（跨后端共享校验）
- `S` = `dsh-session/lib/index.js`｜`T` = `dsh-session/lib/types/types.d.ts`｜`R` = `dsh-session/lib/types/seq-ranges.js`

> [!note] 标注规则
> 未标注 = 已实测或源码直读；**`未验证`** = 仅源码推断、本次未实测。

## 一、文件在哪、叫什么

一个会话一代格式一个文件，文件名由版本号决定：v0 保留 `session.jsonl`，vN 带小写 `vN`（`dsh-session-format/lib/index.js:464,472`），后端再按物理编码追加后缀（`J:746-751`）——`zstd` → `.jsonl.zstd`，`none` → `.jsonl`。

```
$DSH_HOME/sessions/
└── --C-Users-...--proj--/          ← projectKey(cwd)：分隔符与 ":" 折叠成 "-"（J:874-893）
    └── <encodeSegment(sessionId)>/ ← id 转义成单一安全路径段，非安全码位 → ~XXXX（J:852-864）
        ├── session.v3.jsonl.zstd   ← 当前代，追加目标
        └── session.v2.jsonl.zstd   ← 历史代，迁移后才出现
```

- cwd 缺失的会话落在 `_no-cwd`（`J:901-903`）；目录里若同时存在**另一种后缀**的文件，直接按「编码不匹配」拒绝（`J:3161-3184,3321-3326`）。
- 读取端选代规则：取目录里**版本号最大**的 canonical 文件名（`J:3185-3191`），不支持比你更新的版本会明确让你升级 harness（`J:963-967`）。
- 一次性路径构造三件套：`projectKey` → `sessionDir` → `generationLogPath`（`J:874-927`），身份校验会把 header 里的 `id`+`cwd` 重新推回这个路径比对（见第七节）。

## 二、容器 = 一串独立帧的拼接

文件是**普通拼接**的若干 zstd 帧，每帧独立可解、带校验和（magic `0xFD2FB528`，`J:1286`；写入用 `ZSTD_c_checksumFlag: 1`，`J:1289,1367-1369`）。

| 帧 | 内容 | 硬规则 |
|---|---|---|
| 帧 0 | 恰好一行 `{"type":"session",...}` 头 | 必须**恰好一行且以换行结尾**：`assertZstdHeaderFrame`（`J:2184-2186`） |
| 帧 1..n | 一次持久化追加批次 = 1 行或多行事件 | 无行数约束；空会话可只有帧 0（`J:3016-3024`） |

写路径：materialize 时头单独一帧、首批单独一帧（`J:3016-3024`）；此后每次 append 一批压成一帧（`J:3026-3029,3046-3073`）。

> [!tip] 帧边界**不携带任何语义**
> 读取端把每帧解压后得到的明文字节**首尾相接**成一个连续流，再交给行扫描器（`J:2800-2821`）；扫描器本身跨 chunk 保留未完成的行片段（`J:1030-1052`）。因此**一行完全可以横跨两帧**——实测：把明文在行中间切成 3 段各压一帧，`open()` 正常读出 8 条事件。

唯一的边界约束是：**最后一个结构完整的帧必须在行边界结束**——

```js
if (complete.committedBytes !== complete.inputBytes) throw new Error("corrupt Zstandard session log: complete frame contains a torn JSONL record");
```

（`J:2820-2821`；迁移路径同规则，`assertCompleteFramesEndOnRecord`，`J:1712-1714`；扫描器的完整契约见 `F:151-198`）

## 三、信封：`{type, seq, time, data}` + 三个可选项

| 字段 | 必需性 | 校验点 |
|---|---|---|
| `type` | 必需，字符串 | 类型必须在已发布清单内，或在 `knownEventTypes` 内，否则需 `ignorable`（`V23:304-314`；`P:182-189`） |
| `seq` | 必需，非负安全整数 | **必须 == 本行 0-based 行号**（见第四节） |
| `time` | 必需，安全整数 | `V12:270`、`V23:316` |
| `data` | 必需，对象 | 各事件类型自己的载荷校验 |
| `ignorable` | 可选，**只能是 `true`** | `V23:317`；语义是「本 harness 不认识时可安全跳过」 |
| `surfaceOp` | **仅 surface 事件**，且必填 | `append` 或 `{op:'replace',startSeq,endSeq}`，恰好这三个键（`V23:318-324`；类型定义 `T:429-442`） |
| `sourceEventSeqs` | 仅 surface 事件可选 | 非空、全部**更早**、无重复；`assistant/message` 禁止携带（`V23:326-336`） |

surface 事件 = `system/message` / `user/message` / `assistant/message` / `tool/result`（`V23:8-13`）。**多余字段一律拒绝**（`keys()` 逐键白名单，`V23:48-53`）。头行是另一套信封与白名单：必需 `type/version/id/createdAt/isSeeded/delegationDepth`，可选 `cwd/parentSession/origin/agentPreset`（`J:776-790`），已退休的 `sandboxMode`/`approvalPolicy` 直接报错（`J:796-799`）。

## 四、支配一切的不变式：`seq` 必须等于行号

两处决定性检查，**逐字引用**：

```js
// V12:95 —— 整体（非流式）校验
if (record["seq"] !== index) throw new SessionFormatError(`format v2 event ${index} is not dense`);
```

```js
// V12:243-249 —— 流式解码器（读取端实际走的路径）
if (event.seq !== eventCount) {
    const gap = new SessionFormatError(`released v2 row ${currentRow} has seq gap (expected ${eventCount}, got ${event.seq})`);
    if (recovery === "strict") throw gap;
    issue = gap;
    if (event.type === "turn/end") throw issue;
    return;
}
```

> [!danger] 后果：`seq` 忘了重编号 = 整份日志打不开
> 用户看到的不是「少了一条消息」，而是会话**打不开**：
> ```
> SessionPersistenceCorruptionError: session "<sid>": stored log is corrupt:
>   Error: corrupt session log: invalid committed event at line 3:
>   released v2 row 2 has seq gap (expected 2, got 3)
> ```
> （实测：8 行合成日志删掉第 3 行后 `open()` 的结果；异常类型由 `J:2620-2628` / `J:2650-2672` 包装。）

| 改动 | 读取端结果 | 实测 |
|---|---|---|
| 删中间行，**不**重编号 | 硬拒（seq gap） | ✅ 报错见上 |
| 删整帧（帧内若干行） | 硬拒（后续行 seq 全错位） | ✅ `row 3 has seq gap (expected 3, got 6)` |
| 交换两行（JSON 都合法） | 硬拒（seq 错位） | ✅ `row 3 has seq gap (expected 3, got 4)` |
| 删中间行 + **重编号**，但引用漏改 | 硬拒（引用越界/重复/指向自身） | ✅ F1 场景：`sourceEventSeqs range exceeds its event seq` |
| 删中间行 + **重编号 + 引用全对** | **能打开**（前提：被删行没有被任何替换节点/compaction 引用） | ✅ 实测三种：删 append 节点 / 删 `user/message` / 删 log-only `step/start`，全部 `ok`，8 → 7 条 |
| **删尾部后缀** | 通过，事件数减少 | ✅ 删最后 1 行 → 7 条；删最后 3 行 → 5 条 |

> [!warning] 别把「能打开」当成「改对了」
> 上表倒数第二行是本次实测的**反直觉结果**：**删中间行本身不致命，「删了却没把所有引用一起改对」才致命**。这一条同时意味着两件事：
> - 读取端**不会**替你发现「引用改成了另一个合法的、但语义错误的行」——那属于 [[DSH会话脱敏插件缺陷档案]] 里 F2 的静默错引；
> - 因此**「重编号后 seq 密集」是必要不充分条件**：改写工具的自检如果只查 seq 密度，就会放过 F1/F2（这正是该缺陷档案的现场）。
> 另需注意：若被删的行**正被某个替换节点或 compaction 引用**，`sourceEventSeqs` 覆盖关系（`V01:2524-2540`）与 surface 切片完整性（`V01:2576-2583`）会同时失效。**未验证**：本次未构造该夹具实测其报错文本。

**为什么尾部后缀安全**：引用在语义上**只能指向更早的 seq**（`V01:608-612` 的 `earlierSeq`：`seq >= eventSeq` 即报错；`V23:324,333` 同样要求 `< 本行 seq`）。从尾部切除只会删掉「被引用者」，永远不会产生悬空引用。两条例外：

1. **seeded 会话**必须保留 inherited 的 `session/end-seed` 标记：解码器 `finish()` 会检查 `header.isSeeded && inheritedEventCount === undefined` → `released v2 seeded Session lacks an inherited end-seed marker`（`V12:256-260`；v3 包装同规则 `V23:572-577`）。**未验证**：本次未构造 seeded 夹具实测。
2. 尾部缺 `turn/end` 是被**容忍**的：读取端用 `interruptedTurnClosers` 补一个收尾事件（`S:611-709`），实测删掉末尾 `turn/end` 仍能打开（7 条）。

## 五、引用字段：清单、盘上形态、读取端规则

> [!warning] 盘上不是内存形态：`sourceEventSeqs` 是**游程编码**的
> `≥3` 个连续 seq 会压成 `[start, end]` 闭区间对；2 个连续仍是两个整数；非严格递增则原样保留（`R:11-27`；编码端 `V12:327-342`）。实测：`[2,3,4] → [[2,4]]`，`[2,3,4,9] → [[2,4],9]`，`[2,3] → [2,3]`。
> **任何按整数逐项 `map()` 的重编号都会静默改错区间**，然后被读取端硬拒：`decodeSeqRanges([[2,4]], 3)` → `sourceEventSeqs range exceeds its event seq`（`V12:303-326`；`R:34-68` 同规则）。这就是 [[DSH会话脱敏插件缺陷档案]] 里 F1 的根因。

| 位置 | 盘上形态 | 读取端规则 | 出处 |
|---|---|---|---|
| 行级 `sourceEventSeqs` | `(number \| [start,end])[]` | 展开后：每个 < 本行 seq、无重复、非空（assistant/message 除外） | `V23:326-336`；`V01:1548-1559`；解码 `V12:303-326` |
| 行级 `surfaceOp.startSeq/endSeq` | 两个整数（v3 盘上名） | 恰好 `{op:'replace',startSeq,endSeq}` 三键；两端 < 本行 seq | `V23:321-324` |
| `compaction/*` 的 `data.shadowedRange.{start,end}` + `data.shadowedSeqs` | 整数 + 整数数组 | 两端更早、数组非空无重复，且 **range 端点必须等于 seqs 首尾** | `V01:1141-1148` |
| `session/title`、`session/title-llm-request` 的 `data.messageSeqs` | 整数数组 | 必须指向**更早的人类** `user/message`（`source.kind === 'user'`）；空数组当且仅当来源是用户 | `V01:2541-2552` |
| `command/done` 的 `data.sourceEventSeq`（单数） | 整数 | 迁移期按同一映射重映射 | `V23:644-648` |

还有两条**跨行关系**校验，重编号后最容易踩：

- surface 替换的 `start/end` 必须落在**当前 surface** 上，且 `sourceEventSeqs` 必须覆盖被遮蔽的**每一个**节点（`V01:2524-2540`）。
- compaction 的 `shadowedSeqs` 必须正好是当前 surface 的一段连续切片（`V01:2576-2583`）；且不得遮蔽受保护的 system 头（`V23:442-449`）。

> [!tip] 可操作的审计规则
> **任何键名匹配 `/(^|_)(seq|seqs)$/i` 的数值/数组字段都可能是持久化引用。** 目前已知的全部命中：`seq`、`sourceEventSeqs`、`surfaceOp.startSeq/endSeq`、`shadowedSeqs`、`messageSeqs`、`sourceEventSeq`。改写工具的正确姿势是「显式清单 + 清单外命中即失败关闭」，而不是「只改我知道的那几个」——F1/F2 正是漏了区间与 `messageSeqs`。

## 六、准入 vs 容忍：谁会让整份文件被拒

> [!bug] 一句必须记住的话
> **完整帧内的一行坏数据，永远不会被当成「可恢复的崩溃尾」。** 容错只对**物理上未写完的最后一帧**生效。

| 类别 | 判定 | 出处 / 实测 |
|---|---|---|
| 帧魔数非法、保留位、保留块类型 | 整份拒绝 | `J:1307,1315,1338` |
| 帧解压或**校验和**失败 | 整份拒绝：`corrupt Zstandard session log: frame at byte N failed validation` | `J:3146-3151`；✅ 在 payload / 校验和字段翻转任一帧均硬拒 |
| 帧 0 不是「恰好一行」 | 整份拒绝：`first frame is not exactly one header line` | `J:2184-2186`；✅ 帧 0 = 头行+1 条事件行即复现 |
| **完整帧**内出现撕裂行（无换行结尾） | 整份拒绝：`complete frame contains a torn JSONL record` | `J:2820-2821` |
| 完整帧内的行：JSON 不可解析 | 整份拒绝：`unparsable committed event at line N` | `J:1085`；✅ 实测 |
| 完整帧内的行：JSON 合法但形状不合法 | 整份拒绝：`invalid committed event at line N: ...` | `J:1105`；✅ 实测（`released v2 row 1 lacks required field type`） |
| `seq` 不密集 | 整份拒绝 | `V12:95,243-249`；✅ 实测 |
| 引用规则违反 | 整份拒绝 | `V23:324,333`；`V01:610,1146,1556,2550`；✅ 实测 |
| 未知事件类型且无 `ignorable:true` | 整份拒绝（**即使它在最后一行**） | `P:182-189`；✅ 实测 `SessionFormatUnsupportedError` |
| 头行 `id`/`cwd` 推不出该文件路径 | 整份拒绝 | `J:3218-3227`；✅ 实测 |
| 存储版本 > 本 harness | 拒读并提示升级（**不是**「损坏」） | `J:963-967`；`P:137-139`；✅ 实测 version=4 |
| **物理未完成的末帧** | 容忍：保留完整前缀，尽力恢复，剩下的字节定位为可截断点 | `J:2822-2849`；✅ 实测截断末帧 5 字节 → 仍 `ok`，8 条变 6 条 |
| 未知类型 + `ignorable:true` | 容忍：计入日志、语义层跳过 | ✅ 实测 `ok`，9 条 |
| 末尾缺 `turn/end` | 容忍：读取端补 closer | `S:611-709`；✅ 实测 |

> [!warning] 容忍路径的反向风险（本次实测发现）
> 结构走查只看帧头/块头，**不解压**（`J:1298-1361`）。如果损坏让某帧「块长度字段变得超出文件剩余字节」，走查会把它判成**未完成的末帧**，于是读取端走容忍路径——**静默截断，不报错**。实测：翻转中间帧块头的一个字节 → `open()` 返回成功，但事件数从 8 变成 0 / 3 / 6（取决于位置）。
> 触发条件依赖具体位翻转位置（我只测了块头 3 个字节 × 3 个帧），**未验证**是否所有此类损坏都会落到容忍路径。结论：**「能打开」不等于「内容完整」**。

## 七、校验和与身份：什么能检测，什么检测不到

| 机制 | 覆盖范围 | 能检测 | 检测不到 |
|---|---|---|---|
| 每帧 zstd 校验和（`ZSTD_c_checksumFlag: 1`，`J:1289`） | **该帧自己的压缩字节** | 位翻转、截断、字节损坏 | **任何行编辑**：解压→改行→用同样参数重压，校验和自然合法 |
| 头行 `id` + `cwd` → 路径比对（`J:3218-3227`） | 文件位置身份 | 文件被搬到别的会话目录 / 改名 | 内容被改 |
| 存储 `version` 检查（`J:963-967`） | 代际身份 | 更新的 harness 写的日志被旧版读 | 内容被改 |
| 事件类型白名单（`P:182-189`） | 词汇表 | 未来新增的**必需**事件类型 | 已认识的类型被改语义 |
| 行级语义（seq 密集 + 引用规则） | 结构 | 破坏结构的编辑 | **合法但语义错误的编辑** |

> [!danger] 结论：没有签名、没有 MAC、没有全文件摘要
> 实测：把 8 行日志里第 5 行的正文 `"q2"` 改成 `"EDITED-BY-ATTACKER"`，逐帧重压后 `open()` **完全正常**，读回来的就是被改过的文本（字节数 672 → 692）。**任何声称「校验和能证明日志未被篡改」的说法都是错的**；能证明的只有「这份文件的结构仍然自洽」。

## 八、验证配方：不依赖被测工具的复核

复核别人（或别的工具）产出的日志时，**不要**只跑那个工具的自检，也**不要**只看 `open()` 是否成功：

1. **定位帧**：按 zstd 帧结构走一遍（magic `0xFD2FB528` → 帧描述符 → 块头循环 → 可选 4 字节校验和）。不要假设「一帧一批」，也不要假设「行不跨帧」。
2. **逐帧解压并拼接**明文字节流；先断言**帧 0 恰好一行**。
3. **按 `\n` 切行、逐行 `JSON.parse`**。任何一行解析失败 = 整份日志不可读（**不许**当崩溃尾放过）。
4. **校验 `seq === 行号 − 1`**（0-based），并记下事件总数。
5. **递归检查每一个引用字段**：键名匹配 `/(^|_)(seq|seqs)$/i` 的整数 → 必须 `< 本行 seq`；数组 → **先按游程展开**（`[a,b]` 是闭区间），再检查「每个元素 < 本行 seq、无重复、严格递增」；`shadowedRange` 端点必须等于 `shadowedSeqs` 首尾；`messageSeqs` 必须指向更早的人类 `user/message`。
6. **逐字节对账**：扫描出的帧范围拼起来必须恰好覆盖整个文件长度。**任何未被解释的字节，就是「被当成崩溃尾静默截断」的指纹**——这是第六节那个坑的唯一检出手段。
7. **交叉验证权威 oracle**：`dsh-session-persistence-jsonl` 的 `open()`（`open(id,'read')` 即可，实测与 `'write'` 对同一文件的判定一致）。⚠ 它不是充分判据（见第六节），必须与第 4 步的事件计数一起看。
8. **只读检查**：不要用 `open(id,'write')` 当探针——写句柄在首次 append 时会**截断崩溃尾并重放恢复尾**（`J:221-239`），检查动作本身会改文件。写入侧语义见 [[DSH会话持久化与活跃改写安全]]。

```js
// 帧走查的最小实现（与 J:1298-1361 同构，只走结构、不解压）
function scanFrames(buf) {
  const frames = []; let off = 0
  while (off < buf.length) {
    const start = off
    if (buf.length - off < 4) return { frames, tornStart: start }
    if (buf.readUInt32LE(off) !== 0xfd2fb528) throw new Error(`invalid frame magic at byte ${off}`)
    off += 4
    const d = buf.readUInt8(off); off += 1
    const csf = d >>> 6, single = (d & 32) !== 0, checksum = (d & 4) !== 0, df = d & 3
    const dictBytes = df === 3 ? 4 : df
    const sizeBytes = csf === 0 ? (single ? 1 : 0) : 1 << csf
    off += (single ? 0 : 1) + dictBytes + sizeBytes
    for (;;) {
      if (buf.length - off < 3) return { frames, tornStart: start }
      const bh = buf.readUIntLE(off, 3); off += 3
      const last = (bh & 1) !== 0, type = (bh >>> 1) & 3, size = bh >>> 3
      if (type === 3) throw new Error(`reserved block type at byte ${off - 3}`)
      off += type === 1 ? 1 : size              // RLE 块只占 1 字节
      if (last) break
    }
    if (checksum) off += 4
    frames.push({ start, end: off })
  }
  return { frames }
}
```

## 九、未验证 / 待确认

| 项 | 状态 |
|---|---|
| seeded 会话尾部丢失 inherited `session/end-seed` 后的实际报错文本 | **未验证**（源码推断：`V12:256-260`、`V23:572-577`） |
| 块头损坏落入「静默截断」路径的完整触发条件 | **未验证**（只测了 3 帧 × 块头 3 字节） |
| `none`（明文 `.jsonl`）编码下的容忍差异 | **未验证**（本次全部用 `zstd`） |
| v0/v1/v2 历史代在被读取前的迁移行为 | 本轮未覆盖（迁移路径 `J:1744-1795` 有独立规则） |

## Related

- [[DSH会话持久化与活跃改写安全]] — 写入侧：append、崩溃尾截断与重放、活跃改写窗口（本文刻意不展开）
- [[DSH会话脱敏插件缺陷档案]] — F1/F2 就是本文第四节与第五节的活例：漏改游程引用与 `messageSeqs` → 日志打不开
- [[DSH插件与Hook开发最佳实践]] — `session/event` 与 Cordis 事件的区别、插件侧观察姿势
- [[AI-Links-KB-Home]] — AI 链接收藏库 MOC
- [[AGENTS]] — 本库写作与取证规范（§6.5 出结论前回查 [[CORRECTIONS]]）
