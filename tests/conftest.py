import pytest
import pytest_asyncio
from aioresponses import aioresponses
from yaspeedtest.client import YaSpeedTest
from yaspeedtest.types import ProbesResponse, ProbesList, ProbeModel

@pytest.fixture
def mock_probes():
    """
    Mock object similar to Yandex /internet/api/v0/get-probes response
    """
    latency_probe = ProbeModel(url="https://mock/latency", timeout=5)
    download_probe = ProbeModel(url="https://mock/download", timeout=5)
    upload_probe = ProbeModel(url="https://mock/upload", size=1024, timeout=5)
    
    return ProbesResponse(
        mid="mock-mid",
        lid=["mock-lid"],
        latency=ProbesList(probes=[latency_probe]),
        download=ProbesList(probes=[download_probe]),
        upload=ProbesList(probes=[upload_probe]),
        perfLog="mock-perflog"
    )


@pytest_asyncio.fixture
async def ya_client(mock_probes):
    """
    Create YaSpeedTest client with mocked probes
    """
    client = await YaSpeedTest.create()
    client.probes = mock_probes
    return client


@pytest.fixture
def mock_aioresponse():
    """
    Context manager for mocking aiohttp calls.
    """
    with aioresponses() as m:
        yield m