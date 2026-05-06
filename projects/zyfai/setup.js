const { ZyfaiSDK } = require("@zyfai/sdk");
const { createWalletClient, http } = require("viem");
const { base } = require("viem/chains");
const { privateKeyToAccount } = require("viem/accounts");

const API_KEY = process.env.ZYFAI_API_KEY || "";
const MNEMONIC = "state insane tooth rain scan march liberty man sick category noble divorce";
const USER_ADDRESS = "0xC4Cf88b691D9b820040d861954d32e0C5f4538b7";
const CHAIN_ID = 8453;

async function setup() {
  console.log("🔧 Setting up Zyfai for wallet:", USER_ADDRESS);
  
  const sdk = new ZyfaiSDK({ apiKey: API_KEY, referralSource: "openclaw-skill" });
  
  // Derive private key from mnemonic
  const { mnemonicToAccount } = require("viem/accounts");
  const derivedAccount = mnemonicToAccount(MNEMONIC);
  const privateKey = derivedAccount.privateKey;
  
  console.log("   Derived address:", derivedAccount.address);
  
  // Connect using private key string - need to derive properly
  const hdKey = derivedAccount.getHdKey();
  const rawPrivateKey = "0x" + Buffer.from(hdKey.privateKey).toString("hex");
  
  console.log("🔗 Connecting account...");
  await sdk.connectAccount(rawPrivateKey, CHAIN_ID);
  console.log("✅ Connected");
  
  // Check Safe
  console.log("\n🏦 Checking Safe subaccount...");
  const wallet = await sdk.getSmartWalletAddress(USER_ADDRESS, CHAIN_ID);
  console.log("   Safe Address:", wallet.address);
  console.log("   Deployed:", wallet.isDeployed);
  
  if (!wallet.isDeployed) {
    console.log("\n🚀 Deploying Safe (conservative strategy)...");
    try {
      const result = await sdk.deploySafe(USER_ADDRESS, CHAIN_ID, "conservative");
      console.log("   ✅ Deployed:", result.safeAddress);
      console.log("   Tx Hash:", result.txHash);
    } catch (e) {
      console.log("   ❌ Deploy failed:", e.message);
    }
  }
  
  // Create session key
  console.log("\n🔑 Creating session key...");
  try {
    const session = await sdk.createSessionKey(USER_ADDRESS, CHAIN_ID);
    console.log("   Session created:", session.sessionKeyAddress || session.alreadyActive);
  } catch (e) {
    console.log("   ❌ Session key failed:", e.message);
  }
  
  // Get user details
  console.log("\n👤 Getting user details...");
  try {
    const user = await sdk.getUserDetails();
    console.log("   Smart Wallet:", user.smartWallet);
    console.log("   Has Active Session:", user.hasActiveSessionKey);
    console.log("   Strategy:", user.strategy);
    console.log("   Chains:", user.chains);
  } catch (e) {
    console.log("   ❌ User details failed:", e.message);
  }
  
  // Get positions
  console.log("\n📊 Getting positions...");
  try {
    const positions = await sdk.getPositions(USER_ADDRESS, CHAIN_ID);
    console.log("   Positions count:", positions.positions?.length || 0);
  } catch (e) {
    console.log("   ❌ Positions failed:", e.message);
  }
  
  // Get APY
  console.log("\n💰 Getting APY data...");
  try {
    const apy = await sdk.getAPYPerStrategy(false, 7, "conservative", 8453, "USDC");
    console.log("   7d Conservative USDC APY:", apy.data[0]?.average_apy, "%");
  } catch (e) {
    console.log("   ❌ APY failed:", e.message);
  }
  
  // Get protocols
  console.log("\n📋 Available protocols:");
  try {
    const protocols = await sdk.getAvailableProtocols(CHAIN_ID);
    protocols.protocols.forEach(p => {
      console.log(`   - ${p.name} (${p.type})`);
    });
  } catch (e) {
    console.log("   ❌ Protocols failed:", e.message);
  }
  
  await sdk.disconnectAccount();
  console.log("\n✅ Setup complete");
}

setup().catch(console.error);
