"""llm —— 本机 Ollama 的一行式推理入口。

定位：把「小、碎、重复」的推理任务从远端模型卸载到本机，节省远端 token 与长任务成本。
设计取舍：一切以**可用性 / 速率 / 便捷**为先 ——
  * 默认走**原生端点**（只有它能关思考，实测思考开局能吃掉 40 倍 token）
  * 默认**关思考**，按用途自动选最合适的模型
  * 默认上下文按用途给足，避免「窗口不够导致预算被钳到 1」

用法:
    llm "用一句话解释什么是向量数据库"
    llm -t coder "写一个 python 快排"
    llm -t smart --think "这题怎么解：..."
    llm -f notes.md "总结要点"
    git diff | llm "写一条 commit message"
    llm -t vision -i shot.png "这个报错是什么"
    llm --list

用途别名（-t）:
    fast   qwen3.5:0.8b   最快，分类/抽取/改写等简单任务
    chat   granite4:micro-h  通用对话，非思考，最稳
    smart  qwen3.5:2b     需要一点推理时
    coder  qwen2.5-coder:3b  代码
    moe    granite4:tiny-h   7B-A1B，CPU 跑，慢但更强
    vision qwen3-vl:2b    看图（注意它会思考）
"""
from __future__ import annotations

import argparse
from builtins import print as builtins_print
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOST = "http://127.0.0.1:11434"

# 用途 -> (模型, 默认上下文, 默认开思考?, 能力标签)
# 标签来自本机实测（见知识库 ai-dev/本地模型能力矩阵与任务路由），不是抄 benchmark。
ROLES = {
    "gen":    ("qwen3.5:0.8b",     16384, False,
               "长文草稿/扩写最强：3000tok 重复率仅1.2%、67tok/s；但长上下文检索 0/3"),
    "fast":   ("qwen3.5:0.8b",     16384, False, "同 gen，最快"),
    "chat":   ("granite4:micro-h", 32768, False,
               "结构化输出/工具调用/FIM 有厂商背书；分类抽取摘要"),
    "retrie": ("qwen3.5:2b",       16384, False,
               "受控实验里捞针 3/3 的两个之一（另一个是 coder）"),
    "coder":  ("qwen2.5-coder:3b", 16384, False,
               "代码 + 长上下文检索 3/3"),
    "smart":  ("qwen3.5:2b",       16384, False,
               "比 0.8B 通用更强；且是捞针 3/3 的两个之一"),
    "en":     ("llama3.2:3b",       8192, False,
               "多语言对话/改写；已烤 repeat_penalty=1.2 抑制其复读；但 8K 捞针 0/3、知识 4/8"),
    "math":   ("phi4-mini:latest",  8192, False,
               "数学/逻辑推理：官方 GSM8K 88.6 / MATH 64.0；本角色会传 temperature=0"),
    "moe":    ("granite4:tiny-h",   8192, False, "7B-A1B MoE，CPU 跑，慢"),
    "vision": ("qwen3-vl:2b",       8192, True,
               "图像/GUI/OCR；纯文本知识最弱（0/8），别拿它答题"),
}
DEFAULT_ROLE = "fast"

# 「关思考」要分两种模型处理（2026-09-19 实测，组合搞错会反噬）：
#
#  A. qwen3.5 这类 —— 原生端点传 think:false 就够。
#     ⚠️ 若同时再塞 prefill，模型会把字面量 "<think>" 当正文吐出来（实测翻车）。
#
#  B. qwen3-vl —— 它的 GGUF 模板把 "<think>" 【无条件】写死，think:false 压不住
#     （实测 think:false 仍产 577 字符思考）。必须 think:true + 末尾预填一个
#     【已闭合的空 think 块】，模型会直接进正文（实测 thinking 归零、18.7s→1.3s）。
NEEDS_PREFILL = ("qwen3-vl",)
PREFILL = {"role": "assistant", "content": "<think>\n\n</think>\n\n"}

# C. gpt-oss —— 它是「推理模型」，think 只认 low/medium/high 字符串，
#    传 true/false 会被【忽略】（实测 think:false 仍产 129 字符思考）。
#    未传时模板默认注入 "Reasoning: medium"。实测 think:"low" 把思考压到 1/6、
#    速度 4.7 → 7.2 tok/s（+53%）。所以默认给它 low。
LEVEL_THINK_MODELS = {"gpt-oss": "low"}


def _post(path: str, payload: dict, timeout: float):
    req = urllib.request.Request(
        HOST + path, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(path: str, timeout: float = 20):
    with urllib.request.urlopen(HOST + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _out(s: str = ""):
    """Windows 控制台多为 GBK；退化成安全字符，避免 UnicodeEncodeError。"""
    try:
        builtins_print(s)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        _out(s.encode(enc, errors="replace").decode(enc, errors="replace"))


def alive() -> bool:
    try:
        _post("/api/show", {"model": "qwen3.5:0.8b"}, 10)
        return True
    except Exception:
        pass
    try:
        urllib.request.urlopen(HOST + "/api/version", timeout=8).read()
        return True
    except Exception as exc:
        sys.stderr.write("[llm] 连不上本机 Ollama (%s)：%s\n" % (HOST, exc))
        sys.stderr.write("[llm] 启动：\"%%LOCALAPPDATA%%\\Programs\\Ollama\\ollama app.exe\"\n")
        return False


def model_available(name: str) -> bool:
    """注意 /api/tags 是 GET 端点。"""
    try:
        d = _get("/api/tags")
        return any(m["name"] == name for m in d.get("models", []))
    except Exception:
        return False


def build_parser():
    p = argparse.ArgumentParser(
        prog="llm", add_help=False, description="本机 Ollama 一行式推理入口")
    p.add_argument("prompt", nargs="*", help="提示词；省略则读 stdin")
    p.add_argument("-t", "--type", dest="role", default=DEFAULT_ROLE,
                   choices=sorted(ROLES), help="用途别名（默认 fast）")
    p.add_argument("-m", "--model", help="直接指定模型（覆盖 -t）")
    p.add_argument("-c", "--ctx", type=int, help="上下文长度（默认按用途）")
    p.add_argument("-n", "--num-predict", type=int, default=1024, help="最多生成多少 token")
    p.add_argument("--think", action="store_true", help="开启思考（默认关）")
    p.add_argument("--no-think", action="store_true", help="强制关思考")
    p.add_argument("-f", "--file", action="append", default=[],
                   help="把文件内容附在提示词后（可多次）")
    p.add_argument("-i", "--image", action="append", default=[], help="附图片（视觉）")
    p.add_argument("-s", "--system", help="系统提示词")
    p.add_argument("--json", action="store_true", help="额外输出一行 JSON 统计")
    p.add_argument("-q", "--quiet", action="store_true", help="只输出正文")
    p.add_argument("--list", action="store_true", help="列出用途别名与模型")
    p.add_argument("-h", "--help", action="store_true")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.help:
        _out(__doc__)
        return 0
    if args.list:
        _out("用途     模型                 上下文   思考   说明")
        _out("-" * 68)
        for k, (m, c, th, tag) in ROLES.items():
            ok = "✅" if model_available(m) else "❌未装"
            # 思考列要区分三种：真开 / 真关 / 「靠 prefill 补丁关」
            if any(m.startswith(t) for t in NEEDS_PREFILL):
                mark = "补丁"
            elif any(m.startswith(t) for t in LEVEL_THINK_MODELS):
                mark = "低档"
            else:
                mark = "开" if th else "关"
            _out("%-8s %-20s %-8d %-6s %-8s %s" %
                  (k, m, c, mark, ok, tag))
        _out("")
        _out("思考列：关=真关 / 补丁=模型模板写死思考，靠预填空think块绕过 / 低档=gpt-oss 用 think=low")
        _out("选中建议：长文草稿→gen  长文检索/代码→retrie  工具调用/抽取→chat  看图→vision")
        return 0

    if not alive():
        return 2

    role = args.role
    model, ctx, think, _tag = ROLES[role]
    if args.model:
        model = args.model
    if args.ctx:
        ctx = args.ctx
    if args.think:
        think = True
    if args.no_think:
        think = False

    if not model_available(model):
        sys.stderr.write("[llm] 模型 %s 不在本机，试试 `llm --list`\n" % model)
        return 3

    # 组装提示词：命令行 + stdin【都要】。
    # 注意不能写成「有提示词就不读 stdin」——那样 `git diff | llm "写个 commit"` 这种
    # 核心用法会静默丢掉管道内容（实测过：模型反过来问用户"请提供原文"）。
    parts = []
    text = " ".join(args.prompt).strip()
    piped = ""
    try:
        if not sys.stdin.isatty():
            piped = sys.stdin.read().strip()
    except Exception:
        piped = ""
    if text:
        parts.append(text)
    if piped:
        parts.append("\n\n```\n%s\n```" % piped if text else piped)
    for f in args.file:
        p = Path(f)
        if not p.exists():
            sys.stderr.write("[llm] 找不到文件：%s\n" % f)
            return 4
        parts.append("\n\n--- %s ---\n%s" % (p.name, p.read_text(encoding="utf-8", errors="replace")))
    if not parts:
        sys.stderr.write("[llm] 没给提示词（也没有 stdin）\n")
        return 5

    msg = {"role": "user", "content": "\n".join(parts)}
    if args.image:
        imgs = []
        for i in args.image:
            p = Path(i)
            if not p.exists():
                sys.stderr.write("[llm] 找不到图片：%s\n" % i)
                return 4
            imgs.append(base64.b64encode(p.read_bytes()).decode())
        msg["images"] = imgs

    messages = ([{"role": "system", "content": args.system}] if args.system else []) + [msg]

    # 只有 qwen3-vl 这类「模板写死 <think>」的模型才用 prefill 补丁；
    # 且必须配 think:true（think:false 时模板会变，prefill 反而被当正文）。
    if not think and any(model.startswith(t) for t in NEEDS_PREFILL):
        think = True
        messages.append(PREFILL)
    # gpt-oss 用档位而非布尔（false 会被忽略）
    for fam, level in LEVEL_THINK_MODELS.items():
        if model.startswith(fam):
            think = level if not args.think else "high"

    # math 角色用贪心解码 —— 实测同一个数学题 temp=0.0 得 2/3、temp=0.7 只有 1/3
    # （0.7 时它把「进水管3小时/排水管5小时」推成「3/3=1小时」，推理链直接崩）
    temp = 0.0 if role == "math" else 0.7

    body = {"model": model, "messages": messages, "stream": False,
            "think": think,
            "options": {"num_ctx": ctx, "num_predict": args.num_predict, "temperature": temp}}

    t0 = time.time()
    try:
        d = _post("/api/chat", body, timeout=3600)
    except urllib.error.HTTPError as exc:
        sys.stderr.write("[llm] HTTP %s: %s\n" % (exc.code, exc.read()[:300].decode("utf-8", "replace")))
        return 6
    except Exception as exc:
        sys.stderr.write("[llm] 请求失败：%s\n" % exc)
        return 6

    m = d.get("message", {})
    content = (m.get("content") or "").strip()
    thinking = (m.get("thinking") or "").strip()
    dt = time.time() - t0
    ec, ed = d.get("eval_count", 0), d.get("eval_duration", 1) or 1
    pc, pd = d.get("prompt_eval_count", 0), d.get("prompt_eval_duration", 1) or 1

    _out(content if content else (thinking or "(空回复)"))
    if args.json:
        _out(json.dumps({
            "model": model, "role": role, "think": think,
            "prompt_tokens": pc, "completion_tokens": ec,
            "prefill_tok_s": round(pc / (pd / 1e9), 1) if pd else None,
            "decode_tok_s": round(ec / (ed / 1e9), 1),
            "first_token_s": round(pd / 1e9, 2),
            "wall_s": round(dt, 2),
            "empty_content": not content,
        }, ensure_ascii=False))
    elif not args.quiet:
        sys.stderr.write("[llm] %s · %s · 首token %.1fs · %.1f tok/s · 共 %.1fs%s\n" % (
            model, role, pd / 1e9, ec / (ed / 1e9) if ed else 0, dt,
            "  ⚠️ content 为空，思考吃光了预算（试 --no-think 或换 -t chat）" if not content else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
