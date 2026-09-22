"""测「学 AI Agent 开发」的核心能力：能否产出合法的工具调用。

这是本地模型能不能当 Agent 开发练习靶子的分水岭——
学 Agent 开发要反复写 tool schema、调 tool call 解析、看模型怎么选工具，
若模型连合法的 tool call 都产不出，练的就是"跟模型较劲"而不是"学 Agent"。

判据（逐项可判定）：
  1. 是否调用工具（而非自己瞎编答案）
  2. function.name 是否非空且等于 schema 里的名字
  3. arguments 是否是可解析的 JSON
  4. 该带参数时有没有带
"""
import json
import time

import requests

API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的当前天气",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名"}},
            "required": ["city"],
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "search_docs",
        "description": "在项目文档里检索关键词",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}]

CASES = [
    ("该调 get_weather", "杭州今天天气怎么样？", "get_weather", "city"),
    ("该调 search_docs", "帮我查一下文档里关于超时的说明", "search_docs", "query"),
    ("不该调工具", "1+1 等于几？", None, None),
]

MODELS = [("granite4:micro-h", 32768), ("qwen2.5-coder:3b", 16384),
          ("phi4-mini:latest", 8192), ("llama3.2:3b", 8192),
          ("qwen3.5:2b", 16384), ("qwen3.5:0.8b", 16384)]

print("%-20s %-16s %-12s %-10s %s" % ("模型", "用例", "工具名", "参数可解析", "判定"))
print("-" * 74)

for model, ctx in MODELS:
    ok_all = 0
    for label, q, want, argkey in CASES:
        body = {"model": model, "stream": False, "think": False,
                "messages": [{"role": "user", "content": q}],
                "tools": TOOLS,
                "options": {"num_predict": 300, "num_ctx": ctx, "temperature": 0}}
        try:
            d = requests.post(API + "/chat", headers=H,
                              data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                              timeout=1200).json()
        except Exception as exc:
            print("%-20s %-16s 失败" % (model, label)); continue
        m = d.get("message", {})
        tc = m.get("tool_calls") or []
        content = (m.get("content") or "").strip()

        if want is None:  # 不该调工具
            good = not tc and bool(content)
            print("%-20s %-16s %-12s %-10s %s" %
                  (model, label, "(未调用)" if not tc else "误调用",
                   "-", "OK" if good else "x 调了不该调的"))
            ok_all += good
            continue

        if not tc:
            print("%-20s %-16s %-12s %-10s %s" %
                  (model, label, "(未调用)", "-", "x 没调工具，直接答了"))
            continue
        fn = (tc[0].get("function") or {})
        name = fn.get("name") or ""
        try:
            args = json.loads(fn.get("arguments") or "{}")
            parsable = True
        except Exception:
            args, parsable = {}, False
        good = (name == want) and parsable and (argkey in args)
        print("%-20s %-16s %-12s %-10s %s" %
              (model, label, name or "(空)", "是" if parsable else "否",
               "OK" if good else "x " + ("名字错" if name != want else ("参数缺" if not parsable else "无参数"))))
        ok_all += good
    print("%-20s 合计 %d/%d" % ("", ok_all, len(CASES)))
    print()
