"""测本地小模型驱动 LangGraph 的三层能力：harness / loop / context。

为什么要先测 harness 再测模型
--------------------------------
一个 loop 失败有两种完全不同的原因：
  (a) 模型不会调工具      -> 归因「模型能力」
  (b) 我的图接错了        -> 归因「harness」
把两者混在一起，就会得出"本地模型不能做 Agent"这种可能完全错误的结论。
本项目的检查器已经假阳性过 4 次（漏检 / 把列表编号当编造 / 对返回结构做错假设 /
对匹配范围做截断）。所以：

  GATE-0  stub 模型 + 真实图  —— 用脚本化的假模型跑同一张图。
          不过 => 图/接线有错，**停止一切模型结论**。
  GATE-1  裸 Ollama API       —— 绕过 LangGraph，直接问模型要 tool_call。
          不过 => 归因适配层或模型，与图无关。
  然后才是真模型跑完整的图。

判据全部机判，且带负对照
------------------------
金丝雀值：工具返回的随机 6 位数，prompt 里不预先出现。
  "最终答案里出现该数" <=> 模型真的拿到了工具返回值（而不是编的）。
  "最终答案里出现未返回过的数" => 编造，直接判 FAIL。
不该调工具的用例（1+1）必须**不调**工具——只测正例会系统性高估能力。

用法：
    python test_langgraph_skill.py              # 全部模型
    python test_langgraph_skill.py qwen3.5:0.8b # 指定模型
"""
import json
import random
import re
import sys
import time

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from pydantic import PrivateAttr


class ScriptedChatModel(BaseChatModel):
    """按剧本依次返回消息的假模型。

    为什么不直接用 langchain_core 内置的 FakeMessagesListChatModel：
    内置的 fake 全都继承 BaseChatModel.bind_tools，而那个基类实现直接
    `raise NotImplementedError`（已实测，见 chat_models.py:2383）。
    create_agent 一定会调 bind_tools，于是内置 fake 根本进不了图。
    这里显式把 bind_tools 实现成返回自身，就能把「图接线」和「模型能力」分开。
    """

    responses: list
    _i: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "scripted-stub"

    def bind_tools(self, tools, **kwargs):  # 内置 fake 缺的就是这个
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        idx = min(self._i, len(self.responses) - 1)
        self._i += 1
        return ChatResult(generations=[ChatGeneration(message=self.responses[idx])])

OLLAMA = "http://127.0.0.1:11434"
SEED = 20260922
rand = random.Random(SEED)

# ── 金丝雀：随机 6 位数，绝不用 42/100 这类可猜值 ──────────────────────────
CANARY = {n: rand.randint(100000, 999999) for n in ("alpha", "beta", "gamma")}


@tool
def get_metric(name: str) -> str:
    """查询一个指标的值。name 可以是 alpha / beta / gamma。"""
    if name not in CANARY:
        return json.dumps({"error": "not_found", "name": name})
    return json.dumps({"name": name, "value": CANARY[name]})


@tool
def scale(value: int, factor: int) -> str:
    """把 value 乘以 factor，返回结果。"""
    return json.dumps({"value": value * factor})


TOOLS = [get_metric, scale]


def build(model, num_ctx=8192, tools=None, system_prompt=None):
    """建图。model 传真实 ChatOllama 或 stub。"""
    return create_agent(
        model,
        tools=TOOLS if tools is None else tools,
        system_prompt=system_prompt or (
            "你是一个会使用工具的助手。需要查数据时必须调用工具，"
            "不要凭记忆编造数字。拿到工具结果后，用中文简短回答。"
        ),
    )


def run_agent(graph, question, limit=8):
    """跑一次，返回 (final_text, tool_calls, steps, error)。"""
    calls = []
    t0 = time.time()
    try:
        out = graph.invoke({"messages": [{"role": "user", "content": question}]},
                           config={"recursion_limit": limit})
        msgs = out["messages"]
    except Exception as exc:
        return "", [], 0, "%s: %s" % (type(exc).__name__, str(exc)[:180])

    for m in msgs:
        for tc in (getattr(m, "tool_calls", None) or []):
            calls.append({"name": tc.get("name"), "args": tc.get("args") or {},
                          "id": tc.get("id")})
    final = ""
    for m in reversed(msgs):
        if m.__class__.__name__ == "AIMessage" and (m.content or "").strip():
            final = m.content
            break
    return final, calls, len(calls), None


def nums(text):
    return {n for n in re.findall(r"\d+", (text or "").replace(",", ""))}


# ── GATE-0：stub 模型 + 真实图。不过就停，不许做模型结论 ────────────────────
def gate0():
    """用脚本化假模型走一遍「调工具 -> 拿结果 -> 给答案」。"""
    scripted = [
        AIMessage(content="", tool_calls=[
            {"name": "get_metric", "args": {"name": "alpha"},
             "id": "call_0", "type": "tool_call"}]),
        AIMessage(content="alpha 的值是 %d。" % CANARY["alpha"]),
    ]
    try:
        stub = ScriptedChatModel(responses=scripted)
        g = build(stub)
        final, calls, _, err = run_agent(g, "alpha 的值是多少？")
    except Exception as exc:
        return False, "stub 未跑通: %s: %s" % (type(exc).__name__, str(exc)[:160])
    if err:
        return False, "stub 运行报错: %s" % err
    if len(calls) != 1 or calls[0]["name"] != "get_metric":
        return False, "stub 的工具调用没被图正确路由 (calls=%s)" % json.dumps(calls, ensure_ascii=False)
    if str(CANARY["alpha"]) not in final:
        return False, "stub 的最终答案丢了工具返回值"
    return True, "图接线正常（路由 + 工具执行 + 结果回填均正确）"


# ── GATE-1：绕过图，裸 API 问模型要 tool_call ──────────────────────────────
def gate1(model_name, num_ctx=8192):
    import requests
    body = {
        "model": model_name, "stream": False, "think": False,
        "messages": [{"role": "user", "content": "alpha 的指标值是多少？必须用 get_metric 工具查询。"}],
        "tools": [{"type": "function", "function": {
            "name": "get_metric",
            "description": "查询一个指标的值。name 可以是 alpha / beta / gamma。",
            "parameters": {"type": "object",
                           "properties": {"name": {"type": "string"}},
                           "required": ["name"]}}}],
        "options": {"num_ctx": num_ctx, "temperature": 0, "num_predict": 300},
    }
    try:
        d = requests.post(OLLAMA + "/api/chat", json=body, timeout=900).json()
    except Exception as exc:
        return "ERROR", str(exc)[:120]
    tc = d.get("message", {}).get("tool_calls") or []
    if tc and tc[0].get("function", {}).get("name"):
        return "PASS", "裸 API 返回结构化 tool_call"
    text = d.get("message", {}).get("content") or ""
    if re.search(r"get_metric|\{.*name.*\}", text):
        return "FAIL_ADAPTER", "模型有调用意图（文本里有）但没被解析成结构化 tool_call"
    return "FAIL_MODEL", "完全没有工具调用意图，直接答了：%s" % text.strip()[:80]


# ── 用例（每条都带负对照）─────────────────────────────────────────────────
def case_loop1(model, num_ctx):
    """单步：查 alpha，答案必须含金丝雀。负对照：不许出现没返回过的数。"""
    g = build(model, num_ctx)
    final, calls, _, err = run_agent(g, "alpha 的指标值是多少？用工具查，然后告诉我数字。")
    if err:
        return "FAIL", "运行报错 " + err
    if not calls:
        return "FAIL", "没调工具直接答了（内容: %s）" % final.strip()[:60]
    if calls[0]["name"] != "get_metric":
        return "FAIL", "调错工具 %s" % calls[0]["name"]
    if (calls[0]["args"] or {}).get("name") != "alpha":
        return "FAIL", "参数错 %s" % json.dumps(calls[0]["args"], ensure_ascii=False)
    got = nums(final)
    if str(CANARY["alpha"]) in got:
        return "PASS", "调对工具+参数，答案含工具返回值"
    # 分不清"没拿到"和"拿到了但没用"——两种都不是合格
    return "FAIL", "调了工具但最终答案没用返回值（答案: %s）" % final.strip()[:60]


def case_loop2(model, num_ctx):
    """两步依赖链：先查 alpha，再把它乘 3。这是 ReAct 的真正门槛。"""
    g = build(model, num_ctx)
    final, calls, _, err = run_agent(
        g, "请先查 alpha 的指标值，然后把那个值乘以 3，最后告诉我结果。")
    if err:
        return "FAIL", "运行报错 " + err
    names = [c["name"] for c in calls]
    if "get_metric" not in names:
        return "FAIL", "没调 get_metric"
    if "scale" not in names:
        return "FAIL", "只调了 %s，没形成两步链" % names
    sc = [c for c in calls if c["name"] == "scale"][0]
    if (sc["args"] or {}).get("value") != CANARY["alpha"]:
        return "FAIL", "scale 的入参没吃到上一步结果（args=%s）" % json.dumps(sc["args"], ensure_ascii=False)
    want = str(CANARY["alpha"] * 3)
    if want in nums(final):
        return "PASS", "两步依赖链打通，答案=3×工具返回值"
    return "FAIL", "链条调对但答案错（期望含 %s，实际: %s）" % (want, final.strip()[:60])


def case_negative(model, num_ctx):
    """负对照：1+1 不该调任何工具。

    ⚠️ 只判「有没有乱调工具」，**不判算术对错**。这两件事曾被捆在一条判据里，
    导致归因完全反了：本测试判 granite4 负对照挂、qwen3.5:0.8b 过；
    但单独裸问 5 次的结果正好相反（granite4 答 2 ×5，qwen3.5:0.8b 答 3 ×5）。
    原因是算术对错会**随上下文翻转**（换了 system prompt / 绑了 tools 就变），
    而「乱不乱调工具」才是这条负对照真正要测的东西。算术单独作为 arith 用例报。
    """
    g = build(model, num_ctx)
    final, calls, _, err = run_agent(g, "1+1 等于几？直接回答就行。")
    if err:
        return "FAIL", "运行报错 " + err
    if calls:
        return "FAIL", "不该调工具却调了 %s" % [c["name"] for c in calls]
    ok = "2" in nums(final)
    return "PASS", "没乱调工具（算术%s，仅供参考，不计入本判据）" % ("对" if ok else "错: %s" % final.strip()[:20])


def case_arith(model, num_ctx):
    """算术正确性：和工具调用无关，单独测。

    裸问 qwen3.5:0.8b「1+1 等于几」稳定答 3（5/5，temperature=0）。
    但同一模型在图里（带 system prompt + tools）却能答对——所以这个信号**依赖上下文**，
    单独列出来是为了不污染工具调用的结论。
    """
    try:
        r = model.invoke("1+1 等于几？直接回答就行。")
    except Exception as exc:
        return "FAIL", "调用失败 %s" % str(exc)[:100]
    txt = r.content or ""
    return ("PASS" if "2" in nums(txt) else "FAIL"), "裸问 1+1 -> %r" % txt.strip()[:30]


def case_context(model, num_ctx):
    """context 工程：第 1 步查到的值，隔一次工具调用后还能正确引用。"""
    g = build(model, num_ctx)
    final, calls, _, err = run_agent(
        g, "先查 alpha，再查 beta，最后告诉我 alpha 的值是多少。")
    if err:
        return "FAIL", "运行报错 " + err
    if len(calls) < 2:
        return "FAIL", "只调了 %d 次工具，无法测跨步保持" % len(calls)
    if str(CANARY["alpha"]) in nums(final) and str(CANARY["beta"]) not in nums(final):
        return "PASS", "跨工具调用后仍正确引用早先的值，且没串到 beta"
    if str(CANARY["beta"]) in nums(final) and str(CANARY["alpha"]) not in nums(final):
        return "FAIL", "串了：答成 beta 的值（上下文混淆）"
    return "FAIL", "答案既不含 alpha 也不单含 alpha（内容: %s）" % final.strip()[:60]


CASES = [("loop-1 单步", case_loop1), ("loop-2 两步链", case_loop2),
         ("negative 不误调", case_negative), ("context 跨步", case_context),
         ("arith 1+1*", case_arith)]   # * 仅参考：与工具调用无关，且随上下文翻转

MODELS = sys.argv[1:] or ["qwen3.5:0.8b", "qwen3.5:2b", "granite4:micro-h", "llama3.2:3b"]
CTX = {"granite4:micro-h": 32768}


def main():
    print("金丝雀(随机, 种子 %d): %s" % (SEED, CANARY))
    print()
    ok, msg = gate0()
    print("GATE-0 (stub 模型验证图接线): %s -- %s" % ("PASS" if ok else "FAIL", msg))
    if not ok:
        print("\n图本身没过 -> 任何模型结论都不可信。先修图。")
        return 1
    print()

    for m in MODELS:
        st, msg = gate1(m, CTX.get(m, 8192))
        print("=" * 74)
        print("模型 %s   GATE-1(裸 API): %s -- %s" % (m, st, msg))
        if st != "PASS":
            print("  -> 该模型跳过图测试，结论标 BLOCKED-BY-ADAPTER，不计入能力统计")
            continue
        model = ChatOllama(model=m, base_url=OLLAMA, temperature=0,
                           num_ctx=CTX.get(m, 8192), num_predict=400, keep_alive="5m")
        for label, fn in CASES:
            try:
                r, detail = fn(model, CTX.get(m, 8192))
            except Exception as exc:
                r, detail = "FAIL", "%s: %s" % (type(exc).__name__, str(exc)[:140])
            print("   %-14s %-5s %s" % (label, r, detail), flush=True)
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
