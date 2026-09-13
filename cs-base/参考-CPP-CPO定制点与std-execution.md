---
title: 参考-C++CPO定制点与std-execution
aliases: [CPO学习, tag_invoke, std::execution, P2300, 定制点对象]
tags: [reference, reference/cpp]
created: 2026-08-26
updated: 2026-09-13
status: review
source: 基于 P2300/P1895 提案文本、cppreference、stdexec(NVIDIA) 公开资料整理；标准演进快，时效性条目以「待确认」标注
fetched_at: 2026-08-26
---

# 参考-C++ CPO 定制点与 tag_invoke 在 std::execution 下的使用（2026-09-13 更正：execution 的扩展缝已改为成员 connect + 域）

> [!abstract] 谱系一图
> **函数模板开放 ADL 劫持** →（修复）**CPO 定制点对象**：封装"成员优先/ADL 兜底 + 毒丸拦截"的可定制函数对象 → **`tag_invoke` 惯用法**：把所有定制收敛到一个 `tag_invoke(tag_t<CPO>, args...)` 入口（range-v3 发明，P1895 提案化）→ **`std::execution`（P2300 → C++26）**：sender/receiver/operation-state 三件套的扩展缝**最终没有采用 tag_invoke**——P2855/P2999/P3109 已把 ADL 定制点从设计中移除，现行机制是**成员 `connect` + 域（`default_domain`/`transform_sender`/`transform_env`）+ 查询对象的 `query` 成员**（详见 §三「定制机制更替」）。本文给出机制原理、在 stdexec 下的使用与自定义 sender 实操。

> [!warning] 更正（2026-09-13）：原文摘要与 §一/§三/§四/§五 通篇以「`std::execution` 几乎全部以 CPO + `tag_invoke` 作为扩展缝」「`connect(sndr, rcvr)` 定制缝=tag_invoke」为命题，示例写 `friend tag_invoke(ex::connect_t, …)`。该命题已过期：P3109R0 改动表列有「P2855 | Member-function-based customization | Design modification | Remove the tag_invoke ADL-based CPs」，正文写明 In combination with the changes introduced in P2999 … there will be no more ADL-based customization points left in the design.（https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2024/p3109r0.html ）；草案 [exec.connect]/6 现行写法是 `new_sndr.connect(rcvr)`，其中 `new_sndr` 由 `transform_sender(sndr, get_env(rcvr))` 得到（https://eel.is/c++draft/exec.connect ）。本文保留 tag_invoke 段落作为**历史与迁移对照**，新代码一律按成员 `connect` + 域写。

See also: [[lognet-rootcause-multiagent-architecture]] · [[log-analysis-agent-windows-architecture]] · [[opencode-pi-base-development-analysis]] · [[参考-COM组件框架-Windows集成]]

## 一、为什么需要 CPO

| 问题 | 裸 `swap(a,b)` 式 ADL 定制 | CPO 方案 |
|------|---------------------------|----------|
| 用户向 `std` 命名空间塞重载 = UB | 存在 | 不需要在 `std` 加代码 |
| 无限定调用可被最外层命名空间劫持 | 是 | CPO 内部先查成员/毒丸，再受限 ADL |
| 泛型库无法统一"有成员就用成员" | 手写 if constexpr 散落各处 | 定制逻辑集中一处 |

**CPO 三要素**（以 `std::ranges::begin` 为代表）：① 函数对象（全局 const 实例）② 定制查找顺序：成员 → ADL 自由函数（受概念约束）→ 缺省实现；③ **毒丸**（poison pill）：一个模板化的 deleted `begin(auto&&)` 在最内层命名空间兜底，阻断外层无限定重载继续参与重载决议。

> [!note] 两代技术路线
> - **ranges 家族**（C++20）：毒丸 + 约束式 ADL，**不用** tag_invoke
> - **execution / P2300 家族**（C++26 目标）：一度大规模采用 **`tag_invoke`** 统一定制入口，**该方案随后被移除**——现行是成员函数 + 域对象定制（P2855 / P2999 / P3109）
> - `tag_invoke` 本身源自 range-v3 实践、P1895 提案化；但 P1895 未进入现行草案设计，「`std::tag_invoke` 随 execution 一起落地」已不成立（原表述见上方更正块）

## 二、tag_invoke 惯用法速览

```cpp
// 库侧：定义 CPO
inline constexpr struct my_size_fn {
    template <class T>
        requires requires(T& t) { t.my_size(); }          // 1) 成员优先
    constexpr auto operator()(T& t) const { return t.my_size(); }

    template <class T>
        requires (sizeof(my_size_fn) == 0)                // 毒丸变体之一
    friend constexpr auto my_size(T&) = delete;           // 阻断外部裸 ADL

    template <class T>
        requires requires(T& t) { tag_invoke(*this, t); } // 2) tag_invoke 兜底
    constexpr auto operator()(T& t) const { return tag_invoke(*this, t); }
} my_size{};

// 用户侧：非侵入定制 —— 一个友元即可
struct Blob { int n; 
  friend constexpr int tag_invoke(my_size_fn, Blob b) { return b.n; }
};
int s = my_size(Blob{42});   // 42
```

要点：`tag_t<CPO>` 取实例类型；定制点签名第一个参数永远是 tag；**禁止**用户直接调 `tag_invoke` 裸名（那是实现细节），永远经 CPO 调用。

## 三、std::execution 核心三件套（P2300）

```
sender  ──connect(rcvr)──▶ operation_state ──start()──▶ 异步执行
                                   │
                          receiver: set_value / set_error / set_stopped
```

| 概念 | 一句话 | 关键 CPO |
|------|--------|---------|
| sender | "一件将来的工作"的惰性描述（零开销组合子） | `connect(sndr, rcvr)`（定制缝=**成员 connect + 域**；旧写法 tag_invoke 已移除） |
| receiver | 结果的消费者（三种完成信号回调） | `get_env(rcvr)` 查询环境 |
| scheduler | "在哪跑"的句柄 | `schedule(sched)` 返回 sender（同样是成员/域定制点） |
| operation_state | connect 产物，`start()` 触发执行，须保活至完成 | — |

高频工厂/适配器（草案 [exec.adapt] 现行集合，全部是 CPO）：`write_env / unstoppable / starts_on / continues_on / schedule_from / on / then / upon_error / upon_stopped / let_value / let_error / let_stopped / bulk / bulk_chunked / bulk_unchunked / when_all / into_variant / stopped_as_optional / stopped_as_error / associate`（另有 exposition-only 的 `stop-when`）；消费端 `this_thread::sync_wait / sync_wait_with_variant`。

> [!warning] 更正（2026-09-13）：原清单里的 `ensure_started`、`split`、`stop_when` 三个名字在标准中已不存在或不可调用：① `ensure_started` 由 P2519 从设计中删除；② `split` 由 **P3682R0**（2025-06 会合）删除——两者是同一条算法血脉（先更名后删除），故一次清掉两个名字；③ `stop_when` 现行是 **exposition-only**（草案小节标题「Exposition-only execution::stop-when [exec.stop.when]」），用户代码不可调用。另：`sync_wait_with_dynamic` 属记混，标准里只有 `sync_wait` 与 `sync_wait_with_variant`。依据 [exec.adapt]（https://eel.is/c++draft/exec.adapt ）、[exec.stop.when]、P3109R0 改动表、P3682R0「Deficiencies of std::execution::split」。
> 「共享结果 / 急切启动」语义的现行归属：`spawn`/`spawn_future`（[exec.spawn.future]）+ async scope（P3149 系）；仍需共享结果时自行封装。

`sync_wait` 的三条生产边界（[exec.sync.wait]）：① 要求输入 sender 恰有一个 value completion signature；② 值完成时返回**装在 `optional` 里的 tuple**；③ 停止完成返回**空 optional**、错误完成**抛异常**——三者必须分开处理，别用 `.value()` 一把梭。

### 定制机制更替：从 tag_invoke 到「成员 connect + 域」

草案 [exec.snd] 的目录本身就是现行分层：`indeterminate_domain`（33.9.5）、`default_domain`（33.9.6）、`transform_sender`（33.9.7 [exec.snd.transform]）、`apply_sender`（33.9.8）。

- **域怎么被选中**：`get_domain(get_env(rcvr))` 从接收方环境取域；`get_completion_domain` / `get_completion_scheduler` 回答"某个完成信号属于哪个域/调度器"，供算法决定要不要改写 sender
- **分工**：`transform_sender(sndr, env)` 负责**改写 sender 本身**（把通用 sender 换成某域的专用实现，可选）；成员 `connect(rcvr)` 负责**把 sender 变成 operation_state**（必写）
- **何时写域、何时只写成员函数**：只把已有算法接到自家执行资源上 → 写调度器 + 成员 `connect` 就够；要改**通用算法在自家 sender 上的行为**（例如自定义 `then` 的融合规则）→ 才需要自定义域 + `transform_sender` / `transform_env`
- **迁移对照**

| 旧写法（tag_invoke，已移除） | 现行写法（成员 + 域） |
|---|---|
| `friend auto tag_invoke(ex::connect_t, S&&, Rcvr)` | `auto connect(Rcvr) &&` 成员函数 |
| `friend auto tag_invoke(ex::schedule_t, Sched)` | `schedule()` 成员函数 |
| `friend auto tag_invoke(ex::get_env_t, const S&)` | `get_env()` 成员（或经 `env` 查询对象） |
| 靠 ADL 找 `tag_invoke` 兜底 | 靠 `get_domain` / `transform_sender` 在域上定制 |

> 依据：P2999（把 sender 算法定制改为基于 domain 对象的成员函数定制）、[exec.snd]、[exec.connect]/6（`connect(sndr, rcvr)` 等价于 `new_sndr.connect(rcvr)`）。

## 四、在 stdexec（NVIDIA 参考实现）下的实操

```cpp
#include <exec/static_thread_pool.hpp>
#include <stdexec/execution.hpp>
namespace ex = stdexec;

exec::static_thread_pool pool{4};                       // 4 工作线程
ex::scheduler sched = pool.get_scheduler();

auto work =
    ex::schedule(sched)                                 // sender: 在池上开始
  | ex::then([]{ return load_package_index(); })        // 纯变换
  | ex::let_value([](Index& idx){
        return ex::when_all(                            // 并行 fan-out
            ex::then(ex::just(&idx), parse_hilog),
            ex::then(ex::just(&idx), parse_kmsg));
    })
  | ex::upon_error([](std::exception_ptr e){ log(e); return 0; });

auto [result] = ex::sync_wait(std::move(work)).value(); // 阻塞收口（demo 用）
```

### 自定义 sender 的定制路（成员 connect + 域）

```cpp
struct retry_sender {
    using completion_signatures =
        ex::completion_signatures<ex::set_value_t(int),
                                  ex::set_error_t(std::exception_ptr)>;

    sender_of auto inner; int retries;

    // 现行写法：成员 connect —— ex::connect(sndr, rcvr) 会走到这里
    template <receiver_of Rcvr>
    auto connect(Rcvr r) &&;                    // 返回 operation_state

    // —— 以下是旧写法，已从设计中移除，仅作迁移对照 ——
    // template <receiver_of Rcvr>
    // friend auto tag_invoke(ex::connect_t, retry_sender&& s, Rcvr r);
    // friend auto tag_invoke(ex::connect_t, retry_sender&&, Rcvr);
};
// 组合进管道后 ex::connect 会经 CPO 找到上面的成员 connect
```

> [!tip] 与本库 PoC 的映射
> LogNet PoC 的 P1 解析/P2 符号化/P3 建图流水线（[[lognet-rootcause-multiagent-architecture]] §8.1）天然是 `when_all + then` 结构：Sidecar 若选 C++ 实现，stdexec 提供结构化并发（取消传播 `stop_token` 贯穿 sender 链）替代手搓线程池——对应看门狗 T2 interrupt 的语言级支持。

## 五、取消与环境查询（生产化必读）

- **结构化取消**：`get_stop_token(get_env(rcvr))` 沿 sender 链自动传播；做超时/抢占改用**公开手段**——把 `stop_token` 放进环境沿 sender 链传播、`when_all` 的停止传播、或 async scope（P3149 系）——比裸线程 `interrupt()` 语义干净
  - 注：旧文写的 `stop_when(stop_src.token(), progress_sndr)` 在现行草案是 **exposition-only**（[exec.stop.when]），用户代码不可调用；若某实现（如 stdexec）暴露同名工具，那是实现扩展、不是标准接口
- **forward progress 保证**：`get_forward_progress_guarantee` 查询调度器承诺（`concurrent` / `parallel` / `weakly_parallel` —— 第三个值**不是** weakly-sequential，那是 [intro.progress] 里另一套前向进展保证的名字，不可混用）。语义：concurrent=可无锁无等待推进；parallel=有界等待；weakly_parallel=同 parallel 但允许同一线程上交替推进。它影响 fan-out 的设计下限
- **属性查询也是 CPO**：`get_allocator/get_stop_token/get_env/get_domain/get_scheduler/get_start_scheduler/get_delegation_scheduler/get_forward_progress_guarantee/get_completion_scheduler/get_completion_domain` 等**全部是查询对象**（名单不变）；但**实现机制**是环境对象的 `query` 成员，不是 tag_invoke——原「全部走 query 对象 + tag_invoke」一句随本次更正改掉

## 六、采用现状与风险（2026-08 快照）

| 项 | 状态 |
|----|------|
| P2300 → IS 进度 | 目标 C++26；sender/receiver 已进 C++26 工作草案（作为 IS 正式发布仍未定），stdexec 库可用于生产级实验。编译器支持面以 cppreference「C++26」页自带的支持表为准（含 partial 标记）——原「GCC 12+/Clang 15+/MSVC 19.35+ 社区实测带」属无口径说法，已弃用 |
| 定制机制 | **已成定局**：成员函数 + 域（P2855 列为 Design modification，P2999 去掉 ADL 定制）。原「LEWG 有意回归语言级定制点（提案号待确认）」的猜测删除；新代码按成员 `connect` + 域写，tag_invoke 只作历史对照 |
| 生态 | NVIDIA stdexec 最活跃，并自 P2300R10 起同步改为成员 `connect`；libunifex（Meta）为先驱但 API 早于 P2300 定稿 |
| 验收（可执行） | 用 `-std=c++26` 编译 §四 的 `retry_sender`：tag_invoke 版应**不再被识别**（`ex::connect` 找不到定制点而编译失败），成员 `connect` 版应可编译；把命令与输出记进本文件 |

> [!warning] 更正（2026-09-13）：本表原三行的表述为「P2300 → IS 进度：…（GCC 12+/Clang 15+/MSVC 19.35+ 区间为社区实测带，精确下限待确认）」「语言级竞争方案：LEWG 有意让新 API 回归语言级定制点而非 tag_invoke（方向讨论进行中，具体提案号待确认）→ 新代码建议把业务逻辑包在自由函数里、tag_invoke 只留薄壳，降低未来迁移面」「生态：NVIDIA stdexec 最活跃；…」。其中「回归语言级定制点」的猜测已被 P2855/P2999 证伪（改为**成员函数 + 域**，不是语言级定制点）。

> 来源：cppreference「C++26」（逐编译器支持表）https://en.cppreference.com/w/cpp/26 ；设计修改 P3109R0 https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2024/p3109r0.html

## 七、学习路径建议

1. 读 P2300 §3 motivation（半天）→ 2. 跑通 stdexec quick-start 十个例子（半天）→ 3. 手写一个 `retry_sender`（1 天，本文 §四骨架起步）→ 4. 给 LogNet PoC 写 stdexec 版 P1 流水线对照压测 → 5. 追踪 execution 进 IS 的措辞变化再定产线版本

## 待确认项汇总

> ① ~~`std::tag_invoke` 是否随 execution 进入 IS 及版本号~~（2026-09-13 收口：tag_invoke 已从设计中移除，"随 execution 落地"不成立）；② 各编译器对 P2300 的精确支持矩阵（查 cppreference「C++26」逐编译器表的 partial 标记）；③ ~~LEWG 语言级定制点方向的提案编号~~（2026-09-13 收口：方向已成定局=成员函数 + 域，P2855/P2999/P3109）；④ reg-free 场景外（见 COM 文档）无关项不列。

## 反向链接

- [[lognet-rootcause-multiagent-architecture]] — Sidecar 流水线的结构化并发候选
- [[log-analysis-agent-windows-architecture]] · [[opencode-pi-base-development-analysis]] — 服务端语言选型上下文
- [[参考-COM组件框架-Windows集成]] — 同期入库 Windows 侧框架知识

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 摘要与 §一/§三/§四 以「execution 的扩展缝=CPO + tag_invoke」为标题级命题，示例写 `friend tag_invoke(ex::connect_t, …)` | 补正为「成员 `connect` + 域（`default_domain`/`transform_sender`/`transform_env`）+ 查询对象 `query` 成员」，旧段落整体保留作迁移对照；依据 P3109R0 改动表（P2855 Remove the tag_invoke ADL-based CPs）与 [exec.connect]/6 |
| 纠错 | §三 适配器清单含 `ensure_started`、`split`、`stop_when` | 三名字处置：P2519 删 `ensure_started`、P3682R0（2025-06）删 `split`（同一血脉，一次清掉）、`stop_when` 为 exposition-only 不可调用；清单换成 [exec.adapt] 现行集合 |
| 纠错 | §三 消费端写 `sync_wait_with_dynamic` | 正名 `sync_wait` / `sync_wait_with_variant`，并补三条生产边界；依据 [exec.sync.wait] |
| 纠错 | §五 写 `get_forward_progress_guarantee`（…/weakly-sequential） | 第三值正名 `weakly_parallel`，并补三值语义差；依据 [exec.get.fwd.progress] |
| 补疏漏 | 全文 19 处 tag_invoke、0 处 domain/transform_sender/transform_env | 新增 §三「定制机制更替」小节：域的选择、`transform_sender` 与成员 `connect` 分工、何时写域、四行迁移对照表；依据 [exec.snd]/P2999 |
| 加厚 | §六 三行全以「待确认」收口 | 四处收敛：删 LEWG 猜测改为既成事实、编译器支持改引 cppreference 逐编译器表、stdexec 生态补 P2300R10 起改成员 connect、给 `-std=c++26` 编译 `retry_sender` 的可执行验收 |

回链：[[CORRECTIONS]] · [[AGENTS]]
