from pydantic import BaseModel, Field

class AgentInput(BaseModel):
    query: str
    context: str = ""  # Optional context with empty string as default

class AgentOutput(BaseModel):
    result: str
    confidence: float = Field(ge=0.0, le=1.0)  # Ensure confidence is between 0 and 1