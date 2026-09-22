"""扩测 v2：8 组素材 × 6 模型 —— 忠实扩写能力，**可人工复核**。

相对 v1 修掉三个已知缺陷（v1 保留在 test_faithful_ext.py 以便存证）：

  缺陷1 假阳性：提示词里写「约 600 字」，`600` 不在素材里且满足「≥3 位数字」，
        模型回一句「以下约 600 字的报告」就被误判编造。
        -> 现在把**整个提示词模板**里出现的数字也并入 allowed。

  缺陷2 不可复核：v1 只打印汇总，事后无法核对到底哪句话被判编造。
        -> 现在把每组原始输出落盘到 faithful_ext2_raw.json，可逐条回查。

  缺陷3 单一阈值：只看 ≥3 位数字，会漏掉 2 位数的编造（如「共 12 台」）。
        -> 现在同时统计 ≥2 位，作为更宽松的第二信号（仅参考，不作结论）。

其余判据与 v1 一致：输出中出现「素材与提示词都没有的数字」即判该组不忠实。
**注意本检查器只能查数字，查不出编造的专有名词**——这是已知的覆盖缺口。
"""
import json
import re
import sys

import requests

API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}

CASES = [
    (["云栖数据中心一期于 2018 年 9 月投运，机柜 3200 架，设计 PUE 1.28。",
      "二期规划 2400 架，预计 2027 年 3 月投运。"], "云栖数据中心"),
    (["澜川大桥主跨 1088 米，2015 年 11 月合龙，双向 8 车道。",
      "工程造价 62 亿元，抗风设计按 14 级标准。"], "澜川大桥"),
    (["青浦生物医药园引进企业 147 家，其中上市企业 9 家。",
      "2025 年园区总产值 380 亿元，同比增长 21%。"], "青浦生物医药园"),
    (["北辰风电场装机 240 兆瓦，共 60 台机组，单机 4 兆瓦。",
      "年发电量约 5.6 亿千瓦时，2024 年 6 月并网。"], "北辰风电场"),
    (["星海大学材料实验室 2020 年成立，现有 PI 12 人。",
      "近三年发表论文 240 篇，其中高被引 31 篇。"], "星海大学材料实验室"),
    (["江城地铁 7 号线全长 34.2 公里，设站 22 座，2026 年 10 月开通。",
      "采用全自动运行系统，最高时速 100 公里。"], "江城地铁 7 号线"),
    (["恒锐智能 2024 年营收 18.6 亿元，研发投入占 12.4%。",
      "员工 2100 人，其中研发人员 780 人。"], "恒锐智能"),
    (["南海珊瑚礁保护区面积 286 平方公里，覆盖 3 个岛礁。",
      "2019 年起禁止采捕，珊瑚覆盖率由 18% 回升至 27%。"], "南海珊瑚礁保护区"),
]

# 模板本身含数字（"600"），必须一并视为合法，否则模型复述字数就被误判编造。
PROMPT_T = ("下面是一组调研素材。请据此写一份约 600 字的概况报告，"
            "**只使用素材中给出的信息，不要补充任何素材之外的数字、名称或事实**。\n\n素材：\n%s")

MODELS = [("granite4:micro-h", 32768), ("qwen3.5:0.8b", 16384), ("qwen3.5:2b", 16384),
          ("llama3.2:3b", 8192), ("phi4-mini:latest", 8192), ("qwen3-vl:2b", 8192)]

NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def nums_in(text):
    return set(NUM_RE.findall(text))


# 提示词模板（不含素材）里出现的数字——这些是模型被「允许」复述的
TEMPLATE_NUMS = nums_in(PROMPT_T % "")

raw = {}
print("%-20s %-9s %-8s %-9s %-9s %s" % ("模型", "忠实组数", "平均tok", "编造(>=3位)", "可疑(>=2位)", "结论"))
print("-" * 88)

for model, ctx in MODELS:
    faithful = 0
    toks = []
    bad = []
    soft = []
    raw[model] = []
    for facts, topic in CASES:
        src = " ".join(facts)
        prompt = PROMPT_T % "\n".join("- " + f for f in facts)
        allowed = nums_in(src) | nums_in(prompt)

        body = {"model": model, "stream": False, "think": False,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"num_predict": 1200, "num_ctx": ctx, "temperature": 0}}
        try:
            d = requests.post(API + "/chat", headers=H,
                              data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                              timeout=1800).json()
        except Exception as exc:
            bad.append(topic + ":请求失败")
            raw[model].append({"topic": topic, "error": str(exc)[:200]})
            continue

        msg = d.get("message", {})
        out = msg.get("content") or ""
        toks.append(d.get("eval_count", 0))
        raw[model].append({"topic": topic, "output": out,
                           "eval_count": d.get("eval_count", 0),
                           "thinking_field": bool(msg.get("thinking"))})

        hard = {n for n in nums_in(out) if len(n.replace(".", "")) >= 3} - allowed
        soft_nums = {n for n in nums_in(out) if len(n.replace(".", "")) >= 2} - allowed
        if hard:
            bad.append("%s:%s" % (topic, ",".join(sorted(hard)[:3])))
        else:
            faithful += 1
        if soft_nums:
            soft.append("%s:%s" % (topic, ",".join(sorted(soft_nums)[:3])))

    avg = sum(toks) // len(toks) if toks else 0
    print("%-20s %-9s %-8s %-9s %-9s %s" % (
        model, "%d/%d" % (faithful, len(CASES)), avg,
        (", ".join(bad[:2]) if bad else "无"),
        (", ".join(soft[:2]) if soft else "无"),
        "忠实" if not bad else "有编造"), flush=True)

with open("faithful_ext2_raw.json", "w", encoding="utf-8") as fh:
    json.dump(raw, fh, ensure_ascii=False, indent=1)
print("\n原始输出已落盘: faithful_ext2_raw.json (可逐条人工复核)", flush=True)
