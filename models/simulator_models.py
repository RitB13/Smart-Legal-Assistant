from pydantic import BaseModel
from typing import Optional, List


class SimulatorRequest(BaseModel):
    action: str
    jurisdiction: Optional[str] = "India"
    context: Optional[str] = None


class SimulatorResponse(BaseModel):

    risk_level: str
    laws: List[str]
    penalties: str
    alternatives: List[str]
    checklist: List[str]
    explanation: str