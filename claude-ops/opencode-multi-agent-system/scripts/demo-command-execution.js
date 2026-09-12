#!/usr/bin/env node
/**
 * 命令 → Orchestrator → Subagents 执行演示
 *
 * 加载 .opencode/command/*.md 中的命令，模拟 Orchestrator 执行流程。
 * 证明: Workflow 文件 → 可执行命令 → Orchestrator 委托 Subagent
 *
 * 用法: node scripts/demo-command-execution.js [command-name]
 */

const fs = require('fs');
const path = require('path');
const { runQualityGates, buildRetryFeedback } = require('../.opencode/hooks/quality-gate.js');

// ─── 加载命令 ──────────────────────────────────

function loadCommands(dir) {
  const commands = {};
  const cmdDir = path.resolve(dir, '.opencode/command');
  if (!fs.existsSync(cmdDir)) return commands;

  for (const file of fs.readdirSync(cmdDir)) {
    if (!file.endsWith('.md')) continue;
    const content = fs.readFileSync(path.join(cmdDir, file), 'utf8');
    const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!match) continue;

    const frontmatter = {};
    for (const line of match[1].split('\n')) {
      const [k, ...v] = line.split(':');
      if (k && v.length) frontmatter[k.trim()] = v.join(':').trim();
    }

    const name = file.replace('.md', '');
    commands[name] = {
      name,
      description: frontmatter.description || '',
      agent: frontmatter.agent || 'build',
      template: match[2].trim(),
    };
  }
  return commands;
}

// ─── Mock 子智能体调用 ─────────────────────────

let callLog = [];

function mockCallSubagent(agent, prompt) {
  const id = `${agent}#${callLog.filter(c => c.agent === agent).length + 1}`;
  callLog.push({ id, agent, promptLen: prompt.length });

  // 模拟输出 (简化版)
  const outputs = {
    'code-reviewer': `## 审查报告\n### [S-01] 问题 — src/auth.js:5\n\`\`\`diff\n- old\n+ new\n\`\`\`\n`,
    'security-auditor': `## 安全审计\n### [CRIT-01] CWE-798 — src/auth.js:5\n\`\`\`diff\n- const KEY='x';\n+ const KEY=process.env.KEY;\n\`\`\`\n`,
    'doc-writer': `## API 文档\n### POST /api/auth/login\n用户登录，返回 JWT Token。\n\n| 参数 | 类型 | 说明 |\n|------|------|------|\n| username | string | 用户名 |\n| password | string | 密码 |\n`,
    'debugger': `## 根因分析\n- 位置: src/session.js:42\n- 原因: expiresIn 误设为 '5m'\n\`\`\`diff\n- expiresIn: '5m',\n+ expiresIn: '24h',\n\`\`\`\n`,
    'refactor-specialist': `## 重构完成\n\`\`\`diff\n- function old() { ... }\n+ function new() { ... }\n\`\`\`\n所有测试通过 ✅`,
    'test-writer': `## 回归测试\n\`\`\`javascript\ntest('regression', () => { expect(fix).toBeTruthy(); });\n\`\`\`\n\`\`\`bash\nnpm test\n\`\`\``,
  };
  return outputs[agent] || `[${agent}] task completed`;
}

// ─── 执行引擎 ──────────────────────────────────

function executeCommand(command, context = {}) {
  console.log(`\n═══════════════════════════════════════`);
  console.log(`  🎯 执行命令: /${command.name}`);
  console.log(`  📋 Agent: ${command.agent}`);
  console.log(`  📝 ${command.description}`);
  console.log(`═══════════════════════════════════════\n`);

  // 解析模板中的步骤
  const template = command.template;
  const steps = [];

  // 提取步骤中的子智能体名称
  // 匹配格式: **agent-name** 或 "委托 agent-name 子智能体"
  const agentRefs = [];

  // 格式1: **agent-name**
  const boldRefs = template.match(/\*\*([a-z-]+)\*\*/g);
  if (boldRefs) {
    for (const ref of boldRefs) {
      agentRefs.push(ref.replace(/\*\*/g, ''));
    }
  }

  // 格式2: "委托 xxx 子智能体"
  const delegateRefs = template.matchAll(/委托\s+([a-z-]+)\s+子智能体/g);
  for (const match of delegateRefs) {
    agentRefs.push(match[1]);
  }

  const seen = new Set();
  for (const name of agentRefs) {
    if (!seen.has(name)) {
      seen.add(name);
      steps.push({ agent: name, description: '' });
    }
  }

  // 判断执行模式
  const isParallel = template.includes('并行') || template.includes('Fan-Out');
  const mode = isParallel ? 'parallel' : 'serial';

  console.log(`  [ANALYZE] 解析命令模板:`);
  console.log(`    模式: ${mode}`);
  console.log(`    步骤: ${steps.map(s => s.agent).join(' → ')}`);
  console.log(`    主控: ${command.agent}\n`);

  if (mode === 'parallel') {
    console.log('  ⚡ [DELEGATE] Fan-Out 并行:\n');
    const results = [];

    for (const step of steps) {
      console.log(`  📌 ${step.agent} ← 从命令模板提取 prompt`);
      let output = mockCallSubagent(step.agent, step.description);

      // 质量门控
      const gate = runQualityGates(step.agent, output, 0, []);
      let retries = 1;

      while (!gate.pass && gate.action === 'RETRY' && retries <= 2) {
        console.log(`     🔄 RETRY (${gate.failures.map(f => f.gate).join(',')})`);
        output = mockCallSubagent(step.agent, step.description);
        const nextGate = runQualityGates(step.agent, output, retries, gate.failures.map(f => f.gate));
        if (nextGate.pass || nextGate.action === 'ESCALATE') {
          results.push({ step, output, gate: nextGate, retries: retries + 1 });
          break;
        }
        retries++;
      }

      if (gate.pass) {
        console.log(`     ✅ PASS (1 轮)`);
        results.push({ step, output, gate, retries: 1 });
      } else if (retries > 2) {
        console.log(`     🚨 ESCALATE after ${retries} retries`);
        results.push({ step, output, gate, retries, escalated: true });
      }
    }

    console.log(`\n  [INTEGRATE] 汇总 ${results.length} 个结果`);
    const allOk = results.every(r => r.gate && r.gate.pass);
    const totalRetries = results.reduce((s, r) => s + r.retries - 1, 0);
    console.log(`    状态: ${allOk ? '✅ 全部通过' : '⚠️ 有失败'}`);
    console.log(`    重试: ${totalRetries} 次`);
    return { command, mode, results, allOk, totalRetries };

  } else {
    console.log('  🔗 [DELEGATE] 串行执行:\n');
    const results = [];

    for (const step of steps) {
      console.log(`  📌 ${step.agent} ← 从命令模板提取 prompt`);
      let output = mockCallSubagent(step.agent, step.description);

      const gate = runQualityGates(step.agent, output, 0, []);
      let retries = 1;

      while (!gate.pass && gate.action === 'RETRY' && retries <= 2) {
        console.log(`     🔄 RETRY (${gate.failures.map(f => f.gate).join(',')})`);
        output = mockCallSubagent(step.agent, step.description);
        const nextGate = runQualityGates(step.agent, output, retries, gate.failures.map(f => f.gate));
        if (nextGate.pass || nextGate.action === 'ESCALATE') {
          results.push({ step, output, gate: nextGate, retries: retries + 1 });
          break;
        }
        retries++;
      }

      if (gate.pass) {
        console.log(`     ✅ PASS\n`);
        results.push({ step, output, gate, retries: 1 });
      } else if (results.filter(r => r.escalated).length > 0) {
        console.log(`     ⛔ 前序步骤失败，串行中止\n`);
        break;
      }
    }

    console.log(`  [INTEGRATE] 汇总 ${results.length}/${steps.length} 个步骤`);
    const allOk = results.every(r => r.gate && r.gate.pass);
    const totalRetries = results.reduce((s, r) => s + r.retries - 1, 0);
    console.log(`    状态: ${allOk ? '✅ 全部通过' : '⚠️ 有失败'}`);
    console.log(`    重试: ${totalRetries} 次`);
    return { command, mode, results, allOk, totalRetries };
  }
}

// ─── MAIN ──────────────────────────────────────

console.log('═══════════════════════════════════════════');
console.log('  🧠 命令 → Orchestrator → Subagents');
console.log('═══════════════════════════════════════════\n');

// 加载命令文件
const repoDir = path.resolve(__dirname, '..');
const commands = loadCommands(repoDir);

console.log('📂 从 .opencode/command/*.md 加载命令:\n');
for (const [name, cmd] of Object.entries(commands)) {
  console.log(`  /${name} → ${cmd.agent} | ${cmd.description}`);
}

// 执行所有命令（演示）
const results = [];
for (const [name, cmd] of Object.entries(commands)) {
  const result = executeCommand(cmd);
  results.push(result);
}

// ─── 总结 ──────────────────────────────────────

console.log('\n\n═══════════════════════════════════════════');
console.log('  📊 所有命令执行总结');
console.log('═══════════════════════════════════════════\n');

for (const r of results) {
  const icon = r.allOk ? '✅' : '⚠️';
  console.log(`  ${icon} /${r.command.name}`);
  console.log(`     模式: ${r.mode}, 步骤: ${r.results.length}, 重试: ${r.totalRetries}`);
  console.log(`     主控: ${r.command.agent}`);
  for (const s of r.results) {
    const stepIcon = s.gate && s.gate.pass ? '  ✅' : '  ❌';
    console.log(`${stepIcon} ${s.step.agent} (${s.retries}轮)`);
  }
  console.log();
}

console.log('───────────────────────────────────────────');
console.log('  调用链:');
console.log('  /command → orchestrator (主Agent) → subagent → quality gate');
console.log('═══════════════════════════════════════════');
