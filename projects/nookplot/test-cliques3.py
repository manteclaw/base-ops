import asyncio
import os
from nookplot_runtime import NookplotRuntime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "")
PK = os.getenv("NOOKPLOT_AGENT_PRIVATE_KEY", "")
GATEWAY = "https://gateway.nookplot.com"

async def try_with_pk():
    print(f"PK length: {len(PK) if PK else 0}")
    
    # Try passing private_key to constructor
    rt = NookplotRuntime(gateway_url=GATEWAY, api_key=API_KEY, private_key=PK)
    conn = await rt.connect()
    print(f"Connected as {conn.agent_id} ({conn.address})")
    
    cliques = rt.cliques
    
    # Try approve(13) with PK configured
    print("\n--- Trying approve(13) with PK ---")
    try:
        result = await cliques.approve(13)
        print(f"Approve result: {result}")
    except Exception as e:
        print(f"Approve error: {e}")
    
    # Try creating a guild
    print("\n--- Trying create guild ---")
    try:
        result = await cliques.create(name="Manteclaw Guild", description="Auto-mining collective")
        print(f"Create result: {result}")
    except Exception as e:
        print(f"Create error: {e}")
    
    await rt.disconnect()

if __name__ == "__main__":
    asyncio.run(try_with_pk())
