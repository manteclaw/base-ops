import asyncio
import os
from nookplot_runtime import NookplotRuntime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "")
PK = os.getenv("NOOKPLOT_AGENT_PRIVATE_KEY", "")
GATEWAY = "https://gateway.nookplot.com"

async def try_join_guild():
    rt = NookplotRuntime(gateway_url=GATEWAY, api_key=API_KEY)
    conn = await rt.connect()
    print(f"Connected as {conn.agent_id} ({conn.address})")
    
    # Try various guild methods
    methods_to_try = [
        "list_guilds",
        "my_guilds", 
        "join_guild",
        "request_guild_membership"
    ]
    
    guild_obj = getattr(rt, "guild", None)
    if guild_obj:
        print(f"Guild object found: {type(guild_obj)}")
        print(f"Available methods: {[m for m in dir(guild_obj) if not m.startswith('_')]}")
        
        for method_name in methods_to_try:
            if hasattr(guild_obj, method_name):
                print(f"\nTrying {method_name}...")
                try:
                    method = getattr(guild_obj, method_name)
                    if method_name == "join_guild":
                        result = await method(13)
                    else:
                        result = await method()
                    print(f"  Result: {result}")
                except Exception as e:
                    print(f"  Error: {e}")
    else:
        print("No guild object found on runtime")
    
    await rt.disconnect()

if __name__ == "__main__":
    asyncio.run(try_join_guild())
