import pytest
from unittest.mock import AsyncMock, patch
from yaspeedtest.client import YaSpeedTest
from yaspeedtest.types import ProbesResponse, ProbeModel, SpeedResult, ProbesList

@pytest.mark.asyncio
async def test_run_basic_flow():
    ya_client = await YaSpeedTest.create()

    probe_download = ProbeModel(url="https://mock/download", timeout=1, size=1024*1024)
    probe_upload = ProbeModel(url="https://mock/upload", timeout=1, size=1024)
    probe_latency = ProbeModel(url="https://mock/latency", timeout=1, size=0)

    ya_client.probes = ProbesResponse(
        mid="test-mid",
        lid=["test-lid"],
        download=ProbesList(probes=[probe_download]),
        upload=ProbesList(probes=[probe_upload]),
        latency=ProbesList(probes=[probe_latency]),
        perfLog="test-perflog"
    )

    with patch.object(ya_client, "measure_latency", new=AsyncMock(return_value=10.0)), \
         patch.object(ya_client, "measure_download_peak", new=AsyncMock(return_value=0.0)), \
         patch.object(ya_client, "measure_upload_peak", new=AsyncMock(return_value=20.0)):
        result: SpeedResult = await ya_client.run()

    assert isinstance(result, SpeedResult)
    assert result.ping_ms == 10.0
    assert result.download_mbps == 0.0
    assert result.upload_mbps == 20.0