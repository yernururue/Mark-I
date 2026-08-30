from datetime import datetime

from pydantic import BaseModel, Field

class TelegramLinkResponse(BaseModel):
    linkCode: str = Field(pattern=r"^[A-Z0-9]{6}$")
    expiresAt: datetime
    botUsername: str

class SuccessResponse(BaseModel):
    unlinked: bool


# Existing service imports retain the implementation name while the canonical
# OpenAPI component keeps the public contract name.
LinkCodeResponse = TelegramLinkResponse
