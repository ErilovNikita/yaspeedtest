import pytest_asyncio
from yaspeedtest.client import YaSpeedTest

@pytest_asyncio.fixture
async def ya_client():
    """
    Create YaSpeedTest client with mocked probes
    """
    client = await YaSpeedTest.create()
    return client