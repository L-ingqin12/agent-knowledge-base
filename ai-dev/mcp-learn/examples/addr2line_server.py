"""addr2line MCP Server — 将程序地址解析为源码位置

支持 ELF/DWARF 调试信息解析，封装 addr2line/objdump/readelf 等原生工具。
适用于调试 crash 堆栈、性能 profiling 地址反解等场景。
"""
import os
import re
import shutil
import subprocess
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("addr2line-server")

# ========== 工具查找 ==========

def _find_tool(name: str, hints: list[str] | None = None) -> str:
    """查找二进制工具路径，支持 NDK 交叉编译工具链"""
    # 1. 直接查找系统 PATH
    path = shutil.which(name)
    if path:
        return path

    # 2. 在提示目录中查找
    for hint in (hints or []):
        candidate = os.path.join(hint, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # 3. 扫描常见 NDK/工具链目录
    search_dirs = [
        os.path.expanduser("~/Android/Sdk/ndk"),
        os.path.expanduser("~/Library/Android/sdk/ndk"),
        "/usr/lib/llvm-*/bin",
        "/usr/bin",
    ]
    for base in search_dirs:
        for root, dirs, files in os.walk(base):
            for d in dirs[:]:
                if d.startswith("."):
                    dirs.remove(d)
            candidate = os.path.join(root, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            # 限制搜索深度
            if root.count(os.sep) - base.count(os.sep) > 3:
                dirs.clear()

    raise RuntimeError(f"未找到 {name}，请确认 binutils 或 NDK 已安装")

def _find_addr2line(arch: str | None = None) -> str:
    """查找 addr2line，支持交叉编译前缀"""
    if arch:
        prefixes = [
            f"{arch}-linux-android-addr2line",
            f"{arch}-linux-gnu-addr2line",
            f"llvm-addr2line",
        ]
        for prefix in prefixes:
            path = shutil.which(prefix)
            if path:
                return path
    return _find_tool("addr2line")

def _run(cmd: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    """安全地运行外部命令"""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

# ========== Tools ==========

@mcp.tool()
def detect_binary_info(binary_path: str) -> str:
    """检测二进制文件的基本信息: 架构、调试格式、是否 stripped

    Args:
        binary_path: ELF 二进制文件路径
    """
    if not os.path.isfile(binary_path):
        return f"错误: 文件不存在 — {binary_path}"

    readelf = _find_tool("readelf")
    file_cmd = _find_tool("file")

    lines = []

    # file 命令
    r = _run([file_cmd, binary_path])
    lines.append(f"[file] {r.stdout.strip()}")

    # ELF header
    r = _run([readelf, "-h", binary_path])
    if r.returncode == 0:
        for line in r.stdout.splitlines():
            line = line.strip()
            if "Machine:" in line or "Class:" in line or "OS/ABI:" in line:
                lines.append(f"[readelf] {line}")

    # 调试信息段
    r = _run([readelf, "-S", binary_path])
    if r.returncode == 0:
        debug_sections = []
        for line in r.stdout.splitlines():
            for s in [".debug_info", ".debug_line", ".debug_abbrev", ".debug_str", ".symtab", ".strtab"]:
                if s in line:
                    debug_sections.append(line.strip())
                    break
        if debug_sections:
            lines.append(f"\n[调试段] ({len(debug_sections)} 个):")
            lines.extend(f"  {s}" for s in debug_sections)
        else:
            lines.append("\n[调试段] 无 — 该二进制可能已 stripped")

    # 符号表
    r = _run([readelf, "-s", binary_path])
    if r.returncode == 0:
        symbol_count = sum(1 for l in r.stdout.splitlines() if "FUNC" in l)
        lines.append(f"\n[符号] 函数符号数: {symbol_count}")

    # addr2line 快速验证
    try:
        addr2line = _find_addr2line()
        r = _run([addr2line, "--version"], timeout=5)
        version = r.stdout.splitlines()[0] if r.stdout else "unknown"
        lines.append(f"\n[addr2line] {version}")
    except RuntimeError as e:
        lines.append(f"\n[addr2line] 不可用: {e}")

    return "\n".join(lines)


@mcp.tool()
def resolve_address(
    binary_path: str,
    address: str,
    arch: Optional[str] = None,
    show_inlines: bool = True,
) -> str:
    """将一个或多个地址解析为 函数名 + 源文件:行号

    Args:
        binary_path: 带调试信息的 ELF 文件路径
        address: 十六进制地址, 支持空格/逗号分隔多个地址, 如 "0x1234 0x5678"
        arch: 目标架构前缀 (arm, aarch64, x86_64), 可选
        show_inlines: 是否展开内联函数调用栈
    """
    if not os.path.isfile(binary_path):
        return f"错误: 文件不存在 — {binary_path}"

    addr2line = _find_addr2line(arch)

    # 解析地址列表
    addrs = re.split(r'[,\s]+', address.strip())
    addrs = [a for a in addrs if a]  # 去空

    results = []
    for addr in addrs:
        # 规范化地址格式
        addr = addr.strip()
        if not addr.startswith("0x") and not addr.startswith("0X"):
            addr = f"0x{addr}"

        cmd = [addr2line, "-e", binary_path, "-f", "-C", "-p"]
        if show_inlines:
            cmd.append("-i")
        cmd.append(addr)

        try:
            r = _run(cmd, timeout=10)
            output = r.stdout.strip()
            if not output or "??" in output:
                output = f"{addr}: ??:? (无调试信息或被 stripped)"
            results.append(output)
        except subprocess.TimeoutExpired:
            results.append(f"{addr}: 超时")
        except Exception as e:
            results.append(f"{addr}: 错误 — {e}")

    return "\n".join(results)


@mcp.tool()
def find_symbol(binary_path: str, pattern: str) -> str:
    """在二进制文件的符号表中搜索函数/变量

    Args:
        binary_path: ELF 文件路径
        pattern: 搜索关键词 (大小写敏感的子串匹配)
    """
    if not os.path.isfile(binary_path):
        return f"错误: 文件不存在 — {binary_path}"

    readelf = _find_tool("readelf")
    r = _run([readelf, "-s", binary_path])

    if r.returncode != 0:
        return f"readelf 失败: {r.stderr}"

    matches = []
    for line in r.stdout.splitlines():
        if pattern in line and ("FUNC" in line or "OBJECT" in line):
            # 提取: 地址 大小 类型 绑定 可见性 索引 名称
            parts = line.strip().split()
            if len(parts) >= 8:
                addr = parts[1]
                size = parts[2]
                sym_type = parts[3]
                name = parts[-1]
                matches.append(f"  {addr}  {size:>6s}  {sym_type:>6s}  {name}")

    if not matches:
        return f"未找到匹配 '{pattern}' 的符号。尝试用 objdump 查找动态符号..."

    return f"找到 {len(matches)} 个符号:\n" + "\n".join(matches[:50])


@mcp.tool()
def list_source_files(binary_path: str) -> str:
    """列出二进制文件中 DWARF 调试信息记录的所有源文件路径

    Args:
        binary_path: 带调试信息的 ELF 文件
    """
    if not os.path.isfile(binary_path):
        return f"错误: 文件不存在 — {binary_path}"

    readelf = _find_tool("readelf")
    # 使用 --debug-dump=line 获取源文件列表
    r = _run([readelf, "--debug-dump=line", binary_path])

    if r.returncode != 0:
        # 尝试 objdump
        objdump = _find_tool("objdump")
        r = _run([objdump, "--dwarf=decodedline", binary_path])
        if r.returncode != 0:
            return f"无法读取调试信息: {r.stderr[:200]}"

    # 解析 DWARF 输出，提取源文件路径
    seen = set()
    for line in r.stdout.splitlines():
        # 匹配 readelf --debug-dump=line 的目录表和文件表
        # The Directory Table / The File Name Table
        for match in re.finditer(r'([/\w.-]+\.(c|cpp|h|hpp|rs|go|java|py|s|S|asm))\b', line):
            f = match.group(1)
            if f not in seen:
                seen.add(f)

    if not seen:
        return "未找到源文件信息 (可能已 stripped 或无 DWARF 调试数据)"

    files = sorted(seen)
    return f"调试信息中包含 {len(files)} 个源文件:\n" + "\n".join(f"  {f}" for f in files[:100])


@mcp.tool()
def resolve_stack_trace(
    binary_path: str,
    stack_trace: str,
    arch: Optional[str] = None,
) -> str:
    """批量解析 crash 堆栈中的所有地址

    Args:
        binary_path: 带调试信息的 ELF 文件
        stack_trace: 原始堆栈文本，自动提取其中的十六进制地址
        arch: 目标架构前缀
    """
    if not os.path.isfile(binary_path):
        return f"错误: 文件不存在 — {binary_path}"

    # 提取所有十六进制地址
    pattern = r'(?:0x)?([0-9a-fA-F]{4,16})'
    addrs = re.findall(pattern, stack_trace)

    if not addrs:
        return "未在输入中找到十六进制地址"

    addr2line = _find_addr2line(arch)
    unique_addrs = list(dict.fromkeys(addrs))  # 去重保序

    results = []
    for addr in unique_addrs:
        cmd = [addr2line, "-e", binary_path, "-f", "-C", "-p", f"0x{addr}"]
        try:
            r = _run(cmd, timeout=5)
            output = r.stdout.strip()
            results.append(f"  0x{addr} → {output}")
        except Exception as e:
            results.append(f"  0x{addr} → 错误: {e}")

    return f"解析 {len(unique_addrs)} 个地址:\n" + "\n".join(results)


@mcp.tool()
def disassemble_range(
    binary_path: str,
    start_address: str = "0x0",
    count: int = 20,
    arch: Optional[str] = None,
) -> str:
    """反汇编指定地址附近的指令 (带源码交叉引用)

    Args:
        binary_path: ELF 文件
        start_address: 起始地址
        count: 反汇编指令条数
        arch: 目标架构
    """
    if not os.path.isfile(binary_path):
        return f"错误: 文件不存在 — {binary_path}"

    objdump = _find_tool("objdump")
    addr = start_address.strip()
    if not addr.startswith("0x"):
        addr = f"0x{addr}"

    # 计算起止地址
    start_int = int(addr, 16)
    end_int = start_int + count * 4  # 估算

    cmd = [
        objdump, "-d", "-S", "--no-show-raw-insn",
        f"--start-address={start_int}",
        f"--stop-address={end_int}",
        binary_path,
    ]
    r = _run(cmd, timeout=15)

    if r.returncode != 0:
        return f"objdump 失败: {r.stderr}"

    output = r.stdout.strip()
    if not output:
        return f"地址 {addr} 处无反汇编结果"

    # 限制输出行数
    lines = output.splitlines()
    if len(lines) > 80:
        lines = lines[:80]
        lines.append("... (输出已截断)")

    return "\n".join(lines)


# ========== Resources ==========

@mcp.resource("addr2line://supported-tools")
def supported_tools() -> str:
    """列出当前系统可用的二进制分析工具"""
    tools = ["addr2line", "readelf", "objdump", "nm", "file", "c++filt"]
    result = {}
    for tool in tools:
        path = shutil.which(tool)
        if path:
            r = _run([path, "--version"], timeout=3)
            version = r.stdout.splitlines()[0] if r.stdout else "unknown"
            result[tool] = f"{path} — {version}"
        else:
            result[tool] = "不可用"
    return "\n".join(f"  {k}: {v}" for k, v in result.items())


if __name__ == "__main__":
    mcp.run(transport="stdio")
