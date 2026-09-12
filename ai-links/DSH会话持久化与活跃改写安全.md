---
title: DSH 会话持久化与活跃改写安全
aliases: [会话写入语义, 活跃句柄改写, tornTruncateTo]
tags: [ai/tools, ai/agent]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# DSH 会话持久化与活跃改写安全

See also: [[AI-Links-KB-Home]] | [[DSH插件与Hook开发最佳实践]] | [[AGENTS]] | [[DSH会话日志格式与读取端约束]] | [[DSH会话脱敏插件缺陷档案]]

> [!abstract] 一句话结论
> **只在「行数不变、每个 `seq` 不变、header 行不动、只改行内文本」时，活跃句柄下原地改写日志才是安全的**；代价仅仅是内存里的历史仍旧是旧文本，直到会话被重新打开。除此之外的每一种改写（尾帧残缺、有行解不开、动 header 身份字段）都有确切的破坏机制，其中最危险的一种是**静默截断**——它不报错，只是少事件。
>
> 本文只回答这一个问题，以及它牵出的追写/守卫/并发/派生缓存。日志格式与读取端合法性归 [[DSH会话日志格式与读取端约束]]。

---

## 一、先看写路径：没有长驻 fd，也没有缓存写偏移

这是整个安全论证的基石。每条 `append` 批次都是**一次性句柄**：

```js
const handle = await open(path, "a");   // 每次追加都重新 open
const { size: before } = await handle.stat();
await handle.writeFile(content);        // 写到当时 EOF
await handle.sync();                    // fsync
// finally: await closeAppendHandle()    // 立即 close
```

（`@deepseek-ai/dsh-session-persistence-jsonl/lib/index.js:3046-3073`，同步/回滚在 `:3074-3082`）

| 事实 | 位置 | 含义 |
|---|---|---|
| 每批 `open(path, "a")` | `dsh-session-persistence-jsonl/lib/index.js:3049` | 进程里**不存在**跨批次的日志 fd |
| 写完 `sync()` 后立刻 `close()` | `:3060`、`:3070-3072` | 崩溃/关闭不会遗留脏页或半开句柄 |
| 写位置由 `"a"` 决定（EOF），代码里**没有**记录/复用字节偏移 | `:3049-3059` | 文件被外部改写后，下一次追加落在**新 EOF**，不是旧偏移 |
| 写失败时按写入前的 `stat().size` 回滚 | `:3057`、`:3064`、`:3074-3082` | 同一 cursor 会重试，所以绝不能留下半批字节 |

> [!info] 一个容易误读的对照
> 全仓唯一被**记住并复用**的字节偏移是尾帧截断点 `state.tornTruncateTo`（`:226-229` → `:3083-3093`）。它不是写位置，而是**修复位置**——见 §四.2。写位置永远是「打开的这一刻」的 EOF。

**对「文件在下面被编辑了」的直接推论**：由于既不持 fd 也不缓存偏移，追加**不会**写坏前文、不会覆盖旧字节、也不会因为文件变短/变长而错位。风险**不在写路径**，而在内存里那几处「记下来的东西」。

---

## 二、活跃句柄上每一处会过期的状态

写句柄在 `open(id, "write")` 时建立，一次性把日志读进内存并按下表记住若干状态（`:2345-2405`）。读写两条读取路径如下：

- 写句柄有 `state.primed` 时，`read()` **只从内存切**，根本不碰文件（`:67-68`、`:93-99`）；
- 只有冷读（无 primed）才走 `readStoredLog` → 重新解码（`:101-109`、`:2637-2648`）。

| # | 状态 | 位置 | 记的是什么 | 文件被原地改写后 | 有无守卫 |
|---|---|---|---|---|---|
| 1 | `observedLength` | `:35`、`:103-104`、`:94`、`:238` | **已观测的「解码事件条数」上界**（单调递增） | 改写后若**解码条数变少**则触发守卫；条数不变则无事 | ✅ 见 §三.1 |
| 2 | `state.cursor` | `:2384`、`:225`、`:236` | 下一个待写 `seq`（= 事件计数，**不是字节**） | 不随文件变化；下次 `append` 的 `seq` 必须等于它 | `assertContiguous` |
| 3 | `state.primed` | `:2389`、`:93-99` | 打开时解码好的整段快照（事件数组 + eventState） | **原地失效**：读出去的还是旧文本，直到首次 append 才清空（`:237`） | ❌ 无 |
| 4 | `coldLogMemo` 修订备忘 | `:2211-2219`（`dev:ino:size:mtimeNs:ctimeNs`）、`:2641`、`:2523` | 上次解码快照 + 它的 stat 指纹 | 指纹相同 → **直接返回旧快照**（重读，不是拒绝） | 弱：见 §三.3 |
| 5 | `state.tornTruncateTo` | `:2386`、`:226-229`、`:2662`、`:2847` | **唯一的真字节偏移**：尾帧安全截断点 | 布局变了 → 该偏移指向**错误位置**，下次追加前会按它截断 | ❌ 无 —— §四.2 |
| 6 | `state.recoveredTail` | `:2387`、`:230-233` | 残缺尾帧里已解出的事件（zstd 路径会产生） | 与 5 配对；偏移错则补写内容错 | ❌ 无 |
| 7 | `state.materialized` / `inheritedEventCount` | `:2385`、`:2388` | 是否已有落盘产物、fork 继承前缀长度 | 改写不影响（继承长度写在 header 行里，属 §四.3） | ❌ 无 |

> [!warning] 第 5 项是唯一「字节级」的记忆，也是唯一会**主动写坏文件**的记忆
> 其余各项最坏只是「读到旧值」；只有 `tornTruncateTo` 会在下一次 append 之前**执行一次 `truncate`**（`:226-229` → `:2751` → `:3086`）。

内存侧（`dsh-session`）同样不刷新，而且**没有任何回读路径**：`dsh-session` 全文不引用 `sessionPersistence`、不碰文件 I/O（持久化被刻意排除在该包之外）；历史数组只在两处被写入——构造时 seed、append 时 push（`dsh-session/lib/index.js:1075`、`:1200`）；`deriveMessages()` 是**增量折叠**缓存，只在 `surface.replaceGeneration` 变化或追加新节点时重建（`:1269-1284`）。会话恢复时历史只进入内存一次：`persistence.open(id, "write")` → `handle.read(0)` → `prepare({ seed: [...persisted, ...closers] })`（`dsh-agent-loop/lib/index.js:1899-1917`）。

> [!danger] 对脱敏场景的直接后果
> 派生消息对象是**共享且深冻结**的（`deriveMessages` 的注释明确写「The `Message` objects in it are SHARED and **deep-frozen**」，`dsh-session/lib/index.js:1260-1266`）。因此改写落盘后：**内存里仍持有含原文的消息对象**，并且在该会话被重开之前，这些对象还会**继续被送进模型请求**。结论只有一句：**改盘之后必须重开会话，否则等于没脱敏。**

---

## 三、三道守卫的精确触发条件

### 1. 收缩守卫 —— 比较的是「解码事件条数」，不是字节数

```js
if (source.events.length < this.observedLength)
  throw new Error(`session "${this.id}": stored log shrank below a previously observed prefix (...)`)
this.observedLength = source.events.length
```

（`dsh-session-persistence-jsonl/lib/index.js:101-109`）

- 触发条件：**一次解码得到的事件条数少于本句柄曾观测到的条数**。
- 注意 `observedLength` 在追加路径被赋为 `state.cursor`（`:238`）、在读取路径被赋为解码条数（`:94`、`:104`），**全程没有任何字节数参与**。
- 因此「文件变小了但每个 seq 仍在」不会触发它；「有一行解不开导致条数下降」才会。这是刻意设计：守卫保护的是**逻辑前缀**，不是物理长度。
- 该守卫只作用于**同一句柄的生命周期内**（`observedLength` 初值 0，`:35`，类型声明里连注释都没有）；重新打开会话后它不再记得旧条数，所以「重开就安全」是假的。
- **触发时机很反直觉**：活跃写句柄有 `primed` 时 `read()` 只切内存、**从不重读文件**（`:67-68`、`:93-99`），而 `primed` 只在**首次追加成功后**才被清空（`:237`）。所以在「还没写过任何新事件」的活跃句柄上，这条守卫**根本没机会被求值**——它会一直沉默，直到该会话被重开、或该句柄追加过至少一次之后又走冷读。**别把「没报错」当成「文件没被改坏」。**

### 2. 连续性断言 —— 比较内存游标，**不可能**因文件编辑而触发

`assertContiguous(this.id, batch, this.state.cursor)`（`:225`）比较的是**待写批次的 seq 与内存里的 `state.cursor`**；`cursor` 只在 append 成功后自增（`:236`）。文件被编辑不会改变这个内存值，所以这条断言**不会**因为外部改写而报错——它拦的是调用方传错 seq。别把它当成外部改写的守卫。

### 3. 修订备忘 —— 命中就**返回旧快照**，不命中才重读

```js
const probe = fileRevision(await stat(path, { bigint: true }))   // dev:ino:size:mtimeNs:ctimeNs
if (memoized?.status === "current" && memoized.revision === probe) return memoized  // 直接返回旧解码结果
// 否则：readStableJsonlFile → decodeStoredLog（重新读、重新解码、覆盖备忘）
```

（`:2637-2648`、`:2211-2219`；稳定读为 stat→read→stat 双次比对，不一致时最多重试一次并退回「读前提交前缀」，`:1642-1665`）

它做的是**重读**，从不「拒绝」。但反过来说：**指纹相同就当没变过**。原地改写若把 `size` 与时间戳都撞上，备忘录会把**改写前的事件数组**当当前状态直接给出。

> [!question] 未验证：时间戳撞车的真实概率
> `mtimeNs/ctimeNs` 由文件系统给；本机 NTFS 的实际分辨率与「同一时钟刻度内完成改写」是否可能，**我没有实测**。同字节长度的行内等长替换是风险最高的形态（`size` 必然相同）。实现者不应依赖「时间戳一定会变」，而应在改写后主动让缓存失效（§六）。
>
> 同理未验证：`writeEveryEvents` / `writeIntervalMs` 的本机取值与检查点落盘时机——见 §七 的清理建议。

---

## 四、结论与分支：哪些改写安全，哪些不安全

### 4.1 安全条件（唯一成立的一类）

> [!success] 安全的改写
> **行数完全不变 + 每个 `seq` 不变 + header 行一字不动 + 只替换行内文本**，且写入过程中没有并发追加（§五）。

在满足上述条件的原地改写中：

| 关注点 | 结果 |
|---|---|
| 后续 `append` | 正常：重新 `open("a")` 落在新 EOF（`:3049`），`cursor` 与文件条数仍然对齐 |
| 后续冷读 | 正常：修订指纹变化 → 重读重解码，拿到新文本 |
| 安全截断点 | 无尾帧时 `tornTruncateTo` 为 `undefined`（`:2662`），不触发任何截断 |
| **唯一后果** | 本句柄内存里的 `primed` 快照与 `dsh-session` 的历史/派生消息仍是**旧文本**（§二 第 3 项、`:1269-1284`）——**必须重开会话才会看到脱敏后的文本** |

### 4.2 不安全分支及其确切机制

| 分支 | 机制 | 症状 | 位置 |
|---|---|---|---|
| **尾帧残缺（torn tail）** | 句柄记着**改写前布局**算出的 `tornTruncateTo`；行被插入/删除后该偏移落点全错，下次 append 前先 `truncate` 到错位置 | **静默损坏**：可能多切（少事件、守卫随后报收缩）也可能切在行中间（留下解不开的行） | `:226-229`、`:2662`/`:2847`、`:3083-3093` |
| **任意一行解不开**（JSON 坏 / schema 不认 / 违反引用不变式） | 解码在**该行**中断：`committedBytes` 停在上一行 → 条数下降 → `source.events.length < observedLength` | 收缩守卫抛错（响亮失败，不损坏）。**注意时机**：活跃写句柄的 `read()` 走内存 `primed`、不重读文件（`:67-68`、`:93-99`），所以这一击落在**重开/新句柄冷读**时 | `:1078-1113`（条数只在成功解码后 +1）、`:103` |
| **动 header 身份字段** | ① `assertStoredIdentity` 用 header 的 **id + cwd** 反推该会话**应有的产物路径**并要求与实际路径一致（不一致再用 `sameFile` 兜底）（`:3218-3229`、`:3241`）；② `assertStoredId` 要求 header 的 `id` 等于读取方请求的 id（`dsh-session-persistence/lib/index.js:157-159`）；③ 文件名里的版本号必须与 header 的 `version` 一致，且 header 必须已被还原到当前格式版本（`:2909`、`dsh-session-persistence/lib/index.js:165-167`） | 打开/读取直接报 `corrupt session log ...` 或版本不匹配，会话打不开 | `:3218-3229`、`:2909`、`:2677` |
| **改行数（增/删行）** | 若同时重排 `seq`，则 `cursor` 与文件不再一致 → 下次 append 的连续性断言报错（**服务端已不损坏，但该会话从此写不进去**）；若只删不排，则解码条数下降 → 收缩守卫（同上，落在重开时）。另：**插入**行会让后续每个 `seq` 与行号错位，读取端的密集性校验会先拒绝 | 报错 / 写不进去 | `:225`、`:103` |
| **zstd 编码的日志** | 行与帧边界耦合：`tornTruncateTo` 是**最后一片不完整帧的起始字节**（`:2847`），且「完整帧内出现断行」直接判损坏（`:2821`） | 帧边界一动就整片不可解 | `:2821`、`:2835-2849` |

> [!danger] 为什么「尾帧残缺」是这里唯一真正的静默杀手
> 其余分支都会抛错——报错是可恢复的，用户看得见。尾帧截断**不报错**：它只是在下一次追加前悄悄少写入/多丢弃一批事件，等到有人察觉时，原始字节早已不在。**任何原地改写方案都必须先证明「文件末尾没有残缺帧」**，或者干脆先修复尾帧再改写。

---

## 五、并发与写入顺序：为什么必须是「复查 → 截断 → 写 → 验长度」

活跃会话仍在追写。一次「读出全部 → 改写 → 写回」的序列里，真正的窗口有**三段**：

```
T0 读完（拿到 bytes + stat 指纹）
   └─ 窗口 A：还没拿到写句柄，别的写者可以追写 ── 必须复查
T1 open('r+') 拿到 fd
   └─ 窗口 B：fd 到手、还没写 ── 修订复查要放在这里之后
T2 ftruncate → write → fsync
   └─ 窗口 C：write syscall 内部被打断 ── 无法关闭，见下
```

| 动作 | 为什么必须这样 | 证据 |
|---|---|---|
| **open 之后再复查一次修订指纹** | 从「读完」到「拿到 fd」之间可能已被追写；不复查就会把新事件当垃圾覆盖 | 修订令牌契约 `dsh-session-persistence/lib/types/index.d.ts:139-144`（「相等的修订可视为日志未变」）；指纹字段与句柄自用备忘**完全相同**（`dsh-session-persistence-jsonl/lib/index.js:2211-2219`），所以可以直接复用同一实现。工程实证见下文「既有验证」 |
| **`ftruncate` 必须在 `write` 之前** | 输出比原文短时，先截断再写：若在窗口 B 内死掉，文件是**旧日志的前缀**（读取端本来就容忍崩溃尾），而不是「新头 + 旧尾」的混合体 | `dsh-session-persistence/lib/types/index.d.ts:82-84`（「残缺物理尾永不返回给读者，由写路径在首次追加前截断」） |
| **长度变化时必须检查写入返回值** | `write` 可能短写。必须循环写直到写完并核对累计字节数，否则留下的是新前缀+旧尾巴 | — |
| **写后复查文件长度** | 长度**大于**预期说明期间有并发追加；此时应报错并**保留**追加内容，绝不能再截断吃掉它 | — |

> [!note] 顺序上的一处容易搞反
> 后端自己的 write-open 顺序是「先占进程内写者 → 取跨进程租约 → **然后才读日志**」（`dsh-session-persistence-jsonl/lib/index.js:2371`、`:2376`、`:2377`）。那是**打开会话**的顺序，不是「改写他人日志」的顺序。改写方不在这个写者身份里，所以只能靠 §五 的指纹复查自证没有并发——**不要**把后端的三步顺序当成改写方案的模板。

> [!bug] 残留窗口：写入 syscall 本身被打断
> `write(2)` 对较大缓冲区不是原子的。若进程在写入过程中死亡，留下的是「新前缀 + 旧尾巴」的混合体——**这是原地覆盖方案的固有性质，任何顺序调整都关不掉它**。要彻底消除只能改成「写临时文件 → 原子改名安装」，但那就不再是「活跃句柄下的原地改写」了。
> 实践取舍：先把「截断后死」这个更常见、后果更可控的窗口降级为「可容忍的短尾」，如实承认另一个窗口存在，不要声称已完全关闭。

> [!success] 既有验证（真实读取端判据）
> 上述顺序（open 后复查修订号 → 先截断后写 → 校验写入字节数 → 复查文件长度 → fsync）在会话脱敏工程中已被实现并用**真实** `JsonlSessionPersistence.open()` 作为判据实测：并发追加不被吃掉且报错；「截断后崩溃」的状态仍能被真实后端打开（属可容忍的短尾，而非硬损坏）。证据存档见该工程 `docs/reports/fix/REPORT-FIX-zh.md`（本地仓库，非本 Vault）；该报告同时明确把「写入 syscall 被打断」列为**未关闭的残留窗口**，与本节的判断一致。

---

## 六、锁的真实覆盖范围（它保护不了你的改写）

| 平台 | 写租约是什么 | 位置 |
|---|---|---|
| POSIX | `session.lock` 上的**非阻塞 `flock(2)`**（内核锁 inode）；锁后校验 inode 仍是该路径的文件，否则重试 | `dsh-session-persistence-jsonl/lib/types/lease.d.ts:1-27`；`:665-711` |
| Windows | 由锁文件路径派生的**命名内核信号量**（计数 1）——**不是文件锁、不碰文件系统** | `dsh-session-persistence-jsonl/lib/types/win32.d.ts:21-32`；`:672-684` |

三条必须记住的性质：

1. **取锁时机是 write-open**：打开既有产物写句柄时立刻取（`:2371-2376`）；新建会话则推迟到首次真正落盘前（`:247-249`）。因此「有锁」等价于「本进程持有一个写句柄」。
2. **它只排斥其他 DSH 写者**：争用映射为 `SessionAlreadyOwnedError`；进程死亡即由内核释放，没有超时抢锁（刻意设计，避免抢走卡住的写者而撕裂日志）。
3. **它完全不保护「被带外工具编辑的文件」**：锁的对象是**目录里的锁文件/内核对象**，不是日志内容。任何在锁外直接改写日志的方案，**不会**被这个锁拦住，也不会被它告知有并发写者——这就是为什么 §五 的修订复查是**唯一**的并发防线。

> [!warning] 一个自伤的坑
> POSIX 上删掉 `session.lock` 会**丧失互斥**（锁的是 inode，不再是该路径的文件）。Windows 侧压根没有锁文件。所以「清理锁文件」不是安全操作。

> [!note] 官方已知局限（直接读自后端 README 的限制章节）
> ① POSIX 用的是**建议锁** `flock`，在某些网络文件系统（NFSv3）上不可靠；② Windows 的命名信号量名**属于单个登录会话**——跨登录会话（例如服务/session 0 与交互式会话）不见得互相排斥。两条都进一步说明：**不要把锁当作改写安全性的前提**。

> [!info] 顺带一个对「改写后清理」有利的事实
> 该后端的已知限制里明确写着「**没有任何东西会删除会话文件**——日志在 `root` 下累积直到被外部移除，seam 不提供删除 API」。也就是说「脱敏/清理」本质上就是**带外维护**，本来就没有第二种做法。

---

## 七、派生缓存的不对称：改写后必须主动清理

派生缓存**不比对日志字节**。它的失效键是**生命周期身份 + 每行水位**，且**里面没有任何内容摘要**——没有哈希、没有字节数、没有 mtime、也没有事件总数（对两个包做全文检索：`revision|mtime|createHash|sha256|digest|byteLength|checksum` 零命中）：

| 键的组成 | 来源 |
|---|---|
| `formatVersion`、`createdAt`、`cwd`、`isSeeded`、`inheritedEventCount` | header 的不可变字段（`dsh-session-projection-cache/lib/index.js:48-54` 定义，`:361-371` 构造，`:379-389` 逐项比对）。注意 `formatVersion` 是**日志格式代际**，**不是**内容修订号——`SessionHeader` 里根本不存在内容修订令牌 |
| 每行 `ver` | 单元 `stateVersion`，是**代码常量**（`dsh-session-projection/lib/index.js:201`） |
| 每行 `seq` | 「最后折叠到的事件 seq」水位，说明「有多旧」，**不代表「对」**（`:202`） |

**关键代码是折叠时的跳过规则**：

```js
const usable = row !== void 0 && row.ver === def.stateVersion && row.seq >= beforeBase && row.seq <= endSeq;
let state = usable ? def.stateSchema.parse(row.val) : def.init(...)
const startIndex = (usable ? row.seq : beforeBase) - baseSeq + 1;   // 只重放 row.seq 之后的事件
```

（`dsh-session-projection/lib/index.js:287-319`；注释见 `:263-277`）

**没有任何读取路径把 `val` 与日志对照**：命中时只做 `stateSchema.parse(row.val)`（`:251-259`），随后按零 I/O 路径供出（`dsh-session-projection-cache/lib/index.js:188-192`、`:221-235`）。

于是出现**严格的不对称**：

| 改写形态 | 缓存行为 | 后果 |
|---|---|---|
| **行数/`seq` 不变的行内文本替换** | 身份键的五个字段全是不可变元数据、每行 `ver` 是常量、每行 `seq` 假设不变 → 行判定 `usable` → **跳过**该行水位之前的所有事件重放（`:297-302`） | 缓存继续供出**改写前**折叠出的值；**日志赢不了缓存** |
| **日志变短（尾行被删）** | `seq <= endSeq` 不成立 → 行不可用（`:295`） | 新末端之后的行**会**被作废：冷读路径以 `baseSeq = 0` 调用（`dsh-session-projection-cache/lib/index.js:282-289`），不可用的行直接从 `init` 重折、整条记录被**整体覆盖写回**。`baseSeq > 0` 时才抛错要求「从 seq 0 重读」（`:296`），而该抛错路径在本安装树里**没有调用点** |

> [!danger] 因此：脱敏/改写之后不清缓存 = 没脱敏
> 会话列表等「零 I/O」路径直接从缓存按 header 身份取值（`dsh-session-projection-cache/lib/index.js:168-192`、`:245-253`），**不读日志、也不与日志比长度**。行内文本改写后这些路径会继续显示旧文本（即被移除的内容）。

### 要删什么，谁会重建

| 目标 | 路径（占位符形式） | 是否必然存在 |
|---|---|---|
| 单会话的缓存文档 | `$DSH_HOME/storages/session_projcache/sessions/<session-id>.json` | 是（每个有检查点的会话一份） |
| 被判定为非法而挪走的旁支 | 同目录 `<session-id>.json.bak.<YYYYMMDDHHmm>`（`dsh-storage-json/lib/index.js:473-484`） | 否，只在发生过「坏记录挪走」时出现 |

> [!info] 本机实测的目录形态（仅列目录项，未读取任何文档内容）
> `$DSH_HOME/storages/` 下只有 `session_projcache/` 一个域目录；其下就是 `sessions/` 表目录 + 若干 `<id>.json`（格式为缩进 JSON，一条会话一份文档，**不是** sqlite、也不是 zstd 日志）。
> **这里没有 `global.json`，而且也不该有**：该域只声明了 `sessions` 一张表，不含 global 槽（`dsh-storage-json/lib/index.js:343-347`、`:491` 只在 `hasGlobal` 为真时读写它）。所以清理范围就是 `sessions/*.json`（含 `*.json.bak.*`），**不要去动域目录以外的任何东西**。

**谁会重建它**：检查点在三个强制点 + 一个节流阈值上写入（`session/created`、`turn/end`、`session/disposed`，以及事件数/时间阈值；本机默认值 `writeEveryEvents: 200`、`writeIntervalMs: 5000`，见 `dsh-base/cordis.patch.yml:151`、`:165-166`）；冷读路径也会把重新折叠后的整条记录**整体覆盖写回**（`dsh-session-projection-cache/lib/index.js:282-289`）。删除整条记录＝该会话回退为一次更长的冷读，**不会**让会话打不开（缓存是折叠捷径而非权威，`:112-118`；删掉目录按空域处理，`dsh-storage-json/lib/index.js:316-320`）。

> [!warning] 缓存只增不删，是设计如此
> 该域**没有删除行为**：写入是「整条记录替换」，读是「按身份取」，没有任何清理/淘汰路径（README 明确记「No eviction or retention surface … pruning stored checkpoints is out-of-band maintenance」）。所以「改写完由系统自己收敛」这个假设不成立——**清理由改写方负责**。

- 布局与文件名依据：`per-record` 布局 = `<root>/<表名>/<key>.json`（`dsh-storage-json/lib/index.js:60-62`、`:275-277`、`:395`）；域声明 `layout: "per-record"`、`version: 7`、`invalidRecords: "backup-and-skip"`（`dsh-session-projection-cache/lib/index.js:89-101`）。版本戳不在可接受集合内时，该记录**被丢弃而非迁移**（`dsh-storage-json/lib/index.js:155`）。

---

## 八、实现检查清单

> [!danger] 前四条是硬前提，缺一条就不要动文件

**A. 前置条件**

1. **证明尾部完整**：文件最后一帧/最后一行必须是完整提交（无 torn tail）。有残帧先走读取端的修复路径，别在残帧上做原地改写（§四.2）。
2. **锁定改写范围**：行数不变、每个 `seq` 不变、header 行不参与替换。任何增删行都必须走「写临时文件 → 原子改名」，而不是原地覆盖。
3. **确认是当前代产物**：改写的是当前 generation 的日志文件，不是历史代（版本迁移产物）。
4. **拿到隔离副本**：改写前留一份含原文的备份，且**失败文案里必须点名它**。

**B. 写入顺序（顺序本身就是正确性）**

5. 读全量字节 → 记下 stat 指纹（`dev:ino:size:mtimeNs:ctimeNs`）。
6. 写出新内容到内存，校验「行数/seq/header 不变」这一条不变式。
7. `open('r+')` 拿到 fd → **立刻复查一次指纹**：不一致即中止（有并发追加），不要写。
8. 新内容更短 → **先 `ftruncate(len)` 再写**；更长 → 不要先截断（先截断会补零造洞，反而制造硬损坏），直接按长度写满。
9. 循环写直到写完，**核对累计字节数 == 期望长度**；然后 `fsync`。
10. 写后复查文件长度：**精确等于**期望长度才算成功；更长说明期间被追写 → 报错并**保留**追写内容。

**C. 收尾**

11. **清理派生缓存**：删 `$DSH_HOME/storages/session_projcache/sessions/<session-id>.json`（§七）。不清理就等于没改写。
12. **告知用户必须重开会话**：内存中的 `primed` 快照、`deriveMessages` 增量缓存与派生消息都不会自动刷新；当前会话里模型与你看到的仍是**旧文本**（§二、§四.1）。
13. **告知改写是终局性的**：`seq` 不变意味着引用关系不会跟着变；被替换掉的文本不会出现在任何「回滚」路径里，只有隔离备份还留着它。

> [!question] 尚未验证的项（实现前请自行实测）
> - NTFS 上 `mtimeNs/ctimeNs` 的实际分辨率，以及「等长替换 + 同刻度写入」导致修订指纹撞车的真实概率（§三.3）。
> - 本机检查点策略的实际阈值（`writeEveryEvents` / `writeIntervalMs`）与「改写后多久缓存会自行覆盖」。**不要假设它一定会自行纠正**——按 §七 主动清理。
> - **本文写路径结论的证据来源**：`lib/index.js` 的源码阅读（本机 Node 22 安装树）+ §五「既有验证」引用的脱敏工程实测报告。我**本人没有**在本机重跑「活跃句柄下原地改写」的端到端实验；POSIX 的目录 fsync 与 `flock` 分支只有代码级阅读（本机为 Windows）。

---

## 九、相关

- [[DSH会话日志格式与读取端约束]] — header 行/事件行/`seq` 密集性/引用字段的合法性规则（本文的「能不能被读取端接受」那一半）
- [[DSH会话脱敏插件缺陷档案]] — 活跃改写必须避开的失败模式清单（并发覆盖、静默丢事件、缓存未清）
- [[DSH插件与Hook开发最佳实践]] — Cordis 插件/服务/事件基础（本文涉及的服务为 `ctx.sessionPersistence`、`ctx.sessionProjectionCache`）
- [[AI-Links-KB-Home]] — 本子库 MOC
