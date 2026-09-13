---
title: Raft与分布式协同
aliases: [raft, 分布式共识, etcd]
tags: [cs/system, cs, cs/db]
created: 2026-08-26
updated: 2026-09-13
status: review
source: Raft 论文(raft.github.io) 与 etcd 文档口径；工程实现差异处标待确认
fetched_at: 2026-08-26
---

# Raft 与分布式协同

> [!abstract] 定位
> 共识算法的"可理解版"全机制：领导者选举的任期时钟、日志复制的提交规则、安全性五约束、成员变更与脑裂边界；etcd/Raft 在本库各存储分册中的落点回连。选型方法论见 [[架构设计与方案选型]]。

See also: [[CS-KB-Home]] · [[Kafka原理与实践]] · [[容器与云原生基础]] · [[MongoDB原理与实践]]

## 一、问题定义：复制状态机为什么需要共识

```
多副本执行同一命令序列 → 状态一致。难点: 谁定顺序(主从)? 主挂了谁接? 分区时听谁的?
共识 = 让 N 个节点在【存在宕机/网络分区/消息乱序】下对"命令序列"达成一致
```

- 容错模型：**崩溃容错**(crash-stop，Raft/Paxos/ZooKeeper ZAB) vs 拜占庭(恶意节点，PBFT/区块链族)——内网基础设施默认前者
- 多数派(quorum=⌊N/2⌋+1) 是一切安全性的根：任意两个多数集必相交 → 承诺不会互相矛盾

## 二、领导者选举：任期是逻辑时钟

```
节点三态: Follower / Candidate / Leader
触发: follower 在随机超时(150-300ms 抖动)内没听到心跳 → term++ 自荐拉票
当选: 收到多数派选票(每人在一个 term 只投一票, 且候选日志不落后于自己)
心跳: leader 周期 AppendEntries(空日志即心跳) 镇压其他候选人
```

**随机化超时为什么必须**：固定超时→瓜分选票死循环；抖动使先醒者大概率收齐票。

**选举限制(日志完整性投票规则)**：投票前比较 `lastLogTerm > mine || (== && lastIndex ≥ mine)` ——保证当选者**拥有全部已提交日志**（安全性核心，比 Paxos 易读的关键设计）。

**PreVote 防扰动**：候选者先探询"能否当选"再自增任期，避免分区恢复/网络抖动时 term 暴涨踢掉健康 leader——**Kafka 4.0（KRaft）已引入该机制（KIP-996）**；etcd/TiKV 的默认开关仍需逐版本核对（见 §七①）。

> 来源：https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/

## 三、日志复制与提交

```
leader 收到写: 追加本地日志(未提交) → 并行发给 followers
   → 多数派落盘应答 → leader commit(应用状态机) → 下次心跳捎带 commitIndex 让 followers 提交
冲突处理: follower 日志与 leader 不一致 → leader 回退 nextIndex 重发覆盖(follower 无条件服从)
```

- **提交规则铁律**：只直接提交**当前任期**的条目；旧任期条目靠后续新条目间接提交（图 8 问题——防止已被复制的旧条目被新 leader 覆盖）
- ReadIndex/Lease Read：线性一致读不必走日志——leader 确认自己仍是 leader(ReadIndex) 后读状态机，省一次落盘；etcd 串行读=可能读到旧值，线性一致读=确认后读（API 参数级选择）

## 四、安全性五约束速查表

| # | 约束 | 防的事故 |
|---|------|---------|
| 1 | 选举安全：单 term 至多一 leader | 双主双写 |
| 2 | 只有日志最新的候选者可当选 | 新 leader 缺已提交数据 |
| 3 | leader 只追加不覆盖自身日志 | 已复制数据被改 |
| 4 | 日志一致性检查( prevLogIndex/Term ) | 复制流错位 |
| 5 | 当前 term 条目才可直接提交 | 图8 的幽灵提交 |

## 五、脑裂与成员变更的边界诚实

- **少数派分区不会双主**（选不出 quorum），但会**不可用**——CAP 里 Raft 选 C 弃 A：`min.insync` 类似语义，拒绝服务优于不一致
- 成员变更单步法(joint consensus 简化版)：每次只增删一节点，新旧配置各自 quorum 约束天然不相交出两套决定——运维上 etcd 的 member add/remove 必须逐台串行
- 快照+日志压缩：日志无限增长治理；安装快照也是落后过多 follower 的追平手段

## 六、本库各分册的 Raft 落点回连

| 系统 | 共识用法 | 差异点 |
|------|---------|--------|
| etcd | 原生 Raft + MVCC(B+ 类 btree) | K8s 的事实配置库；watch 机制 |
| MongoDB 副本集 | Raft 衍生(带 catchup/优先级) | [[MongoDB原理与实践]] §五选举 |
| Redis Cluster | **非 Raft**：gossip+异步复制故障转移 | 可能丢最近写入——与 Raft 族本质差异 |
| TiKV | **Multi-Raft**：单节点上管理多个 Raft 组，按 Region 切分（Region 可 split/merge） | multi-raft 分片化 |
| Kafka(KRaft) | **单一元数据 Raft 组**（controller quorum），**不是** per-region Raft | 4.0 起为唯一模式（ZooKeeper 已移除） |

> [!warning] 更正（2026-09-13）：原表把 TiKV 与 Kafka(KRaft) 塞进同一格、写成"Raft per region/per 元数据日志"，把两种形态混成了一个——TiKV 是 per-Region 的 Multi-Raft（官方 deep-dive 原文「Here Multi-Raft only means we manage multiple Raft consensus groups on one node」）；Kafka 是**单一元数据 controller quorum**，且 4.0 起 KRaft 是唯一模式。（原表述为「TiKV/Kafka(KRaft) \| Raft per region/per 元数据日志 \| multi-raft 分片化」）
> 来源：https://tikv.org/deep-dive/scalability/multi-raft/ · https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/

## 七、待确认项

> ① etcd/tikv 对 PreVote(防扰动 term 暴涨)的默认开关与调优参数（**KRaft 一侧已确定**：Kafka 4.0 起有 Pre-Vote，KIP-996，见 §二）；② witness/learner 角色在三节点变两节点的运维窗口实践；③ FlexiRaft 类变体在云厂商托管的落地情况。

> [!warning] 残余复核（2026-09-13）：三条**均仍开放**（① 只剩 etcd/TiKV 半边，KRaft 半边已在 §二 定案）。
> - ① 本机无 etcd/TiKV 可查：`command -v etcd` / `command -v tikv-server` 均未命中，也没有其源码可读，默认值无从离线取得。判据：读 etcd 源码 `server/etcdmain/config.go` 的 `--pre-vote` 标志默认值（或 etcd 官方 configuration 文档同名条目的 default 列）、TiKV 侧读其配置模板中 raftstore 的 prevote 相关项；**必须按版本分别记录**，不可跨版本套用，且要区分「有该开关」与「默认打开」两件事。
> - ② 属运维窗口实践，不是文档事实。判据：抓 etcd 官方 "Disaster recovery" 与成员管理文档（learner 用法、`member add/remove` 串行要求、移除成员时的 quorum 重算），再核对 TiKV/PD 侧的 learner 调度；三节点变两节点这种「先加后减」的窗口要给出每一步的 quorum 余量。
> - ③ 属厂商落地情况。判据：抓 FlexiRaft 原文（CIDR 2023 一带）的 evaluation/部署段，确认是否含生产规模数据；再逐个核对各云厂商托管分布式数据库（如 OceanBase/TiDB Cloud/PolarDB-X）的官方架构文档里是否有分层 quorum / 无 witness 站点式设计，没有就写「未见落地通报」，不要用「类变体」含糊带过。

> [!success] 残余复核（2026-09-13 联网轮）：**① 与 ② 已结**（①的 etcd/TiKV 半边已补齐，与 §二 的 KRaft 半边合成完整结论）；**③ 仍开放**（判据见下）。
> - **① 已结**。两边都**既有该开关、且默认打开**（即「有开关」与「默认打开」两件事都成立，且是源码默认值而非文档转述）：
>   - etcd：`server/embed/config.go` 中结构体字段 `PreVote bool \`json:"pre-vote"\``，`NewConfig()` 里 **`PreVote: true`**，命令行由 `fs.BoolVar(&cfg.PreVote, "pre-vote", cfg.PreVote, "Enable the raft Pre-Vote algorithm to prevent disruption when a node that has been partitioned away rejoins the cluster.")` 注册，故 `--pre-vote` 的默认值继承自 `true`。已核 `main` 与标签 `v3.5.21` 两处均为 `PreVote: true`。
>   - TiKV：`components/raftstore/src/store/config.rs` 中 `pub prevote: bool`，`Config::default()` 里 **`prevote: true`**，并在生成 raft 配置时映射为 `pre_vote: self.prevote`。
>   - 即：不存在「需要手工打开 PreVote」的默认状态；调优参数方面两边的可调面就是这一个布尔（etcd `--pre-vote`，TiKV `[raftstore] prevote`），其余为内部行为，按版本记录时应同时标注**取到的版本**（etcd `v3.5.21` 与 `main`、TiKV `master`）。
> - **② 已结（文档事实层面）**。etcd 官方 *Runtime reconfiguration* 与 *Disaster recovery* 给出的约束直接回答了「三节点变两节点」这个窗口：
>   - **learner（非投票成员）自 etcd v3.4 起支持**，官方推荐的三步是：`etcdctl member add --learner` → 用新成员表启动该成员 → `etcdctl member promote` 提升为投票成员；**提升有前置校验**——「Only after its raft log has caught up to leader's can learner be promoted to a voting member」，未追平则 promote 失败。
>   - 官方同时明确：**「It is highly recommended to always have a cluster size greater than two in production. It is unsafe to remove a member from a two member cluster. The majority of a two member cluster is also two.」** 且移除过程中一旦出错，「the cluster might not be able to make progress and need to restart from majority failure」。
>   - 由此该窗口的 quorum 余量可**直接算出**（按文档给出的 (N-1)/2 规则）：**3 → 2 的窗口内 quorum 恒为 2，余量为 0**——即在「已移除一个成员、尚未补入新成员」的整个区间里，任何**再一台**故障即永久失去 quorum。安全做法是官方推荐的**先加后减**：先以 learner 加入第 4 台并 promote（4 成员 quorum=3，此时减一台仍剩 3 台在线、余量 1），再移除待下线的那台，使集群回落为 3 台。
>   - 另有默认开启的保护：**`-strict-reconfig-check`（默认 enabled）**会拒绝会让「已启动成员数少于重配置后集群 quorum」的重配置请求——这正是防「新成员配错 peer URL 反把 quorum 拖没」的机制（文档明确该风险源自新成员即使不可达也被计入 quorum）。
>   - 需要更正的一点：「**witness**」在 etcd 官方文档中没有对应角色（仅有 learner / non-voting member 这一种非投票成员），本条原先把 witness 与 learner 并列成两个角色，应改为「learner」单角色叙述。
> - **③ 仍开放**（判据收紧，本条未在联网轮取到可定论的材料）：需 (a) FlexiRaft 原文的部署/evaluation 段（确认是否含**生产规模**数据还是仅模拟/仿真）与 (b) 逐家云厂商托管分布式数据库官方架构文档中的分层 quorum 设计痕迹。若两家都取不到，结论应写「官方文档中未见落地通报」，**不得**用「类变体」含糊替代。
> 依据：https://github.com/etcd-io/etcd/blob/main/server/embed/config.go 与 https://github.com/etcd-io/etcd/blob/v3.5.21/server/embed/config.go ；https://github.com/tikv/tikv/blob/master/components/raftstore/src/store/config.rs ；https://etcd.io/docs/v3.6/op-guide/runtime-configuration/ ；https://etcd.io/docs/v3.6/op-guide/recovery/ （取回于 2026-09-13）

> [!success] 残余复核（2026-09-13 联网轮）：③ **已结**。原文与云厂商两侧都取到官方材料，且把「有没有落地」与「有没有生产规模数据」拆开：
> - **FlexiRaft 原文：是生产论文，但公开的量化结果是台架微基准**。出处 **CIDR 2023**（program 页署名为 Meta Platforms 的 Ritwik Yadav / Anirban Rahut；论文 PDF 见下）。原文自述「This paper describes the changes we made to Raft for supporting quorum flexibility and the **lessons learned from the production deployment** of these changes.」，背景交代「MySQL is the most popular transactional datastore deployed at Meta with a storage footprint in the order of **petabytes**」。但实验节是受控台架——**「2 million transactions generated by our microbenchmark」**，机器为双路 Xeon Gold 6138 + 256GB。故 **「已落地」= 是（Meta 生产）**；**「生产规模数据」= 论文给的是微基准，不是生产流量口径**。
> - **云厂商侧：确有「非对称 quorum 参与」的同族设计，但都不以 FlexiRaft 命名、也不暴露 FlexiRaft 式参数**：
>   - **PolarDB-X（阿里云官方文档）**：X-Paxos 分四角色，其中 **Logger「only for saving log information and participating in the leader election」**、**Learner「only receives log information … does not participate in the leader election」**——即**投票权分层**，这是本条要找的「分层 quorum / 非全票成员」的直接官方证据。
>   - **OceanBase（官方文档）**：区分 **Paxos 副本**（全功能，「can constitute a Paxos group and participate in elections」）与**非 Paxos 副本**（只读副本，「cannot constitute a Paxos group or participate in elections」）——同为「部分成员不投票」的设计。
>   - **TiDB Cloud：未取到**。所查官方部署文档中 `witness` / `learner` / `quorum` / `voter` **全部零命中**，官方索引里也无 witness 专页（仅在文档仓 PR 中见到 `enable-witness` 一类改动，**未取得正式发布页，故不作依据**）。
>   - **Amazon Aurora：未取到**。当前官方 RDS/Aurora 用户指南中**没有** quorum 表述；「4/6 quorum」只出现在一份 2019 年的 AWS 托管演示 PDF 中，**属演示材料而非文档承诺，不采信**。
> - 本条最终口径：**FlexiRaft 本身在 Meta 有生产部署（原文自述），但公开量化结果是台架微基准；「分层 quorum / 非全票成员」这一族思想在云厂商托管库中确有落地（PolarDB-X X-Paxos、OceanBase），但均未以 FlexiRaft 命名，也未暴露 FlexiRaft 式 quorum 参数面**。
> 依据：https://www.cidrdb.org/cidr2023/program.html ；https://www.cidrdb.org/cidr2023/papers/p83-yadav.pdf ；https://doc.polardbx.com/en/features/topics/x-paxos.html ；https://github.com/oceanbase/oceanbase-doc （V4.3.4 分区副本类型页）（取回于 2026-09-13）

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | §六 表格把 TiKV 与 Kafka(KRaft) 混成一格、写成"Raft per region/per 元数据日志" | 拆成两行：TiKV = per-Region Multi-Raft；Kafka = 单一元数据 controller quorum（4.0 起唯一模式），保留原表述于更正块；依据 [TiKV Multi-Raft](https://tikv.org/deep-dive/scalability/multi-raft/) / [Kafka 4.0 公告](https://kafka.apache.org/blog/2025/03/18/apache-kafka-4.0.0-release-announcement/) |
| 补疏漏 | §七① 把 PreVote 整体挂"待确认" | §二 补 PreVote 机制说明并确定 KRaft 一侧（KIP-996，Kafka 4.0）；§七① 收窄为 etcd/TiKV 逐版本核对；依据 Kafka 4.0 公告 |
| 残余复核 | §七① etcd/TiKV 的 PreVote 默认开关与调优参数（KRaft 半边已定） | 判定**仍开放**：本机无 etcd/TiKV 二进制与源码（`command -v etcd`/`tikv-server` 均未命中），默认值不可离线取得；判据=读 etcd `server/etcdmain/config.go` 的 `--pre-vote` 默认值或官方 configuration 文档 default 列、TiKV 配置模板 raftstore 侧对应项，按版本分别记录 |
| 残余复核 | §七② witness/learner 在三节点变两节点的运维窗口实践 | 仍开放：属运维实践，非文档事实；判据=etcd 官方灾难恢复与成员管理文档（learner 用法、`member add/remove` 串行、移除成员时 quorum 重算）并给出每步 quorum 余量 |
| 残余复核 | §七③ FlexiRaft 类变体在云厂商托管的落地情况 | 仍开放：判据=抓 FlexiRaft 原文的部署/evaluation 段，再逐家核对托管分布式数据库官方架构文档是否有分层 quorum 设计；无则明确写「未见落地通报」 |
| 残余复核（联网轮） | §七① etcd/TiKV 的 PreVote 默认开关（KRaft 半边已定） | **已结**：两边均「有开关且默认打开」——etcd `server/embed/config.go` 的 `NewConfig()` 中 `PreVote: true`（`main` 与 `v3.5.21` 均如此，`--pre-vote` 标志默认值继承自它）；TiKV `components/raftstore/src/store/config.rs` 的 `Config::default()` 中 `prevote: true`。依据：https://github.com/etcd-io/etcd/blob/main/server/embed/config.go ；https://github.com/tikv/tikv/blob/master/components/raftstore/src/store/config.rs |
| 残余复核（联网轮） | §七② witness/learner 角色在三节点变两节点的运维窗口实践 | **已结（文档事实层）**：etcd v3.4 起支持 learner，官方三步为 `member add --learner` → 启动 → `member promote`，且 promote 需 raft log 已追平 leader；文档明写「不建议生产用两台成员」「从两成员集群移除成员不安全（两成员集群的多数派也是 2）」「移除过程出错可能需按 majority failure 恢复」；`-strict-reconfig-check` 默认开启。据此按 (N-1)/2 算出 **3→2 窗口 quorum 余量为 0**，安全路径是先加 learner 凑到 4 台再减。另更正：etcd 官方无 witness 角色，只有 learner。依据：https://etcd.io/docs/v3.6/op-guide/runtime-configuration/ |
| 残余复核（联网轮） | §七③ FlexiRaft 类变体在云厂商托管的落地情况 | 仍开放：联网轮未取得可定论材料，判据收紧为 (a) FlexiRaft 原文部署/evaluation 段是否含生产规模数据、(b) 逐家云厂商托管库官方架构文档是否有分层 quorum 痕迹；两者皆无则写「官方文档中未见落地通报」 |
| 残余复核（联网轮） | §七③ FlexiRaft 类变体在云厂商托管的落地情况 | **已结**：FlexiRaft 为 CIDR 2023 / Meta 的生产论文（原文自述「lessons learned from the production deployment」），但量化结果为台架微基准（「2 million transactions generated by our microbenchmark」）；云厂商侧取得同族设计官方证据——**PolarDB-X X-Paxos 的 Logger（参与选举、只存日志）/ Learner（不参与选举）**、**OceanBase 的 Paxos 副本 vs 非 Paxos 只读副本**；TiDB Cloud 与 Aurora 均**未取到**（Aurora 的「4/6 quorum」仅见于 2019 年演示 PDF，不采信）。结论：FlexiRaft 本身有生产部署，分层 quorum 一族在托管库有落地，但均未以 FlexiRaft 命名。依据：https://www.cidrdb.org/cidr2023/papers/p83-yadav.pdf ；https://doc.polardbx.com/en/features/topics/x-paxos.html |

回链：[[CORRECTIONS]] · [[AGENTS]]

## Related

[[CS-KB-Home]] · [[Kafka原理与实践]] · [[容器与云原生基础]] · [[MongoDB原理与实践]] · [[Redis原理与实践]] · [[架构设计与方案选型]]
