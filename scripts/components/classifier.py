#!/usr/bin/env python3
"""
SkillClassifier — rule-based heuristic classification for skills.

No external API calls. All confidence scores are derived from actual
keyword-match counts. Decision points are annotated with
``# PRODUCTION: replace with LLM call`` comments.
"""
import re
from collections import defaultdict
from typing import Any

# ── namespace keyword maps ──
# Each namespace has a list of keywords checked against skill name + content.
_NAMESPACE_MAP = {
    "logs/queries":     ["elasticsearch", "es-", "query", "search", "index", "lucene"],
    "logs/alerts":      ["alert", "alarm", "notification", "trigger", "threshold"],
    "logs/dashboards":  ["dashboard", "viz", "visualization", "chart", "graph", "monitor"],
    "logs/workflows":   ["pipeline", "workflow", "rca", "flow", "orchestrat", "stage"],
    "logs/shared":      ["builder", "parser", "formatter", "auth", "util", "common", "base"],
}


class SkillClassifier:
    """Rule-based classifier that mimics LLM decisions for skill metadata."""

    def __init__(self, raw_skills: list[dict]):
        self.raw_skills = raw_skills

    @staticmethod
    def _skill_text(skill: dict) -> str:
        fm = skill.get("existing_frontmatter", "")
        if isinstance(fm, dict):
            fm = str(fm)
        return f"{skill.get('name', '')} {skill.get('content', '')} {fm}".lower()

    def infer_namespace(self, skill: dict,
                        candidate_namespaces: list[str] | None = None) -> dict:
        """Return {namespace, confidence, reasoning} based on keyword matches."""
        text = self._skill_text(skill)
        scores: dict[str, int] = {}
        for ns, kws in _NAMESPACE_MAP.items():
            if candidate_namespaces and ns not in candidate_namespaces:
                continue
            count = sum(1 for kw in kws if kw.lower() in text)
            if count:
                scores[ns] = count

        if not scores:
            # PRODUCTION: replace with LLM call for zero-match skills
            return {
                "namespace": "",
                "confidence": 0.0,
                "reasoning": "No namespace keywords matched in skill name or content.",
            }

        best_ns = max(scores, key=scores.get)
        best_score = scores[best_ns]
        max_possible = len(_NAMESPACE_MAP[best_ns])
        confidence = round(best_score / max_possible, 2)
        matched = [kw for kw in _NAMESPACE_MAP[best_ns] if kw.lower() in text]
        return {
            "namespace": best_ns,
            "confidence": confidence,
            "reasoning": f"Matched {len(matched)}/{max_possible} ns keywords: {matched}",
        }

    def infer_dependencies(self, skill: dict,
                           all_skill_names: list[str]) -> dict:
        """Return {includes, optional_includes, confidence} by scanning content."""
        text = self._skill_text(skill)
        my_name = skill.get("name", "")
        includes: list[str] = []
        optional: list[str] = []
        seen_names = {s for s in all_skill_names if s and s != my_name}

        # Phase 1 — direct name mention
        # PRODUCTION: replace with LLM call for semantic dependency extraction
        for sn in all_skill_names:
            if sn and sn != my_name and sn.lower() in text:
                includes.append(sn)

        # Phase 2 — pattern-based (调用/use/depends on /xxx)
        for match in re.finditer(r"(?:调用|use|depends\s+on)\s*[/:：]\s*(\S+)", text):
            cand = match.group(1).rstrip(",. ")
            if cand in seen_names and cand not in includes:
                includes.append(cand)

        # Phase 3 — cross-reference word overlap → optional
        # PRODUCTION: replace with LLM call for semantic matching
        words = set(re.findall(r"\b[a-z]\w+\b", text))
        for sn in all_skill_names:
            if sn == my_name or sn in includes:
                continue
            sn_words = set(re.findall(r"\b[a-z]\w+\b", sn.lower()))
            if sn_words and (words & sn_words):
                optional.append(sn)

        includes = list(dict.fromkeys(includes))
        optional = [s for s in dict.fromkeys(optional) if s not in includes]
        total = len(seen_names) or 1
        confidence = round(min((len(includes) + len(optional)) / total, 1.0), 2)
        return {"includes": includes, "optional_includes": optional, "confidence": confidence}

    def infer_paths(self, skill: dict) -> list[str]:
        """Suggest glob patterns (low confidence — always needs human review).

        # PRODUCTION: replace with LLM call for path inference
        """
        text = self._skill_text(skill)
        lang_pats = {
            "python":     ["**/*.py"],
            "javascript": ["**/*.js"],
            "typescript": ["**/*.ts", "**/*.tsx"],
            "react":      ["**/*.tsx", "**/*.jsx"],
            "go":         ["**/*.go"],
            "rust":       ["**/*.rs"],
            "java":       ["**/*.java"],
            "docker":     ["**/Dockerfile", "**/*.dockerfile"],
            "yaml":       ["**/*.yaml", "**/*.yml"],
            "markdown":   ["**/*.md"],
        }
        patterns: list[str] = []
        for lang, pats in lang_pats.items():
            if lang in text:
                patterns.extend(pats)
        return list(dict.fromkeys(patterns))

    def detect_conflicts(self, skills: list[dict] | None = None) -> list[dict]:
        """Return conflict pairs: [{skill_a, skill_b, reason}, ...]."""
        if skills is None:
            skills = self.raw_skills
        conflicts: list[dict] = []

        # Duplicate names
        by_name = defaultdict(list)
        for s in skills:
            by_name[s.get("name", "")].append(s)
        for name, instances in by_name.items():
            if len(instances) > 1:
                conflicts.append({
                    "skill_a": instances[0].get("name", ""),
                    "skill_b": instances[1].get("name", ""),
                    "reason": f"Duplicate skill name '{name}'",
                })

        # High content overlap within same namespace
        by_ns = defaultdict(list)
        for s in skills:
            by_ns[s.get("namespace", "")].append(s)
        for ns, group in by_ns.items():
            if not ns or len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    words_i = set(self._skill_text(group[i]).split())
                    words_j = set(self._skill_text(group[j]).split())
                    common = words_i & words_j
                    if len(common) > 10:
                        conflicts.append({
                            "skill_a": group[i].get("name", ""),
                            "skill_b": group[j].get("name", ""),
                            "reason": f"High word overlap ({len(common)} words) in ns '{ns}'",
                        })
        return conflicts

    def classify_all(self) -> dict[str, Any]:
        """Run classification over all skills, choosing method by count."""
        n = len(self.raw_skills)
        all_names = [s.get("name", "") for s in self.raw_skills]

        if n < 50:
            method = "keyword_matching"
        elif n <= 200:
            method = "keyword_matching_with_grouping"
        else:
            method = "marked_for_embedding"
            # PRODUCTION: replace with embedding-based classification

        results: dict[str, Any] = {"method": method, "total": n, "skills": []}
        for skill in self.raw_skills:
            results["skills"].append({
                "name": skill.get("name", ""),
                "namespace": self.infer_namespace(skill),
                "dependencies": self.infer_dependencies(skill, all_names),
                "paths": self.infer_paths(skill),
            })
        results["conflicts"] = self.detect_conflicts()
        return results
