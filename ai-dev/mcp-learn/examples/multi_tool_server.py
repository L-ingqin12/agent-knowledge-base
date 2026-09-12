"""多工具 MCP 服务器 — 展示 Tools/Resources/Prompts 的完整用法"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Multi-Tool Server")

# ========== 数据存储 (模拟) ==========
NOTES_FILE = Path("/tmp/mcp_notes.json")

def _load_notes() -> dict:
    if NOTES_FILE.exists():
        return json.loads(NOTES_FILE.read_text())
    return {}

def _save_notes(notes: dict):
    NOTES_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2))

# ========== Tools ==========
class WeatherInput(BaseModel):
    city: str = Field(description="城市名称, 如 '北京'")
    units: str = Field(default="celsius", description="温度单位: celsius 或 fahrenheit")

@mcp.tool()
async def get_weather(params: WeatherInput) -> str:
    """获取指定城市的天气信息 (模拟)"""
    # 实际项目中替换为真实 API 调用
    weather_data = {
        "北京": {"celsius": "22°C, 晴", "fahrenheit": "72°F, 晴"},
        "上海": {"celsius": "25°C, 多云", "fahrenheit": "77°F, 多云"},
    }
    data = weather_data.get(params.city, {})
    temp = data.get(params.units, "暂无数据")
    return f"{params.city}: {temp}, 更新时间: {datetime.now().isoformat()}"

class NoteInput(BaseModel):
    title: str = Field(description="笔记标题")
    content: str = Field(description="笔记内容")
    tags: list[str] = Field(default_factory=list, description="标签列表")

@mcp.tool()
def create_note(params: NoteInput) -> str:
    """创建一条新笔记"""
    notes = _load_notes()
    note_id = str(len(notes) + 1)
    notes[note_id] = {
        "title": params.title,
        "content": params.content,
        "tags": params.tags,
        "created_at": datetime.now().isoformat(),
    }
    _save_notes(notes)
    return f"笔记已创建, ID: {note_id}"

@mcp.tool()
def search_notes(keyword: str) -> str:
    """搜索包含关键词的笔记"""
    notes = _load_notes()
    results = []
    for note_id, note in notes.items():
        if keyword.lower() in note["content"].lower() or keyword.lower() in note["title"].lower():
            results.append(f"[{note_id}] {note['title']}: {note['content'][:50]}...")
    if not results:
        return "未找到匹配的笔记"
    return "\n".join(results)

@mcp.tool()
def calculate(expression: str) -> str:
    """安全的数学表达式计算 (仅支持基本运算)"""
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expression):
        raise ValueError(f"表达式包含不允许的字符。仅允许: {''.join(sorted(allowed))}")
    try:
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        raise ValueError(f"计算错误: {e}")

@mcp.tool()
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前时间"""
    return f"当前时间: {datetime.now().isoformat()}"

# ========== Resources ==========
@mcp.resource("notes://all")
def get_all_notes() -> str:
    """获取所有笔记"""
    notes = _load_notes()
    return json.dumps(notes, ensure_ascii=False, indent=2)

@mcp.resource("notes://{note_id}")
def get_note(note_id: str) -> str:
    """获取指定 ID 的笔记"""
    notes = _load_notes()
    note = notes.get(note_id)
    if not note:
        return f"笔记 {note_id} 不存在"
    return json.dumps(note, ensure_ascii=False, indent=2)

@mcp.resource("health://status")
def health_check() -> str:
    """服务器健康状态"""
    return json.dumps({
        "status": "healthy",
        "uptime": "running",
        "timestamp": datetime.now().isoformat(),
    })

# ========== Prompts ==========
@mcp.prompt()
def summarize_notes() -> str:
    """总结所有笔记的内容"""
    notes = _load_notes()
    notes_text = json.dumps(notes, ensure_ascii=False)
    return f"请用一段话总结以下笔记的主要内容:\n\n{notes_text}"

@mcp.prompt()
def debug_error(error: str, code: str, language: str = "Python") -> str:
    """调试代码错误"""
    return f"""请帮我调试以下 {language} 代码中的错误:

错误信息:
{error}

代码:
{code}

请提供:
1. 错误原因分析
2. 修复方案
3. 修复后的完整代码"""

# ========== 启动 ==========
if __name__ == "__main__":
    print("Starting Multi-Tool MCP Server...")
    print(f"Notes file: {NOTES_FILE}")
    mcp.run(transport="stdio")
