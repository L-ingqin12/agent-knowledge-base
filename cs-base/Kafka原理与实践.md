---
title: Kafka原理与实践
aliases: [kafka, 消息队列, mq]
tags: [cs/db, cs/system, cs]
created: 2026-08-26
updated: 2026-09-13
status: review
source: Apache Kafka 官方文档与设计文档口径；KRaft/新消费者语义版本敏感处标待确认
fetched_at: 2026-08-26
---

# Kafka 原理与实践

> [!abstract] 定位
> 补齐消息队列方向：为什么"日志"是消息队列的正确数据结构、分区/副本/ISR 的可靠性与顺序保证边界、消费组再平衡的真实代价、精确一次的实现链。选型对照 [[Redis原理与实践]](轻量流) 与 [[数据库原理与调优]](LSM 同源思想)。

See also: [[CS-KB-Home]] · [[高并发系统设计]] · [[MySQL-InnoDB精要]] · [[LLM推理部署与量化]]

## 一、核心抽象：日志即一切

```
topic → partition(有序追加日志) → segment 文件(1GB 滚动) + 稀疏索引(offset→position)
消费 = 消费者自己维护 offset 游标(存在 __consumer_offsets 内部 topic)
```

**为什么用追加日志而不是 B+ 树队列**：
① 顺序写磁盘 ≈ 内存写速度（[[数据库原理与调优]] §一 LSM 同源论证）
② 读随机性由 OS page cache 兜底，热数据天然在内存——Kafka 不自己管缓存，把内存管理还给内核（对比 Redis 自管、MySQL buffer pool 自管的三种哲学）
③ 零拷贝 sendfile 直接页缓存→网卡（[[操作系统八股]] §六零拷贝三方案），这是 Kafka 吞吐神话的物理来源
④ 保留策略按时间/大小删旧 segment 而非逐条删——免碎片

## 二、分区与副本：可靠性参数的真实含义

```
replication.factor=N; 每个 partition 一个 leader 多个 follower
ISR(in-sync replicas): 落后 ≤ replica.lag.time.max.ms 的副本集合
acks=0   不等确认      — 可能丢, 最快(日志类)
acks=1   leader 落盘即答 — leader 挂且未同步则丢
acks=all + min.insync.replicas=2 — ISR 至少2份才答, 不满足抛错(拒绝服务优于丢数据)
unclean.leader.election.enable=false — 禁止非 ISR 副本当 leader(一致性优先于可用性)
    KRaft 下动态改为 true 不会立即触发选举: 需等 unclean leader election 线程(默认 5 分钟)或手动 kafka-leader-election.sh
```

> [!warning] 更正（2026-09-13）：原写 `unclean.leader.election=false`——漏了后缀，实际配置键是 `unclean.leader.election.enable`（默认 false）。依据：https://raw.githubusercontent.com/apache/kafka/4.0/clients/src/main/java/org/apache/kafka/common/config/TopicConfig.java

**顺序保证的精确边界**：仅保证**单分区内**有序。要业务有序必须按 key 路由（同 key 进同分区）——但 **key→分区映射只由分区数决定**（`partitionForKey = murmur2(key) % numPartitions`），所以只有**改变分区数**（如 `kafka-topics.sh --alter --partitions`）才会打乱同 key 落点；纯**副本重分配(reassign)** 只搬副本、不改变分区数、也不改变映射。全局有序与水平扩展不可兼得，这是架构层硬约束。

> [!warning] 更正（2026-09-13）：原写「但 key 分区在扩容(reassign)后会变」——术语错位，把「改分区数」与「搬副本」混为一谈。依据 Kafka 4.0 `BuiltInPartitioner`：https://raw.githubusercontent.com/apache/kafka/4.0/clients/src/main/java/org/apache/kafka/clients/producer/internals/BuiltInPartitioner.java

## 二·补、HW / LEO / leader epoch：可靠性讨论的物理基础

```
LEO(log end offset) = 该副本日志末端(下一条待写位置)
HW(high watermark)  = ISR 中的最小 LEO —— 消费者只能读到 HW 之前的消息
HW 推进条件         = acks=all + min.insync.replicas 满足 → follower 拉取进度前移
leader 切换         = follower 用 OffsetsForLeaderEpoch 定位截断点; Fetch 带 leader epoch
                      不一致则返回 FENCED_REPLICA(KIP-320); 消费者可能遇 LogTruncationException
```

| 概念 | 定义 | 决定谁的行为 |
|------|------|--------------|
| LEO | 副本日志末端偏移 | 副本自身写入进度 |
| HW | ISR 中的最小 LEO | 消费者可见性上界——「只读已提交」的物理来源 |
| leader epoch | leader 任期编号（KIP-320） | 故障后的截断点定位与 fencing |

- 缺了这一层，ISR / `min.insync.replicas` / `acks=all` 的讨论就没有落点：「不丢已提交数据」是一条链 = acks 与 ISR 决定 **HW 何时推进** → HW 决定**消费者能读到哪** → epoch 决定故障后**哪些数据被判为未提交而被截断**。
- KIP-320 的立论前提即「HW 以下的数据永不丢失」，`OffsetsForLeaderEpoch` 正是据此定位新 leader 的截断点。

> 来源：https://cwiki.apache.org/confluence/display/KAFKA/KIP-320%3A+Allow+fetchers+to+detect+and+handle+log+truncation ；旁证（HW/epoch 的贯穿性）https://cwiki.apache.org/confluence/display/KAFKA/KIP-405%3A+Kafka+Tiered+Storage

## 三、消费组：再平衡的代价与治理

- 消费组内每分区只归一个消费者 → 并行度上限=分区数（**分区数规划先于消费者数量**）
- 再平衡触发：成员增减/订阅变更/心跳超时(session.timeout vs max.poll.interval 两套超时——处理逻辑太慢被踢是最常见误配)
- 代价：rebalance 期间整组停摆(stop-the-world)；世代号(generation)防僵尸消费者写旧游标
- **位移提交语义**：先处理后提交(at-least-once, 可能重) vs 先提交后处理(at-most-once, 可能丢)——幂等消费端是生产标配（去重表/Redis setnx 业务键）
- **再平衡协议两代**：① KIP-429 协作式再平衡（CooperativeStickyAssignor）自 2.4 引入、3.0 起进入默认策略列表，但仍属 **classic 协议**；② KIP-848 服务端分配器协议已于 **4.0 GA**——成员逐个**增量迁移，不整组停摆**；③ 它是 **opt-in**：需客户端显式设 `group.protocol=consumer`；4.0 里 `group.protocol` 默认仍是 `classic`、默认 `partition.assignment.strategy` 仍是 `[RangeAssignor, CooperativeStickyAssignor]`

> 来源：https://cwiki.apache.org/confluence/display/KAFKA/KIP-848%3A+The+Next+Generation+of+the+Consumer+Rebalance+Protocol （4.0 GA）；https://raw.githubusercontent.com/apache/kafka/4.0/clients/src/main/java/org/apache/kafka/clients/consumer/ConsumerConfig.java （默认 classic 与默认策略列表）

## 四、精确一次的实现链

```
producer 幂等: PID + 序列号 per partition → broker 去重(只治单会话单分区重试)
事务: transactional.id 跨分区原子写 + 消费-转换-生产回环(read_process_write) 的 exactly-once
isolation.level=read_committed: 消费者只读已提交
```

**边界诚实**：exactly-once 只覆盖 Kafka 流内闭环；对接外部系统(DB 写入)仍需业务侧幂等或两阶段——没有免费午餐。

## 五、实践速查

| 问题 | 处置 |
|------|------|
| 消费积压 | 加消费者至分区数上限→仍不够=加分区(注意 key 有序破坏)+批量拉取调优 |
| 频繁 rebalance | max.poll.interval ≥ 最大批处理耗时×安全系数；心跳线程独立 |
| 消息乱序 | 检查是否多分区写入；retry 场景开启幂等(序列号保序) |
| 延迟毛刺 | GC 停顿/页缓存争抢；`kafka-run-class` 性能工具+`perf`(对照 [[计算机组成原理]] TMA) |
| 数据丢失排查 | 先定 acks 配置与 ISR 历史(`getOffset`/under-replicated 告警) |

## 六、待确认项

> ① KRaft 模式替代 ZooKeeper 后的元数据故障恢复实测；② tiered storage 各发行版成熟度；③ Kafka Streams 与 Flink 在 Exactly-once 语义上的最新口径。

### ① 已核（2026-09-13）：KRaft 已是唯一模式，问题换成「元数据怎么恢复」

> [!warning] 更正（2026-09-13）：① 的前提取景已过期（原表述即上一行原文）——KRaft 自 3.3 生产可用，**Kafka 4.0（2025-03-18 GA）完成 KIP-500 并移除 ZooKeeper 模式**（4.0 release notes 含 Remove ZK migration code / Remove KafkaServer 等条目），ZK 已不是可选项。

- 该盯的恢复机制：**controller quorum 多数派**（元数据可用性 = 多数 controller 在线）；**`metadata.log` 的快照 + 增量重放**（先载快照，再重放其后的记录）；broker 的 `metadata.version` 支持矩阵。
- ZK 时代参数在 KRaft 下失效，别再照抄：`leader.imbalance.per.broker.percentage`、`controlled.shutdown.*` 一类只作用于 ZK 模式。
- 版本线（截至 2026-09）：4.0（2025-03-18）→ 4.1（2025-09-02）→ 4.2（2026-02-17）→ 4.3（2026-05-20）。

> 来源：https://archive.apache.org/dist/kafka/4.0.0/RELEASE_NOTES.html ；版本日期 https://endoflife.date/api/kafka.json

### ② 已核（2026-09-13）：Apache 侧 tiered storage 已 production-ready

- KIP-405 自 **Kafka 3.9** 起被标记为 production-ready，不再只是 early access——「各发行版成熟度」在 Apache Kafka 侧已有结论。
- 待核验项收窄为**托管发行版**：Confluent Cloud/Platform 与各云厂商的默认开启策略、冷层计费口径、本地保留(retention)下限，需逐一按厂商文档核对。

> 来源：https://cwiki.apache.org/confluence/display/KAFKA/KIP-405%3A+Kafka+Tiered+Storage （"marked production-ready since Kafka 3.9"）

**③ 仍未定**：Kafka Streams 与 Flink 在 Exactly-once 语义上的最新口径。

## Related

[[CS-KB-Home]] · [[Redis原理与实践]] · [[数据库原理与调优]] · [[操作系统八股]] · [[高并发系统设计]] · [[Raft与分布式协同]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §二 配置键写成 `unclean.leader.election=false`（漏后缀） | 改为 `unclean.leader.election.enable=false`，并补 KRaft 差异（动态开启不立即选举，需等选举线程默认 5 分钟或手动触发）；依据 4.0 `TopicConfig.java` |
| 纠错 | §二 写「key 分区在扩容(reassign)后会变」，把改分区数与搬副本混为一谈 | 改为「映射只由分区数决定（`murmur2(key) % numPartitions`）；只有改分区数才重映射，纯副本重分配不影响」；依据 4.0 `BuiltInPartitioner.java` |
| 纠错 | §六 待确认① 仍在问「KRaft 能否替代 ZooKeeper」 | 改写为已核结论（3.3 生产可用、4.0 移除 ZK 模式）+ 真正该盯的元数据恢复机制（controller 多数派、`metadata.log` 快照重放、ZK 时代参数失效）；依据 4.0 release notes 与 endoflife.date |
| 纠错 | §三 CooperativeStickyAssignor 停在「待确认各客户端版本支持差异」 | 改写为两代协议三段（KIP-429 仍属 classic／KIP-848 于 4.0 GA／opt-in 需 `group.protocol=consumer`，默认仍是 classic + Range 优先）；依据 KIP-848 wiki 与 4.0 `ConsumerConfig.java` |
| 纠错 | §六 待确认② tiered storage「各发行版成熟度」 | Apache 侧定为 3.9 起 production-ready（KIP-405），待核验项收窄为托管发行版的默认开启策略与计费口径 |
| 补疏漏 | 全文无 HW / LEO / leader epoch，ISR 与「消费者只读已提交」缺物理落点 | 新增「二·补」一节（LEO/HW/epoch 定义与分工表 + 截断与 fencing 链条）；依据 KIP-320 |

回链：[[CORRECTIONS]] · [[AGENTS]]
