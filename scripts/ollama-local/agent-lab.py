"""agent-lab —— 本地 Agent 开发练习台（ReAct 循环可视化）。

为什么需要它：
  学 Agent 开发光看文档没用，得反复做「写 tool schema → 看模型怎么调 → 调解析逻辑」。
  这个练习台把每一轮完整暴露出来：模型的原始 tool_call、参数、你返回的结果、它怎么接着做。

用法：
    python agent-lab.py            # 用默认工具集与默认模型
    python agent-lab.py -m qwen3.5:2b
交互（在提示符下输入）：
    /tools      查看当前工具 schema（这就是你要学着写的东西）
    /model X    换模型
    /reset      清空对话
    /raw on|off 是否打印模型原始返回
    /quit       退出
"""
import argparse
import json
import sys
import time
import traceback

import requests

API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}

# ── 示例工具集：这几个故意设计得简单，方便你看清「模型怎么选、参数怎么给」 ──
TOOLS = [
    {"type": "function", "function": {
        "name": "get_time",
        "description": "获取当前系统时间",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "calc",
        "description": "计算一个数学表达式，例如 (3+5)*2",
        "parameters": {"type": "object",
                       "properties": {"expr": {"type": "string", "description": "要计算的表达式"}},
                       "required": ["expr"]}}},
    {"type": "function", "function": {
        "name": "count_text",
        "description": "统计一段文本的字符数",
        "parameters": {"type": "object",
                       "properties": {"text": {"type": "string", "description": "待统计文本"}},
                       "required": ["text"]}}},
]


def _impl(name, args):
    """工具的本地实现——练习台里写死，真实项目里换成你的业务逻辑。"""
    if name == "get_time":
        return time.strftime("%Y-%m-%d %H:%M:%S")
    if name == "calc":
        expr = args.get("expr", "")
        if not isinstance(expr, str) or any(c not in "0123456789+-*/(). %" for c in expr):
            return "错误：表达式含不允许的字符"
        try:
            return str(eval(expr, {"__builtins__": {}}, {}))
        except Exception as exc:
            return "计算失败：%s" % exc
    if name == "count_text":
        return "%d 个字符" % len(args.get("text", ""))
    return "未知工具：%s" % name


def _norm_args(a):
    """Ollama 的 arguments 可能是 dict（已解析）也可能是 JSON 字符串——两种都要吃。
    （血泪教训：只按字符串处理会把全部模型的合法调用误判成「参数缺失」）"""
    if isinstance(a, dict):
        return a
    if isinstance(a, str):
        try:
            return json.loads(a)
        except Exception:
            return {"_raw": a}
    return {}


def chat(model, messages, show_raw):
    body = {"model": model, "messages": messages, "stream": False,
            "think": False, "tools": TOOLS,
            "options": {"num_ctx": 16384, "temperature": 0.7, "num_predict": 1024}}
    t0 = time.time()
    d = requests.post(API + "/chat", headers=H,
                      data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                      timeout=1800).json()
    dt = time.time() - t0
    if show_raw:
        print("\n  [原始返回] %s" % json.dumps(d.get("message", {}), ensure_ascii=False)[:500])
    ec, ed = d.get("eval_count", 0), d.get("eval_duration", 1) or 1
    print("  [%.1fs · %.1f tok/s]" % (dt, ec / (ed / 1e9) if ed else 0))
    return d.get("message", {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--model", default="qwen3.5:0.8b",
                    help="默认 qwen3.5:0.8b（实测工具调用 3/3 且最快）")
    args = ap.parse_args()

    model, show_raw, messages = args.model, False, []

    try:
        requests.get(API.replace("/api", "") + "/api/version", timeout=5)
    except Exception:
        print("连不上 Ollama。先跑：  llm-start")
        return 1

    print("=" * 66)
    print(" Agent 练习台  |  模型: %s" % model)
    print(" 默认工具: %s" % ", ".join(t["function"]["name"] for t in TOOLS))
    print(" 命令: /tools /model X /reset /raw on|off /quit")
    print("=" * 66)

    while True:
        try:
            q = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not q:
            continue
        if q in ("/quit", "/exit"):
            break
        if q == "/tools":
            print(json.dumps(TOOLS, ensure_ascii=False, indent=2))
            continue
        if q == "/reset":
            messages = []
            print("  已清空")
            continue
        if q.startswith("/raw"):
            show_raw = q.endswith("on")
            print("  raw = %s" % show_raw)
            continue
        if q.startswith("/model"):
            model = q.split(None, 1)[1].strip() if " " in q else model
            print("  模型 -> %s" % model)
            continue

        messages.append({"role": "user", "content": q})

        # ── ReAct 循环：最多 5 轮工具调用，防止小模型陷入死循环 ──
        for step in range(5):
            try:
                msg = chat(model, messages, show_raw)
            except Exception as exc:
                print("  请求失败: %s" % exc)
                traceback.print_exc()
                break
            messages.append(msg)

            calls = msg.get("tool_calls") or []
            if not calls:
                print("\n模型> %s" % (msg.get("content") or "(空)"))
                break

            for c in calls:
                fn = c.get("function") or {}
                name = fn.get("name") or ""
                a = _norm_args(fn.get("arguments"))
                print("\n  ┌─ 第 %d 轮：模型请求调用工具" % (step + 1))
                print("  │  工具名: %s" % (name or "(空)"))
                print("  │  参数  : %s" % json.dumps(a, ensure_ascii=False))
                result = _impl(name, a)
                print("  └─ 你返回: %s" % result)
                messages.append({"role": "tool", "content": str(result)})
        else:
            print("\n  (已达 5 轮上限，停止——小模型常见现象，正是你要观察的)")

    print("再见。记得 llm-stop 释放显存。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
