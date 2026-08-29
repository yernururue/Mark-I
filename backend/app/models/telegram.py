from datetime import datetime

from pydantic import BaseModel

class LinkCodeResponse(BaseModel):
    linkCode: str
    expiresAt: datetime
    botUsername: str

class SuccessResponse(BaseModel):
    unlinked: bool
