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
    
    # Try get(13)
    print("\n--- Trying get(13) ---")
    try:
        result = await cliques.get(13)
        print(f"Get result: {result}")
    except Exception as e:
        print(f"Get error: {e}")
    
    # Try propose to join guild 13
    print("\n--- Trying propose(13) ---")
    try:
        result = await cliques.propose(13)
        print(f"Propose result: {result}")
    except Exception as e:
        print(f"Propose error: {e}")
    
    # Try approve(13) - maybe we're already invited
    print("\n--- Trying approve(13) ---")
    try:
        result = await cliques.approve(13)
        print(f"Approve result: {result}")
    except Exception as e:
        print(f"Approve error: {e}")
    
    # Try get_for_agent
    print("\n--- Trying get_for_agent ---")
    try:
        result = await cliques.get_for_agent(conn.address)
        print(f"Get for agent result: {result}")
    except Exception as e:
        print(f"Get for agent error: {e}")
    
    await rt.disconnect()

if __name__ == "__main__":
    asyncio.run(try_cliques())
