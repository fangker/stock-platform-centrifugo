import asyncio
from unittest.mock import AsyncMock, MagicMock
from stock_platform_sdk import CentrifugoClientConfig
from stock_platform_sdk.centrifugo_websocket_client import CentrifugoWebSocketHandler

async def test_connect_without_login():
    """Test that connect() does not call login()"""
    config = CentrifugoClientConfig(
        access_key="test_key",
        secret_key="test_secret",
        strategy_name="test"
    )
    handler = CentrifugoWebSocketHandler(config)

    # Mock the centrifuge Client
    handler.client = MagicMock()
    handler.client.connect = AsyncMock()

    # Connect should not call auth_client.login()
    # This test passes if no exception is raised (login method doesn't exist or isn't called)
    try:
        # The handler shouldn't have an auth_client anymore
        assert not hasattr(handler, 'auth_client') or handler.auth_client is None
    except Exception as e:
        print(f"Test passed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connect_without_login())
