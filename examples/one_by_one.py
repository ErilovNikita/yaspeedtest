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