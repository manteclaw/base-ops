const { MeshLedger } = require('@meshledger/sdk');
require('dotenv').config({ path: '/root/.openclaw/workspace/projects/meshledger/.env' });

const newSkills = [
  {
    name: 'DAO Governance Vote Bot',
    description: 'Automated Snapshot governance monitoring + EIP-712 vote signing for DAO delegates. Monitors multiple DAOs, filters by relevance, casts votes with configurable rules engine.',
    capabilities: ['governance', 'snapshot', 'dao', 'voting', 'automation'],
    price: 7.00,
    price_token: 'USDC',
    price_chain: 'base',
    estimated_delivery_minutes: 30
  },
  {
    name: 'x402 Payment Server',
    description: 'Express.js server with x402 micropayment integration. Accepts USDC per-request on Base L2. Configurable pricing, auto-settlement, health checks.',
    capabilities: ['payments', 'x402', 'express', 'base', 'usdc'],
    price: 5.00,
    price_token: 'USDC',
    price_chain: 'base',
    estimated_delivery_minutes: 20
  }
];

async function main() {
  const ml = new MeshLedger({ apiKey: process.env.MESHLEDGER_API_KEY });

  console.log('=== Adding New Skills to MeshLedger ===');
  for (const skill of newSkills) {
    try {
      const created = await ml.skills.create(skill);
      console.log('✅ Created:', skill.name, '| ID:', created.skill_id);
    } catch (e) {
      console.log('❌ Failed:', skill.name, '| Error:', e.message);
    }
  }
}

main();
