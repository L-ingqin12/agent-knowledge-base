# LSP 生态全景图

> 数据来源：GitHub topic `language-server-protocol` (680+ repos)、LSP 官方实现者页面、GitHub 搜索结果
> 星数统计截至 2026 年 6 月

---

## 一、Top 30 LSP 相关项目（按 GitHub Stars）

| # | 项目 | Stars | 类型 | 说明 |
|---|------|-------|------|------|
| 1 | [coc.nvim](https://github.com/neoclide/coc.nvim) | 25,159 | 编辑器客户端 | Vim/Neovim 的 Node.js 扩展宿主，类 VSCode 生态 |
| 2 | [eclipse-theia/theia](https://github.com/eclipse-theia/theia) | 21,600 | IDE 框架 | 云端 & 桌面 IDE 框架，原生 LSP 支持 |
| 3 | [astral-sh/ty](https://github.com/astral-sh/ty) | 18,908 | 语言服务器 | Rust 写的极速 Python 类型检查器 + LSP |
| 4 | [dense-analysis/ale](https://github.com/dense-analysis/ale) | 14,000 | 编辑器客户端 | Vim/Neovim 异步 lint + LSP |
| 5 | [neovim/nvim-lspconfig](https://github.com/neovim/nvim-lspconfig) | 13,700 | 编辑器配置 | Neovim 内置 LSP 的快速配置集 |
| 6 | [microsoft/language-server-protocol](https://github.com/microsoft/language-server-protocol) | 12,877 | 协议规范 | LSP 官方规范仓库 |
| 7 | [spyder-ide/spyder](https://github.com/spyder-ide/spyder) | 9,200 | IDE | 科学 Python IDE，集成 LSP |
| 8 | [facebook/pyrefly](https://github.com/facebook/pyrefly) | 6,622 | 语言服务器 | Meta 的 Rust 实现 Python 类型检查器 |
| 9 | [supabase-community/postgres-language-server](https://github.com/supabase-community/postgres-language-server) | 5,240 | 语言服务器 | Postgres SQL 语言服务器 |
| 10 | [emacs-lsp/lsp-mode](https://github.com/emacs-lsp/lsp-mode) | 5,096 | 编辑器客户端 | Emacs LSP 客户端 |
| 11 | [zigtools/zls](https://github.com/zigtools/zls) | 4,918 | 语言服务器 | Zig 语言服务器 |
| 12 | [LuaLS/lua-language-server](https://github.com/LuaLS/lua-language-server) | 4,282 | 语言服务器 | Lua 语言服务器（Lua 编写） |
| 13 | [MaskRay/ccls](https://github.com/MaskRay/ccls) | 4,065 | 语言服务器 | C/C++/ObjC 语言服务器 |
| 14 | [VonHeikemen/lsp-zero.nvim](https://github.com/VonHeikemen/lsp-zero.nvim) | 4,000 | 编辑器配置 | Neovim LSP 零配置起步包 |
| 15 | [swiftlang/sourcekit-lsp](https://github.com/swiftlang/sourcekit-lsp) | 3,859 | 语言服务器 | Swift LSP 官方实现 |
| 16 | [autozimu/LanguageClient-neovim](https://github.com/autozimu/LanguageClient-neovim) | 3,553 | 编辑器客户端 | Vim/Neovim LSP 客户端 |
| 17 | [rust-lang/rls](https://github.com/rust-lang/rls) | 3,500 | 语言服务器 | Rust Language Server (已被 rust-analyzer 取代) |
| 18 | [DetachHead/basedpyright](https://github.com/DetachHead/basedpyright) | 3,401 | 语言服务器 | Pyright 增强分支 |
| 19 | [prabirshrestha/vim-lsp](https://github.com/prabirshrestha/vim-lsp) | 3,392 | 编辑器客户端 | Vim/Neovim 异步 LSP 插件 |
| 20 | [Kotlin/kotlin-lsp](https://github.com/Kotlin/kotlin-lsp) | 3,377 | 语言服务器 | Kotlin 官方语言服务器 |
| 21 | [nvimtools/none-ls.nvim](https://github.com/nvimtools/none-ls.nvim) | 3,238 | 编辑器扩展 | Neovim 用 Lua 注入 LSP 诊断和 Code Actions |
| 22 | [artempyanykh/marksman](https://github.com/artempyanykh/marksman) | 3,200 | 语言服务器 | Markdown 语言服务器 |
| 23 | [SilasMarvin/lsp-ai](https://github.com/SilasMarvin/lsp-ai) | 3,184 | AI + LSP | AI 驱动的 LSP 后端（开源） |
| 24 | [mrcjkb/rustaceanvim](https://github.com/mrcjkb/rustaceanvim) | 3,000 | 编辑器扩展 | Neovim Rust 开发超级增强 |
| 25 | [haskell/haskell-language-server](https://github.com/haskell/haskell-language-server) | 2,929 | 语言服务器 | Haskell 官方 LSP |
| 26 | [mtshiba/pylyzer](https://github.com/mtshiba/pylyzer) | 2,865 | 语言服务器 | Rust 写的快速 Python 分析器 |
| 27 | [typescript-language-server/typescript-language-server](https://github.com/typescript-language-server/typescript-language-server) | 2,500 | 语言服务器 | TypeScript & JavaScript LSP 封装 |
| 28 | [eclipse-jdtls/eclipse.jdt.ls](https://github.com/eclipse-jdtls/eclipse.jdt.ls) | 2,400 | 语言服务器 | Java 语言服务器（Eclipse 官方） |
| 29 | [jacobdufault/cquery](https://github.com/jacobdufault/cquery) | 2,400 | 语言服务器 | C/C++ 语言服务器（libclang） |
| 30 | [Feel-ix-343/markdown-oxide](https://github.com/Feel-ix-343/markdown-oxide) | 2,200 | 语言服务器 | PKM Markdown 语言服务器 |

---

## 二、LSP SDK / 框架（按语言分类）

选择 LSP SDK 来实现自己的语言服务器时，参考下表：

| 语言 | 推荐 SDK | Stars | 说明 |
|------|----------|-------|------|
| **TypeScript** | [vscode-languageserver-node](https://github.com/Microsoft/vscode-languageserver-node) | — | Microsoft 官方，VSCode 同款 |
| **TypeScript** | [langium](https://github.com/langium/langium) | — | 语言工程框架，从语法直接生成 LSP |
| **TypeScript** | [Volar.js](https://github.com/volarjs/volar.js) | — | 嵌入式语言工具框架（Vue 同款） |
| **Java** | [lsp4j](https://github.com/eclipse/lsp4j) | — | Eclipse 官方，Java 生态最成熟 |
| **Python** | [pygls](https://github.com/openlawlibrary/pygls) | — | 最流行的 Python LSP 框架 |
| **Python** | [multilspy](https://github.com/microsoft/monitors4codegen) | — | Microsoft，多语言 LSP 统一客户端 |
| **Rust** | [tower-lsp](https://github.com/ebkalderon/tower-lsp) | — | 基于 Tower 的异步 LSP 框架 |
| **Rust** | [lsp-types](https://github.com/gluon-lang/lsp-types) | — | LSP 类型定义 |
| **Rust** | [lsp-server](https://github.com/rust-lang/rust-analyzer/tree/master/lib/lsp-server) | — | rust-analyzer 使用的轻量 LSP 框架 |
| **Go** | [go-lsp](https://github.com/TobiasYin/go-lsp/) | — | 纯 Go LSP 实现 |
| **C#** | [C#-LSP](https://github.com/OmniSharp/csharp-language-server-protocol) | — | C# LSP 协议库 |
| **C++** | [LspCpp](https://github.com/kuafuwang/LspCpp) | — | C++ LSP 实现 |
| **Haskell** | [haskell-lsp](https://github.com/alanz/haskell-lsp) | — | Haskell LSP 类型库 |
| **Swift** | [LanguageServerProtocol](https://github.com/chimehq/LanguageServerProtocol) | — | Swift LSP 库 |
| **Ruby** | [LanguageServer::Protocol](https://github.com/mtsmfm/language_server-protocol-ruby) | — | Ruby LSP 协议库 |

### 框架选型决策树

```
                   需要构建语言服务器?
                         │
          ┌──────────────┼──────────────┐
          │              │              │
     已有完整语法?    需要快速原型?    需要极高性能?
          │              │              │
   用 pygls(Python)  langium(TS)    tower-lsp(Rust)
   lsp4j(Java)      从语法生成      或直接用 Rust
   vscode-lsp(TS)    服务器+客户端    手写 JSON-RPC
```

---

## 三、编辑器 / IDE LSP 客户端

| 编辑器 | 客户端/插件 | Stars | 说明 |
|--------|------------|-------|------|
| **VSCode** | [内置](https://github.com/Microsoft/vscode/) | — | LSP 原生支持，参考实现 |
| **Neovim** | [内置 (v0.5+)](https://neovim.io/doc/user/lsp/) | — | Lua 实现的原生 LSP 客户端 |
| **Neovim** | [nvim-lspconfig](https://github.com/neovim/nvim-lspconfig) | 13,700 | 快速配置集 |
| **Vim/Neovim** | [coc.nvim](https://github.com/neoclide/coc.nvim) | 25,159 | 类 VSCode 扩展生态 |
| **Vim/Neovim** | [vim-lsp](https://github.com/prabirshrestha/vim-lsp) | 3,392 | 纯 Vim script LSP |
| **Vim/Neovim** | [ALE](https://github.com/dense-analysis/ale) | 14,000 | 异步 lint + LSP |
| **Emacs** | [lsp-mode](https://github.com/emacs-lsp/lsp-mode) | 5,096 | 最流行的 Emacs LSP |
| **Emacs** | [eglot](https://github.com/joaotavora/eglot) | — | 轻量级，已内置 Emacs 29+ |
| **Emacs** | [lsp-bridge](https://github.com/manateelazycat/lsp-bridge/) | — | 异步高性能 |
| **Sublime Text** | [LSP](https://github.com/sublimelsp/LSP) | — | Sublime 标准 LSP 客户端 |
| **Helix** | [内置](https://github.com/helix-editor/helix) | — | Rust 编写的 modal 编辑器 |
| **Zed** | [内置](https://github.com/zed-industries/zed) | — | Rust 编写的高性能协作编辑器 |
| **IntelliJ** | [LSP4IJ](https://github.com/redhat-developer/lsp4ij) | — | JetBrains IDE 的 LSP 支持 |
| **JupyterLab** | [jupyterlab-lsp](https://github.com/jupyter-lsp/jupyterlab-lsp) | — | Jupyter 的 LSP 集成 |
| **Qt Creator** | [内置](https://github.com/qt-creator/qt-creator) | — | C++ IDE，原生 LSP |
| **Eclipse** | [LSP4E](https://projects.eclipse.org/projects/technology.lsp4e) | — | Eclipse IDE LSP 集成 |
| **Kakoune** | [kak-lsp](https://github.com/ul/kak-lsp) | — | Kakoune 编辑器 LSP |
| **Kate** | [内置](https://invent.kde.org/kde/kate) | — | KDE 高级文本编辑器 |
| **Spyder** | [内置](https://github.com/spyder-ide/spyder) | 9,200 | 科学 Python IDE |
| **Theia** | [内置](https://github.com/eclipse-theia/theia) | 21,600 | 云端 IDE 框架 |
| **Monaco** | [monaco-languageclient](https://www.npmjs.com/package/monaco-languageclient) | — | 浏览器内 LSP 客户端 |

---

## 四、值得关注的 LSP 服务器（按语言）

### 顶级实现（生产级质量，强烈推荐参考）

| 语言 | 服务器 | 特点 |
|------|--------|------|
| **Rust** | [rust-analyzer](https://github.com/rust-analyzer/rust-analyzer) | LSP 实现的黄金标准，架构典范 |
| **Go** | [gopls](https://github.com/golang/tools/tree/master/gopls) | Go 团队官方，稳定可靠 |
| **Python** | [ty](https://github.com/astral-sh/ty) | 极速 (Rust)，ruff 同团队 |
| **Python** | [Pyright](https://github.com/microsoft/pyright) | Microsoft，TypeScript 编写 |
| **Python** | [python-lsp-server](https://github.com/python-lsp/python-lsp-server) | 社区维护，插件架构 |
| **TypeScript** | [typescript-language-server](https://github.com/typescript-language-server/typescript-language-server) | 封装 tsserver |
| **Java** | [Eclipse JDT LS](https://github.com/eclipse-jdtls/eclipse.jdt.ls) | Java 生态标准 |
| **C/C++** | [clangd](https://github.com/llvm/llvm-project/tree/main/clang-tools-extra/clangd) | LLVM 官方 |
| **C#** | [OmniSharp](https://github.com/OmniSharp/omnisharp-roslyn) | .NET 生态标准 |
| **Swift** | [sourcekit-lsp](https://github.com/swiftlang/sourcekit-lsp) | Apple 官方 |
| **Kotlin** | [kotlin-lsp](https://github.com/Kotlin/kotlin-lsp) | JetBrains 官方 |
| **Scala** | [Metals](https://github.com/scalameta/metals) | Scala 生态主流 |
| **Haskell** | [HLS](https://github.com/haskell/haskell-language-server) | Haskell 官方 |
| **Zig** | [zls](https://github.com/zigtools/zls) | Zig 官方 |
| **Lua** | [lua-language-server](https://github.com/LuaLS/lua-language-server) | Lua 社区标准 |
| **Ruby** | [ruby-lsp](https://github.com/Shopify/ruby-lsp) | Shopify 出品 |
| **Elixir** | [elixir-ls](https://github.com/elixir-lsp/elixir-ls) | Elixir 社区标准 |
| **Clojure** | [clojure-lsp](https://github.com/clojure-lsp/clojure-lsp) | Clojure 社区标准 |
| **Terraform** | [terraform-ls](https://github.com/hashicorp/terraform-ls) | HashiCorp 官方 |
| **Dart** | [Dart SDK](https://github.com/dart-lang/sdk) | Dart 内置分析服务器 |
| **Nix** | [nil](https://github.com/oxalica/nil) / [nixd](https://github.com/nix-community/nixd) | Nix 语言服务器 |
| **Erlang** | [ELP](https://github.com/whatsapp/erlang-language-platform) | WhatsApp 出品 |
| **SQL** | [postgres-language-server](https://github.com/supabase-community/postgres-language-server) | Supabase 社区 |

### 通用/多语言 LSP

| 项目 | 说明 |
|------|------|
| [efm-langserver](https://github.com/mattn/efm-langserver) | 通用 LSP，可包装任意 linter/formatter |
| [diagnostic-languageserver](https://github.com/iamcco/diagnostic-languageserver) | 将 linter 输出转为 LSP 诊断 |
| [SonarLint Language Server](https://github.com/SonarSource/sonarlint-language-server) | 多语言代码质量 |
| [Harper](https://github.com/Automattic/harper) | 英文语法检查 LSP |

---

## 五、新兴趋势

### 1. AI + LSP

| 项目 | Stars | 说明 |
|------|-------|------|
| [lsp-ai](https://github.com/SilasMarvin/lsp-ai) | 3,184 | AI 驱动的 LSP 后端，开源 |
| [@github/copilot-language-server](https://www.npmjs.com/package/@github/copilot-language-server) | — | GitHub Copilot 的 LSP 后端 |
| [continue.dev](https://github.com/continuedev/continue) | — | 开源 AI 代码助手，LSP 集成 |

AI 与 LSP 的结合方向：
- LSP 为 AI 提供代码上下文（符号、类型、诊断）
- AI 作为 LSP 后端提供智能补全和重构
- LSP 的 diagnostics 可反馈 AI 生成代码的质量

### 2. MCP × LSP

Model Context Protocol (MCP) 与 LSP 的融合是 2025-2026 的热点：

- **MCP 作为 LSP 的消费者**：AI agent 通过 MCP 调用 LSP 获取代码智能
- **LSP → MCP 桥接**：将现有 LSP 服务器包装为 MCP 工具
- **示例项目**：[mcp-gopls](https://mcpservers.org/ja/servers/hloiseaufcms/mcp-gopls)

### 3. Rust 重写潮

越来越多的 LSP 服务器用 Rust 重写以获得极致性能：

- **ty** (Python) — astral-sh 出品，替代 Pyright/ruff-lsp
- **pyrefly** (Python) — Meta 出品
- **tinymist** (Typst) — Typst 语言
- **nil** (Nix) — Nix 语言
- **marksman** (Markdown) — Markdown 语言

趋势驱动因素：启动时间、内存占用、并发分析速度。

### 4. LSP 的 Web/云端扩展

- **Monaco LSP Client**：浏览器内 LSP，支持在线 IDE（如 CodeSandbox、GitHub Codespaces）
- **Theia**：云端 IDE 框架，完整 LSP 支持
- **wasm-language-server**：在 WebAssembly 中运行 LSP

### 5. LSP 3.17+ 新能力

- **Inlay Hints**：内联类型提示、参数名（2023 年正式落地）
- **Diagnostic Pull Model**：客户端按需拉取而非被动接收
- **Notebook Support**：Jupyter Notebook 原生支持
- **Linked Editing**：同步编辑配对符号
- **Type Hierarchy**：类型的继承/实现层级

---

## 六、社区 & 学习资源

### 官方资源

| 资源 | 链接 |
|------|------|
| LSP 规范 (3.18) | https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/ |
| LSP 官方 GitHub | https://github.com/microsoft/language-server-protocol |
| 服务器实现列表 | https://microsoft.github.io/language-server-protocol/implementors/servers/ |
| SDK 列表 | https://microsoft.github.io/language-server-protocol/implementors/sdks/ |
| 工具列表 | https://microsoft.github.io/language-server-protocol/implementors/tools/ |

### 博客 / 深度文章

| 标题 | 作者 | 主题 |
|------|------|------|
| [Language Server Protocol Guide](https://langserver.org/) | — | LSP 入门指南 |
| [Why I wrote a Language Server](https://mvolkmann.github.io/blog/) | R. Mark Volkmann | 实战经验 |
| [Building a Language Server with langium](https://langium.org/) | TypeFox | 从语法到 LSP |
| [rust-analyzer Architecture](https://rust-analyzer.github.io/) | rust-analyzer team | 架构设计 |
| [How VSCode Uses LSP](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide) | Microsoft | VSCode 客户端开发 |

### 社区讨论

| 平台 | 链接 |
|------|------|
| GitHub Discussions | https://github.com/microsoft/language-server-protocol/discussions |
| Discord (LSP) | https://discord.gg/lsp |
| Reddit r/LSP | https://reddit.com/r/language_server_protocol |
| Stack Overflow | `[language-server-protocol]` tag |

---

## 七、如何为你的语言选择/构建 LSP

```
1. 你的语言是否已有 LSP 服务器?
   ├─ 有 → 在官方实现列表中查找 → 直接使用
   └─ 无 → 进入下一步

2. 你的语言是否有成熟的编译器/分析库?
   ├─ 有 → 选择该语言的 LSP SDK，封装分析库
   │        (如 pygls 封装 jedi, lsp4j 封装 ECJ)
   └─ 无 → 考虑使用 langium 从语法定义生成

3. 性能要求?
   ├─ 极高 → Rust (tower-lsp) 或 Go
   ├─ 中等 → TypeScript (vscode-lsp-node) 或 Java (lsp4j)
   └─ 快速原型 → Python (pygls)

4. 编辑器支持?
   └─ VSCode 优先 → 用 vscode-languageserver-node，可复用 VSCode 扩展
```

---

## 八、关键指标对比

### 顶级服务器成熟度对比

| 服务器 | Completion | Hover | Def | Refs | Diagnostic | CodeAction | SemanticTokens | InlayHint |
|--------|-----------|-------|-----|------|------------|------------|----------------|-----------|
| rust-analyzer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| gopls | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ty | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| Pyright | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| clangd | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Eclipse JDT LS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HLS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| zls | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| lua-language-server | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| metals | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| kotlin-lsp | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| terraform-ls | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |

✅ = 完整支持 | ⚠️ = 部分支持 | — = 不支持或未知
