# MCP 示例服务器 — 使用与部署指南

## 目录

- [环境准备](#环境准备)
- [通用概念](#通用概念)
  - [三种运行方式](#三种运行方式)
  - [MCP Inspector 调试](#mcp-inspector-调试)
  - [Claude Desktop 集成](#claude-desktop-集成)
- [示例速览](#示例速览)
- [入门示例](#入门示例)
  - [simple_server — 最简入门](#simple_server--最简入门)
  - [multi_tool_server — 完整功能演示](#multi_tool_server--完整功能演示)
  - [http_server — HTTP 传输](#http_server--http-传输)
  - [client_demo — 客户端连接](#client_demo--客户端连接)
- [实战示例](#实战示例)
  - [addr2line_server — 程序地址反解](#addr2line_server--程序地址反解)
  - [image_understanding_server — 图片理解](#image_understanding_server--图片理解)
  - [excalidraw_server — Obsidian Excalidraw 图表](#excalidraw_server--obsidian-excalidraw-图表)
- [跨平台部署](#跨平台部署)
  - [配置生成器](#配置生成器)
  - [各平台配置速查](#各平台配置速查)
- [部署到生产环境](#部署到生产环境)
- [常见问题](#常见问题)

---

## 环境准备

```bash
# 1. 安装 Python MCP SDK (所有示例的公共依赖)
pip install mcp

# 2. (可选) 安装 MCP Inspector — 浏览器调试工具
npm install -g @modelcontextprotocol/inspector
# 或每次用 npx 运行
# npx @modelcontextprotocol/inspector

# 3. 各个示例的额外依赖
pip install pydantic        # multi_tool_server
pip install Pillow           # image_understanding_server
pip install pytesseract      # image_understanding_server (OCR)
# addr2line/excalidraw 无额外 Python 依赖，但需要系统工具
```

---

## 通用概念

### 三种运行方式

```
方式 1: stdio 传输 (最常用)
  ┌──────────┐  stdin/stdout   ┌──────────┐
  │ AI Host  │ ◄──────────────► │ MCP Server│
  │(Claude)  │    JSON-RPC      │ (子进程)  │
  └──────────┘                  └──────────┘
  适用: 本地开发、Claude Desktop、单用户

方式 2: Streamable HTTP 传输
  ┌──────────┐    HTTP POST    ┌──────────┐
  │ AI Host  │ ◄──────────────► │ MCP Server│
  │(远程)    │   /mcp 端点      │ (独立进程)│
  └──────────┘                  └──────────┘
  适用: 远程访问、团队共享、容器化部署

方式 3: MCP Inspector (开发调试)
  ┌──────────┐   代理 stdio     ┌──────────┐
  │ 浏览器 UI│ ◄──────────────► │ MCP Server│
  │ :5173    │                  │          │
  └──────────┘                  └──────────┘
  适用: 开发测试、查看工具列表、交互式调用
```

### MCP Inspector 调试

Inspector 是开发 MCP 服务器最常用的工具，启动后在浏览器中可视化调试。

```bash
# 启动 Inspector，它会启动你的服务器作为子进程
npx @modelcontextprotocol/inspector python examples/simple_server.py

# 指定工作目录
npx @modelcontextprotocol/inspector -w /path/to/workdir python server.py

# 连接已有的 HTTP 服务器
npx @modelcontextprotocol/inspector http://localhost:8000
```

浏览器打开 `http://localhost:5173` 后会看到:
- **左侧**: 服务器信息、Tools/Resources/Prompts 列表
- **右侧**: 交互式调用界面，可填写参数并查看返回结果

### Claude Desktop 集成

配置文件位置:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "MY_API_KEY": "xxx"
      }
    }
  }
}
```

配置后**重启 Claude Desktop**，服务器会自动启动。你可以在对话中直接使用服务器提供的工具。

---

## 示例速览

| 文件 | 工具数 | 复杂度 | 传输 | 用途 |
|------|--------|--------|------|------|
| `simple_server.py` | 2 tools + 1 resource + 1 prompt | ★☆☆☆☆ | stdio | 入门学习 |
| `multi_tool_server.py` | 5 tools + 3 resources + 2 prompts | ★★☆☆☆ | stdio | 完整功能演示 |
| `http_server.py` | 2 tools + 1 resource | ★★☆☆☆ | HTTP | HTTP 传输学习 |
| `client_demo.py` | N/A (客户端) | ★★☆☆☆ | stdio/HTTP | 客户端开发学习 |
| `addr2line_server.py` | 6 tools + 1 resource | ★★★★☆ | stdio | 生产级: 地址反解 |
| `image_understanding_server.py` | 6 tools + 1 resource | ★★★☆☆ | stdio | 生产级: 图片分析 |
| `excalidraw_server.py` | 16 tools + 2 resources | ★★★★★ | stdio | 生产级: 图表生成 |

---

## 入门示例

### simple_server — 最简入门

**功能**: greet 打招呼、add 加法、version 资源、code_review prompt

```bash
# 1. 用 Inspector 测试
npx @modelcontextprotocol/inspector python examples/simple_server.py

# 2. 用 mcp-cli 测试
pip install mcp-cli
mcp-cli --server "python examples/simple_server.py" tools list
mcp-cli --server "python examples/simple_server.py" tools call greet --args '{"name": "世界"}'
mcp-cli --server "python examples/simple_server.py" tools call add --args '{"a": 3, "b": 5}'

# 3. Claude Desktop 配置
# {
#   "mcpServers": {
#     "hello-world": {
#       "command": "python",
#       "args": ["/root/workspace/mcp-learn/examples/simple_server.py"]
#     }
#   }
# }
```

**预期结果**: Inspector 界面显示 2 个工具 (greet, add)、1 个资源 (config://version)、1 个 prompt

---

### multi_tool_server — 完整功能演示

**功能**: 天气查询、笔记 CRUD、计算器、时间查询。演示 Tools/Resources/Prompts 三种原语的完整用法。

```bash
# 安装依赖
pip install pydantic

# 启动 Inspector
npx @modelcontextprotocol/inspector python examples/multi_tool_server.py
```

**工具调用示例**:

```
工具: get_weather
参数: {"params": {"city": "北京", "units": "celsius"}}
返回: 北京: 22°C, 晴, 更新时间: 2026-05-30T...

工具: create_note
参数: {"params": {"title": "学习MCP", "content": "今天学习了MCP协议基础", "tags": ["mcp", "学习"]}}
返回: 笔记已创建, ID: 1

工具: search_notes
参数: {"keyword": "MCP"}
返回: [1] 学习MCP: 今天学习了MCP协议基础...

工具: calculate
参数: {"expression": "(3 + 5) * 2"}
返回: (3 + 5) * 2 = 16

资源: notes://all
资源: notes://1
资源: health://status
```

**Claude Desktop 配置**:
```json
{
  "mcpServers": {
    "multi-tool": {
      "command": "python",
      "args": ["/root/workspace/mcp-learn/examples/multi_tool_server.py"]
    }
  }
}
```

---

### http_server — HTTP 传输

**适用场景**: 远程服务器部署、团队共享、容器化

```bash
# 1. 启动 HTTP 服务器 (默认 127.0.0.1:8000)
python examples/http_server.py

# 2. 自定义地址和端口
python examples/http_server.py 0.0.0.0 9000

# 3. 用 Inspector 连接 HTTP 服务器
npx @modelcontextprotocol/inspector http://127.0.0.1:8000

# 4. 用 curl 直接测试
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# 5. 调用工具
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"echo","arguments":{"message":"hello"}}}'
```

**Claude Desktop 配置 (HTTP 模式)**:
```json
{
  "mcpServers": {
    "http-server": {
      "url": "http://127.0.0.1:8000",
      "transport": "streamable-http"
    }
  }
}
```

**生产部署 (uvicorn + nginx)**:
```bash
# 安装 uvicorn
pip install uvicorn

# 启动
uvicorn http_server:mcp.sse_app --host 0.0.0.0 --port 8000 --workers 4

# Nginx 反向代理 (详见 06-transports.md)
```

---

### client_demo — 客户端连接

**功能**: 演示如何用 Python 代码连接和调用 MCP 服务器

```bash
# stdio 模式 (连接 simple_server)
python examples/client_demo.py

# HTTP 模式 (需要先启动 http_server)
# 终端1: python examples/http_server.py
# 终端2: python examples/client_demo.py --http
```

**代码结构**:
```
demo_stdio_client()
  ├── 建立 stdio 连接 (启动 server 子进程)
  ├── session.initialize() — 握手
  ├── session.list_tools() — 发现工具
  ├── session.call_tool() — 调用工具
  ├── session.list_resources() — 发现资源
  ├── session.read_resource() — 读取资源
  └── session.list_prompts() — 发现提示
```

---

## 实战示例

### addr2line_server — 程序地址反解

**适用场景**: 调试 native crash、性能 profiling 地址反解、逆向工程

#### 系统依赖

```bash
# Ubuntu/Debian
apt install binutils

# macOS (Xcode 自带或)
brew install binutils

# Android NDK (交叉编译 addr2line)
# 下载 NDK 后无需额外配置，服务器会自动搜索
```

#### 使用示例

```bash
# 1. 启动 Inspector
npx @modelcontextprotocol/inspector python examples/addr2line_server.py

# 2. 或者用 mcp-cli 直接测试
# 假设你有一个带调试信息的 ELF 文件 /tmp/test_binary
```

**典型工作流**:

```
步骤1: 检测二进制信息
  工具: detect_binary_info
  参数: {"binary_path": "/path/to/binary"}
  返回: 架构 ARM64, 有 .debug_info .debug_line 段, 未 stripped

步骤2: 解析 crash 地址
  工具: resolve_address
  参数: {"binary_path": "/path/to/binary", "address": "0x1234 0x5678 0xabcd"}
  返回: 
    0x1234: my_function at src/main.c:42
    0x5678: another_func at src/utils.c:108
    0xabcd: ??:? (无调试信息)

步骤3: 查找符号
  工具: find_symbol
  参数: {"binary_path": "/path/to/binary", "pattern": "parseJson"}
  返回: 0x8f3c  156  FUNC  parseJsonInternal

步骤4: 反汇编上下文
  工具: disassemble_range
  参数: {"binary_path": "/path/to/binary", "start_address": "0x1234", "count": 10}
  返回: 10 条汇编指令 + 交叉引用的源码行

步骤5: 批量解析堆栈
  工具: resolve_stack_trace
  参数: {"binary_path": "/path/to/binary", "stack_trace": "backtrace:\n  #00 pc 0x1234\n  #01 pc 0x5678"}
  返回: 每个地址的函数名 + 源文件位置
```

**Claude Desktop 配置**:
```json
{
  "mcpServers": {
    "addr2line": {
      "command": "python",
      "args": ["/root/workspace/mcp-learn/examples/addr2line_server.py"]
    }
  }
}
```

配置后在 Claude Desktop 中你可以直接说:
- "帮我把这个 crash 堆栈里的地址都反解一下，binary 是 build/app"
- "查找 binary 中所有包含 'auth' 的函数符号"

---

### image_understanding_server — 图片理解

**适用场景**: 图片内容分析、OCR 文字提取、批量图片处理、EXIF 信息读取

#### 依赖安装

```bash
# 基础依赖 (图片信息、缩略图、base64 编码)
pip install Pillow

# OCR 依赖 (文字识别)
pip install pytesseract

# 系统 tesseract 引擎
# Ubuntu/Debian:
apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra

# macOS:
brew install tesseract tesseract-lang

# Windows:
# 下载安装 https://github.com/UB-Mannheim/tesseract/wiki
```

#### 使用示例

```bash
npx @modelcontextprotocol/inspector python examples/image_understanding_server.py
```

**典型工作流**:

```
场景1: 查看图片基本信息
  工具: get_image_info
  参数: {"image_path": "/path/to/photo.jpg"}
  返回: 格式 JPEG, 尺寸 4032x3024, EXIF (相机/时间/GPS)

场景2: 让 AI 分析图片内容 (与 AI 配合)
  工具: read_image_for_analysis
  参数: {"image_path": "/path/to/photo.jpg"}
  返回: base64 编码的图片数据 → AI 直接理解图片内容
  → 然后 AI 告诉你图片里有什么

场景3: 提取图片中的文字
  工具: extract_text_ocr
  参数: {"image_path": "/path/to/screenshot.png", "language": "chi_sim+eng"}
  返回: 识别出的中英文文字

场景4: 对比两张图片
  工具: compare_images
  参数: {"image_path1": "/path/to/img1.png", "image_path2": "/path/to/img2.png"}
  返回: 格式/尺寸/文件大小差异

场景5: 批量扫描目录
  工具: batch_analyze_directory
  参数: {"directory": "/path/to/photos", "pattern": "*.jpg"}
  返回: 所有 JPEG 图片的格式、尺寸列表

场景6: 生成缩略图
  工具: create_thumbnail
  参数: {"image_path": "/path/to/large.png", "max_size": 256}
  返回: 缩略图保存路径
```

**Claude Desktop 配置**:
```json
{
  "mcpServers": {
    "image-tools": {
      "command": "python",
      "args": ["/root/workspace/mcp-learn/examples/image_understanding_server.py"]
    }
  }
}
```

---

### excalidraw_server — Obsidian Excalidraw 图表

**适用场景**: 自动生成技术图表、解析/修改已有 Excalidraw 图形、AI 辅助绘图

此为功能最丰富的示例——**16 个工具 + 2 个资源**，覆盖 Excalidraw 绘图的完整生命周期。

#### 无额外依赖

```bash
pip install mcp   # 仅需 MCP SDK，无其他 Python 依赖
```

#### 支持的文件格式

| 格式 | 文件扩展名 | 说明 |
|------|------------|------|
| 纯 JSON | `.excalidraw` | excalidraw.com 原生格式 |
| Obsidian 嵌入 | `.excalidraw.md` | Obsidian Excalidraw Plugin 格式 |
| 通用 Markdown | `.md` | 兼容 Logseq 等工具 |

#### 使用示例

```bash
npx @modelcontextprotocol/inspector python examples/excalidraw_server.py
```

**工作流 A: AI 根据描述自动生成图表**

```
步骤1: 用 generate_from_prompt 创建图表
  工具: generate_from_prompt
  参数: {
    "filepath": "/vault/diagrams/login-flow.excalidraw",
    "prompt": "用户登录流程: 输入账号密码 → 验证身份 → 返回token → 进入主页 → 加载用户数据",
    "diagram_type": "flowchart",
    "color_scheme": "professional",
    "direction": "horizontal"
  }
  返回: 已生成含 5 个节点 + 4 条箭头的流程图

步骤2: 查看生成结果
  工具: read_drawing
  参数: {"filepath": "/vault/diagrams/login-flow.excalidraw"}
  返回: 格式/元素数量/类型分布/文字内容

步骤3: (可选) 用 Obsidian 打开
  在 Obsidian 中打开 login-flow.excalidraw.md → 看到完整流程图
```

**工作流 B: 理解和分析已有图表**

```
步骤1: 读取图表摘要
  工具: read_drawing
  参数: {"filepath": "/vault/architecture.excalidraw"}
  返回: 元素总数 23, 框架 2 个, 文字 "API Gateway" / "Auth Service" ...

步骤2: 查看整体统计
  工具: get_drawing_stats
  参数: {"filepath": "/vault/architecture.excalidraw"}
  返回: 类型分布, 连接关系, 画布尺寸 1200x900

步骤3: 按类型过滤
  工具: list_elements
  参数: {"filepath": "/vault/architecture.excalidraw", "element_type": "arrow"}
  返回: 12 条箭头及其绑定关系

步骤4: 搜索特定文字
  工具: list_elements
  参数: {"filepath": "/vault/architecture.excalidraw", "search_text": "Auth"}
  返回: 所有包含 "Auth" 的元素
```

**工作流 C: 修改和演进已有图表**

```
步骤1: 添加新节点
  工具: add_rectangle
  参数: {
    "filepath": "/vault/architecture.excalidraw",
    "x": 600, "y": 300,
    "width": 160, "height": 60,
    "label": "Cache Layer",
    "stroke_color": "orange",
    "background_color": "#fff3e0"
  }
  返回: 已添加矩形 + 标签文字

步骤2: 连接到已有节点
  工具: add_arrow_between
  参数: {
    "filepath": "/vault/architecture.excalidraw",
    "from_element_id": "api-gateway-id",
    "to_element_id": "cache-rect-id",
    "label": "查询缓存",
    "end_arrowhead": "arrow",
    "stroke_color": "gray"
  }
  返回: 已创建绑定箭头

步骤3: 修改元素样式
  工具: update_element
  参数: {
    "filepath": "/vault/architecture.excalidraw",
    "element_id": "api-gateway-id",
    "stroke_color": "red",
    "background_color": "#fff5f5"
  }

步骤4: 自动重排布局
  工具: auto_layout
  参数: {"filepath": "/vault/architecture.excalidraw", "direction": "horizontal", "gap": 180}
```

**工作流 D: 生成不同图表类型的 prompt 示例**

```
流程图 (flowchart):
  "用户注册流程: 填写信息 → 邮箱验证 → 设置密码 → 创建成功 → 自动登录"

思维导图 (mindmap):
  "系统架构: API Gateway, User Service, Order Service, Payment Service, Notification Service, Database Cluster"

架构图 (architecture):
  "三层架构: Web Layer → Application Layer → Data Layer"
  或 "节点: 负载均衡, Web服务器x4, 应用服务器x2, 数据库主从, Redis缓存"

时序图 (sequence):
  "参与者: Client, API Gateway, Auth Service, Database"

类图 (class_diagram):
  "Order, OrderItem, Customer, Payment, Shipping"
```

**Claude Desktop 配置**:
```json
{
  "mcpServers": {
    "excalidraw": {
      "command": "python",
      "args": ["/root/workspace/mcp-learn/examples/excalidraw_server.py"]
    }
  }
}
```

配置后在 Claude Desktop 中你可以说:
- "帮我在 vault/diagrams/ 下画一个微服务架构图，包含 API Gateway, Auth Service, User Service, Order Service, Database"
- "读取 vault/flow.excalidraw.md 这个图，告诉我里面有哪些流程步骤"
- "把系统架构图中的 Auth Service 改成红色的，在它旁边加一个 Cache Layer 节点并连线"

---

## 跨平台部署

一份 MCP 服务器代码，可部署到所有主流 AI 编码平台。

### 配置生成器

使用 `generate_config.py` 一键生成 6 个平台的配置文件:

```bash
# 基础用法: 生成所有平台的 stdio 配置
python examples/generate_config.py my-server python /path/to/server.py

# 带环境变量
python examples/generate_config.py my-server python server.py --env API_KEY=xxx

# 同时生成 HTTP 配置 (OpenCode/Cursor/Copilot 支持)
python examples/generate_config.py my-server python server.py --http-port 8000

# 指定输出目录
python examples/generate_config.py my-server python server.py -o my-configs/
```

生成的文件:
```
configs/
├── README.md           # 配置说明
├── claude-code.json    # Claude Code / Desktop
├── opencode.json       # OpenCode
├── cursor.json         # Cursor
├── vscode-copilot.json # VS Code Copilot
├── continue.json       # Continue.dev
└── zed.json            # Zed
```

每个 JSON 文件包含 `_meta` (平台/路径说明) + `stdio` + `streamable_http` (如可用)。

### 各平台配置速查

以 `simple_server.py` 为例，在 6 个平台上的配置差异:

**Claude Code** (`.mcp.json`):
```json
{"mcpServers": {"hello": {"command": "python", "args": ["/path/to/simple_server.py"]}}}
```

**OpenCode** (`~/.config/opencode/opencode.json`):
```json
{"mcp": {"hello": {"type": "local", "command": "python", "args": ["/path/to/simple_server.py"], "enabled": true}}}
```

**Cursor** (`~/.cursor/mcp.json`):
```json
{"mcpServers": {"hello": {"command": "python", "args": ["/path/to/simple_server.py"]}}}
```

**VS Code Copilot** (`.vscode/mcp.json`):
```json
{"servers": {"hello": {"type": "stdio", "command": "python", "args": ["/path/to/simple_server.py"]}}}
```

**Continue.dev** (`~/.continue/config.json`):
```json
{"mcpServers": [{"name": "hello", "transport": {"type": "stdio", "command": "python", "args": ["/path/to/simple_server.py"]}}]}
```

**Zed** (`~/.config/zed/settings.json`):
```json
{"assistant": {"mcp_servers": {"hello": {"command": "python", "args": ["/path/to/simple_server.py"]}}}}
```

### 关键差异记三点

1. **root key 不同**: `mcpServers` → `mcp` → `servers` → `context_servers`
2. **Continue.dev 用数组**: 其他都是 object，Continue 是 array + `name` 字段
3. **OpenCode 要 type + enabled**: `"type": "local"` 和 `"enabled": true` 是必填的

详细兼容性矩阵和更多陷阱见 [09-cross-platform.md](../09-cross-platform.md)。

---

## 部署到生产环境

### 方案一: stdio + Claude Desktop (最简单)

```bash
# 1. 放到固定目录
mkdir -p ~/mcp-servers/
cp examples/*.py ~/mcp-servers/

# 2. 配置 Claude Desktop
# 编辑 claude_desktop_config.json，指向 ~/mcp-servers/server.py

# 3. 重启 Claude Desktop
```

### 方案二: Docker + Streamable HTTP

```dockerfile
# Dockerfile
FROM python:3.12-slim
RUN pip install mcp pydantic
COPY my_server.py /app/server.py
WORKDIR /app
EXPOSE 8000
# 服务器需要支持 HTTP 模式
CMD ["python", "server.py"]
```

```bash
docker build -t my-mcp-server .
docker run -p 8000:8000 my-mcp-server

# Claude Desktop 连接
# {"mcpServers": {"my-server": {"url": "http://localhost:8000", "transport": "streamable-http"}}}
```

### 方案三: systemd 守护进程

```ini
# /etc/systemd/system/mcp-server.service
[Unit]
Description=MCP Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/mcp-servers
ExecStart=/home/your-user/.venv/bin/python /home/your-user/mcp-servers/http_server.py 0.0.0.0 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mcp-server
```

### 方案四: pipx 安装为可执行命令

```bash
# 如果你的服务器作为包发布
pipx install my-mcp-server

# Claude Desktop 配置
# {"command": "my-mcp-server", "args": []}
```

---

## 常见问题

### Q: Inspector 报 "Import 'mcp.server.fastmcp' could not be resolved"

```bash
pip install mcp
# 确认安装成功:
python -c "from mcp.server.fastmcp import FastMCP; print('OK')"
```

### Q: Claude Desktop 连接后看不到工具

1. 确认服务器能独立运行: `python server.py` (stdio 模式在终端直接运行会等输入，这是正常的)
2. 检查 Claude Desktop 配置 JSON 语法是否正确 (逗号、引号)
3. 确认路径是**绝对路径**
4. 查看 Claude Desktop 日志:
   - macOS: `~/Library/Logs/Claude/`
   - 搜索 "mcp" 相关错误

### Q: addr2line 找不到工具

服务器会自动搜索系统 PATH、NDK、LLVM 等目录。如果找不到:
```bash
# 手动安装
apt install binutils        # Linux
brew install binutils       # macOS

# 或者指定 NDK 路径
export PATH=$PATH:~/Android/Sdk/ndk/25.0.8775105/toolchains/llvm/prebuilt/linux-x86_64/bin
```

### Q: OCR 识别中文为空

```bash
# 确认安装了中文语言包
tesseract --list-langs | grep chi_sim
# 如果没有，安装:
apt install tesseract-ocr-chi-sim
```

### Q: excalidraw 生成的图在 Obsidian 中不显示

确认文件扩展名是 `.excalidraw.md` (不是 `.excalidraw` 或 `.md`)。
Obsidian Excalidraw Plugin 在 v2.2.0+ 使用新的嵌入格式，本工具生成的 JSON 兼容两种格式。

### Q: 如何让服务器同时支持 stdio 和 HTTP

```python
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dual-server")

@mcp.tool()
def hello() -> str:
    return "Hello"

if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
    else:
        mcp.run(transport="stdio")
```

---

## 开发建议

1. **先用 Inspector 开发** — 在浏览器中可视化调试，比连 Claude Desktop 高效
2. **tools 的 description 要写清楚** — AI 根据描述决定何时调用，模糊的描述会导致调用错误
3. **错误信息要有用** — 抛出有意义的 ValueError，AI 能看到错误并调整
4. **参数用 Pydantic 验证** — 类型安全 + 自动生成 JSON Schema
5. **先 stdio 后 HTTP** — 开发阶段用 stdio，生产部署再切 HTTP
