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

回链：[[CORRECTIONS]] · [[AGENTS]]
