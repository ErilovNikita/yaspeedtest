import pytest
from yaspeedtest.client import YaSpeedTest

@pytest.mark.asyncio
async def test_client_creation():
    client = await YaSpeedTest.create()
    assert client is not None
    assert isinstance(client.DEFAULT_HEADERS, dict)
    assert client.base_url.startswith("https://")