---
title: MongoDB原理与实践
aliases: [mongo八股, MongoDB进阶]
tags: [cs/db, cs]
created: 2026-08-26
updated: 2026-09-13
status: review
source: MongoDB 官方手册（8.x 口径：LTS 8.0 支持至 2029-10-31，Rapid 8.1/8.2/8.3；6.0 已于 2025-07-31 EOL）；版本相关行为按生效版本标注
fetched_at: 2026-08-26
---

# MongoDB 原理与实践

> [!abstract] 定位
> 文档型数据库纵深：BSON/文档模型取舍、WiredTiger 存储引擎(MVCC+COW B 树)、索引体系(ESR 法则)、聚合管道、副本集与分片。与关系型的边界判断放在最后——选型不是站队。

See also: [[CS-KB-Home]] · [[MySQL-InnoDB精要]] · [[Redis原理与实践]] · [[向量数据库与检索]]

## 一、文档模型

- BSON 二进制 JSON：额外类型（ObjectId/Date/Decimal128/二进制）；单文档硬上限 **16MB**
- ObjectId 12 字节 = 4B 时间戳+5B 随机(进程级)+3B 自增计数 → 天然大致有序可做粗排序
- 嵌入 vs 引用决策：**一起访问+有界增长→嵌入**；无限增长或多方共享→引用+$lookup；反范式冗余要写侧同步策略配套
- Schema 校验(`$jsonSchema`)：灵活≠无纪律，关键字段仍应约束

## 二、WiredTiger 引擎机制

| 机制 | 内容 | 与 InnoDB 差异 |
|------|------|----------------|
| MVCC | 快照隔离，写不就地改页而是**COW 新页**，checkpoint 时压实 | InnoDB 原地更新+undo 链；WT 无 undo 段概念 |
| Journal | 压缩 WAL(snappy)，checkpoint(默认 60s) 落稳定版；崩溃恢复三步=定位最后 checkpoint → 在 journal 中匹配其标识 → 重放其后操作；journal 单文件约 100MB 滚动，checkpoint 默认上限 2GB | 双"l"语义靠 journal+checkpoint 组合；官方明确磁盘预留不足会让 mongod 崩溃，容量规划要把 journal+checkpoint 一起算 |
| 压缩 | 块压缩 snappy/zstd + 索引前缀压缩 | 空间友好是 Mongo 实测优势项 |

> 来源：https://raw.githubusercontent.com/mongodb/docs/master/source/core/journaling.txt （恢复流程、journal ≈100MB、checkpoint 默认 2GB、"the MongoDB server will crash"、默认 snappy 压缩）

- 缓存：WT Cache 默认 ~(RAM-1GB)/2，**与 OS page cache 分工**——容量规划双池并看

## 三、索引体系

- 复合索引 **ESR 法则**：Equality → Sort → Range 排列字段序；违反则内存排序
- 特殊族：multikey(数组自动展开)/TTL(过期删除后台任务)/partial(条件子集)/wildcard(异构文档)/text/2dsphere
- `explain("executionStats")` 判读：COLLSCAN 全扫告警 / IXSCAN / totalDocsExamined vs nReturned 比值≈扫描效率；`$indexStats` 找僵尸索引

## 四、聚合管道要点

- `$match/$sort` 尽量前置吃索引；`$group` 内存上限仍是 100MB，但**自 6.0 起 `allowDiskUseByDefault` 默认为 true**——`$group/$sort/$bucket` 等需要更多内存的管道阶段会自动写临时文件；要禁止落盘须显式 `allowDiskUse:false` 或把该参数设为 false（只有此时才报错）。`$search` 在独立进程运行，不受此 100MB 限制
- `$lookup` 即左外连接——大集合互 join 性能差，属建模失败信号而非调优对象
- `$facet` 单次多分支输出仪表盘场景利器

> [!warning] 更正（2026-09-13）：原写「`$group` 内存上限 100MB 需 `allowDiskUse`」——100MB 阈值本身仍成立，但「必须手动开 allowDiskUse」自 MongoDB 6.0 起已过期（默认即自动落盘）。
> 来源：https://raw.githubusercontent.com/mongodb/docs/master/source/includes/fact-agg-memory-limit.rst ；版本支持期 https://endoflife.date/api/mongodb.json

## 四·补、ESR 与 explain 走读（代码级）

### ESR 组装实例
查询：`db.orders.find({user_id: u, status: "paid"}).sort({created_at: -1})`

```
E(quality) → S(sort) → R(range) 的顺序推演:
  user_id 等值 → 放最前(E)
  created_at 排序 → 第二(S): 等值字段之后紧跟排序字段,
                    索引天然按 user_id 内的 created_at 有序 → 免内存排序
  status 过滤 → 最后(R): 若放第二, 则 created_at 在索引里不再连续, sort 需内存 TOP-K
最终: { user_id: 1, created_at: -1, status: 1 }
     (status 挪到末尾仍可被 ISCAN 过滤; 若 status 基数极低可考虑部分索引 partialFilter)
```

**反面教材**：`{status:1, user_id:1, created_at:-1}`——status 只有 3 个取值，索引前缀区分度≈无，等于全索引扫。

### explain("executionStats") 判读模板
```
winningPlan: FETCH←IXSCAN{user_id,created_at}   ✓ 走了目标索引
totalKeysExamined: 42   totalDocsExamined: 42   nReturned: 42
                       ↑ 三数相等=完美比率; keys/docs 远大于 returned = 扫描浪费
executionTimeMillis + stage 里出现 SORT(内存排序) / COLLSCAN = 立刻加索引或改查询
```
健康线：`keysExamined ≈ docsExamined ≈ nReturned`（1:1:1）；分页场景配合范围查询避免 skip 深翻页（与 [[数据库原理与调优]] §七 keyset 思想同源）。

## 五、副本集与分片

- oplog(capped) 增量同步；选举协议 Raft 衍生(v1)：多数派 term+priority；**write concern=majority + read concern majority** 才有跨故障切换的读己之写承诺
- 因果一致性会话(causal consistency)：带 cluster time 的会话内单调读
- **retryable writes 不是「幂等重试」四个字能概括的**（原表述如此），四个边界：① 官方驱动**默认开启**，可用 `retryWrites=false` 关闭；② 只自动重试**一次**，治网络抖动/选主，不解决持续故障、也不覆盖超过 `serverSelectionTimeoutMS` 的故障切换；③ 依赖副本集/分片，**standalone 不支持**，写 `local` 库会直接报写错误（须显式关闭）；④ 官方明确存在同一写被**重复应用**的窗口，业务侧幂等键/去重表仍不可省
- 分片键三要素：高基数/低频率递增避免单调热点(自增时间戳键=永远写最后一片)；range vs hashed 权衡范围查与均匀散；chunk 迁移由 balancer 后台搬，jumbo chunk 无法迁移需拆分治理

> 来源：https://raw.githubusercontent.com/mongodb/docs/master/source/core/retryable-writes.txt （驱动默认开启、only one retry attempt、standalone 不支持、写 local 库报错、重复应用窗口）

## 六、事务边界演进（诚实版）

- 单文档原子性原生免费——建模把原子单元放进一个文档是最优解
- 多文档事务 4.0(副本集)/4.2(分片) 可用但非强项：锁持有与 oplog 压力使其适合短小补偿型操作，长事务回关系型

可验收边界（原表述只给结论，缺这些数字）：

| 边界 | 数值/事实 |
|------|-----------|
| 版本门槛 | 副本集 FCV ≥ 4.0、分片 ≥ 4.2；**standalone 不支持事务** |
| 事务寿命 | 默认 **60 秒**（`transactionLifetimeLimitSeconds`，到期即中止） |
| oplog 体积 | 事务总量上限已取消，但**每条 oplog 条目仍 ≤16MB**（事务写会跨多条 oplog 条目） |
| DDL/迁移互等 | 与 chunk 迁移、DDL 的互相等待由 `maxTransactionLockRequestTimeoutMillis` 兜底 |

> 来源：https://raw.githubusercontent.com/mongodb/docs/master/source/core/transactions-production-consideration.txt 、https://raw.githubusercontent.com/mongodb/docs/master/source/core/transactions.txt

## 七、选型对照（何时不用 Mongo）

| 场景 | 更合适 |
|------|--------|
| 强一致多实体转账/库存扣减 | 关系型(MySQL/PG) |
| 复杂多表 ad-hoc join 分析 | 数仓/ClickHouse |
| 日志事件流海量写 | LSM 族/Cassandra 或对象存储+检索层 |
| 半结构化内容管理/用户画像/物联网元数据/快速迭代业务主存储 | ✅ Mongo 舒适区 |

## 八、待确认项

> ① Query Engine(SIBE) 与列存分析能力的 GA 进度；② 分片 meta 一致性在 balancer 中断下的恢复细节；③ zstd 各 level 对 WT 写放大的实测矩阵。

> [!warning] 残余复核（2026-09-13）：三条**都还是真未决**，但 ① 里混着一个可先定的术语问题。
> - ① 的**术语部分已定**：`SIBE` 这个写法在公开来源里没有对应的 MongoDB 引擎名。库内 2026-09-13 的 C2 复核记录（`_out/kb-completion-2026-09-13/C2-verified.json`）判定它应是 **SBE（Slot-Based Execution Engine）** 的笔误，并给出官方手册专页 `mongodb.com/docs/manual/reference/sbe/`。本轮为离线复核，**未能重验该页面**，故此处只作术语订正、不把它当结论。
> - ① 的**GA 进度部分仍开放**：判据——抓 MongoDB 7.0/8.0 官方 release notes 与上述 SBE 手册页，确认 SBE 自哪个版本起成为默认执行引擎，以及分析/列存路线的产品状态（是否仍只在 Atlas 侧）。
> - ② **仍开放**：需读官方分片运维文档与 `config.version`/`config.chunks` 语义，核对 balancer 中断后 `moveChunk` 的恢复与孤儿文档回收流程。本机无 mongod（`command -v mongod` 未命中），既不能复现也不能对读源码。
> - ③ **仍开放**：属真机实验——固定数据集下对 snappy 与 zstd(level 1–19) 分别测 WiredTiger 写放大与压缩率；本机无实例，装 MongoDB 属新增依赖，按本轮范围不做。

> [!success] 残余复核（2026-09-13 联网轮）：**① 的术语与版本两问已结（列存产品状态仍未决）；② 的 config.version 语义已结（中断恢复流程仍未决）；③ 仍开放**（真机实验，判据不变）。
> - **① 术语部分已结（联网重验）**：官方手册确有该专页 <https://www.mongodb.com/docs/manual/reference/sbe/>，页标题为 **"Slot-Based Query Execution Engine"**，且页面标注 **New in version 5.1**。故第一轮「`SIBE` 是 `SBE` 笔误」的离线判定**成立**，并可补两个事实：引擎由 MongoDB **自动选择**（「MongoDB automatically selects the engine to execute the query」，eligible 查询才走 SBE，且「support for the slot-based execution engine is **version specific and actively changing**」）；**8.0 之前无法手工指定引擎**，「Starting in MongoDB 8.0, you can use query settings to specify an engine for queries」（`setQuerySettings`）。另：**时间序列的 block processing 自 8.0 起**可能被用于执行。注意引入版本是 **5.1 而非 7.0**。
> - **① 的「列存分析能力 GA 进度」仍开放**：SBE 专页通篇讲的是**行式 slot 执行引擎**，未出现列存/columnar 表述，也未回答分析能力是否仅限 Atlas——该半边本轮**未取得官方佐证**。判据收紧为：抓 MongoDB 官方 release notes 与 Atlas 文档中列式/分析路线（Atlas SQL / columnar index 一类）的**产品状态标注**，只以官方「GA / preview / Atlas-only」字样为准。
> - **② 的 `config.version` 语义已结**：官方 *config Database* 页说明——config 库为**内部库**（「The config database is internal. Applications and administrators should **not** modify or depend on its content during normal operation」）；`config.version` 集合存放当前元数据版本号，**只有一个文档**，形如 `{ "_id": 1, "minCompatibleVersion": 5, "currentVersion": 6, "clusterId": ... }`。即「靠 `config.version` 自助判断恢复状态」本身不是官方支持的运维手段——这一条应作为结论写进选型/排障口径。
> - **② 的「balancer 中断下的 meta 恢复流程」仍开放**：本轮取到的只是**孤儿文档清理**侧的可恢复语义（官方 *Sharding Balancer Administration* 页：chunk 迁移的删除阶段在 failover 下被强化，**「Orphaned documents are cleaned up even if a replica set's primary crashes or restarts during this phase」**；有 *Asynchronous Range Migration Cleanup*，balancer 可不等待当前迁移的删除阶段就开始下一块迁移；`orphanCleanupDelaySecs`、`rangeDeleterBatchDelayMS` 默认 20ms；8.2 起 `terminateSecondaryReadsOnOrphanCleanup` 控制清理期长读被终止的行为）。但「balancer 中途停止/中断后，`config.chunks` 与 `config.version` 如何收敛」这一**面向用户的分步流程**，官方未给出——判据收紧为：抓官方 balancer 停止/启动运维页与 chunk 迁移状态字段（`_waitForDelete`、`shardingStatistics.*`）文档，若能取到分步流程则结，否则按上文结论写成「官方仅提供内部库语义，不给自助恢复流程」。
> - **③ 仍开放**：判据不变——本机无 MongoDB 实例，该条是固定数据集下 snappy vs zstd(1–19) 的 WiredTiger 写放大/压缩率真机矩阵，本轮联网手段对其无效。
> 依据：https://www.mongodb.com/docs/manual/reference/sbe/ ；https://www.mongodb.com/docs/manual/reference/config-database/ ；https://www.mongodb.com/docs/manual/core/sharding-balancer-administration/ （取回于 2026-09-13）

## Related

[[CS-KB-Home]] · [[数据库原理与调优]] · [[Redis原理与实践]] · [[向量数据库与检索]] · [[高并发系统设计]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §四 写「`$group` 内存上限 100MB 需 `allowDiskUse`」——6.0 起该语义已过期 | 改为「100MB 阈值不变；6.0 起 `allowDiskUseByDefault` 默认 true、超限自动落临时文件，`allowDiskUse:false` 才报错；`$search` 不受限」；依据官方 fact-agg-memory-limit include |
| 纠错 | frontmatter `source` 停在「6.x/7.x 口径」 | 升到 8.x：LTS 8.0（支持至 2029-10-31）+ Rapid 8.1/8.2/8.3，并注明 6.0 已 EOL；依据 8.0 release notes 与 endoflife.date（附注：文档原覆盖到 7.x、现行最新 8.x，属落后一个大版本，非「两个大版本」） |
| 补疏漏 | §五 把 retryable writes 一句带过成「幂等重试」 | 拆出四条边界（驱动默认开启可关 / 只重试一次 / 依赖副本集且 standalone 不支持 / 仍有重复应用窗口）；依据官方 retryable-writes 文档 |
| 补疏漏 | §六 多文档事务只有结论、没有可验收边界 | 补边界表（FCV 门槛、默认 60s 事务寿命、单条 oplog 仍 ≤16MB、`maxTransactionLockRequestTimeoutMillis`）；依据官方事务生产考量 |
| 加厚 | §二 Journal 只写「压缩 WAL + 默认 60s checkpoint」 | 补恢复三步、journal 约 100MB 滚动、checkpoint 默认上限 2GB、磁盘预留不足会崩溃；依据官方 journaling 文档 |
| 残余复核 | §八 待确认①「Query Engine(SIBE) 与列存分析能力的 GA 进度」 | 拆两半：**术语部分已定**（`SIBE` 无对应引擎名，库内 C2 复核记录判定为 `SBE`/Slot-Based Execution Engine 的笔误并给出手册专页；本轮离线未重验该页）；**GA 进度仍开放**，判据=抓 7.0/8.0 release notes 与 SBE 手册页确认默认引擎生效版本 |
| 残余复核 | §八 待确认②「分片 meta 一致性在 balancer 中断下的恢复细节」 | 仍开放：需官方分片运维文档 + `config.version`/`config.chunks` 语义对读；本机无 mongod（`command -v mongod` 未命中），不可复现 |
| 残余复核 | §八 待确认③「zstd 各 level 对 WT 写放大的实测矩阵」 | 仍开放：属真机实验（固定数据集下 snappy vs zstd 1–19 测写放大与压缩率），本机无实例，装库超出本轮范围 |
| 残余复核（联网轮） | §八 待确认①「Query Engine(SIBE) 与列存分析能力的 GA 进度」 | **拆两半：术语与版本已结，列存产品状态仍开放**。已结部分：官方页为 "Slot-Based Query Execution Engine"（SBE），标注 **New in version 5.1**（非 7.0），引擎由 MongoDB 自动选择、8.0 起可用 `setQuerySettings` 手工指定，时间序列 block processing 自 8.0 起。仍开放部分：该页无列存/分析表述，未取得「是否仅 Atlas」的官方产品状态标注。依据：https://www.mongodb.com/docs/manual/reference/sbe/ |
| 残余复核（联网轮） | §八 待确认②「分片 meta 一致性在 balancer 中断下的恢复细节」 | **拆两半：`config.version` 语义已结，中断后收敛流程仍开放**。已结部分：官方 config 库页明确该库为内部库、不应被依赖，`config.version` 为单文档（`minCompatibleVersion` / `currentVersion` / `clusterId`）。仍开放部分：孤儿清理侧可恢复语义已有官方描述（failover 下仍会清理孤儿文档、异步 range migration cleanup、`orphanCleanupDelaySecs`、`rangeDeleterBatchDelayMS` 默认 20ms、8.2 起 `terminateSecondaryReadsOnOrphanCleanup`），但 `config.chunks`/`config.version` 在 balancer 中断后的**分步收敛流程**官方未给。依据：https://www.mongodb.com/docs/manual/reference/config-database/ ；https://www.mongodb.com/docs/manual/core/sharding-balancer-administration/ |

回链：[[CORRECTIONS]] · [[AGENTS]]
