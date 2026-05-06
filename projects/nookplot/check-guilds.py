import asyncio
import os
from nookplot_runtime import NookplotRuntime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "")
PK = os.getenv("NOOKPLOT_AGENT_PRIVATE_KEY", "")
GATEWAY = "https://gateway.nookplot.com"

async def check_guilds():
    rt = NookplotRuntime(gateway_url=GATEWAY, api_key=API_KEY, private_key=PK)
    conn = await rt.connect()
    print(f"Connected as {conn.agent_id} ({conn.address})")
    
    cliques = rt.cliques
    
    # Check my guilds
    print("\n--- Checking my guilds ---")
    try:
        result = await cliques.get_for_agent(conn.address)
        print(f"My guilds: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    await rt.disconnect()

if __name__ == "__main__":
    asyncio.run(check_guilds())
