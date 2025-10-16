# schemas.py
from typing import List
from pydantic import BaseModel, AnyHttpUrl

class Attachment(BaseModel):
    name: str
    url: str  # data URI or http(s)

class SubmitPayload(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: List[str]
    evaluation_url: AnyHttpUrl
    attachments: List[Attachment] = []
