#!/usr/bin/env node
/**
 * Workflow-Orchestrator 协作演示
 *
 * 模拟 Orchestrator (主 Agent) 加载并执行 workflow 的完整流程。
 * 展示: 匹配→分解→Fan-Out→质量门控→回环→集成→汇报
 *
 * 用法: node scripts/demo-workflow-execution.js [workflow-name]
 */

const { runQualityGates } = require('../.opencode/hooks/quality-gate.js');

// ─── Workflow 剧本库 (内置于 Orchestrator) ───

const WORKFLOWS = {
  'full-review': {
    name: 'full-review',
    description: '上线前全面检查 — 代码审查 + 安全审计 + 文档更新',
    mode: 'parallel',
    keywords: ['上线', '发布', 'release', 'deploy', '全面检查', 'full check', 'checklist'],
    maxRetries: 3,
    steps: [
      { id: 'review', agent: 'code-reviewer', mode: 'readonly',
        prompt: '审查 src/ 全部代码，关注错误处理、边界条件和 API 接口变更' },
      { id: 'security', agent: 'security-auditor', mode: 'readonly',
        prompt: '安全审计 src/，扫描 OWASP Top 10 漏洞和依赖 CVE' },
      { id: 'docs', agent: 'doc-writer', mode: 'readwrite',
        prompt: '检查并更新 README 和 API 文档，确认与代码一致' },
    ]
  },

  'bug-fix': {
    name: 'bug-fix',
    description: 'Bug 修复流程 — debug → 验证 → 重构 → 回归测试',
    mode: 'serial',
    keywords: ['bug', 'fix', '修复', '报错', '异常', 'debug', '调试'],
    maxRetries: 3,
    steps: [
      { id: 'debug', agent: 'debugger', mode: 'readwrite',
        prompt: '定位 bug 根因，输出修复方案' },
      { id: 'refactor', agent: 'refactor-specialist', mode: 'readwrite',
        prompt: '基于修复方案重构相关代码，保留修复逻辑' },
      { id: 'test', agent: 'test-writer', mode: 'readwrite',
        prompt: '为修复编写回归测试，确保不会复发' },
    ]
  },

  'feature-implementation': {
    name: 'feature-implementation',
    description: 'Feature 实现流程 — 实现 → 测试 → 审查',
    mode: 'serial',
    keywords: ['新功能', 'feature', '实现', '开发', 'add', 'implement'],
    maxRetries: 3,
    steps: [
      { id: 'implement', agent: 'refactor-specialist', mode: 'readwrite',
        prompt: '实现 feature，遵循现有代码风格' },
      { id: 'test', agent: 'test-writer', mode: 'readwrite',
        prompt: '为新功能编写测试' },
      { id: 'review', agent: 'code-reviewer', mode: 'readonly',
        prompt: '审查新实现代码' },
    ]
  }
};

// ─── Mock 子智能体输出 ───

const MOCK_OUTPUTS = {
  'code-reviewer:full': `
## 审查总结
- 审查文件: src/auth.js
- 严重问题: 2
- 改进建议: 3

### [S-01] JWT 密钥硬编码
- **位置**: src/auth.js:5
- **修复**:
\`\`\`diff
- const JWT_SECRET = 'my-secret-key-123456';
+ const JWT_SECRET = process.env.JWT_SECRET;
\`\`\`

### [S-02] 密码明文存储
- **位置**: src/auth.js:13
- **修复**: 使用 bcrypt 哈希
\`\`\`diff
- password: password,
+ password: bcrypt.hashSync(password, 10),
\`\`\`
`,

  'code-reviewer:pass': `
## 审查总结
- 审查文件: src/auth.js, src/middleware/session.js
- 严重问题: 0
- 改进建议: 1

### [W-01] 建议添加 Token 刷新机制
- **位置**: src/auth.js:35
- **建议**: 当前 Token 无刷新机制，建议添加 refresh token
\`\`\`diff
+ function refreshToken(oldToken) {
+   const decoded = jwt.verify(oldToken, process.env.JWT_SECRET);
+   return generateToken(decoded.userId);
+ }
\`\`\`

整体代码质量良好，之前的硬编码密钥和明文密码问题已修复。
`,

  'security-auditor:full': `
## 安全审计报告
### [CRIT-01] CWE-798 硬编码凭据 — src/auth.js:5
\`\`\`diff
- const JWT_SECRET = 'my-secret-key-123456';
+ const JWT_SECRET = process.env.JWT_SECRET;
\`\`\`
### [CRIT-02] CWE-312 明文存储 — src/auth.js:13
\`\`\`diff
- password: password,
+ password: bcrypt.hashSync(password, 10),
\`\`\`
### [W-01] 缺少速率限制 — src/auth.js:29
`,

  'doc-writer:pass': `
## API 文档更新

### 认证模块 (src/auth.js)
| 端点 | 方法 | 说明 |
|------|------|------|
| /api/auth/login | POST | 用户登录，返回 JWT |
| /api/auth/register | POST | 用户注册 |
| /api/auth/reset | POST | 密码重置 |

### 配置
- JWT 密钥通过环境变量 \`JWT_SECRET\` 注入
- 密码使用 bcrypt (saltRounds=10) 哈希存储
`,

  'doc-writer:short': '文档已完成。',

  'debugger:rootcause': `
## Bug 报告

### 现象
用户登录后约 5 分钟必定超时，需重新登录。

### 根因分析
- **位置**: src/middleware/session.js:42
- **原因**: JWT \`expiresIn\` 误设为 \`'5m'\` (5 分钟) 应为 \`'24h'\`
\`\`\`diff
- expiresIn: '5m',
+ expiresIn: '24h',
\`\`\`

### 修复方案
修改 session.js:42 的过期时间配置。无副作用。
`,

  'debugger:vague': '登录超时可能是 Token 配置问题。检查一下 session 相关的代码。',

  'refactor-specialist:pass': `
## 重构完成
\`\`\`diff
- function processUserLogin(data) {
-   const u = findUser(data.name);
-   if (!u) throw new Error('no user');
-   return makeToken(u);
- }
+ async function authenticateUser(credentials) {
+   const user = await findUserByName(credentials.username);
+   if (!user) throw new AuthenticationError('Invalid credentials');
+   return generateAuthToken(user);
+ }
\`\`\`
所有现有测试通过 ✅
`,

  'test-writer:pass': `
## 回归测试
\`\`\`javascript
test('token expiresIn should be 24h not 5m', () => {
  const config = require('../src/middleware/session');
  expect(config.expiresIn).toBe('24h');
});

test('login should not timeout before 24h', async () => {
  const token = await login('user', 'pass');
  const decoded = jwt.decode(token);
  const expiresIn = decoded.exp - decoded.iat;
  expect(expiresIn).toBe(86400); // 24 hours in seconds
});
\`\`\`
\`\`\`bash
npm test
\`\`\`
`,
};

// ─── 模拟子智能体调用 ───

let callCounter = 0;

function callSubagent(agent, prompt, retryCount) {
  callCounter++;
  const prefix = retryCount > 0 ? `[R${retryCount + 1}]` : '[R1]';

  // 选择 mock 输出
  let output;
  if (agent === 'doc-writer' && retryCount === 0) {
    output = MOCK_OUTPUTS['doc-writer:short']; // 第一次太短 → 触发 RETRY
  } else if (agent === 'debugger' && retryCount === 0) {
    output = MOCK_OUTPUTS['debugger:vague'];    // 第一次太模糊 → 触发 RETRY
  } else {
    output = MOCK_OUTPUTS[`${agent}:pass`] ||
             MOCK_OUTPUTS[`${agent}:full`] ||
             MOCK_OUTPUTS[`${agent}:rootcause`] ||
             `[mock] ${agent} completed task.`;
  }

  console.log(`    ${prefix} ${agent} → ${output.length} chars`);
  return output;
}

// ─── 核心执行引擎 ───

function matchWorkflow(userInput) {
  const input = userInput.toLowerCase();
  for (const [name, wf] of Object.entries(WORKFLOWS)) {
    for (const kw of wf.keywords) {
      if (input.includes(kw.toLowerCase())) {
        return { workflow: wf, matchedKeyword: kw };
      }
    }
  }
  // 默认: 自动分解
  return { workflow: null, matchedKeyword: null };
}

function executeWorkflowStep(step, retryCount = 0, previousFailures = []) {
  const { agent, prompt, id } = step;
  const output = callSubagent(agent, prompt, retryCount);

  // 质量门控
  const gateResult = runQualityGates(agent, output, retryCount, previousFailures);

  if (gateResult.pass) {
    console.log(`      ✅ GATE PASS`);
    return { pass: true, output, retries: retryCount + 1, gateResult };
  }

  if (gateResult.action === 'ESCALATE') {
    console.log(`      🚨 ESCALATE: ${gateResult.reason}`);
    return { pass: false, output, retries: retryCount + 1, gateResult, escalated: true };
  }

  if (gateResult.action === 'RETRY') {
    const failGates = gateResult.failures.map(f => f.gate).join(',');
    console.log(`      🔄 RETRY (gates: ${failGates})`);

    if (retryCount >= 3) {
      console.log(`      🚨 MAX RETRIES → ESCALATE`);
      return { pass: false, output, retries: retryCount + 1, gateResult, escalated: true };
    }

    // 递归重试
    const failedGateIds = gateResult.failures
      .filter(f => f.severity === 'BLOCKER')
      .map(f => f.gate);

    return executeWorkflowStep(step, retryCount + 1, failedGateIds);
  }

  return { pass: true, output, retries: retryCount + 1, gateResult };
}

function executeWorkflow(workflow, userInput) {
  console.log(`\n📋 Workflow: ${workflow.name}`);
  console.log(`   描述: ${workflow.description}`);
  console.log(`   模式: ${workflow.mode}`);
  console.log(`   步骤: ${workflow.steps.map(s => s.agent).join(' → ')}`);
  console.log(`   最大重试: ${workflow.maxRetries}\n`);

  const startTime = Date.now();

  if (workflow.mode === 'parallel') {
    // Fan-Out: 所有步骤并行
    console.log('  ⚡ Fan-Out — 并行执行所有步骤:\n');

    const stepResults = workflow.steps.map(step => {
      console.log(`  📌 Step [${step.id}] → ${step.agent}`);
      const result = executeWorkflowStep(step);
      console.log('');
      return { step, result };
    });

    // 汇总
    const duration = Date.now() - startTime;
    console.log(`  ══════════════════════════`);
    console.log(`  📊 Fan-Out 汇总 (${duration}ms):`);

    const allPassed = stepResults.every(r => r.result.pass);
    const totalRetries = stepResults.reduce((sum, r) => sum + r.result.retries - 1, 0);

    for (const { step, result } of stepResults) {
      const icon = result.pass ? '✅' : '❌';
      const retryInfo = result.retries > 1 ? ` (${result.retries}轮)` : '';
      console.log(`    ${icon} ${step.agent}${retryInfo}`);
    }

    console.log(`   总重试: ${totalRetries}`);
    console.log(`   串行耗时: ${stepResults.length * 2000}ms (估算)`);
    console.log(`   并行耗时: ${duration}ms`);
    console.log(`   加速比: ${((stepResults.length * 2000) / Math.max(duration, 1)).toFixed(1)}x`);

    return { allPassed, stepResults, duration, totalRetries };

  } else {
    // 串行: 逐个执行
    console.log('  🔗 串行执行:\n');

    const stepResults = [];
    let previousResult = null;

    for (const step of workflow.steps) {
      console.log(`  📌 Step [${step.id}] → ${step.agent}`);

      // 串行时，后续步骤的 prompt 可以引用前一步结果
      let contextualPrompt = step.prompt;
      if (previousResult && previousResult.pass) {
        contextualPrompt += `\n## 上一步结果参考\n${previousResult.output.slice(0, 200)}...`;
      }

      const result = executeWorkflowStep({ ...step, prompt: contextualPrompt });
      stepResults.push({ step, result });
      previousResult = result;
      console.log('');

      // 串行时，前一步失败可以选择中止
      if (!result.pass && result.escalated) {
        console.log('  ⛔ 串行中止: 前一步失败');
        break;
      }
    }

    const duration = Date.now() - startTime;
    console.log(`  ══════════════════════════`);
    console.log(`  📊 串行汇总 (${duration}ms):`);

    const allPassed = stepResults.every(r => r.result.pass);
    const totalRetries = stepResults.reduce((sum, r) => sum + r.result.retries - 1, 0);

    for (const { step, result } of stepResults) {
      const icon = result.pass ? '✅' : '❌';
      const retryInfo = result.retries > 1 ? ` (${result.retries}轮)` : '';
      console.log(`    ${icon} ${step.agent}${retryInfo}`);
    }
    console.log(`   总重试: ${totalRetries}`);

    return { allPassed, stepResults, duration, totalRetries };
  }
}

// ─── 交叉验证 ───

function crossValidate(stepResults) {
  console.log('\n  🔀 交叉验证:');

  const findings = {};

  for (const { step, result } of stepResults) {
    if (!result.pass) continue;
    const output = result.output;

    // 提取引用的文件:行号
    const refs = output.match(/\S+\.\w{1,6}:\d+/g) || [];
    for (const ref of refs) {
      if (!findings[ref]) findings[ref] = [];
      findings[ref].push(step.agent);
    }
  }

  // 找出被多个子智能体报告的同一位置
  const crossHits = Object.entries(findings).filter(([_, agents]) => agents.length > 1);

  if (crossHits.length > 0) {
    console.log('  ⚠️ 以下位置被多个子智能体独立发现 (高置信度):');
    for (const [ref, agents] of crossHits) {
      console.log(`    🎯 ${ref} ← ${agents.join(', ')}`);
    }
    console.log('  → 这些问题的优先级应提升为 CRITICAL');
  } else {
    console.log('  无交叉命中的位置');
  }
}

// ─── MAIN ───

const args = process.argv.slice(2);

console.log('═══════════════════════════════════════════');
console.log('  🧠 Orchestrator Workflow Demo');
console.log('═══════════════════════════════════════════');
console.log('');
console.log('  主 Agent: orchestrator (mode: primary)');
console.log('  Workflow: 预设任务剧本');
console.log('  协作方式: ANALYZE匹配 → DELEGATE执行 → VERIFY门控');
console.log('');

// ─── 场景 1: 自动匹配 workflow ───

const testCases = [
  {
    input: '准备上线 v2.0，做全面检查',
    description: '关键词 "上线" + "全面检查" → 自动匹配 full-review workflow'
  },
  {
    input: '修复登录超时的 bug',
    description: '关键词 "修复" + "bug" → 自动匹配 bug-fix workflow'
  }
];

for (const tc of testCases) {
  console.log('───────────────────────────────────────────');
  console.log(`👤 用户: "${tc.input}"`);
  console.log(`   ${tc.description}`);

  const { workflow, matchedKeyword } = matchWorkflow(tc.input);

  if (workflow) {
    console.log(`   ✅ 匹配: ${workflow.name} (关键词: "${matchedKeyword}")\n`);

    console.log('  [ANALYZE] Orchestrator 分析:');
    console.log(`    → 任务类型: ${workflow.name}`);
    console.log(`    → 执行模式: ${workflow.mode}`);
    console.log(`    → 子智能体: ${workflow.steps.map(s => s.agent).join(', ')}`);

    if (workflow.mode === 'parallel') {
      console.log('    → 依赖判断: 各步骤独立 → 可并行 Fan-Out');
    } else {
      console.log('    → 依赖判断: 步骤有先后依赖 → 串行执行');
    }

    console.log('\n  [DELEGATE] 开始执行:');
    const results = executeWorkflow(workflow, tc.input);

    console.log('\n  [VERIFY] 质量门控:');
    console.log(`    ${results.allPassed ? '✅ 全部通过' : '❌ 有失败'}`);
    console.log(`    总重试: ${results.totalRetries}`);

    if (workflow.mode === 'parallel') {
      crossValidate(results.stepResults);
    }

    console.log('\n  [INTEGRATE → DONE]');
    console.log('  Orchestrator 向用户汇报:');
    console.log(`  "${tc.input} — 完成。"`);
    console.log(`   执行了 ${workflow.steps.length} 个子任务, ${results.totalRetries} 次重试。`);

  } else {
    console.log('   → 无匹配 workflow, Orchestrator 自动分解任务');
  }

  console.log('');
}

console.log('═══════════════════════════════════════════');
console.log('  Demo complete');
console.log('═══════════════════════════════════════════');
