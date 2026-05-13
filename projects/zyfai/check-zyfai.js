const { ZyfaiSDK, getSupportedChainIds } = require("@zyfai/sdk");

async function main() {
  const apiKey = process.env.ZYFAI_API_KEY || "zyfai_your_api_key_here";
  const privateKey = process.env.PRIVATE_KEY || "0x" + require("crypto").randomBytes(32).toString("hex");
  const userAddress = process.env.USER_ADDRESS || "0x8b8AAC89E101b77E5A917278120151FC496e5c39";
  const chainId = 8453; // Base

  const sdk = new ZyfaiSDK(apiKey);

  try {
    console.log("🔍 Checking Zyfai setup for wallet:", userAddress);
    console.log("📋 Supported chains:", getSupportedChainIds());

    // Check smart wallet address (read-only, no auth needed)
    const walletInfo = await sdk.getSmartWalletAddress(userAddress, chainId);
    console.log("🏦 Safe Address:", walletInfo.address);
    console.log("✅ Is Deployed:", walletInfo.isDeployed);

    // Get available protocols
    const protocols = await sdk.getAvailableProtocols(chainId);
    console.log("\n📊 Available Protocols on Base:");
    protocols.protocols.forEach((p) => {
      console.log(`  - ${p.name} (${p.type}) — ${p.pools?.length || 0} pools`);
    });

    // Get opportunities
    const conservative = await sdk.getConservativeOpportunities(chainId, "USDC");
    console.log("\n💰 Conservative Opportunities:");
    conservative.data.slice(0, 5).forEach((o) => {
      console.log(`  - ${o.protocolName} — ${o.apy}% APY`);
    });

    // Get TVL
    const tvl = await sdk.getSdkKeyTVL ? await sdk.getSdkKeyTVL() : null;
    if (tvl) {
      console.log("\n📈 Total TVL:", tvl.totalTvl);
    }

  } catch (err) {
    console.error("❌ Error:", err.message);
    if (err.message.includes("API key")) {
      console.log("\n⚠️  Need a Zyfai API key from https://sdk.zyf.ai/");
    }
  }
}

main();
