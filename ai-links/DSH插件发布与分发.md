---
title: DSH 插件发布与分发
aliases: [DSH插件发布, DSH插件分发, DSH插件市场真相, dsh-plugin topic]
tags: [ai/agent, ai/tools, ai/links]
created: 2026-09-13
updated: 2026-09-13
status: review
---

# DSH 插件发布与分发

See also: [[AI-Links-KB-Home]] | [[DSH插件与Hook开发最佳实践]] | [[DSH会话脱敏项目方法论复盘]] | [[CORRECTIONS]] | [[AGENTS]]

> [!abstract] 一文档一问题
> 「**怎么把一个 DSH 插件发布出去，并让别人找得到。**」
> 三句结论先给：
> 1. **官方没有市场。** `dsh plugin` 是 pnpm 的薄包装，官方通道只有"按名安装"，**没有浏览、没有发现、没有索引**。
> 2. **发现只有两个信号**：GitHub topic `dsh-plugin`（官方 README 唯一推荐的机制）与 npm keyword `dsh-plugin`。**两者都不是包名前缀要求**。
> 3. **这个生态没有守门人**：`dsh plugin add` 接受任意 pnpm spec，安装任何插件 = **以完整用户权限运行任意代码**。
>
> 本文事实全部来自 2026-09-13 的一次完整发布实践：两个包发布、两次版本迭代、仓库公开、topic/keyword、三个提交、守卫体系、供应链核查。**不是文档转述**，凡引用源码者都给出 `文件:行号`。

> [!danger] 三个词分开看，别混
> | 词 | 含义 | 官方给了吗 |
> |---|---|---|
> | **发布** | 把 tarball 发到 npm（或提供 git / tarball 依赖），能被 `dsh plugin add <名>` 装上 | ✅ 给全了 |
> | **分发** | 别人按名安装、`remove` 卸载、`bundles` 自动登记 | ✅ 给全了 |
> | **发现** | 陌生人**怎么知道有你这么个插件** | ❌ **只有 topic / keyword 两个信号** |

---

## 一、官方通道的真相：不存在官方市场

这一节是本文最重要的结论，由**三条相互独立**的证据支撑。

### 1.1 证据一：CLI 层面，`dsh plugin` 就是 pnpm 的薄包装

源码 `@deepseek-ai/dsh/lib/bin.js:105-106` 原文：

```
manage a profile's plugins by forwarding the remaining arguments to pnpm in the profile directory
```

参数说明：

```
pnpm arguments, forwarded verbatim (add <pkg>, remove <pkg>, why <pkg>, ...)
```

实现落在 `plugin-*.js` 里，核心就一行 `spawnSync("pnpm", args, { stdio: "inherit" })`，注释自称 "thin pnpm forwarder"。

**含义**：`dsh plugin` 不含任何注册表、索引或审核逻辑——它的全部语义就是"在 profile 目录里替你跑 pnpm"。

### 1.2 证据二：官方仓库里没有市场

- `deepseek-ai/deepseek-harness` **没有** marketplace / registry 目录；
- `docs/` 里**没有**插件分发章节。

即：官方不仅没做市场，也没有把"分发"当成一个需要文档化的子系统。

### 1.3 证据三：npm 上不存在"官方市场包"

直接探测包名，**全部 404**：

| 被探测的包名 | 结果 |
|---|---|
| `@deepseek-ai/dsh-marketplace` | 404 |
| `@deepseek-ai/dsh-registry` | 404 |
| `@deepseek-ai/dsh-plugins` | 404 |
| `@deepseek-ai/dsh-plugin-registry` | 404 |
| `@deepseek-ai/dsh-store` | 404 |
| `@deepseek-ai/dsh-plugin-store` | 404 |

> [!note] 与既有文档的口径关系
> [[DSH插件与Hook开发最佳实践]] §八 记录过官方文档的说法「插件市场仍处设计阶段」——那次是**2026-08 的官方文档快照**；本次是**源码 + 仓库 + npm 三处直接探测**。两者不矛盾，但结论要更新为一句更硬的话：**到 2026-09-13 为止，官方市场不是"还没上线"，而是"没有这个东西"**。

### 1.4 官方唯一推荐的发现机制：仓库 topic

官方 README 的 "Community and support" 一节原文：

> Add the `dsh-plugin` topic to your plugin repository **for discoverability**

**这是官方推荐的唯一一种发现机制**，而且它落在 GitHub 上，不在 npm 上。

### 1.5 `dsh plugin add` 的真实行为（实测）

`dsh plugin --profile <p> add <pkg>` 走三段：

1. **初始化 profile**（首次使用时）；
2. **在 profile 目录里跑 `pnpm <args>`**；
3. **reconcile `dsh.profile.bundles`**。

实测装上后：

| 观察点 | 实测结果 |
|---|---|
| profile 的 `package.json` | 自动出现 `dependencies` 与 `dsh.profile.bundles` **两项** |
| `dsh --profile <p> --dump-config` | 能看到 `# == <包名>` 层标记与完整 config |

> [!warning] `--dump-config` 只证明配置组合
> 它**从不 import 模块**——这是 [[CORRECTIONS]] C-007，也是 [[DSH会话脱敏项目方法论复盘]] §2.3 的实测结论。别拿它当"插件装好了"的证据。

### 1.6 命令接受任意 pnpm spec

`add` 的实参**原样转发**给 pnpm，因此以下形式全部可用：

| 形式 | 例 |
|---|---|
| registry 包名 | `dsh-hello-plugin` |
| 当前目录 / 相对目录 | `.`、`../plugin` |
| git | `git+…` |
| GitHub 简写 | `github:…` |

**没有白名单、没有审核、没有索引**——这是"薄包装"的直接推论，也是第七节供应链风险的根。

### 1.7 检索能力实测：能按名搜，不能按词发现

| 命令 | 结果 | 原因 |
|---|---|---|
| `dsh plugin … search <精确包名>` | **能搜到** | 转发 pnpm search，精确名匹配 |
| `dsh plugin … search dsh-plugin`（关键词） | **搜不到**新包 | npm 搜索索引对新包有延迟 |
| `npm view <包名>` | **立刻可读** | 直接读元数据，不经过搜索索引 |
| 关键词搜索的第一命中 | 一个**名字就叫 `dsh-plugin`** 的第三方市场包 | npm 搜索里**精确名匹配权重最高** |

> [!important] 本节结论（全文最重要的一句）
> **官方通道只有"按名安装"，没有"浏览 / 发现"能力。**
> 一个插件要被陌生人找到，只能靠**第六节**的那两个信号：**GitHub topic `dsh-plugin`** 与 **npm keyword `dsh-plugin`**。
> 这也解释了为什么"我把包发出去了，怎么没人装"——**发出去 ≠ 被找到**，后者需要额外的动作。

---

## 二、可复现的发布流程

### 2.1 前置条件（第一条真的会咬人）

> [!danger] Node ≥ 22.15 必须排在 PATH 最前
> `prepublishOnly` 会跑 `npm test`，而它 spawn 的是 **PATH 上的 `node`**。
> PATH 上是旧版时**发布会失败**，且引擎抛的是**显式版本错误**——不是"日志损坏"这类误导信息（[[DSH会话脱敏插件缺陷档案]] D-13 记录过反向的误诊）。

### 2.2 流程

| # | 步骤 | 说明 |
|---|---|---|
| 1 | 确认 `node --version` ≥ 22.15 且 PATH 最前 | 见上 |
| 2 | `npm login --registry=https://registry.npmjs.org/` | 本机默认 registry 可能是国内镜像 |
| 3 | 在 `package.json` 设 `publishConfig.registry` | **固定到 npmjs**；不设会有发错地方的风险 |
| 4 | 在 `package.json` 设 `prepublishOnly: npm test` | **发布闸**：测试不过就发不出去 |
| 5 | `npm publish --dry-run` | **不需要凭据**（只 warn），可随时检查将发布什么 |
| 6 | **CI 绿 → publish → 从 registry 真装验收** | 顺序不能反：验收对象是**从 registry 装下来的那一份**，不是磁盘上的源码 |
| 7 | 改动 → **必须发新版本号** | 已发布的版本**不可覆盖**；`npm unpublish` 72 小时后受限。文档类改动也一样 |

### 2.3 2FA 是常见拦路虎

非交互 shell 下 `npm publish` 会报：

```
E403 ... Two-factor authentication or granular access token with bypass 2fa enabled is required to publish packages
```

两条出路（都实测可用）：

| 出路 | 做法 | 特点 |
|---|---|---|
| ① 自己的终端里跑 | npm **交互式**提示输入验证器 6 位码 | 无超时窗口问题 |
| ② granular access token | 建 token 时勾选 **bypass 2FA**，再 `npm config set //registry.npmjs.org/:_authToken <token>` | 适合无人值守 / CI |

> [!warning] 出路 ② 的安全性代价见第七节
> 一个"账号级 + 允许绕过 2FA"的令牌，等价于发布权。首选**限定到具体包的 granular token**。

---

## 三、`files` 白名单的两个坑

### 3.1 坑一：`files` 是唯一权威，但**打不到包目录之外**

实测现场：把仓库根的 `SECURITY.md` 写进 `files`，结果是**"白名单里有、包里没有"**——被仓库里的 pack-check 抓出来：

```
FAIL files 白名单全部命中实际内容 — 白名单里有但包里没有：SECURITY.md
```

**正确做法**：每个包目录内各放一份。

> [!tip] 这条为什么值得单列
> `files` 与 tarball 的关系不是"声明即可得"——npm **打不到包目录之外的文件**。任何"根目录已经有了一份"的直觉在这里都是错的。

### 3.2 坑二：`files` 给消费者的是**可复现证据**

把测试套件一起发布是**有意为之**，不是疏忽：

- 审计者可以对**自己拿到的字节**跑同一批断言，而不必相信仓库的自检；
- 这与 [[DSH会话脱敏项目方法论复盘]] §1.4 的结论同源——判据要在对方那一侧；
- 代价是：**凡是随包发布的测试，都必须能在消费者平台上跑起来**（这正是 [[CORRECTIONS]] C-012 的现场：随包发布的 `preflight.mjs` 用了 Windows 专有的 `USERPROFILE`）。

### 3.3 元数据清单

| 字段 | 要求 |
|---|---|
| `repository` | monorepo 里必须带 `directory` |
| `homepage` / `bugs` | 直接影响 npm 页面质量 |
| `description` | **用英文**（npm 是国际 registry） |

---

## 四、仓库级守卫：守卫 + 自检 + 豁免

发布这件事的可靠性不靠"记得检查"，靠三道关卡：**两个静态守卫 + 一层可证伪自检**（另有显式豁免标记）。

### 4.1 `portability.mjs`：静态扫发布代码与测试

拦平台专有假设：

| # | 规则 |
|---|---|
| 1 | Windows 专有环境变量（`USERPROFILE` / `HOMEDRIVE` / `APPDATA` / `LOCALAPPDATA`） |
| 2 | `import.meta.url` 配 `.pathname` |
| 3 | 硬编码盘符 |
| 4 | `path.win32` |

> [!bug] 规则 1 的判据是「**那个变量自己**有没有回退」
> 不是「这一行有没有 `??`」。
> `DSH_HOME ?? path.join(process.env.USERPROFILE, '.dsh')` 这一行**有 `??`，但仍然是错的**——回退属于 `DSH_HOME`，不属于 `USERPROFILE`。
> 第一版守卫把"整行出现过 `??`"当安全信号，于是**恰好放过了它要抓的那个 bug**（[[CORRECTIONS]] C-012 里「守卫自己的两个假判据」一段）。

### 4.2 `pack-check.mjs`：校验真正会发布的那个 tarball

三组断言：

| 组 | 校验什么 |
|---|---|
| **tarball 完整性** | `files` 白名单全部命中实际内容；包内**相对 import 的目标都在包里**；**无测试残留** |
| **manifest 闸门** | `dsh.bundle.patch` 已声明、文件存在、是**顶层 YAML 数组**、含一个 `name` 等于包名的 loader entry |
| **monorepo discovery** | 根 `dsh.bundles` 登记齐全（见第五节） |

### 4.3 核心方法论：守卫必须可证伪

每个守卫都配一个自检，**把真实缺陷注入回去**：断言守卫（a）以**退出码 1** 失败、（b）**指名正确的文件与行号**，然后 `finally` 恢复。

> [!important] 理由与当场回报
> **不会失败的检查比没有检查更糟**——它把"没查"伪装成"查过了"。
> 这个做法当场就有回报：
> 1. portability 守卫的第一版把「这一行有 `??`」当安全信号，**自检立刻暴露它放过了真正的 bug**；
> 2. 另一条规则又因为它**自己那句解释性注释**（注释里写了 `.pathname`）而误报。

> [!warning] 自检也不要写死行号
> 最初把期望行号写死成 `13`，后来在文件顶部**加一行 import 就红了**。改成从注入后的内容里**动态推算**——判据不能依赖"文件此刻长什么样"。

### 4.4 显式豁免标记 `portability-allow`

测试里会**故意写出平台专有字样**（例如把 `'C:\Windows'` 当越界输入），这类正当用法用 `portability-allow` 标注。

**刻意做成可 grep**，而不是让规则悄悄失明——这是 [[CORRECTIONS]] C-014 的结论（豁免必须显式、可见、可审计）在发布侧的同一条落地。

> [!note] 与本库另一处门禁的关系
> [[ci-and-prepush-gates]] 记的是**知识库仓库**的两道本地闸 + 三道 CI 闸；本节记的是**插件仓库**的守卫。两边共享同一条设计原则：**检出模式 + 显式豁免 + 可证伪自检**，缺一不可。

---

## 五、monorepo 是被收录的关键坎

> [!danger] 目录扫描器**不遍历目录树**
> 它只读两个位置：
> 1. `HEAD:package.json` 的 **`dsh.bundles`**（**复数、数组、目录列表**）；
> 2. 再逐个读 `HEAD:<dir>/package.json` 的 **`dsh.bundle`**（**单数、对象、含 `patch`**）。
>
> **仓库根没有 `package.json` ⇒ 数组为空 ⇒ monorepo 里的包对扫描器等于不存在**，topic 加得再对也没用。

### 5.1 两个键的区别（最容易写反的地方）

| 位置 | 键 | 形态 | 例 |
|---|---|---|---|
| 仓库根 | `dsh.bundles` | 复数、**数组**、目录列表、**带尾斜杠** | `"dsh": { "bundles": ["./packages/x/"] }` |
| 包目录内 | `dsh.bundle` | 单数、**对象** | `"dsh": { "bundle": { "patch": "./cordis.patch.yml" } }` |

**根节点不要声明 `dsh.bundle`**——这样校验会拒绝它，扫描器才会正确落到子目录。

### 5.2 `awesome-dsh-plugin` 的 monorepo 约定

| 项 | 约定 |
|---|---|
| `url` | 指向**子目录**：`…/tree/main/packages/x` |
| `name` | `owner/repo#subname` |
| 文件名 | `owner__repo--packages-x.yml` |

### 5.3 这些都被 pack-check 守住

根 `dsh.bundles` 的登记齐全性是 **pack-check 的断言之一**：将来加第三个包忘了登记，**CI 会红**，不会静默漏掉。

---

## 六、收录信号与目录图谱

### 6.1 两个信号（都不是命名要求）

| 信号 | 谁在扫它 |
|---|---|
| **GitHub topic `dsh-plugin`** | 至少 6 个目录扫它 |
| **npm keyword `dsh-plugin`** | harnessai.io 扫它 |

> [!important] 包名不必以 `dsh-plugin-` 开头
> 两个信号都是**标注**，不是**命名**。反过来说：名字里带 `dsh-plugin` 而不加 topic / keyword，一样不会被扫到。

### 6.2 自动收录（无需提交）

| 目录 | 抓取频率 |
|---|---|
| plugin.dshdesk.com | 每 2 小时 |
| dshfind | 每日 02:17 UTC |
| YELEBAI | 每 2 小时 |
| harnessai.io | —（扫 npm keyword） |
| `bruc3van/awesome-dsh-plugin` | 每日抓取 |
| 各 star 榜单 | — |

> [!note] plugin.dshdesk.com 的 CONTRIBUTING 明确写着
> **不要手动把已发现的插件加进快照**——走自动发现。所以对这类目录，正确动作是**把 topic / keyword 加对**，而不是去提 PR。

### 6.3 手动提交通道（实测可用）

| 通道 | 形态 | 备注 |
|---|---|---|
| dsh.so 的 GitHub submission tracker | issue | **网页表单长期不可用**（见下） |
| `AI-Scarlett/DSH-Store` | 用其 `plugin-submission.yml` 模板开 issue | **明确支持 monorepo**：机器人遍历仓库树列出候选目录（列的是**所有带 `dsh.bundle` 的 `package.json`**，见下） |
| `awesome-dsh-plugin`（★15k） | PR 到 `data/plugins/` | 手动补条目 |

> [!danger] 用 API / CLI 提交"表单型"仓库：两个真正卡住过的点
> 1. **自动化读的是 issue 表单的字段结构，不是人读的正文。** 该仓库的解析器用正则 `/^### (.+)$/` 切分 `### <字段名>` 段落，再按 `GitHub repository` / `Plugin path (optional)` 这样的标签取值；用 API 提交一坨自由 markdown，直接报 **`SUBMISSION_FIELD_MISSING`**。
>    ⇒ **用 API/CLI 代替表单时，必须复刻表单会生成的那套 `### 字段名` 布局**（字段名逐字照抄）。
> 2. **"候选插件歧义"：它遍历仓库树，把所有带 `dsh.bundle` 的 `package.json` 都当候选。** 仓库里除两个真实包外，`docs/reports/boot-verify/{a,b,frozen}/` 下的 5 份历史快照与 `docs/design-notes/bakeoff-policy-engine/` 的设计原型——**因为是从早期版本逐字节冻结的副本，仍然带着 `dsh.bundle.patch`**——于是被识别成 **7 个候选插件**（真实只有 2 个），报 **`SUBMISSION_PACKAGE_AMBIGUOUS`**。
>    ⇒ **把历史快照以"完整可安装形态"留在仓库里，会让任何遍历目录树的工具把它误认为真实插件**——这从"卫生问题"升级成了"功能问题"。快照本身在 `docs/reports/boot-verify/README.md` 里已被标注为不可用，但**扫描器不读 README**。
>    **处置**：提交时显式填 `Plugin path`；根治是把快照里的 `package.json` 改名（如 `package.json.frozen`）或去掉 `dsh.bundle` 字段。
>
> 两条已录入 [[CORRECTIONS]] C-021（表单字段结构）/ C-022（快照被当成真货）。

> [!warning] 一个真、但**不是原因**的陷阱：`--label` 会静默失败
> `gh issue create --label plugin-submission` **退出码 0，但标签为空**；事后 `gh issue edit --add-label` 才报出真正原因：
> ```
> GraphQL: ... does not have the correct permissions to execute AddLabelsToLabelable
> ```
> ——**非维护者无权打标签**，创建时那个 `--label` 因此被静默丢弃。
>
> **但它不是这次提交没被处理的原因。** 该仓库 workflow 的触发条件是 **OR**：
> ```yaml
> if: contains(github.event.issue.labels.*.name, 'plugin-submission')
>     || startsWith(github.event.issue.title, '[Plugin]')
> ```
> 我们的标题以 `[Plugin]` 开头 ⇒ **第二个分支成立，workflow 在创建后 8 秒就跑了**。**标签从来不是必需的。**
>
> **通用教训保留、因果推断撤回**：创建类操作的**退出码 0 不等于副作用已生效**，事后要用独立的读操作回查关键字段；但**回查发现的异常也不等于失败原因**——我最初"缺标签所以没被处理"的判断是错的，并已在 issue 上评论更正。见 [[CORRECTIONS]] C-020。

> [!success] 最终结果：两条提交的预检都 `passed`
> | 条目 | 扫描范围 | 结果 |
> |---|---|---|
> | `#811`（会话脱敏插件） | 14/14 文件 | Critical 0 / Warning 0 / **Info 2** |
> | `#823`（内容策略插件） | 8/8 文件 | Critical 0 / Warning 0 / **Info 0** |
>
> 对方**独立扫描器**报出的两处 Info，恰好是 `test/engine.selftest.mjs:11` 与 `test/path-guard.mjs:12` 的**子进程能力**——与我们自己的审计结论一致。这是一次"**独立分析互相印证**"的样本：判据落在对方那一侧，结论对得上。

### 6.4 不可用 / 不值得

| 对象 | 为什么 |
|---|---|
| `vlln/plugin-registry` | registry 机制 **2026-08 已废弃**，现在只是一个薄控制台 |
| `zaimokuza-yoshiteru/dsh-plugin-hub` | **不是市场**，是资源面板，**无上架入口** |
| `sandbaseai/dsh-plugin-store` | 模板是"**更正已有条目**"而不是新提交；且推送停在 2026-08-20 |
| `dsh-tui-ecosystem` | 偏冷，且要求 `@dsh-tui-ecosystem` scope |
| dsh.so **网页提交表单** | 长期返回 `The submission service is not configured yet`；其 tracker 里已有 issue 标题直接写着 `(web submission endpoint unavailable)` ⇒ **走 GitHub issue** |

---

## 七、供应链安全：这个生态没有守门人

### 7.1 安装即执行

因为 `dsh plugin add` 是 **pnpm 原样转发**：

- **安装任何插件 = 以完整用户权限运行任意代码**；
- `plugin-*.js` 自己就警告：**git 托管的插件会在安装时执行构建脚本**（见 [[DSH插件与Hook开发最佳实践]] §6.2 的 `allowBuilds`）。

### 7.2 那些"市场"自述不做审查

各目录的自述一致：**不做代码审查、不做运行验证**（dshdesk 原文如此）。目录收录 ≠ 安全审核——这一条在官方文档里也写着（[[DSH插件与Hook开发最佳实践]] §八）。

### 7.3 真正的风险是**发布令牌**，不是代码

| 项 | 事实 |
|---|---|
| 风险形态 | **账号级 + 允许绕过 2FA** 的令牌**明文**存在 `~/.npmrc`；泄露即可**向所有使用者投毒** |
| 建议 | 用**限定到具体包的 granular token** |
| 另一处口子 | `.npmrc` 里的 `strict-ssl=false` 会**关闭 npm 下载的 TLS 证书校验**，给中间人投毒留口子。**实测改成 `true` 后 npm 仍正常**（`npm view` 退出码 0） |

### 7.4 供应链延迟保护：`minimumReleaseAge`

| 项 | 事实 |
|---|---|
| 机制（pnpm） | 拒绝安装**发布不足 N 分钟**的新版本——防"恶意版本几小时后被撤"这类窗口 |
| 实测 | 该机器上 **未启用**（值为 `undefined`） |
| 推论 | 配套的 `minimumReleaseAgeExclude` 列表因此是**空转的** |

> [!question] 与既有结论的关系
> 此前有一条判断是「官方 profile 模板带 `minimumReleaseAge` 供应链保护」——**查证为 `undefined`，未启用**，该结论已撤回并录入 [[CORRECTIONS]] C-018。

### 7.5 已发布包做安全披露的价值

在 `SECURITY.md` 里写清"**这个包不能对使用者做什么**"；并且**审计对象应当是已发布的 tarball，而不是源码树**——别人这样才能复现你说的话。

---

## 八、给下一个要发布的人的检查清单

> [!tip] 发布前
> - [ ] `node --version` ≥ 22.15 且在 PATH 最前（`prepublishOnly` 会 spawn 它）。
> - [ ] `publishConfig.registry` 固定到 npmjs；`prepublishOnly: npm test` 作为发布闸。
> - [ ] `npm publish --dry-run` 看一遍将发布什么（不需要凭据）。
> - [ ] **每个包目录内**各放一份 `SECURITY.md` / `LICENSE`（`files` 打不到包目录之外）。
> - [ ] 元数据齐全：`repository`（monorepo 带 `directory`）、`homepage`、`bugs`、英文 `description`。
> - [ ] 随包发布的测试能在**目标平台**上跑（C-012）；平台专有字样加 `portability-allow` 而不是放宽规则。

> [!tip] 发布时
> - [ ] 2FA：交互式输入，或 granular token 勾 bypass 2FA（优先前者；后者限定到具体包）。
> - [ ] **CI 绿 → publish → 从 registry 真装验收**，顺序不反。
> - [ ] 发完记住：**已发布版本不可覆盖**，任何改动都要新版本号。

> [!tip] 发布后（发现这一步最容易漏）
> - [ ] GitHub 仓库加 topic **`dsh-plugin`**；`package.json` 加 keyword **`dsh-plugin`**（两者都要，扫的不是同一批目录）。
> - [ ] monorepo：根 `dsh.bundles` 登记齐全（否则扫描器看不见你，topic 白加）。
> - [ ] 走手动通道提交后，**用一次独立读操作回查**关键字段（如 issue 的 labels）——退出码 0 不算证据；但**回查到的异常不等于失败原因**，真正的验收是**对方预检的结论**（C-020）。
> - [ ] 用 API/CLI 提交"表单型"仓库时，按表单字段**逐字复刻** `### 字段名` 布局（C-021）；仓库里不留"完整可安装形态"的冻结快照，否则会被算成候选插件（C-022）。
> - [ ] 别去 dshdesk 手动加快照；把信号加对即可。

---

## 关联

- [[DSH插件与Hook开发最佳实践]] — 上游：插件模型、bundle/patch、`dsh plugin` 命令面与 git 安装的 `allowBuilds`；本文补的是它 §六 之后的**闭环最后一环**
- [[DSH会话脱敏项目方法论复盘]] — 本文 §四 的守卫体系来自该项目的延续：判据放对方那一侧、守卫必须可证伪
- [[DSH会话脱敏插件缺陷档案]] — D-13 / D-16~D-22（Node 版本、作者路径、可移植性三连）都是**发布物缺陷**，与本文 §二/§三/§四 直接对应
- [[CORRECTIONS]] — C-012（本机绿测 ≠ 跨平台验收）、C-014（豁免必须显式）、C-015~C-022（本轮发布实践新增，含 C-020 的因果推断撤回与 C-021/C-022 两条真实根因）
- [[ci-and-prepush-gates]] — 知识库仓库的同构门禁（两道本地闸 + 三道 CI 闸），与本文 §四 的守卫共享同一套设计原则
- [[AI-Links-KB-Home]] · [[HOME]] · [[AGENTS]] — 子库 MOC / 全局索引 / 协作规范
