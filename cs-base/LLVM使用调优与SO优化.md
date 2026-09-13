---
title: LLVM使用调优与SO优化
aliases: [clang调优, so优化, 编译期工程]
tags: [cs/toolchain, cs]
created: 2026-08-26
updated: 2026-09-13
status: review
source: clang/lld 官方文档与工业实践共识；效果量级为常见经验区间，须以自家基准回归为准
fetched_at: 2026-08-26
---

# LLVM 使用调优与 SO 优化

> [!abstract] 定位
> 从"会编译"到"会调编译"：flag 分层决策、共享库(.so) 的符号面/体积/启动时间/ABI 四维优化、PGO-LTO-BOLT 三引擎、性能回归工作流。理论架构见 [[LLVM编译器基础设施]]，链接加载语义见 [[LibC与动态链接]]，运行时故障见 [[LibC运行时排查-TLS与锁]]。

See also: [[CS-KB-Home]] · [[CPP-核心知识]] · [[计算机组成原理]] · [[lognet-rootcause-multiagent-architecture]]

## 一、Flag 分层决策（不要背清单，要懂分层）

| 层 | 代表 flag | 决策逻辑 |
|----|-----------|---------|
| 代码生成 | `-O2`(默认发布)/`-Oz`(体积)/`-march=native`/`-ffast-math` | fast-math 破坏 IEEE 语义（[[计算机组成原理]] §一）——数值库禁用；`-O3` 对分支密集代码可能因 icache 膨胀反而慢，**必须实测** |
| 可观测 | `-g -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer` | perf 栈回放的前提；发布版也保留 fp 的开销通常可忽略 |
| 硬化 | `-fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE -Wl,-z,relro,-z,now` | 对照 [[LibC与动态链接]] §四 |
| 工程 | `-Wall -Wextra -Wpedantic -Werror` + `-std=c++20` + `compile_commands.json` | clangd/IDE 一致性；警告即债务可视化 |

构建加速：ccache(内容寻址缓存) → 命中率看 `ccache -s`；模块接口单元(modules)是下一代方案但生态未稳（**待确认**）。

> [!success] 残余复核（2026-09-13）：这条「生态未稳」的软标记已拆成三段硬验收并逐段定论——**编译器腿通、构建系统腿通、缓存腿有官方结论（缺）**：
> - 编译器腿：本机 clang 22.1.0-rc3（libc++ 同版本）跑通 module interface unit 全链路，`clang++ -std=c++20 --precompile m.cppm -o m.pcm` 再 `clang++ -std=c++20 -fprebuilt-module-path=. use.cpp m.pcm -o usem`；发行版还随附 `share/libc++/v1/std.cppm`、`std.compat.cppm` 与 `libc++.modules.json`，`import std;` 的原料齐备。
> - 构建系统腿：本机 CMake 4.1.2 已有 `CXX_SCAN_FOR_MODULES`（3.28 起）与 `CXX_MODULE_STD`（`cmake --help-property CXX_SCAN_FOR_MODULES` 可回显文档）。
> - 缓存腿（已拿到官方口径，不必再猜）：ccache 官方手册（ccache.dev/manual/latest.html，2026-09-13 取回）原文——「**Ccache does currently not support standard C++20 modules.** There is however limited support for "Clang modules" (the `-fmodules` option)」，且用它的前提是 `sloppiness=modules` + direct mode + depend mode，机制上它只 hash `module.modulemap`、忽略 Clang 的二进制模块缓存；本机另实测 GCC 12.2 的 `-fmodules-ts` 缓存也只是一个工作目录 `gcm.cache/`（产物 `gcm.cache/mm.gcm`），无共享/分布式接口。结论：**modules 的"分布式缓存"目前确实是缺的那条腿**——"生态未稳"该保留的正是这一条具体判断，而不是一句笼统印象（§七③ 同源）。
> 落地时按这三条逐项目核。

## 二、SO 优化四维（重点章）

### 维度 1：符号面收敛（收益最大且免费）
```cpp
// 全局默认隐藏 —— visibility 只在编译每个 TU 时生效
add_compile_options(-fvisibility=hidden -fvisibility-inlines-hidden)

// API 头文件显式导出宏
#define MYAPI __attribute__((visibility("default")))
MYAPI int plugin_init(...);
```
- 收益链：动态符号表缩小 → ld.so 重定位条目减少(**启动加快**) → GOT 缩小 → 库内调用可在 LTO 时跨 TU 内联 → 符号劫持攻击面消失
- 进一步精确控制：**版本脚本** `--version-script=map.txt`（`{ global: plugin_*; local: *; };`）
- 自查命令：收缩前后 `nm -DC --defined-only lib.so | wc -l`；泄漏检测用 `nm -D --undefined-only`

### 维度 2：体积
```
-fdata-sections -ffunction-sections   # 每函数/数据独立 section
-Wl,--gc-sections                     # 未引用段剥离
-Wl,--icf=safe                        # 相同代码折叠(lld)：默认档其实是 --icf=none，safe 依赖 clang 默认发射的 .llvm_addrsig 地址显著性表
# -Wl,--icf=all                       # 激进折叠：会合并地址不同的函数，破坏"函数地址唯一"假设，须显式接受风险
-Oz + strip                           # 极限体积路径
bloaty lib.so -- base.so              # 体积 diff 归因到符号
```
- `--icf` 三档：`none`（默认）/`safe`（工程建议默认，靠 `.llvm_addrsig` 判定安全）/`all`（即使地址不同也合并）。另有两个"接受不安全优化"的开关：`--ignore-function-address-equality`（非 PIC 调用 / 共享对象场景）与 `--ignore-data-address-equality`（lld man 里 "allows lld to do unsafe optimization that breaks the requirement" 这句属于**后者**，别抄到函数版上）；`--keep-unique=symbol` 可做折叠白名单
- 上 `all` 的前提是"代码里没有函数指针相等比较 + 有回归测试覆盖"；验收用开关前后 `nm -DC --defined-only lib.so | wc -l` 计数对比 + 全量回归
- 典型结果：未收敛符号面的 C++ so 收缩 20–40%（模板实例是重灾区）。

> 来源（`--icf` 三档与不安全优化开关）：ld.lld man 页 https://manpages.debian.org/unstable/lld-19/ld.lld-19.1.en.html

### 维度 3：启动时间
- ld.so 成本 ≈ 重定位处理 + 符号解析 + init_array 执行：
  ① 减 RELATIVE 条目（少导出数据指针、位置无关数据进 .rodata）
  ② 懒绑定默认开启——但安全要求 `-z now` 后变全量急解析：**高安全 so 用 `-z now`+更小符号面来抵消**
  ③ `.init_array` 里禁止重活（全局构造做 IO/建线程池=启动毒药）→ 惰性初始化(pimpl 内首次调用构造)
  ④ 依赖树裁剪：`ldd` 里每多一层 DT_NEEDED 就多一轮 BFS；`--as-needed` 清理"链了没用"的库

### 维度 4：ABI 稳定（跨版本 so 的生死线）
| 手法 | 说明 |
|------|------|
| pimpl | 头文件只留 `unique_ptr<Impl>`——成员变更不破坏 ABI |
| 抽象接口类 | 纯虚+工厂函数导出，实现全隐藏 |
| inline namespace 版本化 | `inline namespace v2 {}` 符号名带版本便于共存 |
| abi-compliance-checker / libabigail | 两 release 的 ABI diff 门禁进 CI |
| `_GLIBCXX_USE_CXX11_ABI` | 双 std::string ABI 经典坑：混载即崩溃，全项目必须统一 |

## 三、PGO / LTO / BOLT 三引擎

| 引擎 | 输入 | 典型增益 | 代价 / 前置约束 |
|------|------|---------|------|
| ThinLTO | `-flto=thin` 全链(clang+lld) | 跨 TU 内联/DCE，5–15% | 链接内存↑；符号面先收敛才吃满 |
| PGO(instr/AutoFDO) | 真实流量 profile | 分支布局+内联重排 10–30%(热点型) | 需代表性负载采集管线 |
| BOLT | 已发布二进制 + perf 采样（x86 用 LBR，AArch64 用 BRBE） | 再排布 5–20% | 目标平台是 **x86-64 与 AArch64 ELF**（不是"仅 x86-64 成熟"）；前置约束四条见下 |

BOLT 的输入要求（README 的 Input Binary Requirements，逐条都是"无需重编"之外的隐藏条件）：① 二进制须带**未剥离符号表**；② 要拿满收益要求原始链接带**重定位**（`--emit-relocs` 或 `-q`），这本身就是构建期改动——"无需重编"只在当初就为此链接过时成立；③ 与 `-freorder-blocks-and-partition` **不兼容**（GCC 8 起默认开启，须显式 `-fno-reorder-blocks-and-partition`）；④ profile 与二进制不一致会产生 **stale profile**（BOLT 会报 stale 函数数、收益下滑），发布分支必须刷新 `.fdata`。

> [!warning] 更正（2026-09-13）：原写作「BOLT | 无需重编(perf LBR 采样) | 已发布二进制再排布 5–20% | 代价：仅 x86-64 Linux 成熟」。平台口径已过期——BOLT README 原文为 "BOLT operates on X86-64 and AArch64 ELF binaries."，采样也对应 x86 LBR / AArch64 BRBE 两条路径。来源：https://api.github.com/repos/llvm/llvm-project/contents/bolt/README.md

组合顺序惯例：LTO 打底 → PGO 热点重排 → （存量包）BOLT 兜底。

## 四、性能回归工作流（单变量纪律）

```
0. 固定基准: google-benchmark + 固定机器/隔离核(taskset)
1. perf record -F997 -g ./bench → report/TMA 归因(见[[计算机组成原理]]§七)
2. 假设驱动改一个变量(如 -O2→-O3 / 加 PGO / march=x86-64-v3)
3. 统计显著性: 多轮取分布, 看中位数±噪声带宽, 不看单次
4. 产物三件套归档: bench 结果 + build-id + flag diff —— 可追溯可回滚
```

## 五、SO 排障速查

| 症状 | 根因域 | 动作 |
|------|--------|------|
| 运行期 `undefined symbol` | 导出面/依赖序 | `ldd -r` 定位；`nm -D` 对账；检查 `--no-undefined` 为何没开 |
| 两份 libstdc++ 共存崩溃 | 混载 | `lsof \| grep c++`；LD_DEBUG=libs 看谁先占位 |
| ODR 违例偶发错值 | 不同 TU 同符号不同定义 | ASan detect_odr_violation；visibility hidden 治本 |
| 升级 so 后老程序崩 | ABI 破坏 | abidiff 两版本；pimpl 重构治本 |
| so 启动拖慢主程序 | §维度3 | `LD_DEBUG=statistics` 看重定位计数 |

## 六、与本库的落点

- LogNet PoC 当前 Python 实现：若 M1 走 native 符号化工具链（[[lognet-rootcause-multiagent-architecture]]），addr2line 类工具的构建即本文 §六符号闭环；Sidecar 若以 C++ 插件承载解析器，§二符号面收敛+§维度4 pimpl 是插件 ABI 不崩的前提
- Windows 对应概念映射：dllexport/dllimport≈visibility 宏、.pdb≈分离 debuginfo、DLL hell≈so 版本地狱（[[参考-COM组件框架-Windows集成]]）

## 七、待确认项

> ① clang 18+ -fsanitize=address 与 PGO 并用的兼容矩阵；② BOLT 对 PIE+静态链接混合场景支持进度；③ modules 大规模项目的分布式缓存(ccache 类)方案成熟度。

> [!success] 残余复核（2026-09-13）：① 已用本机最小实验定论——**clang 22.1.0-rc3 下 ASan 与 PGO 可并用，采集-合并-使用的整条链路都通**：`clang++ -O2 -fsanitize=address -fprofile-instr-generate pgo.c -o pgo_gen` → 运行并写 `pgo.profraw` → `llvm-profdata merge -o pgo.profdata pgo.profraw` → `clang++ -O2 -fsanitize=address -fprofile-instr-use=pgo.profdata pgo.c -o pgo_use`，最终二进制正常运行。故"兼容矩阵"的残余只剩**逐版本回归**：把上面四条命令做成脚本，在 CI 里对每个 clang 大版本跑一遍即可（注意 profile 必须在与使用侧同档的 sanitizer 配置下采集，否则会退化成 out-of-date profile 而不是编译失败，容易误判为"通过"）。

> [!success] 残余复核（2026-09-13）：②③ 均已收口（都拿到了上游原文，不再需要"待确认"）。
> - **② BOLT × PIE（+静态）**：BOLT README（`llvm/llvm-project` 的 `bolt/README.md`，2026-09-13 取回）在「Input Binary Requirements」里对 PIE/.so 的原话是「**PIE and .so support has been added recently. Please report bugs if you encounter any issues.**」——即"最近才加、仍在收 bug"的进度，这正好解释了为何它不能与 `-freorder-blocks-and-partition` 并存（README 同段明确不兼容）。而 **`static` 一词在该 README 中出现 0 次**：静态链接（含 `-static-pie` 混合场景）没有被单独承诺，属未列入口径。判据（复跑）：读该 README 原文，并在带 BOLT 的 LLVM 上对 `-static-pie` 产物跑 `llvm-bolt app -o app.bolt --reorder-blocks=ext-tsp`，看是否报 stale/cannot find relocations 类信息。
> - **③ modules 的分布式缓存**：ccache 官方手册（ccache.dev/manual/latest.html，2026-09-13 取回）明写「**Ccache does currently not support standard C++20 modules.**」，只对 Clang `-fmodules` 有有限支持（要求 `sloppiness=modules` + direct mode + depend mode，且只 hash `module.modulemap`、忽略二进制模块缓存）；机制侧另有一条实测：GCC 12.2 的 `-fmodules-ts` 缓存就是一个工作目录 `gcm.cache/`，clang 侧 `.pcm`/`.pch` 全交给构建系统管（CMake 4.1.2 的 `CXX_SCAN_FOR_MODULES` 只扫依赖、不缓存内容）。故该项结论=**标准 C++20 modules 目前没有成熟的分布式缓存方案**；判据（复跑）：`grep -i "C++ modules" ccache 手册`，以及升级 ccache 后看其是否出现 module 计数。

## Related

[[CS-KB-Home]] · [[LLVM编译器基础设施]] · [[LibC运行时排查-TLS与锁]] · [[CPP-核心知识]] · [[lognet-rootcause-multiagent-architecture]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §三 表称 BOLT「仅 x86-64 Linux 成熟」 | 改为 x86-64 **与 AArch64** ELF，并把采样路径写全（x86 LBR / AArch64 BRBE）；依据 BOLT README「BOLT operates on X86-64 and AArch64 ELF binaries.」 |
| 补疏漏 | §三 把「无需重编」写成零前置条件 | 补 README 的四条输入要求：未剥离符号表、需 `--emit-relocs`/`-q` 重定位、与 `-freorder-blocks-and-partition` 不兼容、stale profile 需刷新 `.fdata` |
| 加厚 | §维度2 只给 `-Wl,--icf=all` 一行，无档位与失败模式 | 补三档（`none` 默认 / `safe` 建议 / `all` 激进）、两个 unsafe 开关的归属辨析、`--keep-unique`、上 `all` 的前提与 `nm -DC` 验收；依据 ld.lld man 页 |
| 残余复核 | §一「模块接口单元(modules)是下一代方案但生态未稳（待确认）」 | 拆成三段硬验收并逐段定论：编译器腿✓（本机 clang 22.1.0-rc3＋libc++ 的 `--precompile`+import 端到端输出 `answer=42`）、构建系统腿✓（CMake 4.1.2 具备 `CXX_SCAN_FOR_MODULES`/`CXX_MODULE_STD`）、缓存腿✗（ccache 官方手册明写不支持标准 C++20 modules；GCC 的 `-fmodules-ts` 缓存只是工作目录 `gcm.cache/`） |
| 残余复核 | §七① clang 18+ 的 ASan 与 PGO 并用兼容矩阵 | 最小实验定论（clang 22.1.0-rc3）：`-fsanitize=address -fprofile-instr-generate` → 运行出 `pgo.profraw` → `llvm-profdata merge` → `-fsanitize=address -fprofile-instr-use` 编译并运行成功；残余只是逐大版本回归（同一组命令脚本化） |
| 残余复核 | §七② BOLT 对 PIE+静态链接混合场景的支持进度 | 已收口：BOLT README 原文「PIE and .so support has been added recently. Please report bugs if you encounter any issues.」＝实验期；且 README 全文 `static` 出现 0 次——静态链接（含 `-static-pie` 混合）无单独承诺 |
| 残余复核 | §七③ modules 大规模项目的分布式缓存(ccache 类)成熟度 | 已收口：ccache 手册明写「Ccache does currently not support standard C++20 modules」，仅对 Clang `-fmodules` 有限支持（`sloppiness=modules`+direct+depend）；GCC 模块缓存=工作目录 `gcm.cache/`，CMake 只扫依赖不缓存内容 |

回链：[[CORRECTIONS]] · [[AGENTS]]
