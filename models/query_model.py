from pydantic import BaseModel
from typing import List

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    summary: str
    laws: List[str]
    suggestions: List[str]
