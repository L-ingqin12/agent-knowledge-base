"""知识准确性测试 —— 针对「速度不重要但准确性重要」的场景（长文探索、知识文档编撰）。

设计原则：
  * 题目答案**客观可判定**，且都是训练语料里高频出现的事实，不存在争议
  * 分三档难度：常识 / 技术常识 / 术语全称（小模型最常在"术语全称"上编造）
  * 强制简短作答（num_predict 小），避免长篇里蒙对关键词
  * 记录错误原文，便于人工判断是"不知道"还是"自信地编"
"""
import json
import re
import time

import requests

API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}

# (问题, 判定模式, 正确答案说明)
CASES = [
    ("MCP 协议的全称是什么？只回英文全称。", r"model\s*context\s*protocol", "Model Context Protocol"),
    ("RAG 的全称是什么？只回英文全称。", r"retrieval[\s-]*augmented\s*generation", "Retrieval-Augmented Generation"),
    ("HTTP 状态码 404 代表什么？四个字以内。", r"未找到|不存在|not\s*found", "Not Found / 未找到"),
    ("SHA-256 的输出是多少位？只回数字。", r"\b256\b", "256"),
    ("Python 里 len([1,2,3]) 的结果？只回数字。", r"\b3\b", "3"),
    ("TCP 三次握手的第二个报文是什么？只回英文缩写。", r"syn[\s-]*ack", "SYN+ACK"),
    ("git 里查看提交历史的命令是什么？只回命令。", r"git\s+log", "git log"),
    ("JSON 的三个基本数据类型举一个即可，只回一个词。", r"string|number|boolean|array|object|null|字符串|数字|布尔|数组|对象", "任意一个"),
]


def ask(model, q, ctx=16384):
    body = {"model": model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": q}],
            "options": {"num_predict": 64, "num_ctx": ctx, "temperature": 0}}
    d = requests.post(API + "/chat", headers=H,
                      data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                      timeout=900).json()
    return (d.get("message", {}).get("content") or "").strip()


for model, ctx in [("qwen3.5:0.8b", 16384), ("granite4:micro-h", 32768),
                   ("qwen2.5-coder:3b", 16384), ("qwen3.5:2b", 16384)]:
    right = 0
    wrong = []
    print("===", model, flush=True)
    for q, pat, expect in CASES:
        try:
            ans = ask(model, q, ctx)
        except Exception as exc:
            print("   [超时/失败] %s" % q[:24]); continue
        ok = bool(re.search(pat, ans, re.I))
        right += ok
        if not ok:
            wrong.append((q[:20], ans[:60].replace("\n", " "), expect))
        print("   %s %-28s → %s" % ("✅" if ok else "❌", q[:28], json.dumps(ans[:50], ensure_ascii=False)),
              flush=True)
    print("   得分: %d/%d" % (right, len(CASES)), flush=True)
    if wrong:
        print("   ❌ 错项（原文 | 应为）:")
        for q, a, e in wrong:
            print("      %-22s %-40s | %s" % (q, a, e), flush=True)
    print(flush=True)
