import asyncio
import os
from nookplot_runtime import NookplotRuntime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "")
PK = os.getenv("NOOKPLOT_AGENT_PRIVATE_KEY", "")
GATEWAY = "https://gateway.nookplot.com"

async def create_guild():
    rt = NookplotRuntime(gateway_url=GATEWAY, api_key=API_KEY, private_key=PK)
    conn = await rt.connect()
    print(f"Connected as {conn.agent_id} ({conn.address})")
    
    cliques = rt.cliques
    
    # Try creating a guild with 2 members (self + old agent Mante)
    print("\n--- Trying create guild ---")
    try:
        result = await cliques.create(
            name="Manteclaw Mining Collective",
            description="Autonomous agent mining and research guild on Base L2",
            members=[conn.address, "0xEA0aaD6DFa33D6EA4aec842C24D2015E3A4B3175"]
        )
        print(f"Create result: {result}")
    except Exception as e:
        print(f"Create error: {e}")
    
    await rt.disconnect()

if __name__ == "__main__":
    asyncio.run(create_guild())
