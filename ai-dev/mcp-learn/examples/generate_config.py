#!/usr/bin/env python3
"""MCP 多平台配置生成器 — 根据服务器信息生成各平台的配置 JSON

用法:
    python generate_config.py server_name /path/to/server.py [--http-port 8000]

输出 configs/ 目录, 包含 6 个平台的配置片段。
"""
import argparse, json, os

TEMPLATES = {
    "claude-code": {
        "file": "claude-code.json",
        "desc": "Claude Code / Claude Desktop",
        "config_path": "~/.claude.json 或 .mcp.json",
        "root_key": "mcpServers",
        "stdio": lambda name, cmd, args: {name: {"command": cmd, "args": args}},
        "http": None,  # Claude Desktop 不支持 HTTP
    },
    "opencode": {
        "file": "opencode.json",
        "desc": "OpenCode (opencode.ai)",
        "config_path": "~/.config/opencode/opencode.json",
        "root_key": "mcp",
        "stdio": lambda name, cmd, args: {name: {"type": "local", "command": cmd, "args": args, "enabled": True}},
        "http": lambda name, url: {name: {"type": "remote", "url": url}},
    },
    "cursor": {
        "file": "cursor.json",
        "desc": "Cursor Editor",
        "config_path": "~/.cursor/mcp.json",
        "root_key": "mcpServers",
        "stdio": lambda name, cmd, args: {name: {"command": cmd, "args": args}},
        "http": lambda name, url: {name: {"url": url, "transport": "sse"}},
    },
    "vscode-copilot": {
        "file": "vscode-copilot.json",
        "desc": "VS Code / GitHub Copilot",
        "config_path": ".vscode/mcp.json",
        "root_key": "servers",
        "stdio": lambda name, cmd, args: {name: {"type": "stdio", "command": cmd, "args": args}},
        "http": lambda name, url: {name: {"type": "sse", "url": url}},
    },
    "continue": {
        "file": "continue.json",
        "desc": "Continue.dev",
        "config_path": "~/.continue/config.json",
        "root_key": "mcpServers",
        "stdio": lambda name, cmd, args: [{"name": name, "transport": {"type": "stdio", "command": cmd, "args": args}}],
        "http": lambda name, url: [{"name": name, "url": url, "transport": "sse"}],
    },
    "zed": {
        "file": "zed.json",
        "desc": "Zed Editor (仅 stdio)",
        "config_path": "~/.config/zed/settings.json",
        "root_key": "assistant.mcp_servers",
        "stdio": lambda name, cmd, args: {name: {"command": cmd, "args": args}},
        "http": None,
    },
}


def main():
    parser = argparse.ArgumentParser(description="生成 MCP 多平台配置文件")
    parser.add_argument("name", help="MCP 服务器名称 (如 my-server)")
    parser.add_argument("command", help="启动命令 (如 python)")
    parser.add_argument("args", nargs="+", help="启动参数 (如 server.py)")
    parser.add_argument("--http-port", type=int, help="HTTP 端口 (可选, 生成远程配置)")
    parser.add_argument("--http-host", default="localhost", help="HTTP 主机 (默认 localhost)")
    parser.add_argument("--output", "-o", default="configs", help="输出目录 (默认 configs/)")
    parser.add_argument("--env", nargs="*", help="环境变量 KEY=VALUE")
    parser.add_argument("--description", default="", help="服务器描述")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # 解析 env
    env_vars = {}
    if args.env:
        for e in args.env:
            if "=" in e:
                k, v = e.split("=", 1)
                env_vars[k] = v

    http_url = f"http://{args.http_host}:{args.http_port}" if args.http_port else None

    generated = []

    for platform_id, tmpl in TEMPLATES.items():
        config = {"_meta": {
            "platform": tmpl["desc"],
            "config_file": tmpl["config_path"],
            "root_key": tmpl["root_key"],
            "server_name": args.name,
            "description": args.description,
        }}

        # stdio 配置
        stdio_conf = tmpl["stdio"](args.name, args.command, args.args)
        if env_vars:
            _inject_env(stdio_conf, env_vars)
        config["stdio"] = stdio_conf

        # HTTP 配置
        if http_url and tmpl["http"]:
            http_conf = tmpl["http"](args.name, http_url)
            if env_vars and "opencode" not in platform_id:
                _inject_env(http_conf, env_vars)
            config["streamable_http"] = http_conf

        filepath = os.path.join(args.output, tmpl["file"])
        with open(filepath, "w") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        generated.append(f"  {tmpl['file']:25s} → {tmpl['desc']} ({tmpl['config_path']})")

    print(f"已生成 {len(generated)} 个平台的配置文件:\n")
    for g in generated:
        print(g)

    print(f"\n输出目录: {args.output}/")
    print()
    print("使用方式:")
    print(f"  1. 打开对应的配置文件")
    print(f"  2. 将 stdio (或 streamable_http) 内容合并到你的客户端配置中")
    print(f"  3. 注意每个平台的 root_key 不同 (见 _meta.root_key)")

    # 生成 README
    readme_path = os.path.join(args.output, "README.md")
    with open(readme_path, "w") as f:
        f.write(f"# MCP 配置 — {args.name}\n\n")
        if args.description:
            f.write(f"{args.description}\n\n")
        f.write(f"服务器名: `{args.name}`\n")
        f.write(f"启动命令: `{args.command} {' '.join(args.args)}`\n")
        if http_url:
            f.write(f"HTTP 端点: `{http_url}`\n")
        f.write("\n## 各平台配置\n\n")
        f.write("| 平台 | 配置位置 | root_key | 传输 |\n")
        f.write("|------|----------|----------|------|\n")
        for platform_id, tmpl in TEMPLATES.items():
            transports = "stdio"
            if tmpl["http"]:
                transports += " + HTTP"
            f.write(f"| {tmpl['desc']} | `{tmpl['config_path']}` | `{tmpl['root_key']}` | {transports} |\n")
        f.write("\n## 详细配置\n\n")
        f.write("请打开各 `.json` 文件查看具体配置内容。\n")
        f.write("`_meta` 字段包含平台和路径说明。\n")
        f.write("`stdio` / `streamable_http` 字段包含实际配置。\n")
        f.write("\n## 环境变量\n\n")
        if env_vars:
            for k, v in env_vars.items():
                f.write(f"- `{k}` = `{v}`\n")
        else:
            f.write("无需特殊环境变量\n")

    print(f"\n配置说明: {readme_path}")


def _inject_env(config, env_vars):
    """在配置中注入环境变量 (处理不同平台的结构差异)"""
    if isinstance(config, dict):
        if "transport" in config and isinstance(config["transport"], dict):
            config["transport"]["env"] = dict(env_vars)
        elif "command" in config:  # 直接包含 command 的是 stdio
            config["env"] = dict(env_vars)
    elif isinstance(config, list):
        for item in config:
            if isinstance(item, dict):
                if "transport" in item and isinstance(item["transport"], dict):
                    item["transport"]["env"] = dict(env_vars)
                elif "command" in item:
                    item["env"] = dict(env_vars)


if __name__ == "__main__":
    main()
