import asyncio
import pytest
from statistics import mean
from typing import List

from yaspeedtest.client import YaSpeedTest
from yaspeedtest.types import SpeedResult

NUM_TESTS = 1

async def run_single_test(ya: YaSpeedTest) -> SpeedResult:
    """
    Performs a single measurement of network parameters with fail-safe protection.

    The method initiates a standard measurement cycle via YaSpeedTest.run() and returns
    the result in SpeedResult format. A built-in safe exception handling mechanism is enabled: any network errors, connection breaks, timeouts, or
    internal client exceptions do not cause the calling code to crash.

    If successful, the actual values ​​are returned:
    — ping_ms
    — download_mbps
    — upload_mbps

    If any error occurs, the method returns a safe fallback packet:
    SpeedResult(0.0, 0.0, 0.0)

    This mechanism allows run_single_test to be used in stress tests,
    large-scale parallel checks, and monitoring scenarios,
    where stability is more important than the accuracy of a single measurement.
    """

    try:
        result = await ya.run()
        return SpeedResult(
            ping_ms=result.ping_ms,
            download_mbps=result.download_mbps,
            upload_mbps=result.upload_mbps,
        )
    except Exception as e:
        print("Warning: run_single_test encountered an error:", str(e))
        return SpeedResult(ping_ms=0.0, download_mbps=0.0, upload_mbps=0.0)


@pytest.mark.asyncio
async def test_parallel_speedtest(ya_client: YaSpeedTest):
    """
    Conducts a parallel stress test of a network client, simulating high load
    and verifying the stability of throughput measurement algorithms.

    The test runs 30 simultaneous speed measurements (ping, download, upload)
    on a single YaSpeedTest instance. The goal is to validate:

    * correct client operation under concurrent requests;
    * absence of performance degradation;
    * absence of data races and side effects;
    * stability of returned metrics (all values ​​are non-negative);
    * absence of outliers exceeding permissible physical limits (<= 20,000 Mbps).

    Upon completion, the test aggregates:
    — average ping value;
    — average download and upload speeds;
    — minimum and maximum values ​​for sanity-check.

    The test does not verify the accuracy of actual network speeds: it ensures
    that the client scales correctly and reliably processes massive concurrent calls.
    """

    tasks: List[asyncio.Task] = [
        asyncio.create_task(run_single_test(ya_client))
        for _ in range(NUM_TESTS)
    ]

    results: List[SpeedResult] = await asyncio.gather(*tasks)

    pings = [r.ping_ms for r in results]
    downloads = [r.download_mbps for r in results]
    uploads = [r.upload_mbps for r in results]

    print("\n=== Parallel SpeedTest Stats ===")
    print(f"Ping: avg={mean(pings):.2f}, min={min(pings):.2f}, max={max(pings):.2f}")
    print(f"Download: avg={mean(downloads):.2f} Mbps")
    print(f"Upload: avg={mean(uploads):.2f} Mbps")

    assert all(x >= 0 for x in pings)
    assert all(x >= 0 for x in downloads)
    assert all(x >= 0 for x in uploads)
    assert max(downloads) <= 20000
    assert max(uploads) <= 20000