from pydantic import BaseModel

class LinkCodeResponse(BaseModel):
    code: str

class SuccessResponse(BaseModel):
    success: bool
