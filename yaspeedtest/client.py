"""API client for yandex.ru/internet minimal endpoints we need."""
import requests
import time
import statistics
import asyncio
import aiohttp
from typing import Tuple

from yaspeedtest.types import YandexAPIError, ProbesResponse

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
    URL_GET_PROBES = "/internet/api/v0/get-probes"
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://yandex.ru".rstrip("/")
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.probes:ProbesResponse = None

        self.__start_proccess()

    def __start_proccess(self) -> None:
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
        url = f"{self.base_url}{self.URL_GET_PROBES}"
        r = self.session.get(url, timeout=10)
        if not r.ok:
            raise YandexAPIError(f"Proccess not started: {r.text}")
        else:
            for key, value in r.headers.items():
                self.session.headers[key] = value
            
            self.probes:ProbesResponse = ProbesResponse.model_validate(r.json())
            self.mid = self.probes.mid
            self.lid = self.probes.lid

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
    
    async def measure_latency(self, url: str, timeout: int = None, attempts: int = 5) -> float:
        """
        Measure the network latency (ping) to a given URL.

        This method performs multiple HTTP GET requests to the target URL
        and calculates the median round-trip time (RTT) in milliseconds.

        Parameters:
            url (str): The URL to ping.
            attempts (int, optional): Number of GET requests to perform. Default is 5.

        Returns:
            float: The median ping in milliseconds. Returns a large value if all attempts fail.
        """
        times = []

        if not timeout: 
            timeout = 10

        timeout_config = aiohttp.ClientTimeout(total=10, connect=timeout, sock_read=10)
        async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS, timeout=timeout_config) as session:
            for _ in range(attempts):
                t0 = time.perf_counter()
                try:
                    async with session.get(url) as r:
                        await r.read() 
                        t1 = time.perf_counter()
                        times.append((t1 - t0) * 1000)
                except Exception:
                    times.append(10000)
                await asyncio.sleep(0.05)

        if not times:
            return float('inf')
        return statistics.median(times)
    
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