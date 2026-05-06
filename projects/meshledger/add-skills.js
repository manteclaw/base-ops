const { MeshLedger } = require('@meshledger/sdk');
require('dotenv').config({ path: '/root/.openclaw/workspace/projects/meshledger/.env' });

const skills = [
  {
    name: 'Self-Healing API Executor',
    description: 'Drop-in retry with circuit breaker, exp backoff, jitter. Survives flaky APIs.',
    capabilities: ['automation', 'retry', 'python'],
    price: 3.00,
    price_token: 'USDC',
    price_chain: 'base',
    estimated_delivery_minutes: 15
  },
  {
    name: 'DeFi Yield Scanner',
    description: 'Real-time Base L2 USDC yield aggregation. 93 pools monitored.',
    capabilities: ['defi', 'yield', 'base', 'scanner'],
    price: 2.00,
    price_token: 'USDC',
    price_chain: 'base',
    estimated_delivery_minutes: 10
  },
  {
    name: 'MCP Security Audit',
    description: 'Weekly MCP server vulnerability scanner. Huntr-compatible reports.',
    capabilities: ['security', 'mcp', 'audit', 'bug-bounty'],
    price: 10.00,
    price_token: 'USDC',
    price_chain: 'base',
    estimated_delivery_minutes: 60
  }
];

async function main() {
  const ml = new MeshLedger({ apiKey: process.env.MESHLEDGER_API_KEY });

  console.log('=== Creating Skills on MeshLedger ===');
  for (const skill of skills) {
    try {
      const created = await ml.skills.create(skill);
      console.log('✅ Created:', skill.name, '| ID:', created.skill_id);
    } catch (e) {
      console.log('❌ Failed:', skill.name, '| Error:', e.message);
    }
  }
}

main();
