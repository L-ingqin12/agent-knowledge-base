/**
 * Quality Gate Hook — 子智能体输出质量门控
 *
 * 在子智能体返回后自动执行质量检查，不通过则携带反馈重试。
 *
 * 安装: 在 opencode.json 中配置:
 * {
 *   "hooks": {
 *     "tool.execute.after": [".opencode/hooks/quality-gate.js"]
 *   }
 * }
 */

// ─── 工具函数 ──────────────────────────────────

function extractCodeBlocks(output) {
  return (output.match(/```[\s\S]*?```/g) || []);
}

function countCodeLines(output) {
  const blocks = extractCodeBlocks(output);
  return blocks.reduce((sum, block) => {
    const lines = block.split('\n');
    // 跳过第一行 (语言标识) 和最后一行 (结尾 ```)
    const codeOnly = lines.slice(1, -1).filter(l => l.trim() && !l.trim().startsWith('//') && !l.trim().startsWith('#'));
    return sum + codeOnly.length;
  }, 0);
}

function hasAnyCode(output) {
  return countCodeLines(output) >= 2; // 至少有 2 行有效代码
}

function textLength(output) {
  // 去掉代码块后的纯文本长度
  return output.replace(/```[\s\S]*?```/g, '').replace(/\s+/g, ' ').trim().length;
}

function isReviewLike(output) {
  // 检测是否像审查报告（有审查/问题/漏洞关键词）
  const reviewKeywords = /审查|问题|漏洞|风险|bug|issue|vuln|CWE|OWASP|安全|修复|建议|refactor/i;
  const findingPattern = /\[S-\d+\]|\[CRIT-\d+\]|\[W-\d+\]|\[N-\d+\]|CWE-\d+|🔴|🟡|🟠/;
  return reviewKeywords.test(output) || findingPattern.test(output);
}

function hasFindingsWithLineRefs(output) {
  // 检查是否有 file:line 或 file line 格式的引用
  return /\S+\.\w{1,6}:\d+/m.test(output) ||
         /\S+\.\w{1,6}\s+(line|行)\s*\d+/i.test(output);
}

// 代码生成类 — 始终期望产出代码
const ALWAYS_CODE = ['test-writer', 'refactor-specialist', 'debugger'];

// ─── 门控规则 ──────────────────────────────────

const GATES = {
  code_generators: {
    agents: ['test-writer', 'refactor-specialist', 'debugger', 'doc-writer'],
    checks: [
      {
        id: 'syntax',
        severity: 'BLOCKER',
        description: '必须有实际代码或内容产出',
        check(output, agentName) {
          const textLen = textLength(output);
          const hasCode = hasAnyCode(output);

          // test-writer/refactor/debugger: 必须有代码
          if (ALWAYS_CODE.includes(agentName)) {
            if (!hasCode) {
              if (textLen < 50) {
                return { pass: false, reason: '输出过短且无有效代码块（可能未执行任务）' };
              }
              return { pass: false, reason: '缺少代码块 — 作为代码生成类智能体必须产出代码' };
            }
          }

          // doc-writer: 代码或足够长的文档内容都行
          if (agentName === 'doc-writer') {
            if (!hasCode && textLen < 80) {
              return { pass: false, reason: `输出过短 (${textLen} chars)，文档产出不足` };
            }
          }

          return { pass: true };
        }
      },
      {
        id: 'completeness',
        severity: 'BLOCKER',
        description: '检查输出完整性',
        check(output, agentName) {
          const issues = [];

          // TODO 占位符 + 几乎无代码
          if (/TODO|FIXME|XXX|TBD/i.test(output) && countCodeLines(output) < 3) {
            issues.push('包含未实现的占位符 (TODO/FIXME/TBD)，缺少实际实现');
          }

          // 大段文字但无代码（仅对 ALWAYS_CODE 类型，doc-writer 豁免）
          if (ALWAYS_CODE.includes(agentName)) {
            const blocks = extractCodeBlocks(output);
            const textOnly = textLength(output);
            if (textOnly > 80 && blocks.length === 0) {
              issues.push('大量文字描述但无任何代码块 — 预期有可运行的代码');
            }
          }

          return issues.length === 0
            ? { pass: true }
            : { pass: false, reason: issues.join('; ') };
        }
      }
    ]
  },

  analyzers: {
    agents: ['code-reviewer', 'security-auditor'],
    checks: [
      {
        id: 'specificity',
        severity: 'BLOCKER',
        description: '审查发现必须具体（有行号或代码引用）',
        check(output) {
          const isReview = isReviewLike(output);
          const hasRefs = hasFindingsWithLineRefs(output);
          const hasCodeBlocks = extractCodeBlocks(output).length > 0;

          // 如果读起来像审查报告，但没有任何具体引用 → 太模糊
          if (isReview && !hasRefs && !hasCodeBlocks) {
            return {
              pass: false,
              reason: '审查输出缺乏具体引用 — 需要 file:line 格式的行号或代码片段'
            };
          }

          // 有具体引用 + 代码块 → 无论长度多少都通过（高质量输出）
          if (hasRefs && hasCodeBlocks) {
            return { pass: true };
          }

          // 如果输出很短，像是没有完成审查
          if (textLength(output) < 60) {
            return { pass: false, reason: `审查输出过短 (${textLength(output)} chars)` };
          }

          return { pass: true };
        }
      },
      {
        id: 'actionable',
        severity: 'WARNING',
        description: '每个严重问题应有修复建议',
        check(output) {
          const diffBlocks = (output.match(/```diff[\s\S]*?```/g) || []).length;
          const findings = (output.match(/\[S-\d+\]|\[CRIT-\d+\]/g) || []).length;

          if (findings > 0 && diffBlocks === 0) {
            return {
              pass: false,
              reason: `${findings} 个严重问题但无修复建议 (diff 块) — 分析类输出应包含可操作的修复`
            };
          }

          return { pass: true };
        }
      }
    ]
  }
};

// ─── 状态追踪 ──────────────────────────────────

const taskStates = new Map();
const MAX_RETRIES = 3;
const SAME_FAILURE_THRESHOLD = 2;

// ─── 核心函数 ──────────────────────────────────

/**
 * 运行质量门控
 */
function runQualityGates(agentName, output, retryCount, previousFailures) {
  // 非子智能体不检查
  const allAgents = [
    ...GATES.code_generators.agents,
    ...GATES.analyzers.agents
  ];
  if (!allAgents.includes(agentName)) {
    return { pass: true, failures: [], action: 'ACCEPT' };
  }

  // 找到适用规则集
  let rules;
  if (GATES.code_generators.agents.includes(agentName)) {
    rules = GATES.code_generators.checks;
  } else if (GATES.analyzers.agents.includes(agentName)) {
    rules = GATES.analyzers.checks;
  } else {
    return { pass: true, failures: [], action: 'ACCEPT' };
  }

  // 执行所有门控
  const failures = [];
  for (const rule of rules) {
    const result = rule.check(output, agentName);
    if (!result.pass) {
      failures.push({
        gate: rule.id,
        severity: rule.severity,
        reason: result.reason
      });
    }
  }

  const blockers = failures.filter(f => f.severity === 'BLOCKER');

  // 无阻塞问题 → 通过
  if (blockers.length === 0) {
    return { pass: true, failures, action: 'ACCEPT' };
  }

  // ─── 不通过时的分支判断 ───

  // 死循环检测: 同一组门控连续失败
  const currentGateIds = blockers.map(f => f.gate).sort().join(',');
  const previousGateIds = (previousFailures || []).sort().join(',');

  if (currentGateIds === previousGateIds) {
    // 同一组门控连续失败 → 死循环
    return {
      pass: false,
      failures: blockers,
      action: 'ESCALATE',
      reason: `死循环检测: 连续失败于相同门控 [${currentGateIds}]，继续重试无法改善。请人工介入。`
    };
  }

  // 超过最大重试次数
  if (retryCount >= MAX_RETRIES) {
    return {
      pass: false,
      failures: blockers,
      action: 'ESCALATE',
      reason: `已重试 ${retryCount} 次（上限 ${MAX_RETRIES}），仍未通过门控 [${currentGateIds}]`
    };
  }

  // 可重试
  return {
    pass: false,
    failures: blockers,
    action: 'RETRY',
    feedback: blockers.map(b => `[GATE:${b.gate}] ${b.reason}`).join('\n')
  };
}

/**
 * 构建 RETRY 反馈文本
 */
function buildRetryFeedback(failures) {
  const blockers = failures.filter(f => f.severity === 'BLOCKER');
  const warnings = failures.filter(f => f.severity === 'WARNING');

  let feedback = '\n## ⚠️ 上一轮未通过质量检查\n';

  if (blockers.length > 0) {
    feedback += '### 阻塞问题 (必须修复):\n';
    blockers.forEach(f => {
      feedback += `- [GATE:${f.gate}] ${f.reason}\n`;
    });
  }

  if (warnings.length > 0) {
    feedback += '\n### 改进建议:\n';
    warnings.forEach(f => {
      feedback += `- [GATE:${f.gate}] ${f.reason}\n`;
    });
  }

  feedback += '\n### 本轮要求:\n请基于以上反馈修正输出，确保所有阻塞问题已解决。\n';

  return feedback;
}

module.exports = {
  GATES,
  runQualityGates,
  buildRetryFeedback,
  taskStates,
  MAX_RETRIES,
  SAME_FAILURE_THRESHOLD
};
