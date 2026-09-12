# 08 — MCP vs Skill: 功能实现选型指南

## 一句话总结

**MCP 是"写代码"，Skill 是"写指令"。** 用 50 行 Python 解决问题选 MCP，用 50 行 prompt 指令解决问题选 Skill。

## 定义

| 维度 | MCP | Skill |
|------|-----|-------|
| 本质 | 独立进程，通过 JSON-RPC 与 AI 通信 | Claude Code 进程内的指令/工作流定义 |
| 文件形式 | Python/Node/Go 代码 | Markdown 文件 |
| 运行环境 | 独立进程 (任意语言/运行时) | Claude Code 内部 |
| 复用 | Claude Desktop, Cursor, Copilot, Zed... | 仅 Claude Code |

## 五维度决策框架

每个维度打分，偏向哪边就选哪个:

### 1. 运行环境

| 倾向 Skill | 倾向 MCP |
|-------------|----------|
| 纯 Claude Code 内部能力即可完成 | 需要启动子进程执行原生二进制 |
| 读写文件、搜索代码、git 操作、shell 调用 | 需要特定运行时 (Python 库、Node 包、C 扩展) |
| Claude Code 内置工具足够 | 需要操作系统级调用 (ptrace, ioctl, mmap) |

```
Skill: Claude Code 已有能力编排
MCP:   需要 Claude Code 不提供的底层能力
```

### 2. 复用范围

| 倾向 Skill | 倾向 MCP |
|-------------|----------|
| 仅你个人使用 | 团队共享、多客户端使用 |
| 单一场景 | 多场景复用 |
| 临时工作流 | 长期维护的服务能力 |

```
Skill: 个人效率工具
MCP:   团队基础设施
```

### 3. 逻辑复杂度

| 倾向 Skill | 倾向 MCP |
|-------------|----------|
| 线性步骤编排 (< 10 步) | 多分支逻辑、循环、状态机 |
| 无错误处理或简单 fallback | 需要细粒度错误处理、重试、超时 |
| 文本拼接、模板化 | 需要解析复杂输出 (JSON/XML/二进制) |
| 不超过 50 行指令 | 超过 200 行代码 |

```
Skill: 顺序流程
MCP:   复杂逻辑 + 错误处理
```

### 4. 外部依赖

| 倾向 Skill | 倾向 MCP |
|-------------|----------|
| 零第三方依赖 | 需要 pip install / npm install |
| 只用标准 shell 工具 | 需要特定版本库的 API |
| 无 API 密钥管理 | 需要管理 Token、证书、密钥 |

```
Skill: 零依赖
MCP:   需要库/API/凭证
```

### 5. 持久状态

| 倾向 Skill | 倾向 MCP |
|-------------|----------|
| 无状态，每次运行独立 | 需要数据库连接池 |
| 不需要缓存 | 需要内存/磁盘缓存 |
| 不需要配置持久化 | 需要配置文件、环境变量、密钥管理 |

```
Skill: 无状态函数
MCP:   有状态服务
```

## 快速判断流程

```
需要的能力 Claude Code 本身就有吗? (读写文件、搜索代码、git、shell)
│
├── 是 → 只是编排这些能力的顺序/逻辑?
│   ├── 是 → Skill
│   └── 仍需复杂逻辑 → 继续往下
│
└── 否 → 需要做什么?

    ├── 调用原生二进制 (addr2line, ffmpeg, objdump, readelf...)
    │   └── MCP ← Skill 调 bash 也能干，但解析输出/错误处理很脆弱
    │
    ├── 需要 Python/Node 第三方库 (Pillow, numpy, pdf-parser, sharp...)
    │   └── MCP ← Skill 无法 import 第三方库
    │
    ├── 需要维护长连接或复杂状态 (数据库连接池、WebSocket、缓存)
    │   └── MCP ← Skill 无状态模型
    │
    ├── 需要被多个 AI 客户端共用 (Claude Desktop + Cursor + Copilot)
    │   └── MCP ← Skill 只在 Claude Code 中有效
    │
    └── 以上都不是，只是把多步操作串起来
        └── Skill
```

## 案例参考

### 应选 MCP

| 功能 | 原因 |
|------|------|
| addr2line 地址反解 | 调原生二进制、解析 DWARF、架构适配、错误处理 |
| 图片 OCR/分析 | 需要 Pillow/pytesseract 库、base64 编码 |
| 数据库查询服务 | 连接池管理、参数化查询防注入、结果序列化 |
| 自定义 CI/CD 检查 | 需要解析 AST、跨文件分析、调用外部 lint 工具 |
| API 网关/代理 | 管理 API Key、限流、重试、缓存 |
| PDF 解析/生成 | 需要 ReportLab/pdfplumber 等库 |
| WebSocket 实时数据 | 长连接管理、断线重连 |

### 应选 Skill

| 功能 | 原因 |
|------|------|
| 标准 PR 工作流 | 纯 git add/commit/push/gh pr create 编排 |
| 代码审查清单 | 纯 prompt 模板，引导 Claude 按步骤检查 |
| 多步骤部署流程 | 编排 shell + git + API 调用顺序 |
| 技术文档生成 | prompt 模板 + 代码读取 + 格式转换 |
| 分支清理 | git branch -d + 条件判断 |
| 提交信息生成 | 读 diff → 分析 → 格式化，纯指令流 |
| 测试运行 + 修复循环 | pytest + 读结果 + 改代码，Claude Code 已有能力 |

### 边界案例

| 功能 | 选型 | 判断理由 |
|------|------|----------|
| 文件格式转换 (markdown→pdf) | **MCP** | 需要 pandoc/pdfkit 库，解析和渲染复杂 |
| 日志分析 | 看情况 | 简单 grep → Skill; 复杂聚合/图表 → MCP |
| 定时任务 | **MCP** | 需要 cron 调度、持久化任务状态 |
| 多 repo 批量操作 | 看情况 | 5 个以内 → Skill; 50 个 + 并发 → MCP |
| Chat 历史导出 | **MCP** | 需要格式转换库、模板引擎 |

## 决策反模式

| 反模式 | 问题 | 正确做法 |
|--------|------|----------|
| 把 500 行 Python 写成 Skill bash 脚本 | 脆弱、不可调试、无复用 | 写 MCP |
| 3 行 shell 包装成 MCP 服务 | 过度工程、维护负担 | 写 Skill |
| 把公司 API 密钥写在 Skill markdown 里 | 安全漏洞 | 写 MCP (用环境变量/密钥管理) |
| MCP 里只做 prompt 拼接 | 用错抽象层 | 写 Skill |
| 为了跨 IDE 复用把简单 shell alias 搞成 MCP | 杀鸡用牛刀 | 写 Skill |

## Skill 的边界何时被突破

以下信号说明你的 Skill 该升级为 MCP 了:

1. **bash 代码超过 50 行** — 可读性和可维护性急剧下降
2. **出现 try/catch 或类似错误处理** — bash 的错误处理非常脆弱
3. **需要 pip install / npm install** — Skill 无法管理依赖
4. **多个人要求使用你的功能** — 需要跨客户端复用了
5. **需要缓存或持久化状态** — Skill 无状态模型不够用
6. **出现 "把输出存到临时文件再解析" 的模式** — 这是 IPC 的原始形式，MCP 就是为此设计的

## 总结

```
                 复杂度 →
              简单          复杂
              │             │
能力来源      │             │
              │             │
Claude Code   │  Skill      │  Skill + bash
已有          │  (纯指令)    │  (小心边界)
              │             │
─────────────────────────────────────
              │             │
外部          │  MCP        │  MCP
二进制/库     │  (薄封装)    │  (完整服务)
              │             │
```

- **Skill** = 编排 Claude Code 已有能力 + 纯 prompt 工作流
- **MCP** = 为 Claude Code 扩展它不具备的能力 + 跨客户端复用

**唯一金标准: 需要写多少代码?** 写 prompt 解决 → Skill。写 Python/Node/Go 解决 → MCP。
