from typing import TypedDict, Literal, Optional
from pydantic import BaseModel

class ResponseFormat(TypedDict):
    response: str
