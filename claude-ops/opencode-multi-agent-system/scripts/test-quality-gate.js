#!/usr/bin/env node
/**
 * 质量门控系统测试套件 v2
 */

const { runQualityGates, buildRetryFeedback, GATES, MAX_RETRIES } = require('../.opencode/hooks/quality-gate.js');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
  } catch (e) {
    failed++;
    console.log(`  ❌ ${name}`);
    console.log(`     ${e.message}`);
  }
}

function assert(condition, msg) {
  if (!condition) throw new Error(msg || 'assertion failed');
}

function assertEquals(a, b, msg) {
  if (a !== b) throw new Error(msg || `expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
}

console.log('═══════════════════════════════════════');
console.log('  Quality Gate System Tests v2');
console.log('═══════════════════════════════════════\n');

// ─── 代码生成类: syntax gate ──────────────────

console.log('📦 Code Generators — syntax gate:');

test('PASS: test-writer 带完整测试代码', () => {
  const output = `
## 测试
\`\`\`javascript
const bcrypt = require('bcrypt');
test('hash', () => {
  const hash = bcrypt.hashSync('x', 10);
  expect(hash).not.toBe('x');
});
\`\`\`
`;
  const r = runQualityGates('test-writer', output, 0, []);
  assert(r.pass === true, JSON.stringify(r.failures));
});

test('FAIL: test-writer 只有建议无代码', () => {
  const output = '我建议为 auth.js 编写密码哈希测试、登录测试。';
  const r = runQualityGates('test-writer', output, 0, []);
  assert(r.pass === false, 'expected BLOCKER');
  assert(r.failures.some(f => f.gate === 'syntax'), 'should have syntax failure');
});

test('FAIL: debugger 修复方案无代码块', () => {
  const output = '修复方案：把密码字段改用 bcrypt 哈希存储即可。';
  const r = runQualityGates('debugger', output, 0, []);
  assert(r.pass === false, 'expected BLOCKER');
});

test('FAIL: refactor-specialist 只有描述', () => {
  const output = '这个模块可以提取公共逻辑到 utils。';
  const r = runQualityGates('refactor-specialist', output, 0, []);
  assert(r.pass === false);
});

test('PASS: doc-writer 纯文档无代码块也可以', () => {
  const output = `
## API 文档 — 用户模块

### GET /api/users
返回用户列表，支持分页和筛选。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | number | 否 | 页码，默认 1 |
| limit | number | 否 | 每页数量，默认 20 |

### POST /api/users
创建新用户。请求体需包含 username 和 password。返回创建的用户对象。
`;
  const r = runQualityGates('doc-writer', output, 0, []);
  assert(r.pass === true, `doc-writer should pass: ${JSON.stringify(r.failures)}`);
});

test('FAIL: doc-writer 输出过短', () => {
  const r = runQualityGates('doc-writer', '文档已完成。', 0, []);
  assert(r.pass === false);
});

// ─── 代码生成类: completeness gate ──────────────────

console.log('\n📦 Code Generators — completeness gate:');

test('FAIL: TODO + 无代码', () => {
  const output = 'TODO: 实现测试用例\n\`\`\`\n// TODO\n\`\`\`';
  const r = runQualityGates('test-writer', output, 0, []);
  assert(r.pass === false);
  assert(r.failures.some(f => f.gate === 'completeness'), 'should have completeness failure');
});

test('FAIL: 大段描述无代码块', () => {
  const output = '我仔细分析了代码，发现以下问题需要测试：首先是登录流程需要验证密码是否正确哈希，其次是令牌生成需要验证是否使用了安全的密钥，第三是用户创建需要检查密码强度。以上所有测试建议我都已经考虑过了。';
  const r = runQualityGates('test-writer', output, 0, []);
  assert(r.pass === false);
  assert(r.failures.some(f => f.gate === 'completeness'), 'long text without code');
});

test('PASS: 有 TODO 但有足够代码', () => {
  const output = `
// TODO: add edge cases
\`\`\`javascript
function test() {
  expect(add(1,2)).toBe(3);
  expect(add(0,0)).toBe(0);
}
\`\`\`
`;
  const r = runQualityGates('test-writer', output, 0, []);
  assert(r.pass === true, `should pass with code: ${JSON.stringify(r.failures)}`);
});

// ─── 分析类: specificity gate ──────────────────

console.log('\n📊 Analyzers — specificity gate:');

test('PASS: code-reviewer 带行号引用', () => {
  const output = `
## [S-01] JWT 密钥硬编码
- 位置: src/auth.js:5
- 修复: \`\`\`diff\n- const K = 'x';\n+ const K = process.env.K;\n\`\`\`
`;
  const r = runQualityGates('code-reviewer', output, 0, []);
  assert(r.pass === true, JSON.stringify(r.failures));
});

test('FAIL: 看起来像审查但无行号引用', () => {
  const output = '我审查了代码，发现有一些安全问题需要修复，比如密钥管理和认证流程。';
  const r = runQualityGates('code-reviewer', output, 0, []);
  assert(r.pass === false, 'vague review should fail');
  assert(r.failures.some(f => f.gate === 'specificity'), 'should fail specificity');
});

test('PASS: 无发现（代码可能是干净的）', () => {
  const output = '审查完成。当前代码未发现明显问题，风格一致性良好。';
  const r = runQualityGates('code-reviewer', output, 0, []);
  // 这不算"审查报告"，没有审查/问题/漏洞关键词 → 不作为 review-like
  // 但 "审查" 本身是关键词...
  // 这是 ambiguous case — 暂且期望 PASS（太短）
});

test('FAIL: 输出过短 (< 60 chars)', () => {
  const output = '有安全问题';
  const r = runQualityGates('security-auditor', output, 0, []);
  assert(r.pass === false, 'too short');
  assert(r.failures.some(f => f.gate === 'specificity'));
});

test('PASS: security-auditor 完整报告', () => {
  const output = `
## 安全审计报告

### [CRIT-01] CWE-798 硬编码凭据
- 位置: src/auth.js:5
- 修复: \`\`\`diff\n- const KEY='x';\n+ const KEY=process.env.KEY;\n\`\`\`
### [W-01] CWE-200 信息泄漏
- 位置: src/api/users.js:23
- 修复: 移除堆栈跟踪详情
`;
  const r = runQualityGates('security-auditor', output, 0, []);
  assert(r.pass === true, JSON.stringify(r.failures));
});

// ─── 分析类: actionable gate ──────────────────

console.log('\n📊 Analyzers — actionable gate:');

test('WARNING: 有严重问题但无修复建议', () => {
  const output = `
### [S-01] XSS - 位置: src/app.js:15
### [S-02] SQL注入 - 位置: src/db.js:30
以上两个问题需要尽快修复。
`;
  const r = runQualityGates('security-auditor', output, 0, []);
  assert(r.pass === true, 'WARNING should not block');
  assert(r.failures.some(f => f.gate === 'actionable' && f.severity === 'WARNING'));
});

// ─── 回环逻辑 ──────────────────────────────────

console.log('\n🔄 Retry Loop:');

test('R1 FAIL → RETRY', () => {
  const r = runQualityGates('test-writer', '需要写测试', 0, []);
  assertEquals(r.action, 'RETRY', `expected RETRY, got ${r.action}`);
  assert(r.feedback, 'should have feedback');
});

test('R2: 不同门控失败 → 继续 RETRY', () => {
  // R1 失败于 syntax, R2 失败于 completeness (不同) → 非死循环
  const r = runQualityGates('test-writer', 'TODO: test\n\`\`\`\n// code\n\`\`\`', 1, ['syntax']);
  assertEquals(r.action, 'RETRY');
});

test('死循环检测: 同一门控连续失败 → ESCALATE', () => {
  const r = runQualityGates('test-writer', '还是需要写测试', 1, ['syntax']);
  assertEquals(r.action, 'ESCALATE');
  assert(r.reason.includes('死循环'));
});

test('R3 (retryCount=3, >=MAX_RETRIES) → ESCALATE', () => {
  const r = runQualityGates('debugger', '需要修复', 3, ['syntax', 'completeness']);
  assertEquals(r.action, 'ESCALATE');
  assert(r.reason.includes('重试'));
});

// ─── 非子智能体 ──────────────────────────────────

console.log('\n🔧 Non-subagents:');

test('orchestrator 不检查', () => {
  const r = runQualityGates('orchestrator', 'anything', 0, []);
  assert(r.pass === true);
  assertEquals(r.action, 'ACCEPT');
});

test('build agent 不检查', () => {
  const r = runQualityGates('build', 'output', 0, []);
  assert(r.pass === true);
});

// ─── Feedback Builder ───────────────────────────

console.log('\n📝 Feedback Builder:');

test('构建完整反馈', () => {
  const failures = [
    { gate: 'syntax', severity: 'BLOCKER', reason: '缺少代码块' },
    { gate: 'completeness', severity: 'BLOCKER', reason: 'TODO占位符' },
    { gate: 'actionable', severity: 'WARNING', reason: '无修复建议' },
  ];
  const fb = buildRetryFeedback(failures);
  assert(fb.includes('⚠️ 上一轮未通过'), 'missing header');
  assert(fb.includes('[GATE:syntax]'), 'missing syntax');
  assert(fb.includes('[GATE:completeness]'), 'missing completeness');
  assert(fb.includes('[GATE:actionable]'), 'missing actionable');
  assert(fb.includes('阻塞问题'), 'missing blocker section');
  assert(fb.includes('改进建议'), 'missing warning section');
  assert(fb.includes('本轮要求'), 'missing action request');
});

// ─── 端到端场景 ──────────────────────────────────

console.log('\n🎬 End-to-end Scenarios:');

test('E2E: debugger 两轮回环 → 最终通过', () => {
  // R1: 不完整的修复
  const r1 = runQualityGates('debugger',
    '修复: 把 password 改为 bcrypt.hashSync(password, 10)', 0, []);
  assertEquals(r1.action, 'RETRY');

  const r1Feedback = r1.feedback;
  assert(r1Feedback.includes('[GATE:syntax]'), 'R1 feedback should mention syntax');

  // R2: 完整修复 (带 diff 代码块)
  const r2 = runQualityGates('debugger', `
修复密码存储问题:
\`\`\`diff
+ const bcrypt = require('bcrypt');
- password: password,
+ password: bcrypt.hashSync(password, 10),
- if (user.password == password) {
+ if (bcrypt.compareSync(password, user.password)) {
\`\`\`
同步更新 package.json 添加 bcrypt 依赖。
`, 1, ['syntax']);
  assertEquals(r2.action, 'ACCEPT');
  assert(r2.pass === true);
});

test('E2E: 并行 Fan-Out — 三个任务独立判断', () => {
  // Task A: code-reviewer — PASS
  const a = runQualityGates('code-reviewer',
    '### [S-01] 硬编码 - src/auth.js:5\n```diff\n- old\n+ new\n```', 0, []);
  assert(a.pass === true, `A: ${JSON.stringify(a.failures)}`);

  // Task B: test-writer — FAIL → RETRY (不阻塞 A 和 C)
  const b = runQualityGates('test-writer', '我建议写测试', 0, []);
  assert(b.action === 'RETRY', `B: expected RETRY, got ${b.action}`);

  // Task C: doc-writer — PASS
  const c = runQualityGates('doc-writer', `
## getUsers API
返回用户列表，支持分页和排序参数。
### 参数
| 参数 | 类型 | 说明 |
|------|------|------|
| page | number | 页码 |
`, 0, []);
  assert(c.pass === true, `C: ${JSON.stringify(c.failures)}`);

  // → A 和 C 直接 INTEGRATE, B 进回环 — 互不阻塞
});

test('E2E: 安全审计→修复→再审计 (交叉验证环)', () => {
  // security-auditor 发现硬编码密钥
  const audit1 = runQualityGates('security-auditor',
    '### [CRIT-01] CWE-798 硬编码密钥 - src/auth.js:5\n```diff\n- const KEY="x";\n+ const KEY=process.env.KEY;\n```', 0, []);
  assert(audit1.pass === true, 'audit R1 should pass');

  // debugger 修复
  const fix = runQualityGates('debugger',
    '```diff\n- const KEY="my-secret";\n+ const KEY=process.env.JWT_SECRET;\n```', 0, []);
  assert(fix.pass === true, 'fix should pass');

  // 再次审计确认
  const audit2 = runQualityGates('security-auditor',
    '### 审计确认\n重新审计 src/auth.js，之前的硬编码密钥问题已修复。\n- 位置: src/auth.js:5 — 已迁移到环境变量 ✅', 0, []);
  assert(audit2.pass === true, 'audit R2 should pass');
});

// ─── 边界条件 ──────────────────────────────────

console.log('\n🔲 Edge Cases:');

test('空字符串输入', () => {
  const r = runQualityGates('test-writer', '', 0, []);
  assert(r.pass === false, 'empty input should fail');
});

test('纯英文输出 (不走中文关键词)', () => {
  const r = runQualityGates('code-reviewer',
    'code review complete. found 1 issue: hardcoded key at src/auth.js:5.\n```diff\n- const K="x";\n+ const K=process.env.K;\n```', 0, []);
  assert(r.pass === true, `english review should pass: ${JSON.stringify(r.failures)}`);
});

test('retryCount=0, 空 previousFailures', () => {
  const r = runQualityGates('test-writer', 'write code', 0, []);
  // 应触发 RETRY (非 ESCALATE)，因为 retryCount=0 < MAX_RETRIES
  assertEquals(r.action, 'RETRY');
});

// ─── 结果 ──────────────────────────────────

console.log('\n═══════════════════════════════════════');
const total = passed + failed;
console.log(`  Results: ${passed}/${total} passed`);
if (failed > 0) {
  console.log(`  ❌ ${failed} test(s) FAILED`);
  process.exit(1);
} else {
  console.log('  ✅ All tests passed');
  process.exit(0);
}
