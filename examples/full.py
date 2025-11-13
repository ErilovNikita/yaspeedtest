import asyncio
from yaspeedtest.client import YaSpeedTest

async def main():
    ya = await YaSpeedTest().create()
    result = await ya.run(10)
    print(f"Ping: {result.ping_ms:.2f} ms")
    print(f"Download: {result.download_mbps:.2f} Mbps")
    print(f"Upload: {result.upload_mbps:.2f} Mbps")

asyncio.run(main())