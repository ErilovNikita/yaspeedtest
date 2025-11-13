"""
Example Script: Yandex Speed Fully Test

This example demonstrates how to use the asynchronous `YaSpeedTest` client
to measure network performance metrics including ping, download speed, and
upload speed.

The test automatically retrieves the available Yandex probe servers,
performs latency checks, measures transfer rates, and returns a summarized
`YaSpeedTest.SpeedResult` object.

Usage
-----
Simply run the script to execute a full asynchronous speed test:z

    python examples/full.py

Output
------
Displays the measured latency, download, and upload speeds in the console:

    Ping: 1.34 ms
    Download: 985.67 Mbps
    Upload: 743.21 Mbps
"""

import asyncio
from yaspeedtest.client import YaSpeedTest

async def main():
    ya = await YaSpeedTest().create()
    result = await ya.run()
    print(f"Ping: {result.ping_ms:.2f} ms")
    print(f"Download: {result.download_mbps:.2f} Mbps")
    print(f"Upload: {result.upload_mbps:.2f} Mbps")

asyncio.run(main())