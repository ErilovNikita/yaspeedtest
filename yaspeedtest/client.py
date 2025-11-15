import time
import statistics
import asyncio
import aiohttp
from typing import Tuple, Deque
from collections import deque

from yaspeedtest.types import YandexAPIError, ProbesResponse, SpeedResult, ProbeModel

class YaSpeedTest:
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 OPR/72.0.3815.459",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer" : "https://yandex.ru/internet",
        "sec-ch-ua" : "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
        "Sec-Fetch-Mode" : "cors",
        "Sec-Fetch-Dest" : "empty",
        "sec-fetch-site" : "cross-site"
    }
    
    def __init__(self):
        """
        Initialize the Yandex Speedtest client.
        """
        self.base_url: str = "https://yandex.ru".rstrip("/")
        self.headers: dict = self.DEFAULT_HEADERS.copy()
        self.probes: ProbesResponse = None
        self.mid: str = None
        self.lid: str = None
    
    @classmethod
    async def create(cls):
        self = cls()
        await self.__start_proccess()
        return self

    def __compute_peak_from_samples(
        self,
        samples: Deque[Tuple[float, int]],
        window: float = 1.0,
        min_window: float = 0.05,
        warmup_skip: float = 0.15,
        cap_mbps: float = 2500.0,
    ) -> float:
        """
        Calculates the actual peak throughput based on a sliding window with adaptive window duration selection.

        The algorithm takes into account the characteristics of high-speed links:
            - skips the link warmup;
            - adaptively reduces the window if this results in higher throughput;
            - correctly handles window boundaries;
            - eliminates the underperformance typical of a fixed window.

        Parameters
        ----------
        `samples` : Deque[Tuple[float, int]]
            A sequence of samples (timestamp, bytes) collected during data loading or unloading.
        `window` : float
            Maximum window size in seconds (usually 1 second).
        `min_window` : float
            Minimum window length. The smaller the value, the more accurate the peak, but the more sensitive it is to noise.
        `warmup_skip` : float
            Skips the initial part of the sample (in seconds) to eliminate the cold start effect. Typically 30–70 ms.
        `cap_mbps` : float
            Upper limit for the result (anti-artifact).

        Returns
        -------
        float
            Peak data transfer rate in megabits per second.
        """

        # Normalize timestamps
        base_ts = samples[0][0]
        normalized = [(ts - base_ts, size) for ts, size in samples]

        # Drop warmup
        normalized = [(ts, size) for ts, size in normalized if ts >= warmup_skip]
        if not normalized:
            return 0.0

        arr = normalized
        n = len(arr)

        # ===== Anti-artifact filter #1: remove impossible bursts =====
        # If delta_t is tiny and bytes are large => burst
        filtered = []
        last_ts = arr[0][0]
        last_size = arr[0][1]

        # IDE Dummy fix
        last_size = last_size

        for ts, size in arr[1:]:
            dt = ts - last_ts
            if dt > 0:
                gbps = (size * 8) / dt / 1_000_000_000
                if gbps < 5.0:  # >5 Gbps == suspicious
                    filtered.append((ts, size))
            last_ts, last_size = ts, size

        if len(filtered) < 3:
            filtered = arr  # fallback if overfiltered

        arr = filtered
        n = len(arr)

        peak_candidates = []

        # Sliding window
        i = 0
        j = 0
        total_bytes = 0

        # Hard minimum window to avoid bursts
        hard_min_window = 0.08  # 80 ms

        while i < n:
            start_ts = arr[i][0]

            # expand window
            while j < n and arr[j][0] - start_ts <= window:
                total_bytes += arr[j][1]
                j += 1

            # compute throughput for multiple subwindows
            for k in range(i + 1, j):
                duration = arr[k][0] - start_ts

                # apply minimum window constraints
                if duration < hard_min_window:
                    continue
                if duration < min_window:
                    continue

                mbps = (total_bytes * 8) / duration / 1_000_000
                peak_candidates.append(mbps)

            total_bytes -= arr[i][1]
            i += 1

        if not peak_candidates:
            return 0.0

        # ===== Anti-artifact filter #2: trimmed peak =====
        values = sorted(peak_candidates)
        # drop top 10% spikes
        cutoff = max(1, int(len(values) * 0.1))
        trimmed = values[:-cutoff] if len(values) > 10 else values

        peak = max(trimmed)

        # ===== Anti-artifact filter #3: physical upper cap =====
        return min(peak, cap_mbps)
    
    async def __start_proccess(self) -> None:
        """
        Initialize the measurement process by fetching probes from the API.

        This method performs a GET request to the Yandex Internet Meter endpoint
        to retrieve available probes. It updates the session headers with any
        headers returned by the server and stores the parsed probes data.

        Steps:
            1. Sends a GET request to the probes endpoint.
            2. Raises `YandexAPIError` if the request fails.
            3. Updates the session headers with returned headers.
            4. Parses the JSON response into a `ProbesResponse` object.
            5. Sets `self.mid` and `self.lid` based on the received probes.
        """
        url = f"{self.base_url}/internet/api/v0/get-probes"
        timeout_config = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS, timeout=timeout_config) as session:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise YandexAPIError(f"Process not started: {text}")
                    
                    # Update headers with any returned headers
                    for key, value in resp.headers.items():
                        self.headers[key] = value

                    # Parse response JSON into ProbesResponse
                    data = await resp.json()
                    self.probes = ProbesResponse.model_validate(data)
                    self.mid = self.probes.mid
                    self.lid = self.probes.lid

            except Exception as e:
                raise YandexAPIError(f"Failed to start process: {e}") from e

    # @deprecated("not stable enough, use measure_download_peak instead")
    async def measure_download(self, url: str, timeout: int = 10) -> Tuple[float, int]:
        """
        Download a file from the specified URL and measure the transfer performance.

        This method streams the content of the URL in chunks to avoid memory spikes
        and calculates the total number of bytes downloaded along with the total
        elapsed time in seconds.

        Parameters:
            url (str): The URL of the file or resource to download.
            timeout (int, optional): Connection timeout in seconds. Default is 60.

        Returns:
            Tuple[float, int]: 
                - Elapsed time in seconds (float). Returns `float('inf')` if download fails.
                - Total bytes downloaded (int). Returns 0 if download fails.
        """
        if not timeout:
            timeout = 10

        timeout_config = aiohttp.ClientTimeout(total=None, connect=timeout, sock_read=60)

        total_bytes = 0
        t0 = time.perf_counter()
        try:
            async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS, timeout=timeout_config) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return float('inf'), 0
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        total_bytes += len(chunk)
        except Exception:
            return float('inf'), 0
        t1 = time.perf_counter()
        return t1 - t0, total_bytes
    
    # @deprecated("not stable enough, use measure_upload_peak instead")
    async def measure_upload(self, url: str, size: int, timeout: int = None) -> Tuple[float, int]:
        """
        Perform an asynchronous file upload to a given URL.

        This method uploads a payload of the specified size using a streamed generator
        to avoid allocating large buffers in memory. It measures the total time taken
        for the upload and returns it along with the number of bytes uploaded.

        Parameters:
            url (str): The endpoint to which the data will be uploaded.
            size (int): The total size of the data to upload, in bytes.
            timeout (int, optional): Maximum time in seconds to establish the connection.
                                    Defaults to 10 seconds if not provided.

        Returns:
            Tuple[float, int]: A tuple containing:
                - The total time taken to upload the data, in seconds.
                - The number of bytes successfully uploaded.
                Returns `(float('inf'), 0)` in case of an error or failed upload.

        Notes:
            - Uses a 64 KB chunked stream for efficient memory usage.
            - The `aiohttp.ClientSession` is created per call to ensure isolated headers
            and timeout settings.
            - This is an asynchronous method and should be awaited.
        """
        if not timeout: 
            timeout = 10

        chunk = b"\0" * (64 * 1024)
        chunks = size // len(chunk)
        tail = size % len(chunk)

        async def gen():
            for _ in range(chunks):
                yield chunk
            if tail:
                yield b"\0" * tail

        timeout_config = aiohttp.ClientTimeout(total=None, connect=timeout, sock_read=120)
        t0 = time.perf_counter()
        async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS, timeout=timeout_config) as session:
            try:
                async with session.post(url, data=gen()) as r:
                    if r.status != 200:
                        return float('inf'), 0
                    await r.read()
            except Exception:
                return float('inf'), 0
        t1 = time.perf_counter()
        return t1 - t0, size
    
    async def measure_latency(
        self,
        url: str,
        timeout: int = None,
        attempts: int = 5,
        warmup: int = 1
    ) -> float:
        """
        Measures the actual network RTT (ping) as the median of several HEAD requests.

        The method is configured to measure latency as accurately as possible:
            - uses HEAD instead of GET (there's no time to read the payload);
            - skips the first warmup measurements (eliminates the effect of a cold TCP/TLS start);
            - uses trimmed median (tail trimming), eliminating outliers;
            - disables SSL validation to avoid inflating ping due to certificate checks;
            - uses the shortest possible timeouts.

        Parameters
        ----------
        `url` : str
            URL to which a series of HEAD requests are made.
        `timeout` : int, optional
            Maximum connection time. Default is 10 ms.
        `attempts` : int
            Number of ping measurement attempts (recommended 5-8).
        `warmup` : int
            Number of first attempts to be discarded.

        Returns
        -------
        float
            Median RTT in milliseconds. Returns a large number on errors.
        """

        if timeout is None:
            timeout = 10  # milliseconds

        timeout_config = aiohttp.ClientTimeout(
            total=30,
            connect=timeout,
            sock_read=1
        )

        times = []

        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(
            headers=self.DEFAULT_HEADERS,
            timeout=timeout_config,
            connector=connector
        ) as session:

            for i in range(attempts + warmup):
                t0 = time.perf_counter()
                try:
                    async with session.head(url) as r:
                        await r.release()
                    t1 = time.perf_counter()

                    if i >= warmup:
                        times.append((t1 - t0) * 1000)
                except Exception:
                    if i >= warmup:
                        times.append(10_000)

                await asyncio.sleep(0.02)

        if not times:
            return float("inf")

        if len(times) >= 5:
            times_sorted = sorted(times)
            k = max(1, len(times_sorted) // 5)
            times_trimmed = times_sorted[:-k]
            return statistics.median(times_trimmed)

        return statistics.median(times)
    
    async def measure_download_peak(self, url: str, timeout: int = 60) -> float:
        """
        Measures the peak incoming traffic speed (download) when receiving data
        from a specified HTTP resource. Downloading is performed in a stream, in uniform
        chunks, with the timestamp and
        size of each received block recorded. Based on the accumulated samples, the maximum
        throughput is calculated using a sliding-window algorithm, allowing for a
        correct and stable estimate of the actual peak throughput.

        Parameters:
            `url` (str):
                URL of the resource from which the test data download is being performed.
            `timeout` (int):
                Timeout for establishing a connection and reading, in seconds.
                Default: 60.

        Returns:
            float:
            Peak download speed in megabits per second (Mbps).
            If the server returns a status other than 200, the method
            returns 0.0.

        Key Features:
            • Downloaded data is read in streaming 64 KB chunks.
            • The time of receipt and its value are recorded for each received chunk. volume.
            • Based on a sequence of samples, the maximum speed is calculated
            using a sliding window, eliminating unrealistic jumps.
            • The method is resistant to network delays, buffering, and regular
            throughput fluctuations, ensuring a stable peak speed metric.
        """

        timeout_config = aiohttp.ClientTimeout(total=None, connect=timeout, sock_read=60)
        samples: Deque[Tuple[float, int]] = deque(maxlen=200000)

        async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS, timeout=timeout_config) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return 0.0

                async for chunk in resp.content.iter_chunked(64 * 1024):
                    now = time.perf_counter()
                    samples.append((now, len(chunk)))

        return self.__compute_peak_from_samples(samples)

    async def measure_upload_peak(self, url: str, size: int, timeout: int = 60) -> float:
        """
        Measures the peak outgoing traffic rate (upload) when sending
        a specified volume of data to the specified server. The transfer is performed
        in a stream, in fixed chunks, with parallel recording of timestamps
        and the sizes of the sent chunks. The resulting samples are analyzed using a
        sliding-window algorithm, ensuring a stable and correct calculation
        of the actual peak throughput without false spikes.

        Parameters:
            `url` (str): The destination of the HTTP POST request for test data transfer.
            `size` (int): The amount of data in bytes to send to the server.
            `timeout` (int): Connection and network operation timeout, in seconds. Default: 60.

        Returns:
            float: The peak data transfer rate, expressed in megabits per second (Mbps).
            If the server returns an invalid status, the method returns 0.0.

        Key Features:
            • Data is sent in a stream, in uniform 64 KB chunks.
            • For each sent block, the sending time and size are recorded.
            • Based on the collected samples, the maximum throughput is calculated
            using a sliding window, reflecting the actual peak network speed.
            • The method is robust to artifacts that arise during overly fast operations,
            and eliminates unrealistic outliers.
        """
        
        chunk = b"\0" * (64 * 1024)
        chunks = size // len(chunk)
        tail = size % len(chunk)

        timeout_config = aiohttp.ClientTimeout(total=None, connect=timeout, sock_read=120)
        samples: Deque[Tuple[float, int]] = deque(maxlen=200000)

        async def gen():
            nonlocal samples
            for _ in range(chunks):
                now = time.perf_counter()
                samples.append((now, len(chunk)))
                yield chunk
            if tail:
                now = time.perf_counter()
                samples.append((now, tail))
                yield b"\0" * tail

        async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS, timeout=timeout_config) as session:
            async with session.post(url, data=gen()) as resp:
                if resp.status != 200:
                    return 0.0
                await resp.read()

        return  self.__compute_peak_from_samples(samples)

    async def run(self, attempts: int = 5) -> SpeedResult:
        """Main async entry point to measure internet speed.
        
        Steps:
        1. Fetch probes.
        2. Measure latency for available latency probes in parallel.
        3. Run download and upload probes against that lid in parallel.
        4. Return SpeedResult with ping, download and upload Mbps.
        """
        latency_probes = self.probes.latency.probes
        download_probes = self.probes.download.probes
        upload_probes = self.probes.upload.probes

        # --- measure latency in parallel ---
        async def ping_task(probe: ProbeModel):
            results = []
            for _ in range(attempts):
                try:
                    ping_ms = await self.measure_latency(probe.url, probe.timeout)
                except Exception:
                    ping_ms = float('inf')
                results.append(ping_ms)
            results.sort()
            median = results[len(results) // 2] if results else float('inf')
            return median

        latency_results = await asyncio.gather(*(ping_task(probe) for probe in latency_probes))
        latency_ms = min(latency_results) if latency_results else 0.0

        # --- prepare download probes in alternating order ---
        def alternating(probes):
            large = [p for p in probes if '50mb' in p.url]
            small = [p for p in probes if '100kb' in p.url]
            result = []
            for i in range(max(len(large), len(small))):
                if i < len(large):
                    result.append(large[i])
                if i < len(small):
                    result.append(small[i])
            return result

        # --- measure downloads in parallel ---
        async def download_task(probe:ProbeModel):
            speeds = []
            for _ in range(attempts):
                mbps = await self.measure_download_peak(probe.url, probe.timeout)
                speeds.append(mbps)
            return max(speeds) if mbps else 0.0

        download_speeds = await asyncio.gather(*(download_task(probe) for probe in alternating(download_probes)))
        download_mbps = max(download_speeds) if download_speeds else 0.0

        # --- measure uploads in parallel ---
        async def upload_task(probe:ProbeModel):
            if not probe.size or probe.size <= 0:
                return 0.0
            speeds = []
            for _ in range(attempts):
                mbps = await self.measure_upload_peak(probe.url, probe.size, probe.timeout)
                speeds.append(mbps)
            return max(speeds) if speeds else 0.0

        upload_speeds = await asyncio.gather(*(upload_task(probe) for probe in upload_probes))
        upload_mbps = max(upload_speeds) if upload_speeds else 0.0

        return SpeedResult(
            ping_ms=latency_ms,
            download_mbps=download_mbps,
            upload_mbps=upload_mbps
        )