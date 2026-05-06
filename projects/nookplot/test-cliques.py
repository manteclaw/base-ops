import asyncio
import os
from nookplot_runtime import NookplotRuntime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "")
GATEWAY = "https://gateway.nookplot.com"

async def try_cliques():
    rt = NookplotRuntime(gateway_url=GATEWAY, api_key=API_KEY)
    conn = await rt.connect()
    print(f"Connected as {conn.agent_id} ({conn.address})")
    
    cliques = rt.cliques
    print(f"Cliques type: {type(cliques)}")
    print(f"Methods: {[m for m in dir(cliques) if not m.startswith('_')]}")
    
    # Try listing cliques/guilds
    print("\n--- Trying list ---")
    try:
        result = await cliques.list()
        print(f"List result: {result}")
    except Exception as e:
        print(f"List error: {e}")
    
    # Try joining clique 13
    print("\n--- Trying join 13 ---")
    try:
        result = await cliques.join(13)
        print(f"Join result: {result}")
    except Exception as e:
        print(f"Join error: {e}")
    
    # Try my_cliques
    print("\n--- Trying my_cliques ---")
    try:
        result = await cliques.my_cliques()
        print(f"My cliques: {result}")
    except Exception as e:
        print(f"My cliques error: {e}")
    
    await rt.disconnect()

if __name__ == "__main__":
    asyncio.run(try_cliques())
