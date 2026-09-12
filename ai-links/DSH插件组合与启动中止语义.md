---
title: DSH 插件组合与启动中止语义
aliases: [DSH组合模型, Cordis启动语义, 插件加载失败]
tags: [ai/tools, ai/agent]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# DSH 插件组合与启动中止语义

See also: [[AI-Links-KB-Home]] | [[DSH插件与Hook开发最佳实践]] | [[DSH-TUI插件使用手册]] | [[DSH会话脱敏插件缺陷档案]] | [[DSH工具结果管线与meta陷阱]] | [[CORRECTIONS]]

> [!abstract] 这篇只回答一个问题
> **一行插件是怎么被组合进来、`name` 从哪里解析、以及为什么"一行没起来"会让整个 profile 启动失败。**
> 会话日志格式见 [[DSH会话日志格式与读取端约束]]；TUI 内部机制见 [[DSH-TUI内部机制与键盘卡死陷阱]]。

> [!info] 引用约定（路径简写）
> | 简写 | 实际路径 |
> |---|---|
> | `dsh/` | `C:\%USERPROFILE%\nodejs-x64\node-v22.21.0-win-x64\node_modules\@deepseek-ai\dsh\` |
> | `pkg/` | `dsh/node_modules/@deepseek-ai/` |
> | `$DSH_HOME` | `C:\%USERPROFILE%\.dsh` |
> | `evidence/` | `C:\%USERPROFILE%\dsh-redaction\docs\reports\boot-verify\` |
>
> 下文 `file:line` 一律相对上表展开。本机 `node`（PATH 上的 v18）**跑不了** DSH 源码，必须用 `C:\%USERPROFILE%\nodejs-x64\node-v22.21.0-win-x64\node.exe`（v22.21.0）。

---

## 一、组合模型：能力 = 一行插件

一个 `cordis.yml` 就是**一个顶层 YAML 数组**，每项是一「行」（loader entry），最少只需 `id` + `name`（`pkg/cordis-plugin-include/lib/index.js:192` 强制数组；行列 schema 见 `pkg/dsh-app-boot/lib/index.js:30`）。

| 行字段 | 作用 |
|---|---|
| `id` | 树内唯一标识，也是**补丁层的靶点**；重名直接抛 `duplicate loader entry id`（`pkg/cordis-plugin-loader/lib/index.js:91`） |
| `name` | 模块定位符（解析规则见第三节）；`cordis:include` / `cordis:group` 是内建名（`pkg/cordis-plugin-loader/lib/index.js:271`） |
| `config` | 传给插件的原始配置，先过 `Config` 校验（第六节） |
| `inject` | **行级**依赖声明，追加语义（第四节） |
| `disabled` | 跳过该行；可以是 `!!js` 表达式（第五节陷阱） |
| `group` + `config: [...]` | 子行容器；`isolate` 与它配套（第七节） |

插件模块导出四个可选成员，框架只在两处读它们：

```js
// pkg/cordis/lib/index.js:1624-1634
let name = plugin.name
if (name === 'apply') name = void 0
runtime = { name, callback, fibers: new DisposableList(), Config: plugin.Config }
const fiber = new Fiber(this.ctx, config, Inject.resolve(plugin.inject), runtime, getOuterStack)
```

- **`apply`** 是被调用的入口。校验形状只认「函数」或「带 `apply` 方法的对象」，否则抛 `invalid plugin, expect function or object with an "apply" method`（`pkg/cordis/lib/index.js:1620`）。调用点在 `_runner.execute`：类插件 `new callback(this.ctx, this.config)`，其余 `callback(this.ctx, this.config)`（`pkg/cordis/lib/index.js:1066-1070`）。
- **`name`** 只用于日志与诊断；模块级 `name` 恰好叫 `apply` 时会被丢弃（`:1625`）。
- **`Config`** 被挂到 `runtime.Config`，是校验的唯一来源（`:1630`）。
- **`inject`** 在 fiber 构造时归一化成 `{服务名: null}` 映射（`pkg/cordis/lib/index.js:1634` + `:1490-1498`）。

`apply` 跑在一个 **Fiber**（一次插件应用的生命周期对象）里，状态由 `_getState()` 反推（`pkg/cordis/lib/index.js:1287-1292`），另有 1/5 两个中间态由 `_updateState` 显式给出：

| state | 含义 | 来源 |
|---|---|---|
| `0` PENDING | 至少一个 `inject` 服务缺席，`apply` **从未执行** | `_getState` 兜底分支；`_refresh` 把 epoch 设为 `INACTIVE`（`pkg/cordis/lib/index.js:1316-1327`） |
| `1` LOADING | 依赖齐了，正在加载 | `:1337` |
| `2` ACTIVE | 正常运行 | `:1290` |
| `3` FAILED | `_error` 已记录（import 或 apply 抛错） | `:1289` |
| `4` / `5` | 已销毁 / 已卸载（依赖消失后回退） | `:1288`、`:1340` |

服务出现时框架自动唤醒等待者：`notify()` 对每个声明了该服务的 fiber 调 `_checkImpl` + `_refresh`（`pkg/cordis/lib/index.js:831-843`）。所以**行在列表里的先后顺序不承载加载语义**（`pkg/dsh-base/cordis.patch.yml:12` 明确写了这一点），激活是「服务可用性驱动」的。

读一个可选服务用 `ctx.get(name)`；它的 `strict` 默认为 `true`，只有提供方 fiber 处于 ACTIVE 才返回实现，否则 `undefined`（`pkg/cordis/lib/index.js:762-771`）。

---

## 二、层级与优先级

`dsh --profile <name>` 的完整补丁栈按此顺序叠加，**后者按行胜出**（`dsh/lib/profile-boot-Dk-7KqJc.js:213-220`、`:232-257`）：

```
1. bundlePatches   ← profile 的 dsh.profile.bundles 列表顺序，逐包一层
2. profile.patches ← <profile>/cordis.patch.yml
3. homePatches     ← $DSH_HOME/cordis.patch.yml（机器级，覆盖所有 profile）
4. overlays        ← 每个 --patch <path>，按 argv 顺序
5. telemetry 开关  ← DSH_TELEMETRY_DISABLED 命中时追加到 overlays 末尾
```

| 层 | 代码 | 备注 |
|---|---|---|
| bundles | `dsh/lib/profile-boot-Dk-7KqJc.js:240`；`dsh plugin` 按**已安装状态**而非依赖差异对账（`dsh/lib/plugin-Ddi42qoW.js:46-78`） | 没声明 `dsh.bundle` 的包会被警告并跳过（`:57`） |
| profile 层 | `:238`；文件名常量 `cordis.patch.yml`（`pkg/dsh-app-boot/lib/index.js:314`） | 本机就是 `$DSH_HOME/profiles/dsh-tui/cordis.patch.yml` |
| home 层 | `homePatchPath()` = `join(resolveDshHome(), 'cordis.patch.yml')`（`:116-118`） | 本机**不存在**该文件，这一层当前是空的 |
| `--patch` | `:239` `patchFiles.flatMap(...)`；定义见 `dsh/lib/bin.js:85` | 可重复，按 argv 顺序 |
| telemetry | `:249-250` | 非空 `DSH_TELEMETRY_DISABLED` 才生成，且只在组合里有该行时 |

根 `cordis.yml` 本身**永远是空数组**，而且每次启动都会被重写（`dsh/lib/profile-boot-Dk-7KqJc.js:209`，理由见 `:192-199`：vendored Loader 的写回可能把已组合的行烘进这个文件，下次启动就会重复插入）。手工往它里面加行 = 下次启动被抹掉，**要改的是补丁层**。

### 2.1 补丁语义（两条，必须记准）

补丁算法只有一份实现，挂载与 `--dump-config` 共用（`pkg/cordis-plugin-include/lib/index.js:57-106`）：

```js
// pkg/cordis-plugin-include/lib/index.js:100-103 —— 按 key 整值赋值
for (const [key, value] of Object.entries(overrides)) {
  if (key === 'id') continue
  target[key] = value
}
```

1. **按 `id` 命中的补丁整值替换该 key**。因为 `config` 只是一个普通 key，写 `- id: X` + `config: {...}` 的结果是 `target.config = {...}`——**没有深合并**，旧键全部消失。本机实测：基行 `{a:1,b:{c:2,d:3}}` 被 `{id:'r',config:{b:{c:9}}}` 打过后变成 `{"b":{"c":9}}`，`a`/`d` 都没了。`dsh-base` 的组合文件开头就把这条写成了设计约束（`pkg/dsh-base/cordis.patch.yml:6-8`，"a row whose value differs by mode does NOT live here"）。
2. **`insert` 不带 `id` 时追加到列表末尾**；带 `id` 时必须命中一个 `group: true` 的行，否则只告警并跳过（`pkg/cordis-plugin-include/lib/index.js:70-85`）。非 `insert` 的补丁没有 `id` 会被拒绝：`patch: id is required for non-insert patches`（`:87-90`）。写 `name` 可以加一道护栏：与目标行 `name` 不符则整条跳过（`:96-99`）。

> [!warning] 最常见的误用
> 覆盖一行的 `config` 时只写出要改的那个键，等于把其余字段静默清空——症状可能延后到运行期才出现。改 `config` 一律把该行需要的键写全。

`patchReload: live` 时还有第二条生效路径：HMR 重新读补丁文件并按**同一顺序**重新组合整个 include 的 patches（`dsh/lib/profile-boot-Dk-7KqJc.js:305-310`、`:321-341`；watcher 见 `pkg/dsh-app-boot/lib/index.js:1109-1129`）。本机 profile 就是 `live`（`$DSH_HOME/profiles/dsh-tui/package.json`），所以改补丁层无需重启。

---

## 三、`name` 的解析基址：**声明它的那个文件所在目录**

### 3.1 规则

根 include 的 `baseUrl` 由 boot 设成**根配置文件所在目录**（`pkg/dsh-app-boot/lib/index.js:1529`），而 `Include` 一构造就把自己这个 ctx 的 `baseUrl` 改写成**自己文件所在目录**（`pkg/cordis-plugin-include/lib/index.js:133,138`）。子 entry 的 ctx 以父 tree 的 ctx 为原型（`pkg/cordis-plugin-loader/lib/index.js:348,385`），于是「哪一层声明，就按哪一层的目录解析」自然成立。真正的分支在这里：

```js
// pkg/cordis-plugin-loader/lib/index.js:270-282（EntryTree.import）
if (name.startsWith('cordis:')) return this.ctx.loader.builtins[name.slice(7)]
return composeError(async (info) => {
  if (this.ctx.loader.internal) return await this.ctx.loader.internal.import(name, this.ctx.baseUrl, {})
  else if (name.startsWith('.')) return await import(new URL(name, this.ctx.baseUrl).href)
  else return await import(name)
}, getOuterStack)
```

| 写法 | 结果 |
|---|---|
| `@scope/pkg`、`pkg` | 交给 Node 内部 ESM loader，锚点为 `this.ctx.baseUrl` → 从声明文件目录逐级向上找 `node_modules` |
| `./x.mjs`、`../x.mjs` | `new URL(name, baseUrl)`，相对**声明文件** |
| `cordis:include` 等 | 直接取 `loader.builtins` |

补丁文件还多一层预处理：`insert[].name` 若是绝对路径或 `./`/`../` 开头，**在补丁加载时**就被改写成锚定在补丁文件目录的 `file://` URL（`pkg/dsh-app-boot/lib/index.js:1169-1178`，调用点 `:1203`）。而根 `cordis.yml`、preset 的 `agent.cordis.yml` 走 `Include.read()`，只有 YAML 解析、**没有这层改写**（`pkg/cordis-plugin-include/lib/index.js:179-196`）。

> [!warning] Windows 绝对路径要写成 `file://` URL
> 在 preset 或根配置里写 `name: C:\x\y.mjs`，`name.startsWith('.')` 为假，于是被当成**裸包名**丢给 Node，直接 `ERR_MODULE_NOT_FOUND`。补丁层不受影响（上面的预改写会处理）。**本条我只读了代码（`pkg/cordis-plugin-loader/lib/index.js:275-282`）没有实跑，标记为 未验证。**

### 3.2 陷阱：`link:` 装进来的插件 import 不到 `@deepseek-ai/*`

这是整套系统里最反直觉的一条，**已在本机实测**。

Node 默认把符号链接解析成 **realpath**（`--preserve-symlinks` 是显式 opt-in，见 `node.exe --help`）。`dsh plugin ... add` 对本地目录写的是 pnpm 的 `link:`，profile 的 `node_modules` 里就是一个符号链接：

| 观测 | 值 |
|---|---|
| `$DSH_HOME/profiles/dsh-tui/node_modules/dsh-plugin-content-policy` | `LinkType = SymbolicLink`，`Target = ..\..\..\..\dsh-plugin-content-policy` |
| 该插件**真实目录**是否有 `node_modules` | 否（`dsh-plugin-redact` 同样为否） |
| `C:\%USERPROFILE%\node_modules\@deepseek-ai` | 不存在（沿真实路径向上找不到任何 `@deepseek-ai`） |
| `$DSH_HOME/profiles/node_modules/@deepseek-ai` | **249 个条目**，是安装闭包的镜像（由 `healProfilesModuleFallback` 维护，`pkg/dsh-app-boot/lib/index.js:657-667`） |

链路因此分成两段：**声明行时**，baseUrl 向上会经过 `$DSH_HOME/profiles/node_modules`，`@deepseek-ai/*` 可解析；**插件模块内部**，模块被 realpath 定位后，它自己的裸 import 只能从真实目录向上找，而 `C:\%USERPROFILE%\node_modules` 里没有 `@deepseek-ai`，解析失败。

判别实验（只读，实测）：

```js
// 1) 从 profile 目录出发，裸 @deepseek-ai/schemastery 能解析
//    -> file:///C:/%USERPROFILE%/nodejs-x64/.../dsh/node_modules/@deepseek-ai/schemastery/lib/index.mjs
// 2) 但通过 profile 的符号链接 import 该插件，它的 Config 仍走 FALLBACK 分支：
const m = await import('file:///C:/%USERPROFILE%/.dsh/profiles/dsh-tui/node_modules/dsh-plugin-content-policy/index.js')
m.Config['~standard'].vendor   // => "dsh-plugin-content-policy" 即兜底实现，真实 Schemastery 没解析到
```

第 2 条是决定性的：如果 Node 用**字面路径**（profile 目录）作锚点，`$DSH_HOME/profiles/node_modules` 里有 `@deepseek-ai/schemastery`，本应解析成功；它没有，说明锚点已经变成 realpath。同理 `evidence/cfgtest.mjs:1-3` 把这条写成了脚本前提，`evidence/b/dsh-plugin-content-policy/test/config-schemastery.mjs:10-12` 必须自己造一个带 junction `node_modules` 的探针包，才能把真实 Schemastery 分支跑起来。

> [!danger] 对插件作者的含义
> **一个用 `link:` 接入的插件，不能 `import '@deepseek-ai/*'`。** 想依赖 cordis / schemastery 这类包，只有三条路：把依赖真实放进插件自己的 `node_modules`；用发布包（pnpm 从 registry 安装会落进 profile 的 `node_modules`，但注意 realpath 规则依旧生效）；或者干脆不 import，自己实现兜底。第二条的可靠性我**未验证**——`link:` 之外的安装形态我没有实测过。

---

## 四、`inject` 语义：行级是**追加**，不是替换

模块级 `inject` 在 fiber 构造时归一化进一个**全新的 map**（`pkg/cordis/lib/index.js:1634`）；行级 `inject` 随后被解析进**同一个 map**（`pkg/cordis-plugin-loader/lib/index.js:706-710`）：

```js
// pkg/cordis-plugin-loader/lib/index.js:709
Inject.resolve(fiber.entry.options.inject, fiber.inject)
```

而 `Inject.resolve(inject, result)` 只往 `result` 里写，从不清空（`pkg/cordis/lib/index.js:1490-1498`）。所以**行级 `inject` 只能加，不能减**——想「覆盖」模块自带的依赖是做不到的。

已收集的实测（`evidence/sweep5.txt:13`）：把行级 `inject` 收窄成只剩 `tuiDialogs`，模块静态 `inject` 里的 `commands` 仍然生效，结果该行永远等不到 `commands` —— `rowInjectAdditive  BOOT_ABORTED  dsh-plugin-redact: pending (waiting for service: commands)`。

副作用：`inject` 出现在 diff 里会**强制重载该行**（`pkg/cordis-plugin-loader/lib/index.js:446`）；行级 `inject` 若指向一个永不出现的服务，这行的 fiber 就停在 state 0，`apply` 一次都不跑（`evidence/sweep5.txt:11`、`:21`）。

---

## 五、失败语义：**一行没起来 = 整个 profile 启动失败**

### 5.1 启动后的两次审计

`boot()` 的顺序是：装 Loader → `prepare` → 挂根 include → **等 loader 结算** → **审计**（`pkg/dsh-app-boot/lib/index.js:1525-1538`）。审计有两关，**任何一关抛错都会 dispose 整个上下文并以 `plugin tree failed to load` 退出，没有按行隔离**（`:1539-1546`）。第一关的判据就是一行代码（`:1435`）：

```js
const failed = [...ctx.loader.entries()].filter((entry) => entry.fiber === void 0 && !entry.disabled)
```

| 关卡 | 触发条件 | 报错形态 |
|---|---|---|
| `assertEntriesLoaded` | 没有 fiber，且此刻**不算 disabled** | `plugin(s) failed to load: <name 列表>`（`:1434-1440`） |
| `assertEntriesActivated` | state `3` FAILED | `await fiber.await()` 后带原始堆栈：`<name>: <stack>`（`:1474-1481`） |
| 同上 | state `0` PENDING | `<name>: pending (waiting for services: a, b)`（`:1483-1486`） |
| 同上 | 其它状态（1/4/5） | `<name>: fiber state N`（`:1487`） |

`evidence/sweep5.txt` 记录的矩阵里，裸包名不存在（`:20`，第一关）、import/apply 抛错（`:17-18`，第二关）、注入一个从不出现的服务（`:21`）全部 `BOOT_ABORTED`；而顶层 `await` 永不了结时是 `BOOT_NEVER_SETTLED __HANG__`——连审计都到不了（`:19`）。另外 `installFailLoud` 把**迟到的 unhandled rejection** 也变成一条 `fatal load failure` 并 `exit(1)`（`pkg/dsh-app-boot/lib/index.js:1401-1425`），所以「启动成功之后再炸」并不存在。

### 5.2 `disabled` 陷阱：一个会在挂载中途翻转的 getter

`Entry.disabled` **不是字段，是 getter**，每次读都重新求值；`!!js` 表达式就在那时执行（`pkg/cordis-plugin-loader/lib/index.js:359-379`）：

```js
get disabled() { return this._disabled(this.options) }
_disabled(options) { if (options.group) return false; if (this.disabledOf(options)) return true; /* 再沿父链找 */ }
disabledOf(options) { return isJsExpr(options.disabled) ? Boolean(this.evaluate(options.disabled.__jsExpr)) : Boolean(options.disabled) }
```

而**挂载期**的那次判断只发生一次，且在**同批 entry 还没全部登记进 `tree.store`** 的时候——`:426` 的检查是同步求值（为真就永远不 `init()`），而 `:97` 虽然用 `Promise.allSettled` 并发创建，`create()` 的同步段仍是**逐个**登记 entry：

```js
if (!this._disabled(candidate)) await this.init()                                    // :426
const outcomes = await Promise.allSettled(config.map((options) => this.create(options)))  // :97
```

于是：**若 `disabled` 谓词依赖「树里有没有某一行」，而被依赖的行排在它后面，两次求值就会得到相反结果**——挂载时判「跳过」（不建 fiber），审计时判「未禁用」→ 命中第一关 → **整个 profile 启动中止**。

> [!bug] 本机最小复现（只读，实测三次结果稳定）
> 基配置用 `evidence/root.yml`（内容 `[]`），补丁插入两行：被守卫行在前，谓词指向列表更靠后的那一行。
> ```js
> const predicate = (n) => "![...ctx.loader.entries()].some(e => e.options.name === '" + n + "')"
> // A 陷阱：谓词引用「排在后面」的行
> await boot('probe', ROOT, [{ insert: [
>   { id: 'x-guarded', name: './fix-dialogs.mjs', disabled: { __jsExpr: predicate('./fix-late-dialogs.mjs') } },
>   { id: 'x-late',    name: './fix-late-dialogs.mjs' },
> ] }])
> ```
> | 场景 | 结果 |
> |---|---|
> | A 谓词指向**靠后**的行 | `BOOT_ABORTED :: probe: plugin(s) failed to load: ./fix-dialogs.mjs` |
> | B 同一谓词形状，指向**自己**（求值前已登记） | `BOOT_OK  include[state=2,disabled=false] x-guarded[state=2,disabled=false]` |
> | C 谓词恒为 `false` | `BOOT_OK` |
>
> B/C 两个对照说明：**不是 `!!js` 本身有问题，也不是谓词形状有问题，而是「树状态」在两次读取之间变了。** 报错落在第一关（`plugin(s) failed to load`）而不是第二关，正好证明审计那一刻该行既没有 fiber、又已不算 disabled。

> [!tip] 写 `disabled` 的安全姿势
> - 谓词只用**进程级常量**：`process.platform`、环境变量。出厂组合与 preset 全是这么写的（`pkg/dsh-base/cordis.patch.yml:216,222,248,252`；`pkg/dsh-agent-presets/presets/cordis/agent.cordis.yml:48,52`）。
> - 需要「提供方在就启用」，用**行级 `inject` + 让这行 PENDING** 表达，而不是 `disabled` 谓词。PENDING 是稳定状态，会在依赖出现时自动激活（第一节）。
> - 真的需要条件禁用时，把条件**烘成补丁**在启动前算好，别在挂载中途读树。

---

## 六、Config 校验

`resolveConfig` 是唯一的校验点（`pkg/cordis/lib/index.js:955-961`）：

| 情况 | 平台行为 |
|---|---|
| **没有导出 `Config`** | `:956` 直接 `return config`——**完全不校验，且没有任何提示** |
| `validate()` 返回 thenable | `:958` 抛 `TypeError: Async config validation is not supported` → 第一关失败。**校验必须是同步的**（`Config['~standard'].validate` 必须同步返回 `{value}` 或 `{issues}`，不能是 Promise） |
| 返回 `issues` | `:959` 抛 `ValidationError`，文案形如 `invalid config:\n  - <message> (at <path>)`（`:940-945`） |
| 正常 | `:960` 采用 `result.value`——**默认值填充、类型强制都在这一步** |

> [!note] 关于「未知键」和报错文案
> - **Schemastery 保留未知键**：`evidence/branch-diff5.txt:13-14` 里 `{bogus:1}` 在真实 Schemastery 分支（`evidence/cfgtest.mjs:13` 定义该分支判据）的输出键集**含 `bogus`**，兜底分支则把它丢掉。启动不会因此失败（`evidence/cfgmatrix.txt:4` `{bogus:1} unknown key → OK`）。**拼错的键不会报错，只会静默无效**——排查时先怀疑键名。缺 `config` 键或写 `config: null` 同样不会被平台拦下，`evidence/cfgmatrix.txt:1-3` 三种写法均 OK，后事由插件自己决定。
> - 收集到的矩阵里 `dsh-redact: invalid config: $.argsCells must be a non-negative integer`（`evidence/cfgmatrix.txt:8`）**不是**上面这条平台文案。它来自插件自己的兜底校验分支（§3.2 的双轨），**该归因是我的阅读判断，未逐行核对插件源码，标记为 未验证。**

---

## 七、什么该放哪里：host composition vs agent preset

| | host composition（`dsh-base/cordis.patch.yml` + profile 层） | agent preset（`agent.cordis.yml`） |
|---|---|---|
| 实例数 | **每进程一份** | **每会话一份**，挂在 agent 的作用域之下 |
| 装什么 | 注册表本身（`tools`/`systemPrompt`/`agents`/`agent-loop`/`sessions`，`pkg/dsh-base/cordis.patch.yml:460-487`）、跨会话的东西（持久化、存储、settings、凭据）、沙箱与审批栈、模型路由、subagent 注册表与其 backend | 这一个会话往注册表里贡献的东西：它的工具行、persona、prompt 段、压缩策略 |
| 卸载 | 进程退出 | 随 agent 的 fiber 一起 unwind（`pkg/dsh-agent-presets/lib/index.js:898-899`、`:911`） |

**「一行发布了服务，就不能裸放在 preset 里」**——这是硬约束，不是风格建议。`mountPreset` 会先拒绝「无作用域 ctx」（`pkg/dsh-agent-presets/lib/index.js:906`，否则注册会作用于进程里每个 agent），挂载后再审一次服务泄漏：

```js
// pkg/dsh-agent-presets/lib/index.js:920-921
const leaked = leakedServices(agentCtx, fiber)
if (leaked.length > 0) throw new Error(`row(s) published process-global service(s) [${leaked.join(', ')}];
  a preset service must sit behind an \`isolate\` realm or move to the host composition`)
```

理由有两条，都指向同一个后果：没有 `isolate` 的 `provide()` 落在**进程全局 realm**，第二个会话挂载时就会撞上 `service "X" has been registered at <Owner>`（冲突检查在 `pkg/cordis/lib/index.js:812`）；而只读的消费者若被错误地包进 realm，又会解析不到宿主提供的实例。规范原文与错误分类见 `pkg/dsh-agent-presets/presets/cordis/skills/editing-cordis-compositions/SKILL.md:78`、`:112`、`:165`。

> [!question] 哪些行「发布服务」看不出来
> 行名不体现这一点，安装后的包里也没有 README。可靠做法是**挂载校验一次，读它抛出的错误**——错误里会点名那个服务（`SKILL.md:112` 列的两种消息形态）。

---

## 八、怎么验证一个改动

三级验证，强度递增，**别把第一级当成第三级**：

| 级别 | 手段 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| 1 组合 | `dsh --profile <n> --dump-config` | 补丁栈按预期叠加、行出现/消失、来源注释标对了贡献文件 | **不 import 任何插件模块** |
| 2 加载 | 从 profile 目录 `import()` 那个 `name` | 模块能被 Node 解析、语法/依赖没问题 | 不跑 `apply`，不校验 config |
| 3 激活 | 真启动一次，或 preset 的 `standingKeyFor(id)` | `apply` 真的跑了、服务真的注册了 | —— |

**第一级为什么只能证明组合**：`--dump-config` 的实现只做「读文件 → 解析 → 应用补丁 → 打印」（`dsh/lib/dump-config-lFgMwK8i.js:24-50` → `pkg/dsh-app-boot/lib/index.js:1236-1281`），路径上**没有任何 `import()`**。本机实测：往补丁层插一行 `name: dsh-plugin-does-not-exist-xyz`，`renderConfigDump` 照样正常输出了这一行、没有报错。

```powershell
# 注意：它会重写 <profile>/cordis.yml（profile-boot-Dk-7KqJc.js:209），内容与常量一致所以看不出变化
dsh --profile dsh-tui --dump-config
dsh --profile dsh-tui --dump-config --patch .\extra.yml   # 只看某层 overlay 的效果
dsh --profile dsh-tui --dump-default-config                # 跳过用户层（补丁文件坏了时的自救），不接受 --patch
```

**第二级**要在**声明该行的目录**里 `import()`（第三节的锚点规则），或者直接 `import()` profile 下那条符号链接路径——本机实测能跑通，且顺带暴露了 §3.2 的 realpath 问题。

**第三级**必须有 boot 路径。`evidence/probe.mjs:1-3` 就是为此写的：它用**不带 `bareModuleBaseUrl`** 的方式直接调 `boot(binName, absoluteConfigPath, patches, prepare)`，与 `dsh` 真正的启动路径一致（`dsh/lib/profile-boot-Dk-7KqJc.js:311`）。preset 场景用 `ctx.agentPresets.standingKeyFor(id)`，它会在真挂载后审出「行没起来」「服务泄漏到 root realm」两类问题（`pkg/dsh-agent-presets/lib/index.js:905-938`）。

> [!warning] 两个环境坑
> - PATH 上的 `node` 是 **v18.16.1**，`import dsh-app-boot` 会直接 `SyntaxError: node:util does not provide an export named 'parseEnv'`。
> - 改动**别碰出厂 preset**（`pkg/dsh-agent-presets/presets/**`）：升级会覆盖，且弄坏 `cordis` 会让 preset 编写能力本身失效。要改就复制一份到 `$DSH_HOME/.agent-presets/<id>/` 再改。

---

## Related

- [[DSH插件与Hook开发最佳实践]] — 插件形态、事件/服务/工具、hooks 桥接与发布分发
- [[DSH-TUI插件使用手册]] — 本机 TUI profile 的日常使用
- [[DSH会话脱敏插件缺陷档案]] — 同一批实测里暴露的插件侧缺陷
- [[DSH工具结果管线与meta陷阱]] — `tools/*` 管线上相邻的一类坑
- [[CORRECTIONS]] — 写判断性结论前的回查清单
