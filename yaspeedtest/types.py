from pydantic import BaseModel

class SpeedResult(BaseModel):
    ping_ms: float
    download_mbps: float
    upload_mbps: float

    def as_dict(self):
        return {
            "ping_ms": self.ping_ms,
            "download_mbps": self.download_mbps,
            "upload_mbps": self.upload_mbps
        }
    
class ProbeModel(BaseModel):
    url: str | None = None
    timeout: int | None = None
    size: int | None = None

class ProbesList(BaseModel):
    probes: list[ProbeModel]

class ProbesResponse(BaseModel):
    mid: str
    lid: list[str]
    latency: ProbesList
    download: ProbesList
    upload: ProbesList
    perfLog: str

class YandexAPIError(RuntimeError):
    pass