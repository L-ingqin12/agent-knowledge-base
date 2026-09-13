---
title: Linux高性能网络编程实战
aliases: [高性能网络, epoll反应堆, io_uring, 用户态协议栈]
tags: [cs/net, cs/system, cs]
created: 2026-08-26
updated: 2026-09-13
status: review
source: Linux man 手册与工业实践共识（Reactor 模式/io_uring liburing/DPDK 官方文档口径）；内核版本敏感处标待确认
fetched_at: 2026-08-26
---

# Linux 高性能网络编程实战

> [!abstract] 定位
> 从 socket API 到百万连接：Reactor 反应堆代码骨架、epoll 工程细节（LT/ET/惊群已在 [[操作系统八股]] §六）、io_uring 新异步模型、DPDK 绕过内核的原理、有栈/无栈协程实现路径、池式组件（内存池/无锁队列）设计要点。理论对照 [[计算机网络八股]]，并发框架见 [[高并发系统设计]]。

See also: [[CS-KB-Home]] · [[操作系统八股]] · [[设计模式实战]] · [[LibC运行时排查-TLS与锁]]

## 一、从阻塞到事件驱动：四种服务模型演进

| 模型 | 每连接成本 | 百万连接 | 关键瓶颈 |
|------|-----------|---------|---------|
| 阻塞+每连接一线程 | 1 线程(8MB 栈) | ✗ | 线程切换+内存 |
| 连接池化线程 | 复用但仍绑定 | 千级 | 阻塞读拖死 worker |
| select/poll 轮询 | 1 线程可管千级 | fd 上限/每次全量拷贝 | O(n) 扫描 |
| **epoll 事件驱动** | ~KB 级就绪表 | ✓ C10M 可期 | 回调内不得阻塞 |

## 二、Reactor 反应堆代码骨架（单 Reactor 单线程版）

```c
// 核心循环: 注册→等待→分发。所有 I/O 必须非阻塞(fd 设 O_NONBLOCK)
// 本例按 ET(边沿触发)演示: 注册必须显式带 EPOLLET, 否则默认是 LT
epoll_ctl(epfd, EPOLL_CTL_ADD, listen_fd, &(struct epoll_event){.events=EPOLLIN|EPOLLET});
for (;;) {
    int n = epoll_wait(epfd, evs, MAXEV, -1);      // 就绪才返回, 不空转; -1 先判 EINTR 重试
    for (int i = 0; i < n; ++i) {
        if (evs[i].data.fd == listen_fd) accept_and_register();   // 新连接入册
        else {
            while ((len = recv(fd, buf, sizeof buf, 0)) > 0) on_msg(buf,len);
            if (len == 0)            close_and_unregister();       // 对端关闭
            else if (errno != EAGAIN) perror_log();               // EAGAIN=暂无数据, 正常
        }
    }
}
```

**推理链**：为什么 recv 要抽干循环（ET 模式契约——注意上面的注册必须带 `EPOLLET`，LT 下"读到 EAGAIN"并非必须）；为什么业务处理必须扔给队列（回调内做 DB 查询=整个事件循环停摆，所有连接陪葬）。多 Reactor 进阶 = mainLoop 只管 accept，subLoop(N 个，每核一) 管 IO——memcached/nginx 同构。

> [!warning] 更正（2026-09-13）：本节原先"注册写 `.events=EPOLLIN`（即 LT）却把抽干循环解释成 ET 契约"自相矛盾，已按 ET 演示补上 `EPOLLET`（fd 必须先 `O_NONBLOCK`）。事件处理还需一并覆盖：
> - `EPOLLRDHUP`（since Linux 2.6.17）：对端半关闭，不必等 recv 返回 0
> - `EPOLLERR | EPOLLHUP`：**即使未注册也会返回**，必须处理
> - `epoll_wait` 返回 -1 先判 `EINTR` 重试，其余才是真错误
> - 收窄一处：审计提的"close 前先 `EPOLL_CTL_DEL`"并非 close(2) 的硬性要求，仅作纪律性建议（fd 号复用前要确认已摘除）
> （原表述为「注册写 .events=EPOLLIN（未加 EPOLLET，即 LT），同一节推理链却写『为什么 recv 要抽干循环（ET 模式契约）』」）
> 来源：https://man7.org/linux/man-pages/man2/epoll_ctl.2.html

### 写事件的处理纪律
大响应不能一次 write（可能 EAGAIN 半途）→ 维护 per-connection 输出缓冲区，EPOLLOUT 仅在缓冲区非空时**动态注册**，写完即摘除——否则空触发风暴。

## 三、io_uring：把"系统调用"也异步掉

```
SQ(提交环) ←── app 填 sqe(操作描述符) ──→ 内核消费
CQ(完成环) ←── 内核填 cqe(结果) ──→ app 收割     共享内存零拷贝交互
```

- 与 epoll 的本质差：epoll 只异步"就绪通知"，读写仍是同步 syscall；io_uring 连 read/write/connect/fsync **全部提交后立即返回**，批量化(SQPOLL 内核线程收割)后 syscall≈0
- 适用：高频小 IO（存储引擎日志盘）、需要 syscall 密集场景降 CPU；普通 web 服务收益有限（~~待确认内核 5.15+ vs 6.x 特性面差异~~ → 该问法不可查：真实分界是"能力 × 最低内核版本"表，见 [[操作系统八股]] §五 附——SQPOLL 5.11 起免注册文件、5.11 非 root 需 `CAP_SYS_NICE`、5.13 起放宽。运维注意：老内核上 liburing 会**静默降级**，压测前先打印 io_uring features 位验证实际能力）
  > 来源：https://man7.org/linux/man-pages/man2/io_uring_setup.2.html
- 多路复用选型直觉：万级长连接 epoll 已够；追求 syscall 极限/存储路径再上 io_uring

## 四、DPDK：绕过内核的用户态协议栈

```
传统: 网卡 → 中断 → 内核协议栈(软中断/skb 分配/拷贝) → socket 缓冲 → 应用   [多次拷贝+上下文切换]
DPDK: 网卡 DMA 直接写用户态 ring → 应用轮询(poll mode driver) 取包          [零拷贝零中断]
```

- 代价独占：网卡被 DPDK 接管后内核看不到它（该口不能再跑 ssh）+ CPU 轮询满载占核——用隔离核(taskset/cgroup)专供
- **四件套前置条件**（DPDK 官方 System Requirements）：① BIOS 侧先开对应项（x86 有专门的 BIOS 设置前提）；② **大页**是"packet buffer 大内存池"的硬需求——64 位应用推荐 1GB 大页，需手工挂载 `mkdir /mnt/huge; mount -t hugetlbfs -o pagesize=1GB none /mnt/huge`（可写 `/etc/fstab` 持久化）；双路 NUMA 机器上启动期预留的大页一般被两个 socket 均分；若不需要 secondary process，可用 in-memory 模式免大页配置；③ **VFIO/UIO 绑定**（vfio-pci 为现代首选，uio_pci_generic 为轻量替代）；④ 隔离核 + **NUMA 亲和**（网卡所在 socket 与轮询核对齐）
- 最小验证：`dpdk-devbind.py --status` 看绑定、`grep Huge /proc/meminfo` 看大页余量、跑 `testpmd` 看 pps
- 在其上自研协议栈=自己实现 ARP/IP/TCP 状态机（教学价值极高，生产多直接用现成栈）；适用面：NFV/网关/流量镜像这类 PPS 敏感型
- 判断准则一句话：**带宽瓶颈在"包个数"(PPS) 而不是字节时才考虑绕内核**

> 来源：https://doc.dpdk.org/guides/linux_gsg/sys_reqs.html

## 五、协程：用户态上下文切换的两条路线

| 路线 | 机制 | 代表 |
|------|------|------|
| 有栈协程（ucontext 系） | 每个协程独立栈；`makecontext/swapcontext` 保存恢复的是**含信号掩码的完整上下文**（`ucontext_t`：uc_link/uc_sigmask/uc_stack/uc_mcontext），不是裸"换寄存器+栈指针" | ucontext（libc 提供） |
| 有栈协程（运行时汇编切换） | 每个协程独立栈；运行时自管栈 + 汇编级上下文切换，**~10ns 量级属于这一族**（数字需挂可复现基准） | goroutine(growable stack) |
| 无栈协程 | 状态机变换+帧存堆，编译器生成 | C++20 coroutine/async-await |

> 来源：https://man7.org/linux/man-pages/man3/makecontext.3.html · https://man7.org/linux/man-pages/man3/getcontext.3.html

- 有栈版最小件：`makecontext/setjmp` 类四件套 + 调度器（round-robin 或事件驱动挂起在 IO 上）——自研协程框架的核心难点是**与 epoll 的融合**（协程内 recv 阻塞时把 fd 挂 epoll 并 yield 给调度器，就绪后再 resume）
- 切换成本对比：线程 ~1µs(内核态) vs 协程 ~10ns(用户态，指汇编切换实现)——三个数量级的差距就是"百万协程"的底气；ucontext 系因保存信号掩码等完整上下文，明显慢于汇编切换（原表把两者混成一行，已拆分）
- 陷阱：有栈协程默认栈小(如 128KB)，深递归/大局部数组爆栈且**难排查**(段错误落在 guard page)；跨协程持有 mutex 在调度下易产生与线程同款的死锁谱系（[[LibC运行时排查-TLS与锁]] §三方法全适用）

## 六、池式组件设计要点（支撑层）

| 组件 | 核心决策点 |
|------|-----------|
| 内存池 | 定长 slab(按 size-class 分桶) vs 变长 free-list；归还时判归属(指针落在哪个池区间)；对齐到 cache line 防 false sharing([[计算机组成原理]]) |
| 无锁环形队列 | 单生产者单消费者最简(CAS 头尾索引即可)；MPMC 需处理 ABA(带代际 tag)；容量取 2^n 使取模变位运算 |
| 定时器 | 时间轮(O(1) 插入删) vs 最小堆(O(log n))；连接心跳管理是时间轮经典应用 |
| 对象池 | 归还重置状态而非析构重建；借用方 RAII 句柄防漏还 |

## 七、待确认项

> ① io_uring 多核 SQPOLL 的最优核数经验值；② DPDK 对 virtio/云厂商虚拟网卡的 PMD 支持矩阵更新；③ 有栈协程栈增长方案(分段栈 vs 拷贝栈)在主流实现的取舍现状；④ epoll 在 6.x 内核对新告警类型(如 EPOLLET 边沿+优先级)的演进。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | §二 注册写 LT 却把抽干循环解释成 ET 契约（文档内部不自洽） | 按 ET 演示补 `EPOLLET`，并补 `EPOLLRDHUP`、必检 `EPOLLERR\|EPOLLHUP`、`EINTR` 重试、"close 前 DEL 非硬性要求"的收窄说明；依据 [epoll_ctl(2)](https://man7.org/linux/man-pages/man2/epoll_ctl.2.html) |
| 补疏漏 | §四 DPDK 只写"接管网卡 + 占核 + 隔离核" | 补大页（1GB 页挂载/NUMA 均分/in-memory 模式）、VFIO/UIO 绑定、隔离核 + NUMA 亲和四件套与最小验证命令；依据 [DPDK System Requirements](https://doc.dpdk.org/guides/linux_gsg/sys_reqs.html) |
| 补疏漏 | §五 把 ucontext 与汇编切换混成一行，"~10ns"归属不清 | 拆成 ucontext 系（含信号掩码的完整上下文）与运行时汇编切换两行，10ns 归后者；依据 [makecontext(3)](https://man7.org/linux/man-pages/man3/makecontext.3.html) / [getcontext(3)](https://man7.org/linux/man-pages/man3/getcontext.3.html) |
| 补疏漏 | §三 io_uring 挂着不可查的"5.15+ vs 6.x"待确认 | 改为指向"能力 × 最低内核版本"表并补 liburing 静默降级的压测前置检查；依据 [io_uring_setup(2)](https://man7.org/linux/man-pages/man2/io_uring_setup.2.html) |

回链：[[CORRECTIONS]] · [[AGENTS]]

## Related

[[CS-KB-Home]] · [[操作系统八股]] · [[计算机网络八股]] · [[高并发系统设计]] · [[Python高级核心]] · [[音视频流媒体开发基础]]
