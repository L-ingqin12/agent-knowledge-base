---
title: MySQL-InnoDB精要
aliases: [InnoDB, MySQL调优, mysql-innodb]
tags: [cs/db, cs]
created: 2026-08-26
updated: 2026-09-13
status: review
source: MySQL 8.x Reference Manual / InnoDB 引擎章节口径；参数默认值随版本核对，存疑标待确认
fetched_at: 2026-08-26
---

# MySQL InnoDB 精要

> [!abstract] 定位
> [[数据库原理与调优]] 的 MySQL 分册：Buffer Pool 内部、redo/binlog 两阶段、锁体系全貌、在线 DDL 与复制，以及可直接上手的参数与 EXPLAIN 实战。通用理论不重复，只讲 InnoDB 特有实现。

See also: [[CS-KB-Home]] · [[数据库原理与调优]] · [[Redis原理与实践]] · [[高并发系统设计]]

## 一、Buffer Pool 内部（不是普通 LRU）

- **中点插入变体**：新页插入 old 子链头部（5/8 处），驻留 `innodb_old_blocks_ms`(默认 1000ms) 后再次访问才晋升 young——防全表扫描把热页冲光
- **Change Buffer**：二级索引页不在池中时先缓存变更，后续读入合并——写多读少二级索引受益；唯一索引不可用（必须校验）
- **Doublewrite Buffer**：先顺序写系统表空间副本再写真位——防部分写失效(torn page)；掉电恢复靠它+redo
- 自适应哈希索引(AHI)：热点等值查询路径自动建哈希，争用时可关

## 二、日志体系与两阶段提交

```
事务提交:
  redo prepare(disk flush 按 innodb_flush_log_at_trx_commit)
    → 写 binlog(sync_binlog)
      → redo commit 打标记   ← 崩溃时以此仲裁回滚/提交(XA 内部协议)
```

| 参数 | 值 | 权衡 |
|------|-----|------|
| `innodb_flush_log_at_trx_commit` | 1 | 每次 fsync，完整持久（默认） |
| | 2 | 只写 OS cache，宕库不丢/宕机丢 1s |
| `sync_binlog` | 1 | 双 1 配置=金融口径，吞吐换安全 |

- binlog 三格式：statement(小但不确定函数危险)/row(大而确定，默认)/mixed；GTID 使从库定位免文件名偏移
- 主从延迟治理：并行复制 LOGICAL_CLOCK、semi-sync 半同步折衷

## 三、锁体系全貌

| 锁粒度 | 名称 | 说明 |
|--------|------|------|
| 表级 | IS/IX 意向锁 | 行锁前置声明，使表锁判断 O(1) |
| 行级 | record | 唯一项精确命中 |
| 行级 | gap | 锁开区间防插入 |
| 行级 | next-key | record+gap，RR 当前读防幻读主力 |
| 插入 | insert intention | gap 锁间兼容的等待意图 |

- 死锁：wait-for 图主动检测，回滚 undo 量小者；热点行高并发下检测本身成瓶颈（`innodb_deadlock_detect` 可关改超时兜底）
- 实践：**小事务+一致锁序+索引精准命中**（无索引更新会升级扫描范围放大锁面）

## 四、在线 DDL 与表维护

- ALGORITHM=COPY / INPLACE / **INSTANT**(8.0 加列秒级元数据变更) 三档；INSTANT 不适用时退 INPLACE 仍允许并发 DML（建二级索引等）
- 大表变更流程：pt-osc/gh-ost 影子表+触发器/ binlog 回放，限速切换
- 维护信号：history list length(长事务)、脏页比例、碎片率(`DATA_FREE`)

## 五、EXPLAIN 实战判读（列级）

| 列 | 关注点 |
|----|--------|
| type | const>eq_ref>ref>range>index>ALL；出现 ALL 先问为什么没走索引 |
| key/rows/filtered | 估算扫描行×选择率——rows 巨大即计划劣化 |
| Extra | Using index(覆盖✓) / Using filesort / Using temporary / Using join buffer(buffer=join 无索引) |

优化器干预：`ANALYZE TABLE` 刷统计；hint(USE/FORCE INDEX) 最后手段并注释原因。

## 五·补、锁矩阵 SQL 复现脚本（RR 隔离级，双会话对照）

准备：`CREATE TABLE t(id INT PRIMARY KEY, k INT, KEY idx_k(k)); INSERT INTO t VALUES (1,3),(5,7),(10,10);`

### 实验 1：无命中行的等值查询 → 间隙锁
| 步 | 会话 A | 会话 B | 现象 |
|----|--------|--------|------|
| 1 | `BEGIN;` | `BEGIN;` | — |
| 2 | `SELECT * FROM t WHERE k=5 FOR UPDATE;` | | 无匹配行 → **只加间隙锁 (3,7)**，不锁任何行 |
| 3 | | `INSERT INTO t VALUES (2,4);` | **阻塞**！k=4 落在间隙内 |
| 4 | | `INSERT INTO t VALUES (9,9);` | 成功——(7,10) 间隙未锁 |
| 5 | A `COMMIT;` 后 B 的步骤3立即完成 | | 锁随事务释放 |

**推理链**：RR 需要"可重复读"且防幻影。k=5 不存在，行锁无处安放；InnoDB 用锁住"空隙"的方式保证 A 再查时结果不变（B 插不进 4）。副作用即生产事故源：**无命中行的 FOR UPDATE 是把隐形刀**——并发插入整段卡死。

### 实验 2：唯一索引 vs 普通索引的加锁差异
- `WHERE id=5 FOR UPDATE`（PK 等值、存在）：仅记录锁该行（唯一性保证无需间隙）
- `WHERE id=7 FOR UPDATE`（不存在）：间隙锁 (5,10)
- `WHERE k BETWEEN 4 AND 8 FOR UPDATE`（普通索引范围）：next-key (3,7] + (7,10) + 可能补到上界——**范围越大锁越多**

### 实验 3：EXPLAIN 输出走读（对应 §五）
```
EXPLAIN SELECT * FROM t WHERE k>4 AND k<9;
type=range | key=idx_k | rows=2 | Extra=Using index condition
```
判读顺序：type(range≥ref≥index≥ALL) → key 是否真用上 → rows 估算与实际行数比(差一个量级=统计过期跑 ANALYZE) → Extra 里 ICP 表示 k 条件下推到引擎层过滤（回表前裁剪）。

## 六、参数基线（起步模板，非万能值）

```
innodb_buffer_pool_size = 物理内存 50–70%
innodb_redo_log_capacity(8.0.30+) ≈ 1h 写放量
max_connections 按连接池×实例数反推，勿拍脑袋万级
tmp_table_size/heap 到顶转磁盘临时表 → 看 Created_tmp_disk_tables
慢参组合验证法: 一次一个变量 + sysbench 回归
```

## 七、待确认项

> ① 8.4 起默认值变动清单（如 redo capacity 自适应）；② Group Replication vs 半同步在跨机房 RTT 下的选型阈值；③ Instant DDL 各操作支持矩阵版本差异。

> [!warning] 残余复核（2026-09-13）：三条**均仍开放**，且都不是「本机翻文档能定」的类型——本轮离线手段（本机二进制/源码、库内交叉核对、链接巡检缓存）对它都不适用。
> - ① 需要 **8.4** 的实例或手册才能列「变动清单」；本机只装了 **MySQL 8.0.25**（`mysql --version` 实测），版本区间覆盖不到，无法比对。
> - ② 「跨机房 RTT 下的选型阈值」是**压测结论**，不是参数表事实——GR 与半同步在不同的 RTT/丢包下有不同的提交延迟拐点，只能测。
> - ③ Instant DDL 的支持矩阵是**逐版本表**，本机 8.0.25 连 8.0.29+ 的新增行都覆盖不到。
> 判据：① 用官方镜像起两实例后逐项 diff——`docker run --rm mysql:8.0 mysqld --verbose --help` 与 `mysql:8.4` 同命令输出求差，或抓 MySQL 8.4 Reference Manual 的 "Changes in MySQL 8.4" 默认值小节（本机有 Docker CLI，但 daemon 未运行、拉镜像需联网，故本轮不做）；② 在延迟注入下分别压 GR（`group_replication_*`）与半同步（`rpl_semi_sync_*`）的提交延迟/吞吐曲线，取拐点 RTT，并注明副本数与 `sync_binlog` 前提；③ 抓手册 "Online DDL Operations" 表，按 INSTANT/INPLACE/COPY 三列逐操作核对并标注引入版本。

> [!success] 残余复核（2026-09-13 联网轮）：**① 与 ③ 已结；② 仍开放**（保留判据）。
> - **① 已结**：8.4 手册 "What Is New in MySQL 8.4 since MySQL 8.0" 内有专表 *InnoDB system variable default values in MySQL 8.4 differing from MySQL 8.0*，即原问的「变动清单」本体。要点：`innodb_adaptive_hash_index` ON→**OFF**；`innodb_change_buffering` all→**none**；`innodb_io_capacity` 200→**10000**（`innodb_io_capacity_max` 随之改为 2×，取消 2000 下限）；`innodb_log_buffer_size` 16 MiB→**64 MiB**；`innodb_numa_interleave` OFF→**ON**；`innodb_use_fdatasync` OFF→**ON**；Linux 上 `innodb_flush_method` fsync→**O_DIRECT（支持时，否则 fsync）**；`innodb_doublewrite_files` 由 `instances*2`→**2**、`innodb_doublewrite_pages` 由 `= innodb_write_io_threads`（默认 4）→**128**；`innodb_buffer_pool_in_core_file` ON→**OFF（支持 MADV_DONTDUMP 时）**；`innodb_buffer_pool_instances` / `innodb_page_cleaners` / `innodb_purge_threads` / `innodb_read_io_threads` / `innodb_parallel_read_threads` 由定值改为**按 buffer pool 与 CPU 数自适应**；`temptable_max_ram` 1 GiB→**总内存 3%（1–4 GiB 区间）**、`temptable_max_mmap` 1 GiB→**0（即 OFF）**、`temptable_use_mmap` ON→**OFF**。关于原问点名的「redo capacity 自适应」：8.4 的变更落在 **`--innodb-dedicated-server` 开时 `innodb_redo_log_capacity` 的算法由「按内存」改为「按 CPU」**（该变量本身默认仍为 OFF，与 8.0 同）。同页另有非 InnoDB 的默认变更：8.4.0 起 `mysql_native_password` **默认不再启用**（需 `--mysql-native-password=ON`）；`CHANGE REPLICATION SOURCE TO` 的 `SOURCE_RETRY_COUNT` 默认改为 **10**。
> - **③ 已结（结论与预期相反）**：把 8.0 与 8.4 手册的 *Online DDL Operations* 页并排比对，**列操作支持矩阵的五列（Instant / In Place / Rebuilds Table / Permits Concurrent DML / Only Modifies Metadata）逐格一致**——12 行（加列/删列/改列名/重排列/改默认值/改数据类型/扩 VARCHAR/删默认值/改自增值/改 NULL/改 NOT NULL/改 ENUM-SET）在 8.0 与 8.4 之间**没有一格变化**。真正的版本差异全在**同页注记**里：8.0 页保留了历史版本门（「INSTANT 自 8.0.12 起为默认算法，之前是 INPLACE」、加列位置「8.0.29 之前只能加在末尾」、「该限制于 8.0.29 加入」），而 8.4 页把这些历史门**删掉**、同位置改写为「**INSTANT is the default algorithm in MySQL 8.4**」，并新增「允许的 row version 上限为 64（**as of MySQL 9.1.0 为 255**）」。即：该矩阵**不是**逐版本表，查版本差异要查注记与上限，不是查矩阵。
> - **② 仍开放**（判据收紧）：GR vs 半同步在跨机房 RTT 下的拐点属**压测结论**，官方手册不含阈值数字；判据仍是在延迟注入下分别压 `group_replication_*`（单主/多主、`group_replication_consistency` 档位）与 `rpl_semi_sync_*`（`rpl_semi_sync_source_timeout`、`sync_binlog`、副本数）的提交延迟/吞吐曲线取拐点。本轮联网未取得任何官方阈值口径，不得以社区经验值代替。
> 依据：https://dev.mysql.com/doc/refman/8.4/en/mysql-nutshell.html （含 Table 1.1 InnoDB 默认值差异）与 https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-operations.html ；对照页 https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html （三页均经 Wayback 取回，取回于 2026-09-13）

## Related

[[CS-KB-Home]] · [[数据库原理与调优]] · [[Redis原理与实践]] · [[MongoDB原理与实践]] · [[操作系统八股]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 残余复核 | §七 待确认项三条（8.4 默认值变动 / GR vs 半同步的 RTT 阈值 / Instant DDL 支持矩阵） | 逐条判定**仍开放**，理由与判据写进 §七 callout：本机仅 MySQL 8.0.25（`mysql --version` 实测）、覆盖不到 8.4；RTT 阈值是压测结论；Instant DDL 矩阵是逐版本表。三条判据落到可执行动作（`mysqld --verbose --help` 双版本求差 / 延迟注入下压 GR 与半同步曲线取拐点 / 按手册 Online DDL Operations 表逐操作核对） |
| 加厚 | 本页此前无「待确认项处置」记录，修正与来源没有落点 | 新建本节并回链 [[CORRECTIONS]] · [[AGENTS]] |
| 残余复核（联网轮） | §七 待确认①「8.4 起默认值变动清单（如 redo capacity 自适应）」 | **已结**：取 MySQL 8.4 手册 1.4 节内 Table 1.1（InnoDB 默认值 8.4 vs 8.0 差异表），列全 adaptive_hash_index/change_buffering/io_capacity(200→10000)/log_buffer_size(16→64MiB)/numa_interleave/use_fdatasync/flush_method/doublewrite_files/doublewrite_pages/buffer_pool_in_core_file/temptable_* 等；原问点名的「redo capacity 自适应」实为 `--innodb-dedicated-server` 下 `innodb_redo_log_capacity` 算法由按内存改为按 CPU。依据：https://dev.mysql.com/doc/refman/8.4/en/mysql-nutshell.html （Wayback 取回） |
| 残余复核（联网轮） | §七 待确认③「Instant DDL 各操作支持矩阵版本差异」 | **已结**：8.0 与 8.4 手册 Online DDL Operations 页并排比对，12 行操作 × 5 列的支持矩阵**逐格一致**；版本差异全在同页**注记**（8.0 保留「INSTANT 自 8.0.12 起为默认」「8.0.29 前只能加在末尾」等历史门，8.4 删除并改写为「INSTANT is the default algorithm in MySQL 8.4」，新增 row version 上限 64／MySQL 9.1.0 起 255）。依据：https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-operations.html 对照 8.0 同名页（均经 Wayback 取回） |

回链：[[CORRECTIONS]] · [[AGENTS]]
