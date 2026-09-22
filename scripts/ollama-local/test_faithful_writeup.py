"""测「忠实扩写」能力：给一组确定事实，要求写成报告，检查是否编造素材外内容。

这是本地模型能否承担「调研写稿环节」的分水岭：
  - 若忠实（只用给定素材）→ 可以承担长输出，省大量输出成本
  - 若编造（补充了素材里没有的数字/名称）→ 不能用，因为调研报告的价值就在准确性

检查法：从输出里抽出所有「数字」与「大写英文缩写」，逐个比对是否出现在素材里。
"""
import json
import re
import time

import requests

API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}

# 一组虚构但自洽的"调研素材"（刻意不含任何真实常识，便于检出编造）
FACTS = [
    "澄江市轨道交通 3 号线于 2019 年 4 月开工，全长 28.6 公里，设站 19 座。",
    "该项目总投资 147 亿元，由澄江城建集团与南方轨道装备联合承建。",
    "线路采用 CBTC 信号系统，设计最高时速 80 公里，日均客流预测 42 万人次。",
    "施工中遇到的主要困难是穿越老城区的软土地层，采用了冻结法施工。",
    "3 号线计划 2026 年 12 月开通试运营，比原计划推迟了 14 个月。",
]
PROMPT = ("下面是一组调研素材。请据此写一份约 800 字的项目概况报告，"
          "**只使用素材中给出的信息，不要补充任何素材之外的数字、名称或事实**。若需要展开论述，"
          "只能围绕素材已有内容展开。\n\n素材：\n" + "\n".join("- " + f for f in FACTS))

# 素材中允许出现的数字/缩写白名单
SRC = " ".join(FACTS)
ALLOWED_NUM = set(re.findall(r"\d+(?:\.\d+)?", SRC))
ALLOWED_ABBR = set(re.findall(r"\b[A-Z]{2,}\b", SRC))

MODELS = [("qwen3.5:0.8b", 16384), ("phi4-mini:latest", 8192),
          ("granite4:micro-h", 32768), ("llama3.2:3b", 8192)]

print("素材白名单: 数字 %s | 缩写 %s" % (sorted(ALLOWED_NUM), sorted(ALLOWED_ABBR)))
print("%-20s %-8s %-10s %-10s %s" % ("模型", "输出tok", "编造数字", "编造缩写", "结论"))
print("-" * 72)

for model, ctx in MODELS:
    body = {"model": model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": PROMPT}],
            "options": {"num_predict": 1500, "num_ctx": ctx, "temperature": 0}}
    try:
        d = requests.post(API + "/chat", headers=H,
                          data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                          timeout=2400).json()
    except Exception as exc:
        print("%-20s 失败: %s" % (model, str(exc)[:40]), flush=True)
        continue
    out = (d.get("message", {}).get("content") or "")
    nums = set(re.findall(r"\d+(?:\.\d+)?", out)) - ALLOWED_NUM
    abbrs = set(re.findall(r"\b[A-Z]{2,}\b", out)) - ALLOWED_ABBR
    # 过滤明显无害的（年份片段等已含在 allowed；只报真正多出来的）
    verdict = "✅ 忠实" if not nums and not abbrs else "❌ 编造"
    print("%-20s %-8d %-10s %-10s %s" % (
        model, d.get("eval_count", 0),
        (",".join(sorted(nums)[:5]) or "无"),
        (",".join(sorted(abbrs)[:4]) or "无"), verdict), flush=True)
