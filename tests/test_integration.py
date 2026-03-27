"""
Integration test for Centrifugo proxy authentication
"""
import asyncio
from stock_platform_sdk import create_websocket_handler

async def test_proxy_authentication():
    """Test full flow: connect via proxy with access_key/secret_key"""
    handler = create_websocket_handler(
        access_key="your_test_access_key",
        secret_key="your_test_secret_key",
        strategy_name="test"
    )

    print("Connecting to Centrifugo via proxy...")
    connected = await handler.connect()

    if connected:
        print(f"✓ Connected successfully! UID: {handler.get_uid()}")
        print(f"✓ Channels: {handler.get_channels()}")
        await handler.disconnect()
        return True
    else:
        print("✗ Connection failed")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_proxy_authentication())
    exit(0 if result else 1)
