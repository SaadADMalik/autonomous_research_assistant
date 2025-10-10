from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class AgentInput:
    query: str
    context: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class AgentOutput:
    result: str
    confidence: float
    metadata: Optional[Dict] = None