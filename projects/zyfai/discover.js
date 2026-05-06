const { ZyfaiSDK, getSupportedChainIds } = require("@zyfai/sdk");

async function main() {
  // We need an API key for even read-only operations
  const apiKey = process.env.ZYFAI_API_KEY;
  if (!apiKey) {
    console.log("❌ No ZYFAI_API_KEY found in environment");
    console.log("   Get one from: https://sdk.zyf.ai/");
    process.exit(1);
  }

  const userAddress = "0xC4Cf88b691D9b820040d861954d32e0C5f4538b7";
  const chainId = 8453; // Base

  const sdk = new ZyfaiSDK(apiKey);

  try {
    console.log("🔍 Zyfai Discovery for wallet:", userAddress);
    console.log("📋 Supported chains:", getSupportedChainIds());

    // Check smart wallet address (read-only, no auth needed)
    const walletInfo = await sdk.getSmartWalletAddress(userAddress, chainId);
    console.log("\n🏦 Safe Address:", walletInfo.address);
    console.log("✅ Is Deployed:", walletInfo.isDeployed);

    // Get available protocols
    const protocols = await sdk.getAvailableProtocols(chainId);
    console.log("\n📊 Available Protocols on Base:");
    protocols.protocols.forEach((p) => {
      console.log(`  - ${p.name} (${p.type}) — ${p.pools?.length || 0} pools, strategies: ${p.strategies?.join(", ") || "n/a"}`);
    });

    // Get opportunities
    const conservative = await sdk.getConservativeOpportunities(chainId, "USDC");
    console.log("\n💰 Conservative USDC Opportunities:");
    conservative.data.slice(0, 5).forEach((o) => {
      console.log(`  - ${o.protocolName} — ${o.apy}% APY (${o.poolName})`);
    });

    // Get aggressive opportunities too
    const aggressive = await sdk.getAggressiveOpportunities(chainId, "USDC");
    console.log("\n🔥 Aggressive USDC Opportunities:");
    aggressive.data.slice(0, 3).forEach((o) => {
      console.log(`  - ${o.protocolName} — ${o.apy}% APY (${o.poolName})`);
    });

    // Get TVL
    try {
      const tvl = await sdk.getSdkKeyTVL();
      console.log("\n📈 Zyfai Total TVL:", tvl.totalTvl);
    } catch (e) {
      console.log("\n📈 TVL: (SDK key method not available with this key type)");
    }

    // Get smart wallet by EOA
    const sw = await sdk.getSmartWalletByEOA(userAddress);
    console.log("\n🔗 Smart Wallet by EOA:");
    console.log("  EOA:", sw.eoa);
    console.log("  Smart Wallet:", sw.smartWallet);
    console.log("  Chains:", sw.chains);

  } catch (err) {
    console.error("\n❌ Error:", err.message);
    if (err.response?.data) {
      console.error("   Details:", JSON.stringify(err.response.data, null, 2));
    }
  }
}

main();
