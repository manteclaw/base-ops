const { MeshLedger } = require('@meshledger/sdk');

async function main() {
  try {
    console.log('Registering Manteclaw on MeshLedger...');
    const ml = await MeshLedger.register({
      name: 'Manteclaw-v2',
      description: 'Base L2 automation agent — mining, research, and DeFi ops',
      wallet_address: '0xFC56950105883F46a3bB96ac9517A110724F2F27',
      chains: ['base'],
      capabilities: ['python', 'solidity', 'automation', 'research', 'defi']
    });
    console.log('✅ Registered!');
    console.log('Agent ID:', ml.agent_id);
    console.log('API Key:', ml.api_key);
    console.log('Profile URL:', ml.profile_url);
  } catch (err) {
    console.error('❌ Registration failed:', err.message);
    process.exit(1);
  }
}

main();
