"""lg-lab —— LangChain / LangGraph 手动实践台（本地模型，离线可跑）。

和 bin/agent-lab.py 的区别：
  agent-lab 是「裸 API + 手写 ReAct 循环」——你亲手实现循环，看清每一步。
  lg-lab    是「框架层」——用 LangGraph 把循环交给框架，你观察图和状态怎么走。
  两个对照着看，才知道框架替你做了什么、又坑了你什么。

课程设计（由浅入深，每节都能直接跑）：
  1 最小图        START -> 单节点 -> END          —— 理解节点/状态/编译
  2 条件边        classify -> 两条分支            —— 理解路由
  3 ReAct agent   create_agent + 工具             —— 理解框架替你实现的循环
  4 状态累加      Annotated[list, add_messages]   —— 理解 reducer，最容易踩的坑
  5 多轮记忆      checkpointer + thread_id        —— 理解会话隔离
  6 自由对话      对着 ReAct agent 连续提问        —— 手动实践

用法：
    python lg-lab.py               # 菜单
    python lg-lab.py -m qwen3.5:2b # 换模型
"""
import argparse
import json
import sys
from typing import Annotated, TypedDict

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

OLLAMA = "http://127.0.0.1:11434"


def mkmodel(name):
    """统一的模型构造。num_ctx 是本机调优过的关键参数，别用默认值。"""
    ctx = 32768 if name.startswith("granite4") else 16384
    return ChatOllama(model=name, base_url=OLLAMA, temperature=0,
                      num_ctx=ctx, num_predict=400, keep_alive="5m")


# ── 课程 1：最小图 ────────────────────────────────────────────────────────
def lesson1(model):
    print("\n【课程 1】最小图：START -> 一个节点 -> END")
    print("要看的是：状态怎么在节点间传递、invoke 的输入输出长什么样。\n")

    class S(TypedDict):
        text: str          # 图的状态：就是一个普通 dict 的类型声明

    def node(state: S):
        # 节点就是普通函数：收 state，返回「要合并进 state 的字段」
        print("   节点收到 state =", state)
        reply = model.invoke("用一句话解释什么是 LangGraph。").content
        return {"text": reply}

    g = StateGraph(S)
    g.add_node("only", node)
    g.add_edge(START, "only")
    g.add_edge("only", END)
    app = g.compile()      # 编译 = 校验图 + 生成可执行对象

    out = app.invoke({"text": ""})
    print("\n   最终 state =", json.dumps(out, ensure_ascii=False)[:400])


# ── 课程 2：条件边 ────────────────────────────────────────────────────────
def lesson2(model):
    print("\n【课程 2】条件边：按 state 走不同分支")
    print("要看的是：路由函数只读 state、只返回分支名，不做事。\n")

    class S(TypedDict):
        q: str
        kind: str
        answer: str

    def classify(state: S):
        # 小模型做分类很不稳，所以这里刻意把 prompt 收得很紧、只要一个词
        r = model.invoke(
            "判断下面这句话是「数学」还是「闲聊」，只回答两个字，不要解释：\n" + state["q"])
        k = "数学" if "数学" in r.content else "闲聊"
        print("   分类节点判定 ->", k, " (原始输出: %r)" % r.content.strip()[:40])
        return {"kind": k}

    def math_node(state: S):
        return {"answer": "你问的是数学问题，我来算。" + state["q"]}

    def chat_node(state: S):
        return {"answer": "你问的是闲聊，我陪你聊。" + state["q"]}

    def route(state: S):
        return state["kind"]      # 返回值必须是节点名

    g = StateGraph(S)
    g.add_node("classify", classify)
    g.add_node("math", math_node)
    g.add_node("chat", chat_node)
    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route, {"数学": "math", "闲聊": "chat"})
    g.add_edge("math", END)
    g.add_edge("chat", END)
    app = g.compile()

    for q in ("3 的平方是多少", "今天心情不错"):
        print("   输入:", q)
        print("   输出:", app.invoke({"q": q, "kind": "", "answer": ""})["answer"])


# ── 课程 3：ReAct agent ───────────────────────────────────────────────────
@tool
def get_time() -> str:
    """获取当前的系统时间。"""
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")


@tool
def word_count(text: str) -> str:
    """统计一段文本有多少个字符。"""
    return "%d 个字符" % len(text)


def lesson3(model):
    print("\n【课程 3】ReAct agent：框架替你实现的工具循环")
    print("要看的是：你不再手写 while 循环，create_agent 把「调工具→回填→再问」包好了。")
    print("一行代码背后，就是我们 agent-lab 里手写的那种循环。\n")

    app = create_agent(model, tools=[get_time, word_count],
                       system_prompt="你是助手。需要时间或字数时必须调用工具，不要自己编。")
    out = app.invoke({"messages": [{"role": "user", "content": "现在几点？顺便帮我数一下「你好世界」有几个字。"}]})

    for m in out["messages"]:
        kind = m.__class__.__name__
        tcs = getattr(m, "tool_calls", None) or []
        if tcs:
            for tc in tcs:
                print("   [%s] 调工具 %s  参数 %s" % (kind, tc.get("name"),
                       json.dumps(tc.get("args"), ensure_ascii=False)))
        elif (m.content or "").strip():
            print("   [%s] %s" % (kind, m.content.strip()[:200]))


# ── 课程 4：状态累加（最容易踩的坑）────────────────────────────────────────
def lesson4(model):
    print("\n【课程 4】reducer：为什么消息要写成 Annotated[list, add_messages]")
    print("要看的是：不加 reducer 时，后一个节点的返回值会**覆盖**前面所有消息——")
    print("         对话历史凭空消失，而模型看起来只是「失忆」。这是最常见的坑。\n")

    class Bad(TypedDict):
        messages: list          # 没有 reducer

    class Good(TypedDict):
        messages: Annotated[list, add_messages]   # 有 reducer：追加而不是覆盖

    def n1(s):
        return {"messages": [HumanMessage("第一句")]}

    def n2(s):
        return {"messages": [AIMessage("第二句")]}

    for label, schema in (("无 reducer", Bad), ("有 add_messages", Good)):
        g = StateGraph(schema)
        g.add_node("n1", n1)
        g.add_node("n2", n2)
        g.add_edge(START, "n1")
        g.add_edge("n1", "n2")
        g.add_edge("n2", END)
        out = g.compile().invoke({"messages": []})
        print("   %-16s 结束时 messages 共 %d 条: %s" % (
            label, len(out["messages"]),
            [m.content for m in out["messages"]]))


# ── 课程 5：多轮记忆 ──────────────────────────────────────────────────────
def lesson5(model):
    print("\n【课程 5】checkpointer：多轮记忆与会话隔离")
    print("要看的是：同一个 thread_id 记得住，换一个 thread_id 立刻失忆。")
    print("         这就是「记忆」在框架里的真实实现——不是模型记住了，是状态被存了。\n")

    app = create_agent(model, tools=[], checkpointer=InMemorySaver(),
                       system_prompt="你是助手，回答尽量简短。")
    a = {"configurable": {"thread_id": "会话A"}}
    b = {"configurable": {"thread_id": "会话B"}}

    def say(cfg, text):
        out = app.invoke({"messages": [{"role": "user", "content": text}]}, config=cfg)
        return out["messages"][-1].content.strip()[:120]

    print("   A 说: 我叫小明")
    say(a, "我叫小明，请记住。")
    print("   B 问: 我叫什么？  ->", say(b, "我叫什么名字？"))
    print("   A 问: 我叫什么？  ->", say(a, "我叫什么名字？"))
    print("\n   注意：本地小模型即便状态里真有名字，也可能答错——")
    print("   这时要区分是「状态没存」还是「模型没用」，看上面的 messages 长度即可。")


# ── 课程 6：自由对话 ──────────────────────────────────────────────────────
def lesson6(model):
    print("\n【课程 6】自由实践：对着 ReAct agent 连续提问")
    print("输入 /reset 重开会话，/quit 退出。\n")
    app = create_agent(model, tools=[get_time, word_count],
                       system_prompt="你是助手。需要时间或字数时调用工具。",
                       checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "lab"}}
    turn = 0
    while True:
        try:
            q = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not q:
            continue
        if q == "/quit":
            return
        if q == "/reset":
            turn += 1
            cfg = {"configurable": {"thread_id": "lab-%d" % turn}}   # 换个 thread 就是全新会话
            print("  已重开会话")
            continue
        out = app.invoke({"messages": [{"role": "user", "content": q}]}, config=cfg)
        for m in out["messages"][-4:]:
            for tc in (getattr(m, "tool_calls", None) or []):
                print("   [工具] %s(%s)" % (tc.get("name"),
                      json.dumps(tc.get("args"), ensure_ascii=False)))
        print("模型>", out["messages"][-1].content.strip()[:500])


LESSONS = [("最小图（节点/状态/编译）", lesson1),
           ("条件边（路由）", lesson2),
           ("ReAct agent（框架替你实现的循环）", lesson3),
           ("reducer（消息为什么会被覆盖）", lesson4),
           ("checkpointer（多轮记忆与会话隔离）", lesson5),
           ("自由实践（连续提问）", lesson6)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--model", default="qwen3.5:2b")
    args = ap.parse_args()
    import requests
    try:
        requests.get(OLLAMA + "/api/version", timeout=5)
    except Exception:
        print("连不上 Ollama。先跑：  llm-start")
        return 1

    model = mkmodel(args.model)
    print("=" * 70)
    print(" LangChain/LangGraph 实践台 | 模型: %s" % args.model)
    print("=" * 70)
    while True:
        for i, (name, _) in enumerate(LESSONS, 1):
            print("  %d) %s" % (i, name))
        print("  q) 退出")
        try:
            c = input("\n选一节 > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if c in ("q", "quit", ""):
            break
        if c.isdigit() and 1 <= int(c) <= len(LESSONS):
            try:
                LESSONS[int(c) - 1][1](model)
            except Exception as exc:
                print("  这一节跑挂了: %s: %s" % (type(exc).__name__, str(exc)[:300]))
            print()
    print("再见。记得 llm-stop 释放显存。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
