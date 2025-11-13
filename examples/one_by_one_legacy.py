"""
!!! Depricated !!!
Example Script: Asynchronous Probe Runner

This example demonstrates a lower-level, approach to measuring
network performance using the `YaSpeedTest` client. Instead of running
the unified `run()` method, the script directly executes the probe
methods for download, latency, and upload tests individually.

The script fetches the available Yandex test probes, then sequentially:
1. Runs all available download probes to measure transfer time and volume.
2. Executes latency probes to determine network response times.
3. Performs upload tests to measure outgoing bandwidth.

Note:
-----
This example uses the deprecated one-by-one execution model.
It remains useful for debugging, analyzing probe behavior, or verifying
specific endpoints individually.

Usage
-----
Run the script to execute all probes asynchronously:

    python examples/one_by_one_legacy.py

Output
------
Each probe prints its individual result:
    Download probe run: 2 pcs
    [Download] 102400 bytes in 0.05 seconds
    [Download] 52428800 bytes in 1.02 seconds

    Latency probe run: 2 pcs
    [Latency] 1.54 ms
    [Latency] 1.89 ms

    Upload probe run: 2 pcs
    [Upload] 1048576 bytes in 0.55 seconds
    [Upload] 52428800 bytes in 1.47 seconds
"""

import asyncio
from yaspeedtest.client import YaSpeedTest
from yaspeedtest.types import ProbeModel, ProbesResponse

async def main():
    yaSpeedTestClinet = await YaSpeedTest.create()
    probes:ProbesResponse = yaSpeedTestClinet.probes

    # --- Download ---
    print(f'Download probe run: {len(probes.download.probes)} ')
    download_tasks = []
    for probe in probes.download.probes:
        async def download_task(p:ProbeModel=probe):
            secs, bytes_downloaded = await yaSpeedTestClinet.measure_download(p.url, p.timeout)
            print(f"[Download] {bytes_downloaded} bytes in {secs:.2f} seconds")
        download_tasks.append(download_task())
    await asyncio.gather(*download_tasks)
    print()

    # --- Latency ---
    print(f'Latency probe run: {len(probes.latency.probes)} pcs')
    latency_tasks = []
    for probe in probes.latency.probes:
        async def latency_task(p:ProbeModel=probe):
            ms = await yaSpeedTestClinet.measure_latency(p.url, p.timeout)
            print(f"[Latency] {ms:.2f} ms")
        latency_tasks.append(latency_task())
    await asyncio.gather(*latency_tasks)
    print()

    # --- Upload ---
    print(f'Upload probe run: {len(probes.upload.probes)} pcs')
    upload_tasks = []
    for probe in probes.upload.probes:
        async def upload_task(p:ProbeModel=probe):
            secs, bytes_uploaded = await yaSpeedTestClinet.measure_upload(p.url, p.size, p.timeout)
            print(f"[Upload] {bytes_uploaded} bytes in {secs:.2f} seconds")
        upload_tasks.append(upload_task())
    await asyncio.gather(*upload_tasks)


if __name__ == "__main__":
    asyncio.run(main())