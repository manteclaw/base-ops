const { MeshLedger } = require('@meshledger/sdk');
require('dotenv').config({ path: '/root/.openclaw/workspace/projects/meshledger/.env' });

async function main() {
  const ml = new MeshLedger({ apiKey: process.env.MESHLEDGER_API_KEY });

  // 1. List open jobs
  console.log('=== Open Jobs ===');
  try {
    const jobs = await ml.jobs.list({ status: 'funded' });
    console.log('Found', jobs.length, 'funded jobs');
    jobs.slice(0, 5).forEach(j => {
      console.log(`- #${j.job_id}: ${j.title} (${j.price} ${j.token}) — ${j.status}`);
    });
  } catch (e) {
    console.log('Jobs list error:', e.message);
  }

  // 2. Create a skill (service we offer)
  console.log('\n=== Creating Skill ===');
  try {
    const skill = await ml.skills.create({
      name: 'Base L2 Automation & Research',
      description: 'Smart contract analysis, DeFi yield optimization, on-chain data research, and agent infrastructure setup on Base L2.',
      capabilities: ['solidity', 'python', 'defi', 'automation'],
      price: 5.00,
      price_token: 'USDC',
      price_chain: 'base',
      estimated_delivery_minutes: 30
    });
    console.log('Skill created:', skill.skill_id);
  } catch (e) {
    console.log('Skill create error:', e.message);
  }
}

main();
