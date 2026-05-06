import { OpenAgent } from '@openagentmarket/nodejs';
import { Contract, parseUnits, parseEther, JsonRpcProvider, Wallet } from 'ethers';
import 'dotenv/config';

async function main() {
  const mnemonic = process.env.MNEMONIC;
  if (!mnemonic || mnemonic.includes("your twelve word")) {
    console.error("❌ Please set a valid MNEMONIC in .env");
    process.exit(1);
  }

  const recipientAddress = process.env.RECIPIENT_ADDRESS || "0x0000000000000000000000000000000000000000";
  if (recipientAddress === "0x0000000000000000000000000000000000000000") {
    console.warn("⚠️  RECIPIENT_ADDRESS not set in .env — payment skill will use zero address");
  }

  const agent = await OpenAgent.create({
    mnemonic,
    env: "production",
    card: {
      name: "Manteclaw",
      description: "Autonomous Litcoiin miner on Base L2. Specializes in crypto automation, research, and Base L2 operations.",
      skills: ["automation","research","base-l2","crypto-mining","python","send_usdc","send_eth","self-healing-api","defi-yield-scan","mcp-security-audit","governance-voting","x402-server"]
    },
    payment: {
      currency: "USDC",
      recipientAddress
    },
  });

  // Derive wallet once for task handlers
  const wallet = Wallet.fromPhrase(mnemonic);
  const provider = new JsonRpcProvider(process.env.BASE_RPC_URL || "https://mainnet.base.org");

  agent.onTask("automation", async (input) => {
    return { message: `Handled automation with ${JSON.stringify(input)}` };
  });

  agent.onTask("research", async (input) => {
    return { message: `Handled research with ${JSON.stringify(input)}` };
  });

  agent.onTask("base-l2", async (input) => {
    return { message: `Handled base-l2 with ${JSON.stringify(input)}` };
  });

  agent.onTask("crypto-mining", async (input) => {
    return { message: `Handled crypto-mining with ${JSON.stringify(input)}` };
  });

  agent.onTask("python", async (input) => {
    return { message: `Handled python with ${JSON.stringify(input)}` };
  });

  // ── Send USDC on Base ──
  const USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
  const USDC_ABI = [
    "function transfer(address to, uint256 amount) returns (bool)",
    "function balanceOf(address owner) view returns (uint256)"
  ];

  agent.onTask("send_usdc", async (input) => {
    const connectedWallet = wallet.connect(provider);
    const usdc = new Contract(USDC_ADDRESS, USDC_ABI, connectedWallet);

    // USDC has 6 decimals
    const amount = parseUnits(input.amount, 6);
    const tx = await usdc.transfer(input.to, amount);
    const receipt = await tx.wait();

    return {
      success: true,
      txHash: receipt.hash,
      chain: "base",
      currency: "USDC",
      amount: input.amount,
      to: input.to
    };
  });

  // ── Send ETH on Base ──
  agent.onTask("send_eth", async (input) => {
    const connectedWallet = wallet.connect(provider);

    const tx = await connectedWallet.sendTransaction({
      to: input.to,
      value: parseEther(input.amount)
    });
    const receipt = await tx.wait();

    return {
      success: true,
      txHash: receipt.hash,
      chain: "base",
      currency: "ETH",
      amount: input.amount,
      to: input.to
    };
  });

  await agent.start();
  console.log(`✅ Daemon running. Agent: ${wallet.address} | Press Ctrl+C to stop`);

  // ── Keep-alive: prevent Node from exiting ──
  setInterval(() => {
    const now = new Date().toISOString();
    console.log(`[${now}] 💓 heartbeat — OpenAgent daemon alive`);
  }, 30000);

  // Also hold stdin to keep event loop active
  process.stdin.resume();
}


// ── Register on-chain (optional) ──
async function registerAgent(agent: any) {
  const result = await agent.register(
    {
      name: "Manteclaw",
      description: "Autonomous Litcoiin miner on Base L2. Specializes in crypto automation, research, and Base L2 operations.",
      image: "https://example.com/avatar.png",
      metadata: {
        skills: ["automation","research","base-l2","crypto-mining","python","send_usdc","send_eth","self-healing-api","defi-yield-scan","mcp-security-audit","governance-voting","x402-server"],
        pricing: { amount: "5.0", currency: "USDC", chain: "base" },
        category: "utility",
        tags: ["openagent"]
      }
    },
    {
      privateKey: process.env.REGISTRATION_PRIVATE_KEY!,
      pinataJwt: process.env.PINATA_JWT!,
    }
  );
  console.log("Registered:", result);
}
main().catch(console.error);
