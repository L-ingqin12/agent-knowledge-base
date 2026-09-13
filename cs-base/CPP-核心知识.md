---
title: C++核心知识
aliases: [现代C++, CPP基础, cpp-core]
tags: [cs/cpp, cs]
created: 2026-08-26
updated: 2026-09-13
status: review
source: 教科书级标准事实整理（ISO C++11/17/20/23 口径）；机制类论断以 cppreference/cpdishes 社区共识为准，存疑处标待确认
fetched_at: 2026-08-26
---

# C++ 核心知识

> [!abstract] 定位
> 现代 C++（11→23）主干知识地图：资源管理、移动语义、模板与泛型、并发内存模型、工程实践坑位。深度专题见姊妹篇 [[参考-CPP-CPO定制点与std-execution]]；Windows COM 场景见 [[参考-COM组件框架-Windows集成]]。

See also: [[CS-KB-Home]] · [[参考-CPP-CPO定制点与std-execution]] · [[数据结构与算法]] · [[高并发系统设计]]

## 一、资源管理（RAII 是一切的地基）

| 设施 | 要点 | 口诀 |
|------|------|------|
| 构造/析构 | 资源获取即初始化；析构默认不抛（`noexcept` 违约即 terminate） | 谁拥有谁释放 |
| `unique_ptr` | 独占所有权，零开销；`make_unique` 异常安全 | 默认选择 |
| `shared_ptr` | 引用计数原子操作（有开销）；**循环引用**靠 `weak_ptr` 破 | 共享才用 |
| `weak_ptr` | 不持计数，`lock()` 临时提升 | 观察者/缓存 |
| 自定义删除器 | FILE/socket/句柄包成 RAII 类或 unique_ptr + deleter | 句柄必包 |

> [!danger] 高频坑
> ① `shared_ptr` 的计数线程安全 ≠ 对象本身线程安全；② `get()` 裸指针逃逸后 delete 双释放；③ 构造函数中调用虚函数不具多态性（派生层未构造）。

## 二、值语义与移动语义

- 左值/右值/将亡值：`T&&` 绑定右值；移动构造"偷资源后置空源"
- `std::move` 只是转 rvalue 强制转换（不移动任何东西）；被移动对象=有效但未定状态
- 完美转发：万能引用 `template<class T> f(T&&)` + `std::forward<T>` 保值类别传递
- RVO/NRVO 与 C++17 强制拷贝消除：返回临时值不再调用移动构造
- 五法则/零法则：写了自定义析构/拷贝/移动之一 → 考虑全五个；能用成员 RAII 就一个都不写（零法则）

## 三、模板与泛型

| 主题 | 关键点 |
|------|--------|
| 类型萃取 | `<type_traits>`：`decay/remove_reference/conditional` 编译期计算 |
| SFINAE→concepts | C++20 `requires` 子句取代 enable_if 黑魔法，报错可读 |
| 变参模板 | 参数包展开；折叠表达式 `(args + ...)` |
| CTAD | `std::lock_guard lg(m);` 类模板实参推导 |
| 两阶段查找 | 依赖名须 `this->`/限定，否则二期查找不到（经典编译错） |

## 四、并发与内存模型（对接 [[高并发系统设计]]）

- `std::thread/jthread`（jthread 自动 join+stop_token 协作取消）
- **内存序**五档：relaxed / acquire / release / acq_rel / seq_cst（默认）；acquire 读、release 写构成同步于 happens-before。`memory_order_consume` 不用学：现行草案的枚举里已没有它（枚举值 1 空出），历史上它与 acquire 等价、且已被建议弃用。
- 锁族：`mutex/recursive/shared(shared_mutex 读写锁)/scoped_lock 多锁防死锁`
- 条件变量三件套：`unique_lock<mutex>` + `cv.wait(lk, pred)` **谓词版必带**（防虚假唤醒）
- async/future/promise；`launch::deferred vs async` 执行策略差异；**future 析构语义要按来源分两类**：`std::async` 返回的 future 若未移出局部作用域，析构可能阻塞到共享状态就绪（是"隐式等待"，不是"析构不 join"）；只有来自 `packaged_task`/`promise` 等其他来源的 future，析构才从不阻塞
  - 反例：`auto h = std::async(...); work1(); h.get();` —— 默认策略可能落到 `launch::deferred`，此时两段工作在同一线程串行执行，没有并发

> [!warning] 更正（2026-09-13）：原表述为「**内存序**六档：relaxed / acquire-release 配对 / seq_cst 默认」，既称六档却只列了三项，且全文未提 consume。依 C++ 现行草案 [atomics.order]（https://eel.is/c++draft/atomics.order），`enum class memory_order` 只有 relaxed / acquire / release / acq_rel / seq_cst 五个枚举值。

> [!warning] 更正（2026-09-13）：原表述为「future 析构不 join 的 async 特例（**经典陷阱**）」，方向写反。依草案 [futures.async]/5 Note 2（https://eel.is/c++draft/futures.async）：async 取得的 future 被移出局部作用域时，其析构**可以阻塞**等待共享状态就绪；不阻塞的是其他来源的 future。

## 五、工程实践速查

| 主题 | 结论 |
|------|------|
| 初始化 | 用 `{}` 防 narrowing；类内成员默认初始化防 UB |
| 字符串 | `string_view` 免拷贝传参（注意悬垂：不存临时）；SSO 小串栈上分配 |
| 容器选型 | 连续优先（vector/string）cache 友好；`reserve` 预扩容；map vs unordered_map 按有序需求与哈希攻击面取舍 |
| ABI/编译 | `-O2` 起步；sanitizers：ASan(内存)/TSan(数据竞争)/UBSan 全套进 CI |
| 标准 | 项目锁定单一标准版本；C++23 主要件：`expected/print/mdspan` |

## 六、新特性纵深（C++11 → 26：每代解决什么，怎么用对）

### 演进主线一句话
11 立语言现代化（移动/lambda/智能指针）→ 14 补漏 → 17 工程化（结构化绑定/optional）→ 20 范式跃迁（concepts/ranges/coroutines/modules）→ 23 易用性收官（expected/print/deducing this）→ 26 反射已收录（P2996 已进 C++26 工作草案，头文件 `<meta>`）。

### 必须用对的十件事（附反例）
| 特性 | 正确用法 | 反面案例 |
|------|---------|---------|
| 移动语义 | 移后即弃源对象；容器扩容自动受益 | 对 const 对象 std::move（退化成拷贝） |
| lambda | 默认按值捕获+mutable；异步场景**显式捕获 shared_from_this** | `[&]` 引用逃逸出作用域→悬垂 |
| constexpr | 编译期查表/静态配置 | 把 IO 塞进 constexpr 函数幻想优化 |
| structured bindings | `auto [k,v] : map` | 绑定到临时对象再长期持有 |
| optional/variant | 替换哨兵值与 union 手艺 | .value() 不检查直接炸（应 value_or） |
| string_view | 免拷贝入参 | **存下 view 指向临时 string**（悬垂重灾区） |
| span | 数组段抽象替代 ptr+len 双参 | 同上，不拥有内存 |
| concepts | `template<CComparable T>` 报错可读 | 概念里塞运行期才可知的约束 |
| coroutines(20) | co_await 封装 IO；框架层(asio)消费 | 裸写 promise_type（极易错，用库） |
| modules(20/23) | 隔离宏泄漏、加速构建 | 与 unity build/ccache 生态混用踩坑 |

### C++23 落地清单（项目可直接吃）
- `std::expected<T,E>`：错误通道标准化——替换自研 result 类型（错误码+值双轨终结）
- `std::print/println`：格式化输出统一 i18n 安全
- `deducing this`：显式对象形参，CRGB 类模板递归简化、ref-qualified 去重载
- `std::mdspan`：多维视图（数值/图像路径）
- stacktrace：异常带栈（配合 [[LLVM编译器基础设施]] 符号化）

### C++26 展望（跟踪不押注）
反射已收录（P2996 进 C++26 工作草案，头文件 `<meta>`）/契约（`<contracts>`）/std::execution 入 IS（已进工作草案；作为 IS 正式发布仍未定）——生产采用按下表分档，新代码按 [[参考-CPP-CPO定制点与std-execution]] 的迁移建议留薄壳。

> [!warning] 更正（2026-09-13）：原表述为「反射(P2996 进展中)」「26 反射在路上」。反射已是 C++26 的既定内容，不再是"在路上/进展中"——要跟踪的不再是"是否进标准"，而是"各编译器实现进度"。依 cppreference「C++26」页的库头文件清单（https://en.cppreference.com/w/cpp/26）：`<meta>`、`<execution>`、`<contracts>`、`<hive>`、`<inplace_vector>`、`<linalg>`、`<rcu>`、`<simd>`、`<text_encoding>`、`<stdbit.h>`、`<stdckdint.h>` 均已列入。

**C++26 可落地库件一览**（解决什么问题 / 语言还是库 / 今天能否用）

| 头文件 | 解决什么问题 | 类型 | 今天能否用 |
|---|---|---|---|
| `<meta>` | 编译期反射（P2996）：类型与成员信息可枚举 | 库 + 语言机制 | 主流编译器未齐；原型可走 bloomberg/clang-p2996 分支 |
| `<contracts>` | 前置/后置条件与契约断言（P2900） | 库 + 语言机制 | 未见生产实现；回退 `assert`/gsl `Expects` |
| `<execution>` | sender/receiver 异步与并行（P2300） | 纯库 | 上游 stdexec 可先吃；迁移见 [[参考-CPP-CPO定制点与std-execution]] |
| `<hive>` | 元素地址稳定的无序容器（增删不失效） | 纯库 | 回退 `std::list`/`deque` + 索引池 |
| `<inplace_vector>` | 定容 vector（内联存储、无堆分配） | 纯库 | 回退 `std::array`+手工 size，或 `boost::static_vector` |
| `<simd>` | 数据并行类型（`std::simd`） | 纯库 | 回退编译器 vector 扩展 / `std::experimental::simd` |
| `<linalg>` | 稠密线性代数（BLAS 后端） | 纯库 | 回退 Eigen / 直接调 BLAS |
| `<rcu>` | 读多写少的 RCU 同步原语 | 纯库 | 回退 `shared_mutex` / `atomic<shared_ptr>` |
| `<text_encoding>` | 查询平台文本编码（替代 `codecvt` 手艺） | 纯库 | 回退 iconv / ICU 探测 |
| `<stdbit.h>` / `<stdckdint.h>` | C23 位操作与带溢出检查的整数运算 | 纯库 | 回退 `__builtin_*`（如 `__builtin_add_overflow`） |

**编译器落地三档（判据 + 回退）**：逐编译器版本号与 partial 标记以 cppreference「C++26」页自带的支持表为准（本环境抓取该页失败，故不在此抄录版本号，落地前现场核对）。

| 档 | 判据（可验收） | 回退方案 |
|---|---|---|
| 可生产 | 目标编译器在该页标为完整支持，且本项目用到的库件能用 `-std=c++26` 编译并跑通回归 | 直接采用 |
| 需厂家实现验证 | 该页标 partial，或只在 nightly/分支里可用 | `std::print` 缺→`{fmt}`；`std::execution` 缺→`stdexec`；`<inplace_vector>` 缺→`boost::static_vector`；反射缺→bloomberg/clang-p2996 分支做原型 |
| 暂不可用 | 无任何实现可跑通最小用例 | 维持 C++20/23 基线，接口留薄壳，逐条按上表回退 |

> 来源：cppreference「C++26」（C++26 库头文件清单 + 逐编译器支持表）https://en.cppreference.com/w/cpp/26 ；内存序与 future 语义分别取草案 [atomics.order]、[futures.async]。

## 七、待确认项

> ① 各编译器对 C++20 modules 的生产可用度差异；② coroutine TS→C++20 无栈协程在主流库（asio/cppcoro）的封装成熟度；③ 硬件内存模型（TSO/ARM 弱序）与 C++ 序映射的逐平台对照表。

> [!success] 残余复核（2026-09-13）：三条**全部就地定论**——①② 由权威页面 + 本机实测收口，③ 收口为"两档口径 + 权威模型来源"。
> - **① 已定论：生产可用度的差异就在"只有 MSVC 标为完整支持"**。依 cppreference「C++20 compiler support」的 Modules（P1103R3）行（2026-09-13 取回）：GCC **11 (partial)**、Clang **8 (partial)**、MSVC 19.0(2015)* (partial) → 19.10*（仅 Modules TS）→ **19.28 (16.8)=VS2019 16.8 起**（该格绿底=完整支持）、Apple Clang 10.0.1* (partial)、Intel C++ 2023.1 (partial)、EDG eccp 与 Nvidia HPC 无支持。本机实测互证：clang 22.1.0-rc3（llvm-mingw，libc++）`clang++ -std=c++20 --precompile m.cppm -o m.pcm` + `clang++ -std=c++20 -fprebuilt-module-path=. use.cpp m.pcm -o usem` 端到端跑通（输出 `answer=42`），且发行版随附 `share/libc++/v1/std.cppm`、`std.compat.cppm`、`libc++.modules.json`；gcc 12.2 用 `gcc -std=c++20 -fmodules-ts -x c++` 亦端到端跑通，模块缓存落在**当前工作目录** `gcm.cache/`。缓存侧的短板见 [[LLVM使用调优与SO优化]] §一（ccache 官方手册明言不支持标准 C++20 modules）；本机 CMake 4.1.2 已有 `CXX_SCAN_FOR_MODULES`（3.28 起）与 `CXX_MODULE_STD`。
> - **② 已定论：asio 活跃且在维护 C++20 协程面，cppcoro 已停更**。本次取回（2026-09-13）：asio 仓库最后推送 2026-07-18（未归档），源码树中 `include/asio/co_spawn.hpp`、`include/asio/awaitable.hpp` 均存在（HTTP 200）——C++20 无栈协程的封装入口是真实且现役的；cppcoro（lewissbaker/cppcoro）最后推送 **2024-01-09**，仓库描述仍写着 "a library of C++ coroutine abstractions for the **coroutines TS**"，即 TS 时代产物、不再跟进 C++20 语义。选型上应直接对接 stdexec（[[参考-CPP-CPO定制点与std-execution]] §四），不押 cppcoro。
> - **③ 已定论（两档口径 + 权威来源）**：cppreference `std::memory_order`（2026-09-13 取回）原文——「On strongly-ordered systems — x86, SPARC TSO, IBM mainframe, etc. — release-acquire ordering is automatic for the majority of operations. No additional CPU instructions are issued for this synchronization mode」；「On weakly-ordered systems (ARM, Itanium, PowerPC), special CPU load or memory fence instructions are used」。逐平台明细的权威来源即该页 External links 的两篇模型论文（Sewell 等《x86-TSO: A Rigorous and Usable Programmer's Model for x86 Multiprocessors》2010、《A Tutorial Introduction to the ARM and POWER Relaxed Memory Models》），本文不另造表；要落到自家微架构仍以 litmus7/herd7 实测为准（[[LLVM使用调优与SO优化]] §四 的单变量纪律）。

## Related

[[CS-KB-Home]] · [[参考-CPP-CPO定制点与std-execution]] · [[参考-COM组件框架-Windows集成]] · [[操作系统八股]] · [[高并发系统设计]] · [[lognet-rootcause-multiagent-architecture]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §六 把反射写成「在路上 / P2996 进展中」 | 改为「已收录（P2996 工作草案，`<meta>`）」，不确定性移到编译器实现进度；依据 cppreference「C++26」页头文件清单 |
| 纠错 | §四 称内存序「六档」却只列三项，且无 consume 说明 | 改为五档完整清单 + 「consume 不用学」；依据草案 [atomics.order]（枚举仅 5 值） |
| 纠错 | §四 写「future 析构不 join 的 async 特例」 | 方向写反：async 的 future 析构可能阻塞，其他来源才不阻塞；依据草案 [futures.async]/5 Note 2，并补最小反例 |
| 加厚 | §六 展望只有一句话，无库件清单、无编译器矩阵 | 补「C++26 库件一览表」与「编译器落地三档（判据+回退）」；依据同页逐编译器支持表 |
| 残余复核 | §七① 各编译器对 C++20 modules 的生产可用度差异 | 定论：cppreference「C++20 compiler support」Modules(P1103R3) 行=GCC 11 (partial)、Clang 8 (partial)、MSVC 19.28/VS2019 16.8 起完整、Apple Clang 10.0.1 (partial)、Intel 2023.1 (partial)、EDG/Nvidia 无；本机 clang 22.1.0-rc3＋libc++ 与 gcc 12.2（`-fmodules-ts`）均端到端实测通过，缓存落工作目录 `gcm.cache/` |
| 残余复核 | §七② asio/cppcoro 对 C++20 无栈协程的封装成熟度 | 定论：asio 活跃（最后推送 2026-07-18）且 `include/asio/co_spawn.hpp`、`awaitable.hpp` 现役（200）；cppcoro 停更（最后推送 2024-01-09，描述仍为 coroutines TS）→ 选型对接 stdexec |
| 残余复核 | §七③ TSO/ARM 弱序与 C++ 序映射的逐平台对照表 | 定论为口径+来源：cppreference `std::memory_order` 的两档原文（强序 x86/SPARC TSO 无需额外指令；弱序 ARM/Itanium/PowerPC 用 fence/acquire 指令）+ 其 External links 的 Sewell《x86-TSO》2010 与 ARM/POWER relaxed 模型教程；微架构明细仍以 litmus 实测为准 |

回链：[[CORRECTIONS]] · [[AGENTS]]
