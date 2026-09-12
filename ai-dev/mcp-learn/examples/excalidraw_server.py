#!/usr/bin/env python3
"""Obsidian Excalidraw MCP Server — 读取、理解、修改、生成 Excalidraw 图

支持:
- .excalidraw (纯 JSON, excalidraw.com 格式)
- .excalidraw.md (Obsidian Excalidraw Plugin 格式, Markdown + 嵌入 JSON)

能力:
- 读取并解析绘图文件, 输出结构化摘要
- 搜索/过滤元素 (按类型、文本、属性)
- 增删改元素 (矩形、椭圆、菱形、箭头、文字、自由绘制)
- 元素绑定 (箭头连接形状、文字标签绑定)
- 根据自然语言描述自动生成绘图
"""
import json
import math
import os
import re
import random
from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("obsidian-excalidraw-server")

# ============================================================
# Constants
# ============================================================

EXCALIDRAW_NEW_FILE = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": [],
    "appState": {
        "gridSize": None,
        "viewBackgroundColor": "#ffffff",
    },
    "files": {},
}

COLORS = {
    "black": "#1e1e1e", "red": "#e03131", "blue": "#1971c2",
    "green": "#2f9e44", "orange": "#f08c00", "purple": "#9c36b5",
    "gray": "#868e96", "pink": "#c2255c", "cyan": "#1098ad",
    "yellow": "#f59f00", "white": "#ffffff",
}

STROKE_STYLES = ["solid", "dashed", "dotted"]
FILL_STYLES = ["solid", "hachure", "cross-hatch"]
FONT_FAMILIES = {1: "Virgil (手写)", 2: "Helvetica (无衬线)", 3: "Cascadia (等宽)"}
ARROWHEAD_TYPES = [None, "arrow", "bar", "dot", "triangle"]
ELEMENT_TYPES = [
    "rectangle", "ellipse", "diamond", "arrow", "line",
    "freedraw", "text", "image", "frame",
]

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 800
DEFAULT_ELEMENT_SIZE = 200


# ============================================================
# Format detection / parsing
# ============================================================

def _detect_format(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".excalidraw":
        return "json"
    if ext in (".md", ".excalidraw.md") or filepath.endswith(".excalidraw.md"):
        return "obsidian"
    raise ValueError(f"不支持的文件格式: {filepath}")


def _load_drawing(filepath: str) -> tuple[dict, str]:
    """加载绘图文件, 返回 (data, format)"""
    fmt = _detect_format(filepath)
    if not os.path.exists(filepath):
        raise ValueError(f"文件不存在: {filepath}")

    raw = open(filepath, encoding="utf-8").read()

    if fmt == "json":
        return json.loads(raw), "json"
    else:
        # obsidian markdown 格式
        # 匹配 ```json ... ``` 或 ```json ... ```+ LZString 压缩
        # Drawing 数据在 %% 注释块中
        match = re.search(r"```json\s*\n(.*?)\n```", raw, re.DOTALL)
        if not match:
            match = re.search(r"```json\s*\n(.*?)\n```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1)), "obsidian"
            except json.JSONDecodeError:
                pass

        # 可能是压缩格式, 尝试整段提取
        match = re.search(r'%%\s*\n## Drawing\s*\n```json\s*\n(.*?)\n```\s*\n%%', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1)), "obsidian"
            except json.JSONDecodeError:
                raise ValueError("无法解析压缩的绘图数据 (需要 LZString 解压)")

        raise ValueError("无法在 .md 文件中找到嵌入的绘图 JSON 数据")


def _save_drawing(filepath: str, data: dict) -> str:
    """保存绘图文件"""
    fmt = _detect_format(filepath)
    if fmt == "json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        # obsidian markdown: 更新嵌入的 JSON
        if os.path.exists(filepath):
            raw = open(filepath, encoding="utf-8").read()
        else:
            raw = f"---\nexcalidraw-plugin: parsed\n---\n\n# Excalidraw Data\n## Drawing\n```json\n\n```\n"

        drawing_json = json.dumps(data, ensure_ascii=False, indent=2)
        # 替换 %% 注释块中的 JSON
        if "```json" in raw:
            raw = re.sub(
                r"(```json\s*\n).*?(\n```)",
                rf"\1{drawing_json}\2",
                raw, flags=re.DOTALL, count=1,
            )
        else:
            raw += f"\n%%\n## Drawing\n```json\n{drawing_json}\n```\n%%\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(raw)

    return fmt


def _make_id() -> str:
    """生成类似 excalidraw 的元素 ID"""
    # excalidraw ID 格式: 20 位 base64url 随机字符
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    return "".join(random.choices(chars, k=20))


def _build_base_element(
    element_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    **overrides,
) -> dict:
    """构建一个 Excalidraw 元素的基础结构"""
    el: dict[str, Any] = {
        "id": _make_id(),
        "type": element_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": COLORS["black"],
        "backgroundColor": "transparent",
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3} if element_type == "rectangle" else None,
        "boundElements": [],
        "updated": int(datetime.now().timestamp() * 1000),
        "link": None,
        "locked": False,
    }
    el.update(overrides)
    return el


# ============================================================
# Tools — Read / Understand
# ============================================================

@mcp.tool()
def read_drawing(filepath: str) -> str:
    """读取并解析 Excalidraw 绘图文件, 返回结构化摘要

    支持 .excalidraw (纯JSON) 和 .excalidraw.md (Obsidian嵌入格式) 两种格式
    """
    data, fmt = _load_drawing(filepath)
    elements = data.get("elements", [])

    # 统计
    type_counts = {}
    text_elements = []
    frames = []
    for el in elements:
        if el.get("isDeleted"):
            continue
        t = el.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        if t == "text" and el.get("text"):
            text_elements.append(el.get("text", ""))
        if t in ("frame", "magicframe"):
            frames.append(el.get("name", "(未命名)"))

    lines = [
        f"文件: {os.path.basename(filepath)}",
        f"格式: {'Obsidian Excalidraw (markdown)' if fmt == 'obsidian' else '纯净 JSON (.excalidraw)'}",
        f"元素总数: {len([e for e in elements if not e.get('isDeleted')])}",
        f"类型分布: {json.dumps(type_counts, ensure_ascii=False)}",
    ]

    if frames:
        lines.append(f"框架: {', '.join(frames)}")
    if text_elements:
        preview = text_elements[:10]
        lines.append(f"文字内容 ({len(text_elements)} 处):")
        for t in preview:
            lines.append(f"  \"{t[:80]}{'...' if len(t) > 80 else ''}\"")

    return "\n".join(lines)


@mcp.tool()
def list_elements(
    filepath: str,
    element_type: str = "all",
    search_text: str = "",
    limit: int = 50,
) -> str:
    """列出绘图中的所有元素, 支持按类型和文字过滤

    Args:
        filepath: 绘图文件路径
        element_type: 过滤元素类型 (rectangle/ellipse/diamond/arrow/line/text/frame/freedraw 或 all)
        search_text: 搜索文字内容 (模糊匹配)
        limit: 最多返回条数
    """
    data, _ = _load_drawing(filepath)
    elements = data.get("elements", [])

    results = []
    for el in elements:
        if el.get("isDeleted"):
            continue
        t = el.get("type", "?")
        if element_type != "all" and t != element_type:
            continue

        text_content = el.get("text", "")
        if search_text and search_text.lower() not in text_content.lower():
            continue

        info = {
            "id": el["id"][:8],
            "type": t,
            "x": round(el.get("x", 0)),
            "y": round(el.get("y", 0)),
            "w": round(el.get("width", 0)),
            "h": round(el.get("height", 0)),
        }
        if t == "text":
            info["text"] = text_content[:60]
        if t in ("arrow", "line"):
            info["points"] = len(el.get("points", []))
            info["startBinding"] = bool(el.get("startBinding"))
            info["endBinding"] = bool(el.get("endBinding"))
        if el.get("groupIds"):
            info["groups"] = el["groupIds"]
        if el.get("boundElements"):
            info["bound"] = [b["id"][:8] for b in el["boundElements"]]

        results.append(info)

    if len(results) > limit:
        results = results[:limit]
        truncated = True
    else:
        truncated = False

    return json.dumps({
        "file": os.path.basename(filepath),
        "filter": f"type={element_type}, search='{search_text}'",
        "total_matched": len([e for e in elements if not e.get("isDeleted")]),
        "showing": len(results),
        "truncated": truncated,
        "elements": results,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def get_element_detail(filepath: str, element_id: str) -> str:
    """获取单个元素的完整属性 (用于理解绑定关系、颜色、样式等细节)

    Args:
        filepath: 绘图文件路径
        element_id: 元素 ID (完整或前8位前缀)
    """
    data, _ = _load_drawing(filepath)
    for el in data.get("elements", []):
        if el["id"] == element_id or el["id"].startswith(element_id):
            return json.dumps(el, ensure_ascii=False, indent=2)
    return json.dumps({"error": f"未找到元素: {element_id}"}, ensure_ascii=False)


@mcp.tool()
def get_drawing_stats(filepath: str) -> str:
    """获取绘图整体统计信息: 元素数量、连接关系、空间分布等"""
    data, _ = _load_drawing(filepath)
    elements = [e for e in data.get("elements", []) if not e.get("isDeleted")]

    if not elements:
        return json.dumps({"message": "绘图为空"}, ensure_ascii=False)

    types = {}
    texts = 0
    arrows = 0
    bindings = 0
    groups = set()
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    for el in elements:
        t = el["type"]
        types[t] = types.get(t, 0) + 1
        if el.get("text"):
            texts += 1

        x, y = el.get("x", 0), el.get("y", 0)
        w, h = el.get("width", 0), el.get("height", 0)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)

        if t in ("arrow", "line"):
            arrows += 1
            if el.get("startBinding"):
                bindings += 1
            if el.get("endBinding"):
                bindings += 1
        for g in el.get("groupIds", []):
            groups.add(g)

    # 连接关系
    connections = []
    for el in elements:
        if el["type"] in ("arrow", "line"):
            sb = el.get("startBinding")
            eb = el.get("endBinding")
            if sb or eb:
                connections.append({
                    "arrow_id": el["id"][:8],
                    "from": sb["elementId"][:8] if sb else None,
                    "to": eb["elementId"][:8] if eb else None,
                })

    return json.dumps({
        "file": os.path.basename(filepath),
        "total_elements": len(elements),
        "type_distribution": types,
        "text_elements": texts,
        "arrows": arrows,
        "bindings": bindings,
        "groups": len(groups),
        "canvas_bounds": {
            "x": [round(min_x), round(max_x)],
            "y": [round(min_y), round(max_y)],
            "size": f"{round(max_x - min_x)} x {round(max_y - min_y)}",
        },
        "connections": connections[:30],
    }, ensure_ascii=False, indent=2)


# ============================================================
# Tools — Modify / Add
# ============================================================

@mcp.tool()
def add_rectangle(
    filepath: str,
    x: float,
    y: float,
    width: float = 150,
    height: float = 80,
    label: str = "",
    stroke_color: str = "black",
    background_color: str = "transparent",
    fill_style: str = "hachure",
) -> str:
    """在绘图中添加矩形

    Args:
        filepath: 绘图文件路径
        x, y: 左上角坐标
        width, height: 宽高
        label: 矩形内的文字标签 (为空则不添加)
        stroke_color: 边框颜色 (black/red/blue/green/orange/purple/gray/pink/cyan)
        background_color: 填充色
        fill_style: 填充样式 (solid/hachure/cross-hatch)
    """
    data, _ = _load_drawing(filepath)

    rect = _build_base_element(
        "rectangle", x, y, width, height,
        strokeColor=COLORS.get(stroke_color, stroke_color),
        backgroundColor=background_color,
        fillStyle=fill_style,
    )

    new_elements = [rect]

    if label:
        text_el = _build_base_element(
            "text",
            x + 10, y + height / 2 - 12,
            width - 20, 24,
            type="text",
            text=label,
            fontSize=16,
            fontFamily=2,
            textAlign="center",
            verticalAlign="middle",
            containerId=rect["id"],
            lineHeight=1.25,
        )
        rect["boundElements"].append({"type": "text", "id": text_el["id"]})
        new_elements.append(text_el)

    data["elements"].extend(new_elements)
    fmt = _save_drawing(filepath, data)

    return json.dumps({
        "success": True,
        "added": [f"rectangle id={rect['id'][:8]} with label='{label}'" if label else f"rectangle id={rect['id'][:8]}"],
        "saved_as": fmt,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def add_ellipse(
    filepath: str,
    x: float,
    y: float,
    width: float = 120,
    height: float = 120,
    label: str = "",
    stroke_color: str = "black",
    background_color: str = "transparent",
) -> str:
    """在绘图中添加椭圆/圆形

    Args:
        filepath: 绘图文件路径
        x, y: 左上角坐标
        width, height: 宽高 (相等为圆形)
        label: 椭圆内文字
        stroke_color, background_color: 颜色
    """
    data, _ = _load_drawing(filepath)

    ellipse = _build_base_element(
        "ellipse", x, y, width, height,
        strokeColor=COLORS.get(stroke_color, stroke_color),
        backgroundColor=background_color,
        roundness=None,
    )

    new_elements = [ellipse]

    if label:
        text_el = _build_base_element(
            "text",
            x + 20, y + height / 2 - 12,
            width - 40, 24,
            type="text",
            text=label,
            fontSize=16,
            fontFamily=2,
            textAlign="center",
            verticalAlign="middle",
            containerId=ellipse["id"],
            lineHeight=1.25,
        )
        ellipse["boundElements"].append({"type": "text", "id": text_el["id"]})
        new_elements.append(text_el)

    data["elements"].extend(new_elements)
    fmt = _save_drawing(filepath, data)

    return json.dumps({"success": True, "added": [f"ellipse id={ellipse['id'][:8]}"], "saved_as": fmt}, ensure_ascii=False, indent=2)


@mcp.tool()
def add_diamond(
    filepath: str,
    x: float,
    y: float,
    width: float = 120,
    height: float = 120,
    label: str = "",
    stroke_color: str = "black",
    background_color: str = "transparent",
) -> str:
    """在绘图中添加菱形 (常用于流程图决策节点)

    Args:
        filepath: 绘图文件路径
        x, y: 左上角坐标
        width, height: 宽高
        label: 菱形内文字
        stroke_color, background_color: 颜色
    """
    data, _ = _load_drawing(filepath)

    diamond = _build_base_element(
        "diamond", x, y, width, height,
        strokeColor=COLORS.get(stroke_color, stroke_color),
        backgroundColor=background_color,
        roundness=None,
    )

    new_elements = [diamond]

    if label:
        text_el = _build_base_element(
            "text",
            x + 30, y + height / 2 - 12,
            width - 60, 24,
            type="text",
            text=label,
            fontSize=14,
            fontFamily=2,
            textAlign="center",
            verticalAlign="middle",
            containerId=diamond["id"],
            lineHeight=1.25,
        )
        diamond["boundElements"].append({"type": "text", "id": text_el["id"]})
        new_elements.append(text_el)

    data["elements"].extend(new_elements)
    fmt = _save_drawing(filepath, data)

    return json.dumps({"success": True, "added": [f"diamond id={diamond['id'][:8]}"], "saved_as": fmt}, ensure_ascii=False, indent=2)


@mcp.tool()
def add_text(
    filepath: str,
    x: float,
    y: float,
    content: str,
    font_size: int = 16,
    font_family: int = 2,
    text_align: str = "left",
    stroke_color: str = "black",
) -> str:
    """在绘图中添加独立文字元素

    Args:
        filepath: 绘图文件路径
        x, y: 文字坐标
        content: 文字内容
        font_size: 字体大小
        font_family: 1=手写, 2=Helvetica, 3=等宽
        text_align: 对齐方式 (left/center/right)
        stroke_color: 文字颜色
    """
    data, _ = _load_drawing(filepath)

    el = _build_base_element(
        "text",
        x, y, 400, font_size * 1.5,
        type="text",
        text=content,
        fontSize=font_size,
        fontFamily=font_family,
        textAlign=text_align,
        verticalAlign="top",
        containerId=None,
        lineHeight=1.25,
        strokeColor=COLORS.get(stroke_color, stroke_color),
        backgroundColor="transparent",
        fillStyle="solid",
        strokeWidth=0,
        roughness=0,
        roundness=None,
        autoResize=True,
    )

    data["elements"].append(el)
    fmt = _save_drawing(filepath, data)

    return json.dumps({"success": True, "added": f"text id={el['id'][:8]}: \"{content[:40]}\"", "saved_as": fmt}, ensure_ascii=False, indent=2)


@mcp.tool()
def add_arrow(
    filepath: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    label: str = "",
    start_arrowhead: str = "none",
    end_arrowhead: str = "arrow",
    stroke_color: str = "black",
    stroke_style: str = "solid",
    elbowed: bool = False,
) -> str:
    """在绘图中添加箭头/连接线 (自由坐标模式)

    Args:
        filepath: 绘图文件路径
        x1, y1: 起点坐标
        x2, y2: 终点坐标
        label: 箭头上的文字
        start_arrowhead: 起点箭头样式 (none/arrow/bar/dot/triangle)
        end_arrowhead: 终点箭头样式
        stroke_color: 线条颜色
        stroke_style: solid/dashed/dotted
        elbowed: 是否使用直角弯折
    """
    data, _ = _load_drawing(filepath)

    arrow = _build_base_element(
        "arrow",
        x1, y1,
        0, 0,
        points=[[0, 0], [x2 - x1, y2 - y1]],
        startBinding=None,
        endBinding=None,
        startArrowhead=None if start_arrowhead == "none" else start_arrowhead,
        endArrowhead=None if end_arrowhead == "none" else end_arrowhead,
        strokeColor=COLORS.get(stroke_color, stroke_color),
        strokeStyle=stroke_style,
        roundness={"type": 2},
        elbowed=elbowed,
    )

    new_elements = [arrow]

    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2 - 10
        text_el = _build_base_element(
            "text",
            mx - 40, my,
            80, 20,
            type="text",
            text=label,
            fontSize=12,
            fontFamily=2,
            textAlign="center",
            verticalAlign="middle",
            containerId=None,
            lineHeight=1.25,
            strokeColor=COLORS.get(stroke_color, stroke_color),
            strokeWidth=0,
            roughness=0,
            roundness=None,
        )
        arrow["boundElements"].append({"type": "text", "id": text_el["id"]})
        new_elements.append(text_el)

    data["elements"].extend(new_elements)
    fmt = _save_drawing(filepath, data)

    return json.dumps({"success": True, "added": [f"arrow id={arrow['id'][:8]}"], "saved_as": fmt}, ensure_ascii=False, indent=2)


@mcp.tool()
def add_arrow_between(
    filepath: str,
    from_element_id: str,
    to_element_id: str,
    label: str = "",
    end_arrowhead: str = "arrow",
    stroke_color: str = "black",
    stroke_style: str = "solid",
) -> str:
    """在两个元素之间添加绑定箭头 (元素间连接)

    Args:
        filepath: 绘图文件路径
        from_element_id: 起始元素 ID (完整或前缀)
        to_element_id: 目标元素 ID (完整或前缀)
        label: 箭头标签
        end_arrowhead: 箭头样式
        stroke_color, stroke_style: 样式
    """
    data, _ = _load_drawing(filepath)

    # 查找元素
    from_el = to_el = None
    for el in data["elements"]:
        if el["id"] == from_element_id or el["id"].startswith(from_element_id):
            from_el = el
        if el["id"] == to_element_id or el["id"].startswith(to_element_id):
            to_el = el

    if not from_el:
        return json.dumps({"error": f"未找到源元素: {from_element_id}"}, ensure_ascii=False)
    if not to_el:
        return json.dumps({"error": f"未找到目标元素: {to_element_id}"}, ensure_ascii=False)

    # 计算箭头起止点 (元素中心)
    fx, fy = from_el["x"], from_el["y"]
    fw, fh = from_el.get("width", 0), from_el.get("height", 0)
    tx, ty = to_el["x"], to_el["y"]
    tw, th = to_el.get("width", 0), to_el.get("height", 0)

    arrow = _build_base_element(
        "arrow",
        fx + fw / 2, fy + fh / 2,
        0, 0,
        points=[[0, 0], [(tx + tw / 2) - (fx + fw / 2), (ty + th / 2) - (fy + fh / 2)]],
        startBinding={"elementId": from_el["id"], "focus": 0.0, "gap": 4},
        endBinding={"elementId": to_el["id"], "focus": 0.0, "gap": 4},
        startArrowhead=None,
        endArrowhead=end_arrowhead,
        strokeColor=COLORS.get(stroke_color, stroke_color),
        strokeStyle=stroke_style,
        roundness={"type": 2},
    )

    from_el.setdefault("boundElements", []).append({"type": "arrow", "id": arrow["id"]})
    to_el.setdefault("boundElements", []).append({"type": "arrow", "id": arrow["id"]})

    new_elements = [arrow]

    if label:
        mx = (fx + fw / 2 + tx + tw / 2) / 2
        my = (fy + fh / 2 + ty + th / 2) / 2 - 10
        text_el = _build_base_element(
            "text",
            mx - 40, my,
            80, 20,
            type="text",
            text=label,
            fontSize=12,
            fontFamily=2,
            textAlign="center",
            verticalAlign="middle",
            containerId=None,
            lineHeight=1.25,
            strokeColor=COLORS.get(stroke_color, stroke_color),
            strokeWidth=0,
            roughness=0,
            roundness=None,
        )
        arrow["boundElements"].append({"type": "text", "id": text_el["id"]})
        new_elements.append(text_el)

    data["elements"].extend(new_elements)
    fmt = _save_drawing(filepath, data)

    return json.dumps({
        "success": True,
        "arrow_id": arrow["id"][:8],
        "from": f"{from_el['type']}:{from_el['id'][:8]}",
        "to": f"{to_el['type']}:{to_el['id'][:8]}",
        "saved_as": fmt,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def update_element(
    filepath: str,
    element_id: str,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
    text: str | None = None,
    stroke_color: str | None = None,
    background_color: str | None = None,
    font_size: int | None = None,
    opacity: int | None = None,
    locked: bool | None = None,
) -> str:
    """修改已有元素的属性

    Args:
        filepath: 绘图文件路径
        element_id: 要修改的元素 ID
        x, y: 新坐标 (可选)
        width, height: 新尺寸 (可选)
        text: 新文字内容 (文本元素)
        stroke_color: 新边框/文字颜色
        background_color: 新填充色
        font_size: 新字体大小
        opacity: 不透明度 (0-100)
        locked: 是否锁定
    """
    data, _ = _load_drawing(filepath)

    target = None
    for el in data["elements"]:
        if el["id"] == element_id or el["id"].startswith(element_id):
            target = el
            break

    if not target:
        return json.dumps({"error": f"未找到元素: {element_id}"}, ensure_ascii=False)

    changed = []
    if x is not None:
        target["x"] = x; changed.append(f"x={x}")
    if y is not None:
        target["y"] = y; changed.append(f"y={y}")
    if width is not None:
        target["width"] = width; changed.append(f"width={width}")
    if height is not None:
        target["height"] = height; changed.append(f"height={height}")
    if text is not None:
        target["text"] = text; changed.append("text updated")
    if stroke_color is not None:
        target["strokeColor"] = COLORS.get(stroke_color, stroke_color); changed.append(f"strokeColor={stroke_color}")
    if background_color is not None:
        target["backgroundColor"] = background_color; changed.append(f"backgroundColor={background_color}")
    if font_size is not None:
        target["fontSize"] = font_size; changed.append(f"fontSize={font_size}")
    if opacity is not None:
        target["opacity"] = max(0, min(100, opacity)); changed.append(f"opacity={opacity}")
    if locked is not None:
        target["locked"] = locked; changed.append(f"locked={locked}")

    target["updated"] = int(datetime.now().timestamp() * 1000)
    fmt = _save_drawing(filepath, data)

    return json.dumps({
        "success": True,
        "element": target["id"][:8],
        "type": target["type"],
        "changed": changed,
        "saved_as": fmt,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def delete_element(filepath: str, element_id: str) -> str:
    """删除指定元素 (同时也清理相关的绑定文本/箭头)

    Args:
        filepath: 绘图文件路径
        element_id: 要删除的元素 ID
    """
    data, _ = _load_drawing(filepath)

    target = None
    target_idx = -1
    full_id = element_id
    for i, el in enumerate(data["elements"]):
        if el["id"] == element_id or el["id"].startswith(element_id):
            target = el
            target_idx = i
            full_id = el["id"]
            break

    if target is None:
        return json.dumps({"error": f"未找到元素: {element_id}"}, ensure_ascii=False)

    # 收集需要一并删除的元素 (绑定到这个元素的文字、箭头)
    ids_to_delete = {full_id}
    for el in data["elements"]:
        if el.get("containerId") == full_id:
            ids_to_delete.add(el["id"])
        if el.get("startBinding", {}).get("elementId") == full_id:
            ids_to_delete.add(el["id"])
        if el.get("endBinding", {}).get("elementId") == full_id:
            ids_to_delete.add(el["id"])

    # 清理其他元素的 boundElements 引用
    for el in data["elements"]:
        bound = el.get("boundElements")
        if bound:
            el["boundElements"] = [b for b in bound if b["id"] not in ids_to_delete]

    # 删除
    data["elements"] = [e for e in data["elements"] if e["id"] not in ids_to_delete]

    fmt = _save_drawing(filepath, data)
    return json.dumps({
        "success": True,
        "deleted_ids": [i[:8] for i in ids_to_delete],
        "count": len(ids_to_delete),
        "saved_as": fmt,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def group_elements(filepath: str, element_ids: list[str]) -> str:
    """将多个元素编组

    Args:
        filepath: 绘图文件路径
        element_ids: 要编组的元素 ID 列表
    """
    data, _ = _load_drawing(filepath)
    group_id = _make_id()

    grouped = 0
    for el in data["elements"]:
        if el["id"] in element_ids or any(el["id"].startswith(pid) for pid in element_ids):
            g = el.get("groupIds", [])
            g.append(group_id)
            el["groupIds"] = g
            grouped += 1

    fmt = _save_drawing(filepath, data)
    return json.dumps({"success": True, "group_id": group_id[:8], "grouped_elements": grouped, "saved_as": fmt}, ensure_ascii=False, indent=2)


# ============================================================
# Tools — Generate
# ============================================================

def _parse_prompt(prompt: str) -> dict:
    """从自然语言 prompt 中提取图表类型和节点信息"""
    prompt_lower = prompt.lower()

    # 检测图表类型
    if any(k in prompt_lower for k in ["flowchart", "flow chart", "流程图", "流程"]):
        diagram_type = "flowchart"
    elif any(k in prompt_lower for k in ["mindmap", "mind map", "思维导图", "脑图"]):
        diagram_type = "mindmap"
    elif any(k in prompt_lower for k in ["architecture", "架构", "系统设计", "system design"]):
        diagram_type = "architecture"
    elif any(k in prompt_lower for k in ["sequence", "时序", "sequence diagram"]):
        diagram_type = "sequence"
    elif any(k in prompt_lower for k in ["class diagram", "类图", "uml"]):
        diagram_type = "class_diagram"
    else:
        diagram_type = "generic"

    # 提取节点 (中英文)
    # 模式: "包含 X, Y, Z" / "步骤: A → B → C" / "节点: A, B, C"
    nodes = []
    edges = []

    # 尝试提取 A → B 箭头关系
    arrow_pattern = r'(\S+?)\s*[-=]>\s*(\S+)'
    arrow_matches = re.findall(arrow_pattern, prompt)
    for a, b in arrow_matches:
        edges.append((a.strip(), b.strip()))
        for n in [a.strip(), b.strip()]:
            if n not in nodes:
                nodes.append(n)

    # 尝试提取列表: "节点: A, B, C" / "components: A, B, C"
    list_pattern = r'(?:nodes?|节点|components?|组件|步骤|steps?|layers?|层)[:：]\s*([^\n]+)'
    list_match = re.search(list_pattern, prompt_lower if "节点" not in prompt else prompt)
    # 用原始 prompt 重新匹配
    list_match = re.search(r'(?:nodes?|节点|components?|组件|步骤|steps?|layers?|层)\s*[:：]\s*([^\n]+)', prompt, re.IGNORECASE)
    if list_match:
        items = re.split(r'[,，;；、]\s*', list_match.group(1))
        for item in items:
            item = item.strip().rstrip('.。')
            if item and item not in nodes:
                nodes.append(item)

    # 按行提取 (每行一个节点)
    if not nodes:
        lines = [l.strip() for l in prompt.split("\n") if l.strip()]
        for line in lines:
            # 跳过明显的描述句
            if len(line) < 3 or any(line.lower().startswith(w) for w in ["create", "draw", "make", "生成", "绘制", "创建"]):
                continue
            # 跳过带箭头的行 (已处理)
            if re.search(arrow_pattern, line):
                continue
            # 提取独立短语作为节点
            clean = re.sub(r'^[\d]+[\.\)、]\s*', '', line)  # 去掉编号
            clean = clean.rstrip('.。')
            if clean and clean not in nodes and len(clean) < 80:
                nodes.append(clean)

    return {"type": diagram_type, "nodes": nodes, "edges": edges}


@mcp.tool()
def generate_from_prompt(
    filepath: str,
    prompt: str,
    diagram_type: str = "auto",
    color_scheme: str = "default",
    direction: str = "horizontal",
) -> str:
    """根据自然语言描述自动生成 Excalidraw 绘图

    支持: 流程图(flowchart)、思维导图(mindmap)、架构图(architecture)、时序图(sequence)、类图(class_diagram)

    Args:
        filepath: 保存路径 (.excalidraw 或 .excalidraw.md)
        prompt: 自然语言描述, 如 "用户登录流程: 输入账号 → 验证密码 → 进入主页"
        diagram_type: 图表类型 (auto/flowchart/mindmap/architecture/sequence/class_diagram)
        color_scheme: 配色 (default/pastel/dark/professional)
        direction: 方向 (horizontal/vertical), 仅 flowchart/mindmap/architecture 有效
    """
    # 解析 prompt
    parsed = _parse_prompt(prompt)
    if diagram_type == "auto":
        diagram_type = parsed["type"]

    nodes = parsed.get("nodes", [])
    edges = parsed.get("edges", [])

    # 如果解析不到节点，尝试按逗号/分号分割
    if not nodes:
        # fallback: 从 prompt 中逐行提取
        lines = [l.strip() for l in prompt.split("\n") if l.strip() and len(l.strip()) > 2]
        nodes = [re.sub(r'^\d+[\.\)、]\s*', '', l).rstrip('.。') for l in lines]

    # 如果还是没有节点，直接从 prompt 中提取逗号分隔的短语
    if not nodes:
        raw = re.sub(r'(create|draw|make|generate|绘制|生成|创建|画|做)\s+(a |an |一个)?', '', prompt, flags=re.IGNORECASE)
        # 分割提取
        parts = re.split(r'[,，;；\n]', raw)
        nodes = [p.strip().rstrip('.。') for p in parts if p.strip() and len(p.strip()) > 2]

    if not nodes:
        return json.dumps({
            "error": "无法从 prompt 中提取节点信息。请使用以下格式之一:\n"
                     "  - \"A → B → C → D\"\n"
                     "  - \"节点: A, B, C, D\"\n"
                     "  - 或在 prompt 中逐行列出节点"
        }, ensure_ascii=False, indent=2)

    # 配色方案
    color_schemes = {
        "default": [COLORS["black"], COLORS["blue"], COLORS["green"], COLORS["orange"], COLORS["purple"]],
        "pastel": ["#a3d2ca", "#f4c7ab", "#b4a7d6", "#ffe599", "#d5a6bd"],
        "dark": ["#495057", "#212529", "#343a40", "#6c757d", "#adb5bd"],
        "professional": ["#1971c2", "#2f9e44", "#e03131", "#f08c00", "#9c36b5"],
    }
    colors = color_schemes.get(color_scheme, color_schemes["default"])

    is_vertical = direction == "vertical"
    elements = []

    if diagram_type == "flowchart":
        elements = _generate_flowchart(nodes, edges, colors, is_vertical)
    elif diagram_type == "mindmap":
        elements = _generate_mindmap(nodes, colors, is_vertical)
    elif diagram_type == "architecture":
        elements = _generate_architecture(nodes, edges, colors, is_vertical)
    elif diagram_type == "sequence":
        elements = _generate_sequence(nodes, colors)
    elif diagram_type == "class_diagram":
        elements = _generate_class_diagram(nodes, colors, is_vertical)
    else:
        elements = _generate_flowchart(nodes, edges, colors, is_vertical)

    # 保存
    data = dict(EXCALIDRAW_NEW_FILE)
    data["elements"] = elements
    fmt = _save_drawing(filepath, data)

    return json.dumps({
        "success": True,
        "diagram_type": diagram_type,
        "node_count": len(nodes),
        "element_count": len(elements),
        "file": filepath,
        "format": fmt,
        "nodes": nodes,
        "edges": [[a, b] for a, b in edges],
    }, ensure_ascii=False, indent=2)


def _generate_flowchart(nodes, edges, colors, vertical):
    """生成流程图: 矩形节点 + 箭头连接"""
    elements = []
    gap = 160
    box_w, box_h = 140, 60

    if vertical:
        x0, y0 = 100, 80
        for i, node in enumerate(nodes):
            x = x0
            y = y0 + i * gap
            color = colors[i % len(colors)]
            rect = _build_base_element(
                "rectangle", x, y, box_w, box_h,
                strokeColor=color, backgroundColor="transparent", fillStyle="solid",
            )
            rect["id"] = f"node-{i:04d}"  # 稳定 ID 用于 edges
            elements.append(rect)
            if node:
                text_el = _build_base_element(
                    "text", x + 10, y + box_h / 2 - 10, box_w - 20, 20,
                    type="text", text=node, fontSize=13, fontFamily=2,
                    textAlign="center", verticalAlign="middle",
                    containerId=rect["id"], lineHeight=1.25,
                    strokeColor=color, strokeWidth=0, roughness=0, roundness=None,
                )
                rect["boundElements"].append({"type": "text", "id": text_el["id"]})
                elements.append(text_el)
            if i > 0:
                arrow = _build_base_element(
                    "arrow",
                    x0 + box_w / 2, y0 + (i - 1) * gap + box_h,
                    0, 0,
                    points=[[0, 0], [0, gap - box_h]],
                    startBinding={"elementId": f"node-{i-1:04d}", "focus": 0.0, "gap": 4},
                    endBinding={"elementId": f"node-{i:04d}", "focus": 0.0, "gap": 4},
                    startArrowhead=None, endArrowhead="arrow",
                    strokeColor=COLORS["gray"], roundness={"type": 2},
                )
                elements.append(arrow)
    else:
        x0, y0 = 80, 200
        for i, node in enumerate(nodes):
            x = x0 + i * gap
            y = y0
            color = colors[i % len(colors)]
            rect = _build_base_element(
                "rectangle", x, y, box_w, box_h,
                strokeColor=color, backgroundColor="transparent", fillStyle="solid",
            )
            rect["id"] = f"node-{i:04d}"
            elements.append(rect)
            if node:
                text_el = _build_base_element(
                    "text", x + 10, y + box_h / 2 - 10, box_w - 20, 20,
                    type="text", text=node, fontSize=13, fontFamily=2,
                    textAlign="center", verticalAlign="middle",
                    containerId=rect["id"], lineHeight=1.25,
                    strokeColor=color, strokeWidth=0, roughness=0, roundness=None,
                )
                rect["boundElements"].append({"type": "text", "id": text_el["id"]})
                elements.append(text_el)
            if i > 0:
                arrow = _build_base_element(
                    "arrow",
                    x0 + (i - 1) * gap + box_w, y0 + box_h / 2,
                    0, 0,
                    points=[[0, 0], [gap - box_w, 0]],
                    startBinding={"elementId": f"node-{i-1:04d}", "focus": 0.0, "gap": 4},
                    endBinding={"elementId": f"node-{i:04d}", "focus": 0.0, "gap": 4},
                    startArrowhead=None, endArrowhead="arrow",
                    strokeColor=COLORS["gray"], roundness={"type": 2},
                )
                elements.append(arrow)

    # 额外 edges
    for src, dst in edges:
        src_idx = nodes.index(src) if src in nodes else -1
        dst_idx = nodes.index(dst) if dst in nodes else -1
        if src_idx >= 0 and dst_idx >= 0:
            elements.append(_build_base_element(
                "arrow",
                0, 0, 0, 0,
                points=[[0, 0], [0, 0]],
                startBinding={"elementId": f"node-{src_idx:04d}", "focus": 0.0, "gap": 4},
                endBinding={"elementId": f"node-{dst_idx:04d}", "focus": 0.0, "gap": 4},
                startArrowhead=None, endArrowhead="arrow",
                strokeColor=COLORS["blue"], roundness={"type": 2},
            ))

    return elements


def _generate_mindmap(nodes, colors, vertical):
    """生成思维导图: 中心节点 + 辐射分支"""
    elements = []
    cx, cy = 500, 400
    center_color = colors[0]

    # 中心节点
    center = _build_base_element(
        "ellipse", cx - 60, cy - 60, 120, 120,
        strokeColor=center_color, backgroundColor=colors[1] if len(colors) > 1 else "#a5d8ff",
        fillStyle="solid", roughness=0, roundness=None,
    )
    center["id"] = "mindmap-center"
    elements.append(center)

    if nodes:
        center_label = _build_base_element(
            "text", cx - 50, cy - 14, 100, 28,
            type="text", text=nodes[0], fontSize=16, fontFamily=2,
            textAlign="center", verticalAlign="middle",
            containerId=center["id"], lineHeight=1.25,
            strokeColor="#ffffff", strokeWidth=0, roughness=0, roundness=None,
        )
        center["boundElements"].append({"type": "text", "id": center_label["id"]})
        elements.append(center_label)

    # 分支 (二级节点)
    branches = nodes[1:] if len(nodes) > 1 else nodes
    n = len(branches)
    radius = 200

    for i, branch in enumerate(branches):
        angle = (i / max(n, 1)) * 2 * 3.14159 - 3.14159 / 2
        bx = cx + radius * math.cos(angle) - 60
        by = cy + radius * math.sin(angle) - 25
        color = colors[i % len(colors)]

        r = _build_base_element(
            "rectangle", bx, by, 120, 50,
            strokeColor=color, backgroundColor="transparent",
            fillStyle="solid", roughness=0,
        )
        r["id"] = f"mindmap-branch-{i:04d}"
        elements.append(r)

        if branch:
            tb = _build_base_element(
                "text", bx + 8, by + 13, 104, 24,
                type="text", text=branch, fontSize=12, fontFamily=2,
                textAlign="center", verticalAlign="middle",
                containerId=r["id"], lineHeight=1.25,
                strokeColor=color, strokeWidth=0, roughness=0, roundness=None,
            )
            r["boundElements"].append({"type": "text", "id": tb["id"]})
            elements.append(tb)

        # 连线
        elements.append(_build_base_element(
            "arrow",
            cx, cy, 0, 0,
            points=[[0, 0], [bx + 60 - cx, by + 25 - cy]],
            startBinding={"elementId": center["id"], "focus": 0.0, "gap": 4},
            endBinding={"elementId": r["id"], "focus": 0.0, "gap": 4},
            startArrowhead=None, endArrowhead="arrow",
            strokeColor=COLORS["gray"], strokeStyle="dashed",
            roundness={"type": 2},
        ))

    return elements


def _generate_architecture(nodes, edges, colors, vertical):
    """生成架构图: 分层/分组矩形框"""
    elements = []
    x0, y0 = 80, 80
    layer_h = 100
    layer_gap = 20
    canvas_w = 900

    for i, node in enumerate(nodes):
        y = y0 + i * (layer_h + layer_gap) if vertical else y0
        x = x0 if vertical else x0 + i * 220
        w = canvas_w if vertical else 200
        h = layer_h if vertical else 300

        color = colors[i % len(colors)]
        rect = _build_base_element(
            "rectangle", x, y, w, h,
            strokeColor=color, backgroundColor=f"{color}15",
            fillStyle="solid", roughness=0,
        )
        rect["id"] = f"arch-{i:04d}"
        elements.append(rect)

        if node:
            label = _build_base_element(
                "text", x + 12, y + 8, w - 24, 20,
                type="text", text=node, fontSize=14, fontFamily=2,
                textAlign="left", verticalAlign="top",
                containerId=rect["id"], lineHeight=1.25,
                strokeColor=color, strokeWidth=0, roughness=0, roundness=None,
            )
            rect["boundElements"].append({"type": "text", "id": label["id"]})
            elements.append(label)

    return elements


def _generate_sequence(nodes, colors):
    """生成时序图: 顶部参与者 + 竖直生命线"""
    elements = []
    actor_gap = 200
    lifeline_h = 400
    y_top = 80
    x0 = 100

    for i, node in enumerate(nodes[:6]):  # 最多 6 个参与者
        x = x0 + i * actor_gap
        color = colors[i % len(colors)]

        # Actor box
        box = _build_base_element(
            "rectangle", x, y_top, 120, 40,
            strokeColor=color, backgroundColor=f"{color}20",
            fillStyle="solid", roughness=0, roundness={"type": 3},
        )
        box["id"] = f"seq-actor-{i:04d}"
        elements.append(box)

        if node:
            label = _build_base_element(
                "text", x + 5, y_top + 10, 110, 20,
                type="text", text=node, fontSize=12, fontFamily=2,
                textAlign="center", verticalAlign="middle",
                containerId=box["id"], lineHeight=1.25,
                strokeColor=color, strokeWidth=0, roughness=0, roundness=None,
            )
            box["boundElements"].append({"type": "text", "id": label["id"]})
            elements.append(label)

        # 生命线 (虚线)
        elements.append(_build_base_element(
            "arrow",
            x + 60, y_top + 40, 0, 0,
            points=[[0, 0], [0, lifeline_h]],
            startBinding=None, endBinding=None,
            startArrowhead=None, endArrowhead=None,
            strokeColor=COLORS["gray"], strokeStyle="dashed",
            roundness=None,
        ))

    return elements


def _generate_class_diagram(nodes, colors, vertical):
    """生成简化类图: 三栏 UML 框"""
    elements = []
    x0, y0 = 80, 80
    gap = 220
    box_w = 180
    header_h = 30
    attr_h = 60
    method_h = 60
    total_h = header_h + attr_h + method_h

    for i, node in enumerate(nodes[:8]):
        x = x0 + i * gap if not vertical else x0
        y = y0 if not vertical else y0 + i * gap
        color = colors[i % len(colors)]

        # 主框
        box = _build_base_element(
            "rectangle", x, y, box_w, total_h,
            strokeColor=color, backgroundColor="transparent",
            fillStyle="solid", roughness=0, roundness=None,
        )
        box["id"] = f"class-{i:04d}"
        elements.append(box)

        # 类名
        name_el = _build_base_element(
            "text", x + 5, y + 6, box_w - 10, header_h - 6,
            type="text", text=node, fontSize=14, fontFamily=2,
            textAlign="center", verticalAlign="middle",
            containerId=box["id"], lineHeight=1.25,
            strokeColor=color, strokeWidth=0, roughness=0, roundness=None,
        )
        box["boundElements"].append({"type": "text", "id": name_el["id"]})
        elements.append(name_el)

        # 分隔线
        elements.append(_build_base_element(
            "line",
            x, y + header_h, 0, 0,
            points=[[0, 0], [box_w, 0]],
            startBinding={"elementId": box["id"], "focus": 0.0, "gap": 0},
            endBinding={"elementId": box["id"], "focus": 0.0, "gap": 0},
            startArrowhead=None, endArrowhead=None,
            strokeColor=color, roundness=None,
        ))
        elements.append(_build_base_element(
            "line",
            x, y + header_h + attr_h, 0, 0,
            points=[[0, 0], [box_w, 0]],
            startBinding={"elementId": box["id"], "focus": 0.0, "gap": 0},
            endBinding={"elementId": box["id"], "focus": 0.0, "gap": 0},
            startArrowhead=None, endArrowhead=None,
            strokeColor=color, roundness=None,
        ))

    return elements


@mcp.tool()
def create_new_drawing(
    filepath: str,
    format_type: str = "auto",
) -> str:
    """创建新的空白 Excalidraw 绘图文件

    Args:
        filepath: 文件路径
        format_type: auto (根据扩展名) / json (.excalidraw) / obsidian (.excalidraw.md)
    """
    if format_type == "auto":
        fmt = _detect_format(filepath)
    else:
        fmt = format_type

    data = dict(EXCALIDRAW_NEW_FILE)

    if fmt == "obsidian":
        content = f"""---
excalidraw-plugin: parsed
---

# Excalidraw Data
## Drawing
```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return json.dumps({
        "success": True,
        "file": filepath,
        "format": fmt,
        "elements": 0,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def auto_layout(
    filepath: str,
    direction: str = "horizontal",
    gap: float = 160,
    start_x: float = 80,
    start_y: float = 200,
) -> str:
    """自动排列绘图中的元素 (流程图布局)

    Args:
        filepath: 绘图文件路径
        direction: horizontal/vertical
        gap: 元素间距
        start_x, start_y: 起始坐标
    """
    data, _ = _load_drawing(filepath)
    elements = [e for e in data["elements"] if not e.get("isDeleted")]

    # 分类
    shapes = []
    arrows = []
    texts = []
    for el in elements:
        t = el["type"]
        if t in ("rectangle", "ellipse", "diamond", "frame"):
            shapes.append(el)
        elif t in ("arrow", "line"):
            arrows.append(el)
        elif t == "text" and not el.get("containerId"):
            texts.append(el)

    # 排列形状
    for i, shape in enumerate(shapes):
        if direction == "horizontal":
            shape["x"] = start_x + i * gap
            shape["y"] = start_y
        else:
            shape["x"] = start_x
            shape["y"] = start_y + i * gap
        shape["updated"] = int(datetime.now().timestamp() * 1000)

    fmt = _save_drawing(filepath, data)
    return json.dumps({
        "success": True,
        "laid_out": len(shapes),
        "direction": direction,
        "gap": gap,
        "saved_as": fmt,
    }, ensure_ascii=False, indent=2)


# ============================================================
# Resources
# ============================================================

@mcp.resource("excalidraw://supported-elements")
def supported_elements() -> str:
    return json.dumps({
        "shapes": ["rectangle", "ellipse", "diamond"],
        "lines": ["arrow", "line"],
        "containers": ["frame", "magicframe"],
        "content": ["text", "image", "freedraw"],
        "colors": list(COLORS.keys()),
        "stroke_styles": STROKE_STYLES,
        "fill_styles": FILL_STYLES,
        "font_families": FONT_FAMILIES,
        "arrowhead_styles": ARROWHEAD_TYPES,
        "diagram_types": [
            "flowchart", "mindmap", "architecture",
            "sequence", "class_diagram", "generic",
        ],
        "color_schemes": ["default", "pastel", "dark", "professional"],
    }, ensure_ascii=False, indent=2)


@mcp.resource("excalidraw://color-palette")
def color_palette() -> str:
    return json.dumps(COLORS, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
