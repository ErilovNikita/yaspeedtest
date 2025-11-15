"""
Example Script: Modern Asynchronous Probe Runner (Peak Speed Measurement)

This example demonstrates the up-to-date, asynchronous usage of the
`YaSpeedTest` client leveraging the new *peak-speed measurement* methods:
`YaSpeedTest.measure_download_peak()` and `YaSpeedTest.measure_upload_peak()`.

The script initializes a Yandex Speedtest client, fetches available
test probes, and then performs three categories of network measurements:

1. Download Probes — Measures peak download speed (Mbps) using multiple
   server probes in parallel.
2. Latency Probes — Measures average network response time (ms).
3. Upload Probes — Measures peak upload speed (Mbps) across several
   Yandex servers.

Unlike the legacy implementation, this version focuses on real-time
throughput detection rather than average file-transfer rates, providing
more accurate results for short bursts and fast connections.

Usage
-----
Run the script to execute all available probes asynchronously:

    python examples/one_by_one.py

Output
------
Each probe prints its individual peak measurement:

    [Download] {URL}, timeout: {timeout}
    [Download] {URL}, timeout: {timeout}
    [Upload] {URL}, timeout: {timeout}, size: {size}
    [Upload] {URL}, timeout: {timeout}, size: {size}
    [Latency] {URL}

    [Download] 8.00 Mbps
    [Download] 295.19 Mbps
    [Upload] 0.00 Mbps
    [Upload] 149.68 Mbps
    [Latency] 16.55 ms

Notes
-----
- This version uses `YaSpeedTest.measure_download_peak()` and `YaSpeedTest.measure_upload_peak()`,
  which provide more realistic speed values closer to the official
  Yandex Internet Speed Test.
- Intended for testing, diagnostics, and API integration scenarios.
"""

import asyncio
from yaspeedtest.client import YaSpeedTest
from yaspeedtest.types import ProbeModel, ProbesResponse

async def main():
    yaSpeedTestClinet = await YaSpeedTest.create()
    probes:ProbesResponse = yaSpeedTestClinet.probes

    # --- Probes ---
    for probe in probes.download.probes:
        print(f"[Download] {probe.url}, timeout: {probe.timeout}")
    for probe in probes.upload.probes:
        print(f"[Upload] {probe.url}, timeout: {probe.timeout}, size: {probe.size}")
    for probe in probes.latency.probes:
        print(f"[Latency] {probe.url}")
    print()

    # --- Download ---
    download_tasks = []
    for probe in probes.download.probes:
        async def download_task(p:ProbeModel=probe):
            mbps = await yaSpeedTestClinet.measure_download_peak(p.url, p.timeout)
            print(f"[Download] {mbps:.2f} Mbps")
        download_tasks.append(download_task())
    await asyncio.gather(*download_tasks)

    # --- Upload ---
    upload_tasks = []
    for probe in probes.upload.probes:
        async def upload_task(p:ProbeModel=probe):
            mbps = await yaSpeedTestClinet.measure_upload_peak(p.url, p.size, p.timeout)
            print(f"[Upload] {mbps:.2f} Mbps")
        upload_tasks.append(upload_task())
    await asyncio.gather(*upload_tasks)

    # --- Latency ---
    latency_tasks = []
    for probe in probes.latency.probes:
        async def latency_task(p:ProbeModel=probe):
            ms = await yaSpeedTestClinet.measure_latency(p.url, p.timeout)
            print(f"[Latency] {ms:.2f} ms")
        latency_tasks.append(latency_task())
    await asyncio.gather(*latency_tasks)
    print()


if __name__ == "__main__":
    asyncio.run(main())