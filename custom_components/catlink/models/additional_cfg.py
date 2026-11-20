"""Models for additional device configuration."""

from pydantic import BaseModel


class AdditionalDeviceConfig(BaseModel):
    """Additional device configuration."""

    name: str = ""
    mac: str = ""
    empty_weight: float = 0.0
