import asyncio
import argparse
from yaspeedtest.client import YaSpeedTest
from yaspeedtest.types import SpeedResult

async def run_cli(count: int = 1, json_output: bool = False):
    """
    Runs YaSpeedTest in CLI mode.

    Runs network performance measurements through a single YaSpeedTest instance and returns the results in human-readable or JSON format.
    Used as an asynchronous entry point for the CLI wrapper.

    Args:
        `count` (int): The number of consecutive measurements to be performed. All results are aggregated using the `ya.run(count)` method.
        `json_output` (bool): Flag enabling output of results in JSON format. If `True`, the CLI returns a structured JSON object without any additional formatting.

    Returns:
        None: The function outputs data directly to stdout and does not return a value.

    Raises:
        Exception: Any unhandled exceptions are propagated up the stack. It is recommended to use external handlers when embedding the CLI in other processes.
    """

    ya = await YaSpeedTest.create()
    result:SpeedResult = await ya.run(count)

    if json_output:
        import json
        print(json.dumps(
            {
                "ping_ms": result.ping_ms,
                "download_mbps": result.download_mbps,
                "upload_mbps": result.upload_mbps
            }, 
            indent=2)
        )
        return

    print(f"Ping: {result.ping_ms:.2f} ms | "
            f"Download: {result.download_mbps:.2f} Mbps | "
            f"Upload: {result.upload_mbps:.2f} Mbps")

def main():
    """
    Entry point for the `yaspeedtest` CLI tool.

    Responsible for processing command-line arguments, initializing
    asynchronous execution, and passing parameters to `run_cli`.

    Command line arguments:
        `--count` or `-c` (int): Number of measurements. Defaults to 1.
        `--json` (flag): Enables the JSON output format.

    Behavior:
        - Parses parameters and generates an `args` object.
        - Runs the asynchronous `run_cli()` function via `asyncio.run`.
        - Provides a standard user experience for installing via pip and invoking
        the `yaspeedtest` command in the terminal.
    """

    parser = argparse.ArgumentParser(description="YaSpeedTest CLI")
    parser.add_argument("--count", "-c", type=int, default=1,
                        help="Tests count")
    parser.add_argument("--json", action="store_true",
                        help="Return JSON format")

    args = parser.parse_args()
    asyncio.run(run_cli(args.count, args.json))