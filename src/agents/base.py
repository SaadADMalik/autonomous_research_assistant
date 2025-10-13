from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class AgentInput(BaseModel):
    query: str
    context: str = ""  # Optional context with empty string as default
    metadata: Optional[Dict[str, Any]] = None  # Add this field

class AgentOutput(BaseModel):
    result: str
    confidence: float = Field(ge=0.0, le=1.0)  # Ensure confidence is between 0 and 1
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Add metadata field