# 13 — GitHub 高分 MCP 项目目录

整理 GitHub 上最值得关注的 Awesome MCP 项目，按类别分类，附星数参考 (2026 年中)。

## 一、Awesome 精选列表

最权威的 MCP 项目发现入口。

| 项目 | 星数 | 特点 |
|------|------|------|
| **[punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)** | ~86k ⭐ | 最大最全的 MCP 服务器目录，按类别整理 (浏览器自动化、数据库、云平台、安全等)，带语言图标，接受 PR 提交 |
| **[wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers)** | ~88k ⭐ | 最早的精选列表，关联 mcpservers.org |
| **[Rodert/awesome-mcp](https://github.com/Rodert/awesome-mcp)** | 日更 | 4819+ 项目自动收录，每日 GitHub Actions 刷新，含星数排行 |
| **[abordage/awesome-mcp](https://github.com/abordage/awesome-mcp)** | 日更 | 自动维护，按 AI Agents/Memory/浏览器/CLI/数据库/开发者工具分类 |
| **[tolkonepiu/best-of-mcp-servers](https://github.com/tolkonepiu/best-of-mcp-servers)** | 周更 | 400+ 项目含质量评分，34 个类别，每周更新排名 |
| **[bh-rat/awesome-mcp-enterprise](https://github.com/bh-rat/awesome-mcp-enterprise)** | 精选 | 企业级: 私有注册中心、网关、安全治理、部署，不含个人服务器 |
| **[crowdere/Awesome-RE-MCP](https://github.com/crowdere/Awesome-RE-MCP)** | 62 ⭐ | 逆向工程 MCP 专项 (IDA Pro, Ghidra, Binary Ninja, Frida, x64dbg) |
| **[SciSharp/Awesome-DotNET-MCP](https://github.com/SciSharp/Awesome-DotNET-MCP)** | 143 ⭐ | .NET 生态 MCP 资源 |
| **[yzfly/Awesome-MCP-ZH](https://github.com/yzfly/Awesome-MCP-ZH)** | ~4k ⭐ | 中文 MCP 资源汇总 |

### 选择建议

- **日常浏览发现新项目** → punkpeye/awesome-mcp-servers (最大最全)
- **按质量排序选型** → tolkonepiu/best-of-mcp-servers (含评分)
- **企业级选型** → bh-rat/awesome-mcp-enterprise (治理/安全/部署)
- **特定领域** → Awesome-RE-MCP (逆向) / Awesome-DotNET-MCP (.NET)

---

## 二、官方参考实现

| 项目 | 星数 | 说明 |
|------|------|------|
| **[modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)** | ~87k ⭐ | 7 个活跃参考服务器: Everything, Fetch, Filesystem, Git, Memory, Sequential Thinking, Time |
| **[modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)** | ~22k ⭐ | Python 官方 SDK — `pip install mcp` |
| **[modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)** | ~12k ⭐ | TypeScript 官方 SDK — `npm i @modelcontextprotocol/sdk` |
| **[microsoft/mcp-for-beginners](https://github.com/microsoft/mcp-for-beginners)** | ~16k ⭐ | 11 模块官方课程，跨 6 语言，从入门到 PostgreSQL 集成 |

### 官方参考服务器详解

| 服务器 | 用途 | 学习价值 |
|--------|------|----------|
| **Filesystem** | 安全文件操作 + 访问控制 | 路径校验模式、最小 API surface 设计 |
| **Git** | 仓库读取、搜索、操作 | 命令封装、防误操作设计 |
| **Memory** | 知识图谱持久记忆 | 图数据库集成、状态管理 |
| **Fetch** | Web 内容抓取 + 格式转换 | HTTP 客户端封装、响应处理 |
| **Sequential Thinking** | 动态分步推理 | 多步有状态工作流模式 |
| **Time** | 时区转换 | 简单工具设计参考 |

---

## 三、教程与学习项目

| 项目 | 星数 | 适合人群 |
|------|------|----------|
| **[microsoft/mcp-for-beginners](https://github.com/microsoft/mcp-for-beginners)** | ~16k ⭐ | 所有人的首选，11 模块 + 7 案例 + PostgreSQL 实战 |
| **[DazzleML/MCP-Server-Tutorial](https://github.com/DazzleML/MCP-Server-Tutorial)** | — | Python 开发者，含 VS Code 调试配置和 9 章教程 |
| **[ydmitry/mcp-tools-cookbook](https://github.com/ydmitry/mcp-tools-cookbook)** | 19 ⭐ | 设计模式配方集: Prompt 暴露、多步工作流、客户端编排 |
| **[smithery-ai/smithery-cookbook](https://github.com/smithery-ai/smithery-cookbook)** | 16 ⭐ | FastMCP Python/TS 示例，stdio→HTTP 迁移，Docker 部署 |
| **[ran-isenberg/aws-lambda-mcp-cookbook](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook)** | — | Serverless MCP 部署: Lambda + CDK + CI/CD + DynamoDB |

---

## 四、SDK 与框架

| 项目 | 语言 | 星数 | 特点 |
|------|------|------|------|
| **[jlowin/fastmcp](https://github.com/jlowin/fastmcp)** | Python | ~25k ⭐ | 最流行的 Python MCP 框架，装饰器 API |
| **[modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)** | Python | ~22k ⭐ | 官方，底层控制 |
| **[modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)** | TypeScript | ~12k ⭐ | 官方 |
| **[modelcontextprotocol/csharp-sdk](https://github.com/modelcontextprotocol/csharp-sdk)** | C# | — | Microsoft 官方，v1.0 (2026.03) |
| **[rust-mcp-stack/rust-mcp-sdk](https://github.com/rust-mcp-stack/rust-mcp-sdk)** | Rust | — | 2025-11-25 全特性，OAuth，DNS rebinding 保护 |
| **[mark3labs/mcp-go](https://github.com/mark3labs/mcp-go)** | Go | — | 社区最流行的 Go SDK |
| **[fiberplane/mcp-lite](https://github.com/fiberplane/mcp-lite)** | TS (边缘) | — | 零依赖，Cloudflare Workers/Deno/Bun 可用 |

---

## 五、高星 MCP 服务器 (按领域)

### 浏览器自动化

| 项目 | 星数 | 说明 |
|------|------|------|
| **[microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)** | ~33k ⭐ | 浏览器自动化标杆，Microsoft 官方 |
| **[browserbase/stagehand](https://github.com/browserbase/stagehand)** | — | AI 驱动的浏览器操作 |

### 开发者工具

| 项目 | 星数 | 说明 |
|------|------|------|
| **[github/github-mcp-server](https://github.com/github/github-mcp-server)** | ~30k ⭐ | GitHub 官方 MCP 服务器 |
| **[modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)** | ~87k ⭐ | 7 个官方参考实现 |
| **[ComposioHQ/composio](https://github.com/ComposioHQ/composio)** | ~28k ⭐ | 1000+ 工具集成平台，含认证管理和工具搜索 |

### 设计与创意

| 项目 | 星数 | 说明 |
|------|------|------|
| **[ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)** | ~22k ⭐ | Blender 3D 建模集成 |
| **[glips/Figma-Context-MCP](https://github.com/glips/Figma-Context-MCP)** | ~15k ⭐ | Figma 设计稿 → AI 理解 |

### 数据库

| 项目 | 星数 | 说明 |
|------|------|------|
| **[crystaldba/postgres-mcp](https://github.com/crystaldba/postgres-mcp)** | ~1.1k ⭐ | 生产级 PostgreSQL，可配置读写权限 |
| **[ClickHouse/mcp-clickhouse](https://github.com/ClickHouse/mcp-clickhouse)** | ~513 ⭐ | ClickHouse 官方 |

### 可观测性与安全

| 项目 | 星数 | 说明 |
|------|------|------|
| Sentry MCP (内建) | 60M 请求/月 | 生产级错误监控 |
| **[anthropics/skills](https://github.com/anthropics/skills)** | — | Anthropic 官方 Skills (Claude Code 内置) |

---

## 六、服务器脚手架与构建工具

| 项目 | 星数 | 说明 |
|------|------|------|
| **[boguan/create-mcp-app](https://github.com/boguan/create-mcp-app)** | 56 ⭐ | TypeScript MCP 脚手架 CLI |
| **[Nishant-Chaudhary5338/mcp-toolkit](https://github.com/Nishant-Chaudhary5338/mcp-toolkit)** | — | 17 个 MCP 包 (React/TS 自动化)，450 测试 |
| **[mcp-server-forge](https://pypi.org/project/mcp-server-forge/)** | PyPI | Python 脚手架: `mcp-forge new/test/validate/publish` |
| **[vlyl/mcpc](https://github.com/vlyl/mcpc)** | 7 ⭐ | Rust 写的 TS/Python 模板生成器 |
| **[CaptainCrouton89/mcp-maker](https://github.com/CaptainCrouton89/mcp-maker)** | 4 ⭐ | MCP 服务器生成 MCP 服务器 (元工具) |

---

## 七、企业网关与安全治理

MCP 企业级基础设施，2025-2026 年增长最快的细分领域。

### 网关 (Gateway)

| 项目 | 说明 |
|------|------|
| **[agentic-community/mcp-gateway-registry](https://github.com/agentic-community/mcp-gateway-registry)** | 企业级 Gateway + Registry，OAuth (Keycloak/Entra)，OpenTelemetry |
| **[abwaters/mcp-zero](https://github.com/abwaters/mcp-zero)** | 轻量治理网关，YAML 策略，PII 脱敏 (Presidio) |
| **IBM ContextForge** | 开源 Registry + Proxy，RBAC，gRPC→MCP 转换，多传输 |
| **Docker MCP Gateway** | 容器隔离 + 密钥管理 + 签名验证 |
| **Microsoft MCP Gateway** | K8s-native，会话感知路由 |
| **Traefik Hub MCP Gateway** | 基于任务的访问控制 (TBAC) |
| **MetaMCP** | 多 MCP 聚合代理，OAuth 中间件 |

### 安全

| 领域 | 关键工具 |
|------|----------|
| 认证 | Scalekit, Stytch, WorkOS (OAuth 2.1 专为 MCP 设计) |
| 运行时安全 | Acuvity (Proofpoint 收购), Invariant Labs (Snyk 收购) |
| 零信任 | Pomerium (人/服务/AI Agent 统一身份) |
| 策略执行 | APM (Microsoft) — install-time 策略 + CI gate + lockfile |
| 威胁检测 | Noma Security — 无 Agent MCP 发现 + 供应链扫描 |

**安全现状 (2026 年 3 月)**:
- 38% 的扫描 MCP 服务器无认证
- 30 个 MCP 相关 CVE (60 天内)
- 43% 的实现存在命令注入漏洞

---

## 八、生态系统总览

```
MCP 生态 (GitHub 300K+ Stars)

├── 官方组织 (155K+ stars, 30+ repos)
│   ├── specification
│   ├── python-sdk
│   ├── typescript-sdk
│   ├── servers (参考实现)
│   └── docs
│
├── Awesome 列表 (聚合发现)
│   ├── punkpeye/awesome-mcp-servers ★86k
│   ├── wong2/awesome-mcp-servers ★88k
│   └── tolkonepiu/best-of-mcp-servers (质量评分)
│
├── 学习资源
│   ├── microsoft/mcp-for-beginners ★16k
│   ├── MCP-Server-Tutorial
│   └── mcp-tools-cookbook
│
├── 高星服务器
│   ├── servers (官方) ★87k
│   ├── playwright-mcp ★33k
│   ├── github-mcp-server ★30k
│   ├── composio ★28k
│   ├── fastmcp ★25k
│   ├── blender-mcp ★22k
│   └── Figma-Context-MCP ★15k
│
├── 企业基础设施
│   ├── 网关 (10+ 方案)
│   ├── 安全治理 (19+ 方案)
│   ├── 注册中心 (15+ 方案)
│   └── 部署平台 (8+ 方案)
│
└── 社区
    ├── mcpservers.org
    ├── registry.modelcontextprotocol.io
    ├── MCP Discord (glama.ai/mcp/discord)
    └── /r/mcp (Reddit)
```

---

## 九、推荐探索路径

```
第 1 步: 学习
  → microsoft/mcp-for-beginners (官方课程)
  → modelcontextprotocol/servers (看官方怎么写)

第 2 步: 发现
  → punkpeye/awesome-mcp-servers (浏览有什么)
  → tolkonepiu/best-of-mcp-servers (找高质量的)

第 3 步: 构建
  → fastmcp (Python) 或 typescript-sdk (TS)
  → mcp-server-forge (脚手架快速起步)
  → mcp-tools-cookbook (设计模式参考)

第 4 步: 部署
  → stdio (个人) → Docker (团队) → Gateway (企业)
  → bh-rat/awesome-mcp-enterprise (企业方案选型)

第 5 步: 分享
  → 提交 PR 到 awesome-mcp-servers
  → 发布到 mcpservers.org
  → 分享到 MCP Discord / Reddit
```
