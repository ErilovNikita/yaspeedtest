"""yainternet package
Public API: YaSpeedTest
"""
from yaspeedtest.client import YaSpeedTest
from .types import SpeedResult, ProbeModel, ProbesResponse

__all__ = ["YaSpeedTest", "SpeedResult", "ProbeModel", "ProbesResponse"]
__author__ = "Erilov Nikita"