from .base import BaseAgent
from .models import AgentInput, AgentOutput

class ResearcherAgent(BaseAgent):
    async def run(self, input_data: AgentInput) -> AgentOutput:
        # Placeholder implementation
        return AgentOutput(
            result=f"Research findings for query: {input_data.query}",
            confidence=0.8
        )